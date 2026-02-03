from dataclasses import dataclass
from uuid import uuid4

@dataclass(frozen=True)
class Order:
    order_id: str
    sku: str
    qty: int

def create_order(sku: str, qty: int) -> Order:
    if not sku or not isinstance(sku, str):
        raise ValueError("sku is required")
    if qty <= 0:
        raise ValueError("qty must be > 0")
    return Order(order_id=str(uuid4()), sku=sku, qty=qty)
