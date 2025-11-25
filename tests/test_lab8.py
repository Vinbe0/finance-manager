import asyncio
import pytest
from core.async_reports import expenses_by_month, balance_forecast
from core.domain import Transaction, Account


def make_tx(id, acc_id, cat_id, amount, ts):
    return Transaction(id=id, account_id=acc_id, cat_id=cat_id, amount=amount, ts=ts, note="")


def make_acc(id, name, balance):
    return Account(id=id, name=name, balance=balance, currency="KZT")


@pytest.mark.asyncio
async def test_expenses_by_month_simple():
    trans = [
        make_tx("t1", "a1", "c1", -100, "2025-01-02"),
        make_tx("t2", "a1", "c2", -200, "2025-01-15"),
        make_tx("t3", "a2", "c1", -50, "2025-02-05"),
        make_tx("t4", "a2", "c2", 300, "2025-01-20"),
    ]
    months = ["2025-01", "2025-02"]
    res = await expenses_by_month(trans, months)
    import asyncio
    import pytest
    from core.async_reports import expenses_by_month, balance_forecast
    from core.domain import Transaction, Account


    def make_tx(id, acc_id, cat_id, amount, ts):
        return Transaction(id=id, account_id=acc_id, cat_id=cat_id, amount=amount, ts=ts, note="")


    def make_acc(id, name, balance):
        return Account(id=id, name=name, balance=balance, currency="KZT")


    @pytest.mark.asyncio
    async def test_expenses_by_month_simple():
        trans = [
            make_tx("t1", "a1", "c1", -100, "2025-01-02"),
            make_tx("t2", "a1", "c2", -200, "2025-01-15"),
            make_tx("t3", "a2", "c1", -50, "2025-02-05"),
            make_tx("t4", "a2", "c2", 300, "2025-01-20"),
        ]
        months = ["2025-01", "2025-02"]
        res = await expenses_by_month(trans, months)
        assert res["2025-01"] == 300
        assert res["2025-02"] == 50


    @pytest.mark.asyncio
    async def test_expenses_by_month_empty_month():
        trans = [make_tx("t1", "a1", "c1", -500, "2025-03-10")]
        months = ["2025-01", "2025-03"]
        res = await expenses_by_month(trans, months)
        assert res["2025-01"] == 0
        assert res["2025-03"] == 500


    @pytest.mark.asyncio
    async def test_balance_forecast_simple():
        accounts = [make_acc("a1", "Kaspi", 1000), make_acc("a2", "Halyk", 2000)]
        trans = [
            make_tx("t1", "a1", "c1", -300, "2025-01-02"),
            make_tx("t2", "a1", "c2", 200, "2025-01-05"),
            make_tx("t3", "a2", "c1", -500, "2025-01-06"),
        ]
        res = await balance_forecast(accounts, trans)
        assert res["a1"] == 900  # 1000 + (-300 + 200)
        assert res["a2"] == 1500


    def test_end_to_end_aggregation_and_forecast():
        # run both reports concurrently using asyncio
        accounts = [make_acc("a1", "Kaspi", 1000), make_acc("a2", "Halyk", 2000)]
        trans = [
            make_tx("t1", "a1", "c1", -100, "2025-01-02"),
            make_tx("t2", "a1", "c2", -200, "2025-01-15"),
            make_tx("t3", "a2", "c1", -50, "2025-02-05"),
        ]
        months = ["2025-01", "2025-02"]

        async def run_both():
            return await asyncio.gather(expenses_by_month(trans, months), balance_forecast(accounts, trans))

        exp_res, bal_res = asyncio.run(run_both())
        assert exp_res["2025-01"] == 300
        assert exp_res["2025-02"] == 50
        assert bal_res["a1"] == 700  # 1000 + (-100 -200)
        assert bal_res["a2"] == 1950


    @pytest.mark.asyncio
    async def test_concurrent_month_tasks_scale():
        # ensure asyncio.gather runs per-month tasks concurrently (smoke test)
        trans = [make_tx(str(i), "a1", "c1", -10, "2025-01-01") for i in range(100)]
        months = ["2025-01", "2025-02", "2025-03", "2025-04"]
        res = await expenses_by_month(trans, months)
        assert res["2025-01"] == 1000
        assert res["2025-02"] == 0