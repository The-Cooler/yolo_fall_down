from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.auth import (
    authenticate,
    build_captcha_response,
    build_login_response,
    build_user_info_response,
    create_token,
    decode_token,
    get_user_from_db,
    hash_password,
)
from app.db import SessionLocal
from app.models import User
from app.schemas import LoginRequest

router = APIRouter(tags=["认证"])


@router.get("/auth/code")
async def get_captcha():
    resp = build_captcha_response()
    with SessionLocal() as db:
        resp["registerMode"] = db.query(User).count() == 0
    return JSONResponse(resp)


@router.post("/auth/register")
async def register(request: LoginRequest):
    with SessionLocal() as db:
        existing_count = db.query(User).count()
        if existing_count > 0:
            return JSONResponse({"code": 403, "msg": "系统已初始化，不允许注册"})
        if db.query(User).filter(User.username == request.username).first():
            return JSONResponse({"code": 400, "msg": "用户名已存在"})

        user = User(
            user_id=uuid.uuid4().hex,
            username=request.username,
            password_hash=hash_password(request.password),
            nickname=request.username,
            status="0",
        )
        db.add(user)
        db.commit()
        token = create_token(user.user_id, user.username)
        return JSONResponse(build_login_response(token))


@router.post("/auth/login")
async def login(request: LoginRequest):
    user = authenticate(request.username, request.password)
    if user is None:
        return JSONResponse({"code": 500, "msg": "用户名或密码错误"})
    token = create_token(user.user_id, user.username)
    return JSONResponse(build_login_response(token))


@router.get("/system/user/getInfo")
async def get_user_info(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return JSONResponse({"code": 401, "msg": "缺少 Authorization"}, status_code=401)
    token = auth_header.removeprefix("Bearer ").removeprefix("bearer ")
    try:
        payload = decode_token(token)
    except Exception:
        return JSONResponse({"code": 401, "msg": "登录信息无效"}, status_code=401)
    user_id = payload.get("userId")
    if not user_id:
        return JSONResponse({"code": 401, "msg": "无法识别当前用户"}, status_code=401)
    user = get_user_from_db(user_id)
    if user is None:
        return JSONResponse({"code": 401, "msg": "用户不存在"}, status_code=401)
    return JSONResponse(build_user_info_response(user))
