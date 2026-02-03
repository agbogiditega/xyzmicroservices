from fastapi.testclient import TestClient

from services.orders_service.app import main as app_main


def test_health_endpoint_returns_ok():
    client = TestClient(app_main.app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_order_happy_path_publishes_event(monkeypatch):
    published = {}

    def fake_publish(order: dict) -> None:
        published.update(order)

    monkeypatch.setattr(app_main, "publish_order_created", fake_publish)

    client = TestClient(app_main.app)
    r = client.post("/orders", json={"sku": "SKU-123", "qty": 2})
    assert r.status_code == 201
    body = r.json()
    assert "order_id" in body
    assert published["sku"] == "SKU-123"
    assert published["qty"] == 2
    assert published["order_id"] == body["order_id"]


def test_create_order_invalid_qty_returns_400(monkeypatch):
    monkeypatch.setattr(app_main, "publish_order_created", lambda _: None)

    client = TestClient(app_main.app)
    r = client.post("/orders", json={"sku": "SKU-123", "qty": 0})
    assert r.status_code == 400
