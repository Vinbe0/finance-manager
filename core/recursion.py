from core.domain import Category, Transaction


def by_category(cat_id: str):
    def _filter(t: Transaction) -> bool:
        return t.cat_id == cat_id

    return _filter


def by_date_range(start: str, end: str):
    def _filter(t: Transaction) -> bool:
        return start <= t.ts <= end

    return _filter


def by_amount_range(min: int, max: int):
    def _filter(t: Transaction) -> bool:
        return min <= t.amount <= max

    return _filter


def flatten_categories(cats: tuple[Category, ...], root: str) -> tuple[Category, ...]:
    children = tuple(c for c in cats if c.parent_id == root)
    result = children
    for child in children:
        result += flatten_categories(cats, child.id)
    return result


def sum_expenses_recursive(
    cats: tuple[Category, ...], 
    trans: tuple[Transaction, ...], 
    root_id: str, 
    visited: set[str] | None = None
) -> int:
    if visited is None:
        visited = set()
    if root_id in visited:
        return 0
    visited.add(root_id)

    children = [c for c in cats if c.parent_id == root_id]

    total = sum(t.amount for t in trans if t.cat_id == root_id and t.amount < 0)

    for child in children:
        total += sum_expenses_recursive(cats, trans, child.id, visited)

    return total


