from core.functional import compose, pipe
from core.services import BudgetService, ReportService


def test_compose_simple():
    def add1(x):
        return x + 1
    def mul2(x):
        return x * 2
    f = compose(add1, mul2)
    # compose(add1, mul2)(3) -> add1(mul2(3)) = add1(6) = 7
    assert f(3) == 7


def test_pipe_simple():
    def add1(x):
        return x + 1
    def mul2(x):
        return x * 2
    # pipe(3, add1, mul2) -> mul2(add1(3)) = mul2(4) = 8
    assert pipe(3, add1, mul2) == 8


def test_budgetservice_validators_and_calculators():
    # validator returns [] when ok
    def v_ok(month, transactions, budgets, categories):
        return []

    # calculator returns partial dict
    def c_total_spent(month, transactions, budgets, categories, acc=None):
        # simple: count negative amounts in transactions
        total = sum(-t['amount'] for t in transactions if t['amount'] < 0)
        return {'total_spent': total}

    transactions = [
        {'amount': -100},
        {'amount': -200},
        {'amount': 500}
    ]
    budgets = []
    categories = []

    svc = BudgetService(validators=[v_ok], calculators=[c_total_spent])
    rpt = svc.monthly_report('2024-01', transactions, budgets, categories)
    assert rpt['month'] == '2024-01'
    assert len(rpt['validation']) == 1
    assert rpt['validation'][0]['messages'] == []
    assert rpt['steps'][0]['output']['total_spent'] == 300
    assert rpt['result']['total_spent'] == 300


def test_reportservice_aggregator_sequence():
    def agg_count(cat_id, transactions, categories, acc=None):
        count = sum(1 for t in transactions if t.get('category_id') == cat_id)
        return {'count': count}

    transactions = [
        {'category_id': 'food'},
        {'category_id': 'food'},
        {'category_id': 'rent'},
    ]
    svc = ReportService(aggregators=[agg_count])
    rpt = svc.category_report('food', transactions, [])
    assert rpt['category'] == 'food'
    assert rpt['steps'][0]['output']['count'] == 2
    assert rpt['result']['count'] == 2


def test_budgetservice_validator_error_handling():
    def bad_validator(month, transactions, budgets, categories):
        raise RuntimeError('oops')

    def c_dummy(month, transactions, budgets, categories, acc=None):
        return {'x': 1}

    svc = BudgetService(validators=[bad_validator], calculators=[c_dummy])
    rpt = svc.monthly_report('m', [], [], [])
    assert 'validator_error' in rpt['validation'][0]['messages'][0]
    assert rpt['result']['x'] == 1
