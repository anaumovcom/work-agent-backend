from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HidCommand:
    id: str
    type: str  # "mouse.click" | "mouse.move" | "mouse.drag" | "mouse.scroll"
                # | "mouse.double_click" | "keyboard.type" | "keyboard.key"
                # | "keyboard.hotkey" | "system.stop"
    payload: dict[str, Any] = field(default_factory=dict)


class HidBridge:
    name: str = "base"

    @property
    def connected(self) -> bool:  # pragma: no cover
        return True

    async def start(self) -> None:  # pragma: no cover
        pass

    async def ping(self) -> bool:  # pragma: no cover
        return self.connected

    def diagnostics(self) -> dict[str, Any]:
        return {"bridge": self.name, "connected": self.connected}

    async def stop(self) -> None:  # pragma: no cover
        pass

    async def execute(self, cmd: HidCommand) -> None:  # pragma: no cover
        raise NotImplementedError

    async def system_stop(self) -> None:
        await self.execute(HidCommand(id="sys_stop", type="system.stop"))
