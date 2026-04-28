from __future__ import annotations

import logging
from typing import Any

import httpx

from ...core.config import get_settings
from .base import HidBridge, HidCommand

log = logging.getLogger(__name__)


class Esp32HttpHidBridge(HidBridge):
    """ESP32 принимает POST /hid/command c JSON {id, type, payload}.

    Авторизация через заголовок X-Api-Token.
    """

    name = "esp32_http"

    def __init__(self) -> None:
        s = get_settings()
        self._base = s.esp32_base_url.rstrip("/")
        self._token = s.esp32_api_token
        self._timeout = s.hid_command_timeout_ms / 1000
        self._client: httpx.AsyncClient | None = None
        self._connected = False
        self._last_error: str | None = None
        self._last_status: dict[str, Any] = {}

    @property
    def connected(self) -> bool:
        return self._connected

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self._base,
            timeout=self._timeout,
            headers={"X-Api-Token": self._token},
        )
        await self._ping()

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _ping(self) -> bool:
        if self._client is None:
            return False
        try:
            r = await self._client.get("/hid/status")
            self._connected = r.status_code == 200
            if self._connected:
                self._last_status = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                self._last_error = None
            else:
                self._last_error = f"http {r.status_code}: {r.text[:200]}"
            return self._connected
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            return False

    async def ping(self) -> bool:
        if self._client is None:
            await self.start()
        return await self._ping()

    def diagnostics(self) -> dict[str, Any]:
        return {
            "bridge": self.name,
            "baseUrl": self._base,
            "connected": self._connected,
            "lastError": self._last_error,
            "device": self._last_status,
        }

    async def execute(self, cmd: HidCommand) -> None:
        if self._client is None:
            await self.start()
        assert self._client is not None
        body: dict[str, Any] = {"id": cmd.id, "type": cmd.type, "payload": cmd.payload}
        try:
            r = await self._client.post("/hid/command", json=body)
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            raise
        if r.status_code != 200:
            self._connected = False
            self._last_error = f"http {r.status_code}: {r.text[:200]}"
            raise RuntimeError(self._last_error)
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if data.get("status") == "error":
            err = data.get("error") or "esp32 error"
            self._last_error = err
            raise RuntimeError(err)
        self._connected = True
        self._last_error = None
