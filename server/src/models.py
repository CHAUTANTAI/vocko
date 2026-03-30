from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class User(BaseModel):
    id: str
    email: str
    display_name: str
    password_hash: str
    created_at: datetime
    settings: dict

class Deck(BaseModel):
    id: str
    owner_id: str
    title: str
    description: Optional[str]
    language_pair: dict
    card_count: int
    sample_cards: list
    settings: dict
    created_at: datetime

class Flashcard(BaseModel):
    id: str
    deck_id: str
    front: dict
    back: dict
    media: Optional[list]
    order_index: int
    tags: Optional[list]
    created_at: datetime
    deleted: Optional[bool]

class UserProgress(BaseModel):
    id: str
    user_id: str
    card_id: str
    deck_id: str
    ease_factor: float
    repetition: int
    interval_days: int
    next_due_at: datetime
    last_reviewed_at: datetime
    total_reviews: int
    correct_count: int
    streak: int
    suspended: Optional[bool]

class LearningSession(BaseModel):
    id: str
    user_id: str
    deck_id: str
    mode: str
    started_at: datetime
    ended_at: Optional[datetime]
    summary: dict
    events_count: int
    events_sample: Optional[list]
