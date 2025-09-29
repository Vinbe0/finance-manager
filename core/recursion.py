from typing import Tuple
from core.domain import Category, Transaction


def get_subcategories(categories: Tuple[Category, ...], parent_id: str) -> Tuple[Category, ...]:

    subs = tuple(c for c in categories if c.parent_id == parent_id)

    deeper = tuple(
        sub for c in subs for sub in get_subcategories(categories, c.id)
    )

    return subs + deeper


def sum_by_category(
    transactions: Tuple[Transaction, ...],
    categories: Tuple[Category, ...],
    cat_id: str,
) -> int:
    
    subcats = get_subcategories(categories, cat_id)
    subcat_ids = {c.id for c in subcats} | {cat_id}

    total = sum(t.amount for t in transactions if t.cat_id in subcat_ids)
    return total
