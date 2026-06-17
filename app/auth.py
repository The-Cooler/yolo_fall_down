from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import jwt
from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import User
from app.schemas import CurrentUser

JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()



def create_token(user_id: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.auth.jwt_expire_hours)
    payload = {
        "userId": user_id,
        "user_name": username,
        "exp": expire,
    }
    return jwt.encode(payload, settings.auth.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.auth.jwt_secret, algorithms=[JWT_ALGORITHM])


def authenticate(username: str, password: str) -> User | None:
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == username).first()
        if user is None:
            return None
        if user.password_hash != hash_password(password):
            return None
        if user.status == "1":
            return None
        return user
    finally:
        session.close()


def get_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少 Authorization")
    token = authorization.removeprefix("Bearer ").removeprefix("bearer ")
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="登录信息无效")
    user_id = payload.get("userId")
    if not user_id:
        raise HTTPException(status_code=401, detail="无法识别当前用户")
    return CurrentUser(user_id=str(user_id), username=payload.get("user_name"))


def get_user_from_db(user_id: str) -> User | None:
    session = SessionLocal()
    try:
        return session.query(User).filter(User.user_id == user_id).first()
    finally:
        session.close()


# ── RuoYi 兼容响应格式 ──

def build_login_response(token: str) -> dict:
    return {
        "code": 200,
        "msg": "操作成功",
        "token": token,
    }


def build_user_info_response(user: User) -> dict:
    return {
        "code": 200,
        "msg": "操作成功",
        "data": {
            "user": {
                "userId": user.user_id,
                "userName": user.username,
                "nickName": user.nickname or user.username,
                "avatar": user.avatar,
                "email": user.email,
                "phonenumber": user.phone,
                "status": user.status,
            }
        },
    }


def build_captcha_response() -> dict:
    return {
        "code": 200,
        "msg": "操作成功",
        "uuid": uuid.uuid4().hex,
        "img": "",
        "captchaEnabled": False,
    }
