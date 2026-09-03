import asyncio

import pytest

from app.inference_runtime.backpressure import BackpressureGate


@pytest.mark.asyncio
async def test_backpressure_releases():
    g = BackpressureGate(1)
    await g.enter()
    done = False

    async def f():
        nonlocal done
        async with g:
            done = True

    t = asyncio.create_task(f())
    await asyncio.sleep(0.001)
    assert not done
    await g.leave()
    await t
    assert done
