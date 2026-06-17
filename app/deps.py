from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import FallCamera, FallTask
from app.schemas import CurrentUser


def current_user_dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user


def get_user_camera(camera_id: str, user: CurrentUser, db: Session) -> FallCamera:
    camera = db.get(FallCamera, camera_id)
    if camera is None or camera.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="摄像头不存在")
    return camera


def get_user_task(camera_id: str, user: CurrentUser, db: Session) -> FallTask:
    task = db.get(FallTask, camera_id)
    if task is None or task.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="检测任务不存在")
    return task
