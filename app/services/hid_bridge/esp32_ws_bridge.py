from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from ...core.config import get_settings
from .base import HidBridge, HidCommand

log = logging.getLogger(__name__)


class Esp32WebSocketHidBridge(HidBridge):
    """ESP32 со встроенным WS-сервером /hid. Клиент шлёт JSON-команды
    и ждёт ответ с тем же id."""

    name = "esp32_ws"

    def __init__(self) -> None:
        s = get_settings()
        self._url = s.esp32_ws_url
        self._token = s.esp32_api_token
        self._timeout = s.hid_command_timeout_ms / 1000
        self._ws: Any = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._last_error: str | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    async def start(self) -> None:
        await self._ensure()

    async def _ensure(self) -> None:
        if self._connected and self._ws is not None:
            return
        try:
            import websockets  # type: ignore

            self._ws = await asyncio.wait_for(
                websockets.connect(
                    self._url,
                    additional_headers=[("X-Api-Token", self._token)],
                ),
                timeout=3.0,
            )
            self._connected = True
            self._last_error = None
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            self._ws = None
            raise

    async def stop(self) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None
        self._connected = False

    async def ping(self) -> bool:
        try:
            await self._ensure()
            return True
        except Exception:
            return False

    def diagnostics(self) -> dict[str, Any]:
        return {
            "bridge": self.name,
            "wsUrl": self._url,
            "connected": self._connected,
            "lastError": self._last_error,
        }

    async def execute(self, cmd: HidCommand) -> None:
        async with self._lock:
            await self._ensure()
            assert self._ws is not None
            msg = json.dumps({"id": cmd.id, "type": cmd.type, "payload": cmd.payload})
            try:
                await asyncio.wait_for(self._ws.send(msg), timeout=self._timeout)
                while True:
                    raw = await asyncio.wait_for(self._ws.recv(), timeout=self._timeout)
                    data = json.loads(raw)
                    if data.get("id") != cmd.id:
                        continue
                    if data.get("status") == "error":
                        err = data.get("error", "esp32 error")
                        self._last_error = err
                        raise RuntimeError(err)
                    self._last_error = None
                    return
            except Exception as e:
                self._connected = False
                self._last_error = str(e)
                self._ws = None
                raise
