"""SRS (SM-2 style) and learning queue helpers."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any, List

INITIAL_EASE = 2.5


def _quality_from_answer(correct: bool, grade: int | None) -> int:
    if correct:
        if grade is not None:
            return max(3, min(5, grade))
        return 4
    return 0


def update_user_progress(
    db: Any,
    user_id: str,
    card_id: str,
    deck_id: str,
    correct: bool,
    grade: int | None,
) -> None:
    now = datetime.utcnow()
    quality = _quality_from_answer(correct, grade)
    q = {"user_id": user_id, "card_id": card_id}
    existing = db.user_progress.find_one(q)

    total = int(existing.get("total_reviews", 0)) if existing else 0
    correct_n = int(existing.get("correct_count", 0)) if existing else 0
    streak = int(existing.get("streak", 0)) if existing else 0
    ease = float(existing.get("ease_factor", INITIAL_EASE)) if existing else INITIAL_EASE
    rep = int(existing.get("repetition", 0)) if existing else 0
    interval = int(existing.get("interval_days", 0)) if existing else 0

    if quality < 3:
        new_rep = 0
        new_interval = 0
        next_due = now
        new_streak = 0
        ease = max(1.3, ease - 0.2)
    else:
        if rep == 0:
            new_interval = 1
        elif rep == 1:
            new_interval = 6
        else:
            new_interval = max(1, round(interval * ease))
        new_rep = rep + 1
        new_streak = streak + 1
        ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        ease = max(1.3, ease)
        next_due = now + timedelta(days=new_interval)

    db.user_progress.update_one(
        q,
        {
            "$set": {
                "user_id": user_id,
                "card_id": card_id,
                "deck_id": deck_id,
                "ease_factor": ease,
                "repetition": new_rep,
                "interval_days": new_interval,
                "next_due_at": next_due,
                "last_reviewed_at": now,
                "total_reviews": total + 1,
                "correct_count": correct_n + (1 if correct else 0),
                "streak": new_streak,
                "suspended": False,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


def build_learning_queue(
    db: Any,
    deck_id: str,
    user_id: str,
    mode: str,
    queue_size: int,
) -> List[Any]:
    all_cards = list(db.flashcards.find({"deck_id": deck_id}))
    if not all_cards:
        return []

    now = datetime.utcnow()
    prog = {
        p["card_id"]: p
        for p in db.user_progress.find({"user_id": user_id, "deck_id": deck_id})
    }

    if mode == "review":
        due = []
        for c in all_cards:
            cid = str(c["_id"])
            p = prog.get(cid)
            if p and p.get("next_due_at") and p["next_due_at"] <= now:
                due.append(c)
        due.sort(key=lambda c: prog[str(c["_id"])]["next_due_at"])
        return due[:queue_size]

    new_cards = [c for c in all_cards if str(c["_id"]) not in prog]
    due_cards = []
    for c in all_cards:
        cid = str(c["_id"])
        p = prog.get(cid)
        if p and p.get("next_due_at") and p["next_due_at"] <= now:
            due_cards.append(c)

    random.shuffle(new_cards)
    due_cards.sort(key=lambda c: prog[str(c["_id"])]["next_due_at"])
    seen: set[str] = set()
    ordered: List[Any] = []
    for c in new_cards + due_cards:
        cid = str(c["_id"])
        if cid not in seen:
            seen.add(cid)
            ordered.append(c)
    if len(ordered) < queue_size:
        rest = [c for c in all_cards if str(c["_id"]) not in seen]
        random.shuffle(rest)
        for c in rest:
            if len(ordered) >= queue_size:
                break
            ordered.append(c)
    return ordered[:queue_size]
