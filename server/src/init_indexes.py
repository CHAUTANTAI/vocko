"""MongoDB indexes + light migrations.

Callable from FastAPI startup (Render deploy uses env vars — no local .env needed)
or as a CLI: `python src/init_indexes.py` from `server/`.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger("vocko.init_indexes")


def mask_uri(uri: str) -> str:
    return re.sub(r"(//[^:]+:)[^@]+(@)", r"\1***\2", uri)


def seed_tags(database: Any) -> None:
    defaults = [
        ("Phrasal verb", "phrasal-verb"),
        ("Collocation", "collocation"),
        ("Present tense", "tense-present"),
        ("Business", "business"),
        ("Formal", "formal"),
        ("Confusable", "confusable"),
    ]
    for name, slug in defaults:
        if not database.tags.find_one({"slug": slug}):
            database.tags.insert_one({"name": name, "slug": slug})


def migrate_flashcard_defaults(database: Any) -> None:
    database.flashcards.update_many(
        {"card_type": {"$exists": False}},
        {"$set": {"card_type": "vocab", "language": "en"}},
    )


def migrate_unset_flashcard_source_id(database: Any) -> None:
    """Deck title is the content source; drop legacy per-card source_id."""
    database.flashcards.update_many({"source_id": {"$exists": True}}, {"$unset": {"source_id": ""}})


def create_indexes(database: Any) -> None:
    """Idempotent indexes + migrations. Safe to run on every app start / deploy."""
    database.users.create_index("email", unique=True)
    database.decks.create_index([("owner_id", 1)])
    database.decks.create_index([("title", "text"), ("description", "text")])
    database.flashcards.create_index([("deck_id", 1), ("order_index", 1)])
    database.flashcards.create_index([("deck_id", 1), ("card_type", 1)])
    database.flashcards.create_index([("front.content", "text")])
    database.tags.create_index("slug", unique=True)
    database.card_tags.create_index([("card_id", 1), ("tag_id", 1)], unique=True)
    database.card_tags.create_index([("tag_id", 1)])
    database.study_records.create_index([("user_id", 1), ("created_at", -1)])
    database.study_records.create_index([("session_id", 1)])
    database.study_records.create_index([("card_id", 1), ("user_id", 1)])
    database.user_progress.create_index([("user_id", 1), ("next_due_at", 1)])
    database.user_progress.create_index([("user_id", 1), ("deck_id", 1)])
    database.learning_sessions.create_index([("user_id", 1), ("started_at", -1)])
    database.learning_sessions.create_index([("user_id", 1), ("deck_id", 1), ("started_at", -1)])
    # Simple Flashcard module (separate from vocab decks)
    database.simple_decks.create_index([("owner_id", 1), ("created_at", -1)])
    database.simple_decks.create_index([("title", "text"), ("description", "text")])
    database.simple_cards.create_index([("deck_id", 1), ("order_index", 1)])
    database.simple_cards.create_index([("front", "text"), ("back", "text")])
    database.simple_card_stats.create_index([("user_id", 1), ("card_id", 1)], unique=True)
    database.simple_card_stats.create_index([("user_id", 1), ("deck_id", 1)])
    database.simple_card_stats.create_index([("user_id", 1), ("forget_count", -1)])
    database.simple_learning_sessions.create_index([("user_id", 1), ("started_at", -1)])
    database.simple_learning_sessions.create_index([("user_id", 1), ("deck_id", 1), ("started_at", -1)])
    migrate_flashcard_defaults(database)
    migrate_unset_flashcard_source_id(database)
    seed_tags(database)
    logger.info("Indexes created.")
    print("Indexes created.")


def main() -> None:
    from pymongo.mongo_client import MongoClient
    from pymongo.server_api import ServerApi

    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB", "vocko")
    print(f"[DEBUG] Using MONGO_URI: {mask_uri(mongo_uri)}")
    client = MongoClient(mongo_uri, server_api=ServerApi("1"))
    database = client[db_name]
    try:
        client.admin.command("ping")
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)
        raise SystemExit(1) from e
    create_indexes(database)


if __name__ == "__main__":
    main()
