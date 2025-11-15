import os
import json
import re
import traceback
import jwt
import secrets
from io import BytesIO
from textwrap import wrap
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from passlib.context import CryptContext

import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

from database import (
    users_collection,
    summaries_collection,
    quizzes_collection,
    create_indexes,
    close_db_connection,
    test_connection,
)
from auth_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    JWT_SECRET,
    JWT_ALGORITHM,
)
from otp_service import (
    generate_otp,
    store_otp,
    verify_otp,
    send_otp_email,
    OTP_EXPIRY_MINUTES,
)

# ---------------- Load ENV ----------------
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "models/gemini-2.0-flash-exp")
if not GEMINI_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

# ---------------- Configure Gemini ----------------
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel(MODEL_NAME)

# ---------------- FastAPI App ----------------
app = FastAPI(title="AI Study Assistant API")

@app.on_event("startup")
async def startup_event():
    await test_connection()
    await create_indexes()
    print("🚀 Application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    await close_db_connection()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------- Helper Functions ----------------
def call_gemini(prompt: str):
    try:
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini failed: {e}")

def extract_video_id(url: str):
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def clean_youtube_url(url: str):
    video_id = extract_video_id(url)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url

def get_youtube_transcript(video_id: str):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(["en", "en-US", "en-GB"])
            transcript_data = transcript.fetch()
            transcript_text = " ".join([item["text"] for item in transcript_data])
            return (transcript_text, "en")
        except Exception:
            pass

        available_transcripts = list(transcript_list)
        if available_transcripts:
            transcript = available_transcripts[0]
            try:
                translated = transcript.translate("en")
                transcript_data = translated.fetch()
                transcript_text = " ".join([item["text"] for item in transcript_data])
                return (transcript_text, "en-translated")
            except Exception:
                transcript_data = transcript.fetch()
                transcript_text = " ".join([item["text"] for item in transcript_data])
                return (transcript_text, transcript.language_code)
        return (None, None)
    except Exception:
        return (None, None)

def analyze_youtube_with_gemini(youtube_url: str):
    try:
        clean_url = clean_youtube_url(youtube_url)
        prompt = """Please analyze this YouTube video and provide a comprehensive summary formatted as study notes.
Use the following Markdown formatting:
- Use **bold** for important terms and key concepts
- Use ## for main topics and ### for subtopics
- Use bullet points (-) for lists
- Use numbered lists (1., 2., etc.) for sequential information
- Use > for important quotes or key takeaways
Include:
1. Main topic and purpose of the video
2. Key concepts explained
3. Important details and examples
4. Practical applications or takeaways
"""
        response = model.generate_content(
            [
                {"file_data": {"file_uri": clean_url}},
                prompt,
            ]
        )
        return (response.text or "").strip()
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze video with Gemini: {error_msg}. Make sure the video is public or unlisted.",
        )

# ---------------- Pydantic Models ----------------
class SummarizeRequest(BaseModel):
    text: str = None
    youtube_url: str = None

class QuizRequest(BaseModel):
    text: str

class DownloadRequest(BaseModel):
    title: str
    quiz_data: list

class UserCreate(BaseModel):
    email: str
    phone: Optional[str] = ""
    full_name: str

class OTPRequest(BaseModel):
    email: str
    phone: Optional[str] = None

class OTPVerify(BaseModel):
    email: str
    otp: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

# ---------------- Authentication Routes ----------------
@app.post("/api/auth/register")
async def register_user(user: UserCreate):
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user_id = secrets.token_urlsafe(16)
    user_doc = {
        "user_id": user_id,
        "email": user.email,
        "phone": user.phone or "",
        "full_name": user.full_name,
        "verified": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await users_collection.insert_one(user_doc)
    return {"message": "User registered. Please verify your email", "user_id": user_id}

@app.post("/api/auth/send-otp")
async def send_otp(request: OTPRequest):
    otp = generate_otp()
    await store_otp(request.email, otp)
    send_otp_email(request.email, otp)
    return {"message": "OTP sent successfully to your email", "expires_in": OTP_EXPIRY_MINUTES * 60}

@app.post("/api/auth/verify-otp")
async def verify_otp_endpoint(request: OTPVerify):
    if not await verify_otp(request.email, request.otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user = await users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await users_collection.update_one(
        {"email": request.email},
        {"$set": {"verified": True, "last_login": datetime.utcnow()}},
    )

    access_token = create_access_token(user["user_id"], user["email"])
    refresh_token = create_refresh_token(user["user_id"])

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "full_name": user["full_name"],
        },
    }

@app.post("/api/auth/refresh")
async def refresh_access_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=403, detail="Invalid token type")

        user_id = payload["user_id"]
        user = await users_collection.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_access_token = create_access_token(user_id, user["email"])
        return {"access_token": new_access_token, "token_type": "bearer"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token")

@app.get("/api/user/profile")
async def get_profile(token_data: dict = Security(verify_token)):
    user_id = token_data["user_id"]
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.pop("_id", None)
    return {"profile": user}

# ---------------- Summarize (Text or YouTube) ----------------
@app.post("/api/summarize")
async def summarize(payload: SummarizeRequest, token_data: dict = Security(verify_token)):
    user_id = token_data["user_id"]

    if payload.youtube_url:
        video_id = extract_video_id(payload.youtube_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL format")

        transcript_text, lang_code = get_youtube_transcript(video_id)
        if transcript_text:
            prompt = f"""Summarize the following YouTube video transcript into clear, concise study notes.
Format your response using Markdown:
- Use **bold** for important terms
- Use ## for main headings and ### for subheadings
- Use bullet points (-) for lists
- Use numbered lists (1., 2., etc.) for sequential steps
- Use > for important quotes or highlights

Transcript:
{transcript_text[:25000]}
"""
            summary = call_gemini(prompt)
        else:
            summary = analyze_youtube_with_gemini(payload.youtube_url)

        summary_doc = {
            "user_id": user_id,
            "type": "youtube",
            "source": payload.youtube_url,
            "video_id": video_id,
            "summary": summary,
            "created_at": datetime.utcnow(),
        }
        await summaries_collection.insert_one(summary_doc)
        return {"summary": summary}

    if payload.text:
        prompt = f"""Summarize the following text into clear, concise study notes.
Format your response using Markdown:
- Use **bold** for important terms
- Use ## for main headings and ### for subheadings
- Use bullet points (-) for lists

Text:
{payload.text[:20000]}
"""
        summary = call_gemini(prompt)
        summary_doc = {
            "user_id": user_id,
            "type": "text",
            "original_text": payload.text[:1000],
            "summary": summary,
            "created_at": datetime.utcnow(),
        }
        await summaries_collection.insert_one(summary_doc)
        return {"summary": summary}

    raise HTTPException(status_code=400, detail="No text or YouTube URL provided")

# ---------------- Summarize PDF ----------------
@app.post("/api/summarize-pdf")
async def summarize_pdf(file: UploadFile = File(...), token_data: dict = Security(verify_token)):
    user_id = token_data["user_id"]
    try:
        from PyPDF2 import PdfReader

        content = await file.read()
        pdf = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        if not text.strip():
            try:
                import pdfplumber

                with pdfplumber.open(BytesIO(content)) as pdf_plumb:
                    text = "\n".join(page.extract_text() or "" for page in pdf_plumb.pages)
            except Exception:
                pass

        if not text.strip():
            raise ValueError("No readable text found in PDF.")

        prompt = f"Summarize this PDF into concise study notes using Markdown:\n\n{text[:20000]}"
        summary = call_gemini(prompt)

        summary_doc = {
            "user_id": user_id,
            "type": "pdf",
            "filename": file.filename,
            "summary": summary,
            "created_at": datetime.utcnow(),
        }
        await summaries_collection.insert_one(summary_doc)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

@app.post("/api/quiz")
async def generate_quiz(input: QuizRequest, token_data: dict = Security(verify_token)):
    """Generate quiz and store in MongoDB with robust error handling"""
    user_id = token_data["user_id"]
    try:
        prompt = f"""You are a quiz generator. Create exactly 5 multiple-choice questions.

Text to analyze:
{input.text[:5000]}

CRITICAL: Return ONLY a valid JSON array. No markdown, no code blocks, no explanations.

Expected format:
[
  {{"question": "What is the main concept?", "options": ["Option A", "Option B", "Option C", "Option D"], "answer_index": 0, "explanation": "Brief explanation"}}
]

Rules:
- Exactly 5 questions
- Exactly 4 options per question
- answer_index must be 0, 1, 2, or 3
- No markdown formatting
- Pure JSON only
"""
        response = model.generate_content(prompt)
        raw_text = (response.text or "").strip()

        # SAFELY strip markdown fences (build fence strings at runtime to avoid syntax errors)
        cleaned_text = raw_text
        fence_json = chr(96) + chr(96) + chr(96) + "json"  # ```
        fence = chr(96) + chr(96) + chr(96)  # ```
        
        if fence_json in cleaned_text:
            parts = cleaned_text.split(fence_json, 1)
            cleaned_text = parts[1] if len(parts) > 1 else cleaned_text
        
        if fence in cleaned_text:
            parts2 = cleaned_text.split(fence, 1)
            cleaned_text = parts2[0]
        
        cleaned_text = cleaned_text.strip()

        # Parse JSON with fallback extractor
        try:
            quiz = json.loads(cleaned_text)
        except json.JSONDecodeError:
            m = re.search(r"\[\s*\{[\s\S]*\}\s*\]", cleaned_text)
            if not m:
                raise HTTPException(status_code=500, detail="Could not extract valid JSON from AI response. Try again with a longer summary.")
            try:
                quiz = json.loads(m.group(0))
            except Exception:
                raise HTTPException(status_code=500, detail="AI returned invalid JSON format. Try again with a longer summary.")

        # Validate structure
        if not isinstance(quiz, list) or len(quiz) == 0:
            raise HTTPException(status_code=500, detail="AI returned empty or invalid quiz list.")

        valid_questions = []
        for i, q in enumerate(quiz):
            try:
                if not all(k in q for k in ["question", "options", "answer_index"]):
                    continue
                if not isinstance(q["options"], list) or len(q["options"]) < 2:
                    continue

                # Ensure exactly 4 options
                if len(q["options"]) < 4:
                    while len(q["options"]) < 4:
                        q["options"].append(f"Option {len(q['options']) + 1}")
                elif len(q["options"]) > 4:
                    q["options"] = q["options"][:4]

                # Validate answer index
                if not isinstance(q["answer_index"], int) or q["answer_index"] < 0 or q["answer_index"] > 3:
                    q["answer_index"] = 0

                # Add explanation if missing
                if "explanation" not in q or not q["explanation"]:
                    q["explanation"] = f"The correct answer is: {q['options'][q['answer_index']]}"

                valid_questions.append(q)
            except Exception:
                continue

        if len(valid_questions) < 3:
            raise HTTPException(status_code=500, detail="Only a few valid questions were generated. Try with a more detailed summary.")

        quiz = valid_questions[:5]

        # Store in MongoDB
        quiz_doc = {
            "user_id": user_id,
            "source_text": input.text[:1000],
            "questions": quiz,
            "created_at": datetime.utcnow(),
        }
        await quizzes_collection.insert_one(quiz_doc)
        return {"questions": quiz}
        
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Quiz generation failed. Please try again.")

# ---------------- Download Quiz PDF ----------------
@app.post("/api/download-quiz")
async def download_quiz(input: DownloadRequest):
    try:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 50

        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, input.title)
        y -= 30

        c.setFont("Helvetica", 10)
        for i, q in enumerate(input.quiz_data):
            question_text = f"Q{i+1}: {q['question']}"
            wrapped = wrap(question_text, width=80)
            for line in wrapped:
                if y < 100:
                    c.showPage()
                    y = height - 50
                c.drawString(50, y, line)
                y -= 15

            for j, opt in enumerate(q["options"]):
                opt_text = f"   {chr(65 + j)}. {opt}"
                wrapped_opt = wrap(opt_text, width=78)
                for line in wrapped_opt:
                    if y < 100:
                        c.showPage()
                        y = height - 50
                    c.drawString(50, y, line)
                    y -= 12
            y -= 10

        c.save()
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={input.title}.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

# ---------------- User History ----------------
@app.get("/api/user/summaries")
async def get_user_summaries(token_data: dict = Security(verify_token)):
    user_id = token_data["user_id"]
    cursor = summaries_collection.find({"user_id": user_id}).sort("created_at", -1).limit(50)
    summaries = await cursor.to_list(length=50)
    for s in summaries:
        s.pop("_id", None)
    return {"summaries": summaries}

@app.get("/api/user/quizzes")
async def get_user_quizzes(token_data: dict = Security(verify_token)):
    user_id = token_data["user_id"]
    cursor = quizzes_collection.find({"user_id": user_id}).sort("created_at", -1).limit(50)
    quizzes = await cursor.to_list(length=50)
    for q in quizzes:
        q.pop("_id", None)
    return {"quizzes": quizzes}

# ---------------- Root ----------------
@app.get("/")
async def root():
    return {"message": "AI Study Assistant API with MongoDB - All data persisted"}
