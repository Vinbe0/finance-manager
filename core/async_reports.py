import asyncio
from typing import List, Dict
from core.domain import Transaction, Account
from collections import defaultdict


async def expenses_by_month(trans: List[Transaction], months: List[str]) -> Dict[str, int]:
    """Compute total expenses per month in parallel for given months.

    months: list of YYYY-MM strings (e.g., '2025-01')
    Returns mapping month->total_expense (positive int representing absolute expense)
    """
    async def month_total(month: str) -> tuple[str, int]:
        # simulate async work
        total = 0
        ym = month
        for t in trans:
            ts = getattr(t, "ts", None)
            try:
                # allow ts like '2025-01-03' or pandas Timestamp string
                if ts and str(ts).startswith(ym) and getattr(t, "amount", 0) < 0:
                    total += abs(int(t.amount))
            except Exception:
                continue
        await asyncio.sleep(0)  # cooperate
        return month, total

    results = await asyncio.gather(*(month_total(m) for m in months))
    return {k: v for k, v in results}


async def balance_forecast(accounts: List[Account], trans: List[Transaction]) -> Dict[str, int]:
    """Produce a simple balance forecast per account in parallel.

    For each account, sum transactions for that account and add to the account.balance
    to produce a forecasted balance.
    """
    async def acc_forecast(a: Account) -> tuple[str, int]:
        acct_id = a.id
        acc_balance = a.balance
        tx_sum = 0
        for t in trans:
            if getattr(t, "account_id", None) == acct_id:
                tx_sum += int(getattr(t, "amount", 0))
        await asyncio.sleep(0)
        return acct_id, acc_balance + tx_sum

    results = await asyncio.gather(*(acc_forecast(a) for a in accounts))
    return {k: v for k, v in results}
