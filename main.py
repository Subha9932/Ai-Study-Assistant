import os
import json
import re
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
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

# Import database and authentication modules
from database import (
    users_collection, 
    summaries_collection, 
    quizzes_collection, 
    create_indexes, 
    close_db_connection,
    test_connection
)
from auth_handler import create_access_token, create_refresh_token, verify_token, JWT_SECRET, JWT_ALGORITHM
from otp_service import generate_otp, store_otp, verify_otp, send_otp_email, OTP_EXPIRY_MINUTES

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
    """Initialize database on startup"""
    await test_connection()
    await create_indexes()
    print("🚀 Application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
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
    """Call Gemini model safely"""
    try:
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini failed: {e}")

def extract_video_id(url: str):
    """Extract YouTube video ID from various URL formats"""
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
    """Clean YouTube URL to standard format"""
    video_id = extract_video_id(url)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url

def get_youtube_transcript(video_id: str):
    """Try to fetch transcript from YouTube video in ANY language"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
            transcript_data = transcript.fetch()
            transcript_text = " ".join([item['text'] for item in transcript_data])
            return (transcript_text, 'en')
        except:
            pass
        
        try:
            available_transcripts = list(transcript_list)
            if available_transcripts:
                transcript = available_transcripts[0]
                print(f"Found transcript in language: {transcript.language_code}")
                
                try:
                    translated = transcript.translate('en')
                    transcript_data = translated.fetch()
                    transcript_text = " ".join([item['text'] for item in transcript_data])
                    print("Successfully translated to English")
                    return (transcript_text, 'en-translated')
                except Exception as translate_error:
                    print(f"Translation failed: {translate_error}")
                    transcript_data = transcript.fetch()
                    transcript_text = " ".join([item['text'] for item in transcript_data])
                    return (transcript_text, transcript.language_code)
        except Exception as e:
            print(f"Could not fetch any transcript: {e}")
            return (None, None)
            
    except Exception as e:
        print(f"Transcript API error: {e}")
        return (None, None)

def analyze_youtube_with_gemini(youtube_url: str):
    """Use Gemini's native video understanding to analyze YouTube video"""
    try:
        clean_url = clean_youtube_url(youtube_url)
        print(f"Analyzing video with Gemini: {clean_url}")
        
        prompt = """
Please analyze this YouTube video and provide a comprehensive summary formatted as study notes.

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
        
        response = model.generate_content([
            {
                "file_data": {
                    "file_uri": clean_url
                }
            },
            prompt
        ])
        
        return response.text.strip()
        
    except Exception as e:
        error_msg = str(e)
        print(f"Gemini video analysis error: {error_msg}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to analyze video with Gemini: {error_msg}. Make sure the video is public or unlisted."
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
    """Register new user in MongoDB"""
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
        "updated_at": datetime.utcnow()
    }
    
    await users_collection.insert_one(user_doc)
    print(f"✅ User registered in MongoDB: {user.email}")
    
    return {"message": "User registered. Please verify your email", "user_id": user_id}

@app.post("/api/auth/send-otp")
async def send_otp(request: OTPRequest):
    """Send OTP to user's email and store in MongoDB"""
    otp = generate_otp()
    await store_otp(request.email, otp)  # Stores in MongoDB
    send_otp_email(request.email, otp)
    
    print(f"✅ OTP stored in MongoDB for: {request.email}")
    
    return {
        "message": "OTP sent successfully to your email",
        "expires_in": OTP_EXPIRY_MINUTES * 60
    }

@app.post("/api/auth/verify-otp")
async def verify_otp_endpoint(request: OTPVerify):
    """Verify OTP from MongoDB and issue JWT tokens"""
    if not await verify_otp(request.email, request.otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    user = await users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await users_collection.update_one(
        {"email": request.email},
        {
            "$set": {
                "verified": True,
                "last_login": datetime.utcnow()
            }
        }
    )
    
    print(f"✅ User verified in MongoDB: {request.email}")
    
    access_token = create_access_token(user["user_id"], user["email"])
    refresh_token = create_refresh_token(user["user_id"])
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "full_name": user["full_name"]
        }
    }

@app.post("/api/auth/refresh")
async def refresh_access_token(refresh_token: str):
    """Refresh expired access token"""
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
    """Get user profile from MongoDB"""
    user_id = token_data["user_id"]
    user = await users_collection.find_one({"user_id": user_id})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.pop('_id', None)
    return {"profile": user}

# ---------------- Summarize Routes (Store in MongoDB) ----------------
@app.post("/api/summarize")
async def summarize(payload: SummarizeRequest, token_data: dict = Security(verify_token)):
    """Summarize text or YouTube and store in MongoDB"""
    user_id = token_data["user_id"]
    
    if payload.youtube_url:
        video_id = extract_video_id(payload.youtube_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL format")
        
        print(f"Processing video: {video_id}")
        
        transcript_text, lang_code = get_youtube_transcript(video_id)
        
        if transcript_text:
            print(f"Using transcript (language: {lang_code})")
            prompt = f"""
Summarize the following YouTube video transcript into clear, concise study notes.
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
            print("No transcript available. Using Gemini video analysis...")
            summary = analyze_youtube_with_gemini(payload.youtube_url)
        
        # Save to MongoDB
        summary_doc = {
            "user_id": user_id,
            "type": "youtube",
            "source": payload.youtube_url,
            "video_id": video_id,
            "summary": summary,
            "created_at": datetime.utcnow()
        }
        result = await summaries_collection.insert_one(summary_doc)
        print(f"✅ YouTube summary stored in MongoDB: {result.inserted_id}")
        
        return {"summary": summary}
    
    elif payload.text:
        prompt = f"""
Summarize the following text into clear, concise study notes.
Format your response using Markdown:
- Use **bold** for important terms
- Use ## for main headings and ### for subheadings
- Use bullet points (-) for lists

Text:
{payload.text[:20000]}
"""
        summary = call_gemini(prompt)
        
        # Save to MongoDB
        summary_doc = {
            "user_id": user_id,
            "type": "text",
            "original_text": payload.text[:1000],  # Store first 1000 chars
            "summary": summary,
            "created_at": datetime.utcnow()
        }
        result = await summaries_collection.insert_one(summary_doc)
        print(f"✅ Text summary stored in MongoDB: {result.inserted_id}")
        
        return {"summary": summary}
    
    else:
        raise HTTPException(status_code=400, detail="No text or YouTube URL provided")

@app.post("/api/summarize-pdf")
async def summarize_pdf(file: UploadFile = File(...), token_data: dict = Security(verify_token)):
    """Summarize PDF and store in MongoDB"""
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
            except:
                pass
        
        if not text.strip():
            raise ValueError("No readable text found in PDF.")
        
        prompt = f"Summarize this PDF into concise study notes using Markdown:\n\n{text[:20000]}"
        summary = call_gemini(prompt)
        
        # Save to MongoDB
        summary_doc = {
            "user_id": user_id,
            "type": "pdf",
            "filename": file.filename,
            "summary": summary,
            "created_at": datetime.utcnow()
        }
        result = await summaries_collection.insert_one(summary_doc)
        print(f"✅ PDF summary stored in MongoDB: {result.inserted_id}")
        
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

# ---------------- Quiz Routes (Store in MongoDB) ----------------
@app.post("/api/quiz")
async def generate_quiz(input: QuizRequest, token_data: dict = Security(verify_token)):
    """Generate quiz and store in MongoDB"""
    user_id = token_data["user_id"]
    
    try:
        prompt = f"""
Generate 5 multiple-choice quiz questions from this material:
"{input.text[:5000]}"

Return ONLY a JSON array (no markdown):
[
{{
  "question": "Question text",
  "options": ["A", "B", "C", "D"],
  "answer_index": 0,
  "explanation": "Why this is correct"
}}
]
"""
        response = model.generate_content(prompt)
        text = response.text.strip().replace("``````", "").strip()
        quiz = json.loads(text)
        
        # Save to MongoDB
        quiz_doc = {
            "user_id": user_id,
            "source_text": input.text[:1000],  # Store first 1000 chars
            "questions": quiz,
            "created_at": datetime.utcnow()
        }
        result = await quizzes_collection.insert_one(quiz_doc)
        print(f"✅ Quiz stored in MongoDB: {result.inserted_id}")
        
        return {"questions": quiz}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {e}")

# ---------------- Download Quiz PDF ----------------
@app.post("/api/download-quiz")
async def download_quiz(input: DownloadRequest):
    """Download quiz as PDF (no auth required for download)"""
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

            for j, opt in enumerate(q['options']):
                opt_text = f"   {chr(65+j)}. {opt}"
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
        return StreamingResponse(buffer, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename={input.title}.pdf"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

# ---------------- Get User History ----------------
@app.get("/api/user/summaries")
async def get_user_summaries(token_data: dict = Security(verify_token)):
    """Get all summaries for logged-in user"""
    user_id = token_data["user_id"]
    
    cursor = summaries_collection.find({"user_id": user_id}).sort("created_at", -1).limit(50)
    summaries = await cursor.to_list(length=50)
    
    # Remove MongoDB _id field
    for summary in summaries:
        summary.pop('_id', None)
    
    return {"summaries": summaries}

@app.get("/api/user/quizzes")
async def get_user_quizzes(token_data: dict = Security(verify_token)):
    """Get all quizzes for logged-in user"""
    user_id = token_data["user_id"]
    
    cursor = quizzes_collection.find({"user_id": user_id}).sort("created_at", -1).limit(50)
    quizzes = await cursor.to_list(length=50)
    
    # Remove MongoDB _id field
    for quiz in quizzes:
        quiz.pop('_id', None)
    
    return {"quizzes": quizzes}

# ---------------- Root Endpoint ----------------
@app.get("/")
async def root():
    return {"message": "AI Study Assistant API with MongoDB - All data persisted"}
