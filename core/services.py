from typing import Callable, Iterable, List, Dict, Any, Sequence


class BudgetService:
    """Facade for budget-related operations using injected validators and calculators.

    validators: sequence of functions taking (month, transactions, budgets, categories) -> Sequence[str]
    calculators: sequence of functions taking (month, transactions, budgets, categories) -> dict (partial results)
    """

    def __init__(self, validators: Sequence[Callable[..., Sequence[str]]], calculators: Sequence[Callable[..., Dict[str, Any]]]):
        self.validators = validators
        self.calculators = calculators

    def monthly_report(self, month: str, transactions: Iterable, budgets: Iterable, categories: Iterable) -> Dict[str, Any]:
        """Run validators and calculators and return an aggregated report with intermediate steps."""
        report = {
            "month": month,
            "validation": [],
            "steps": [],
            "result": {}
        }

        # run validators (pure functions) and collect messages
        for v in self.validators:
            try:
                msgs = v(month, transactions, budgets, categories)
            except Exception as e:
                msgs = [f"validator_error: {e}"]
            report["validation"].append({"validator": getattr(v, "__name__", str(v)), "messages": list(msgs)})

        # run calculators sequentially and capture intermediate outputs
        acc = {}
        for calc in self.calculators:
            try:
                out = calc(month, transactions, budgets, categories, acc)
            except TypeError:
                # older calculators may ignore acc
                out = calc(month, transactions, budgets, categories)
            report["steps"].append({"calculator": getattr(calc, "__name__", str(calc)), "output": out})
            if isinstance(out, dict):
                acc.update(out)

        report["result"] = acc
        return report


class ReportService:
    """Facade for generating reports about categories using injected aggregators."""

    def __init__(self, aggregators: Sequence[Callable[..., Dict[str, Any]]]):
        self.aggregators = aggregators

    def category_report(self, cat_id: str, transactions: Iterable, categories: Iterable) -> Dict[str, Any]:
        report = {"category": cat_id, "steps": [], "result": {}}
        acc = {}
        for agg in self.aggregators:
            try:
                out = agg(cat_id, transactions, categories, acc)
            except TypeError:
                out = agg(cat_id, transactions, categories)
            report["steps"].append({"aggregator": getattr(agg, "__name__", str(agg)), "output": out})
            if isinstance(out, dict):
                acc.update(out)
        report["result"] = acc
        return report
