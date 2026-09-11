"""Daily news digest API (VnExpress RSS + AI summaries)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from .news_pipeline import get_or_build_today, serialize_digest
from .openrouter_client import http_status_for_openrouter_error
from .rate_limit import limiter
from .utils import decode_token

router = APIRouter(prefix="/news", tags=["news"])


def get_current_user(request: Request):
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth.split()[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


def _digest_response(doc: dict):
    if doc.get("status") == "failed":
        err = (doc.get("error") or "News digest failed").strip()
        raise HTTPException(
            status_code=http_status_for_openrouter_error(err, default_for_unknown=503),
            detail=err,
        )
    if doc.get("status") != "ready":
        raise HTTPException(status_code=503, detail="News digest is not ready yet")
    return serialize_digest(doc)


@router.get("/today")
def news_today(user=Depends(get_current_user)):
    """Return today's digest; builds lazily on first request of the day (VN date)."""
    doc = get_or_build_today(force=False)
    return _digest_response(doc)


@router.post("/refresh")
@limiter.limit("1/hour")
def news_refresh(request: Request, user=Depends(get_current_user)):
    """Force rebuild today's digest (rate-limited)."""
    doc = get_or_build_today(force=True)
    return _digest_response(doc)
