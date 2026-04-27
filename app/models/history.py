from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel

Actor = Literal["user", "agent", "system", "vdi"]
EventStatus = Literal["success", "info", "error", "warn"]


class HistoryEvent(BaseModel):
    id: str
    timestamp: str
    actor: Actor
    type: str
    summary: str
    status: EventStatus = "info"
    related_entities: list[str] = []
    metadata: dict[str, Any] = {}


class CreateHistoryEvent(BaseModel):
    actor: Actor
    type: str
    summary: str
    status: EventStatus = "info"
    related_entities: list[str] = []
    metadata: dict[str, Any] = {}
