import os
import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from fastapi import HTTPException
from database import otp_collection

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 3

def generate_otp(length: int = OTP_LENGTH) -> str:
    """Generate secure numeric OTP"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))

async def store_otp(email: str, otp: str, expiry_minutes: int = OTP_EXPIRY_MINUTES):
    """Store OTP in MongoDB with expiration - ASYNC"""
    expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    
    # Upsert (update if exists, insert if not)
    await otp_collection.update_one(
        {"email": email},
        {
            "$set": {
                "otp": otp,
                "expires_at": expires_at,
                "attempts": 0,
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    print(f"✅ Stored OTP for {email}: {otp}")

async def verify_otp(email: str, otp: str) -> bool:
    """Verify OTP with rate limiting - ASYNC"""
    otp_doc = await otp_collection.find_one({"email": email})
    
    if not otp_doc:
        raise HTTPException(status_code=400, detail="OTP not found. Please request a new one.")
    
    # Check expiration
    if datetime.utcnow() > otp_doc["expires_at"]:
        await otp_collection.delete_one({"email": email})
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")
    
    # Check attempts
    if otp_doc["attempts"] >= MAX_OTP_ATTEMPTS:
        await otp_collection.delete_one({"email": email})
        raise HTTPException(status_code=429, detail="Too many failed attempts. Please request a new OTP.")
    
    # Verify OTP
    if otp_doc["otp"] != otp:
        # Increment attempts
        await otp_collection.update_one(
            {"email": email},
            {"$inc": {"attempts": 1}}
        )
        return False
    
    # Success - delete OTP
    await otp_collection.delete_one({"email": email})
    return True

def send_otp_email(email: str, otp: str):
    """Send OTP via Gmail SMTP - NOT ASYNC"""
    SMTP_EMAIL = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print(f"\n{'='*60}")
        print(f"📧 OTP SENT TO: {email}")
        print(f"🔐 OTP CODE: {otp}")
        print(f"⚠️  Email not configured - using console mode")
        print(f"{'='*60}\n")
        return True
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Your AI Study Assistant OTP: {otp}"
        msg['From'] = SMTP_EMAIL
        msg['To'] = email
        
        # HTML email body
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
              <div style="text-align: center; margin-bottom: 30px;">
                <h2 style="color: #667eea; margin: 0;">🎓 AI Study Assistant</h2>
                <p style="color: #666; margin-top: 10px;">Secure Login Verification</p>
              </div>
              
              <p style="color: #333; font-size: 16px;">Hello,</p>
              <p style="color: #666; font-size: 14px; line-height: 1.6;">
                Your one-time password (OTP) for logging into AI Study Assistant is:
              </p>
              
              <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; font-size: 36px; font-weight: bold; 
                          padding: 25px; text-align: center; border-radius: 10px; 
                          letter-spacing: 10px; margin: 25px 0;">
                {otp}
              </div>
              
              <div style="background: #fef5e7; padding: 15px; border-radius: 8px; border-left: 4px solid #f39c12; margin: 20px 0;">
                <p style="color: #856404; margin: 0; font-size: 14px;">
                  ⏰ This code will expire in <strong>{OTP_EXPIRY_MINUTES} minutes</strong>
                </p>
              </div>
              
              <p style="color: #666; font-size: 14px; line-height: 1.6;">
                If you didn't request this code, please ignore this email.
              </p>
              
              <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
              
              <p style="color: #999; font-size: 12px; text-align: center; margin: 0;">
                © 2025 AI Study Assistant. All rights reserved.<br>
                This is an automated message, please do not reply.
              </p>
            </div>
          </body>
        </html>
        """
        
        # Plain text alternative
        text = f"""
AI Study Assistant - Login Verification

Your one-time password (OTP) is: {otp}

This code will expire in {OTP_EXPIRY_MINUTES} minutes.

If you didn't request this code, please ignore this email.

© 2025 AI Study Assistant
        """
        
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Send via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"\n{'='*60}")
        print(f"✅ EMAIL SENT SUCCESSFULLY!")
        print(f"📧 To: {email}")
        print(f"🔐 OTP: {otp}")
        print(f"{'='*60}\n")
        
        return True
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ EMAIL FAILED!")
        print(f"📧 To: {email}")
        print(f"🔐 OTP (use this for testing): {otp}")
        print(f"❌ Error: {str(e)}")
        print(f"{'='*60}\n")
        # Still return True to allow console-based testing
        return True
