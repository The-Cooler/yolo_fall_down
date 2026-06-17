from __future__ import annotations

import socket

from fastapi import APIRouter

from app.config import settings
from app.schemas import BaseResponse

router = APIRouter(tags=["健康检查"])


@router.get("/health")
def health():
    return BaseResponse.success(
        {
            "service": "fall-detection",
            "host": socket.gethostname(),
            "port": settings.server.port,
        },
        msg="服务正常",
    )
