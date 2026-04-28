from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from ..models.vdi import (
    CommandResult,
    FrameStatus,
    HidQueueItem,
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


@router.post("/frame/refresh", response_model=VdiFrame, response_model_by_alias=True)
async def refresh_frame() -> VdiFrame:
    try:
        return await vdi_service.refresh_frame()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"frame refresh failed: {e}")


@router.get("/frame/status", response_model=FrameStatus, response_model_by_alias=True)
async def frame_status_endpoint() -> FrameStatus:
    return vdi_service.frame_status()


@router.get("/frame/{frame_id}/image")
async def frame_image(frame_id: str) -> Response:
    snap = vdi_service.get_frame_image(frame_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="frame not found")
    return Response(content=snap.image_bytes, media_type=snap.mime)


@router.post("/mouse/click", response_model=CommandResult, response_model_by_alias=True)
async def mouse_click(cmd: MouseClick) -> CommandResult:
    return await vdi_service.click(cmd)


@router.post("/mouse/down", response_model=CommandResult, response_model_by_alias=True)
async def mouse_down(cmd: MouseClick) -> CommandResult:
    return await vdi_service.mouse_down(cmd)


@router.post("/mouse/up", response_model=CommandResult, response_model_by_alias=True)
async def mouse_up(cmd: MouseClick) -> CommandResult:
    return await vdi_service.mouse_up(cmd)


@router.post("/mouse/double-click", response_model=CommandResult, response_model_by_alias=True)
async def mouse_double_click(cmd: MouseClick) -> CommandResult:
    return await vdi_service.double_click(cmd)


@router.post("/mouse/move", response_model=CommandResult, response_model_by_alias=True)
async def mouse_move(cmd: MouseMove) -> CommandResult:
    return await vdi_service.move(cmd)


@router.post("/mouse/drag", response_model=CommandResult, response_model_by_alias=True)
async def mouse_drag(cmd: MouseDrag) -> CommandResult:
    return await vdi_service.drag(cmd)


@router.post("/mouse/scroll", response_model=CommandResult, response_model_by_alias=True)
async def mouse_scroll(cmd: MouseScroll) -> CommandResult:
    return await vdi_service.scroll(cmd)


@router.post("/keyboard/type", response_model=CommandResult, response_model_by_alias=True)
async def keyboard_type(cmd: TypeText) -> CommandResult:
    return await vdi_service.type_text(cmd)


@router.post("/keyboard/key", response_model=CommandResult, response_model_by_alias=True)
async def keyboard_key(cmd: KeyPress) -> CommandResult:
    return await vdi_service.key(cmd)


@router.post("/keyboard/hotkey", response_model=CommandResult, response_model_by_alias=True)
async def keyboard_hotkey(cmd: Hotkey) -> CommandResult:
    return await vdi_service.hotkey(cmd)


@router.get("/queue", response_model=list[HidQueueItem], response_model_by_alias=True)
async def list_queue() -> list[HidQueueItem]:
    return vdi_service.list_queue()


@router.post("/queue/clear")
async def clear_queue() -> dict:
    n = await vdi_service.clear_queue()
    return {"cleared": n}
