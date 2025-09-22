from core.domain import Transaction, Budget
from core.transforms import add_transaction, update_budget, account_balance, load_seed


def test_add_transaction():
    t1 = Transaction(
        id="t1",
        account_id="a1",
        cat_id="c1",
        amount=100,
        ts="2025-09-01",
        note="Salary",
    )
    t2 = Transaction(
        id="t2",
        account_id="a1",
        cat_id="c2",
        amount=-50,
        ts="2025-09-02",
        note="Groceries",
    )

    transactions = (t1,)
    new_transactions = add_transaction(transactions, t2)

    assert len(new_transactions) == 2
    assert transactions != new_transactions


def test_update_budget():
    b1 = Budget(id="b1", cat_id="c1", limit=300, period="month")
    b2 = Budget(id="b2", cat_id="c2", limit=150, period="month")

    budgets = (b1, b2)
    new_budgets = update_budget(budgets, "b1", 500)

    assert new_budgets[0].limit == 500
    assert budgets[0].limit == 300


def test_account_balance():
    t1 = Transaction(
        id="t1",
        account_id="a1",
        cat_id="c1",
        amount=100,
        ts="2025-09-01",
        note="Salary",
    )
    t2 = Transaction(
        id="t2",
        account_id="a1",
        cat_id="c2",
        amount=-50,
        ts="2025-09-02",
        note="Groceries",
    )
    t3 = Transaction(
        id="t3",
        account_id="a2",
        cat_id="c3",
        amount=200,
        ts="2025-09-03",
        note="Freelance",
    )

    transactions = (t1, t2, t3)
    balance_a1 = account_balance(transactions, "a1")

    assert balance_a1 == 50


def test_load_seed():
    accounts, categories, transactions, budgets = load_seed("data/seed.json")

    assert len(accounts) >= 3
    assert len(categories) >= 10
    assert len(transactions) >= 5
    assert len(budgets) >= 3


def test_add_transaction_immutability():
    t1 = Transaction(
        id="t1",
        account_id="a1",
        cat_id="c1",
        amount=100,
        ts="2025-09-01",
        note="Salary",
    )
    transactions = (t1,)
    new_transactions = add_transaction(transactions, t1)

    assert new_transactions is not transactions
    assert len(new_transactions) == 2
    assert len(transactions) == 1
