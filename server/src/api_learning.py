import datetime
import os
import random

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from . import services
from .answer_match import typo_one_highlight
from .db import db
from .learning_ai import generate_explain, generate_hint, grade_answer
from .openrouter_client import http_status_for_openrouter_error
from .study_records import (
    canonical_match_type,
    count_session_attempts_for_card,
    insert_study_record,
)
from .utils import decode_token

router = APIRouter()

SELF_RATINGS = frozenset({"known", "unsure", "forgot"})


def _self_rating_to_progress(rating: str) -> tuple[bool, int, str]:
    """Returns (correct, grade, match_type_canonical) for SRS + study_records."""
    if rating == "known":
        return True, 5, "self_known"
    if rating == "unsure":
        return True, 3, "self_unsure"
    return False, 0, "self_forgot"


def get_current_user(request: Request):
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth.split()[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

class StartSessionRequest(BaseModel):
    deck_id: str
    mode: str = "learn"
    options: dict = {}

class AnswerRequest(BaseModel):
    card_id: str
    response: str
    time_ms: int = 0
    client_grade: int = None


class HintRequest(BaseModel):
    card_id: str


class ExplainRequest(BaseModel):
    card_id: str
    deck_id: str | None = None


class SelfGradeRequest(BaseModel):
    card_id: str
    rating: str
    time_ms: int = 0


class ContinueRoundRequest(BaseModel):
    scope: str


def _question_payload(card: dict, card_id: str, mode: str, *, include_back: bool = False) -> dict:
    stored = card.get("hint")
    has_stored = bool(stored and str(stored).strip())
    out = {
        "card_id": card_id,
        "front": card["front"],
        "question_type": mode,
        "has_stored_hint": has_stored,
        "card_type": card.get("card_type") or "vocab",
        "language": card.get("language") or "en",
    }
    pos = (card.get("part_of_speech") or "").strip()
    if pos:
        out["part_of_speech"] = pos
    if include_back:
        out["back"] = card.get("back") or {}
    return out

@router.post("/learning/sessions")
def start_session(req: StartSessionRequest, user=Depends(get_current_user)):
    deck = db.decks.find_one({"_id": ObjectId(req.deck_id), "owner_id": user["user_id"]})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    interaction_mode = str(req.options.get("interaction_mode") or "typed")
    if interaction_mode not in ("typed", "self_grade"):
        interaction_mode = "typed"

    if interaction_mode == "self_grade":
        cards, queue_meta = services.build_self_grade_initial_queue(db, req.deck_id)
    else:
        queue_size = int(req.options.get("queue_size", 30))
        use_smart = bool(req.options.get("smart_queue", False))
        weights = None
        w = req.options.get("smart_queue_weights")
        if isinstance(w, (list, tuple)) and len(w) == 3:
            try:
                weights = (float(w[0]), float(w[1]), float(w[2]))
            except (TypeError, ValueError):
                weights = None
        if use_smart:
            cards, queue_meta = services.build_learning_queue_smart(
                db,
                req.deck_id,
                user["user_id"],
                req.mode,
                queue_size,
                weights=weights,
            )
        else:
            cards, queue_meta = services.build_learning_queue_meta(
                db, req.deck_id, user["user_id"], req.mode, queue_size
            )
    if not cards:
        raise HTTPException(
            status_code=400,
            detail="No cards in queue for this deck/mode",
        )
    session: dict = {
        "user_id": user["user_id"],
        "deck_id": req.deck_id,
        "mode": req.mode,
        "started_at": datetime.datetime.utcnow(),
        "queue": [str(c["_id"]) for c in cards],
        "answers": [],
        "study_record_ids": [],
        "interaction_mode": interaction_mode,
    }
    if interaction_mode == "self_grade":
        session["ratings"] = {}
        session["last_round_ratings"] = {}
        session["round_index"] = 0
        session["initial_card_ids"] = [str(c["_id"]) for c in cards]
        session["pending_round_choice"] = False
    result = db.learning_sessions.insert_one(session)
    session_id = str(result.inserted_id)
    inc_back = interaction_mode == "self_grade"
    preloaded = [
        _question_payload(c, str(c["_id"]), req.mode, include_back=inc_back) for c in cards[:5]
    ]
    return {
        "session_id": session_id,
        "preloaded_questions": preloaded,
        "queue_meta": queue_meta,
        "interaction_mode": interaction_mode,
    }

@router.get("/learning/sessions/{session_id}/next")
def get_next_question(session_id: str, user=Depends(get_current_user)):
    try:
        sid = ObjectId(session_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Session not found")
    session = db.learning_sessions.find_one({"_id": sid, "user_id": user["user_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("interaction_mode") == "self_grade" and session.get("pending_round_choice"):
        lrr = session.get("last_round_ratings") or {}
        bd = {"known": 0, "unsure": 0, "forgot": 0}
        for r in lrr.values():
            if r in bd:
                bd[r] += 1
        return {
            "question": None,
            "interaction_mode": "self_grade",
            "pending_round_choice": True,
            "breakdown": bd,
            "round_index": int(session.get("round_index") or 0),
        }
    if not session["queue"]:
        return {"question": None, "interaction_mode": session.get("interaction_mode", "typed")}
    card_id = session["queue"][0]
    card = db.flashcards.find_one({"_id": ObjectId(card_id)})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    inc_back = session.get("interaction_mode") == "self_grade"
    out = {
        "question": _question_payload(card, card_id, session["mode"], include_back=inc_back),
    }
    if session.get("interaction_mode") == "self_grade":
        out["interaction_mode"] = "self_grade"
    return out


@router.post("/learning/sessions/{session_id}/hint")
def get_session_hint(session_id: str, req: HintRequest, user=Depends(get_current_user)):
    try:
        sid = ObjectId(session_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Session not found")
    session = db.learning_sessions.find_one({"_id": sid, "user_id": user["user_id"]})
    if not session or not session.get("queue"):
        raise HTTPException(status_code=404, detail="Session not found or finished")
    head = session["queue"][0]
    if head != req.card_id:
        raise HTTPException(
            status_code=400,
            detail="Hint is only available for the current card (queue head)",
        )
    try:
        cid = ObjectId(req.card_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Card not found")
    card = db.flashcards.find_one({"_id": cid})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if str(card.get("deck_id")) != str(session.get("deck_id")):
        raise HTTPException(status_code=400, detail="Card not in this session")

    stored = (card.get("hint") or "").strip()
    if stored:
        return {"hint": stored, "source": "stored"}

    if not os.getenv("OPENROUTER_API_KEY", "").strip():
        raise HTTPException(
            status_code=503,
            detail="AI hints require OPENROUTER_API_KEY on the server",
        )
    front_text = (card.get("front") or {}).get("content") or ""
    back_text = (card.get("back") or {}).get("content") or ""
    h, hint_err = generate_hint(front_text, back_text or None)
    if not h:
        msg = (hint_err or "Could not generate a hint").strip()
        if len(msg) > 500:
            msg = msg[:497] + "..."
        raise HTTPException(
            status_code=http_status_for_openrouter_error(msg, default_for_unknown=503),
            detail=msg,
        )
    db.flashcards.update_one({"_id": cid}, {"$set": {"hint": h}})
    return {"hint": h, "source": "ai"}

@router.post("/learning/sessions/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest, user=Depends(get_current_user)):
    session = db.learning_sessions.find_one({"_id": ObjectId(session_id), "user_id": user["user_id"]})
    if not session or not session["queue"]:
        raise HTTPException(status_code=404, detail="Session not found or finished")
    if session.get("interaction_mode") == "self_grade":
        raise HTTPException(
            status_code=400,
            detail="This session uses self-grade; call POST /learning/sessions/{id}/self-grade instead.",
        )
    # Lấy card đầu tiên trong queue
    card_id = session["queue"][0]
    if card_id != req.card_id:
        raise HTTPException(status_code=400, detail="Card mismatch")
    card = db.flashcards.find_one({"_id": ObjectId(card_id)})
    back_content = card["back"]["content"] or ""
    expected = back_content.strip().lower()
    user_ans = (req.response or "").strip().lower()
    exact = user_ans == expected
    match_type_legacy = "exact"
    note: str | None = None
    typo_h: dict | None = None
    llm_used = False
    if exact:
        correct = True
        grade = 5
        match_type_legacy = "exact"
    else:
        typo_h = typo_one_highlight(back_content, req.response or "")
        if typo_h is not None:
            correct = True
            grade = 5
            match_type_legacy = "typo_one"
        else:
            correct = False
            grade = 0
            match_type_legacy = "none"
            if os.getenv("OPENROUTER_API_KEY", "").strip():
                llm_used = True
                ok, llm_note = grade_answer(
                    (card.get("front") or {}).get("content") or "",
                    back_content,
                    req.response,
                )
                note = llm_note
                if ok:
                    correct = True
                    grade = 4
                    match_type_legacy = "llm"
                else:
                    match_type_legacy = "none"
            else:
                note = None

    match_type_canonical = canonical_match_type(
        match_type_legacy,
        correct=correct,
        llm_used=llm_used,
    )

    sid_oid = ObjectId(session_id)
    prior = count_session_attempts_for_card(
        db,
        session_id=sid_oid,
        card_id=card_id,
        user_id=user["user_id"],
    )
    is_first_attempt = prior == 0
    rec_id = insert_study_record(
        db,
        user_id=user["user_id"],
        session_id=sid_oid,
        card_id=card_id,
        user_answer=req.response or "",
        result="correct" if correct else "incorrect",
        grade=grade,
        match_type_canonical=match_type_canonical,
        time_ms=req.time_ms,
        is_first_attempt=is_first_attempt,
    )

    answer_event = {
        "card_id": card_id,
        "response": req.response,
        "result": "correct" if correct else "incorrect",
        "grade": grade,
        "match_type": match_type_canonical,
        "match_type_legacy": match_type_legacy,
        "note": note,
        "typo_highlight": typo_h,
        "time_ms": req.time_ms,
        "ts": datetime.datetime.utcnow(),
        "study_record_id": str(rec_id),
    }
    db.learning_sessions.update_one(
        {"_id": sid_oid},
        {
            "$push": {
                "answers": answer_event,
                "study_record_ids": rec_id,
            },
            "$pop": {"queue": -1},
        },
    )
    services.update_user_progress(
        db,
        user["user_id"],
        card_id,
        session["deck_id"],
        correct,
        grade,
    )
    sess_after = db.learning_sessions.find_one({"_id": sid_oid})
    ans_list = (sess_after or {}).get("answers") or []
    out: dict = {
        "result": answer_event["result"],
        "grade": grade,
        "match_type": match_type_canonical,
        "match_type_legacy": match_type_legacy,
        "session_answered": len(ans_list),
        "session_correct": sum(1 for x in ans_list if x.get("result") == "correct"),
    }
    if note:
        out["note"] = note
    if typo_h and match_type_canonical == "typo":
        out["typo_highlight"] = typo_h
    out["card_back"] = card.get("back") or {}
    fn = (card.get("note") or "").strip()
    if fn:
        out["flashcard_note"] = fn
    fe = (card.get("example") or "").strip()
    if fe:
        out["flashcard_example"] = fe
    return out


@router.post("/learning/sessions/{session_id}/self-grade")
def submit_self_grade(session_id: str, req: SelfGradeRequest, user=Depends(get_current_user)):
    try:
        sid_oid = ObjectId(session_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Session not found")
    session = db.learning_sessions.find_one({"_id": sid_oid, "user_id": user["user_id"]})
    if not session or not session.get("queue"):
        raise HTTPException(status_code=404, detail="Session not found or finished")
    if session.get("interaction_mode") != "self_grade":
        raise HTTPException(status_code=400, detail="Not a self-grade session")
    if session.get("pending_round_choice"):
        raise HTTPException(status_code=400, detail="Choose how to continue the round first")
    rating = (req.rating or "").strip().lower()
    if rating not in SELF_RATINGS:
        raise HTTPException(status_code=400, detail="rating must be one of: known, unsure, forgot")

    card_id = session["queue"][0]
    if card_id != req.card_id:
        raise HTTPException(status_code=400, detail="Card mismatch")
    card = db.flashcards.find_one({"_id": ObjectId(card_id)})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    correct, grade, match_type_canonical = _self_rating_to_progress(rating)
    prior = count_session_attempts_for_card(
        db,
        session_id=sid_oid,
        card_id=card_id,
        user_id=user["user_id"],
    )
    is_first_attempt = prior == 0
    rec_id = insert_study_record(
        db,
        user_id=user["user_id"],
        session_id=sid_oid,
        card_id=card_id,
        user_answer="",
        result="correct" if correct else "incorrect",
        grade=grade,
        match_type_canonical=match_type_canonical,
        time_ms=req.time_ms,
        is_first_attempt=is_first_attempt,
        grading_mode="self_grade",
        self_rating=rating,
    )

    answer_event = {
        "card_id": card_id,
        "response": "",
        "self_rating": rating,
        "grading_mode": "self_grade",
        "result": "correct" if correct else "incorrect",
        "grade": grade,
        "match_type": match_type_canonical,
        "match_type_legacy": rating,
        "note": None,
        "typo_highlight": None,
        "time_ms": req.time_ms,
        "ts": datetime.datetime.utcnow(),
        "study_record_id": str(rec_id),
    }
    db.learning_sessions.update_one(
        {"_id": sid_oid},
        {
            "$push": {
                "answers": answer_event,
                "study_record_ids": rec_id,
            },
            "$pop": {"queue": -1},
            "$set": {
                f"ratings.{card_id}": rating,
                f"last_round_ratings.{card_id}": rating,
            },
        },
    )
    services.update_user_progress(
        db,
        user["user_id"],
        card_id,
        session["deck_id"],
        correct,
        grade,
    )
    sess_after = db.learning_sessions.find_one({"_id": sid_oid})
    q_after = (sess_after or {}).get("queue") or []
    ans_list = (sess_after or {}).get("answers") or []
    round_complete = len(q_after) == 0
    extra: dict = {}
    if round_complete:
        db.learning_sessions.update_one(
            {"_id": sid_oid},
            {"$set": {"pending_round_choice": True}},
        )
        lrr = (sess_after or {}).get("last_round_ratings") or {}
        bd = {"known": 0, "unsure": 0, "forgot": 0}
        for r in lrr.values():
            if r in bd:
                bd[r] += 1
        extra = {
            "round_complete": True,
            "pending_round_choice": True,
            "breakdown": bd,
            "round_index": int((sess_after or {}).get("round_index") or 0),
        }

    out: dict = {
        "result": answer_event["result"],
        "grade": grade,
        "match_type": match_type_canonical,
        "session_answered": len(ans_list),
        "session_correct": sum(1 for x in ans_list if x.get("result") == "correct"),
        **extra,
    }
    out["card_back"] = card.get("back") or {}
    fn = (card.get("note") or "").strip()
    if fn:
        out["flashcard_note"] = fn
    fe = (card.get("example") or "").strip()
    if fe:
        out["flashcard_example"] = fe
    return out


@router.post("/learning/sessions/{session_id}/continue-round")
def continue_self_grade_round(session_id: str, req: ContinueRoundRequest, user=Depends(get_current_user)):
    try:
        sid_oid = ObjectId(session_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Session not found")
    session = db.learning_sessions.find_one({"_id": sid_oid, "user_id": user["user_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("interaction_mode") != "self_grade":
        raise HTTPException(status_code=400, detail="Not a self-grade session")
    if not session.get("pending_round_choice"):
        raise HTTPException(status_code=400, detail="No round break pending")
    scope = (req.scope or "").strip().lower()
    if scope not in ("weak", "all"):
        raise HTTPException(status_code=400, detail="scope must be weak or all")

    initial = list(session.get("initial_card_ids") or [])
    last_rr = dict(session.get("last_round_ratings") or {})
    if scope == "all":
        new_queue = list(initial)
        random.shuffle(new_queue)
    else:
        new_queue = [cid for cid, r in last_rr.items() if r in ("unsure", "forgot")]
        random.shuffle(new_queue)
        if not new_queue:
            raise HTTPException(
                status_code=400,
                detail="No cards rated unsure or forgot in this round. Try reviewing the full deck or finish the session.",
            )

    new_round = int(session.get("round_index") or 0) + 1
    db.learning_sessions.update_one(
        {"_id": sid_oid},
        {
            "$set": {
                "queue": new_queue,
                "pending_round_choice": False,
                "last_round_ratings": {},
                "round_index": new_round,
            },
        },
    )
    return {"ok": True, "queue_length": len(new_queue), "round_index": new_round}


@router.post("/learning/sessions/{session_id}/finish")
def finish_session(session_id: str, user=Depends(get_current_user)):
    session = db.learning_sessions.find_one({"_id": ObjectId(session_id), "user_id": user["user_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ended_at = datetime.datetime.utcnow()
    answers = session.get("answers") or []
    correct = sum(1 for a in answers if a["result"] == "correct")
    total = len(answers)
    accuracy = correct / total if total else 0
    summary: dict = {"questions": total, "correct": correct, "accuracy": accuracy}
    items: list[dict] = []
    is_self_grade = session.get("interaction_mode") == "self_grade"

    if is_self_grade:
        last_by_cid: dict[str, dict] = {}
        last_idx: dict[str, int] = {}
        for i, a in enumerate(answers):
            cid = a.get("card_id")
            if not cid:
                continue
            cs = str(cid)
            last_by_cid[cs] = a
            last_idx[cs] = i
        bd = {"known": 0, "unsure": 0, "forgot": 0}
        for a in last_by_cid.values():
            r = (str(a.get("self_rating") or "")).lower()
            if r in bd:
                bd[r] += 1
        summary["self_grade"] = {
            "cards": len(last_by_cid),
            "known": bd["known"],
            "unsure": bd["unsure"],
            "forgot": bd["forgot"],
        }
        for cid in sorted(last_by_cid.keys(), key=lambda c: last_idx[c]):
            a = last_by_cid[cid]
            try:
                oc = ObjectId(cid)
            except InvalidId:
                continue
            fc = db.flashcards.find_one({"_id": oc})
            items.append(
                {
                    "card_id": cid,
                    "front": (fc or {}).get("front") or {},
                    "back": (fc or {}).get("back") or {},
                    "result": a.get("result"),
                    "response": a.get("response"),
                    "match_type": a.get("match_type"),
                    "note": a.get("note"),
                    "typo_highlight": a.get("typo_highlight"),
                    "self_rating": a.get("self_rating"),
                    "grading_mode": a.get("grading_mode", "typed"),
                }
            )
    else:
        for a in answers:
            cid = a.get("card_id")
            if not cid:
                continue
            try:
                oc = ObjectId(cid)
            except InvalidId:
                continue
            fc = db.flashcards.find_one({"_id": oc})
            items.append(
                {
                    "card_id": cid,
                    "front": (fc or {}).get("front") or {},
                    "back": (fc or {}).get("back") or {},
                    "result": a.get("result"),
                    "response": a.get("response"),
                    "match_type": a.get("match_type"),
                    "note": a.get("note"),
                    "typo_highlight": a.get("typo_highlight"),
                    "self_rating": a.get("self_rating"),
                    "grading_mode": a.get("grading_mode", "typed"),
                }
            )

    db.learning_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"ended_at": ended_at, "summary": summary}},
    )
    return {
        "summary": summary,
        "items": items,
        "interaction_mode": session.get("interaction_mode", "typed"),
    }


@router.get("/learning/history")
def learning_history(
    deck_id: str | None = None,
    page: int = 1,
    page_size: int = 30,
    user=Depends(get_current_user),
):
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    skip = (page - 1) * page_size
    q: dict = {"user_id": user["user_id"]}
    if deck_id:
        try:
            ObjectId(deck_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid deck_id")
        deck = db.decks.find_one({"_id": ObjectId(deck_id), "owner_id": user["user_id"]})
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        q["deck_id"] = deck_id
    total = db.learning_sessions.count_documents(q)
    cur = (
        db.learning_sessions.find(q)
        .sort("started_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    rows: list[dict] = []
    for s in cur:
        did = s.get("deck_id")
        title = ""
        if did:
            d = db.decks.find_one({"_id": ObjectId(did), "owner_id": user["user_id"]})
            if d:
                title = str(d.get("title") or "")
        sa = s.get("started_at")
        ea = s.get("ended_at")
        rows.append(
            {
                "session_id": str(s["_id"]),
                "deck_id": did,
                "deck_title": title,
                "started_at": (sa.isoformat() + "Z") if sa and hasattr(sa, "isoformat") else None,
                "ended_at": (ea.isoformat() + "Z") if ea and hasattr(ea, "isoformat") else None,
                "interaction_mode": s.get("interaction_mode", "typed"),
                "summary": s.get("summary"),
                "queue_meta": s.get("queue_meta"),
            }
        )
    return {"sessions": rows, "page": page, "page_size": page_size, "total": total}


@router.get("/learning/sessions/{session_id}/detail")
def get_learning_session_detail(session_id: str, user=Depends(get_current_user)):
    try:
        sid = ObjectId(session_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Session not found")
    s = db.learning_sessions.find_one({"_id": sid, "user_id": user["user_id"]})
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    s["_id"] = str(s["_id"])
    for k in ("study_record_ids",):
        if k in s and isinstance(s[k], list):
            s[k] = [str(x) if not isinstance(x, str) else x for x in s[k]]
    return {"session": s}


@router.get("/learning/weak-tags")
def get_weak_tags(deck_id: str, user=Depends(get_current_user)):
    try:
        did = ObjectId(deck_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Deck not found")
    deck = db.decks.find_one({"_id": did, "owner_id": user["user_id"]})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    rows = services.aggregate_weak_tag_rows(db, user["user_id"], deck_id)
    out: list[dict] = []
    for row in rows:
        t = db.tags.find_one({"_id": row["tag_id"]})
        if t:
            out.append(
                {
                    "tag_id": str(row["tag_id"]),
                    "name": t.get("name"),
                    "slug": t.get("slug"),
                    "incorrect_count": row["incorrect_count"],
                }
            )
    return {"tags": out}


@router.get("/learning/stats/summary")
def learning_stats_summary(deck_id: str | None = None, user=Depends(get_current_user)):
    uid = user["user_id"]
    base_match: dict = {"user_id": uid}
    if deck_id:
        try:
            did = ObjectId(deck_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid deck_id")
        deck = db.decks.find_one({"_id": did, "owner_id": uid})
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        card_ids = [c["_id"] for c in db.flashcards.find({"deck_id": deck_id}, {"_id": 1})]
        base_match["card_id"] = {"$in": card_ids}
    total = db.study_records.count_documents(base_match)
    correct = db.study_records.count_documents({**base_match, "result": "correct"})
    accuracy = (correct / total) if total else None
    streaks = [int(p.get("streak", 0)) for p in db.user_progress.find({"user_id": uid})]
    streak_max = max(streaks) if streaks else 0
    weak_topics: list[dict] = []
    if deck_id:
        for row in services.aggregate_weak_tag_rows(db, uid, deck_id, limit=8):
            t = db.tags.find_one({"_id": row["tag_id"]})
            if t:
                weak_topics.append(
                    {
                        "tag_id": str(row["tag_id"]),
                        "name": t.get("name"),
                        "incorrect_count": row["incorrect_count"],
                    }
                )
    return {
        "study_records_total": total,
        "study_records_correct": correct,
        "accuracy": accuracy,
        "streak_max": streak_max,
        "weak_topics": weak_topics,
    }


@router.post("/learning/explain")
def explain_card(req: ExplainRequest, user=Depends(get_current_user)):
    if not os.getenv("OPENROUTER_API_KEY", "").strip():
        raise HTTPException(
            status_code=503,
            detail="AI explain requires OPENROUTER_API_KEY on the server",
        )
    try:
        cid = ObjectId(req.card_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Card not found")
    card = db.flashcards.find_one({"_id": cid})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    did = req.deck_id or str(card.get("deck_id"))
    try:
        deck_oid = ObjectId(did)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Deck not found")
    deck = db.decks.find_one({"_id": deck_oid, "owner_id": user["user_id"]})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    names: list[str] = []
    for row in db.card_tags.find({"card_id": cid}):
        t = db.tags.find_one({"_id": row["tag_id"]})
        if t and t.get("name"):
            names.append(str(t["name"]))
    front = (card.get("front") or {}).get("content") or ""
    back = (card.get("back") or {}).get("content") or ""
    recent_incorrect = db.study_records.count_documents(
        {"user_id": user["user_id"], "card_id": cid, "result": "incorrect"}
    )
    expl, err = generate_explain(
        front_text=front,
        expected_back=back,
        card_type=card.get("card_type"),
        tag_names=names,
        recent_incorrect=recent_incorrect,
    )
    if not expl:
        msg = (err or "Could not generate explanation").strip()
        if len(msg) > 500:
            msg = msg[:497] + "..."
        raise HTTPException(
            status_code=http_status_for_openrouter_error(msg, default_for_unknown=503),
            detail=msg,
        )
    return {"explanation": expl}
