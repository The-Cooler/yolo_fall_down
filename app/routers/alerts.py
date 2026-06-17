from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user_dep
from app.models import FallAlert
from app.schemas import AlertData, BaseResponse, CurrentUser

router = APIRouter(prefix="/alerts", tags=["告警"])


def _alert_to_data(alert: FallAlert) -> AlertData:
    return AlertData(
        alert_id=alert.alert_id,
        camera_id=alert.camera_id,
        camera_name=alert.camera_name,
        fall_count=alert.fall_count,
        detections=alert.detections,
        image_width=alert.image_width,
        image_height=alert.image_height,
        is_read=alert.is_read,
        created_at=alert.created_at,
    )


@router.get("", response_model=BaseResponse)
def list_alerts(
    camera_id: str | None = Query(default=None),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    user: CurrentUser = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    query = db.query(FallAlert).filter(FallAlert.user_id == user.user_id)
    if camera_id:
        query = query.filter(FallAlert.camera_id == camera_id)
    if unread_only:
        query = query.filter(FallAlert.is_read.is_(False))
    alerts = query.order_by(FallAlert.created_at.desc()).limit(limit).all()
    return BaseResponse.success([_alert_to_data(a).model_dump() for a in alerts])


@router.post("/{alert_id}/read", response_model=BaseResponse)
def mark_alert_read(
    alert_id: int,
    user: CurrentUser = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    alert = db.get(FallAlert, alert_id)
    if alert is None or alert.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="告警不存在")
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return BaseResponse.success(
        _alert_to_data(alert).model_dump(), msg="告警已读"
    )


@router.delete("/{alert_id}", response_model=BaseResponse)
def delete_alert(
    alert_id: int,
    user: CurrentUser = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    alert = db.get(FallAlert, alert_id)
    if alert is None or alert.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="告警不存在")
    db.delete(alert)
    db.commit()
    return BaseResponse.success(None, msg="告警已删除")
