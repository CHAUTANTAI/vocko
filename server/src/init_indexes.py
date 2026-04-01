import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv


load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "vocko")

# Log MONGO_URI (mask password for debug)
def mask_uri(uri):
    import re
    return re.sub(r'(//[^:]+:)[^@]+(@)', r'\1***\2', uri)
print(f"[DEBUG] Using MONGO_URI: {mask_uri(MONGO_URI)}")

client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
db = client[DB_NAME]

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
    exit(1)

def seed_tags():
    defaults = [
        ("Phrasal verb", "phrasal-verb"),
        ("Collocation", "collocation"),
        ("Present tense", "tense-present"),
        ("Business", "business"),
        ("Formal", "formal"),
        ("Confusable", "confusable"),
    ]
    for name, slug in defaults:
        if not db.tags.find_one({"slug": slug}):
            db.tags.insert_one({"name": name, "slug": slug})


def migrate_flashcard_defaults():
    db.flashcards.update_many(
        {"card_type": {"$exists": False}},
        {"$set": {"card_type": "vocab", "language": "en"}},
    )


def migrate_unset_flashcard_source_id():
    """Deck title is the content source; drop legacy per-card source_id."""
    db.flashcards.update_many({"source_id": {"$exists": True}}, {"$unset": {"source_id": ""}})


def create_indexes():
    db.users.create_index("email", unique=True)
    db.decks.create_index([("owner_id", 1)])
    db.decks.create_index([("title", "text"), ("description", "text")])
    db.flashcards.create_index([("deck_id", 1), ("order_index", 1)])
    db.flashcards.create_index([("deck_id", 1), ("card_type", 1)])
    db.flashcards.create_index([("front.content", "text")])
    db.tags.create_index("slug", unique=True)
    db.card_tags.create_index([("card_id", 1), ("tag_id", 1)], unique=True)
    db.card_tags.create_index([("tag_id", 1)])
    db.study_records.create_index([("user_id", 1), ("created_at", -1)])
    db.study_records.create_index([("session_id", 1)])
    db.study_records.create_index([("card_id", 1), ("user_id", 1)])
    db.user_progress.create_index([("user_id", 1), ("next_due_at", 1)])
    db.user_progress.create_index([("user_id", 1), ("deck_id", 1)])
    db.learning_sessions.create_index([("user_id", 1), ("started_at", -1)])
    migrate_flashcard_defaults()
    migrate_unset_flashcard_source_id()
    seed_tags()
    print("Indexes created.")

if __name__ == "__main__":
    create_indexes()
