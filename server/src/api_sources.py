"""Global sources (roadmap Phase 0)."""

import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from bson import ObjectId
from bson.errors import InvalidId

from .db import db
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


class SourceCreate(BaseModel):
    name: str
    exam: str = ""
    part: Any = None
    meta: dict = {}


@router.get("/sources")
def list_sources(user=Depends(get_current_user)):
    sources = list(db.sources.find().sort("name", 1))
    for s in sources:
        s["_id"] = str(s["_id"])
    return {"sources": sources}


@router.post("/sources")
def create_source(body: SourceCreate, user=Depends(get_current_user)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    doc = {
        "name": name,
        "exam": (body.exam or "").strip(),
        "part": body.part,
        "meta": body.meta or {},
        "created_at": datetime.datetime.utcnow(),
    }
    r = db.sources.insert_one(doc)
    doc["_id"] = str(r.inserted_id)
    return {"source": doc}


@router.delete("/sources/{source_id}")
def delete_source(source_id: str, user=Depends(get_current_user)):
    try:
        sid = ObjectId(source_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Source not found")
    db.flashcards.update_many({"source_id": sid}, {"$unset": {"source_id": ""}})
    r = db.sources.delete_one({"_id": sid})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"success": True}
