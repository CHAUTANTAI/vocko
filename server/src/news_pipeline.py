"""Daily VnExpress digest: RSS fetch + OpenRouter Vietnamese summaries."""
from __future__ import annotations

import datetime
import html
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from pymongo.errors import DuplicateKeyError

from .db import db
from .openrouter_client import chat_completion

logger = logging.getLogger(__name__)

# Fixed UTC+7 — avoids tzdata dependency on Windows/minimal images
VN_TZ = datetime.timezone(datetime.timedelta(hours=7))
SOURCE = "vnexpress"
ITEMS_PER_FEED = 5
RSS_TIMEOUT = 20.0
AI_TIMEOUT = 45.0
BUILD_WAIT_SECONDS = 120
BUILD_POLL_INTERVAL = 2.0
STALE_BUILDING_SECONDS = 180

FEEDS: dict[str, str] = {
    "domestic": "https://vnexpress.net/rss/thoi-su.rss",
    "world": "https://vnexpress.net/rss/the-gioi.rss",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def vietnam_today() -> str:
    return datetime.datetime.now(VN_TZ).date().isoformat()


def _model_news() -> str:
    explicit = os.getenv("OPENROUTER_MODEL_NEWS", "").strip()
    if explicit:
        return explicit
    return os.getenv("OPENROUTER_MODEL_HINT", "openrouter/free").strip() or "openrouter/free"


def _strip_html(raw: str) -> str:
    text = html.unescape(_TAG_RE.sub(" ", raw or ""))
    return _WS_RE.sub(" ", text).strip()


def _text_of(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return (el.text or "").strip()


def _parse_rss_items(xml_bytes: bytes, *, limit: int) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        return []
    out: list[dict[str, str]] = []
    for item in channel.findall("item"):
        title = _strip_html(_text_of(item.find("title")))
        link = _text_of(item.find("link"))
        if not title or not link:
            continue
        desc = _strip_html(_text_of(item.find("description")))
        pub = _text_of(item.find("pubDate"))
        out.append(
            {
                "title": title[:500],
                "url": link[:2000],
                "description": desc[:4000],
                "published_at": pub[:120] if pub else "",
            }
        )
        if len(out) >= limit:
            break
    return out


def fetch_feed_items(url: str, *, limit: int = ITEMS_PER_FEED) -> list[dict[str, str]]:
    headers = {
        "User-Agent": "VocKO/1.0 (daily-news; educational)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    with httpx.Client(timeout=RSS_TIMEOUT, follow_redirects=True) as client:
        r = client.get(url, headers=headers)
        r.raise_for_status()
        return _parse_rss_items(r.content, limit=limit)


def _fallback_summary(description: str, title: str) -> str:
    base = description or title
    if len(base) <= 400:
        return base
    return base[:397].rstrip() + "…"


def summarize_item(title: str, description: str) -> str:
    """Return Vietnamese summary; fall back to truncated description on AI failure."""
    excerpt = description or title
    system = (
        "Bạn là biên tập viên tin tức tiếng Việt. Tóm tắt ngắn gọn, trung lập, 2–4 câu. "
        "Chỉ dùng thông tin được cung cấp; không bịa thêm. Không dùng markdown hay tiêu đề."
    )
    user = f"Tiêu đề: {title}\n\nNội dung RSS:\n{excerpt}\n\nViết bản tóm tắt tiếng Việt."
    raw, err = chat_completion(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=_model_news(),
        temperature=0.3,
        timeout=AI_TIMEOUT,
    )
    if err or not raw:
        logger.warning("News summarize failed for %r: %s", title[:80], err)
        return _fallback_summary(description, title)
    text = raw.strip()
    return text if text else _fallback_summary(description, title)


def _enrich(items: list[dict[str, str]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for it in items:
        summary = summarize_item(it["title"], it.get("description") or "")
        entry: dict[str, Any] = {
            "title": it["title"],
            "url": it["url"],
            "summary": summary,
        }
        if it.get("published_at"):
            entry["published_at"] = it["published_at"]
        enriched.append(entry)
    return enriched


def serialize_digest(doc: dict[str, Any]) -> dict[str, Any]:
    built = doc.get("built_at")
    built_at = built.isoformat() + "Z" if isinstance(built, datetime.datetime) else built
    return {
        "date": doc.get("date"),
        "built_at": built_at,
        "source": doc.get("source") or SOURCE,
        "domestic": doc.get("domestic") or [],
        "world": doc.get("world") or [],
    }


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


def _claim_build_lock(date: str, *, force: bool) -> bool:
    """
    Try to become the builder for this date.
    Returns True if this caller should run the pipeline.
    """
    now = _utcnow()
    stale_before = now - datetime.timedelta(seconds=STALE_BUILDING_SECONDS)
    building_fields = {
        "date": date,
        "status": "building",
        "source": SOURCE,
        "building_started_at": now,
        "error": None,
    }

    if force:
        db.news_digests.update_one(
            {"date": date},
            {"$set": building_fields},
            upsert=True,
        )
        return True

    existing = db.news_digests.find_one({"date": date})
    if existing:
        status = existing.get("status")
        if status == "ready":
            return False
        if status == "building":
            started = existing.get("building_started_at")
            if isinstance(started, datetime.datetime) and started > stale_before:
                return False
            res = db.news_digests.update_one(
                {
                    "date": date,
                    "status": "building",
                    "building_started_at": started,
                },
                {"$set": building_fields},
            )
            return res.modified_count > 0
        res = db.news_digests.update_one(
            {"date": date, "status": {"$ne": "ready"}},
            {"$set": building_fields},
        )
        return res.modified_count > 0

    try:
        db.news_digests.insert_one(building_fields)
        return True
    except DuplicateKeyError:
        return False


def _wait_for_ready(date: str) -> dict[str, Any] | None:
    deadline = time.monotonic() + BUILD_WAIT_SECONDS
    while time.monotonic() < deadline:
        doc = db.news_digests.find_one({"date": date})
        if not doc:
            time.sleep(BUILD_POLL_INTERVAL)
            continue
        status = doc.get("status")
        if status == "ready":
            return doc
        if status == "failed":
            return doc
        time.sleep(BUILD_POLL_INTERVAL)
    return db.news_digests.find_one({"date": date})


def run_build(date: str) -> dict[str, Any]:
    """Fetch RSS, summarize, persist ready (or failed) digest. Returns the Mongo doc."""
    try:
        domestic_raw = fetch_feed_items(FEEDS["domestic"])
        world_raw = fetch_feed_items(FEEDS["world"])
        domestic = _enrich(domestic_raw)
        world = _enrich(world_raw)
        now = _utcnow()
        doc = {
            "date": date,
            "status": "ready",
            "source": SOURCE,
            "built_at": now,
            "domestic": domestic,
            "world": world,
            "error": None,
        }
        db.news_digests.update_one(
            {"date": date},
            {"$set": doc, "$unset": {"building_started_at": ""}},
            upsert=True,
        )
        return db.news_digests.find_one({"date": date}) or doc
    except Exception as e:
        logger.exception("News digest build failed for %s", date)
        err = str(e)[:500]
        now = _utcnow()
        failed = {
            "date": date,
            "status": "failed",
            "source": SOURCE,
            "built_at": now,
            "domestic": [],
            "world": [],
            "error": err,
        }
        db.news_digests.update_one(
            {"date": date},
            {"$set": failed, "$unset": {"building_started_at": ""}},
            upsert=True,
        )
        return db.news_digests.find_one({"date": date}) or failed


def get_or_build_today(*, force: bool = False) -> dict[str, Any]:
    """
    Return today's digest document (status ready or failed).
    Builds synchronously when needed; waits if another builder holds the lock.
    """
    date = vietnam_today()
    if not force:
        existing = db.news_digests.find_one({"date": date, "status": "ready"})
        if existing:
            return existing

    if _claim_build_lock(date, force=force):
        return run_build(date)

    waited = _wait_for_ready(date)
    if waited and waited.get("status") == "ready":
        return waited
    if waited and waited.get("status") == "failed":
        return waited

    # Timed out waiting — try to take over
    if _claim_build_lock(date, force=True):
        return run_build(date)
    final = db.news_digests.find_one({"date": date})
    if final:
        return final
    return {
        "date": date,
        "status": "failed",
        "source": SOURCE,
        "built_at": _utcnow(),
        "domestic": [],
        "world": [],
        "error": "Unable to build news digest",
    }
