"""Unit tests for SRS helpers (no MongoDB required)."""
from bson import ObjectId

from src.services import build_learning_queue, update_user_progress


class _Find:
    def __init__(self, items):
        self._items = list(items)

    def find(self, query):
        deck_id = query.get("deck_id")
        if deck_id is not None:
            return iter([x for x in self._items if x.get("deck_id") == deck_id])
        return iter(list(self._items))


def test_build_learning_queue_empty_deck():
    db = type("DB", (), {})()
    db.flashcards = _Find([])
    db.user_progress = _Find([])
    assert build_learning_queue(db, "deck1", "user1", "learn", 5) == []


def test_build_learning_queue_new_cards():
    c1 = {"_id": ObjectId(), "deck_id": "d1", "front": {}, "back": {}}
    c1["_id"] = c1["_id"]
    db = type("DB", (), {})()
    db.flashcards = _Find([c1])
    db.user_progress = _Find([])

    out = build_learning_queue(db, "d1", "u1", "learn", 10)
    assert len(out) == 1
    assert out[0]["_id"] == c1["_id"]


def test_update_user_progress_upsert():
    stored = {}

    class Progress:
        def find_one(self, q):
            return stored.get((q["user_id"], q["card_id"]))

        def update_one(self, q, upd, upsert=False):
            doc = stored.get((q["user_id"], q["card_id"]), {})
            setv = upd["$set"]
            ins = upd.get("$setOnInsert", {})
            if not doc and upsert:
                doc = {**ins, **setv}
            else:
                doc = {**doc, **setv}
            stored[(q["user_id"], q["card_id"])] = doc
            return type("R", (), {"modified_count": 1, "upserted_id": None})()

    db = type("DB", (), {})()
    db.user_progress = Progress()
    update_user_progress(db, "u1", "c1", "d1", True, 5)
    p = stored[("u1", "c1")]
    assert p["total_reviews"] == 1
    assert p["correct_count"] == 1
    assert p["repetition"] >= 0
