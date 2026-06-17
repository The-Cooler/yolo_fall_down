from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.db import init_db
from app.detection_runner import task_manager
from app.routers import alerts, auth, cameras, health, streams, tasks, ws
from app.schemas import BaseResponse

EXCLUDED_PATHS = {
    "/docs", "/redoc", "/openapi.json", "/health",
    "/auth/code", "/auth/register", "/auth/login", "/system/user/getInfo",
}


class ProjectIdMiddleware:
    # 纯 ASGI 中间件，避免 BaseHTTPMiddleware 与 CORS 冲突

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)

        if request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        if request.url.path in EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        project_id = (
            request.headers.get("project_id")
            or request.query_params.get("project_id")
        )
        if project_id is None:
            response = JSONResponse(
                status_code=400,
                content=BaseResponse.error(400, "缺少 project_id").model_dump(),
            )
            await response(scope, receive, send)
            return

        if project_id != settings.auth.project_id:
            response = JSONResponse(
                status_code=403,
                content=BaseResponse.error(403, "project_id 无效").model_dump(),
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from app.test_stream import start as start_test_stream, stop as stop_test_stream
    start_test_stream()
    yield
    task_manager.stop_all()
    stop_test_stream()


app = FastAPI(
    title="摔倒检测系统",
    description="本地摔倒检测服务，集成 YOLO 推理、视频流处理、告警推送",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(ProjectIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(cameras.router)
app.include_router(tasks.router)
app.include_router(alerts.router)
app.include_router(ws.router)
app.include_router(streams.router)
app.include_router(streams.router_detect)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
    )
