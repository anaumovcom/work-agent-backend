from __future__ import annotations

from fastapi import APIRouter

from ..models.history import CreateHistoryEvent, HistoryEvent
from ..services import history_service
from ..storage.repositories import storage

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[HistoryEvent])
async def list_history(limit: int = 200, actor: str | None = None) -> list[HistoryEvent]:
    items = storage.history.all()
    if actor:
        items = [h for h in items if h.actor == actor]
    return items[-limit:]


@router.post("", response_model=HistoryEvent)
async def create_event(body: CreateHistoryEvent) -> HistoryEvent:
    return await history_service.record(body)
