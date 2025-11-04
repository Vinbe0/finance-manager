from collections import defaultdict
from typing import Callable, Iterable, Iterator, Tuple

from core.domain import Category, Transaction


def iter_transactions(
    trans: tuple[Transaction, ...], pred: Callable[[Transaction], bool]
) -> Iterable[Transaction]:
    for t in trans:
        if pred(t):
            yield t


def lazy_top_categories(
    trans: Iterable[Transaction], cats: tuple[Category, ...], k: int
) -> Iterator[tuple[str, int]]:
    category_name_by_id: dict[str, str] = {c.id: c.name for c in cats}
    totals_by_category: dict[str, int] = defaultdict(int)

    for t in trans:
        if t.amount < 0:
            totals_by_category[t.cat_id] += -t.amount

    ordered: list[Tuple[str, int]] = sorted(
        ((category_name_by_id.get(cid, cid), total) for cid, total in totals_by_category.items()),
        key=lambda item: item[1],
        reverse=True,
    )

    for name, total in ordered[: max(0, k)]:
        yield name, total
