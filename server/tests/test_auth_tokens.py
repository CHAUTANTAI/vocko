"""JWT refresh helpers (no MongoDB)."""
import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-tests-please")

from src.utils import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    REFRESH_TOKEN_EXPIRE_DAYS_SHORT,
    create_refresh_token,
    decode_token,
    refresh_token_ttl_days_from_payload,
)


def test_create_refresh_token_default_rt_days():
    t = create_refresh_token({"user_id": "abc"})
    p = decode_token(t)
    assert p is not None
    assert p["type"] == "refresh"
    assert p["rt_days"] == REFRESH_TOKEN_EXPIRE_DAYS
    assert p["user_id"] == "abc"


def test_create_refresh_token_short_ttl():
    t = create_refresh_token({"user_id": "x"}, refresh_days=REFRESH_TOKEN_EXPIRE_DAYS_SHORT)
    p = decode_token(t)
    assert p is not None
    assert p["rt_days"] == REFRESH_TOKEN_EXPIRE_DAYS_SHORT


def test_create_refresh_token_clamps_high():
    t = create_refresh_token({"user_id": "x"}, refresh_days=999)
    p = decode_token(t)
    assert p["rt_days"] == REFRESH_TOKEN_EXPIRE_DAYS


def test_create_refresh_token_clamps_low():
    t = create_refresh_token({"user_id": "x"}, refresh_days=0)
    p = decode_token(t)
    assert p["rt_days"] == REFRESH_TOKEN_EXPIRE_DAYS_SHORT


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({}, REFRESH_TOKEN_EXPIRE_DAYS),
        ({"rt_days": 7}, REFRESH_TOKEN_EXPIRE_DAYS_SHORT),
        ({"rt_days": 30}, REFRESH_TOKEN_EXPIRE_DAYS),
        ({"rt_days": "bad"}, REFRESH_TOKEN_EXPIRE_DAYS),
        ({"rt_days": 999}, REFRESH_TOKEN_EXPIRE_DAYS),
    ],
)
def test_refresh_token_ttl_days_from_payload(payload, expected):
    assert refresh_token_ttl_days_from_payload(payload) == expected
