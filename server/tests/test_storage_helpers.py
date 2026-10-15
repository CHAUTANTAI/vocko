"""Unit tests for storage helpers (no MongoDB)."""
from bson import Binary, ObjectId

from src.api_storage import _safe_filename, _serialize


def test_safe_filename_strips_path_and_controls():
    assert _safe_filename(r"..\..\evil\name.pdf") == "name.pdf"
    assert _safe_filename("a\x00b.txt") == "ab.txt"
    assert _safe_filename("") == "file"
    assert _safe_filename(None) == "file"


def test_serialize_omits_binary_and_flags_file():
    doc = {
        "_id": ObjectId(),
        "title": "Note",
        "contents": "hello",
        "filename": "a.bin",
        "content_type": "application/octet-stream",
        "file_size": 3,
        "binary_data": Binary(b"abc"),
        "created_at": None,
        "updated_at": None,
    }
    out = _serialize(doc, include_contents=True)
    assert out["has_file"] is True
    assert out["contents"] == "hello"
    assert "binary_data" not in out
    listed = _serialize(doc, include_contents=False)
    assert "contents" not in listed
