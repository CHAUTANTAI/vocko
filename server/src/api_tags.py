"""Global tags (roadmap Phase 0)."""

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from bson import ObjectId
from bson.errors import InvalidId

from .db import db
from .openrouter_client import http_status_for_openrouter_error
from .tag_suggest import suggest_and_upsert_tags
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


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower().strip())
    s = s.strip("-")
    return s or "tag"


class TagCreate(BaseModel):
    name: str


class TagSuggestRequest(BaseModel):
    front: str
    back: str | None = None
    card_type: str = "vocab"
    max_tags: int = 6
    part_of_speech: Optional[str] = Field(
        default=None,
        description="If card_type is vocab, learner-chosen POS for context only (not emitted as a tag).",
    )


@router.get("/tags")
def list_tags(user=Depends(get_current_user)):
    tags = list(db.tags.find().sort("name", 1))
    for t in tags:
        t["_id"] = str(t["_id"])
    return {"tags": tags}


@router.post("/tags/suggest")
def suggest_tags(body: TagSuggestRequest, user=Depends(get_current_user)):
    tags, pending_new, err = suggest_and_upsert_tags(
        db,
        front=body.front,
        back=body.back,
        card_type=body.card_type,
        max_tags=body.max_tags,
        part_of_speech=body.part_of_speech,
        slugify_fn=slugify,
    )
    if err:
        raise HTTPException(
            status_code=http_status_for_openrouter_error(err),
            detail=err,
        )
    return {"tags": tags, "pending_new": pending_new}


@router.post("/tags")
def create_tag(body: TagCreate, user=Depends(get_current_user)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    slug = slugify(name)
    existing = db.tags.find_one({"slug": slug})
    if existing:
        existing["_id"] = str(existing["_id"])
        return {"tag": existing}
    doc = {"name": name, "slug": slug}
    r = db.tags.insert_one(doc)
    doc["_id"] = str(r.inserted_id)
    return {"tag": doc}


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: str, user=Depends(get_current_user)):
    try:
        tid = ObjectId(tag_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.card_tags.delete_many({"tag_id": tid})
    r = db.tags.delete_one({"_id": tid})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"success": True}
