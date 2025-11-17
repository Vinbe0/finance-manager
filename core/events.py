from typing import Callable, Dict, List, NamedTuple
from datetime import datetime
from core.domain import Transaction, Budget, Account

__all__ = ['event_bus', 'TRANSACTION_ADDED', 'BUDGET_ALERT', 'BALANCE_ALERT', 'Event', 'EventBus']

class Event(NamedTuple):
    name: str
    ts: str
    payload: dict

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Event, dict], dict]]] = {}

    def subscribe(self, name: str, handler: Callable[[Event, dict], dict]) -> None:
        if name not in self._subscribers:
            self._subscribers[name] = []
        self._subscribers[name].append(handler)

    def publish(self, name: str, payload: dict) -> List[dict]:
        if name not in self._subscribers:
            return []
        
        event = Event(
            name=name,
            ts=datetime.now().isoformat(),
            payload=payload
        )
        
        results = []
        for handler in self._subscribers[name]:
            result = handler(event, payload)
            results.append(result)
        return results

    def unsubscribe(self, name: str, handler: Callable[[Event, dict], dict]) -> None:
        if name in self._subscribers:
            if handler in self._subscribers[name]:
                self._subscribers[name].remove(handler)

TRANSACTION_ADDED = "TRANSACTION_ADDED"
BUDGET_ALERT = "BUDGET_ALERT"
BALANCE_ALERT = "BALANCE_ALERT"

event_bus = EventBus()

def update_balance_handler(event: Event, payload: dict) -> dict:
    amount = payload.get("amount", 0)
    return {"balance_delta": amount}

def check_budget_handler(event: Event, payload: dict) -> dict:
    amount = payload.get("amount", 0)
    category_id = payload.get("category_id") or payload.get("cat_id", "")
    budget_limit = payload.get("budget_limit", 0)
    current_spent = payload.get("current_spent", 0)
    
    if amount < 0:
        expense_amount = abs(amount)
        new_spent = current_spent + expense_amount
        if new_spent > budget_limit and budget_limit > 0:
            return {
                "alert": f"Budget exceeded for category {category_id}: {new_spent} / {budget_limit} KZT",
                "category_id": category_id,
                "spent": new_spent,
                "limit": budget_limit
            }
        return {"spent": new_spent}
    return {}

def check_balance_handler(event: Event, payload: dict) -> dict:
    balance = payload.get("balance", 0)
    threshold = payload.get("threshold", 0)
    
    if balance < threshold and threshold > 0:
        return {
            "alert": f"Balance alert: Current balance {balance} KZT is below threshold {threshold} KZT",
            "balance": balance,
            "threshold": threshold
        }
    return {}

def register_default_handlers():
    event_bus.subscribe(TRANSACTION_ADDED, update_balance_handler)
    event_bus.subscribe(TRANSACTION_ADDED, check_budget_handler)
    event_bus.subscribe(BALANCE_ALERT, check_balance_handler)

register_default_handlers()
