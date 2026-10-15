"""User file + text storage (Mongo Binary + contents)."""
from __future__ import annotations

import datetime
import re
from typing import Optional
from urllib.parse import quote

from bson import Binary, ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from .db import db
from .utils import decode_token

router = APIRouter(prefix="/storage", tags=["storage"])

# BSON document hard limit is 16MB; leave headroom for metadata + contents
MAX_FILE_BYTES = 12 * 1024 * 1024
# Practical cap so a single request cannot exhaust memory (UI is "unlimited" wording)
MAX_CONTENTS_CHARS = 2_000_000
TITLE_MAX = 200


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


def _safe_filename(name: str | None) -> str:
    raw = (name or "file").strip() or "file"
    raw = raw.replace("\\", "/").split("/")[-1]
    raw = re.sub(r"[\x00-\x1f\x7f]", "", raw)
    return raw[:255] or "file"


def _serialize(doc: dict, *, include_contents: bool = True) -> dict:
    out = {
        "_id": str(doc["_id"]),
        "title": doc.get("title") or "",
        "filename": doc.get("filename"),
        "content_type": doc.get("content_type"),
        "file_size": int(doc.get("file_size") or 0),
        "has_file": bool(doc.get("binary_data") is not None and int(doc.get("file_size") or 0) > 0),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }
    if include_contents:
        out["contents"] = doc.get("contents") or ""
    return out


async def _read_upload(file: UploadFile | None) -> tuple[Optional[Binary], Optional[str], Optional[str], int]:
    if file is None:
        return None, None, None, 0
    data = await file.read()
    if not data:
        return None, None, None, 0
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {MAX_FILE_BYTES // (1024 * 1024)} MB)",
        )
    filename = _safe_filename(file.filename)
    content_type = (file.content_type or "application/octet-stream")[:200]
    return Binary(data), filename, content_type, len(data)


def _require_owned(item_id: str, user_id: str) -> tuple[dict, ObjectId]:
    oid = _oid(item_id)
    doc = db.user_storage.find_one({"_id": oid, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")
    return doc, oid


@router.get("")
def list_items(user=Depends(get_current_user)):
    rows = list(
        db.user_storage.find(
            {"user_id": user["user_id"]},
            {"binary_data": 0},
        ).sort("updated_at", -1)
    )
    return {"items": [_serialize(r, include_contents=False) for r in rows]}


@router.get("/{item_id}")
def get_item(item_id: str, user=Depends(get_current_user)):
    doc, _ = _require_owned(item_id, user["user_id"])
    return _serialize(doc, include_contents=True)


@router.get("/{item_id}/file")
def download_file(item_id: str, user=Depends(get_current_user)):
    doc, _ = _require_owned(item_id, user["user_id"])
    blob = doc.get("binary_data")
    size = int(doc.get("file_size") or 0)
    if blob is None or size <= 0:
        raise HTTPException(status_code=404, detail="No file attached")
    data = bytes(blob)
    filename = _safe_filename(doc.get("filename"))
    media = doc.get("content_type") or "application/octet-stream"
    # RFC 5987 filename*
    disposition = f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": disposition},
    )


@router.post("")
async def create_item(
    title: str = Form(""),
    contents: str = Form(""),
    file: UploadFile | None = File(None),
    user=Depends(get_current_user),
):
    contents = contents if contents is not None else ""
    if len(contents) > MAX_CONTENTS_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Contents too long (max {MAX_CONTENTS_CHARS} characters)",
        )
    title_n = (title or "").strip()[:TITLE_MAX]
    binary, filename, content_type, file_size = await _read_upload(file)
    if not title_n and not contents and not binary:
        raise HTTPException(status_code=400, detail="Provide a file and/or contents")
    if not title_n:
        title_n = filename or "Untitled"
    now = datetime.datetime.utcnow()
    doc = {
        "user_id": user["user_id"],
        "title": title_n,
        "contents": contents,
        "filename": filename,
        "content_type": content_type,
        "file_size": file_size,
        "binary_data": binary,
        "created_at": now,
        "updated_at": now,
    }
    ins = db.user_storage.insert_one(doc)
    doc["_id"] = ins.inserted_id
    return _serialize(doc, include_contents=True)


@router.put("/{item_id}")
async def update_item(
    item_id: str,
    title: str = Form(""),
    contents: str = Form(""),
    clear_file: str = Form("0"),
    file: UploadFile | None = File(None),
    user=Depends(get_current_user),
):
    doc, oid = _require_owned(item_id, user["user_id"])
    contents = contents if contents is not None else ""
    if len(contents) > MAX_CONTENTS_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Contents too long (max {MAX_CONTENTS_CHARS} characters)",
        )
    title_n = (title or "").strip()[:TITLE_MAX] or (doc.get("title") or "Untitled")
    now = datetime.datetime.utcnow()
    update: dict = {
        "title": title_n,
        "contents": contents,
        "updated_at": now,
    }
    binary, filename, content_type, file_size = await _read_upload(file)
    if binary is not None:
        update["binary_data"] = binary
        update["filename"] = filename
        update["content_type"] = content_type
        update["file_size"] = file_size
    elif (clear_file or "").strip() in ("1", "true", "yes"):
        update["binary_data"] = None
        update["filename"] = None
        update["content_type"] = None
        update["file_size"] = 0

    db.user_storage.update_one({"_id": oid}, {"$set": update})
    fresh = db.user_storage.find_one({"_id": oid})
    return _serialize(fresh or {**doc, **update, "_id": oid}, include_contents=True)


@router.delete("/{item_id}")
def delete_item(item_id: str, user=Depends(get_current_user)):
    _, oid = _require_owned(item_id, user["user_id"])
    db.user_storage.delete_one({"_id": oid})
    return {"ok": True}
