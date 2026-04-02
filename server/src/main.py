import logging
import os

from fastapi import FastAPI

logger = logging.getLogger("vocko.openrouter")
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .api_auth import router as auth_router
from .api_decks import router as decks_router
from .api_import import router as import_router
from .api_learning import router as learning_router
from .api_tags import router as tags_router
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
app.include_router(import_router)
app.include_router(learning_router)
app.include_router(tags_router)

@app.on_event("startup")
def startup_db():
    # Kiểm tra kết nối MongoDB khi khởi động (tắt bằng SKIP_DB_PING=1 khi debug deploy)
    if os.getenv("SKIP_DB_PING", "").strip().lower() in ("1", "true", "yes"):
        return
    db.command("ping")


@app.on_event("startup")
def startup_log_openrouter_models():
    """Log env + resolved model ids so deploy matches OpenRouter activity (hint/grade vs tag suggest)."""
    hint_env = os.getenv("OPENROUTER_MODEL_HINT", "")
    grade_env = os.getenv("OPENROUTER_MODEL_GRADE", "")
    tag_env = os.getenv("OPENROUTER_MODEL_TAG", "")
    import_env = os.getenv("OPENROUTER_MODEL_IMPORT", "")
    logger.info(
        "OPENROUTER_MODEL_HINT env raw: %r (empty=%s)",
        hint_env,
        not hint_env.strip(),
    )
    logger.info(
        "OPENROUTER_MODEL_GRADE env raw: %r (empty=%s)",
        grade_env,
        not grade_env.strip(),
    )
    logger.info(
        "OPENROUTER_MODEL_TAG env raw: %r (empty=%s) — if empty, tag suggest follows HINT",
        tag_env,
        not tag_env.strip(),
    )
    logger.info(
        "OPENROUTER_MODEL_IMPORT env raw: %r (empty=%s) — if empty, uses HINT model",
        import_env,
        not import_env.strip(),
    )
    from .api_import import _model_import
    from .learning_ai import _model_grade, _model_hint
    from .tag_suggest import _model_tag

    logger.info(
        "OpenRouter resolved: hint=%r grade=%r tag_suggest=%r import=%r",
        _model_hint(),
        _model_grade(),
        _model_tag(),
        _model_import(),
    )
