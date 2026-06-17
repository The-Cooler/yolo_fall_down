import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VIDEO_PATH = PROJECT_ROOT / "data" / "fall.mp4"
PORT = 9999

_process: subprocess.Popen | None = None


def start():
    global _process
    kwargs = dict(
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    _process = subprocess.Popen(
        [
            "ffmpeg",
            "-stream_loop", "-1",
            "-re",
            "-i", str(VIDEO_PATH),
            "-an",
            "-c:v", "mjpeg",
            "-q:v", "5",
            "-listen", "1",
            "-multiple_requests", "1",
            "-f", "mpjpeg",
            f"http://127.0.0.1:{PORT}",
        ],
        **kwargs,
    )
    print(f"测试视频: http://127.0.0.1:{PORT}")


def stop():
    global _process
    if _process is not None:
        _process.terminate()
        _process.wait()
        _process = None
