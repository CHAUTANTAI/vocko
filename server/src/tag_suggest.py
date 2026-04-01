"""LLM-assisted tag suggestions for flashcards (find-or-create in tags collection)."""

from __future__ import annotations

import logging
import os
import textwrap
from typing import Any

from .card_helpers import POS_WHITELIST
from .learning_ai import _model_hint, _parse_json_object
from .openrouter_client import chat_completion

logger = logging.getLogger(__name__)

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
    part_of_speech: str | None = None,
    slugify_fn,
) -> tuple[list[dict], list[dict], str | None]:
    """
    Returns (matched_tags, pending_new, error).

    matched_tags: existing catalog only, each { _id, name, slug }.
    pending_new: names with no row yet, each { name, slug } — created when the card is saved, not here.

    Only **front** is sent to the model; `back` is ignored (no translation-language tags).
    """
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return [], "AI tag suggestions require OPENROUTER_API_KEY on the server"

    _ = back  # API keeps `back` for compatibility; never use for tagging.
    front_t = (front or "").strip()[:MAX_FRONT_LEN]
    if not front_t:
        return [], [], "front is required"

    n = max(1, min(max_tags or MAX_TAGS_DEFAULT, MAX_TAGS_CAP))
    ct = (card_type or "vocab").strip() or "vocab"
    pos = (part_of_speech or "").strip() if ct == "vocab" else ""
    pos_line = (
        f"Learner part of speech (metadata only; never output this or any single-word POS as a tag): {pos}"
        if pos
        else "Learner part of speech: (not set)"
    )

    catalog = list(db.tags.find({}, {"name": 1, "slug": 1}).sort("name", 1))
    cat_lines = [f"- {t['name']} (slug: {t.get('slug', '')})" for t in catalog[:200]]
    catalog_block = "\n".join(cat_lines) if cat_lines else "(no existing tags)"

    type_hint = ""
    if ct == "sentence":
        type_hint = (
            "This is a **sentence** card: prefer multi-word topic tags such as Time Expression, Fixed Phrase, "
            "Everyday English, Formal Register, Contrast, or TOEIC-style skill buckets — never a one-word POS "
            "like Preposition or Noun (those are blocked)."
        )
    elif ct == "grammar":
        type_hint = (
            "This is a **grammar** card: prefer tags like Word Order, Tense Agreement, Article Use, "
            "Prepositional Phrase (multi-word label), Conditionals — not bare POS words."
        )
    else:
        type_hint = "This is a **vocab** card: topic/skill tags (collocation sense as a phrase is OK, e.g. Business Collocations)."

    system = textwrap.dedent(
        f"""
        You assign short **topic / skill** tags for a TOEIC-oriented flashcard app (weak-area grouping).

        Reply with ONLY a JSON object, no markdown:
        {{ "tags": [ {{ "name": "Short Label", "is_new": false }} ] }}

        Rules:
        - You ONLY use the **front** English text below for meaning. Ignore any translation.
        - You MUST output between 1 and {n} tags whenever the front is non-empty. Never return an empty "tags" array.
        - Prefer reusing an existing tag from the catalog when it fits (is_new false).
        - Set is_new true only when nothing in the catalog fits; names: 1–4 words, Title Case.
        - New names are not saved to the database until the learner saves the card; the API only returns them.
        - Use **multi-word topic labels** when the front is a phrase (e.g. "Time Expression", "Same Day Usage").
        - NEVER output a tag whose slug would be a single **part of speech** word (noun, verb, preposition, …)
          or the word collocation alone — the app stores POS separately.
        - NEVER output **language names** or translation-related labels (Vietnamese, English, Translation, …).
        - {type_hint}
        """
    ).strip()

    user = textwrap.dedent(
        f"""
        Card type: {ct}
        {pos_line}
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
        temperature=0.4,
    )
    if err:
        return [], [], err
    obj = _parse_json_object(raw or "")
    if not obj or not isinstance(obj.get("tags"), list):
        return [], [], "Model did not return valid JSON with a tags array"

    raw_tags = obj["tags"]
    seen_slugs: set[str] = set()
    matched: list[dict] = []
    pending_new: list[dict] = []
    rejected: list[tuple[str, str, str]] = []
    for item in raw_tags:
        if len(matched) + len(pending_new) >= n:
            break
        if not isinstance(item, dict):
            rejected.append(("", "", "not_an_object"))
            continue
        name = str(item.get("name") or "").strip()
        if not name or len(name) > 80:
            rejected.append((name, "", "empty_or_long_name"))
            continue
        slug = slugify_fn(name)
        if not slug or slug in seen_slugs:
            rejected.append((name, slug or "(empty)", "duplicate_or_empty_slug"))
            continue
        if _slug_blocked(slug):
            rejected.append((name, slug, "blocked_pos_or_language_slug"))
            continue
        seen_slugs.add(slug)

        existing = db.tags.find_one({"slug": slug})
        if existing:
            tid = existing["_id"]
            matched.append(
                {
                    "_id": str(tid),
                    "name": existing.get("name", name),
                    "slug": slug,
                }
            )
            continue

        pending_new.append({"name": name, "slug": slug})

    if not matched and not pending_new:
        if raw_tags:
            logger.warning(
                "tag_suggest: model returned %d tag(s) but all were dropped (rejected=%s); raw_snip=%s",
                len(raw_tags),
                rejected[:12],
                (raw or "")[:400],
            )
            return [], [], "No suitable tags were found for this card."
        logger.warning(
            "tag_suggest: model returned empty tags array; front=%r card_type=%s; raw_snip=%s",
            front_t[:80],
            ct,
            (raw or "")[:400],
        )
        return [], [], "No suitable tags were found for this card."

    return matched, pending_new, None
