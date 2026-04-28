"""Очередь HID-команд: последовательное выполнение, emergency stop,
таймауты, события для UI."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..core.config import get_settings
from ..core.event_bus import bus
from ..models.vdi import HidQueueItem
from .hid_bridge import HidBridge, HidCommand, build_bridge

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"cmd_{uuid.uuid4().hex[:10]}"


class HidCommandQueue:
    def __init__(self) -> None:
        self._bridge: HidBridge | None = None
        self._items: list[HidQueueItem] = []
        self._lock = asyncio.Lock()
        self._wakeup = asyncio.Event()
        self._worker: Optional[asyncio.Task] = None
        self._after_action_tasks: set[asyncio.Task] = set()
        self._emergency_stop = False
        self._after_action_cb = None  # type: ignore[assignment]

    # ----- lifecycle -----
    async def start(self) -> None:
        self._bridge = build_bridge()
        try:
            await self._bridge.start()
        except Exception:  # pragma: no cover
            log.exception("HID bridge start failed")
        self._worker = asyncio.create_task(self._run())

    async def reconfigure(self) -> None:
        old_bridge = self._bridge
        self._bridge = build_bridge()
        if old_bridge is not None:
            try:
                await old_bridge.stop()
            except Exception:  # pragma: no cover
                log.exception("old HID bridge stop failed")
        try:
            await self._bridge.start()
        except Exception:  # pragma: no cover
            log.exception("HID bridge start failed")
        await bus.publish("hid.bridge.updated", self.bridge_diagnostics())

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()
        for task in list(self._after_action_tasks):
            task.cancel()
        if self._after_action_tasks:
            await asyncio.gather(*self._after_action_tasks, return_exceptions=True)
        if self._bridge:
            await self._bridge.stop()

    @property
    def bridge(self) -> HidBridge | None:
        return self._bridge

    async def refresh_bridge_status(self) -> bool:
        if self._bridge is None:
            return False
        try:
            return await self._bridge.ping()
        except Exception:
            log.exception("HID bridge ping failed")
            return False

    def bridge_diagnostics(self) -> dict:
        if self._bridge is None:
            return {"bridge": "none", "connected": False}
        return self._bridge.diagnostics()

    # ----- API -----
    def set_after_action_callback(self, cb) -> None:
        """Колбэк, который дёргается после успешной команды (refresh frame)."""
        self._after_action_cb = cb

    @property
    def emergency_stop_active(self) -> bool:
        return self._emergency_stop

    async def enqueue(self, type_: str, payload: dict) -> HidQueueItem:
        if self._emergency_stop:
            item = HidQueueItem(
                commandId=_new_id(),
                type=type_,
                payload=payload,
                status="failed",
                enqueuedAt=_now_iso(),
                error="emergency_stop_active",
            )
            await bus.publish("hid.command.failed", item.model_dump(by_alias=True))
            return item

        item = HidQueueItem(
            commandId=_new_id(),
            type=type_,
            payload=payload,
            status="pending",
            enqueuedAt=_now_iso(),
        )
        async with self._lock:
            self._items.append(item)
        await bus.publish("hid.command.queued", item.model_dump(by_alias=True))
        self._wakeup.set()
        return item

    def list(self) -> list[HidQueueItem]:
        return list(self._items)

    async def clear(self) -> int:
        async with self._lock:
            removed = [i for i in self._items if i.status in ("pending", "queued")]
            for i in removed:
                i.status = "cancelled"
                i.finished_at = _now_iso()
            self._items = [i for i in self._items if i.status not in ("cancelled",)]
        for i in removed:
            await bus.publish(
                "hid.command.failed",
                i.model_dump(by_alias=True),
            )
        await bus.publish("hid.queue.cleared", {"count": len(removed)})
        return len(removed)

    async def emergency_stop(self) -> None:
        self._emergency_stop = True
        await self.clear()
        if self._bridge is not None:
            try:
                await self._bridge.system_stop()
            except Exception:
                log.exception("system.stop failed")
        await bus.publish("emergency_stop.triggered", {"timestamp": _now_iso()})

    async def reset_emergency_stop(self) -> None:
        self._emergency_stop = False
        await bus.publish("emergency_stop.reset", {"timestamp": _now_iso()})

    # ----- worker -----
    async def _run(self) -> None:
        while True:
            try:
                timeout_s = get_settings().hid_command_timeout_ms / 1000
                await self._wakeup.wait()
                self._wakeup.clear()
                while True:
                    async with self._lock:
                        next_item = next(
                            (i for i in self._items if i.status == "pending"), None
                        )
                    if next_item is None:
                        break
                    if self._emergency_stop:
                        break
                    await self._process(next_item, timeout_s)
            except asyncio.CancelledError:
                break
            except Exception:  # pragma: no cover
                log.exception("hid queue worker error")

    async def _process(self, item: HidQueueItem, timeout_s: float) -> None:
        item.status = "running"
        item.started_at = _now_iso()
        await bus.publish("hid.command.running", item.model_dump(by_alias=True))
        t0 = time.monotonic()
        try:
            assert self._bridge is not None
            cmd = HidCommand(id=item.command_id, type=item.type, payload=item.payload)
            await asyncio.wait_for(self._bridge.execute(cmd), timeout=timeout_s)
            item.status = "done"
            item.duration_ms = int((time.monotonic() - t0) * 1000)
            item.finished_at = _now_iso()
            await bus.publish("hid.command.done", item.model_dump(by_alias=True))
            if self._after_action_cb is not None:
                self._schedule_after_action(item)
        except asyncio.TimeoutError:
            item.status = "failed"
            item.error = "timeout"
            item.duration_ms = int((time.monotonic() - t0) * 1000)
            item.finished_at = _now_iso()
            await bus.publish("hid.command.failed", item.model_dump(by_alias=True))
        except Exception as e:
            item.status = "failed"
            item.error = str(e)
            item.duration_ms = int((time.monotonic() - t0) * 1000)
            item.finished_at = _now_iso()
            await bus.publish("hid.command.failed", item.model_dump(by_alias=True))

    def _schedule_after_action(self, item: HidQueueItem) -> None:
        task = asyncio.create_task(self._run_after_action(item))
        self._after_action_tasks.add(task)
        task.add_done_callback(self._after_action_tasks.discard)

    async def _run_after_action(self, item: HidQueueItem) -> None:
        try:
            assert self._after_action_cb is not None
            await self._after_action_cb(item)
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover
            log.exception("after-action callback failed")


hid_queue = HidCommandQueue()
