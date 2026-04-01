"""SRS (SM-2 style) and learning queue helpers."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any, List

from .learning_config import (
    DIFFICULTY_EASY_MIN,
    DIFFICULTY_MEDIUM_MIN,
    EASY_POOL_MIN_EASE,
    RECENT_GRADES_MAX,
    SMART_QUEUE_WEIGHTS,
    WEAK_TAG_AGG_LIMIT,
)

INITIAL_EASE = 2.5


def difficulty_bucket_from_avg(avg: float | None) -> str:
    if avg is None:
        return "medium"
    if avg >= DIFFICULTY_EASY_MIN:
        return "easy"
    if avg >= DIFFICULTY_MEDIUM_MIN:
        return "medium"
    return "hard"


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

    if grade is not None:
        grade_val = max(0, min(5, int(grade)))
    else:
        grade_val = 0 if not correct else 4
    recent = list(existing.get("recent_grades", [])) if existing else []
    recent.append(grade_val)
    recent = recent[-RECENT_GRADES_MAX:]
    avg_last = sum(recent) / len(recent) if recent else None
    diff_bucket = difficulty_bucket_from_avg(avg_last)

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
                "recent_grades": recent,
                "avg_last_5_grades": avg_last,
                "difficulty_bucket": diff_bucket,
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
    cards, _ = build_learning_queue_meta(db, deck_id, user_id, mode, queue_size)
    return cards


def build_learning_queue_meta(
    db: Any,
    deck_id: str,
    user_id: str,
    mode: str,
    queue_size: int,
) -> tuple[List[Any], dict]:
    """Classic queue builder + queue_meta for API transparency."""
    empty_meta: dict = {
        "strategy": "classic",
        "mode": mode,
        "counts": {"new": 0, "due": 0, "fill": 0, "total": 0},
    }
    all_cards = list(db.flashcards.find({"deck_id": deck_id}))
    if not all_cards:
        return [], empty_meta

    now = datetime.utcnow()
    prog = {
        p["card_id"]: p
        for p in db.user_progress.find({"user_id": user_id, "deck_id": deck_id})
    }

    counts = {"new": 0, "due": 0, "fill": 0}

    if mode == "review":
        due = []
        for c in all_cards:
            cid = str(c["_id"])
            p = prog.get(cid)
            if p and p.get("next_due_at") and p["next_due_at"] <= now:
                due.append(c)
        due.sort(key=lambda c: prog[str(c["_id"])]["next_due_at"])
        result = due[:queue_size]
        counts["due"] = len(result)
        meta = {
            "strategy": "classic",
            "mode": "review",
            "counts": {**counts, "total": len(result)},
            "note": "Due cards only, oldest due first.",
        }
        return result, meta

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
    for c in new_cards:
        cid = str(c["_id"])
        if cid not in seen:
            seen.add(cid)
            ordered.append(c)
            counts["new"] += 1
    for c in due_cards:
        cid = str(c["_id"])
        if cid not in seen:
            seen.add(cid)
            ordered.append(c)
            counts["due"] += 1
    if len(ordered) < queue_size:
        rest = [c for c in all_cards if str(c["_id"]) not in seen]
        random.shuffle(rest)
        for c in rest:
            if len(ordered) >= queue_size:
                break
            ordered.append(c)
            counts["fill"] += 1
    result = ordered[:queue_size]
    meta = {
        "strategy": "classic",
        "mode": "learn",
        "counts": {**counts, "total": len(result)},
        "note": "New cards first (shuffled), then due (by due date), then fill from rest.",
    }
    return result, meta


def aggregate_weak_tag_rows(
    db: Any,
    user_id: str,
    deck_id: str,
    limit: int = WEAK_TAG_AGG_LIMIT,
) -> List[dict]:
    """Incorrect counts per tag in this deck (Phase 3 weak-by-tag)."""
    all_cards = list(db.flashcards.find({"deck_id": deck_id}, {"_id": 1}))
    if not all_cards:
        return []
    card_ids = [c["_id"] for c in all_cards]
    pipeline = [
        {
            "$match": {
                "user_id": user_id,
                "result": "incorrect",
                "card_id": {"$in": card_ids},
            }
        },
        {
            "$lookup": {
                "from": "card_tags",
                "localField": "card_id",
                "foreignField": "card_id",
                "as": "ct",
            }
        },
        {"$unwind": "$ct"},
        {"$group": {"_id": "$ct.tag_id", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$limit": limit},
    ]
    return [{"tag_id": r["_id"], "incorrect_count": r["n"]} for r in db.study_records.aggregate(pipeline)]


def aggregate_weak_tag_ids(
    db: Any,
    user_id: str,
    deck_id: str,
    limit: int = WEAK_TAG_AGG_LIMIT,
) -> List[Any]:
    return [row["tag_id"] for row in aggregate_weak_tag_rows(db, user_id, deck_id, limit)]


def _card_tags_map(db: Any, card_ids: List[Any]) -> dict:
    out: dict = {}
    if not card_ids:
        return out
    for row in db.card_tags.find({"card_id": {"$in": card_ids}}):
        cid = row["card_id"]
        out.setdefault(cid, []).append(row["tag_id"])
    return out


def _is_due_srs(card: dict, prog: dict, now: datetime) -> bool:
    cid = str(card["_id"])
    p = prog.get(cid)
    if not p:
        return False
    nd = p.get("next_due_at")
    if nd is None:
        return True
    return nd <= now


def _is_new_card(card: dict, prog: dict) -> bool:
    cid = str(card["_id"])
    p = prog.get(cid)
    if not p:
        return True
    return int(p.get("total_reviews", 0)) == 0


def _weak_for_smart(
    card: dict,
    prog: dict,
    ct_map: dict,
    weak_tag_ids: set,
) -> bool:
    p = prog.get(str(card["_id"])) or {}
    tags = ct_map.get(card["_id"], [])
    has_wt = bool(weak_tag_ids) and any(t in weak_tag_ids for t in tags)
    if has_wt:
        return True
    return p.get("difficulty_bucket") == "hard"


def _review_priority(card: dict, prog: dict, ct_map: dict, weak_tag_ids: set) -> int:
    p = prog.get(str(card["_id"])) or {}
    tags = ct_map.get(card["_id"], [])
    has_wt = bool(weak_tag_ids) and any(t in weak_tag_ids for t in tags)
    if has_wt:
        return 0
    bucket = p.get("difficulty_bucket") or "medium"
    if bucket == "hard":
        return 1
    if bucket == "medium":
        return 2
    return 3


def build_learning_queue_smart(
    db: Any,
    deck_id: str,
    user_id: str,
    mode: str,
    queue_size: int,
    *,
    weights: tuple[float, float, float] | None = None,
) -> tuple[List[Any], dict]:
    """
    Smart queue + queue_meta. Learn: target weak/new/easy ratio, then weighted round-robin
    among pools that still have cards, then fill. Review: due only, priority-sorted (not 70/20/10).
    """
    w = weights or SMART_QUEUE_WEIGHTS
    w_weak, w_new, w_easy = w[0], w[1], w[2]
    wsum = w_weak + w_new + w_easy
    if wsum <= 0:
        w_weak, w_new, w_easy = SMART_QUEUE_WEIGHTS
        wsum = sum(SMART_QUEUE_WEIGHTS)
    w_weak, w_new, w_easy = w_weak / wsum, w_new / wsum, w_easy / wsum

    all_cards = list(db.flashcards.find({"deck_id": deck_id}))
    if not all_cards:
        return [], {
            "strategy": "smart",
            "mode": mode,
            "counts": {"weak": 0, "new": 0, "easy": 0, "fill": 0, "total": 0},
        }

    now = datetime.utcnow()
    prog = {
        p["card_id"]: p
        for p in db.user_progress.find({"user_id": user_id, "deck_id": deck_id})
    }

    weak_tag_ids = set(aggregate_weak_tag_ids(db, user_id, deck_id))
    ct_map = _card_tags_map(db, [c["_id"] for c in all_cards])

    if mode == "review":
        due = [c for c in all_cards if _is_due_srs(c, prog, now)]

        def sort_key(c: dict) -> tuple:
            pri = _review_priority(c, prog, ct_map, weak_tag_ids)
            nd = (prog.get(str(c["_id"])) or {}).get("next_due_at") or now
            return (pri, nd)

        due.sort(key=sort_key)
        result = due[:queue_size]
        priority_high = sum(
            1 for c in result if _review_priority(c, prog, ct_map, weak_tag_ids) <= 1
        )
        meta = {
            "strategy": "smart",
            "mode": "review",
            "counts": {
                "due": len(result),
                "priority_high": priority_high,
                "due_other": len(result) - priority_high,
                "weak": 0,
                "new": 0,
                "easy": 0,
                "fill": 0,
                "total": len(result),
            },
            "note": (
                "Review: only due cards. Order = weak tags / hard bucket first, "
                "then medium/easy, then by due date. (Not a 70/20/10 mix.)"
            ),
        }
        return result, meta

    weak_pool: List[Any] = []
    easy_pool: List[Any] = []
    new_pool: List[Any] = []

    for c in all_cards:
        if _is_new_card(c, prog):
            new_pool.append(c)
            continue
        if not _is_due_srs(c, prog, now):
            continue
        p = prog.get(str(c["_id"])) or {}
        ease = float(p.get("ease_factor", INITIAL_EASE))
        if _weak_for_smart(c, prog, ct_map, weak_tag_ids):
            weak_pool.append(c)
        if p.get("difficulty_bucket") == "easy" and ease >= EASY_POOL_MIN_EASE:
            easy_pool.append(c)

    if not weak_pool:
        weak_pool = [c for c in all_cards if _is_due_srs(c, prog, now)]

    random.shuffle(new_pool)
    random.shuffle(weak_pool)
    random.shuffle(easy_pool)

    n_w = max(0, int(round(queue_size * w_weak)))
    n_n = max(0, int(round(queue_size * w_new)))
    n_e = max(0, queue_size - n_w - n_n)

    seen: set[str] = set()
    ordered: List[Any] = []
    meta_counts = {"weak": 0, "new": 0, "easy": 0, "fill": 0}

    def take_n(pool: List[Any], target: int, label: str) -> None:
        taken = 0
        for c in pool:
            if len(ordered) >= queue_size or taken >= target:
                break
            cid = str(c["_id"])
            if cid in seen:
                continue
            seen.add(cid)
            ordered.append(c)
            meta_counts[label] += 1
            taken += 1

    take_n(weak_pool, n_w, "weak")
    take_n(new_pool, n_n, "new")
    take_n(easy_pool, n_e, "easy")

    # Reallocate remaining slots: round-robin weak → new → easy while any pool has unseen cards.
    pools_rr: List[tuple[str, List[Any]]] = [
        ("weak", weak_pool),
        ("new", new_pool),
        ("easy", easy_pool),
    ]
    while len(ordered) < queue_size:
        progressed = False
        for label, pool in pools_rr:
            if len(ordered) >= queue_size:
                break
            for c in pool:
                cid = str(c["_id"])
                if cid in seen:
                    continue
                seen.add(cid)
                ordered.append(c)
                meta_counts[label] += 1
                progressed = True
                break
        if not progressed:
            break

    if len(ordered) < queue_size:
        rest = [c for c in all_cards if str(c["_id"]) not in seen]
        random.shuffle(rest)
        for c in rest:
            if len(ordered) >= queue_size:
                break
            ordered.append(c)
            meta_counts["fill"] += 1

    result = ordered[:queue_size]
    meta = {
        "strategy": "smart",
        "mode": "learn",
        "counts": {**meta_counts, "total": len(result)},
        "weights": {"weak": w_weak, "new": w_new, "easy": w_easy},
        "note": (
            "Learn: target slots weak/new/easy from weights; extra slots use weak→new→easy "
            "round-robin, then random fill. Needs tags + incorrect history for strong weak signal."
        ),
    }
    return result, meta
