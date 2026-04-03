"""Headword normalization; full checks require en_core_web_sm."""

import pytest

from src.toeic_lemma import build_spacy_doc, normalize_vocab_headword, surface_preserve_set


def test_surface_preserve_contains_sales():
    assert "sales" in surface_preserve_set()


def test_preserve_sales_without_doc():
    assert normalize_vocab_headword("sales", None).lower() == "sales"


def test_spacy_goals_and_sales_if_model_installed():
    try:
        import spacy

        spacy.load("en_core_web_sm")
    except Exception:
        pytest.skip("en_core_web_sm not available")
    passage = (
        "Their sales team set ambitious goals for Q3. She offers help daily. "
        "Employees waited in long lines for rave reviews in the coming months."
    )
    doc = build_spacy_doc(passage)
    assert doc is not None
    assert normalize_vocab_headword("goals", doc) == "goal"
    assert normalize_vocab_headword("offers", doc) == "offer"
    assert normalize_vocab_headword("sales", doc) == "sales"
    assert normalize_vocab_headword("word of mouth", doc) == "word of mouth"
    assert normalize_vocab_headword("employees", doc) == "employee"
    assert normalize_vocab_headword("rave reviews", doc) == "rave review"
    assert normalize_vocab_headword("long lines", doc) == "long line"
    # spaCy may map VBG "coming" → "come"; we only guarantee plural headnouns collapse
    assert normalize_vocab_headword("coming months", doc) in ("come month", "coming month")
