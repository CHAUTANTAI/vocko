"""Simple Flashcard queue + per-card stats (no SM-2)."""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any


def build_simple_queue(db: Any, deck_id: str) -> list[str]:
    """Shuffle all card ids in a simple deck."""
    cards = list(db.simple_cards.find({"deck_id": deck_id}, {"_id": 1}))
    ids = [str(c["_id"]) for c in cards]
    random.shuffle(ids)
    return ids


def apply_grade_to_queue(queue: list[str], card_id: str, remembered: bool) -> list[str]:
    """
    Remembered: drop front card.
    Forgot: move front card to end.
    Raises ValueError if queue empty or card_id mismatch.
    """
    if not queue:
        raise ValueError("empty queue")
    if queue[0] != card_id:
        raise ValueError("card mismatch")
    rest = queue[1:]
    if remembered:
        return rest
    return rest + [card_id]


def upsert_simple_card_stat(
    db: Any,
    *,
    user_id: str,
    card_id: str,
    deck_id: str,
    remembered: bool,
) -> None:
    now = datetime.utcnow()
    result = "remembered" if remembered else "forgot"
    if remembered:
        inc = {"remember_count": 1}
        on_insert = {"forget_count": 0}
    else:
        inc = {"forget_count": 1}
        on_insert = {"remember_count": 0}
    db.simple_card_stats.update_one(
        {"user_id": user_id, "card_id": card_id},
        {
            "$inc": inc,
            "$set": {
                "deck_id": deck_id,
                "last_result": result,
                "last_reviewed_at": now,
            },
            "$setOnInsert": {
                "user_id": user_id,
                "card_id": card_id,
                **on_insert,
            },
        },
        upsert=True,
    )


def serialize_simple_card(card: dict) -> dict:
    return {
        "_id": str(card["_id"]),
        "deck_id": card.get("deck_id") or "",
        "front": card.get("front") or "",
        "back": card.get("back") or "",
        "order_index": int(card.get("order_index") or 0),
        "created_at": card.get("created_at"),
        "updated_at": card.get("updated_at"),
    }


def serialize_simple_deck(deck: dict) -> dict:
    return {
        "_id": str(deck["_id"]),
        "owner_id": deck.get("owner_id") or "",
        "title": deck.get("title") or "",
        "description": deck.get("description") or "",
        "card_count": int(deck.get("card_count") or 0),
        "created_at": deck.get("created_at"),
        "updated_at": deck.get("updated_at"),
    }


def session_summary_preview(session: dict) -> dict:
    events = session.get("events") or []
    forgot_events = sum(1 for e in events if e.get("result") == "forgot")
    remembered = sum(1 for e in events if e.get("result") == "remembered")
    return {
        "total_cards": int(session.get("initial_count") or 0),
        "remembered": remembered,
        "forgot_events": forgot_events,
        "remaining": len(session.get("queue") or []),
    }
