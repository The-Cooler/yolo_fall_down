from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base, FallTask

_url = settings.database_url
if _url.startswith("sqlite:///"):
    db_path = _url[len("sqlite:///"):]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(_url, pool_pre_ping=True, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.query(FallTask).filter(FallTask.detection_enabled.is_(True)).update(
            {
                FallTask.detection_enabled: False,
                FallTask.status: "stopped",
                FallTask.last_error: "服务重启后未自动恢复检测任务",
            },
            synchronize_session=False,
        )
        db.commit()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
