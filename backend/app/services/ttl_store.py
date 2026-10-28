"""最終アクセスから一定時間で破棄するインメモリストア（アップロード・ディレクトリ両セッションの共通部分）。

ローカル単独利用を前提にした揮発ストアで、プロセス再起動で消える。単一ワーカー前提のためロックは持たない
（DESIGN.md: `--workers` は増やさない）。時刻はテストで差し替えられるよう clock として受け取る。
"""

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _Slot(Generic[T]):
    value: T
    last_access: float


class TTLStore(Generic[T]):
    def __init__(
        self,
        ttl_seconds: float,
        clock: Callable[[], float] = time.time,
        on_expire: Callable[[str, T], None] | None = None,
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._on_expire = on_expire
        self._slots: dict[str, _Slot[T]] = {}

    def add(self, value: T) -> str:
        self._purge_expired()
        entry_id = uuid.uuid4().hex
        self._slots[entry_id] = _Slot(value=value, last_access=self._clock())
        return entry_id

    def get(self, entry_id: str) -> T:
        """値を返し、最終アクセス時刻を更新する。無い・期限切れなら KeyError。"""
        slot = self._slots.get(entry_id)
        now = self._clock()
        if slot is None or self._is_expired(slot, now):
            self._expire(entry_id)
            raise KeyError(entry_id)
        slot.last_access = now
        return slot.value

    def delete(self, entry_id: str) -> None:
        self._slots.pop(entry_id, None)

    def _is_expired(self, slot: _Slot[T], now: float) -> bool:
        return now - slot.last_access > self._ttl

    def _expire(self, entry_id: str) -> None:
        slot = self._slots.pop(entry_id, None)
        if slot is not None and self._on_expire is not None:
            self._on_expire(entry_id, slot.value)

    def _purge_expired(self) -> None:
        now = self._clock()
        for entry_id in [i for i, s in self._slots.items() if self._is_expired(s, now)]:
            self._expire(entry_id)
