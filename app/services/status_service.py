from __future__ import annotations

from ..core.event_bus import bus
from ..models.status import ModePatch, SystemStatus
from ..storage.repositories import storage
from . import history_service
from .hid_command_queue import hid_queue
from .screen_capture_service import screen_capture


def _apply_runtime_status() -> SystemStatus:
    capture = screen_capture.status()
    bridge = hid_queue.bridge
    obs_status = "online" if capture.connected else ("mock" if capture.provider == "mock" else "offline")
    esp_status = (
        "connected"
        if (bridge is not None and bridge.connected)
        else ("mock_connected" if (bridge is None or bridge.name == "mock") else "disconnected")
    )
    storage.status = storage.status.model_copy(update={
        "obs": storage.status.obs.model_copy(update={
            "status": obs_status,
            "delay_ms": capture.latency_ms,
        }),
        "esp32": storage.status.esp32.model_copy(update={"status": esp_status}),
        "vdi": "online" if capture.connected else ("mock" if capture.provider == "mock" else "offline"),
        "emergency_stop": hid_queue.emergency_stop_active,
    })
    return storage.status


async def get_status() -> SystemStatus:
    await hid_queue.refresh_bridge_status()
    return _apply_runtime_status()


async def set_mode(patch: ModePatch) -> SystemStatus:
    storage.status = storage.status.model_copy(update={"current_mode": patch.mode})
    status = _apply_runtime_status()
    await bus.publish("status.updated", status.model_dump(by_alias=True))
    await history_service.quick("user", "status.mode_changed", f"Режим переключён: {patch.mode}")
    return status


async def set_paused(paused: bool) -> SystemStatus:
    storage.status = storage.status.model_copy(update={"agents_paused": paused})
    status = _apply_runtime_status()
    await bus.publish("status.updated", status.model_dump(by_alias=True))
    await history_service.quick(
        "user",
        "agents.paused" if paused else "agents.resumed",
        "Агенты на паузе" if paused else "Агенты возобновлены",
    )
    return status


async def emergency_stop() -> SystemStatus:
    await hid_queue.emergency_stop()
    storage.status = storage.status.model_copy(update={
        "agents_paused": True,
        "emergency_stop": True,
    })
    status = _apply_runtime_status()
    await bus.publish("status.updated", status.model_dump(by_alias=True))
    await history_service.quick(
        "user", "system.emergency_stop", "Аварийная остановка агентов", status="error",
    )
    return status


async def reset_emergency_stop() -> SystemStatus:
    await hid_queue.reset_emergency_stop()
    storage.status = storage.status.model_copy(update={"emergency_stop": False})
    status = _apply_runtime_status()
    await bus.publish("status.updated", status.model_dump(by_alias=True))
    await history_service.quick("user", "system.emergency_stop_reset", "Аварийная остановка снята")
    return status
