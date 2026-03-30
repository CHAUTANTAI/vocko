from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel
from bson import ObjectId
from bson.errors import InvalidId
from .db import db
from .rate_limit import limiter
from .utils import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
import datetime

router = APIRouter()

class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: str

class SigninRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/auth/signup")
@limiter.limit("10/minute")
def signup(request: Request, req: SignupRequest):
    if db.users.find_one({"email": req.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = {
        "email": req.email,
        "display_name": req.display_name,
        "password_hash": hash_password(req.password),
        "created_at": datetime.datetime.utcnow(),
        "settings": {},
    }
    result = db.users.insert_one(user)
    user["_id"] = str(result.inserted_id)
    access_token = create_access_token({"user_id": user["_id"], "email": user["email"]})
    refresh_token = create_refresh_token({"user_id": user["_id"]})
    return {"user": {"id": user["_id"], "display_name": user["display_name"], "email": user["email"]}, "access_token": access_token, "refresh_token": refresh_token}

@router.post("/auth/signin")
@limiter.limit("20/minute")
def signin(request: Request, req: SigninRequest):
    user = db.users.find_one({"email": req.email})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user_id = str(user["_id"])
    access_token = create_access_token({"user_id": user_id, "email": user["email"]})
    refresh_token = create_refresh_token({"user_id": user_id})
    return {"user": {"id": user_id, "display_name": user["display_name"], "email": user["email"]}, "access_token": access_token, "refresh_token": refresh_token}

@router.post("/auth/refresh")
@limiter.limit("30/minute")
def refresh(request: Request, req: RefreshRequest):
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload["user_id"]
    try:
        oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    access_token = create_access_token({"user_id": user_id, "email": user["email"]})
    refresh_token = create_refresh_token({"user_id": user_id})
    return {"access_token": access_token, "refresh_token": refresh_token}
