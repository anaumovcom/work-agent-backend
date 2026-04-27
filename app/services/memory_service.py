from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..core.event_bus import bus
from ..models.memory import CorrectRequest, MemoryItem, MemoryPatch, SearchRequest
from ..storage.repositories import storage
from . import history_service


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_items(type_: Optional[str] = None) -> list[MemoryItem]:
    items = storage.memory.all()
    if type_:
        items = [i for i in items if i.type == type_]
    return items


def get_item(item_id: str) -> MemoryItem | None:
    return storage.memory.get(item_id)


def search(req: SearchRequest) -> list[MemoryItem]:
    items = storage.memory.all()
    if req.types:
        items = [i for i in items if i.type in req.types]
    q = req.query.strip().lower()
    if q:
        items = [
            i for i in items
            if q in (i.title or "").lower()
            or q in (i.summary or "").lower()
            or q in (i.content or "").lower()
            or q in (i.meta or "").lower()
        ]
    return items[: req.limit]


async def patch(item_id: str, body: MemoryPatch) -> MemoryItem | None:
    item = storage.memory.get(item_id)
    if not item:
        return None
    update = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    update["updated_at"] = _now_iso()
    item = item.model_copy(update=update)
    storage.memory.put(item.id, item)
    await bus.publish("memory.item.updated", item.model_dump(mode="json"))
    return item


async def correct(item_id: str, body: CorrectRequest) -> MemoryItem | None:
    item = storage.memory.get(item_id)
    if not item:
        return None
    item = item.model_copy(update={"content": body.content, "updated_at": _now_iso()})
    storage.memory.put(item.id, item)
    await bus.publish("memory.item.updated", item.model_dump(mode="json"))
    await history_service.quick("user", "memory.corrected",
                                f"Исправлено в памяти: {item.title}")
    return item


async def forget(item_id: str) -> bool:
    ok = storage.memory.delete(item_id)
    if ok:
        await bus.publish("memory.item.deleted", {"id": item_id})
        await history_service.quick("user", "memory.forgotten",
                                    f"Удалено из памяти: {item_id}")
    return ok
