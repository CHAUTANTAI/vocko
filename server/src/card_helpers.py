"""Flashcard serialization + card_tags junction (roadmap Phase 0)."""

from typing import Any

from bson import ObjectId
from bson.errors import InvalidId


def set_card_tags(db: Any, card_id: ObjectId, tag_id_strings: list[str]) -> None:
    db.card_tags.delete_many({"card_id": card_id})
    for tid in tag_id_strings or []:
        try:
            toid = ObjectId(tid)
        except InvalidId:
            continue
        if db.tags.find_one({"_id": toid}):
            try:
                db.card_tags.insert_one({"card_id": card_id, "tag_id": toid})
            except Exception:
                pass


POS_WHITELIST = frozenset(
    {
        "noun",
        "verb",
        "adjective",
        "adverb",
        "preposition",
        "conjunction",
        "pronoun",
        "determiner",
        "interjection",
        "phrasal_verb",
        "collocation",
        "other",
    }
)

CEFR_WHITELIST = frozenset({"A1", "A2", "B1", "B2", "C1", "C2"})


def serialize_card(db: Any, card: dict) -> dict:
    c = dict(card)
    cid = c.get("_id")
    if cid is not None and not isinstance(cid, str):
        c["_id"] = str(cid)
    c.pop("source_id", None)
    oid = card.get("_id")
    if oid is not None:
        qid = oid if isinstance(oid, ObjectId) else ObjectId(str(oid))
        tags = list(db.card_tags.find({"card_id": qid}))
        c["tag_ids"] = [str(t["tag_id"]) for t in tags]
    else:
        c["tag_ids"] = []
    return c


def flashcard_doc_from_payload(data: dict) -> dict:
    """Apply defaults; deck is content context (no per-card source)."""
    d = {k: v for k, v in data.items() if k not in ("tag_ids", "new_tag_names")}
    d.pop("tag_ids", None)
    d.pop("new_tag_names", None)
    d.pop("source_id", None)
    d.setdefault("card_type", "vocab")
    d.setdefault("language", "en")
    if d.get("card_type") not in ("vocab", "sentence", "grammar"):
        d["card_type"] = "vocab"
    if d.get("card_type") != "vocab":
        d.pop("part_of_speech", None)
    elif d.get("part_of_speech") is not None:
        pos = str(d["part_of_speech"]).strip()
        if not pos or pos not in POS_WHITELIST:
            d.pop("part_of_speech", None)
        else:
            d["part_of_speech"] = pos
    # Normalize CEFR if provided
    if d.get("cefr") is not None:
        try:
            c = str(d.get("cefr") or "").strip().upper()
        except Exception:
            c = ""
        if not c or c not in CEFR_WHITELIST:
            d.pop("cefr", None)
        else:
            d["cefr"] = c
    # Normalize approx (short approximate meaning/text)
    if d.get("approx") is not None:
        try:
            a = str(d.get("approx") or "").strip()
        except Exception:
            a = ""
        if not a:
            d.pop("approx", None)
        else:
            d["approx"] = a

    # Normalize phrases: accept list[str] or comma-separated string
    if d.get("phrases") is not None:
        raw = d.get("phrases")
        out_phrases: list[str] = []
        try:
            if isinstance(raw, str):
                parts = [p.strip() for p in raw.split(",") if p and p.strip()]
            elif isinstance(raw, (list, tuple)):
                parts = [str(p).strip() for p in raw if p is not None]
            else:
                parts = []
            for p in parts:
                if p and len(p) <= 200:
                    out_phrases.append(p)
                if len(out_phrases) >= 20:
                    break
        except Exception:
            out_phrases = []
        if out_phrases:
            d["phrases"] = out_phrases
        else:
            d.pop("phrases", None)
    return d
