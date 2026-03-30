import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "vocko")

client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
db = client[DB_NAME]

def get_db():
    return db
