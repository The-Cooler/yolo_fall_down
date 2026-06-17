from __future__ import annotations

import cv2
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response, StreamingResponse

from app.detector import YOLODetector
from app.schemas import (
    BaseResponse,
    StreamProbeRequest,
    StreamResolveData,
    StreamResolveRequest,
)
from app.shared_capture import CaptureManager
from app.stream_reader import StreamReader, StreamUrlResolver

router = APIRouter(prefix="/streams", tags=["视频流"])


@router.post("/resolve", response_model=BaseResponse)
def resolve_stream(request: StreamResolveRequest):
    try:
        resolved = StreamUrlResolver.resolve(
            request.source_url, request.suffix, request.auto_append_suffix
        )
    except ValueError as exc:
        return BaseResponse.error(400, str(exc))
    return BaseResponse.success(
        StreamResolveData(
            source_url=resolved.source_url,
            opencv_url=resolved.opencv_url,
            suffix_applied=resolved.suffix_applied,
        ).model_dump(),
        msg="解析成功",
    )


@router.post("/probe", response_model=BaseResponse)
def probe_stream(request: StreamProbeRequest):
    try:
        resolved = StreamUrlResolver.resolve(
            request.source_url, request.suffix, request.auto_append_suffix
        )
        capture = StreamReader.open_capture(
            resolved.opencv_url, request.timeout_ms
        )
        try:
            if not capture.isOpened():
                return BaseResponse.success({
                    "source_url": resolved.source_url,
                    "opencv_url": resolved.opencv_url,
                    "suffix_applied": resolved.suffix_applied,
                    "opened": False,
                    "message": "OpenCV 无法打开该视频源",
                })
            ok, frame = capture.read()
            if not ok or frame is None:
                return BaseResponse.success({
                    "source_url": resolved.source_url,
                    "opencv_url": resolved.opencv_url,
                    "suffix_applied": resolved.suffix_applied,
                    "opened": False,
                    "message": "OpenCV 已打开视频源，但无法读取第一帧",
                })
            width = (
                int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                or frame.shape[1]
                or None
            )
            height = (
                int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                or frame.shape[0]
                or None
            )
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0) or None
            frame_count = (
                int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0) or None
            )
            return BaseResponse.success({
                "source_url": resolved.source_url,
                "opencv_url": resolved.opencv_url,
                "suffix_applied": resolved.suffix_applied,
                "opened": True,
                "width": width,
                "height": height,
                "fps": fps,
                "frame_count": frame_count,
                "message": "OpenCV 已成功打开该视频源",
            })
        finally:
            capture.release()
    except ValueError as exc:
        return BaseResponse.error(400, str(exc))


@router.post("/snapshot")
def snapshot_stream(request: StreamResolveRequest):
    try:
        resolved = StreamUrlResolver.resolve(
            request.source_url, request.suffix, request.auto_append_suffix
        )
        image = StreamReader.read_jpeg_frame(resolved.opencv_url)
    except ValueError as exc:
        return BaseResponse.error(400, str(exc))
    return Response(content=image, media_type="image/jpeg")


@router.get("/mjpeg")
def mjpeg_stream(
    source_url: str = Query(..., min_length=1),
    suffix: str | None = Query(default=None),
    auto_append_suffix: bool = Query(default=True),
):
    try:
        resolved = StreamUrlResolver.resolve(
            source_url, suffix, auto_append_suffix
        )
    except ValueError as exc:
        return BaseResponse.error(400, str(exc))
    try:
        shared = CaptureManager.acquire(resolved.opencv_url)
    except RuntimeError as exc:
        return BaseResponse.error(400, str(exc))
    try:
        first_frame = shared.read()
        if first_frame is None:
            CaptureManager.release(resolved.opencv_url)
            return BaseResponse.error(400, "OpenCV 无法从视频源读取画面")
        return StreamingResponse(
            StreamReader.mjpeg_frames_from_shared(shared, first_frame, resolved.opencv_url),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except ValueError as exc:
        return BaseResponse.error(400, str(exc))


# ── 检测端点 ──

router_detect = APIRouter(prefix="/detect", tags=["目标检测"])


@router_detect.post("/frame")
async def detect_frame(request: Request):
    conf_threshold = float(
        request.query_params.get("conf_threshold", 0.25)
    )
    content_type = (
        (request.headers.get("content-type") or "")
        .split(";", 1)[0]
        .strip()
        .lower()
    )
    if content_type not in {
        "image/jpeg",
        "image/png",
        "application/octet-stream",
    }:
        return BaseResponse.error(400, "请求体必须是 JPEG/PNG 图片字节")
    try:
        result = YOLODetector.detect(await request.body(), conf_threshold)
        return BaseResponse.success(result, msg="检测成功")
    except ValueError as exc:
        return BaseResponse.error(400, str(exc))
    except FileNotFoundError as exc:
        return BaseResponse.error(500, str(exc))
    except RuntimeError as exc:
        return BaseResponse.error(501, str(exc))