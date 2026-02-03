import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pika
from jsonschema import validate as jsonschema_validate

EXCHANGE = "xyz.events"
ROUTING_KEY = "orders.created"

_SCHEMA_CACHE = None


def _repo_root() -> Path:
    # publisher.py -> app -> orders_service -> services -> repo root
    return Path(__file__).resolve().parents[3]


def _load_schema() -> dict:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        schema_path = _repo_root() / "events" / "order-created.schema.json"
        _SCHEMA_CACHE = json.loads(schema_path.read_text(encoding="utf-8"))
    return _SCHEMA_CACHE


def build_order_created_event(order: dict) -> dict:
    event = {
        "type": "OrderCreated",
        "version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": order,
    }
    jsonschema_validate(instance=event, schema=_load_schema())
    return event


def _connect_rabbitmq(url: str) -> pika.BlockingConnection:
    params = pika.URLParameters(url)

    last = None
    for _ in range(10):
        try:
            return pika.BlockingConnection(params)
        except Exception as e:
            last = e
            time.sleep(0.5)

    raise RuntimeError(f"Unable to connect to RabbitMQ at {url}: {last!r}")


def publish_order_created(order: dict) -> None:
    backend = os.getenv("MESSAGE_BACKEND", "rabbitmq").lower()
    event = build_order_created_event(order)

    if backend == "sns":
        topic_arn = os.environ["ORDER_EVENTS_TOPIC_ARN"]
        region = os.getenv("AWS_REGION")
        client = boto3.client("sns", region_name=region)
        client.publish(TopicArn=topic_arn, Message=json.dumps(event))
        return

    url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    conn = _connect_rabbitmq(url)
    try:
        ch = conn.channel()
        ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
        ch.basic_publish(
            exchange=EXCHANGE,
            routing_key=ROUTING_KEY,
            body=json.dumps(event).encode("utf-8"),
        )
    finally:
        try:
            conn.close()
        except Exception:
            pass
