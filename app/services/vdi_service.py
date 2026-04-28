from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from ..core.config import get_settings
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
from . import history_service
from .hid_command_queue import hid_queue
from .screen_capture_service import screen_capture

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_result(item: HidQueueItem) -> CommandResult:
    if item.status == "failed":
        return CommandResult(
            commandId=item.command_id,
            status="failed",
            estimatedDelayMs=0,
            error=item.error,
        )
    return CommandResult(commandId=item.command_id, status="queued", estimatedDelayMs=0)


async def _after_action(item: HidQueueItem) -> None:
    settings = get_settings()
    delay = settings.after_action_refresh_delay_ms
    if item.type == "keyboard.type":
        delay = max(delay, 800)
    await asyncio.sleep(delay / 1000)
    await screen_capture._safe_refresh()


async def init_vdi_runtime() -> None:
    await screen_capture.start()
    await hid_queue.start()
    hid_queue.set_after_action_callback(_after_action)


async def shutdown_vdi_runtime() -> None:
    await screen_capture.stop()
    await hid_queue.stop()


async def current_frame() -> VdiFrame:
    snap = screen_capture.last()
    if snap is None:
        snap = await screen_capture._safe_refresh()
    if snap is None:
        return VdiFrame(
            frameId="frame_unavailable",
            timestamp=_now_iso(),
            imageUrl=None,
            source=screen_capture._provider.name,
            latencyMs=0,
            status="error",
        )

    frame = screen_capture.snapshot_to_frame(snap)
    settings = get_settings()
    try:
        age_ms = int(
            (datetime.now(timezone.utc) - datetime.fromisoformat(snap.timestamp))
            .total_seconds()
            * 1000
        )
    except Exception:
        age_ms = 0
    if age_ms > settings.stale_frame_warning_ms:
        frame.status = "stale"
    return frame


async def refresh_frame() -> VdiFrame:
    snap = await screen_capture.refresh()
    return screen_capture.snapshot_to_frame(snap)


def get_frame_image(frame_id: str):
    return screen_capture.get_image(frame_id)


def frame_status() -> FrameStatus:
    return screen_capture.status()


async def click(cmd: MouseClick) -> CommandResult:
    item = await hid_queue.enqueue("mouse.click", cmd.model_dump())
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.click",
        f"Клик по VDI: {cmd.x:.0f}, {cmd.y:.0f}",
        commandId=item.command_id,
        x=cmd.x,
        y=cmd.y,
        button=cmd.button,
    )
    return _to_result(item)


async def mouse_down(cmd: MouseClick) -> CommandResult:
    item = await hid_queue.enqueue("mouse.down", cmd.model_dump())
    return _to_result(item)


async def mouse_up(cmd: MouseClick) -> CommandResult:
    item = await hid_queue.enqueue("mouse.up", cmd.model_dump())
    return _to_result(item)


async def double_click(cmd: MouseClick) -> CommandResult:
    item = await hid_queue.enqueue("mouse.double_click", cmd.model_dump())
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.double_click",
        f"Двойной клик: {cmd.x:.0f}, {cmd.y:.0f}",
        commandId=item.command_id,
        x=cmd.x,
        y=cmd.y,
    )
    return _to_result(item)


async def move(cmd: MouseMove) -> CommandResult:
    item = await hid_queue.enqueue("mouse.move", cmd.model_dump())
    return _to_result(item)


async def drag(cmd: MouseDrag) -> CommandResult:
    payload = cmd.model_dump(by_alias=True)
    item = await hid_queue.enqueue("mouse.drag", payload)
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.drag",
        f"Drag {cmd.from_x:.0f},{cmd.from_y:.0f} → {cmd.to_x:.0f},{cmd.to_y:.0f}",
        commandId=item.command_id,
    )
    return _to_result(item)


async def scroll(cmd: MouseScroll) -> CommandResult:
    item = await hid_queue.enqueue("mouse.scroll", cmd.model_dump(by_alias=True))
    return _to_result(item)


async def type_text(cmd: TypeText) -> CommandResult:
    item = await hid_queue.enqueue("keyboard.type", cmd.model_dump())
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.typed",
        f"Ввод текста: {cmd.text!r}",
        commandId=item.command_id,
        text=cmd.text,
    )
    return _to_result(item)


async def key(cmd: KeyPress) -> CommandResult:
    item = await hid_queue.enqueue("keyboard.key", cmd.model_dump())
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.key",
        f"Клавиша: {cmd.key}",
        commandId=item.command_id,
        key=cmd.key,
    )
    return _to_result(item)


async def hotkey(cmd: Hotkey) -> CommandResult:
    item = await hid_queue.enqueue("keyboard.hotkey", cmd.model_dump())
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.hotkey",
        f"Hotkey: {'+'.join(cmd.keys)}",
        commandId=item.command_id,
        keys=cmd.keys,
    )
    return _to_result(item)


def list_queue() -> list[HidQueueItem]:
    return hid_queue.list()


async def clear_queue() -> int:
    return await hid_queue.clear()
