from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import cv2

from app.config import settings

KNOWN_STREAM_EXTENSIONS = {
    ".flv", ".m3u8", ".mp4", ".mov", ".avi", ".mkv", ".webm", ".ts", ".mjpeg", ".mjpg",
}


@dataclass(frozen=True)
class ResolvedStreamUrl:
    source_url: str
    opencv_url: str
    suffix_applied: str | None


class StreamUrlResolver:
    @staticmethod
    def resolve(
        source_url: str,
        suffix: str | None = None,
        auto_append_suffix: bool = True,
    ) -> ResolvedStreamUrl:
        normalized = StreamUrlResolver._normalize_source_url(source_url)
        if not normalized:
            raise ValueError("source_url 不能为空")
        if suffix is not None:
            suffix = suffix.strip() or None
        if not auto_append_suffix or suffix is None:
            return ResolvedStreamUrl(normalized, normalized, None)
        resolved = StreamUrlResolver._append_suffix_if_needed(normalized, suffix)
        applied = suffix if resolved != normalized else None
        return ResolvedStreamUrl(normalized, resolved, applied)

    @staticmethod
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

    @staticmethod
    def _append_suffix_if_needed(source_url: str, suffix: str) -> str:
        split = urlsplit(source_url)
        path_extension = Path(split.path).suffix.lower()
        if path_extension in KNOWN_STREAM_EXTENSIONS:
            return source_url
        if suffix.startswith("?"):
            return StreamUrlResolver._append_query_suffix(split, suffix)
        if suffix.startswith("&"):
            query = split.query + suffix if split.query else suffix[1:]
            return urlunsplit((split.scheme, split.netloc, split.path, query, split.fragment))
        if suffix.startswith(".") or suffix.startswith("/"):
            path = split.path.rstrip("/") + suffix
            return urlunsplit((split.scheme, split.netloc, path, split.query, split.fragment))
        separator = "" if split.path.endswith("/") else "/"
        path = f"{split.path}{separator}{suffix}"
        return urlunsplit((split.scheme, split.netloc, path, split.query, split.fragment))

    @staticmethod
    def _append_query_suffix(split, suffix: str) -> str:
        suffix_query = suffix[1:]
        existing = dict(parse_qsl(split.query, keep_blank_values=True))
        incoming = dict(parse_qsl(suffix_query, keep_blank_values=True))
        existing.update(incoming)
        return urlunsplit((
            split.scheme, split.netloc, split.path,
            urlencode(existing, doseq=True), split.fragment,
        ))


class StreamReader:
    @staticmethod
    def open_capture(opencv_url: str, timeout_ms: int | None = None) -> cv2.VideoCapture:
        capture = cv2.VideoCapture()
        capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms or settings.stream.open_timeout_ms)
        capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, settings.stream.read_timeout_ms)
        capture.open(opencv_url)
        return capture

    @staticmethod
    def read_jpeg_frame(opencv_url: str) -> bytes:
        capture = StreamReader.open_capture(opencv_url)
        try:
            if not capture.isOpened():
                raise ValueError("OpenCV 无法打开该视频源")
            ok, frame = capture.read()
            if not ok or frame is None:
                raise ValueError("无法从该视频源读取画面")
            return StreamReader._encode_jpeg(frame)
        finally:
            capture.release()

    @staticmethod
    def mjpeg_frames_from_capture(
        capture: cv2.VideoCapture,
        first_frame=None,
    ) -> Iterator[bytes]:
        frame_interval = 1 / settings.stream.mjpeg_fps
        try:
            if not capture.isOpened():
                raise ValueError("OpenCV 无法打开该视频源")
            if first_frame is not None:
                jpeg = StreamReader._encode_jpeg(first_frame)
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            while True:
                started = time.monotonic()
                frame = StreamReader._read_frame_with_retry(capture)
                if frame is None:
                    break
                jpeg = StreamReader._encode_jpeg(frame)
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                elapsed = time.monotonic() - started
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
        finally:
            capture.release()

    @staticmethod
    def mjpeg_frames_from_shared(shared, first_frame, opencv_url: str) -> Iterator[bytes]:
        """从 SharedCapture 读取帧并生成 MJPEG 流，退出时自动释放引用"""
        from app.shared_capture import CaptureManager

        frame_interval = 1 / settings.stream.mjpeg_fps
        try:
            jpeg = StreamReader._encode_jpeg(first_frame)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            while True:
                started = time.monotonic()
                frame = shared.read()
                if frame is None:
                    # 瞬时读取失败不中断流，短暂等待后重试
                    time.sleep(0.1)
                    continue
                jpeg = StreamReader._encode_jpeg(frame)
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                elapsed = time.monotonic() - started
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
        finally:
            CaptureManager.release(opencv_url)

    @staticmethod
    def _read_frame_with_retry(capture: cv2.VideoCapture):
        for attempt in range(settings.stream.mjpeg_read_retry_count + 1):
            ok, frame = capture.read()
            if ok and frame is not None:
                return frame
            if attempt < settings.stream.mjpeg_read_retry_count:
                time.sleep(settings.stream.mjpeg_read_retry_delay_ms / 1000)
        return None

    @staticmethod
    def _encode_jpeg(frame) -> bytes:
        ok, buf = cv2.imencode(
            ".jpg", frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), settings.stream.jpeg_quality],
        )
        if not ok:
            raise ValueError("视频帧 JPEG 编码失败")
        return buf.tobytes()
