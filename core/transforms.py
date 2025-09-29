import json
from functools import reduce
from typing import Tuple
from core.domain import Account, Category, Transaction, Budget


def load_seed(
    path: str,
) -> Tuple[
    Tuple[Account, ...],
    Tuple[Category, ...],
    Tuple[Transaction, ...],
    Tuple[Budget, ...],
]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    accounts = tuple(Account(**a) for a in data["accounts"])
    categories = tuple(Category(**c) for c in data["categories"])
    transactions = tuple(Transaction(**t) for t in data["transactions"])
    budgets = tuple(Budget(**b) for b in data["budgets"])

    return accounts, categories, transactions, budgets


def add_transaction(
    trans: Tuple[Transaction, ...], t: Transaction
) -> Tuple[Transaction, ...]:
    return trans + (t,)


def update_budget(
    budgets: Tuple[Budget, ...], bid: str, new_limit: int
) -> Tuple[Budget, ...]:
    return tuple(
        Budget(
            id=b.id,
            cat_id=b.cat_id,
            limit=new_limit if b.id == bid else b.limit,
            period=b.period,
        )
        for b in budgets
    )


def account_balance(trans: Tuple[Transaction, ...], acc_id: str) -> int:
    return reduce(
        lambda acc, t: acc + t.amount if t.account_id == acc_id else acc, trans, 0
    )


def income_transactions(trans: Tuple[Transaction, ...]) -> Tuple[Transaction, ...]:
    return tuple(filter(lambda t: t.amount > 0, trans))


def expense_transactions(trans: Tuple[Transaction, ...]) -> Tuple[Transaction, ...]:
    return tuple(filter(lambda t: t.amount < 0, trans))


def transaction_amounts(trans: Tuple[Transaction, ...]) -> Tuple[int, ...]:
    return tuple(map(lambda t: t.amount, trans))
