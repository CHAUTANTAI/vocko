from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from bson import ObjectId
from bson.errors import InvalidId
import datetime

from .card_helpers import flashcard_doc_from_payload, serialize_card, set_card_tags
from .db import db
from .utils import decode_token

router = APIRouter()


def _require_owned_card(card_id: str, owner_id: str):
    try:
        cid = ObjectId(card_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Card not found")
    card = db.flashcards.find_one({"_id": cid})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    try:
        did = ObjectId(card["deck_id"])
    except InvalidId:
        raise HTTPException(status_code=404, detail="Card not found")
    deck = db.decks.find_one({"_id": did, "owner_id": owner_id})
    if not deck:
        raise HTTPException(status_code=404, detail="Card not found")
    return card, cid


def get_current_user(request: Request):
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth.split()[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


class DeckCreate(BaseModel):
    title: str
    description: str = ""
    language_pair: dict = {}
    settings: dict = {}


class CardCreate(BaseModel):
    front: dict
    back: dict
    media: list = []
    order_index: int = 0
    tags: list = []
    hint: Optional[str] = None
    note: Optional[str] = None
    example: Optional[str] = None
    card_type: str = "vocab"
    part_of_speech: Optional[str] = None
    language: str = "en"
    tag_ids: list = []


@router.get("/decks")
def list_decks(page: int = 1, page_size: int = 50, user=Depends(get_current_user)):
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    skip = (page - 1) * page_size
    cursor = (
        db.decks.find({"owner_id": user["user_id"]})
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    decks = []
    for d in cursor:
        d["_id"] = str(d["_id"])
        decks.append(d)
    return {"decks": decks, "page": page, "page_size": page_size}


@router.post("/decks")
def create_deck(deck: DeckCreate, user=Depends(get_current_user)):
    doc = deck.dict()
    doc["owner_id"] = user["user_id"]
    doc["card_count"] = 0
    doc["sample_cards"] = []
    doc["created_at"] = datetime.datetime.utcnow()
    result = db.decks.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return {"deck": doc}


@router.get("/decks/{deck_id}")
def get_deck(deck_id: str, include_cards: bool = False, page: int = 1, limit: int = 50, user=Depends(get_current_user)):
    deck = db.decks.find_one({"_id": ObjectId(deck_id), "owner_id": user["user_id"]})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    deck["_id"] = str(deck["_id"])
    if include_cards:
        skip = (page - 1) * limit
        cards = list(db.flashcards.find({"deck_id": deck_id}).skip(skip).limit(limit))
        out = [serialize_card(db, c) for c in cards]
        return {"deck": deck, "cards": out}
    return {"deck": deck}


@router.patch("/decks/{deck_id}")
def update_deck(deck_id: str, deck: DeckCreate, user=Depends(get_current_user)):
    result = db.decks.update_one({"_id": ObjectId(deck_id), "owner_id": user["user_id"]}, {"$set": deck.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Deck not found or not owned")
    return {"success": True}


@router.delete("/decks/{deck_id}")
def delete_deck(deck_id: str, user=Depends(get_current_user)):
    result = db.decks.delete_one({"_id": ObjectId(deck_id), "owner_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Deck not found or not owned")
    card_ids = [c["_id"] for c in db.flashcards.find({"deck_id": deck_id}, {"_id": 1})]
    if card_ids:
        db.card_tags.delete_many({"card_id": {"$in": card_ids}})
    db.flashcards.delete_many({"deck_id": deck_id})
    return {"success": True}


@router.post("/decks/{deck_id}/cards")
def create_card(deck_id: str, card: CardCreate, user=Depends(get_current_user)):
    deck = db.decks.find_one({"_id": ObjectId(deck_id), "owner_id": user["user_id"]})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or not owned")
    raw = card.dict()
    tag_ids = raw.pop("tag_ids", []) or []
    doc = flashcard_doc_from_payload(raw)
    doc["deck_id"] = deck_id
    doc["created_at"] = datetime.datetime.utcnow()
    result = db.flashcards.insert_one(doc)
    cid = result.inserted_id
    set_card_tags(db, cid, tag_ids)
    inserted = db.flashcards.find_one({"_id": cid})
    return {"card": serialize_card(db, inserted)}


@router.patch("/cards/{card_id}")
def update_card(card_id: str, card: CardCreate, user=Depends(get_current_user)):
    _, cid = _require_owned_card(card_id, user["user_id"])
    raw = card.dict()
    tag_ids = raw.pop("tag_ids", []) or []
    doc = flashcard_doc_from_payload(raw)
    update: dict = {"$set": doc}
    if "part_of_speech" not in doc:
        update["$unset"] = {"part_of_speech": ""}
    db.flashcards.update_one({"_id": cid}, update)
    set_card_tags(db, cid, tag_ids)
    inserted = db.flashcards.find_one({"_id": cid})
    return {"card": serialize_card(db, inserted)}


@router.delete("/cards/{card_id}")
def delete_card(card_id: str, user=Depends(get_current_user)):
    card, cid = _require_owned_card(card_id, user["user_id"])
    db.card_tags.delete_many({"card_id": cid})
    db.flashcards.delete_one({"_id": cid})
    db.decks.update_one({"_id": ObjectId(card["deck_id"]), "owner_id": user["user_id"]}, {"$inc": {"card_count": -1}})
    return {"success": True}
