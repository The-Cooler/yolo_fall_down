from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import current_user_dep, get_user_camera
from app.detection_runner import task_manager
from app.models import FallCamera, FallTask
from app.schemas import (
    BaseResponse,
    CameraCreateRequest,
    CameraData,
    CameraUpdateRequest,
    CurrentUser,
)

router = APIRouter(prefix="/cameras", tags=["摄像头"])


def _normalize_source_url(source_url: str) -> str:
    value = source_url.strip()
    lowered = value.lower()
    for scheme in ("rtsp", "rtmp", "http", "https", "file"):
        prefix = f"{scheme} "
        if lowered.startswith(prefix):
            rest = value[len(prefix):].strip()
            if rest.lower().startswith(f"{scheme}://"):
                return rest
    return value


def _camera_to_data(camera: FallCamera) -> CameraData:
    return CameraData(
        camera_id=camera.camera_id,
        name=camera.name,
        source_url=camera.source_url,
        suffix=camera.suffix,
        enabled=camera.enabled,
        created_at=camera.created_at,
        updated_at=camera.updated_at,
    )


@router.post("", response_model=BaseResponse)
def create_camera(
    request: CameraCreateRequest,
    user: CurrentUser = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    camera = FallCamera(
        camera_id=uuid4().hex,
        user_id=user.user_id,
        name=request.name,
        source_url=_normalize_source_url(request.source_url),
        suffix=request.suffix,
        enabled=request.enabled,
    )
    task = FallTask(
        camera_id=camera.camera_id,
        user_id=user.user_id,
        detection_enabled=False,
        show_boxes=False,
        detection_fps=settings.detection.default_fps,
        conf_threshold=settings.detection.default_conf_threshold,
        status="stopped",
    )
    db.add(camera)
    db.add(task)
    db.commit()
    db.refresh(camera)
    return BaseResponse.success(
        _camera_to_data(camera).model_dump(), msg="摄像头创建成功"
    )


@router.get("", response_model=BaseResponse)
def list_cameras(
    user: CurrentUser = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    cameras = (
        db.query(FallCamera)
        .filter(FallCamera.user_id == user.user_id)
        .order_by(FallCamera.created_at.desc())
        .all()
    )
    return BaseResponse.success([_camera_to_data(c).model_dump() for c in cameras])


@router.patch("/{camera_id}", response_model=BaseResponse)
def update_camera(
    camera_id: str,
    request: CameraUpdateRequest,
    user: CurrentUser = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    camera = get_user_camera(camera_id, user, db)
    data = request.model_dump(exclude_unset=True)
    if "source_url" in data and data["source_url"] is not None:
        data["source_url"] = _normalize_source_url(data["source_url"])
    for key, value in data.items():
        setattr(camera, key, value)
    if data.get("enabled") is False:
        task = db.get(FallTask, camera_id)
        if task is not None:
            task.detection_enabled = False
            task.status = "stopped"
            task.stopped_at = datetime.now()
        task_manager.stop_task(camera_id)
    db.commit()
    db.refresh(camera)
    return BaseResponse.success(
        _camera_to_data(camera).model_dump(), msg="摄像头更新成功"
    )
