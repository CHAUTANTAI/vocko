import pytest

from src.answer_match import typo_one_highlight


def test_exact_returns_none():
    assert typo_one_highlight("Hello", "  hello ") is None


def test_substitute():
    h = typo_one_highlight("hello", "hallo")
    assert h == {"start": 1, "end": 2, "kind": "substitute"}


def test_insert():
    h = typo_one_highlight("hello", "heello")
    assert h is not None
    assert h["kind"] == "insert"
    assert h["end"] == h["start"] + 1
    assert "hello" == ("heello"[: h["start"]] + "heello"[h["end"] :])


def test_delete():
    h = typo_one_highlight("hello", "helo")
    # Removing expected[2] (first "l") yields "helo"; caret on user at index 2.
    assert h == {"start": 2, "end": 2, "kind": "delete"}


def test_two_edits_returns_none():
    assert typo_one_highlight("ab", "cd") is None  # two substitutions
    assert typo_one_highlight("ab", "ba") is None  # swap = distance 2


def test_len_diff_two_returns_none():
    assert typo_one_highlight("hi", "hiya") is None
