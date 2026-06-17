from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth import decode_token
from app.config import settings
from app.db import SessionLocal
from app.models import FallCamera
from app.ws_manager import ws_manager

router = APIRouter(tags=["实时推送"])


@router.websocket("/ws/fall")
async def fall_ws(websocket: WebSocket):
    camera_id = websocket.query_params.get("camera_id")
    project_id = websocket.query_params.get("project_id")
    authorization = (
        websocket.headers.get("authorization")
        or websocket.query_params.get("authorization")
    )
    token = websocket.query_params.get("token")
    if authorization is None and token:
        authorization = (
            token if token.lower().startswith("bearer ") else f"Bearer {token}"
        )

    if not camera_id:
        await websocket.close(code=1008, reason="缺少 camera_id")
        return
    if project_id != settings.auth.project_id:
        await websocket.close(code=1008, reason="project_id 无效")
        return
    if not authorization:
        await websocket.close(code=1008, reason="缺少 Authorization")
        return

    try:
        token_str = authorization.removeprefix("Bearer ").removeprefix("bearer ")
        payload = decode_token(token_str)
        user_id = payload.get("userId")
        if not user_id:
            await websocket.close(code=1008, reason="登录信息无效")
            return
    except Exception:
        await websocket.close(code=1008, reason="登录信息无效")
        return

    with SessionLocal() as db:
        camera = db.get(FallCamera, camera_id)
        if camera is None or camera.user_id != user_id:
            await websocket.close(code=1008, reason="摄像头不存在")
            return

    ws_manager.bind_loop()
    await ws_manager.connect(camera_id, user_id, websocket)
    try:
        await websocket.send_json({
            "type": "task_status",
            "camera_id": camera_id,
            "status": "connected",
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(camera_id, user_id, websocket)
