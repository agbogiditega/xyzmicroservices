import json
import os
from pathlib import Path

import pika
from jsonschema import validate as jsonschema_validate
from testcontainers.rabbitmq import RabbitMqContainer

from services.orders_service.app.publisher import publish_order_created, EXCHANGE, ROUTING_KEY


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]  # services/orders_service/tests/integration -> repo root

def _load_schema() -> dict:
    return json.loads((_repo_root() / "events" / "order-created.schema.json").read_text(encoding="utf-8"))

def test_publish_order_created_to_rabbitmq_is_schema_valid():
    with RabbitMqContainer("rabbitmq:3.13-management") as rabbit:
        host = rabbit.get_container_host_ip()
        port = rabbit.get_exposed_port(5672)
        url = f"amqp://guest:guest@{host}:{port}/"

        os.environ["MESSAGE_BACKEND"] = "rabbitmq"
        os.environ["RABBITMQ_URL"] = url

        conn = pika.BlockingConnection(pika.URLParameters(url))
        ch = conn.channel()
        ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
        q = ch.queue_declare(queue="", exclusive=True).method.queue
        ch.queue_bind(queue=q, exchange=EXCHANGE, routing_key=ROUTING_KEY)

        publish_order_created({"order_id": "o-1", "sku": "SKU-123", "qty": 2})

        method, _, body = ch.basic_get(queue=q, auto_ack=True)
        conn.close()

        assert method is not None, "Expected at least one message"
        msg = json.loads(body.decode("utf-8"))
        assert msg["type"] == "OrderCreated"
        jsonschema_validate(instance=msg, schema=_load_schema())
