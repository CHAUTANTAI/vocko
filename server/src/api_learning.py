import datetime
import os

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from . import services
from .answer_match import typo_one_highlight
from .db import db
from .learning_ai import generate_hint, grade_answer
from .utils import decode_token

router = APIRouter()

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


def _question_payload(card: dict, card_id: str, mode: str) -> dict:
    stored = card.get("hint")
    has_stored = bool(stored and str(stored).strip())
    return {
        "card_id": card_id,
        "front": card["front"],
        "question_type": mode,
        "has_stored_hint": has_stored,
    }

@router.post("/learning/sessions")
def start_session(req: StartSessionRequest, user=Depends(get_current_user)):
    deck = db.decks.find_one({"_id": ObjectId(req.deck_id), "owner_id": user["user_id"]})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    queue_size = int(req.options.get("queue_size", 30))
    cards = services.build_learning_queue(
        db, req.deck_id, user["user_id"], req.mode, queue_size
    )
    if not cards:
        raise HTTPException(
            status_code=400,
            detail="No cards in queue for this deck/mode",
        )
    session = {
        "user_id": user["user_id"],
        "deck_id": req.deck_id,
        "mode": req.mode,
        "started_at": datetime.datetime.utcnow(),
        "queue": [str(c["_id"]) for c in cards],
        "answers": [],
    }
    result = db.learning_sessions.insert_one(session)
    session_id = str(result.inserted_id)
    preloaded = [
        _question_payload(c, str(c["_id"]), req.mode) for c in cards[:5]
    ]
    return {"session_id": session_id, "preloaded_questions": preloaded}

@router.get("/learning/sessions/{session_id}/next")
def get_next_question(session_id: str, user=Depends(get_current_user)):
    session = db.learning_sessions.find_one({"_id": ObjectId(session_id), "user_id": user["user_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session["queue"]:
        return {"question": None}
    card_id = session["queue"][0]
    card = db.flashcards.find_one({"_id": ObjectId(card_id)})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"question": _question_payload(card, card_id, session["mode"])}


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
        raise HTTPException(status_code=503, detail=msg)
    db.flashcards.update_one({"_id": cid}, {"$set": {"hint": h}})
    return {"hint": h, "source": "ai"}

@router.post("/learning/sessions/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest, user=Depends(get_current_user)):
    session = db.learning_sessions.find_one({"_id": ObjectId(session_id), "user_id": user["user_id"]})
    if not session or not session["queue"]:
        raise HTTPException(status_code=404, detail="Session not found or finished")
    # Lấy card đầu tiên trong queue
    card_id = session["queue"][0]
    if card_id != req.card_id:
        raise HTTPException(status_code=400, detail="Card mismatch")
    card = db.flashcards.find_one({"_id": ObjectId(card_id)})
    back_content = card["back"]["content"] or ""
    expected = back_content.strip().lower()
    user_ans = (req.response or "").strip().lower()
    exact = user_ans == expected
    match_type = "exact"
    note: str | None = None
    typo_h: dict | None = None
    if exact:
        correct = True
        grade = 5
        match_type = "exact"
    else:
        typo_h = typo_one_highlight(back_content, req.response or "")
        if typo_h is not None:
            correct = True
            grade = 5
            match_type = "typo_one"
        else:
            correct = False
            grade = 0
            match_type = "none"
            if os.getenv("OPENROUTER_API_KEY", "").strip():
                ok, llm_note = grade_answer(
                    (card.get("front") or {}).get("content") or "",
                    back_content,
                    req.response,
                )
                note = llm_note
                if ok:
                    correct = True
                    grade = 4
                    match_type = "llm"
                else:
                    match_type = "none"
            else:
                note = None

    answer_event = {
        "card_id": card_id,
        "response": req.response,
        "result": "correct" if correct else "incorrect",
        "grade": grade,
        "match_type": match_type,
        "note": note,
        "typo_highlight": typo_h,
        "time_ms": req.time_ms,
        "ts": datetime.datetime.utcnow(),
    }
    db.learning_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$push": {"answers": answer_event}, "$pop": {"queue": -1}},
    )
    services.update_user_progress(
        db,
        user["user_id"],
        card_id,
        session["deck_id"],
        correct,
        grade,
    )
    sess_after = db.learning_sessions.find_one({"_id": ObjectId(session_id)})
    ans_list = (sess_after or {}).get("answers") or []
    out: dict = {
        "result": answer_event["result"],
        "grade": grade,
        "match_type": match_type,
        "session_answered": len(ans_list),
        "session_correct": sum(1 for x in ans_list if x.get("result") == "correct"),
    }
    if note:
        out["note"] = note
    if typo_h and match_type == "typo_one":
        out["typo_highlight"] = typo_h
    out["card_back"] = card.get("back") or {}
    return out

@router.post("/learning/sessions/{session_id}/finish")
def finish_session(session_id: str, user=Depends(get_current_user)):
    session = db.learning_sessions.find_one({"_id": ObjectId(session_id), "user_id": user["user_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ended_at = datetime.datetime.utcnow()
    correct = sum(1 for a in session["answers"] if a["result"] == "correct")
    total = len(session["answers"])
    accuracy = correct / total if total else 0
    db.learning_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"ended_at": ended_at, "summary": {"questions": total, "correct": correct, "accuracy": accuracy}}},
    )
    items: list[dict] = []
    for a in session.get("answers") or []:
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
            }
        )
    return {
        "summary": {"questions": total, "correct": correct, "accuracy": accuracy},
        "items": items,
    }
