from core.domain import Transaction, Category
from core.recursion import (
    by_category,
    by_date_range,
    by_amount_range,
    flatten_categories,
    sum_expenses_recursive,
)


def test_by_category():
    t1 = Transaction("t1", "a1", "food", -1000, "2024-05-01", "groceries")
    t2 = Transaction("t2", "a1", "transport", -500, "2024-05-02", "bus")
    result = list(filter(by_category("food"), [t1, t2]))
    assert len(result) == 1
    assert result[0].id == "t1"


def test_by_date_range():
    t1 = Transaction("t1", "a1", "food", -1000, "2024-05-01", "groceries")
    t2 = Transaction("t2", "a1", "food", -500, "2023-05-01", "old")
    result = list(filter(by_date_range("2024-01-01", "2024-12-31"), [t1, t2]))
    assert len(result) == 1
    assert result[0].id == "t1"


def test_by_amount_range():
    t1 = Transaction("t1", "a1", "food", -2000, "2024-05-01", "groceries")
    t2 = Transaction("t2", "a1", "food", -8000, "2024-05-01", "big expense")
    result = list(filter(by_amount_range(-5000, -1000), [t1, t2]))
    assert len(result) == 1
    assert result[0].id == "t1"


def test_flatten_categories():
    cats = (
        Category("c1", "Food", None, "expense"),
        Category("c2", "Groceries", "c1", "expense"),
        Category("c3", "Fruits", "c2", "expense"),
    )
    subs = flatten_categories(cats, "c1")
    assert len(subs) == 2  # Groceries + Fruits
    assert {c.id for c in subs} == {"c2", "c3"}


def test_sum_expenses_recursive():
    cats = (
        Category("c1", "Food", None, "expense"),
        Category("c2", "Groceries", "c1", "expense"),
    )
    trans = (
        Transaction("t1", "a1", "c1", -1000, "2024-05-01", "restaurant"),
        Transaction("t2", "a1", "c2", -2000, "2024-05-02", "groceries"),
    )
    total = sum_expenses_recursive(cats, trans, "c1")
    assert total == -3000
