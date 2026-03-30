from fastapi import APIRouter, HTTPException, status, Request, Depends
from pydantic import BaseModel
from .db import db
from .utils import decode_token
from . import services
from bson import ObjectId
import datetime

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
    preloaded = []
    for c in cards[:5]:
        preloaded.append({"card_id": str(c["_id"]), "front": c["front"], "question_type": req.mode})
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
    return {"question": {"card_id": card_id, "front": card["front"], "question_type": session["mode"]}}

@router.post("/learning/sessions/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest, user=Depends(get_current_user)):
    session = db.learning_sessions.find_one({"_id": ObjectId(session_id), "user_id": user["user_id"]})
    if not session or not session["queue"]:
        raise HTTPException(status_code=404, detail="Session not found or finished")
    # Lấy card đầu tiên trong queue
    card_id = session["queue"][0]
    if card_id != req.card_id:
        raise HTTPException(status_code=400, detail="Card mismatch")
    # Giả lập grading: đúng nếu response == back.content
    card = db.flashcards.find_one({"_id": ObjectId(card_id)})
    correct = (req.response.strip().lower() == card["back"]["content"].strip().lower())
    grade = 5 if correct else 0
    answer_event = {
        "card_id": card_id,
        "response": req.response,
        "result": "correct" if correct else "incorrect",
        "grade": grade,
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
    return {"result": answer_event["result"], "grade": grade}

@router.post("/learning/sessions/{session_id}/finish")
def finish_session(session_id: str, user=Depends(get_current_user)):
    session = db.learning_sessions.find_one({"_id": ObjectId(session_id), "user_id": user["user_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ended_at = datetime.datetime.utcnow()
    correct = sum(1 for a in session["answers"] if a["result"] == "correct")
    total = len(session["answers"])
    accuracy = correct / total if total else 0
    db.learning_sessions.update_one({"_id": ObjectId(session_id)}, {"$set": {"ended_at": ended_at, "summary": {"questions": total, "correct": correct, "accuracy": accuracy}}})
    return {"summary": {"questions": total, "correct": correct, "accuracy": accuracy}}
