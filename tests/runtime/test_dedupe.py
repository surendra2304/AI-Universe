import asyncio

import pytest

from app.inference_runtime.dedupe import RequestDeduper


@pytest.mark.asyncio
async def test_dedupe_shares_task():
    d = RequestDeduper()
    calls = 0

    async def f():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return 4

    out = await asyncio.gather(d.run("x", f), d.run("x", f))
    assert out == [4, 4] and calls == 1
