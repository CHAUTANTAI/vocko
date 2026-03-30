import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .api_auth import router as auth_router
from .api_decks import router as decks_router
from .api_learning import router as learning_router
from .db import db
from .rate_limit import limiter

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
if _raw == "*":
    _origins = ["*"]
else:
    _origins = [o.strip() for o in _raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(decks_router)
app.include_router(learning_router)

@app.on_event("startup")
def startup_db():
    # Kiểm tra kết nối MongoDB khi khởi động
    db.command("ping")
