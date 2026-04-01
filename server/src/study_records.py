"""Normalized study records + canonical match_type (roadmap Phase 1)."""

import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId


def canonical_match_type(legacy: str, *, correct: bool, llm_used: bool) -> str:
    """
    Map internal grading labels to stored enum:
    exact | typo | synonym | wrong_meaning | none
    (grammar_error reserved for future)
    """
    if legacy == "exact":
        return "exact"
    if legacy == "typo_one":
        return "typo"
    if legacy == "llm":
        return "synonym"
    if legacy == "none":
        if llm_used and not correct:
            return "wrong_meaning"
        return "none"
    return "none"


def insert_study_record(
    db: Any,
    *,
    user_id: str,
    session_id: ObjectId,
    card_id: str,
    user_answer: str,
    result: str,
    grade: int,
    match_type_canonical: str,
    time_ms: int,
    is_first_attempt: bool,
) -> ObjectId:
    doc = {
        "user_id": user_id,
        "session_id": session_id,
        "card_id": ObjectId(card_id) if isinstance(card_id, str) else card_id,
        "user_answer": user_answer,
        "result": result,
        "grade": grade,
        "match_type": match_type_canonical,
        "is_first_attempt": is_first_attempt,
        "time_ms": time_ms,
        "created_at": datetime.datetime.utcnow(),
    }
    ins = db.study_records.insert_one(doc)
    return ins.inserted_id


def count_session_attempts_for_card(
    db: Any,
    *,
    session_id: ObjectId,
    card_id: str,
    user_id: str,
) -> int:
    try:
        cid = ObjectId(card_id)
    except InvalidId:
        return 0
    return db.study_records.count_documents(
        {"session_id": session_id, "card_id": cid, "user_id": user_id}
    )
