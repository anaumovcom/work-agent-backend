from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..core.event_bus import bus
from ..models.history import CreateHistoryEvent, HistoryEvent
from ..storage.repositories import storage


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def record(event: CreateHistoryEvent) -> HistoryEvent:
    n = storage.history_counter.next()
    h = HistoryEvent(
        id=f"event_{n:04d}",
        timestamp=_now_iso(),
        actor=event.actor,
        type=event.type,
        summary=event.summary,
        status=event.status,
        related_entities=event.related_entities,
        metadata=event.metadata,
    )
    storage.history.put(h.id, h)
    await bus.publish("history.event.created", h.model_dump(mode="json"))
    return h


async def quick(actor: str, type_: str, summary: str, **meta: Any) -> HistoryEvent:
    return await record(
        CreateHistoryEvent(
            actor=actor,  # type: ignore[arg-type]
            type=type_,
            summary=summary,
            metadata=meta,
        )
    )
