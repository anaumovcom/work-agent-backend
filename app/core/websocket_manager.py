from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from .event_bus import bus

log = logging.getLogger(__name__)


async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    queue = await bus.subscribe()
    sender_task: asyncio.Task[None] | None = None
    try:
        async def sender() -> None:
            while True:
                event = await queue.get()
                await ws.send_json(event)

        sender_task = asyncio.create_task(sender())

        # читаем входящие, чтобы фиксировать disconnect; payload игнорируем
        while True:
            try:
                await ws.receive_text()
            except WebSocketDisconnect:
                break
    except Exception:
        log.exception("websocket error")
    finally:
        if sender_task is not None:
            sender_task.cancel()
        await bus.unsubscribe(queue)
