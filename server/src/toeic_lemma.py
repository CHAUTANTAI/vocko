"""Context-aware headword normalization (goals→goal) via spaCy; preserve sales-type lexemes."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DIR = Path(__file__).resolve().parent.parent / "data"

# Surface forms we never replace with a shorter lemma (often plural = lexicalized sense).
_SURFACE_PRESERVE: frozenset[str] | None = None

_nlp = None
_nlp_unavailable = False

_LEAD_STRIP = "\"'([{<"
_TRAIL_STRIP = "\")]}>.,;:!?"


def _strip_token_edges(token: str) -> str:
    s = token.strip()
    while s and s[0] in _LEAD_STRIP:
        s = s[1:].lstrip()
    while s and s[-1] in _TRAIL_STRIP:
        s = s[:-1].rstrip()
    return s.strip()


def _default_preserve() -> frozenset[str]:
    return frozenset(
        {
            "sales",
            "news",
            "politics",
            "economics",
            "statistics",
            "mathematics",
            "physics",
            "linguistics",
            "athletics",
            "acoustics",
            "logistics",
            "headquarters",
            "means",
            "goods",
            "clothes",
            "jeans",
            "pants",
            "shorts",
            "glasses",
            "scissors",
            "pliers",
            "tweezers",
            "binoculars",
            "thanks",
            "congratulations",
            "remains",
            "customs",
            "arms",
            "damages",
            "earnings",
            "savings",
            "findings",
            "belongings",
            "surroundings",
            "outskirts",
            "dregs",
            "amends",
            "series",
            "species",
            "works",
            "crossroads",
            "gallows",
            "measles",
            "shambles",
            "whereabouts",
        }
    )


def _load_preserve_file() -> frozenset[str]:
    path = _DIR / "toeic_lemma_preserve.txt"
    if not path.is_file():
        return frozenset()
    extra: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip().lower()
        if s and not s.startswith("#"):
            extra.add(s)
    return frozenset(extra)


def surface_preserve_set() -> frozenset[str]:
    global _SURFACE_PRESERVE
    if _SURFACE_PRESERVE is None:
        _SURFACE_PRESERVE = _default_preserve() | _load_preserve_file()
    return _SURFACE_PRESERVE


def get_nlp():
    """Lazy-load spaCy English model; None if spacy or en_core_web_sm missing."""
    global _nlp, _nlp_unavailable
    if _nlp_unavailable:
        return None
    if _nlp is not None:
        return _nlp
    try:
        import spacy
    except ImportError:
        logger.info("spacy not installed; headword normalization skipped")
        _nlp_unavailable = True
        return None
    try:
        _nlp = spacy.load("en_core_web_sm")
    except OSError:
        logger.info("en_core_web_sm not found; run: python -m spacy download en_core_web_sm")
        _nlp_unavailable = True
        return None
    return _nlp


def build_spacy_doc(text: str):
    """Parse full cleaned passage once for context-sensitive lemmas."""
    nlp = get_nlp()
    if nlp is None or not (text or "").strip():
        return None
    try:
        return nlp(text[:1_000_000])
    except Exception as e:
        logger.warning("spaCy parse failed: %s", e)
        return None


def _lemma_single_surface(term: str, doc) -> str:
    """One surface word (no spaces); may include hyphens e.g. co-workers."""
    term = (term or "").strip()
    if not term:
        return term
    core = _strip_token_edges(term)
    if not core:
        return term.lower()

    tl = core.lower()
    preserve = surface_preserve_set()
    if tl in preserve:
        if doc is not None:
            for tok in doc:
                if tok.text.lower() == tl:
                    return tok.text.lower()
        return tl

    nlp = get_nlp()
    if nlp is None:
        return core

    if doc is not None:
        for tok in doc:
            if tok.text.lower() != tl:
                continue
            if tok.pos_ == "PROPN":
                return tok.text
            lem = (tok.lemma_ or "").strip()
            if not lem:
                return tok.text.lower()
            ll = lem.lower()
            if ll in preserve or tok.text.lower() in preserve:
                return tok.text.lower()
            return ll

    t2 = nlp(core)
    if not len(t2):
        return core
    tok = t2[0]
    if tok.pos_ == "PROPN":
        return core
    lem = (tok.lemma_ or "").strip()
    if not lem:
        return tl
    ll = lem.lower()
    if ll in preserve or tl in preserve:
        return tl
    return ll


def _normalize_phrase(phrase: str, doc) -> str:
    """
    Lemmatize each word using a mini spaCy parse of the phrase so POS is local
    (e.g. rave→ADJ in 'rave reviews', reviews→review). Falls back to full-doc scan if token count mismatches.
    """
    parts = [p for p in phrase.split() if p]
    if not parts:
        return phrase.strip()
    cores = []
    for p in parts:
        c = _strip_token_edges(p)
        cores.append(c if c else p.strip())
    nlp = get_nlp()
    if nlp is None:
        return " ".join(_lemma_single_surface(c, doc) for c in cores)

    joined = " ".join(cores)
    preserve = surface_preserve_set()
    try:
        pdoc = nlp(joined[:500])
    except Exception:
        return " ".join(_lemma_single_surface(c, doc) for c in cores)

    if len(pdoc) != len(cores):
        return " ".join(_lemma_single_surface(c, doc) for c in cores)

    out: list[str] = []
    for tok in pdoc:
        tl = tok.text.lower()
        if tok.pos_ == "PROPN":
            out.append(tok.text)
            continue
        if tl in preserve:
            out.append(tok.text.lower())
            continue
        lem = (tok.lemma_ or "").strip()
        if not lem:
            out.append(tok.text.lower())
            continue
        ll = lem.lower()
        if ll in preserve or tl in preserve:
            out.append(tok.text.lower())
        else:
            out.append(ll)
    return " ".join(out)


def normalize_vocab_headword(term: str, doc) -> str:
    """
    Map inflected forms to dictionary headwords using passage context when possible.
    Multi-word phrases: mini-parse the whole phrase with spaCy (better than matching each word in the full doc).
    Single tokens: full-document match, then isolated parse. Hyphenated compounds: one token (co-workers).
    """
    term = (term or "").strip()
    if not term:
        return term
    if " " in term:
        return _normalize_phrase(term, doc)
    return _lemma_single_surface(term, doc)
