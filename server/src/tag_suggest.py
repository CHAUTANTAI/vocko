"""LLM-assisted tag suggestions for flashcards (find-or-create in tags collection)."""

from __future__ import annotations

import os
import textwrap
from typing import Any

from pymongo.errors import DuplicateKeyError

from .card_helpers import POS_WHITELIST
from .learning_ai import _model_hint, _parse_json_object
from .openrouter_client import chat_completion

MAX_FRONT_LEN = 600
MAX_TAGS_DEFAULT = 6
MAX_TAGS_CAP = 7

# Tags must not duplicate Part of speech (separate card field).
# Do not infer "language of translation" from the back — back is not shown to the model.
_LANGUAGE_SLUGS = frozenset(
    {
        "vietnamese",
        "english",
        "spanish",
        "french",
        "german",
        "italian",
        "portuguese",
        "chinese",
        "japanese",
        "korean",
        "thai",
        "hindi",
        "arabic",
        "russian",
        "polish",
        "dutch",
        "swedish",
        "turkish",
        "indonesian",
        "malay",
        "filipino",
        "tagalog",
        "translation",
        "translate",
        "bilingual",
        "multilingual",
        "foreign-language",
        "second-language",
    }
)

BLOCKED_SUGGESTION_SLUGS = frozenset(POS_WHITELIST) | _LANGUAGE_SLUGS


def _slug_blocked(slug: str) -> bool:
    if not slug:
        return True
    if slug in BLOCKED_SUGGESTION_SLUGS:
        return True
    if slug.startswith("language-") or slug.endswith("-language"):
        return True
    return False


def _model_tag() -> str:
    """Explicit OPENROUTER_MODEL_TAG, else same resolved model as hints (OPENROUTER_MODEL_HINT)."""
    explicit = os.getenv("OPENROUTER_MODEL_TAG", "").strip()
    if explicit:
        return explicit
    return _model_hint()


def suggest_and_upsert_tags(
    db: Any,
    *,
    front: str,
    back: str | None,
    card_type: str,
    max_tags: int,
    slugify_fn,
) -> tuple[list[dict], str | None]:
    """
    Returns (list of { _id str, name, slug, created bool }, error).

    Only **front** is sent to the model; `back` is ignored (no translation-language tags).
    """
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return [], "AI tag suggestions require OPENROUTER_API_KEY on the server"

    _ = back  # API keeps `back` for compatibility; never use for tagging.
    front_t = (front or "").strip()[:MAX_FRONT_LEN]
    if not front_t:
        return [], "front is required"

    n = max(1, min(max_tags or MAX_TAGS_DEFAULT, MAX_TAGS_CAP))
    ct = (card_type or "vocab").strip() or "vocab"

    catalog = list(db.tags.find({}, {"name": 1, "slug": 1}).sort("name", 1))
    cat_lines = [f"- {t['name']} (slug: {t.get('slug', '')})" for t in catalog[:200]]
    catalog_block = "\n".join(cat_lines) if cat_lines else "(no existing tags)"

    system = textwrap.dedent(
        f"""
        You assign short **topic / skill** tags for a flashcard app (weak-area grouping for review).

        Reply with ONLY a JSON object, no markdown:
        {{ "tags": [ {{ "name": "Short Label", "is_new": false }} ] }}

        Rules:
        - You ONLY see the card **front** (English/prompt side). Do not guess from any translation or answer text.
        - Suggest at most {n} tags.
        - Prefer reusing an existing tag from the catalog when it fits (is_new false).
        - Set is_new true only when nothing in the catalog fits; new names: 1–4 words, Title Case.
        - Tags = domain, register, word-formation, exam skill, confusable concepts — e.g. Business, Formal,
          Confusable, Idioms, Multi-word expressions, or tense/aspect *topics* (e.g. Present tense) when clearly
          a teaching theme — not a single-word POS label.
        - NEVER output: any **part of speech** as a tag (noun, verb, adjective, adverb, preposition, pronoun,
          determiner, conjunction, interjection, etc.) — the app has a separate Part of speech field.
        - NEVER output **language names** or translation-related labels (Vietnamese, English, Translation, …).
        - If the front is a single common English word, prefer broad learning tags (e.g. Formal, Business)
          or morphology (e.g. Abstract nouns) only when clearly justified; otherwise reuse catalog topics.
        """
    ).strip()

    user = textwrap.dedent(
        f"""
        Card type: {ct}
        Max tags: {n}

        Existing tag catalog:
        {catalog_block}

        Front text only (use this alone to choose tags):
        {front_t}

        JSON only.
        """
    ).strip()

    raw, err = chat_completion(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=_model_tag(),
        temperature=0.35,
    )
    if err:
        return [], err
    obj = _parse_json_object(raw or "")
    if not obj or not isinstance(obj.get("tags"), list):
        return [], "Model did not return valid JSON with a tags array"

    seen_slugs: set[str] = set()
    out: list[dict] = []
    for item in obj["tags"]:
        if len(out) >= n:
            break
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name or len(name) > 80:
            continue
        slug = slugify_fn(name)
        if not slug or slug in seen_slugs or _slug_blocked(slug):
            continue
        seen_slugs.add(slug)

        existing = db.tags.find_one({"slug": slug})
        if existing:
            tid = existing["_id"]
            out.append(
                {
                    "_id": str(tid),
                    "name": existing.get("name", name),
                    "slug": slug,
                    "created": False,
                }
            )
            continue

        try:
            ins = db.tags.insert_one({"name": name, "slug": slug})
            tid = ins.inserted_id
            out.append({"_id": str(tid), "name": name, "slug": slug, "created": True})
        except DuplicateKeyError:
            existing2 = db.tags.find_one({"slug": slug})
            if not existing2:
                continue
            tid = existing2["_id"]
            out.append(
                {
                    "_id": str(tid),
                    "name": existing2.get("name", name),
                    "slug": slug,
                    "created": False,
                }
            )

    return out, None
