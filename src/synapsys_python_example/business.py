"""Ordinary reusable business logic with no dependency on Synapsys."""

from __future__ import annotations

import math
import queue
import threading
import time
from collections import defaultdict


class ExampleServices:
    """Stateful stand-ins for databases, queues, APIs, and batch services."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._cache_entries = 0
        self._scratch_open = False
        self.work_queue: queue.Queue[str] = queue.Queue()
        for number in range(1, 9):
            self.work_queue.put(f"message-{number}")

    def next_count(self, name: str) -> int:
        with self._lock:
            self._counters[name] += 1
            return self._counters[name]

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "cacheEntries": self._cache_entries,
                "archiveScratchOpen": self._scratch_open,
                "queuedMessages": self.work_queue.qsize(),
            }

    def poll_invoices(self) -> int:
        tick = self.next_count("invoice-polls")
        return (tick * 17) % 6

    def reconcile_payments(self) -> int:
        tick = self.next_count("payment-reconciliations")
        return (tick * 13) % 9

    def warm_cache(self) -> int:
        with self._lock:
            self._cache_entries += 5
            return self._cache_entries

    def close_cache(self) -> int:
        with self._lock:
            released = self._cache_entries
            self._cache_entries = 0
            return released

    def open_archive_scratch(self) -> None:
        with self._lock:
            self._scratch_open = True

    def close_archive_scratch(self) -> bool:
        with self._lock:
            was_open = self._scratch_open
            self._scratch_open = False
            return was_open

    def simulate_io(self, seconds: float) -> None:
        time.sleep(seconds)

    def burn_cpu(self, iterations: int) -> float:
        sink = 0.0
        for number in range(iterations):
            sink += math.sqrt(number + 1) * math.sin(number)
        return sink

    def legacy_sync_batch(self) -> int:
        self.simulate_io(0.25)
        return self.next_count("legacy-records") * 11

    def calculate_tax(self, account: int) -> float:
        return round((account * 97.13) * 0.22, 2)
