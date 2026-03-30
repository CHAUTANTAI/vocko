"""Local flashcard answer matching: single-edit (Levenshtein distance 1) + highlight on user text."""


def typo_one_highlight(expected_raw: str, user_raw: str) -> dict | None:
    """
    If normalized strings (strip + lower) differ by exactly one edit, return half-open
    [start, end) on user_raw.strip() (Python str indices / code points).

    substitute: one char wrong — highlight that char (end = start + 1).
    insert: user has one extra char — highlight that char.
    delete: user missing one char vs expected — start == end at insertion point in user string.
    """
    user_s = (user_raw or "").strip()
    a = (expected_raw or "").strip().lower()
    b = user_s.lower()

    if a == b:
        return None

    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return None

    if la == lb:
        mismatches = [i for i in range(la) if a[i] != b[i]]
        if len(mismatches) != 1:
            return None
        i = mismatches[0]
        return {"start": i, "end": i + 1, "kind": "substitute"}

    if lb == la + 1:
        for j in range(lb):
            if b[:j] + b[j + 1 :] == a:
                return {"start": j, "end": j + 1, "kind": "insert"}
        return None

    # lb == la - 1: one deletion in user relative to expected
    for j in range(la):
        if a[:j] + a[j + 1 :] == b:
            return {"start": j, "end": j, "kind": "delete"}
    return None
