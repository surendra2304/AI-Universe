from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass
class BatchItem(Generic[T]):
    payload: T
    future: asyncio.Future
    submitted_at: float


class MicroBatcher(Generic[T]):
    def __init__(self, max_batch: int = 16, max_wait_ms: int = 15):
        self.max_batch = max(1, max_batch)
        self.max_wait = max_wait_ms / 1000
        self._q: list[BatchItem[T]] = []
        self._cv = asyncio.Condition()
        self._task: asyncio.Task[None] | None = None
        self._closed = False

    async def start(self, worker: Callable[[list[T]], Awaitable[list[object]]]):
        self._task = asyncio.create_task(self._run(worker))

    async def submit(self, payload: T):
        fut = asyncio.get_running_loop().create_future()
        async with self._cv:
            self._q.append(BatchItem(payload, fut, time.monotonic()))
            self._cv.notify()
        return await fut

    async def _run(self, worker):
        while not self._closed:
            async with self._cv:
                while not self._q and not self._closed:
                    await self._cv.wait()
                if self._closed:
                    break
                start = time.monotonic()
                while len(self._q) < self.max_batch and time.monotonic() - start < self.max_wait:
                    try:
                        await asyncio.wait_for(self._cv.wait(), self.max_wait - (time.monotonic() - start))
                    except asyncio.TimeoutError:
                        break
                batch = self._q[: self.max_batch]
                del self._q[: self.max_batch]
            try:
                results = await worker([x.payload for x in batch])
                if len(results) != len(batch):
                    raise RuntimeError("batch worker returned incorrect result count")
                for item, result in zip(batch, results):
                    if not item.future.done():
                        item.future.set_result(result)
            except Exception as exc:
                for item in batch:
                    if not item.future.done():
                        item.future.set_exception(exc)

    async def close(self):
        self._closed = True
        async with self._cv:
            self._cv.notify_all()
        if self._task:
            await self._task
