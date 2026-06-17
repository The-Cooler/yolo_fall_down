from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self) -> None:
        self._loop = asyncio.get_running_loop()

    async def connect(self, camera_id: str, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[self._channel(camera_id, user_id)].add(websocket)

    def disconnect(self, camera_id: str, user_id: str, websocket: WebSocket) -> None:
        channel = self._channel(camera_id, user_id)
        conns = self._connections.get(channel)
        if conns is None:
            return
        conns.discard(websocket)
        if not conns:
            self._connections.pop(channel, None)

    def publish(self, camera_id: str, user_id: str, payload: dict) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(
            self._publish(camera_id, user_id, payload), loop
        )

    async def _publish(self, camera_id: str, user_id: str, payload: dict) -> None:
        conns = list(self._connections.get(self._channel(camera_id, user_id), set()))
        dead = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(camera_id, user_id, ws)

    @staticmethod
    def _channel(camera_id: str, user_id: str) -> str:
        return f"{user_id}:{camera_id}"


ws_manager = WebSocketManager()
