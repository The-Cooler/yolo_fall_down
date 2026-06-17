from __future__ import annotations

import threading

import cv2
import numpy as np
from ultralytics import YOLO

from app.config import settings
from app.schemas import DetectionBox


class YOLODetector:
    _model: YOLO | None = None
    _lock = threading.Lock()

    @classmethod
    def load_model(cls) -> YOLO:
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    model_path = settings.model_path
                    if not model_path.exists():
                        raise FileNotFoundError(f"未找到模型路径: {model_path}")
                    cls._model = YOLO(str(model_path))
        return cls._model

    @classmethod
    def detect(cls, raw: bytes, conf_threshold: float = 0.25) -> dict:
        if not raw:
            raise ValueError("图片内容为空")
        np_buffer = np.frombuffer(raw, np.uint8)
        source = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
        if source is None:
            raise ValueError("文件必须是可解码的图片")

        model = cls.load_model()
        results = model.predict(source, conf=conf_threshold, verbose=False)
        result = results[0]
        height, width = source.shape[:2]

        boxes = result.boxes
        detections: list[dict] = []
        if boxes is not None and len(boxes) > 0:
            names = result.names or {}
            xyxy = boxes.xyxy.cpu().numpy()
            conf = boxes.conf.cpu().numpy()
            cls_ids = boxes.cls.cpu().numpy().astype(int)
            for box, confidence, class_id in zip(xyxy, conf, cls_ids):
                x1, y1, x2, y2 = [round(float(v), 2) for v in box.tolist()]
                w = round(x2 - x1, 2)
                h = round(y2 - y1, 2)
                detections.append(
                    DetectionBox(
                        class_id=int(class_id),
                        class_name=str(names.get(int(class_id), class_id)),
                        confidence=round(float(confidence), 4),
                        bbox=[x1, y1, x2, y2],
                        center=[round(x1 + w / 2, 2), round(y1 + h / 2, 2)],
                        width=w,
                        height=h,
                    ).model_dump()
                )

        fall_count = sum(1 for d in detections if d["class_name"].lower() == "fall")
        inference_ms = sum(float(v) for v in result.speed.values())

        return {
            "image_width": width,
            "image_height": height,
            "inference_ms": round(inference_ms, 3),
            "detections": detections,
            "fall_count": fall_count,
            "is_fall": fall_count > 0,
        }
