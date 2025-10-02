import time
from core.memo import forecast_expenses
from core.domain import Transaction

def test_forecast_expenses_basic():
    trans = (
        Transaction(id="t1", account_id="a1", cat_id="food", amount=-100, ts="2024-01-01", note=""),
        Transaction(id="t2", account_id="a1", cat_id="food", amount=-200, ts="2024-02-01", note=""),
        Transaction(id="t3", account_id="a1", cat_id="food", amount=-300, ts="2024-03-01", note=""),
    )
    avg = forecast_expenses("food", trans, 3)
    assert avg == 200 

def test_forecast_expenses_empty():
    trans = ()
    avg = forecast_expenses("food", trans, 3)
    assert avg == 0

def test_forecast_expenses_one_transaction():
    trans = (
        Transaction(id="t1", account_id="a1", cat_id="food", amount=-500, ts="2024-01-01", note=""),
    )
    avg = forecast_expenses("food", trans, 3)
    assert avg == 500

def test_forecast_expenses_cache_speed():
    trans = tuple(
        Transaction(id=str(i), account_id="a1", cat_id="food", amount=-100, ts="2024-01-01", note="")
        for i in range(1000)
    )

    start = time.time()
    forecast_expenses("food", trans, 10)
    first_time = time.time() - start

    start = time.time()
    forecast_expenses("food", trans, 10)
    second_time = time.time() - start

    assert second_time <= first_time

def test_forecast_expenses_different_category():
    trans = (
        Transaction(id="t1", account_id="a1", cat_id="food", amount=-100, ts="2024-01-01", note=""),
        Transaction(id="t2", account_id="a1", cat_id="transport", amount=-400, ts="2024-01-01", note=""),
    )
    avg = forecast_expenses("transport", trans, 1)
    assert avg == 400
