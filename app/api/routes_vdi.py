from __future__ import annotations

from fastapi import APIRouter

from ..models.vdi import (
    CommandResult,
    Hotkey,
    KeyPress,
    MouseClick,
    MouseDrag,
    MouseMove,
    MouseScroll,
    TypeText,
    VdiFrame,
)
from ..services import vdi_service

router = APIRouter(prefix="/api/vdi", tags=["vdi"])


@router.get("/frame/current", response_model=VdiFrame, response_model_by_alias=True)
async def current_frame() -> VdiFrame:
    return await vdi_service.current_frame()


@router.post("/mouse/click", response_model=CommandResult)
async def mouse_click(cmd: MouseClick) -> CommandResult:
    return await vdi_service.click(cmd)


@router.post("/mouse/double-click", response_model=CommandResult)
async def mouse_double_click(cmd: MouseClick) -> CommandResult:
    return await vdi_service.double_click(cmd)


@router.post("/mouse/move", response_model=CommandResult)
async def mouse_move(cmd: MouseMove) -> CommandResult:
    return await vdi_service.move(cmd)


@router.post("/mouse/drag", response_model=CommandResult)
async def mouse_drag(cmd: MouseDrag) -> CommandResult:
    return await vdi_service.drag(cmd)


@router.post("/mouse/scroll", response_model=CommandResult)
async def mouse_scroll(cmd: MouseScroll) -> CommandResult:
    return await vdi_service.scroll(cmd)


@router.post("/keyboard/type", response_model=CommandResult)
async def keyboard_type(cmd: TypeText) -> CommandResult:
    return await vdi_service.type_text(cmd)


@router.post("/keyboard/key", response_model=CommandResult)
async def keyboard_key(cmd: KeyPress) -> CommandResult:
    return await vdi_service.key(cmd)


@router.post("/keyboard/hotkey", response_model=CommandResult)
async def keyboard_hotkey(cmd: Hotkey) -> CommandResult:
    return await vdi_service.hotkey(cmd)
