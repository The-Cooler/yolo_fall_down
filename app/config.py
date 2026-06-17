from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 9500


@dataclass
class DetectionConfig:
    model_path: str = "models/out/best.pt"
    default_fps: float = 2.0
    default_conf_threshold: float = 0.25
    alert_cooldown_seconds: int = 30


@dataclass
class StreamConfig:
    open_timeout_ms: int = 5000
    read_timeout_ms: int = 5000
    mjpeg_fps: int = 20
    jpeg_quality: int = 80
    mjpeg_read_retry_count: int = 30
    mjpeg_read_retry_delay_ms: int = 100


@dataclass
class DatabaseConfig:
    url: str = "sqlite:///data/fall_down.db"


@dataclass
class AuthConfig:
    jwt_secret: str = "change-me"
    jwt_expire_hours: int = 24
    project_id: str = "001"


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    stream: StreamConfig = field(default_factory=StreamConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_PATH.exists():
            return cls()
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        def _populate(dc, raw_dict):
            if raw_dict is None:
                return dc()
            field_names = {f.name for f in dc.__dataclass_fields__.values()}
            kwargs = {k: v for k, v in raw_dict.items() if k in field_names and v is not None}
            return dc(**kwargs)

        return cls(
            server=_populate(ServerConfig, raw.get("server")),
            detection=_populate(DetectionConfig, raw.get("detection")),
            stream=_populate(StreamConfig, raw.get("stream")),
            database=_populate(DatabaseConfig, raw.get("database")),
            auth=_populate(AuthConfig, raw.get("auth")),
        )

    @property
    def model_path(self) -> Path:
        p = Path(self.detection.model_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p.resolve()

    @property
    def database_url(self) -> str:
        url = self.database.url
        if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
            db_path = url[len("sqlite:///"):]
            if not Path(db_path).is_absolute():
                abs_path = (PROJECT_ROOT / db_path).resolve()
                return f"sqlite:///{abs_path}"
        return url


settings = AppConfig.load()
