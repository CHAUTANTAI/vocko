from typing import Optional

from fastapi import APIRouter, HTTPException, status, Request, Depends
from pydantic import BaseModel
from .db import db
from .utils import decode_token
from bson import ObjectId
from bson.errors import InvalidId
import datetime

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
        for c in cards:
            c["_id"] = str(c["_id"])
        return {"deck": deck, "cards": cards}
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
    db.flashcards.delete_many({"deck_id": deck_id})
    return {"success": True}

@router.post("/decks/{deck_id}/cards")
def create_card(deck_id: str, card: CardCreate, user=Depends(get_current_user)):
    deck = db.decks.find_one({"_id": ObjectId(deck_id), "owner_id": user["user_id"]})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or not owned")
    doc = card.dict()
    doc["deck_id"] = deck_id
    doc["created_at"] = datetime.datetime.utcnow()
    result = db.flashcards.insert_one(doc)
    db.decks.update_one({"_id": ObjectId(deck_id)}, {"$inc": {"card_count": 1}})
    doc["_id"] = str(result.inserted_id)
    return {"card": doc}

@router.patch("/cards/{card_id}")
def update_card(card_id: str, card: CardCreate, user=Depends(get_current_user)):
    _, cid = _require_owned_card(card_id, user["user_id"])
    result = db.flashcards.update_one({"_id": cid}, {"$set": card.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"success": True}

@router.delete("/cards/{card_id}")
def delete_card(card_id: str, user=Depends(get_current_user)):
    card, cid = _require_owned_card(card_id, user["user_id"])
    db.flashcards.delete_one({"_id": cid})
    db.decks.update_one({"_id": ObjectId(card["deck_id"]), "owner_id": user["user_id"]}, {"$inc": {"card_count": -1}})
    return {"success": True}
