from core.functional import (
    Maybe, Some, Nothing, Either, Left, Right,
    safe_category, validate_transaction, check_budget
)
from core.domain import Category, Transaction, Account, Budget


def test_maybe_map():
    maybe_value = Some(5)
    doubled = maybe_value.map(lambda x: x * 2)
    
    assert doubled.is_some()
    assert doubled.get_or_else(0) == 10
    
    nothing = Nothing()
    mapped_nothing = nothing.map(lambda x: x * 2)
    assert mapped_nothing.is_none()
    assert mapped_nothing.get_or_else(0) == 0


def test_maybe_bind():
    def safe_divide(x: int) -> Maybe[int]:
        if x == 0:
            return Nothing()
        return Some(10 // x)
    
    some_value = Some(2)
    result = some_value.bind(safe_divide)
    assert result.is_some()
    assert result.get_or_else(0) == 5
    
    zero_value = Some(0)
    result_zero = zero_value.bind(safe_divide)
    assert result_zero.is_none()
    
    nothing = Nothing()
    result_nothing = nothing.bind(safe_divide)
    assert result_nothing.is_none()


def test_either_map():
    right_value = Right(5)
    doubled = right_value.map(lambda x: x * 2)
    
    assert doubled.is_right()
    assert doubled.get_or_else(0) == 10
    
    left_value = Left("error")
    mapped_left = left_value.map(lambda x: x * 2)
    assert mapped_left.is_left()
    assert mapped_left.get_or_else(0) == 0
    assert mapped_left.get_error() == "error"


def test_either_bind():
    def safe_divide(x: int) -> Either[str, int]:
        if x == 0:
            return Left("Division by zero")
        return Right(10 // x)
    
    right_value = Right(2)
    result = right_value.bind(safe_divide)
    assert result.is_right()
    assert result.get_or_else(0) == 5
    
    right_zero = Right(0)
    result_error = right_zero.bind(safe_divide)
    assert result_error.is_left()
    assert result_error.get_error() == "Division by zero"
    
    left_value = Left("original error")
    result_left = left_value.bind(safe_divide)
    assert result_left.is_left()
    assert result_left.get_error() == "original error"


def test_safe_category():
    categories = (
        Category("cat1", "Food", None, "expense"),
        Category("cat2", "Transport", None, "expense"),
    )
    
    result = safe_category(categories, "cat1")
    assert result.is_some()
    category = result.get_or_else(None)
    assert category is not None
    assert category.name == "Food"
    
    result_none = safe_category(categories, "nonexistent")
    assert result_none.is_none()
    assert result_none.get_or_else(None) is None


def test_validate_transaction_success():
    accounts = (Account("acc1", "Kaspi", 1000, "KZT"),)
    categories = (Category("cat1", "Food", None, "expense"),)
    
    transaction = Transaction("t1", "acc1", "cat1", -100, "2025-01-01", "Groceries")
    result = validate_transaction(transaction, accounts, categories)
    
    assert result.is_right()
    validated_transaction = result.get_or_else(None)
    assert validated_transaction is not None
    assert validated_transaction.id == "t1"


def test_validate_transaction_account_not_found():
    accounts = (Account("acc1", "Kaspi", 1000, "KZT"),)
    categories = (Category("cat1", "Food", None, "expense"),)
    
    transaction = Transaction("t1", "nonexistent", "cat1", -100, "2025-01-01", "Groceries")
    result = validate_transaction(transaction, accounts, categories)
    
    assert result.is_left()
    error = result.get_error()
    assert error["error"] == "account_not_found"
    assert "nonexistent" in error["message"]


def test_validate_transaction_category_not_found():
    accounts = (Account("acc1", "Kaspi", 1000, "KZT"),)
    categories = (Category("cat1", "Food", None, "expense"),)
    
    transaction = Transaction("t1", "acc1", "nonexistent", -100, "2025-01-01", "Groceries")
    result = validate_transaction(transaction, accounts, categories)
    
    assert result.is_left()
    error = result.get_error()
    assert error["error"] == "category_not_found"
    assert "nonexistent" in error["message"]


def test_validate_transaction_category_type_mismatch():
    accounts = (Account("acc1", "Kaspi", 1000, "KZT"),)
    categories = (
        Category("cat1", "Food", None, "expense"),
        Category("cat2", "Salary", None, "income"),
    )
    
    transaction = Transaction("t1", "acc1", "cat2", -100, "2025-01-01", "Salary")
    result = validate_transaction(transaction, accounts, categories)
    
    assert result.is_left()
    error = result.get_error()
    assert error["error"] == "category_type_mismatch"
    assert "Income category" in error["message"]
    
    transaction2 = Transaction("t2", "acc1", "cat1", 100, "2025-01-01", "Food")
    result2 = validate_transaction(transaction2, accounts, categories)
    
    assert result2.is_left()
    error2 = result2.get_error()
    assert error2["error"] == "category_type_mismatch"
    assert "Expense category" in error2["message"]


def test_check_budget_success():
    budget = Budget("b1", "cat1", 1000, "month")
    transactions = (
        Transaction("t1", "acc1", "cat1", -300, "2025-01-01", "Groceries"),
        Transaction("t2", "acc1", "cat1", -200, "2025-01-02", "Restaurant"),
    )
    
    result = check_budget(budget, transactions)
    assert result.is_right()
    validated_budget = result.get_or_else(None)
    assert validated_budget is not None
    assert validated_budget.id == "b1"


def test_check_budget_exceeded():
    budget = Budget("b1", "cat1", 1000, "month")
    transactions = (
        Transaction("t1", "acc1", "cat1", -300, "2025-01-01", "Groceries"),
        Transaction("t2", "acc1", "cat1", -200, "2025-01-02", "Restaurant"),
        Transaction("t3", "acc1", "cat1", -600, "2025-01-03", "Expensive meal"),
    )
    
    result = check_budget(budget, transactions)
    assert result.is_left()
    error = result.get_error()
    assert error["error"] == "budget_exceeded"
    assert error["limit"] == 1000
    assert error["spent"] == 1100
    assert error["over_budget"] == 100


def test_check_budget_ignores_income():
    budget = Budget("b1", "cat1", 1000, "month")
    transactions = (
        Transaction("t1", "acc1", "cat1", -300, "2025-01-01", "Groceries"),
        Transaction("t2", "acc1", "cat1", 5000, "2025-01-02", "Salary"),
        Transaction("t3", "acc1", "cat1", -200, "2025-01-03", "Restaurant"),
    )
    
    result = check_budget(budget, transactions)
    assert result.is_right()
    validated_budget = result.get_or_else(None)
    assert validated_budget is not None


def test_check_budget_different_categories():
    budget = Budget("b1", "cat1", 1000, "month")
    transactions = (
        Transaction("t1", "acc1", "cat1", -300, "2025-01-01", "Food"),
        Transaction("t2", "acc1", "cat2", -800, "2025-01-02", "Transport"),
        Transaction("t3", "acc1", "cat1", -200, "2025-01-03", "More Food"),
    )
    
    result = check_budget(budget, transactions)
    assert result.is_right()
    validated_budget = result.get_or_else(None)
    assert validated_budget is not None
