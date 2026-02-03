import json
import time
from pathlib import Path

import pika
from fastapi.testclient import TestClient
from jsonschema import validate as jsonschema_validate
from testcontainers.rabbitmq import RabbitMqContainer

from services.orders_service.app.main import app

EXCHANGE = "xyz.events"

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]  # services/orders_service/tests/integration -> repo root

def _load_schema() -> dict:
    return json.loads((_repo_root() / "events" / "order-created.schema.json").read_text(encoding="utf-8"))

def test_rest_api_publishes_schema_valid_event(monkeypatch):
    # Use a real RabbitMQ broker (container) and validate both REST behavior and message contract.
    with RabbitMqContainer("rabbitmq:3.13-management") as rabbit:
        host = rabbit.get_container_host_ip()
        port = rabbit.get_exposed_port(5672)
        rabbit_url = f"amqp://guest:guest@{host}:{port}/"

        # Force publisher to use rabbitmq for this test
        monkeypatch.setenv("MESSAGE_BACKEND", "rabbitmq")
        monkeypatch.setenv("RABBITMQ_URL", rabbit_url)

        # Set up consumer binding
        conn = pika.BlockingConnection(pika.URLParameters(rabbit_url))
        ch = conn.channel()
        ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
        q = ch.queue_declare(queue="", exclusive=True).method.queue
        ch.queue_bind(queue=q, exchange=EXCHANGE, routing_key="#")

        client = TestClient(app)
        r = client.post("/orders", json={"sku": "SKU-999", "qty": 1})
        assert r.status_code == 201

        # Poll for message
        deadline = time.time() + 10
        body = None
        while time.time() < deadline:
            method, _, b = ch.basic_get(queue=q, auto_ack=True)
            if method is not None:
                body = b
                break
            time.sleep(0.2)

        conn.close()
        assert body is not None, "Expected event to be published after POST /orders"

        msg = json.loads(body.decode("utf-8"))
        assert msg["type"] == "OrderCreated"
        jsonschema_validate(instance=msg, schema=_load_schema())
