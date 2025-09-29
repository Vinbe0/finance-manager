from core.domain import Category, Transaction
from core.recursion import get_subcategories, sum_by_category


def test_get_subcategories_simple():
    cats = (
        Category("c1", "Еда", None, "expense"),
        Category("c2", "Фрукты", "c1", "expense"),
        Category("c3", "Яблоки", "c2", "expense"),
    )
    subs = get_subcategories(cats, "c1")
    assert {c.id for c in subs} == {"c2", "c3"}


def test_sum_by_category_with_subs():
    cats = (
        Category("c1", "Еда", None, "expense"),
        Category("c2", "Фрукты", "c1", "expense"),
    )
    trans = (
        Transaction("t1", "a1", "c1", -100, "2025-01-01", ""),
        Transaction("t2", "a1", "c2", -200, "2025-01-02", ""),
    )
    total = sum_by_category(trans, cats, "c1")
    assert total == -300
