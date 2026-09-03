import asyncio

import pytest

from app.inference_runtime.scheduler import FairScheduler


@pytest.mark.asyncio
async def test_scheduler_runs_job():
    s = FairScheduler()
    task = asyncio.create_task(s.run(lambda x: asyncio.sleep(0.001, result=x), 1))
    out = await s.submit("a")
    assert out == "a"
    await s.stop()
    task.cancel()
