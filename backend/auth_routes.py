import os
import re
import sqlite3
import threading
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from backend.services import auth_service as auth

router = APIRouter(prefix="/api/auth")
COOKIE = "onair_session"
attempts = {}
lock = threading.Lock()


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


def check_origin(request):
    origin = request.headers.get("origin")
    allowed = {"http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"}
    if request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin not in allowed):
        raise HTTPException(403, "허용되지 않은 요청입니다.")


def limit(request):
    check_origin(request)
    key = request.client.host if request.client else "local"
    now = time.monotonic()
    with lock:
        for expired in [item for item, values in attempts.items() if not values or now - values[-1] > 60]:
            del attempts[expired]
        values = [value for value in attempts.get(key, []) if now - value < 60]
        if len(values) >= 10:
            raise HTTPException(429, "요청이 많습니다. 잠시 후 다시 시도해주세요.")
        attempts[key] = values + [now]


@router.get("/me")
def me(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"user": auth.current_user(request.cookies.get(COOKIE))}


@router.post("/register")
def register(payload: Credentials, request: Request):
    limit(request)
    username = payload.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,32}", username):
        raise HTTPException(422, "아이디는 영문 소문자, 숫자, 밑줄 3~32자로 입력해주세요.")
    try:
        auth.register(username, payload.password)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "이미 사용 중인 아이디입니다.")
    return {"ok": True}


@router.post("/login")
def login(payload: Credentials, request: Request, response: Response):
    limit(request)
    user = auth.authenticate(payload.username.strip().lower(), payload.password)
    if not user:
        raise HTTPException(401, "아이디 또는 비밀번호를 확인해주세요.")
    response.set_cookie(COOKIE, auth.create_session(user["id"]), max_age=7 * 86400, httponly=True, samesite="strict", secure=os.environ.get("ONAIR_SECURE_COOKIE") == "1")
    response.headers["Cache-Control"] = "no-store"
    return {"user": {"id": user["id"], "username": user["username"]}}


@router.post("/logout")
def logout(request: Request, response: Response):
    check_origin(request)
    auth.logout(request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE)
    return {"ok": True}


@router.post("/guest")
def guest_login(request: Request, response: Response):
    limit(request)
    response.headers["Cache-Control"] = "no-store"
    existing = auth.current_user(request.cookies.get(COOKIE))
    if existing:
        return {"user": existing}
    token, user = auth.create_guest_session()
    response.set_cookie(COOKIE, token, max_age=86400, httponly=True, samesite="strict", secure=os.environ.get("ONAIR_SECURE_COOKIE") == "1")
    return {"user": user}
