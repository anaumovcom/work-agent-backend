from __future__ import annotations

import logging

from ...core.config import get_settings
from .base import HidBridge

log = logging.getLogger(__name__)


def build_bridge() -> HidBridge:
    s = get_settings()
    kind = s.hid_bridge
    if kind == "esp32_http":
        from .esp32_http_bridge import Esp32HttpHidBridge

        return Esp32HttpHidBridge()
    if kind == "esp32_ws":
        from .esp32_ws_bridge import Esp32WebSocketHidBridge

        return Esp32WebSocketHidBridge()
    from .mock_bridge import MockHidBridge

    return MockHidBridge()
