import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from .env
load_dotenv()

# Get Mongo URI from .env
MONGO_URI = os.getenv("MONGO_URI")

# Safety check (optional but good)
if not MONGO_URI:
    raise ValueError("MONGO_URI not found in environment variables")

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Database
db = client["smart_traffic_db"]

# Collections
traffic_collection = db["traffic_data"]
alerts_collection = db["alerts"]
signals_collection = db["traffic_signals"]

print("✅ Connected to MongoDB Atlas")