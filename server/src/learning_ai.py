"""OpenRouter-backed hint generation and approximate answer grading."""

import json
import os
import re
import textwrap

from .openrouter_client import chat_completion

# Default: OpenRouter free auto-router (see openrouter_client.MODEL_OPENROUTER_FREE + X-OpenRouter-Only-Free).
# Override with OPENROUTER_MODEL_HINT / OPENROUTER_MODEL_GRADE for explicit model ids.
DEFAULT_MODEL_HINT = "openrouter/free"
DEFAULT_MODEL_GRADE = "openrouter/free"


def _model_hint() -> str:
    return (
        os.getenv("OPENROUTER_MODEL_HINT", DEFAULT_MODEL_HINT).strip()
        or DEFAULT_MODEL_HINT
    )


def _model_grade() -> str:
    return (
        os.getenv("OPENROUTER_MODEL_GRADE", DEFAULT_MODEL_GRADE).strip()
        or DEFAULT_MODEL_GRADE
    )


def _parse_json_object(text: str) -> dict | None:
    t = text.strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", t)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    brace = re.search(r"\{[\s\S]*\}", t)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass
    return None


_HINT_SYSTEM = textwrap.dedent(
    """
You grade flashcard answers.

Return ONLY JSON:
{
  "result": "correct" | "almost" | "incorrect",
  "grade": number from 0 to 1,
  "match_type": "exact" | "typo" | "synonym" | "partial" | "none",
  "note": "short explanation"
}

Rules:
- Be tolerant to minor typos, missing accents, or small spelling errors.
- If the answer clearly matches the meaning, mark as correct even with typos.
- If very close but not perfect, mark as "almost".
- Only mark "incorrect" if meaning is wrong or unrelated.

Guidelines:
- Typo (abondon vs abandon) → correct, grade ~0.9
- Missing accents (tranh chap vs tranh chấp) → correct
- Slight misspelling (cháp vs chấp) → almost
- Wrong meaning → incorrect

Be fair and learner-friendly.
"""
).strip()


def generate_hint(
    front_text: str, back_text: str | None = None
) -> tuple[str | None, str | None]:
    """Return (hint, error). error is None on success."""
    front = (front_text or "").strip()
    if not front:
        return None, "Card front text is empty"
    back_display = (
        back_text or ""
    ).strip() or "(empty — use only the front; do not invent a specific answer)"
    user = textwrap.dedent(
        f"""
        Flashcard front:
        {front}

        Flashcard back (hidden from learner):
        {back_display}

        Task:
        Write a hint to help the learner recall the back content from the front.

        Do NOT reveal:
        - the answer
        - first letter
        - spelling hints (unless clearly appropriate)

        Write the hint now.
        """
    ).strip()
    raw, err = chat_completion(
        [
            {"role": "system", "content": _HINT_SYSTEM},
            {"role": "user", "content": user},
        ],
        model=_model_hint(),
        temperature=0.5,
    )
    if err:
        return None, err
    if not raw:
        return None, "Empty hint from model"
    hint = raw.strip()
    return (hint, None) if hint else (None, "Empty hint from model")


def grade_answer(
    front_text: str,
    expected_back: str,
    user_response: str,
) -> tuple[bool, str | None]:
    """Return (correct, optional short note). On parse failure, (False, None)."""
    system = (
        "You grade flashcard free-text answers. Reply with ONLY a JSON object, no markdown: "
        '{"correct": true or false, "note": "optional short reason for the learner"}. '
        "Accept minor typos and clear synonyms if they match the intended meaning of the expected answer. "
        "Be strict if the answer is wrong or unrelated."
    )
    user = (
        f"Front/prompt:\n{front_text}\n\n"
        f"Expected answer (back):\n{expected_back}\n\n"
        f"Learner answer:\n{user_response}\n\n"
        "JSON only."
    )
    raw, err = chat_completion(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=_model_grade(),
        temperature=0.2,
    )
    if err or not raw:
        return False, None
    obj = _parse_json_object(raw)
    if not obj or "correct" not in obj:
        return False, None
    correct = bool(obj.get("correct"))
    note = obj.get("note")
    note_s = str(note).strip()[:500] if note is not None else None
    return correct, note_s or None


def generate_explain(
    *,
    front_text: str,
    expected_back: str,
    card_type: str | None,
    tag_names: list[str],
    recent_incorrect: int,
) -> tuple[str | None, str | None]:
    """Short coach explanation (Phase 4). Returns (text, error)."""
    front = (front_text or "").strip()
    back = (expected_back or "").strip()
    if not front:
        return None, "Card front is empty"
    tags_s = ", ".join(tag_names) if tag_names else "(none)"
    ct = (card_type or "vocab").strip()
    system = textwrap.dedent(
        """
        You are a concise language tutor. Explain in 2–4 short sentences why the expected answer fits,
        and one tip to remember it. Do not repeat the learner's wrong answer verbatim.
        Reply in plain text, no JSON.
        """
    ).strip()
    user = textwrap.dedent(
        f"""
        Card type: {ct}
        Tags: {tags_s}
        Recent incorrect attempts on this card (same user): {recent_incorrect}

        Front: {front}
        Expected back: {back}

        Give a helpful mini-explanation.
        """
    ).strip()
    raw, err = chat_completion(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=_model_hint(),
        temperature=0.4,
    )
    if err:
        return None, err
    if not raw:
        return None, "Empty explanation from model"
    text = raw.strip()
    return (text, None) if text else (None, "Empty explanation from model")
