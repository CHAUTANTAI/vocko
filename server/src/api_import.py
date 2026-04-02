"""TOEIC-style vocabulary extraction from pasted text (OpenRouter)."""

from __future__ import annotations

import logging
import os
import re
import textwrap
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .card_helpers import POS_WHITELIST
from .learning_ai import _parse_json_object
from .openrouter_client import chat_completion, http_status_for_openrouter_error
from .utils import decode_token

logger = logging.getLogger(__name__)

router = APIRouter()

TOEIC_MAX_TEXT_LEN = 35_000
TOEIC_CHUNK_SIZE = 2_800
TOEIC_MAX_TERMS_DEFAULT = 50
TOEIC_MAX_TERMS_CAP = 100
TOEIC_PER_CHUNK_CAP = 28


def get_current_user(request: Request):
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth.split()[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


def _model_import() -> str:
    raw = os.getenv("OPENROUTER_MODEL_IMPORT", "").strip()
    if raw:
        return raw
    raw = os.getenv("OPENROUTER_MODEL_HINT", "openrouter/free").strip()
    return raw or "openrouter/free"


def _import_timeout() -> float:
    raw = os.getenv("OPENROUTER_TIMEOUT_IMPORT", "75").strip()
    try:
        v = float(raw)
        return max(15.0, min(v, 180.0))
    except ValueError:
        return 75.0


def _chunk_text(text: str) -> list[str]:
    t = (text or "").strip()
    if not t:
        return []
    parts: list[str] = []
    buf: list[str] = []
    n = 0
    for para in re.split(r"\n\s*\n", t):
        p = para.strip()
        if not p:
            continue
        if n + len(p) + (2 if buf else 0) <= TOEIC_CHUNK_SIZE:
            buf.append(p)
            n += len(p) + (2 if len(buf) > 1 else 0)
            continue
        if buf:
            parts.append("\n\n".join(buf))
            buf = []
            n = 0
        if len(p) <= TOEIC_CHUNK_SIZE:
            buf = [p]
            n = len(p)
        else:
            for i in range(0, len(p), TOEIC_CHUNK_SIZE):
                parts.append(p[i : i + TOEIC_CHUNK_SIZE])
    if buf:
        parts.append("\n\n".join(buf))
    return parts if parts else [t[:TOEIC_CHUNK_SIZE]]


_POS_NORMALIZE = {
    "noun": "noun",
    "verb": "verb",
    "adjective": "adjective",
    "adverb": "adverb",
    "preposition": "preposition",
    "conjunction": "conjunction",
    "pronoun": "pronoun",
    "determiner": "determiner",
    "interjection": "interjection",
    "phrasalverb": "phrasal_verb",
    "phrasal_verb": "phrasal_verb",
    "phrasal verb": "phrasal_verb",
    "collocation": "collocation",
    "other": "other",
}


def _normalize_pos(raw: Any) -> tuple[str | None, str | None]:
    """Returns (whitelist_pos or None, warning or None). None pos → caller may use 'other' or skip."""
    if raw is None:
        return None, None
    s = str(raw).strip().lower()
    if not s:
        return None, None
    s_compact = re.sub(r"[\s\-]+", "", s)
    if s in _POS_NORMALIZE:
        out = _POS_NORMALIZE[s]
    elif s_compact in _POS_NORMALIZE:
        out = _POS_NORMALIZE[s_compact]
    else:
        out = s.replace(" ", "_")
    if out in POS_WHITELIST:
        return out, None
    return "other", f"Unknown POS normalized to other: {raw!r}"


_CEFR_VALID = frozenset({"A1", "A2", "B1", "B2", "C1", "C2"})
_CEFR_RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}


def _normalize_cefr(raw: Any) -> tuple[str | None, str | None]:
    if raw is None:
        return None, "missing cefr"
    s = str(raw).strip().upper()
    if not s:
        return None, "empty cefr"
    s = s.split("+")[0].strip()
    if s in _CEFR_VALID:
        return s, None
    return None, f"invalid cefr {raw!r}"


def _parse_difficulty_score(raw: Any) -> tuple[int, str | None]:
    if raw is None:
        return 5, "missing difficulty_score; defaulted to 5"
    try:
        if isinstance(raw, bool):
            return 5, "invalid difficulty_score type"
        v = int(float(raw))
    except (TypeError, ValueError):
        return 5, "invalid difficulty_score; defaulted to 5"
    if v < 1 or v > 10:
        v = max(1, min(10, v))
        return v, "difficulty_score clamped to 1–10"
    return v, None


def _term_pick_harder(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    da = int(a.get("difficulty_score") or 0)
    db = int(b.get("difficulty_score") or 0)
    if db > da:
        return b
    if db < da:
        return a
    ra = _CEFR_RANK.get(str(a.get("cefr") or "").upper(), 0)
    rb = _CEFR_RANK.get(str(b.get("cefr") or "").upper(), 0)
    if rb > ra:
        return b
    if rb < ra:
        return a
    return a


_TOEIC_SYSTEM = textwrap.dedent(
    """
    You extract TOEIC Reading/Listening vocabulary for learners targeting score 750+ (not 600-level).

    Priorities (strict):
    - Favor LESS common / higher-register items actually in the excerpt: formal nouns, adjectives, verbs, two- to four-word collocations, and idioms typical of news, business, HR, facilities, contracts, or Part 7-style passages.
    - Actively SKIP elementary words normal at A1–A2 unless they appear inside a clearly advanced collocation (e.g. do not output "go", "big", "say", "money" alone).
    - Do NOT list several near-synonyms of the same idea (e.g. prefer ONE of restore / restoration / renovated unless the passage uses distinct senses).
    - Aim to surface words a 750+ candidate might still miss: e.g. intact, preserve, civic, petition, iconic, restoration, deserted, clerk, pouring in, former glory — when they appear or match the passage tone.

    For EACH term you MUST output:
    - word: headword or short phrase as in the text
    - part_of_speech: one of noun, verb, adjective, adverb, preposition, conjunction, pronoun, determiner, interjection, phrasal_verb, collocation, other
    - meaning_vi: concise Vietnamese gloss for the sense in THIS passage
    - cefr: exactly one of A1, A2, B1, B2, C1, C2 (your best estimate for the lemma/phrase in general English)
    - difficulty_score: integer 1–10 for TOEIC difficulty in context (1=trivial, 4–5=B1 routine, 6–7=B2, 8–9=C1/part-7 hard, 10=C2 or rare). For 750+ lists, most picks should be 6–10; avoid flooding with 1–4.
    - note_en: optional short English hint (register, collocation, or trap)

    Return ONLY valid JSON (no markdown outside JSON) with this exact shape:
    {"terms":[{"word":"string","part_of_speech":"noun","meaning_vi":"string","cefr":"B2","difficulty_score":8,"note_en":"optional"}]}

    Do not include more than MAX_TERMS_IN_CHUNK terms in this response.
    """
).strip()


class ToeicVocabRequest(BaseModel):
    text: str = Field(..., min_length=1)
    max_terms: int = Field(default=TOEIC_MAX_TERMS_DEFAULT, ge=1, le=TOEIC_MAX_TERMS_CAP)


@router.post("/import/toeic-vocab")
def import_toeic_vocabulary(body: ToeicVocabRequest, user=Depends(get_current_user)):
    _ = user
    text = body.text
    if len(text) > TOEIC_MAX_TEXT_LEN:
        raise HTTPException(
            status_code=413,
            detail=f"Text exceeds maximum length ({TOEIC_MAX_TEXT_LEN} characters)",
        )
    chunks = _chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="Text is empty")

    max_terms = min(body.max_terms, TOEIC_MAX_TERMS_CAP)
    model = _model_import()
    timeout = _import_timeout()
    merged: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    for ci, chunk in enumerate(chunks):
        cap = min(TOEIC_PER_CHUNK_CAP, max_terms + 5)
        user_msg = textwrap.dedent(
            f"""
            MAX_TERMS_IN_CHUNK={cap}

            Excerpt (chunk {ci + 1} of {len(chunks)}):
            ---
            {chunk}
            ---
            """
        ).strip()
        raw, err = chat_completion(
            [
                {"role": "system", "content": _TOEIC_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=model,
            temperature=0.25,
            timeout=timeout,
        )
        if err:
            status = http_status_for_openrouter_error(err, default_for_unknown=503)
            logger.warning("toeic-vocab chunk %s model error: %s", ci, err[:300])
            raise HTTPException(status_code=status, detail="Vocabulary extraction failed. Try again or shorten the text.")

        parsed = _parse_json_object(raw or "")
        if not isinstance(parsed, dict):
            logger.warning("toeic-vocab chunk %s: JSON parse failed", ci)
            raise HTTPException(
                status_code=502,
                detail="Model returned invalid JSON. Try again.",
            )
        terms = parsed.get("terms")
        if not isinstance(terms, list):
            warnings.append(f"Chunk {ci + 1}: missing or invalid 'terms' array; skipped.")
            continue

        for item in terms:
            if not isinstance(item, dict):
                warnings.append(f"Chunk {ci + 1}: skipped non-object term.")
                continue
            w = item.get("word")
            mv = item.get("meaning_vi")
            if not isinstance(w, str) or not w.strip():
                warnings.append(f"Chunk {ci + 1}: skipped term without word.")
                continue
            if not isinstance(mv, str) or not mv.strip():
                warnings.append(f"Chunk {ci + 1}: skipped {w!r} without meaning_vi.")
                continue
            word = w.strip()[:500]
            meaning_vi = mv.strip()[:2000]
            pos, wpos = _normalize_pos(item.get("part_of_speech"))
            if wpos:
                warnings.append(wpos)
            if pos is None:
                pos = "other"
            key = word.lower()
            note_en = item.get("note_en")
            note = None
            if isinstance(note_en, str) and note_en.strip():
                note = note_en.strip()[:500]
            cefr_s, wcef = _normalize_cefr(item.get("cefr"))
            if wcef:
                warnings.append(f"Chunk {ci + 1} {word!r}: {wcef}")
            if not cefr_s:
                cefr_s = "B1"
            diff, wdiff = _parse_difficulty_score(item.get("difficulty_score"))
            if wdiff:
                warnings.append(f"Chunk {ci + 1} {word!r}: {wdiff}")

            entry = {
                "word": word,
                "part_of_speech": pos,
                "meaning_vi": meaning_vi,
                "cefr": cefr_s,
                "difficulty_score": diff,
                "note_en": note,
            }
            if key not in merged:
                merged[key] = entry
            else:
                merged[key] = _term_pick_harder(merged[key], entry)
            if len(merged) >= max_terms + 50:
                break
        if len(merged) >= max_terms + 50:
            break

    items = list(merged.values())
    items.sort(key=lambda x: (-int(x.get("difficulty_score") or 0), -_CEFR_RANK.get(x.get("cefr") or "", 0)))
    items = items[:max_terms]
    if not items and not warnings:
        warnings.append("No terms extracted. Try different text or a smaller excerpt.")

    return {"terms": items, "warnings": warnings, "chunks_processed": len(chunks)}
