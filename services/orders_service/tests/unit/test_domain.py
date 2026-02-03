import pytest
from services.orders_service.app.domain import create_order
#from orders_service.app.domain import create_order

def test_create_order_happy_path():
    o = create_order("SKU-123", 2)
    assert o.sku == "SKU-123"
    assert o.qty == 2
    assert o.order_id

@pytest.mark.parametrize("sku,qty", [("", 1), ("SKU-1", 0), ("SKU-1", -5)])
def test_create_order_rejects_invalid_inputs(sku, qty):
    with pytest.raises(ValueError):
        create_order(sku, qty)
