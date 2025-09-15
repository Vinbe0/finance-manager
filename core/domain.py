from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Account:
    id: str          
    name: str        
    balance: int     
    currency: str    


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    parent_id: Optional[str]  
    type: str                 

@dataclass(frozen=True)
class Transaction:
    id: str
    account_id: str  # which account
    cat_id: str      # which category
    amount: int      # + for income, - for expense
    ts: str          # timestamp, e.g. "2025-09-01T10:00:00"
    note: str = ""   # optional note

# A budget (limit for a category)
@dataclass(frozen=True)
class Budget:
    id: str
    cat_id: str
    limit: int
    period: str  # e.g. "month" or "week"

@dataclass(frozen=True)
class Event:
    id: str
    ts: str
    name: str
    payload: dict
