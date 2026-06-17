from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import current_user_dep, get_user_camera, get_user_task
from app.detection_runner import task_manager
from app.schemas import (
    BaseResponse,
    BoxSwitchRequest,
    CurrentUser,
    DetectionSwitchRequest,
    TaskData,
    TaskParamsRequest,
)

router = APIRouter(prefix="/tasks", tags=["检测任务"])


def _task_to_data(task) -> TaskData:
    return TaskData(
        camera_id=task.camera_id,
        detection_enabled=task.detection_enabled,
        show_boxes=task.show_boxes,
        detection_fps=task.detection_fps,
        conf_threshold=task.conf_threshold,
        status=task.status,
        last_error=task.last_error,
        started_at=task.started_at,
        stopped_at=task.stopped_at,
        updated_at=task.updated_at,
    )


@router.get("/{camera_id}", response_model=BaseResponse)
def get_task(
    camera_id: str,
    user: CurrentUser = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    task = get_user_task(camera_id, user, db)
    return BaseResponse.success(_task_to_data(task).model_dump())


@router.post("/{camera_id}/detection", response_model=BaseResponse)
def switch_detection(
    camera_id: str,
    request: DetectionSwitchRequest,
    user: CurrentUser = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    camera = get_user_camera(camera_id, user, db)
    if request.enabled and not camera.enabled:
        return BaseResponse.error(400, "摄像头已禁用")
    task = get_user_task(camera_id, user, db)
    task.detection_enabled = request.enabled
    if request.detection_fps is not None:
        task.detection_fps = request.detection_fps
    if request.conf_threshold is not None:
        task.conf_threshold = request.conf_threshold
    if request.enabled:
        task.status = "starting"
        task.last_error = None
        task.started_at = datetime.now()
        task.stopped_at = None
    else:
        task.status = "stopped"
        task.stopped_at = datetime.now()
    db.commit()
    db.refresh(task)
    if request.enabled:
        task_manager.start_task(camera_id)
    elif not task.show_boxes:
        # 仅当显示框也关了才停 runner
        task_manager.stop_task(camera_id)
    return BaseResponse.success(
        _task_to_data(task).model_dump(), msg="检测开关已更新"
    )


@router.post("/{camera_id}/boxes", response_model=BaseResponse)
def switch_boxes(
    camera_id: str,
    request: BoxSwitchRequest,
    user: CurrentUser = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    get_user_camera(camera_id, user, db)
    task = get_user_task(camera_id, user, db)
    task.show_boxes = request.enabled
    db.commit()
    db.refresh(task)
    if request.enabled:
        # 开启显示框时确保 runner 在运行
        task_manager.start_task(camera_id)
    elif not task.detection_enabled:
        # 两个开关都关了才停 runner
        task_manager.stop_task(camera_id)
    return BaseResponse.success(
        _task_to_data(task).model_dump(), msg="框选显示开关已更新"
    )


@router.put("/{camera_id}/params", response_model=BaseResponse)
def update_task_params(
    camera_id: str,
    request: TaskParamsRequest,
    user: CurrentUser = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    get_user_camera(camera_id, user, db)
    task = get_user_task(camera_id, user, db)
    if request.detection_fps is not None:
        task.detection_fps = request.detection_fps
    if request.conf_threshold is not None:
        task.conf_threshold = request.conf_threshold
    db.commit()
    db.refresh(task)
    return BaseResponse.success(
        _task_to_data(task).model_dump(), msg="检测参数已更新"
    )
