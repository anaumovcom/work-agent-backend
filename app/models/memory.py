from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel

MemoryItemType = Literal[
    "task",
    "epic",
    "person",
    "project",
    "message",
    "email",
    "meeting",
    "voice",
    "screen",
    "action",
    "conversation",
    "decision",
    "preference",
    "ui_zone",
]


class MemoryItem(BaseModel):
    id: str
    type: MemoryItemType
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    meta: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    related: list[str] = []
    extra: dict[str, Any] = {}
    created_at: str
    updated_at: str


class MemoryPatch(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    meta: Optional[str] = None
    confidence: Optional[float] = None


class CorrectRequest(BaseModel):
    content: str
    note: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = ""
    types: list[MemoryItemType] | None = None
    limit: int = 20
