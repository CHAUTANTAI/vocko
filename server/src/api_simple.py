"""Simple Flashcard API — separate decks/cards from vocab module."""
from __future__ import annotations

import datetime
import re
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .db import db
from .simple_services import (
    apply_grade_to_queue,
    build_simple_queue,
    serialize_simple_card,
    serialize_simple_deck,
    session_summary_preview,
    upsert_simple_card_stat,
)
from .utils import decode_token

router = APIRouter(prefix="/simple", tags=["simple"])

TEXT_MAX = 2000
SEARCH_Q_MAX = 120
SEARCH_LIMIT_CAP = 40


def get_current_user(request: Request):
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth.split()[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


def _oid(value: str, detail: str = "Not found") -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=404, detail=detail)


def _require_owned_deck(deck_id: str, owner_id: str) -> tuple[dict, ObjectId]:
    oid = _oid(deck_id, "Deck not found")
    deck = db.simple_decks.find_one({"_id": oid, "owner_id": owner_id})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck, oid


def _require_owned_card(card_id: str, owner_id: str) -> tuple[dict, ObjectId, dict]:
    cid = _oid(card_id, "Card not found")
    card = db.simple_cards.find_one({"_id": cid})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    deck, _ = _require_owned_deck(str(card.get("deck_id") or ""), owner_id)
    return card, cid, deck


def _normalize_side(value: str | None, *, required: bool) -> Optional[str]:
    if value is None:
        if required:
            raise HTTPException(status_code=400, detail="front and back are required")
        return None
    text = str(value).strip()
    if required and not text:
        raise HTTPException(status_code=400, detail="front and back must be non-empty")
    if len(text) > TEXT_MAX:
        raise HTTPException(status_code=400, detail=f"Text max length is {TEXT_MAX}")
    return text


def _bump_card_count(deck_oid: ObjectId, delta: int) -> None:
    db.simple_decks.update_one(
        {"_id": deck_oid},
        {
            "$inc": {"card_count": delta},
            "$set": {"updated_at": datetime.datetime.utcnow()},
        },
    )


def _card_payload(card: dict) -> dict:
    return serialize_simple_card(card)


class DeckCreate(BaseModel):
    title: str
    description: str = ""


class DeckPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class CardCreate(BaseModel):
    front: str
    back: str


class CardPatch(BaseModel):
    front: Optional[str] = None
    back: Optional[str] = None


class CardBatchCreate(BaseModel):
    cards: list[CardCreate] = Field(default_factory=list)


class CardSyncUpdate(BaseModel):
    id: str
    front: str
    back: str


class CardSyncRequest(BaseModel):
    """One round-trip: apply creates, updates, deletes for a deck."""
    create: list[CardCreate] = Field(default_factory=list)
    update: list[CardSyncUpdate] = Field(default_factory=list)
    delete_ids: list[str] = Field(default_factory=list)


class StartSessionRequest(BaseModel):
    deck_id: str


class GradeRequest(BaseModel):
    card_id: str
    remembered: bool
    time_ms: int = 0


class StudyEventItem(BaseModel):
    card_id: str
    remembered: bool
    time_ms: int = 0


class CompleteSessionRequest(BaseModel):
    """Client-run queue: flush all grades in one request when the session ends."""
    events: list[StudyEventItem] = Field(default_factory=list)


@router.get("/decks")
def list_decks(page: int = 1, page_size: int = 50, user=Depends(get_current_user)):
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    skip = (page - 1) * page_size
    q = {"owner_id": user["user_id"]}
    total = db.simple_decks.count_documents(q)
    rows = (
        db.simple_decks.find(q).sort("created_at", -1).skip(skip).limit(page_size)
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "decks": [serialize_simple_deck(d) for d in rows],
    }


@router.post("/decks")
def create_deck(req: DeckCreate, user=Depends(get_current_user)):
    title = (req.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    if len(title) > 200:
        raise HTTPException(status_code=400, detail="title too long")
    now = datetime.datetime.utcnow()
    doc = {
        "owner_id": user["user_id"],
        "title": title,
        "description": (req.description or "").strip()[:2000],
        "card_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    ins = db.simple_decks.insert_one(doc)
    doc["_id"] = ins.inserted_id
    return serialize_simple_deck(doc)


@router.get("/decks/{deck_id}")
def get_deck(deck_id: str, user=Depends(get_current_user)):
    deck, _ = _require_owned_deck(deck_id, user["user_id"])
    cards = list(
        db.simple_cards.find({"deck_id": deck_id}).sort([("order_index", 1), ("_id", 1)])
    )
    out = serialize_simple_deck(deck)
    out["cards"] = [_card_payload(c) for c in cards]
    return out


@router.patch("/decks/{deck_id}")
def patch_deck(deck_id: str, req: DeckPatch, user=Depends(get_current_user)):
    _, oid = _require_owned_deck(deck_id, user["user_id"])
    updates: dict = {}
    if req.title is not None:
        title = req.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="title is required")
        updates["title"] = title[:200]
    if req.description is not None:
        updates["description"] = req.description.strip()[:2000]
    if not updates:
        deck, _ = _require_owned_deck(deck_id, user["user_id"])
        return serialize_simple_deck(deck)
    updates["updated_at"] = datetime.datetime.utcnow()
    db.simple_decks.update_one({"_id": oid}, {"$set": updates})
    deck = db.simple_decks.find_one({"_id": oid})
    return serialize_simple_deck(deck)


@router.delete("/decks/{deck_id}")
def delete_deck(deck_id: str, user=Depends(get_current_user)):
    _, oid = _require_owned_deck(deck_id, user["user_id"])
    card_ids = [str(c["_id"]) for c in db.simple_cards.find({"deck_id": deck_id}, {"_id": 1})]
    db.simple_cards.delete_many({"deck_id": deck_id})
    if card_ids:
        db.simple_card_stats.delete_many({"card_id": {"$in": card_ids}})
    db.simple_card_stats.delete_many({"deck_id": deck_id})
    db.simple_learning_sessions.delete_many({"deck_id": deck_id, "user_id": user["user_id"]})
    db.simple_decks.delete_one({"_id": oid})
    return {"ok": True}


@router.get("/decks/{deck_id}/cards")
def list_cards(deck_id: str, q: str = "", user=Depends(get_current_user)):
    _require_owned_deck(deck_id, user["user_id"])
    filt: dict = {"deck_id": deck_id}
    raw = (q or "").strip()[:SEARCH_Q_MAX]
    if raw:
        pattern = {"$regex": re.escape(raw), "$options": "i"}
        filt["$or"] = [{"front": pattern}, {"back": pattern}]
    cards = list(db.simple_cards.find(filt).sort([("order_index", 1), ("_id", 1)]))
    return {"cards": [_card_payload(c) for c in cards]}


@router.post("/decks/{deck_id}/cards")
def create_card(deck_id: str, req: CardCreate, user=Depends(get_current_user)):
    _, oid = _require_owned_deck(deck_id, user["user_id"])
    front = _normalize_side(req.front, required=True)
    back = _normalize_side(req.back, required=True)
    now = datetime.datetime.utcnow()
    last = db.simple_cards.find_one({"deck_id": deck_id}, sort=[("order_index", -1)])
    order_index = int(last.get("order_index") or 0) + 1 if last else 0
    doc = {
        "deck_id": deck_id,
        "front": front,
        "back": back,
        "order_index": order_index,
        "created_at": now,
        "updated_at": now,
    }
    ins = db.simple_cards.insert_one(doc)
    doc["_id"] = ins.inserted_id
    _bump_card_count(oid, 1)
    return _card_payload(doc)


@router.post("/decks/{deck_id}/cards/batch")
def create_cards_batch(deck_id: str, req: CardBatchCreate, user=Depends(get_current_user)):
    _, oid = _require_owned_deck(deck_id, user["user_id"])
    if not req.cards:
        return {"cards": []}
    if len(req.cards) > 200:
        raise HTTPException(status_code=400, detail="Max 200 cards per batch")
    now = datetime.datetime.utcnow()
    last = db.simple_cards.find_one({"deck_id": deck_id}, sort=[("order_index", -1)])
    order_index = int(last.get("order_index") or 0) + 1 if last else 0
    docs = []
    for item in req.cards:
        front = _normalize_side(item.front, required=True)
        back = _normalize_side(item.back, required=True)
        docs.append(
            {
                "deck_id": deck_id,
                "front": front,
                "back": back,
                "order_index": order_index,
                "created_at": now,
                "updated_at": now,
            }
        )
        order_index += 1
    result = db.simple_cards.insert_many(docs)
    for doc, _id in zip(docs, result.inserted_ids):
        doc["_id"] = _id
    _bump_card_count(oid, len(docs))
    return {"cards": [_card_payload(d) for d in docs]}


@router.post("/decks/{deck_id}/cards/sync")
def sync_cards(deck_id: str, req: CardSyncRequest, user=Depends(get_current_user)):
    """Apply draft creates/updates/deletes in one request (fewer cold-start round-trips)."""
    _, oid = _require_owned_deck(deck_id, user["user_id"])
    if len(req.create) > 200 or len(req.update) > 200 or len(req.delete_ids) > 200:
        raise HTTPException(status_code=400, detail="Max 200 items per sync list")

    deleted = 0
    for raw_id in req.delete_ids:
        try:
            cid = ObjectId(raw_id)
        except InvalidId:
            continue
        card = db.simple_cards.find_one({"_id": cid, "deck_id": deck_id})
        if not card:
            continue
        db.simple_cards.delete_one({"_id": cid})
        db.simple_card_stats.delete_many({"card_id": raw_id})
        deleted += 1

    updated = 0
    now = datetime.datetime.utcnow()
    for item in req.update:
        try:
            cid = ObjectId(item.id)
        except InvalidId:
            raise HTTPException(status_code=400, detail=f"Invalid card id: {item.id}")
        card = db.simple_cards.find_one({"_id": cid, "deck_id": deck_id})
        if not card:
            raise HTTPException(status_code=404, detail=f"Card not found: {item.id}")
        front = _normalize_side(item.front, required=True)
        back = _normalize_side(item.back, required=True)
        db.simple_cards.update_one(
            {"_id": cid},
            {"$set": {"front": front, "back": back, "updated_at": now}},
        )
        updated += 1

    created_docs: list[dict] = []
    if req.create:
        last = db.simple_cards.find_one({"deck_id": deck_id}, sort=[("order_index", -1)])
        order_index = int(last.get("order_index") or 0) + 1 if last else 0
        for item in req.create:
            front = _normalize_side(item.front, required=True)
            back = _normalize_side(item.back, required=True)
            created_docs.append(
                {
                    "deck_id": deck_id,
                    "front": front,
                    "back": back,
                    "order_index": order_index,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            order_index += 1
        result = db.simple_cards.insert_many(created_docs)
        for doc, _id in zip(created_docs, result.inserted_ids):
            doc["_id"] = _id

    real_count = db.simple_cards.count_documents({"deck_id": deck_id})
    db.simple_decks.update_one(
        {"_id": oid},
        {"$set": {"card_count": real_count, "updated_at": datetime.datetime.utcnow()}},
    )

    cards = list(
        db.simple_cards.find({"deck_id": deck_id}).sort([("order_index", 1), ("_id", 1)])
    )
    deck = db.simple_decks.find_one({"_id": oid})
    return {
        "created": len(created_docs),
        "updated": updated,
        "deleted": deleted,
        "deck": serialize_simple_deck(deck),
        "cards": [_card_payload(c) for c in cards],
    }


@router.patch("/cards/{card_id}")
def patch_card(card_id: str, req: CardPatch, user=Depends(get_current_user)):
    card, cid, _ = _require_owned_card(card_id, user["user_id"])
    updates: dict = {}
    if req.front is not None:
        updates["front"] = _normalize_side(req.front, required=True)
    if req.back is not None:
        updates["back"] = _normalize_side(req.back, required=True)
    if not updates:
        return _card_payload(card)
    updates["updated_at"] = datetime.datetime.utcnow()
    db.simple_cards.update_one({"_id": cid}, {"$set": updates})
    card = db.simple_cards.find_one({"_id": cid})
    return _card_payload(card)


@router.delete("/cards/{card_id}")
def delete_card(card_id: str, user=Depends(get_current_user)):
    card, cid, deck = _require_owned_card(card_id, user["user_id"])
    db.simple_cards.delete_one({"_id": cid})
    db.simple_card_stats.delete_many({"card_id": card_id})
    _bump_card_count(deck["_id"], -1)
    # Clamp card_count >= 0
    db.simple_decks.update_one(
        {"_id": deck["_id"], "card_count": {"$lt": 0}},
        {"$set": {"card_count": 0}},
    )
    return {"ok": True}


@router.get("/search")
def simple_search(q: str = "", user=Depends(get_current_user)):
    raw = (q or "").strip()[:SEARCH_Q_MAX]
    if not raw:
        return {"decks": [], "cards": []}
    owner_id = user["user_id"]
    pattern = {"$regex": re.escape(raw), "$options": "i"}

    decks_out = []
    for d in (
        db.simple_decks.find(
            {"owner_id": owner_id, "title": pattern},
            {"title": 1, "created_at": 1},
        )
        .sort("created_at", -1)
        .limit(SEARCH_LIMIT_CAP)
    ):
        decks_out.append({"_id": str(d["_id"]), "title": d.get("title") or ""})

    owned_ids = [
        str(d["_id"])
        for d in db.simple_decks.find({"owner_id": owner_id}, {"_id": 1})
    ]
    cards_out = []
    if owned_ids:
        for c in (
            db.simple_cards.find(
                {
                    "deck_id": {"$in": owned_ids},
                    "$or": [{"front": pattern}, {"back": pattern}],
                }
            ).limit(SEARCH_LIMIT_CAP)
        ):
            deck = db.simple_decks.find_one({"_id": ObjectId(c["deck_id"])}, {"title": 1})
            cards_out.append(
                {
                    "_id": str(c["_id"]),
                    "deck_id": c.get("deck_id") or "",
                    "deck_title": (deck or {}).get("title") or "",
                    "front": c.get("front") or "",
                    "back": c.get("back") or "",
                }
            )
    return {"decks": decks_out, "cards": cards_out}


@router.get("/decks/{deck_id}/stats")
def deck_stats(deck_id: str, user=Depends(get_current_user)):
    _require_owned_deck(deck_id, user["user_id"])
    rows = list(
        db.simple_card_stats.find({"user_id": user["user_id"], "deck_id": deck_id})
        .sort("forget_count", -1)
        .limit(20)
    )
    total_forget = sum(int(r.get("forget_count") or 0) for r in rows)
    # Recompute total forget across all stats for deck (not only top 20)
    agg = list(
        db.simple_card_stats.aggregate(
            [
                {"$match": {"user_id": user["user_id"], "deck_id": deck_id}},
                {
                    "$group": {
                        "_id": None,
                        "forget_total": {"$sum": "$forget_count"},
                        "remember_total": {"$sum": "$remember_count"},
                    }
                },
            ]
        )
    )
    totals = agg[0] if agg else {"forget_total": 0, "remember_total": 0}
    hard = []
    for r in rows:
        if int(r.get("forget_count") or 0) <= 0:
            continue
        card = db.simple_cards.find_one({"_id": ObjectId(r["card_id"])}, {"front": 1, "back": 1})
        hard.append(
            {
                "card_id": r["card_id"],
                "front": (card or {}).get("front") or "",
                "back": (card or {}).get("back") or "",
                "forget_count": int(r.get("forget_count") or 0),
                "remember_count": int(r.get("remember_count") or 0),
            }
        )
    return {
        "deck_id": deck_id,
        "forget_total": int(totals.get("forget_total") or 0),
        "remember_total": int(totals.get("remember_total") or 0),
        "hard_cards": hard,
        "top_forget_sum_sample": total_forget,
    }


@router.post("/learning/sessions")
def start_session(req: StartSessionRequest, user=Depends(get_current_user)):
    _require_owned_deck(req.deck_id, user["user_id"])
    queue = build_simple_queue(db, req.deck_id)
    if not queue:
        raise HTTPException(status_code=400, detail="No cards in this deck")
    now = datetime.datetime.utcnow()
    session = {
        "user_id": user["user_id"],
        "deck_id": req.deck_id,
        "started_at": now,
        "ended_at": None,
        "queue": queue,
        "initial_count": len(queue),
        "initial_card_ids": list(queue),
        "events": [],
        "summary": None,
        "client_queue": True,
    }
    ins = db.simple_learning_sessions.insert_one(session)
    session_id = str(ins.inserted_id)
    by_id = {
        str(c["_id"]): c
        for c in db.simple_cards.find({"deck_id": req.deck_id})
    }
    cards = []
    for cid in queue:
        doc = by_id.get(cid)
        if doc:
            cards.append(_card_payload(doc))
    return {
        "session_id": session_id,
        "remaining": len(cards),
        "initial_count": len(cards),
        "card": cards[0] if cards else None,
        "cards": cards,
    }


@router.get("/learning/sessions/{session_id}/next")
def next_card(session_id: str, user=Depends(get_current_user)):
    sid = _oid(session_id, "Session not found")
    session = db.simple_learning_sessions.find_one({"_id": sid, "user_id": user["user_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    queue = session.get("queue") or []
    if not queue or session.get("ended_at"):
        return {
            "done": True,
            "remaining": 0,
            "summary": session.get("summary") or session_summary_preview(session),
            "card": None,
        }
    card = db.simple_cards.find_one({"_id": ObjectId(queue[0])})
    if not card:
        # Skip missing card
        new_q = queue[1:]
        db.simple_learning_sessions.update_one({"_id": sid}, {"$set": {"queue": new_q}})
        if not new_q:
            return {
                "done": True,
                "remaining": 0,
                "summary": session_summary_preview({**session, "queue": []}),
                "card": None,
            }
        card = db.simple_cards.find_one({"_id": ObjectId(new_q[0])})
        return {
            "done": False,
            "remaining": len(new_q),
            "card": _card_payload(card) if card else None,
        }
    return {
        "done": False,
        "remaining": len(queue),
        "card": _card_payload(card),
    }


@router.post("/learning/sessions/{session_id}/grade")
def grade_card(session_id: str, req: GradeRequest, user=Depends(get_current_user)):
    sid = _oid(session_id, "Session not found")
    session = db.simple_learning_sessions.find_one({"_id": sid, "user_id": user["user_id"]})
    if not session or session.get("ended_at"):
        raise HTTPException(status_code=404, detail="Session not found or finished")
    queue = list(session.get("queue") or [])
    try:
        new_queue = apply_grade_to_queue(queue, req.card_id, req.remembered)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = "remembered" if req.remembered else "forgot"
    event = {
        "card_id": req.card_id,
        "result": result,
        "ts": datetime.datetime.utcnow(),
        "time_ms": max(0, int(req.time_ms or 0)),
    }
    upsert_simple_card_stat(
        db,
        user_id=user["user_id"],
        card_id=req.card_id,
        deck_id=session["deck_id"],
        remembered=req.remembered,
    )
    done = len(new_queue) == 0
    update: dict = {
        "$set": {"queue": new_queue},
        "$push": {"events": event},
    }
    summary = None
    if done:
        preview = session_summary_preview(
            {
                **session,
                "queue": new_queue,
                "events": list(session.get("events") or []) + [event],
            }
        )
        summary = {
            **preview,
            "duration_ms": None,
        }
        started = session.get("started_at")
        if started:
            summary["duration_ms"] = int(
                (datetime.datetime.utcnow() - started).total_seconds() * 1000
            )
        update["$set"]["ended_at"] = datetime.datetime.utcnow()
        update["$set"]["summary"] = summary

    db.simple_learning_sessions.update_one({"_id": sid}, update)

    next_card_doc = None
    if new_queue:
        next_card_doc = db.simple_cards.find_one({"_id": ObjectId(new_queue[0])})

    return {
        "done": done,
        "remaining": len(new_queue),
        "card": _card_payload(next_card_doc) if next_card_doc else None,
        "summary": summary,
    }


@router.post("/learning/sessions/{session_id}/complete")
def complete_session(session_id: str, req: CompleteSessionRequest, user=Depends(get_current_user)):
    """Persist all client-side grades in one round-trip (stats + session summary)."""
    sid = _oid(session_id, "Session not found")
    session = db.simple_learning_sessions.find_one({"_id": sid, "user_id": user["user_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("ended_at") and session.get("summary"):
        return {"ok": True, "summary": session["summary"]}
    if len(req.events) > 5000:
        raise HTTPException(status_code=400, detail="Too many events")

    deck_id = session["deck_id"]
    owned_ids = {
        str(c["_id"])
        for c in db.simple_cards.find({"deck_id": deck_id}, {"_id": 1})
    }
    # Also allow ids that were in the initial session queue (deleted mid-session edge case)
    for cid in session.get("queue") or []:
        owned_ids.add(str(cid))
    for cid in session.get("initial_card_ids") or []:
        owned_ids.add(str(cid))

    events: list[dict] = []
    now = datetime.datetime.utcnow()
    for item in req.events:
        if item.card_id not in owned_ids:
            raise HTTPException(status_code=400, detail=f"Card not in deck: {item.card_id}")
        remembered = bool(item.remembered)
        result = "remembered" if remembered else "forgot"
        events.append(
            {
                "card_id": item.card_id,
                "result": result,
                "ts": now,
                "time_ms": max(0, int(item.time_ms or 0)),
            }
        )
        upsert_simple_card_stat(
            db,
            user_id=user["user_id"],
            card_id=item.card_id,
            deck_id=deck_id,
            remembered=remembered,
        )

    preview = session_summary_preview(
        {
            **session,
            "queue": [],
            "events": events,
        }
    )
    summary = {**preview, "duration_ms": None}
    started = session.get("started_at")
    if started:
        summary["duration_ms"] = int((now - started).total_seconds() * 1000)

    db.simple_learning_sessions.update_one(
        {"_id": sid},
        {
            "$set": {
                "ended_at": now,
                "summary": summary,
                "queue": [],
                "events": events,
            }
        },
    )
    return {"ok": True, "summary": summary}


@router.post("/learning/sessions/{session_id}/finish")
def finish_session(session_id: str, user=Depends(get_current_user)):
    sid = _oid(session_id, "Session not found")
    session = db.simple_learning_sessions.find_one({"_id": sid, "user_id": user["user_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("ended_at") and session.get("summary"):
        return {"ok": True, "summary": session["summary"]}
    summary = session_summary_preview(session)
    started = session.get("started_at")
    if started:
        summary["duration_ms"] = int(
            (datetime.datetime.utcnow() - started).total_seconds() * 1000
        )
    else:
        summary["duration_ms"] = None
    db.simple_learning_sessions.update_one(
        {"_id": sid},
        {
            "$set": {
                "ended_at": datetime.datetime.utcnow(),
                "summary": summary,
                "queue": [],
            }
        },
    )
    return {"ok": True, "summary": summary}
