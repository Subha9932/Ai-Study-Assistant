import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

print(f"Account SID: {TWILIO_ACCOUNT_SID}")
print(f"Auth Token: {TWILIO_AUTH_TOKEN[:10]}...")
print(f"From Number: {TWILIO_PHONE_NUMBER}")

try:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    message = client.messages.create(
        body="Test message from AI Study Assistant! Your OTP system is working! 🎉",
        from_=TWILIO_PHONE_NUMBER,
        to="+919932876978"  # Your Indian phone number
    )
    
    print(f"\n✅ SUCCESS!")
    print(f"Message SID: {message.sid}")
    print(f"Status: {message.status}")
    
except Exception as e:
    print(f"\n❌ FAILED: {str(e)}")
