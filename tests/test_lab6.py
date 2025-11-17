from core.events import (
    Event, EventBus, event_bus,
    TRANSACTION_ADDED, BUDGET_ALERT, BALANCE_ALERT,
    update_balance_handler, check_budget_handler, check_balance_handler
)
from datetime import datetime


def test_event_creation():
    event = Event(
        name=TRANSACTION_ADDED,
        ts=datetime.now().isoformat(),
        payload={"amount": -100, "account_id": "a1"}
    )
    assert event.name == TRANSACTION_ADDED
    assert "amount" in event.payload
    assert event.payload["amount"] == -100


def test_event_bus_subscribe_and_publish():
    bus = EventBus()
    results_collected = []
    
    def test_handler(event: Event, payload: dict) -> dict:
        results_collected.append(payload)
        return {"processed": True}
    
    bus.subscribe(TRANSACTION_ADDED, test_handler)
    results = bus.publish(TRANSACTION_ADDED, {"amount": -50})
    
    assert len(results) == 1
    assert results[0]["processed"] is True
    assert len(results_collected) == 1
    assert results_collected[0]["amount"] == -50


def test_multiple_subscribers_same_event():
    bus = EventBus()
    handler1_called = []
    handler2_called = []
    
    def handler1(event: Event, payload: dict) -> dict:
        handler1_called.append(payload)
        return {"handler": 1}
    
    def handler2(event: Event, payload: dict) -> dict:
        handler2_called.append(payload)
        return {"handler": 2}
    
    bus.subscribe(TRANSACTION_ADDED, handler1)
    bus.subscribe(TRANSACTION_ADDED, handler2)
    
    results = bus.publish(TRANSACTION_ADDED, {"amount": -200})
    
    assert len(results) == 2
    assert len(handler1_called) == 1
    assert len(handler2_called) == 1
    assert handler1_called[0]["amount"] == -200
    assert handler2_called[0]["amount"] == -200


def test_update_balance_handler_pure():
    event = Event(
        name=TRANSACTION_ADDED,
        ts=datetime.now().isoformat(),
        payload={"amount": -150, "account_id": "a1"}
    )
    
    payload1 = {"amount": -150, "account_id": "a1"}
    result1 = update_balance_handler(event, payload1)
    
    payload2 = {"amount": -150, "account_id": "a1"}
    result2 = update_balance_handler(event, payload2)
    
    assert result1["balance_delta"] == -150
    assert result2["balance_delta"] == -150
    assert result1 == result2
    assert payload1 == payload2


def test_check_budget_handler_pure():
    event = Event(
        name=TRANSACTION_ADDED,
        ts=datetime.now().isoformat(),
        payload={"amount": -600, "category_id": "c1", "budget_limit": 1000, "current_spent": 0}
    )
    
    payload1 = {"amount": -600, "category_id": "c1", "budget_limit": 1000, "current_spent": 0}
    result1 = check_budget_handler(event, payload1)
    
    payload2 = {"amount": -600, "category_id": "c1", "budget_limit": 1000, "current_spent": 0}
    result2 = check_budget_handler(event, payload2)
    
    assert result1 == result2
    assert "spent" in result1
    assert result1["spent"] == 600
    assert payload1 == payload2


def test_check_budget_handler_exceeds_limit():
    event = Event(
        name=TRANSACTION_ADDED,
        ts=datetime.now().isoformat(),
        payload={"amount": -1500, "category_id": "c1", "budget_limit": 1000, "current_spent": 0}
    )
    
    payload = {"amount": -1500, "category_id": "c1", "budget_limit": 1000, "current_spent": 0}
    result = check_budget_handler(event, payload)
    
    assert "alert" in result
    assert "Budget exceeded" in result["alert"]
    assert result["spent"] == 1500
    assert result["limit"] == 1000


def test_check_balance_handler_pure():
    event = Event(
        name=BALANCE_ALERT,
        ts=datetime.now().isoformat(),
        payload={"balance": 50, "threshold": 100}
    )
    
    payload1 = {"balance": 50, "threshold": 100}
    result1 = check_balance_handler(event, payload1)
    
    payload2 = {"balance": 50, "threshold": 100}
    result2 = check_balance_handler(event, payload2)
    
    assert result1 == result2
    assert "alert" in result1
    assert "Balance alert" in result1["alert"]
    assert payload1 == payload2


def test_check_balance_handler_no_alert():
    event = Event(
        name=BALANCE_ALERT,
        ts=datetime.now().isoformat(),
        payload={"balance": 500, "threshold": 100}
    )
    
    payload = {"balance": 500, "threshold": 100}
    result = check_balance_handler(event, payload)
    
    assert "alert" not in result
    assert result == {}


def test_event_bus_unsubscribe():
    bus = EventBus()
    calls = []
    
    def handler(event: Event, payload: dict) -> dict:
        calls.append(payload)
        return {}
    
    bus.subscribe(TRANSACTION_ADDED, handler)
    bus.publish(TRANSACTION_ADDED, {"amount": -100})
    assert len(calls) == 1
    
    bus.unsubscribe(TRANSACTION_ADDED, handler)
    bus.publish(TRANSACTION_ADDED, {"amount": -200})
    assert len(calls) == 1


def test_different_event_types():
    bus = EventBus()
    transaction_results = []
    budget_results = []
    balance_results = []
    
    def transaction_handler(event: Event, payload: dict) -> dict:
        transaction_results.append(event.name)
        return {}
    
    def budget_handler(event: Event, payload: dict) -> dict:
        budget_results.append(event.name)
        return {}
    
    def balance_handler(event: Event, payload: dict) -> dict:
        balance_results.append(event.name)
        return {}
    
    bus.subscribe(TRANSACTION_ADDED, transaction_handler)
    bus.subscribe(BUDGET_ALERT, budget_handler)
    bus.subscribe(BALANCE_ALERT, balance_handler)
    
    bus.publish(TRANSACTION_ADDED, {"amount": -100})
    bus.publish(BUDGET_ALERT, {"category_id": "c1"})
    bus.publish(BALANCE_ALERT, {"balance": 50})
    
    assert len(transaction_results) == 1
    assert len(budget_results) == 1
    assert len(balance_results) == 1
    assert transaction_results[0] == TRANSACTION_ADDED
    assert budget_results[0] == BUDGET_ALERT
    assert balance_results[0] == BALANCE_ALERT

