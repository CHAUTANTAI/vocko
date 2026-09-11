"""Unit tests for Simple Flashcard helpers (no MongoDB)."""
from datetime import datetime

from src.simple_services import (
    apply_grade_to_queue,
    build_quick_5_queue,
    session_summary_preview,
    upsert_simple_card_stat,
    weakness_score,
)


def test_apply_grade_remembered_removes_front():
    q = apply_grade_to_queue(["a", "b", "c"], "a", True)
    assert q == ["b", "c"]


def test_apply_grade_forgot_moves_to_end():
    q = apply_grade_to_queue(["a", "b", "c"], "a", False)
    assert q == ["b", "c", "a"]


def test_apply_grade_mismatch_raises():
    try:
        apply_grade_to_queue(["a", "b"], "x", True)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "mismatch" in str(e)


def test_apply_grade_empty_raises():
    try:
        apply_grade_to_queue([], "a", True)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "empty" in str(e)


def test_forgot_until_remembered_clears_queue():
    q = ["a", "b"]
    q = apply_grade_to_queue(q, "a", False)  # b, a
    assert q == ["b", "a"]
    q = apply_grade_to_queue(q, "b", True)  # a
    assert q == ["a"]
    q = apply_grade_to_queue(q, "a", True)
    assert q == []


def test_session_summary_preview():
    s = {
        "initial_count": 3,
        "queue": ["x"],
        "events": [
            {"result": "forgot"},
            {"result": "remembered"},
            {"result": "forgot"},
        ],
    }
    p = session_summary_preview(s)
    assert p["total_cards"] == 3
    assert p["remembered"] == 1
    assert p["forgot_events"] == 2
    assert p["remaining"] == 1


def test_upsert_simple_card_stat_forget_then_remember():
    stored = {}

    class Stats:
        def update_one(self, q, upd, upsert=False):
            key = (q["user_id"], q["card_id"])
            doc = stored.get(key, {})
            if not doc and upsert:
                doc = dict(upd.get("$setOnInsert") or {})
            for k, v in (upd.get("$inc") or {}).items():
                doc[k] = int(doc.get(k) or 0) + int(v)
            doc.update(upd.get("$set") or {})
            stored[key] = doc
            return type("R", (), {})()

    db = type("DB", (), {})()
    db.simple_card_stats = Stats()
    upsert_simple_card_stat(
        db, user_id="u1", card_id="c1", deck_id="d1", remembered=False
    )
    upsert_simple_card_stat(
        db, user_id="u1", card_id="c1", deck_id="d1", remembered=False
    )
    upsert_simple_card_stat(
        db, user_id="u1", card_id="c1", deck_id="d1", remembered=True
    )
    doc = stored[("u1", "c1")]
    assert doc["forget_count"] == 2
    assert doc["remember_count"] == 1
    assert doc["last_result"] == "remembered"
    assert isinstance(doc["last_reviewed_at"], datetime)
    assert weakness_score(doc["forget_count"], doc["remember_count"]) == 1


def test_weakness_score():
    assert weakness_score(5, 1) == 4
    assert weakness_score(3, 0) == 3
    assert weakness_score(3, 3) == 0
    assert weakness_score(1, 4) == -3


def test_build_quick_5_queue_orders_by_net_forget():
    cards = [{"_id": "a"}, {"_id": "b"}, {"_id": "c"}, {"_id": "d"}]
    stats = [
        {"card_id": "a", "forget_count": 5, "remember_count": 1},  # 4
        {"card_id": "b", "forget_count": 3, "remember_count": 0},  # 3
        {"card_id": "c", "forget_count": 2, "remember_count": 2},  # 0 excluded
        {"card_id": "d", "forget_count": 1, "remember_count": 0},  # 1
    ]

    class CardsCol:
        def find(self, q, proj=None):
            return cards

    class StatsCol:
        def find(self, q, proj=None):
            return stats

    db = type("DB", (), {})()
    db.simple_cards = CardsCol()
    db.simple_card_stats = StatsCol()
    q = build_quick_5_queue(db, deck_id="d1", user_id="u1", limit=12)
    assert q == ["a", "b", "d"]
    q2 = build_quick_5_queue(db, deck_id="d1", user_id="u1", limit=2)
    assert q2 == ["a", "b"]
