import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = "ai_study_assistant"

# Create async MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]

# Collections
users_collection = database["users"]
otp_collection = database["otps"]
summaries_collection = database["summaries"]
quizzes_collection = database["quizzes"]

async def create_indexes():
    """Create database indexes for performance and auto-deletion"""
    try:
        # User indexes
        await users_collection.create_index("email", unique=True)
        await users_collection.create_index("user_id", unique=True)
        
        # OTP indexes with TTL (Time To Live) - auto-delete expired OTPs
        await otp_collection.create_index("expires_at", expireAfterSeconds=0)
        await otp_collection.create_index("email")
        
        # Summary indexes
        await summaries_collection.create_index([("user_id", 1), ("created_at", -1)])
        
        # Quiz indexes
        await quizzes_collection.create_index([("user_id", 1), ("created_at", -1)])
        
        print("✅ Database indexes created successfully")
    except Exception as e:
        print(f"⚠️  Index creation warning: {e}")

async def close_db_connection():
    """Close database connection"""
    client.close()
    print("📤 Database connection closed")

# Test connection
async def test_connection():
    """Test MongoDB connection"""
    try:
        await client.admin.command('ping')
        print("✅ MongoDB connected successfully")
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False
