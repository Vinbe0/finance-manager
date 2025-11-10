from typing import Callable, Dict, List, NamedTuple
from datetime import datetime

# Make sure event_bus is exported
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

# Event types
TRANSACTION_ADDED = "TRANSACTION_ADDED"
BUDGET_ALERT = "BUDGET_ALERT"
BALANCE_ALERT = "BALANCE_ALERT"

# Global event bus instance
event_bus = EventBus()

# Ensure the event bus is created at module level
__event_bus = event_bus  # This ensures the event_bus is created when the module is imported

# Pure event handlers
def update_balance(event: Event, state: dict) -> dict:
    """Update account balance when a transaction is added"""
    transaction = event.payload
    current_balance = state.get("balance", 0)
    new_balance = current_balance + transaction["amount"]
    return {"balance": new_balance}

def check_budget(event: Event, state: dict) -> dict:
    """Check if transaction exceeds budget limits"""
    transaction = event.payload
    budget_limit = state.get("budget_limit", 1000)
    if abs(transaction["amount"]) > budget_limit:
        return {
            "alert": f"Budget alert: Transaction amount {transaction['amount']} exceeds limit {budget_limit}"
        }
    return {}

def check_balance(event: Event, state: dict) -> dict:
    """Check if balance is below threshold"""
    balance = event.payload.get("balance", 0)
    threshold = state.get("balance_threshold", 100)
    if balance < threshold:
        return {
            "alert": f"Balance alert: Current balance {balance} is below threshold {threshold}"
        }
    return {}

# Function to register default handlers
def register_default_handlers():
    """Register all default event handlers"""
    event_bus.subscribe(TRANSACTION_ADDED, update_balance)
    event_bus.subscribe(TRANSACTION_ADDED, check_budget)
    event_bus.subscribe(BALANCE_ALERT, check_balance)

# Register handlers when module is imported
register_default_handlers()
