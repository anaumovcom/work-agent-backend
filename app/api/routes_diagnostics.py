from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from ..core.event_bus import bus
from ..services.hid_command_queue import hid_queue
from ..services.screen_capture_service import screen_capture
from ..services import vdi_service
from ..models.vdi import MouseClick, TypeText

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


_started_at = time.monotonic()


def _diagnostics_payload() -> list[dict]:
    cap = screen_capture.status()
    bridge = hid_queue.bridge
    bridge_diag = hid_queue.bridge_diagnostics()
    queue_items = hid_queue.list()
    pending = sum(1 for i in queue_items if i.status in ("pending", "running"))
    failed = sum(1 for i in queue_items if i.status == "failed")
    last_cmd = queue_items[-1] if queue_items else None
    uptime_s = int(time.monotonic() - _started_at)

    obs_status = "ok" if cap.connected else ("warn" if cap.provider == "mock" else "error")
    esp_status = (
        "ok"
        if (bridge is not None and bridge.connected)
        else ("warn" if (bridge is None or bridge.name == "mock") else "error")
    )

    return [
        {"id": "obs", "name": "OBS", "status": obs_status, "metrics": [
            {"label": "Provider", "value": cap.provider},
            {"label": "Connected", "value": "yes" if cap.connected else "no"},
            {"label": "Last frame", "value": (cap.last_frame_at or "—")[-12:]},
            {"label": "Latency", "value": f"{cap.latency_ms} ms"},
            {"label": "FPS approx", "value": f"{cap.fps_approx}"},
            {"label": "Resolution", "value": f"{cap.resolution.width}×{cap.resolution.height}"},
            {"label": "Error", "value": cap.error or "—"},
        ]},
        {"id": "esp32", "name": "ESP32", "status": esp_status, "metrics": [
            {"label": "Bridge", "value": bridge_diag.get("bridge", bridge.name if bridge else "—")},
            {"label": "Endpoint", "value": bridge_diag.get("baseUrl") or bridge_diag.get("wsUrl") or "—"},
            {"label": "Connected", "value": "yes" if (bridge and bridge.connected) else "no"},
            {"label": "HID ready", "value": str(bridge_diag.get("device", {}).get("hidReady", "—"))},
            {"label": "Mouse pos", "value": (
                f"{bridge_diag.get('device', {}).get('mouseX')},{bridge_diag.get('device', {}).get('mouseY')}"
                if bridge_diag.get("device", {}).get("mouseX") is not None else "—"
            )},
            {"label": "Last error", "value": bridge_diag.get("lastError") or "—"},
            {"label": "Queue pending", "value": str(pending)},
            {"label": "Queue failed", "value": str(failed)},
            {"label": "Last command", "value": (last_cmd.type if last_cmd else "—")},
            {"label": "Last duration", "value": f"{last_cmd.duration_ms or 0} ms" if last_cmd else "—"},
        ]},
        {"id": "backend", "name": "Backend", "status": "ok", "metrics": [
            {"label": "Uptime", "value": f"{uptime_s}s"},
            {"label": "Queue size", "value": str(len(queue_items))},
            {"label": "Emergency stop", "value": "ON" if hid_queue.emergency_stop_active else "off"},
        ]},
        {"id": "vision", "name": "Vision", "status": "warn", "metrics": [
            {"label": "OCR", "value": "mock"},
            {"label": "Vision", "value": "mock"},
        ]},
        {"id": "llm", "name": "LLM", "status": "warn", "metrics": [
            {"label": "Mode", "value": "mock"},
        ]},
        {"id": "memory", "name": "Memory", "status": "warn", "metrics": [
            {"label": "Storage", "value": "in-memory"},
        ]},
    ]


@router.get("")
async def get_diagnostics() -> list[dict]:
    await hid_queue.refresh_bridge_status()
    return _diagnostics_payload()


@router.get("/esp32")
async def get_esp32_diagnostics() -> dict:
    await hid_queue.refresh_bridge_status()
    return hid_queue.bridge_diagnostics()


@router.post("/test-esp32-move")
async def test_esp32_move() -> dict:
    from ..models.vdi import MouseMove

    res = await vdi_service.move(MouseMove(x=0, y=0, source="user"))
    await bus.publish("diagnostics.updated", {"test": "esp32_move", "commandId": res.command_id})
    return {"test": "esp32_move", "commandId": res.command_id, "status": res.status}


@router.post("/test-click")
async def test_click() -> dict:
    res = await vdi_service.click(MouseClick(x=100, y=100, source="user"))
    await bus.publish("diagnostics.updated", {"test": "click", "commandId": res.command_id})
    return {"test": "click", "commandId": res.command_id, "status": res.status}


@router.post("/test-typing")
async def test_typing() -> dict:
    res = await vdi_service.type_text(TypeText(text="test", source="user"))
    await bus.publish("diagnostics.updated", {"test": "typing", "commandId": res.command_id})
    return {"test": "typing", "commandId": res.command_id, "status": res.status}


@router.post("/test-frame")
async def test_frame() -> dict:
    frame = await vdi_service.refresh_frame()
    return {"test": "frame", "frameId": frame.frame_id, "latencyMs": frame.latency_ms}


@router.post("/test-ocr")
async def test_ocr() -> dict:
    return {"test": "ocr", "status": "mock"}


@router.post("/test-vision")
async def test_vision() -> dict:
    return {"test": "vision", "status": "mock"}
