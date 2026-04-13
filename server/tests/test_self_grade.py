"""Self-grade queue builder (no MongoDB server)."""
from bson import ObjectId

from src.services import build_self_grade_initial_queue, update_user_progress


class _Find:
    def __init__(self, items):
        self._items = list(items)

    def find(self, query):
        deck_id = query.get("deck_id")
        if deck_id is not None:
            return iter([x for x in self._items if x.get("deck_id") == deck_id])
        return iter(list(self._items))


def test_build_self_grade_empty_deck():
    db = type("DB", (), {})()
    db.flashcards = _Find([])
    cards, meta = build_self_grade_initial_queue(db, "d1")
    assert cards == []
    assert meta["counts"]["total"] == 0


def test_build_self_grade_returns_all_cards():
    c1 = {"_id": ObjectId(), "deck_id": "d1", "front": {}, "back": {}}
    c2 = {"_id": ObjectId(), "deck_id": "d1", "front": {}, "back": {}}
    db = type("DB", (), {})()
    db.flashcards = _Find([c1, c2])
    cards, meta = build_self_grade_initial_queue(db, "d1")
    assert len(cards) == 2
    assert {c["_id"] for c in cards} == {c1["_id"], c2["_id"]}
    assert meta["strategy"] == "self_grade"
    assert meta["counts"]["total"] == 2


def test_update_user_progress_unsure_grade3():
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
    update_user_progress(db, "u1", "c1", "d1", True, 3)
    p = stored[("u1", "c1")]
    assert p["total_reviews"] == 1
    assert p["correct_count"] == 1
