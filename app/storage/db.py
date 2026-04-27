from __future__ import annotations

import itertools
import threading
from typing import Generic, Iterable, TypeVar

T = TypeVar("T")


class Counter:
    def __init__(self, start: int = 0) -> None:
        self._counter = itertools.count(start + 1)
        self._lock = threading.Lock()

    def next(self) -> int:
        with self._lock:
            return next(self._counter)


class Repository(Generic[T]):
    def __init__(self) -> None:
        self._items: dict[str, T] = {}
        self._lock = threading.Lock()

    def all(self) -> list[T]:
        with self._lock:
            return list(self._items.values())

    def get(self, item_id: str) -> T | None:
        with self._lock:
            return self._items.get(item_id)

    def put(self, item_id: str, item: T) -> T:
        with self._lock:
            self._items[item_id] = item
            return item

    def delete(self, item_id: str) -> bool:
        with self._lock:
            return self._items.pop(item_id, None) is not None

    def bulk_load(self, items: Iterable[tuple[str, T]]) -> None:
        with self._lock:
            for item_id, item in items:
                self._items[item_id] = item
