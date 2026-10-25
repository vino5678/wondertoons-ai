from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable


class JobRunner:
    """Minimal in-process job runner. Jobs are lost if the server restarts
    (they stay 'queued'/'running' in the DB); a durable queue is a future step."""

    def __init__(self, max_workers: int, inline: bool = False):
        self._inline = inline
        self._pool = None if inline else ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="wt-job")

    def submit(self, fn: Callable, *args) -> None:
        if self._inline:
            fn(*args)
        else:
            self._pool.submit(fn, *args)

    def shutdown(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
