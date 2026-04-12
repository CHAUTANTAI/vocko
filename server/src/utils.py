import os
import jwt
import datetime
import bcrypt

SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
REFRESH_TOKEN_EXPIRE_DAYS_SHORT = 7


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, refresh_days: int | None = None):
    days = REFRESH_TOKEN_EXPIRE_DAYS if refresh_days is None else int(refresh_days)
    if days < REFRESH_TOKEN_EXPIRE_DAYS_SHORT:
        days = REFRESH_TOKEN_EXPIRE_DAYS_SHORT
    if days > REFRESH_TOKEN_EXPIRE_DAYS:
        days = REFRESH_TOKEN_EXPIRE_DAYS
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh", "rt_days": days})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def refresh_token_ttl_days_from_payload(payload: dict) -> int:
    raw = payload.get("rt_days")
    if raw is None:
        return REFRESH_TOKEN_EXPIRE_DAYS
    try:
        d = int(raw)
    except (TypeError, ValueError):
        return REFRESH_TOKEN_EXPIRE_DAYS
    if d == REFRESH_TOKEN_EXPIRE_DAYS_SHORT:
        return REFRESH_TOKEN_EXPIRE_DAYS_SHORT
    if d == REFRESH_TOKEN_EXPIRE_DAYS:
        return REFRESH_TOKEN_EXPIRE_DAYS
    return REFRESH_TOKEN_EXPIRE_DAYS


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
