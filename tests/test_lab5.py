from itertools import islice
from typing import Iterable

from core.domain import Category, Transaction
from core.lazy import iter_transactions, lazy_top_categories


def make_sample():
    cats = (
        Category("c1", "Food", None, "expense"),
        Category("c2", "Transport", None, "expense"),
        Category("c3", "Salary", None, "income"),
    )
    trans = (
        Transaction("t1", "a1", "c1", -300, "2025-01-01", "Groceries"),
        Transaction("t2", "a1", "c2", -200, "2025-01-02", "Bus"),
        Transaction("t3", "a1", "c3", 5000, "2025-01-03", "Salary"),
        Transaction("t4", "a1", "c1", -700, "2025-01-04", "Restaurant"),
        Transaction("t5", "a1", "c2", -100, "2025-01-05", "Taxi"),
    )
    return cats, trans


def test_iter_transactions_filters_expenses_only():
    cats, trans = make_sample()
    result = list(iter_transactions(trans, lambda t: t.amount < 0))
    assert len(result) == 4
    assert all(t.amount < 0 for t in result)


def test_iter_transactions_is_lazy_stop_early():
    _, trans = make_sample()
    calls = {"n": 0}

    def pred(t: Transaction) -> bool:
        calls["n"] += 1
        return t.amount < 0

    gen = iter_transactions(trans, pred)
    first_two = list(islice(gen, 2))

    assert len(first_two) == 2
    assert calls["n"] < len(trans)


def test_lazy_top_categories_basic_sum_and_order():
    cats, trans = make_sample()
    result = list(lazy_top_categories(trans, cats, k=2))
    assert result[0][0] == "Food"
    assert result[0][1] == 1000
    assert result[1][0] == "Transport"
    assert result[1][1] == 300


def test_lazy_top_categories_ignores_income_and_maps_names():
    cats, trans = make_sample()
    names = [name for name, _ in lazy_top_categories(trans, cats, k=3)]
    assert "Salary" not in names
    assert set(names) >= {"Food", "Transport"}


def test_lazy_top_categories_accepts_generator_input():
    cats, trans = make_sample()

    def tx_stream() -> Iterable[Transaction]:
        for t in trans:
            yield t

    res = list(lazy_top_categories(tx_stream(), cats, k=1))
    assert res == [("Food", 1000)]


def test_lazy_top_categories_k_bigger_than_categories():
    cats, trans = make_sample()
    res = list(lazy_top_categories(trans, cats, k=10))
    assert len(res) == 2
