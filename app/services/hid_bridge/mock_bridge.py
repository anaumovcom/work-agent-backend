from __future__ import annotations

import asyncio
import logging
import random

from .base import HidBridge, HidCommand

log = logging.getLogger(__name__)


class MockHidBridge(HidBridge):
    name = "mock"

    @property
    def connected(self) -> bool:
        return True

    async def execute(self, cmd: HidCommand) -> None:
        # имитируем небольшую задержку, как у реального HID
        delay = 0.01 + random.random() * 0.04
        await asyncio.sleep(delay)
        log.debug("mock HID exec %s %s", cmd.type, cmd.payload)
