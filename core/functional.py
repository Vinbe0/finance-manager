from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Callable, Union
from core.domain import Category, Transaction, Account, Budget

T = TypeVar('T')
U = TypeVar('U')
E = TypeVar('E')


class Maybe(Generic[T], ABC):
    
    @abstractmethod
    def map(self, f: Callable[[T], U]) -> 'Maybe[U]':
        pass
    
    @abstractmethod
    def bind(self, f: Callable[[T], 'Maybe[U]']) -> 'Maybe[U]':
        pass
    
    @abstractmethod
    def get_or_else(self, default: T) -> T:
        pass
    
    @abstractmethod
    def is_some(self) -> bool:
        pass
    
    @abstractmethod
    def is_none(self) -> bool:
        pass


class Some(Generic[T], Maybe[T]):
    
    def __init__(self, value: T):
        self._value = value
    
    def map(self, f: Callable[[T], U]) -> 'Maybe[U]':
        return Some(f(self._value))
    
    def bind(self, f: Callable[[T], 'Maybe[U]']) -> 'Maybe[U]':
        return f(self._value)
    
    def get_or_else(self, default: T) -> T:
        return self._value
    
    def is_some(self) -> bool:
        return True
    
    def is_none(self) -> bool:
        return False
    
    def __repr__(self) -> str:
        return f"Some({self._value})"
    
    def __eq__(self, other) -> bool:
        return isinstance(other, Some) and self._value == other._value


class Nothing(Generic[T], Maybe[T]):
    
    def map(self, f: Callable[[T], U]) -> 'Maybe[U]':
        return Nothing()
    
    def bind(self, f: Callable[[T], 'Maybe[U]']) -> 'Maybe[U]':
        return Nothing()
    
    def get_or_else(self, default: T) -> T:
        return default
    
    def is_some(self) -> bool:
        return False
    
    def is_none(self) -> bool:
        return True
    
    def __repr__(self) -> str:
        return "Nothing()"
    
    def __eq__(self, other) -> bool:
        return isinstance(other, Nothing)


class Either(Generic[E, T], ABC):
    
    @abstractmethod
    def map(self, f: Callable[[T], U]) -> 'Either[E, U]':
        pass
    
    @abstractmethod
    def bind(self, f: Callable[[T], 'Either[E, U]']) -> 'Either[E, U]':
        pass
    
    @abstractmethod
    def get_or_else(self, default: T) -> T:
        pass
    
    @abstractmethod
    def is_right(self) -> bool:
        pass
    
    @abstractmethod
    def is_left(self) -> bool:
        pass
    
    @abstractmethod
    def get_error(self) -> E:
        pass


class Right(Generic[E, T], Either[E, T]):
    
    def __init__(self, value: T):
        self._value = value
    
    def map(self, f: Callable[[T], U]) -> 'Either[E, U]':
        return Right(f(self._value))
    
    def bind(self, f: Callable[[T], 'Either[E, U]']) -> 'Either[E, U]':
        return f(self._value)
    
    def get_or_else(self, default: T) -> T:
        return self._value
    
    def is_right(self) -> bool:
        return True
    
    def is_left(self) -> bool:
        return False
    
    def get_error(self) -> E:
        raise ValueError("Cannot get error from Right")
    
    def __repr__(self) -> str:
        return f"Right({self._value})"
    
    def __eq__(self, other) -> bool:
        return isinstance(other, Right) and self._value == other._value


class Left(Generic[E, T], Either[E, T]):
    
    def __init__(self, error: E):
        self._error = error
    
    def map(self, f: Callable[[T], U]) -> 'Either[E, U]':
        return Left(self._error)
    
    def bind(self, f: Callable[[T], 'Either[E, U]']) -> 'Either[E, U]':
        return Left(self._error)
    
    def get_or_else(self, default: T) -> T:
        return default
    
    def is_right(self) -> bool:
        return False
    
    def is_left(self) -> bool:
        return True
    
    def get_error(self) -> E:
        return self._error
    
    def __repr__(self) -> str:
        return f"Left({self._error})"
    
    def __eq__(self, other) -> bool:
        return isinstance(other, Left) and self._error == other._error




def safe_category(cats: tuple[Category, ...], cat_id: str) -> Maybe[Category]:
    for cat in cats:
        if cat.id == cat_id:
            return Some(cat)
    return Nothing()


def validate_transaction(
    t: Transaction, 
    accs: tuple[Account, ...], 
    cats: tuple[Category, ...]
) -> Either[dict, Transaction]:
    
    account_exists = any(acc.id == t.account_id for acc in accs)
    if not account_exists:
        return Left({
            "error": "account_not_found",
            "message": f"Account with ID {t.account_id} does not exist",
            "account_id": t.account_id
        })
    
    category_exists = any(cat.id == t.cat_id for cat in cats)
    if not category_exists:
        return Left({
            "error": "category_not_found", 
            "message": f"Category with ID {t.cat_id} does not exist",
            "category_id": t.cat_id
        })
    
    category = next(cat for cat in cats if cat.id == t.cat_id)
    if category.type == "income" and t.amount < 0:
        return Left({
            "error": "category_type_mismatch",
            "message": f"Income category {category.name} cannot have negative amount",
            "category_type": category.type,
            "amount": t.amount
        })
    elif category.type == "expense" and t.amount > 0:
        return Left({
            "error": "category_type_mismatch", 
            "message": f"Expense category {category.name} cannot have positive amount",
            "category_type": category.type,
            "amount": t.amount
        })
    
    return Right(t)


def check_budget(
    b: Budget, 
    trans: tuple[Transaction, ...]
) -> Either[dict, Budget]:
    category_expenses = sum(
        abs(t.amount) for t in trans 
        if t.cat_id == b.cat_id and t.amount < 0
    )
    
    if category_expenses > b.limit:
        return Left({
            "error": "budget_exceeded",
            "message": f"Budget limit exceeded for category {b.cat_id}",
            "category_id": b.cat_id,
            "limit": b.limit,
            "spent": category_expenses,
            "over_budget": category_expenses - b.limit
        })
    
    return Right(b)


# --- Functional utilities for composition / pipelines (Lab 7)
from typing import Iterable, Any


def compose(*funcs):
    """Return a function that's the composition of the given functions.

    compose(f, g, h)(x) == f(g(h(x)))
    Works left-to-right in the argument order provided.
    """
    def _composed(x):
        res = x
        for f in reversed(funcs):
            res = f(res)
        return res
    return _composed


def pipe(x, *funcs):
    """Pipe a value through a series of functions.

    pipe(x, f, g, h) == h(g(f(x)))
    Returns the final result.
    """
    res = x
    for f in funcs:
        res = f(res)
    return res
