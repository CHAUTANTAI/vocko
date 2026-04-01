import pytest

from src.study_records import canonical_match_type


@pytest.mark.parametrize(
    "legacy,correct,llm_used,expected",
    [
        ("exact", True, False, "exact"),
        ("typo_one", True, False, "typo"),
        ("llm", True, True, "synonym"),
        ("none", False, False, "none"),
        ("none", False, True, "wrong_meaning"),
    ],
)
def test_canonical_match_type(legacy, correct, llm_used, expected):
    assert canonical_match_type(legacy, correct=correct, llm_used=llm_used) == expected
