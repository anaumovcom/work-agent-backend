from __future__ import annotations

from ..core.event_bus import bus
from ..models.status import ModePatch, SystemMode, SystemStatus
from ..storage.repositories import storage
from . import history_service


async def get_status() -> SystemStatus:
    return storage.status


async def set_mode(patch: ModePatch) -> SystemStatus:
    storage.status = storage.status.model_copy(update={"current_mode": patch.mode})
    await bus.publish("status.updated", storage.status.model_dump(by_alias=True))
    await history_service.quick("user", "status.mode_changed",
                                f"Режим переключён: {patch.mode}")
    return storage.status


async def set_paused(paused: bool) -> SystemStatus:
    storage.status = storage.status.model_copy(update={"agents_paused": paused})
    await bus.publish("status.updated", storage.status.model_dump(by_alias=True))
    await history_service.quick(
        "user",
        "agents.paused" if paused else "agents.resumed",
        "Агенты на паузе" if paused else "Агенты возобновлены",
    )
    return storage.status


async def emergency_stop() -> SystemStatus:
    storage.status = storage.status.model_copy(update={"agents_paused": True})
    await bus.publish("status.updated", storage.status.model_dump(by_alias=True))
    await history_service.quick("user", "system.emergency_stop", "Аварийная остановка агентов")
    return storage.status
