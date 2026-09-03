from __future__ import annotations

import asyncio


class CancellationToken:
    def __init__(self):
        self.event = asyncio.Event()

    def cancel(self) -> None:
        self.event.set()

    @property
    def cancelled(self) -> bool:
        return self.event.is_set()

    async def wait(self) -> None:
        await self.event.wait()

    async def race(self, awaitable):
        task = asyncio.create_task(awaitable)
        cancel_task = asyncio.create_task(self.wait())
        done, pending = await asyncio.wait({task, cancel_task}, return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()
        if cancel_task in done:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise asyncio.CancelledError
        cancel_task.cancel()
        return task.result()
