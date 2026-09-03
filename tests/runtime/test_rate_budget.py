import asyncio

import pytest

from app.inference_runtime.budget import BudgetLedger
from app.inference_runtime.errors import BudgetExceeded
from app.inference_runtime.rate_limit import AsyncTokenBucket


@pytest.mark.asyncio
async def test_token_bucket_concurrency():
    b = AsyncTokenBucket(100, 2)
    await asyncio.gather(*(b.acquire() for _ in range(4)))


def test_budget_reservation_and_reconcile():
    b = BudgetLedger(1)
    b.reserve("t", 0.6)
    assert round(b.remaining("t"), 2) == 0.4
    b.reconcile("t", 0.6, 0.2)
    assert round(b.remaining("t"), 2) == 0.8


def test_budget_rejects():
    b = BudgetLedger(1)
    b.reserve("t", 0.8)
    with pytest.raises(BudgetExceeded):
        b.reserve("t", 0.3)
