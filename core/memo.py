from core.domain import Transaction
from functools import lru_cache

@lru_cache(maxsize=None)
def forecast_expenses(category: str, transactions: tuple[Transaction, ...], months: int) -> float:

    values = [abs(t.amount) for t in transactions if t.cat_id == category]

    if not values:
        return 0.0

    avg_per_month = sum(values) / len(values)

    return avg_per_month
