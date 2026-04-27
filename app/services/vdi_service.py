from __future__ import annotations

from datetime import datetime, timezone

from ..core.event_bus import bus
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
from ..storage.repositories import storage
from . import history_service


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def current_frame() -> VdiFrame:
    n = storage.frame_counter.next()
    return VdiFrame(
        frameId=f"frame_{n:04d}",
        timestamp=_now_iso(),
        imageUrl=None,
    )


async def click(cmd: MouseClick) -> CommandResult:
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.click",
        f"Клик по VDI: {cmd.x:.0f}, {cmd.y:.0f}",
        x=cmd.x, y=cmd.y, button=cmd.button,
    )
    await bus.publish("vdi.click", {
        "x": cmd.x, "y": cmd.y, "button": cmd.button,
        "source": cmd.source, "timestamp": _now_iso(),
    })
    return CommandResult()


async def double_click(cmd: MouseClick) -> CommandResult:
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.double_click",
        f"Двойной клик: {cmd.x:.0f}, {cmd.y:.0f}",
        x=cmd.x, y=cmd.y,
    )
    await bus.publish("vdi.double_click", {
        "x": cmd.x, "y": cmd.y, "source": cmd.source, "timestamp": _now_iso(),
    })
    return CommandResult()


async def move(cmd: MouseMove) -> CommandResult:
    await bus.publish("vdi.move", {
        "x": cmd.x, "y": cmd.y, "source": cmd.source, "timestamp": _now_iso(),
    })
    return CommandResult()


async def drag(cmd: MouseDrag) -> CommandResult:
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.drag",
        f"Drag {cmd.from_x:.0f},{cmd.from_y:.0f} → {cmd.to_x:.0f},{cmd.to_y:.0f}",
    )
    await bus.publish("vdi.drag", cmd.model_dump(by_alias=True) | {"timestamp": _now_iso()})
    return CommandResult()


async def scroll(cmd: MouseScroll) -> CommandResult:
    await bus.publish("vdi.scroll", cmd.model_dump(by_alias=True) | {"timestamp": _now_iso()})
    return CommandResult()


async def type_text(cmd: TypeText) -> CommandResult:
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.typed",
        f"Ввод текста: {cmd.text!r}",
        text=cmd.text,
    )
    await bus.publish("vdi.typed", {
        "text": cmd.text, "source": cmd.source, "timestamp": _now_iso(),
    })
    return CommandResult()


async def key(cmd: KeyPress) -> CommandResult:
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.key",
        f"Клавиша: {cmd.key}",
        key=cmd.key,
    )
    await bus.publish("vdi.key", {
        "key": cmd.key, "source": cmd.source, "timestamp": _now_iso(),
    })
    return CommandResult()


async def hotkey(cmd: Hotkey) -> CommandResult:
    combo = "+".join(cmd.keys)
    await history_service.quick(
        "user" if cmd.source == "user" else "agent",
        "vdi.hotkey",
        f"Hotkey: {combo}",
        keys=cmd.keys,
    )
    await bus.publish("vdi.hotkey", {
        "keys": cmd.keys, "source": cmd.source, "timestamp": _now_iso(),
    })
    return CommandResult()
