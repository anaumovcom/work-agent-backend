"""Сервис захвата экрана VDI.

Абстракция над реальным OBS WebSocket и mock-провайдером.
Хранит последний полученный кадр в памяти, выдаёт frame_id и image bytes.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..core.config import get_settings
from ..core.event_bus import bus
from ..models.vdi import FrameStatus, Resolution, VdiFrame

log = logging.getLogger(__name__)


class ObsRequestError(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FrameSnapshot:
    frame_id: str
    timestamp: str
    image_bytes: bytes
    mime: str = "image/png"
    resolution: Resolution = field(default_factory=Resolution)
    source: str = "mock"
    latency_ms: int = 0


class FrameProvider:
    name = "base"

    async def start(self) -> None:  # pragma: no cover
        pass

    async def stop(self) -> None:  # pragma: no cover
        pass

    async def capture(self) -> FrameSnapshot:  # pragma: no cover
        raise NotImplementedError

    @property
    def connected(self) -> bool:  # pragma: no cover
        return True


# ---------------------------------------------------------------------------
# Mock provider — генерирует простой PNG на лету
# ---------------------------------------------------------------------------
def _mock_png(width: int, height: int, frame_no: int) -> bytes:
    """Минимальный 1x1 PNG (серый), enough для img src; UI всё равно
    масштабирует по naturalSize; реальный размер указан в resolution."""
    # 1x1 grey PNG (pre-baked)
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )


class MockFrameProvider(FrameProvider):
    name = "mock"

    def __init__(self) -> None:
        self._counter = 0
        self._w = get_settings().vdi_width
        self._h = get_settings().vdi_height

    @property
    def connected(self) -> bool:
        return True

    async def capture(self) -> FrameSnapshot:
        self._counter += 1
        png = _mock_png(self._w, self._h, self._counter)
        return FrameSnapshot(
            frame_id=f"frame_mock_{self._counter:06d}",
            timestamp=_now_iso(),
            image_bytes=png,
            mime="image/png",
            resolution=Resolution(width=self._w, height=self._h),
            source="mock",
            latency_ms=0,
        )


# ---------------------------------------------------------------------------
# OBS WebSocket provider
# ---------------------------------------------------------------------------
class ObsWebSocketFrameProvider(FrameProvider):
    """Минимальный клиент OBS WebSocket v5: GetSourceScreenshot.

    Подключается по необходимости, переиспользует соединение, поддерживает
    переподключение. Использует протокол v5 с хэшированной авторизацией.
    """

    name = "obs"

    def __init__(self) -> None:
        s = get_settings()
        self._url = s.obs_ws_url
        self._password = s.obs_ws_password
        self._source = s.obs_source_name
        self._w = s.vdi_width
        self._h = s.vdi_height
        self._ws = None
        self._lock = asyncio.Lock()
        self._req_counter = 0
        self._connected = False
        self._last_error: Optional[str] = None

    @property
    def connected(self) -> bool:
        return self._connected

    async def stop(self) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None
        self._connected = False

    async def _ensure_connected(self) -> None:
        if self._connected and self._ws is not None:
            return
        try:
            import websockets  # type: ignore
            import hashlib

            self._ws = await asyncio.wait_for(
                websockets.connect(self._url, max_size=64 * 1024 * 1024),
                timeout=3.0,
            )
            hello = json.loads(await asyncio.wait_for(self._ws.recv(), timeout=3.0))
            if hello.get("op") != 0:
                raise RuntimeError(f"unexpected OBS hello: {hello}")
            d = hello["d"]
            identify_data: dict = {"rpcVersion": d.get("rpcVersion", 1)}
            auth = d.get("authentication")
            if auth:
                secret = base64.b64encode(
                    hashlib.sha256(
                        (self._password + auth["salt"]).encode()
                    ).digest()
                ).decode()
                ident = base64.b64encode(
                    hashlib.sha256(
                        (secret + auth["challenge"]).encode()
                    ).digest()
                ).decode()
                identify_data["authentication"] = ident
            await self._ws.send(json.dumps({"op": 1, "d": identify_data}))
            ident_resp = json.loads(
                await asyncio.wait_for(self._ws.recv(), timeout=3.0)
            )
            if ident_resp.get("op") != 2:
                raise RuntimeError(f"OBS identify failed: {ident_resp}")
            self._connected = True
            self._last_error = None
            log.info("OBS WebSocket connected at %s", self._url)
        except Exception as e:
            self._last_error = str(e)
            self._connected = False
            self._ws = None
            raise

    async def _request(self, request_type: str, request_data: dict) -> dict:
        assert self._ws is not None
        self._req_counter += 1
        rid = f"req_{self._req_counter}"
        msg = {
            "op": 6,
            "d": {
                "requestType": request_type,
                "requestId": rid,
                "requestData": request_data,
            },
        }
        await self._ws.send(json.dumps(msg))
        # ждём именно наш ответ
        while True:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
            data = json.loads(raw)
            if data.get("op") == 7 and data["d"].get("requestId") == rid:
                return data["d"]

    async def _checked_request(self, request_type: str, request_data: dict) -> dict:
        resp = await self._request(request_type, request_data)
        status = resp.get("requestStatus", {})
        if not status.get("result"):
            code = status.get("code")
            comment = status.get("comment", "")
            raise ObsRequestError(f"OBS {request_type} failed: {code} {comment}")
        return resp

    async def _current_program_scene_name(self) -> str:
        resp = await self._checked_request("GetCurrentProgramScene", {})
        data = resp.get("responseData", {})
        name = data.get("currentProgramSceneName") or data.get("sceneName")
        if not name:
            raise ObsRequestError("OBS current program scene name is empty")
        return str(name)

    async def _screenshot_response(self, source_name: str) -> dict:
        return await self._checked_request(
            "GetSourceScreenshot",
            {
                "sourceName": source_name,
                "imageFormat": "png",
                "imageWidth": self._w,
                "imageHeight": self._h,
            },
        )

    async def capture(self) -> FrameSnapshot:
        async with self._lock:
            t0 = time.monotonic()
            await self._ensure_connected()
            assert self._ws is not None
            try:
                source_name = self._source.strip()
                if source_name:
                    try:
                        resp = await self._screenshot_response(source_name)
                    except ObsRequestError as e:
                        scene_name = await self._current_program_scene_name()
                        log.warning(
                            "OBS source %r unavailable (%s), using current scene %r",
                            source_name,
                            e,
                            scene_name,
                        )
                        resp = await self._screenshot_response(scene_name)
                        source_name = scene_name
                else:
                    source_name = await self._current_program_scene_name()
                    resp = await self._screenshot_response(source_name)
            except ObsRequestError as e:
                self._last_error = str(e)
                raise
            except Exception as e:
                self._connected = False
                self._last_error = str(e)
                self._ws = None
                raise

            img_b64 = resp["responseData"]["imageData"]
            # OBS возвращает data URI: "data:image/png;base64,...."
            if "," in img_b64:
                img_b64 = img_b64.split(",", 1)[1]
            png = base64.b64decode(img_b64)
            latency = int((time.monotonic() - t0) * 1000)
            fid = f"frame_obs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
            return FrameSnapshot(
                frame_id=fid,
                timestamp=_now_iso(),
                image_bytes=png,
                mime="image/png",
                resolution=Resolution(width=self._w, height=self._h),
                source="obs",
                latency_ms=latency,
            )


# ---------------------------------------------------------------------------
# File provider — читает последний *.png из папки (полезно для отладки)
# ---------------------------------------------------------------------------
class FileFrameProvider(FrameProvider):
    name = "file"

    def __init__(self) -> None:
        s = get_settings()
        self._dir = Path(s.frame_storage_dir)
        self._w = s.vdi_width
        self._h = s.vdi_height

    @property
    def connected(self) -> bool:
        return self._dir.exists()

    async def capture(self) -> FrameSnapshot:
        if not self._dir.exists():
            raise RuntimeError(f"frame dir not found: {self._dir}")
        files = sorted(self._dir.glob("*.png"))
        if not files:
            raise RuntimeError("no png files in frame dir")
        latest = files[-1]
        data = latest.read_bytes()
        return FrameSnapshot(
            frame_id=f"frame_file_{latest.stem}",
            timestamp=_now_iso(),
            image_bytes=data,
            mime="image/png",
            resolution=Resolution(width=self._w, height=self._h),
            source="file",
        )


# ---------------------------------------------------------------------------
# ScreenCaptureService — фасад с кешем последнего кадра
# ---------------------------------------------------------------------------
class ScreenCaptureService:
    def __init__(self) -> None:
        self._provider: FrameProvider = MockFrameProvider()
        self._last: Optional[FrameSnapshot] = None
        self._lock = asyncio.Lock()
        self._auto_task: Optional[asyncio.Task] = None
        self._frames: dict[str, FrameSnapshot] = {}
        self._frame_order: list[str] = []
        self._max_cache = 32
        self._fps_window: list[float] = []

    def _make_provider(self) -> FrameProvider:
        s = get_settings()
        if s.frame_provider == "obs":
            return ObsWebSocketFrameProvider()
        elif s.frame_provider == "file":
            return FileFrameProvider()
        return MockFrameProvider()

    def configure(self) -> None:
        self._provider = self._make_provider()
        log.info("ScreenCaptureService provider=%s", self._provider.name)

    async def reconfigure(self) -> None:
        async with self._lock:
            old_provider = self._provider
            self._provider = self._make_provider()
            self._last = None
            self._frames.clear()
            self._frame_order.clear()
            self._fps_window.clear()
            await old_provider.stop()
        log.info("ScreenCaptureService provider=%s", self._provider.name)

    async def start(self) -> None:
        self.configure()
        await self._provider.start()
        # первичный захват в фоне (best-effort)
        asyncio.create_task(self._safe_refresh())
        self._auto_task = asyncio.create_task(self._auto_loop())

    async def stop(self) -> None:
        if self._auto_task:
            self._auto_task.cancel()
        await self._provider.stop()

    async def _auto_loop(self) -> None:
        while True:
            try:
                interval = max(0.2, get_settings().frame_refresh_interval_ms / 1000)
                await asyncio.sleep(interval)
                await self._safe_refresh()
            except asyncio.CancelledError:
                break
            except Exception:  # pragma: no cover
                log.exception("auto refresh failed")

    async def _safe_refresh(self) -> Optional[FrameSnapshot]:
        try:
            return await self.refresh()
        except Exception as e:
            log.debug("frame refresh failed: %s", e)
            return None

    async def refresh(self) -> FrameSnapshot:
        async with self._lock:
            snap = await self._provider.capture()
            self._last = snap
            self._frames[snap.frame_id] = snap
            self._frame_order.append(snap.frame_id)
            while len(self._frame_order) > self._max_cache:
                old = self._frame_order.pop(0)
                self._frames.pop(old, None)
            self._fps_window.append(time.monotonic())
            self._fps_window = [
                t for t in self._fps_window if time.monotonic() - t < 5.0
            ]
        await bus.publish(
            "vdi.frame.updated",
            self.snapshot_to_frame(snap).model_dump(by_alias=True),
        )
        return snap

    def get_image(self, frame_id: str) -> Optional[FrameSnapshot]:
        if frame_id == "current" and self._last is not None:
            return self._last
        return self._frames.get(frame_id)

    def last(self) -> Optional[FrameSnapshot]:
        return self._last

    def snapshot_to_frame(self, snap: FrameSnapshot) -> VdiFrame:
        return VdiFrame(
            frameId=snap.frame_id,
            timestamp=snap.timestamp,
            imageUrl=f"/api/vdi/frame/{snap.frame_id}/image",
            resolution=snap.resolution,
            source=snap.source,
            latencyMs=snap.latency_ms,
            status="ok",
        )

    def status(self) -> FrameStatus:
        last = self._last
        fps = (
            len(self._fps_window) / 5.0
            if len(self._fps_window) > 1
            else 0.0
        )
        s = get_settings()
        return FrameStatus(
            provider=self._provider.name,
            connected=self._provider.connected,
            lastFrameAt=last.timestamp if last else None,
            resolution=last.resolution if last else Resolution(width=s.vdi_width, height=s.vdi_height),
            latencyMs=last.latency_ms if last else 0,
            fpsApprox=round(fps, 2),
            error=getattr(self._provider, "_last_error", None),
        )


screen_capture = ScreenCaptureService()
