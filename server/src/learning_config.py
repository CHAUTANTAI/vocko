"""Roadmap Phase 3 — smart queue & difficulty thresholds (tunable)."""

# build_learning_queue_smart: (weak, new, easy) — roadmap 70 / 20 / 10
SMART_QUEUE_WEIGHTS = (0.7, 0.2, 0.1)

# avg_last_5_grades (0–5) → difficulty_bucket
DIFFICULTY_EASY_MIN = 3.5
DIFFICULTY_MEDIUM_MIN = 2.5

# "easy" pool: due cards with ease at least this (stable items)
EASY_POOL_MIN_EASE = 2.2

# Max tags returned for weak-by-tag aggregation
WEAK_TAG_AGG_LIMIT = 24

# Rolling window for avg_last_5_grades on user_progress
RECENT_GRADES_MAX = 5
