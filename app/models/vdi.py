from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

MouseButton = Literal["left", "right", "middle"]
Source = Literal["user", "agent", "scenario"]


class Resolution(BaseModel):
    width: int = 1920
    height: int = 1080


class VdiFrame(BaseModel):
    frame_id: str = Field(alias="frameId")
    timestamp: str
    image_url: Optional[str] = Field(default=None, alias="imageUrl")
    resolution: Resolution = Resolution()

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
    ok: bool = True
