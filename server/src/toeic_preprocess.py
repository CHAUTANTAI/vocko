"""Clean TOEIC paste text, dedupe tokens, drop stopwords and basic A1–A2 words before AI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

_DIR = Path(__file__).resolve().parent.parent / "data"

# TOEIC placeholder / line-break noise: [1], --[1]--, —[2]—, -[3]-, etc.
_PLACEHOLDER_PATTERNS = [
    re.compile(r"--\s*\[\s*(\d+)\s*\]\s*--", re.I),
    re.compile(r"[—–]\s*\[\s*(\d+)\s*\]\s*[—–]"),
    re.compile(r"-\s*\[\s*(\d+)\s*\]\s*-"),
    re.compile(r"\[\s*(\d+)\s*\]"),
    re.compile(r"\(\s*(\d+)\s*\)"),  # occasional (1) markers
]

# Long runs of dashes used as separators
_DASH_RUN = re.compile(r"[—–\-]{2,}")

# Token: letters + optional internal apostrophe / hyphen (e.g. don't, co-workers)
_TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?(?:-[A-Za-z]+)*")


def _load_lines(filename: str) -> frozenset[str]:
    path = _DIR / filename
    if not path.is_file():
        return frozenset()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip().lower()
        if s and not s.startswith("#"):
            out.add(s)
    return frozenset(out)


_STOPWORDS_CACHE: frozenset[str] | None = None
_BASIC_CACHE: frozenset[str] | None = None


def stopwords_set() -> frozenset[str]:
    global _STOPWORDS_CACHE
    if _STOPWORDS_CACHE is None:
        loaded = _load_lines("toeic_stopwords.txt")
        _STOPWORDS_CACHE = loaded if loaded else _FALLBACK_STOPWORDS
    return _STOPWORDS_CACHE


def basic_words_set() -> frozenset[str]:
    global _BASIC_CACHE
    if _BASIC_CACHE is None:
        loaded = _load_lines("toeic_basic_words.txt")
        _BASIC_CACHE = loaded if loaded else _FALLBACK_BASIC
    return _BASIC_CACHE


def clean_toeic_text(raw: str) -> str:
    """Remove TOEIC bracket/dash placeholders, collapse noise punctuation, normalize whitespace."""
    t = raw or ""
    for pat in _PLACEHOLDER_PATTERNS:
        t = pat.sub(" ", t)
    t = _DASH_RUN.sub(" ", t)
    # Replace most punctuation with space (keep word-internal apostrophe handled at tokenize)
    t = re.sub(r"[^\w\s']", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def tokenize_words(text: str) -> list[str]:
    return _TOKEN_RE.findall(text or "")


def unique_tokens_preserve_order(tokens: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tok in tokens:
        key = tok.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(tok)
    return out


def filter_stopwords(tokens: Iterable[str], stop: frozenset[str] | None = None) -> list[str]:
    sw = stop if stop is not None else stopwords_set()
    return [t for t in tokens if t.lower() not in sw]


def filter_basic_words(tokens: Iterable[str], basic: frozenset[str] | None = None) -> list[str]:
    bw = basic if basic is not None else basic_words_set()
    return [t for t in tokens if t.lower() not in bw]


def preprocess_for_toeic_ai(raw_text: str) -> tuple[str, list[str], dict[str, int | bool]]:
    """
    Returns:
      cleaned_text: passage after noise removal (for model context)
      candidates: unique tokens after dedupe → stopwords only (basic A1–A2 filter is NOT applied
        here so the model gets richer hints; single-token junk is still dropped after AI via api_import)
      stats: small counters for API/debug
    """
    cleaned = clean_toeic_text(raw_text)
    raw_tokens = tokenize_words(cleaned)
    unique = unique_tokens_preserve_order(raw_tokens)
    no_stop = filter_stopwords(unique)
    candidates = no_stop
    stats: dict[str, int | bool] = {
        "raw_token_count": len(raw_tokens),
        "unique_after_dedupe": len(unique),
        "after_stopwords": len(no_stop),
        "candidates_after_basic": len(candidates),
        "candidates_is_empty": len(candidates) == 0,
    }
    return cleaned, candidates, stats


# Fallback if data files are missing (subset; prefer shipping full txt in server/data/)
_FALLBACK_STOPWORDS = frozenset(
    """
    a an the and or but if so as at by for from in into of on to with without
    i you he she it we they me him her us them my your his its our their mine yours
    this that these those what which who whom whose when where why how
    be am is are was were been being have has had having do does did doing done
    will would shall should can could may might must
    not no nor yes all any some every each both few more most other such own same
    than then there here just only very too also back even still again once
    up down out off over under again further once
    get got go went come came make made take took give gave see saw know knew think thought
    say said tell asked want use find work seem feel try leave call keep let begin seem
    help show hear play run move live believe hold bring happen write provide sit stand lose
    pay meet include continue set learn lead understand watch follow stop create speak read
    spend grow open walk win offer remember love consider appear buy wait die send expect
    build stay fall cut reach kill remain suggest raise pass sell require report like
    """.split()
)

_FALLBACK_BASIC = frozenset(
    """
    monday tuesday wednesday thursday friday saturday sunday am pm
    one two three four five six seven eight nine ten first second last next new old long
    big small large little high low good bad new old same different right left
    day week month year time today tomorrow morning afternoon evening night
    place home work school shop store food water money book hand eye year way
    man woman child people person family friend company business office job work team
    city town country world area room door window table seat line
    menu item items open close hot cold full empty long short
    fitness health lunch dinner breakfast break meal eat drink
    """.split()
)
