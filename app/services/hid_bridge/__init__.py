"""HID Bridge — абстракция над исполнителем (ESP32 / mock)."""

from __future__ import annotations

from .base import HidBridge, HidCommand
from .factory import build_bridge

__all__ = ["HidBridge", "HidCommand", "build_bridge"]
