from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

import cv2

from app.config import settings
from app.db import SessionLocal
from app.detector import YOLODetector
from app.models import FallAlert, FallCamera, FallTask
from app.shared_capture import CaptureManager
from app.stream_reader import StreamUrlResolver
from app.ws_manager import ws_manager


class DetectionTaskRunner:
    def __init__(self, camera_id: str) -> None:
        self.camera_id = camera_id
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        opencv_url = None
        try:
            with SessionLocal() as db:
                camera, task = self._load_camera_and_task(db)
                self._mark_running(db, task)
                resolved = StreamUrlResolver.resolve(camera.source_url, camera.suffix)
                opencv_url = resolved.opencv_url

            shared = CaptureManager.acquire(opencv_url)
            try:
                frame = self._read_frame_with_retry(shared)
                if frame is None:
                    raise RuntimeError("无法从视频源读取画面")

                self._publish_status("running")
                while not self.stop_event.is_set():
                    started = time.monotonic()

                    with SessionLocal() as db:
                        camera, task = self._load_camera_and_task(db)
                        # 两个开关都关了才停止 runner
                        if not task.detection_enabled and not task.show_boxes:
                            break
                        if not camera.enabled:
                            raise RuntimeError("摄像头已禁用")
                        data = self._detect_frame(frame, task.conf_threshold)
                        self._handle_detection(db, camera, task, data)
                        frame_interval = 1 / max(task.detection_fps, 0.1)

                    elapsed = time.monotonic() - started
                    if elapsed < frame_interval:
                        self.stop_event.wait(frame_interval - elapsed)
                    frame = self._read_frame_with_retry(shared)
                    if frame is None:
                        raise RuntimeError("无法从视频源读取画面")

                with SessionLocal() as db:
                    _, task = self._load_camera_and_task(db)
                    self._mark_stopped(db, task)
                self._publish_status("stopped")
            finally:
                CaptureManager.release(opencv_url)

        except Exception as exc:
            self._mark_error(str(exc))
        finally:
            task_manager.remove_runner(self.camera_id, self)

    def _load_camera_and_task(self, db):
        camera = db.get(FallCamera, self.camera_id)
        if camera is None:
            raise RuntimeError("摄像头不存在")
        task = db.get(FallTask, self.camera_id)
        if task is None:
            raise RuntimeError("检测任务不存在")
        return camera, task

    def _detect_frame(self, frame, conf_threshold: float) -> dict:
        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            raise RuntimeError("视频帧 JPEG 编码失败")
        return YOLODetector.detect(buf.tobytes(), conf_threshold)

    @staticmethod
    def _read_frame_with_retry(shared) -> any:
        """从 SharedCapture 读取一帧，带重试"""
        for _ in range(settings.stream.mjpeg_read_retry_count + 1):
            frame = shared.read()
            if frame is not None:
                return frame
            time.sleep(settings.stream.mjpeg_read_retry_delay_ms / 1000)
        return None

    def _handle_detection(self, db, camera: FallCamera, task: FallTask, data: dict) -> None:
        now = datetime.now()
        detections = data.get("detections") or []
        fall_detections = [
            d for d in detections
            if str(d.get("class_name", "")).lower() == "fall"
        ]

        if task.show_boxes:
            ws_manager.publish(camera.camera_id, camera.user_id, {
                "type": "bbox_update",
                "camera_id": camera.camera_id,
                "image_width": data.get("image_width"),
                "image_height": data.get("image_height"),
                "detections": detections,
                "timestamp": now.isoformat(),
            })

        # 仅当检测开关开启时才生成摔倒告警
        if not task.detection_enabled:
            return

        if not data.get("is_fall"):
            return

        recent = (
            db.query(FallAlert)
            .filter(
                FallAlert.camera_id == camera.camera_id,
                FallAlert.created_at >= now - timedelta(
                    seconds=settings.detection.alert_cooldown_seconds
                ),
            )
            .order_by(FallAlert.created_at.desc())
            .first()
        )
        if recent is not None:
            return

        alert = FallAlert(
            camera_id=camera.camera_id,
            user_id=camera.user_id,
            camera_name=camera.name,
            fall_count=int(data.get("fall_count") or len(fall_detections)),
            detections=fall_detections or detections,
            image_width=data.get("image_width"),
            image_height=data.get("image_height"),
            is_read=False,
            created_at=now,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        ws_manager.publish(camera.camera_id, camera.user_id, {
            "type": "fall_alert",
            "alert_id": alert.alert_id,
            "camera_id": camera.camera_id,
            "camera_name": camera.name,
            "fall_count": alert.fall_count,
            "detections": alert.detections,
            "image_width": alert.image_width,
            "image_height": alert.image_height,
            "created_at": alert.created_at.isoformat(),
        })

    def _mark_running(self, db, task: FallTask) -> None:
        task.status = "running"
        task.last_error = None
        task.started_at = datetime.now()
        task.stopped_at = None
        db.commit()

    def _mark_stopped(self, db, task: FallTask) -> None:
        task.status = "stopped"
        task.stopped_at = datetime.now()
        db.commit()

    def _mark_error(self, message: str) -> None:
        with SessionLocal() as db:
            task = db.get(FallTask, self.camera_id)
            if task is not None:
                task.status = "error"
                task.last_error = message
                task.stopped_at = datetime.now()
                db.commit()
        user_id = self._get_user_id()
        if user_id:
            ws_manager.publish(self.camera_id, user_id, {
                "type": "error",
                "camera_id": self.camera_id,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            })

    def _publish_status(self, status: str) -> None:
        user_id = self._get_user_id()
        if user_id is None:
            return
        ws_manager.publish(self.camera_id, user_id, {
            "type": "task_status",
            "camera_id": self.camera_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        })

    def _get_user_id(self) -> str | None:
        with SessionLocal() as db:
            camera = db.get(FallCamera, self.camera_id)
            return camera.user_id if camera is not None else None


class DetectionTaskManager:
    def __init__(self) -> None:
        self._runners: dict[str, DetectionTaskRunner] = {}
        self._lock = threading.Lock()

    def start_task(self, camera_id: str) -> None:
        with self._lock:
            runner = self._runners.get(camera_id)
            if runner is not None and runner.thread.is_alive():
                return
            runner = DetectionTaskRunner(camera_id)
            self._runners[camera_id] = runner
            runner.start()

    def stop_task(self, camera_id: str) -> None:
        with self._lock:
            runner = self._runners.get(camera_id)
            if runner is not None:
                runner.stop()

    def stop_all(self) -> None:
        with self._lock:
            runners = list(self._runners.values())
        for runner in runners:
            runner.stop()

    def remove_runner(self, camera_id: str, runner: DetectionTaskRunner) -> None:
        with self._lock:
            current = self._runners.get(camera_id)
            if current is runner:
                self._runners.pop(camera_id, None)


task_manager = DetectionTaskManager()
