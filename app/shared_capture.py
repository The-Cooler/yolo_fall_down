from __future__ import annotations

import threading
import time

import cv2

from app.config import settings


class SharedCapture:
    """共享视频捕获 —— 后台线程持续读帧，多消费者通过 read() 获取最新帧副本"""

    def __init__(self, opencv_url: str):
        self._url = opencv_url
        self._cap: cv2.VideoCapture | None = None
        self._frame = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._failures = 0

    # ── 生命周期 ──

    def start(self):
        self._open_capture()
        # 同步读取首帧，确保 acquire 返回后立即可用
        ok, frame = self._cap.read()
        if not ok or frame is None:
            self._cap.release()
            self._cap = None
            raise RuntimeError(f"SharedCapture 无法读取首帧: {self._url}")
        self._frame = frame
        self._stop_event.clear()
        self._failures = 0
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _open_capture(self):
        if self._cap is not None:
            self._cap.release()
        self._cap = cv2.VideoCapture()
        self._cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, settings.stream.open_timeout_ms)
        self._cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, settings.stream.read_timeout_ms)
        self._cap.open(self._url)
        if not self._cap.isOpened():
            self._cap.release()
            self._cap = None
            raise RuntimeError(f"SharedCapture 无法打开视频源: {self._url}")

    # ── 后台读取 ──

    def _read_loop(self):
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                if self._cap is None:
                    break
                ok, frame = self._cap.read()
                if ok and frame is not None:
                    with self._lock:
                        self._frame = frame
                    self._failures = 0
                else:
                    self._failures += 1
                    print(f"[SharedCapture] 读帧失败 (连续 {self._failures} 次)")
                    if self._failures >= 30:
                        print("[SharedCapture] 连续失败过多，尝试重连…")
                        try:
                            self._open_capture()
                            self._failures = 0
                            print("[SharedCapture] 重连成功")
                        except Exception as exc:
                            print(f"[SharedCapture] 重连失败: {exc}")
                            self._stop_event.wait(2)
            except Exception as exc:
                self._failures += 1
                print(f"[SharedCapture] 读帧异常: {exc}")
                if self._failures >= 30:
                    try:
                        self._open_capture()
                        self._failures = 0
                    except Exception:
                        pass
            elapsed = time.monotonic() - started
            # 按配置帧率限速，但至少等 10ms 避免空转
            frame_interval = 1 / settings.stream.mjpeg_fps
            sleep_time = max(frame_interval - elapsed, 0.01)
            self._stop_event.wait(sleep_time)

    # ── 消费者接口 ──

    def read(self):
        """获取最新帧副本，无新帧时返回 None"""
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()


# ── 全局管理器 ──

class CaptureManager:
    """按 opencv_url 去重，引用计数管理 SharedCapture 生命周期"""

    _instances: dict[str, SharedCapture] = {}
    _refcount: dict[str, int] = {}
    _lock = threading.Lock()

    @classmethod
    def acquire(cls, opencv_url: str) -> SharedCapture:
        with cls._lock:
            if opencv_url in cls._instances:
                cls._refcount[opencv_url] += 1
                return cls._instances[opencv_url]
            cap = SharedCapture(opencv_url)
            cap.start()
            cls._instances[opencv_url] = cap
            cls._refcount[opencv_url] = 1
            return cap

    @classmethod
    def release(cls, opencv_url: str):
        with cls._lock:
            if opencv_url not in cls._instances:
                return
            cls._refcount[opencv_url] -= 1
            if cls._refcount[opencv_url] <= 0:
                cls._instances[opencv_url].stop()
                del cls._instances[opencv_url]
                del cls._refcount[opencv_url]
