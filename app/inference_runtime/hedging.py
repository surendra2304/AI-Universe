from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


async def _run(fn: Callable[[], Awaitable[T]]) -> T:
    return await fn()


async def hedge(callers: list[Callable[[], Awaitable[T]]], delay_seconds: float = 0.2) -> T:
    if not callers:
        raise ValueError("at least one caller required")
    tasks: list[asyncio.Task[T]] = []
    try:
        for i, fn in enumerate(callers):
            if i:
                await asyncio.sleep(delay_seconds)
            tasks.append(asyncio.create_task(_run(fn)))
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for d in done:
                exc = d.exception()
                if exc is None:
                    return d.result()
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        return next(iter(done)).result()
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
