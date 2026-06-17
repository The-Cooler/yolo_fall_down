from pathlib import Path
from ultralytics import YOLO
import os

# 禁用git信息检查
os.environ['ULTRALYTICS_GIT_INFO'] = '0'

def main():
    ROOT = Path(__file__).resolve().parents[1]

    model = YOLO(ROOT / "models/yolov8m.pt")

    results = model.train(
        data=ROOT / "train" / "train.yaml",
        imgsz=640,
        device="cuda",
    )



if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
