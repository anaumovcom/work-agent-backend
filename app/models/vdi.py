from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

MouseButton = Literal["left", "right", "middle"]
Source = Literal["user", "agent", "scenario"]
CommandStatus = Literal["queued", "pending", "running", "done", "failed", "cancelled"]


class Resolution(BaseModel):
    width: int = 1920
    height: int = 1080


class VdiFrame(BaseModel):
    frame_id: str = Field(alias="frameId")
    timestamp: str
    image_url: Optional[str] = Field(default=None, alias="imageUrl")
    resolution: Resolution = Resolution()
    source: str = "mock"
    latency_ms: int = Field(0, alias="latencyMs")
    status: Literal["ok", "stale", "error"] = "ok"

    model_config = {"populate_by_name": True}


class FrameStatus(BaseModel):
    provider: str
    connected: bool
    last_frame_at: Optional[str] = Field(default=None, alias="lastFrameAt")
    resolution: Resolution = Resolution()
    latency_ms: int = Field(0, alias="latencyMs")
    fps_approx: float = Field(0.0, alias="fpsApprox")
    error: Optional[str] = None

    model_config = {"populate_by_name": True}


class MouseClick(BaseModel):
    x: float
    y: float
    button: MouseButton = "left"
    source: Source = "user"


class MouseMove(BaseModel):
    x: float
    y: float
    source: Source = "user"


class MouseDrag(BaseModel):
    from_x: float = Field(alias="fromX")
    from_y: float = Field(alias="fromY")
    to_x: float = Field(alias="toX")
    to_y: float = Field(alias="toY")
    button: MouseButton = "left"
    source: Source = "user"

    model_config = {"populate_by_name": True}


class MouseScroll(BaseModel):
    x: float
    y: float
    delta_x: float = Field(0, alias="deltaX")
    delta_y: float = Field(0, alias="deltaY")
    source: Source = "user"

    model_config = {"populate_by_name": True}


class TypeText(BaseModel):
    text: str
    source: Source = "user"


class KeyPress(BaseModel):
    key: str
    source: Source = "user"


class Hotkey(BaseModel):
    keys: list[str]
    source: Source = "user"


class CommandResult(BaseModel):
    """Возвращается сразу после постановки в очередь HID."""

    command_id: str = Field(alias="commandId")
    status: CommandStatus = "queued"
    estimated_delay_ms: int = Field(0, alias="estimatedDelayMs")
    error: Optional[str] = None

    model_config = {"populate_by_name": True}


class HidQueueItem(BaseModel):
    command_id: str = Field(alias="commandId")
    type: str
    payload: dict[str, Any] = {}
    status: CommandStatus = "pending"
    enqueued_at: str = Field(alias="enqueuedAt")
    started_at: Optional[str] = Field(default=None, alias="startedAt")
    finished_at: Optional[str] = Field(default=None, alias="finishedAt")
    duration_ms: Optional[int] = Field(default=None, alias="durationMs")
    error: Optional[str] = None

    model_config = {"populate_by_name": True}