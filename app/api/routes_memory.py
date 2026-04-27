from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models.memory import CorrectRequest, MemoryItem, MemoryPatch, SearchRequest
from ..services import memory_service

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/items", response_model=list[MemoryItem])
async def list_items(type: str | None = None) -> list[MemoryItem]:
    return memory_service.list_items(type)


@router.get("/items/{item_id}", response_model=MemoryItem)
async def get_item(item_id: str) -> MemoryItem:
    item = memory_service.get_item(item_id)
    if not item:
        raise HTTPException(404, "memory item not found")
    return item


@router.post("/search", response_model=list[MemoryItem])
async def search(body: SearchRequest) -> list[MemoryItem]:
    return memory_service.search(body)


@router.patch("/items/{item_id}", response_model=MemoryItem)
async def patch_item(item_id: str, body: MemoryPatch) -> MemoryItem:
    item = await memory_service.patch(item_id, body)
    if not item:
        raise HTTPException(404, "memory item not found")
    return item


@router.post("/items/{item_id}/correct", response_model=MemoryItem)
async def correct_item(item_id: str, body: CorrectRequest) -> MemoryItem:
    item = await memory_service.correct(item_id, body)
    if not item:
        raise HTTPException(404, "memory item not found")
    return item


@router.post("/items/{item_id}/forget")
async def forget_item(item_id: str) -> dict[str, bool]:
    ok = await memory_service.forget(item_id)
    if not ok:
        raise HTTPException(404, "memory item not found")
    return {"ok": True}
