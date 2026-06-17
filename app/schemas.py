from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    code: int = 200
    msg: str = "成功"
    data: object | None = None

    @classmethod
    def success(cls, data=None, msg: str = "成功"):
        return cls(code=200, msg=msg, data=data)

    @classmethod
    def error(cls, code: int, msg: str):
        return cls(code=code, msg=msg, data=None)


# ── 认证 ──

class LoginRequest(BaseModel):
    tenantId: str = "000000"
    username: str
    password: str
    rememberMe: bool = False
    code: str | None = None
    uuid: str | None = None
    clientId: str | None = None
    grantType: str = "password"


class CurrentUser(BaseModel):
    user_id: str
    username: str | None = None


# ── 摄像头 ──

class CameraCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    source_url: str = Field(..., min_length=1, max_length=1000)
    suffix: str | None = Field(default=None, max_length=100)
    enabled: bool = True


class CameraUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    source_url: str | None = Field(default=None, min_length=1, max_length=1000)
    suffix: str | None = Field(default=None, max_length=100)
    enabled: bool | None = None


class CameraData(BaseModel):
    camera_id: str
    name: str
    source_url: str
    suffix: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


# ── 检测任务 ──

class DetectionSwitchRequest(BaseModel):
    enabled: bool
    detection_fps: float | None = Field(default=None, ge=0.1, le=30.0)
    conf_threshold: float | None = Field(default=None, ge=0.01, le=1.0)


class BoxSwitchRequest(BaseModel):
    enabled: bool


class TaskParamsRequest(BaseModel):
    detection_fps: float | None = Field(default=None, ge=0.1, le=30.0)
    conf_threshold: float | None = Field(default=None, ge=0.01, le=1.0)


class TaskData(BaseModel):
    camera_id: str
    detection_enabled: bool
    show_boxes: bool
    detection_fps: float
    conf_threshold: float
    status: str
    last_error: str | None
    started_at: datetime | None
    stopped_at: datetime | None
    updated_at: datetime


# ── 告警 ──

class AlertData(BaseModel):
    alert_id: int
    camera_id: str
    camera_name: str | None
    fall_count: int
    detections: list[dict]
    image_width: int | None
    image_height: int | None
    is_read: bool
    created_at: datetime


# ── 检测结果 ──

class DetectionBox(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]
    center: list[float]
    width: float
    height: float


# ── 视频流 ──

class StreamResolveRequest(BaseModel):
    source_url: str = Field(..., min_length=1, max_length=1000)
    suffix: str | None = Field(default=None, max_length=100)
    auto_append_suffix: bool = True


class StreamProbeRequest(StreamResolveRequest):
    timeout_ms: int = 5000


class StreamResolveData(BaseModel):
    source_url: str
    opencv_url: str
    suffix_applied: str | None
