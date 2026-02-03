# tests/e2e/test_order_to_payment_flow.py

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pika
from jsonschema import validate as jsonschema_validate
from testcontainers.rabbitmq import RabbitMqContainer

EXCHANGE = "xyz.events"


def _repo_root() -> Path:
    # tests/e2e -> tests -> repo root
    return Path(__file__).resolve().parents[2]


def _load_schema() -> dict:
    schema_path = _repo_root() / "events" / "order-created.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_http(url: str, timeout_s: int = 20) -> None:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=1.0)
            # If the app is up, it should respond; don't require 200 specifically here.
            if r.status_code < 500:
                return
        except Exception as e:
            last = e
        time.sleep(0.25)
    raise RuntimeError(f"Service not ready: {url}. Last error: {last!r}")


def wait_amqp(url: str, timeout_s: int = 30) -> None:
    """
    Readiness check that avoids noisy pika handshake logs by:
    1) waiting for the TCP port to accept connections, then
    2) doing a single AMQP handshake via pika.
    """
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5672

    deadline = time.time() + timeout_s
    last = None

    # 1) TCP readiness (quiet)
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                break
        except OSError as e:
            last = e
            time.sleep(0.25)
    else:
        raise RuntimeError(f"RabbitMQ port not ready at {host}:{port}. Last error: {last!r}")

    # 2) One AMQP handshake (should succeed now)
    conn = pika.BlockingConnection(pika.URLParameters(url))
    conn.close()


def test_e2e_order_created_event():
    with RabbitMqContainer("rabbitmq:3.13-management") as rabbit:
        host = rabbit.get_container_host_ip()
        # Normalize host for macOS/docker + ipv6 oddities
        if host in ("localhost", "0.0.0.0", "::1"):
            host = "127.0.0.1"

        port = int(rabbit.get_exposed_port(5672))
        rabbit_url = f"amqp://guest:guest@{host}:{port}/"

        # Ensure RabbitMQ is truly ready before starting the service
        wait_amqp(rabbit_url, timeout_s=30)

        env = os.environ.copy()
        env["RABBITMQ_URL"] = rabbit_url
        env["MESSAGE_BACKEND"] = "rabbitmq"

        service_port = _free_port()

        # Start Orders service using the current interpreter (venv-safe)
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "services.orders_service.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(service_port),
            ],
            cwd=str(_repo_root()),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        conn = None
        try:
            wait_http(f"http://127.0.0.1:{service_port}/health", timeout_s=25)

            # Bind a temporary queue to all events
            conn = pika.BlockingConnection(pika.URLParameters(rabbit_url))
            ch = conn.channel()
            ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

            q = ch.queue_declare(queue="", exclusive=True).method.queue
            ch.queue_bind(queue=q, exchange=EXCHANGE, routing_key="#")

            # Trigger event via REST
            r = httpx.post(
                f"http://127.0.0.1:{service_port}/orders",
                json={"sku": "SKU-123", "qty": 1},
                timeout=5.0,
            )
            assert r.status_code == 201, r.text

            # Assert an event arrives
            deadline = time.time() + 10
            body = None
            while time.time() < deadline:
                method, _, b = ch.basic_get(queue=q, auto_ack=True)
                if method is not None:
                    body = b
                    break
                time.sleep(0.2)

            assert body is not None, "Expected an OrderCreated event to be published"

            msg = json.loads(body.decode("utf-8"))
            assert msg.get("type") == "OrderCreated"
            jsonschema_validate(instance=msg, schema=_load_schema())

        finally:
            # Clean shutdown of service
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

            # Clean shutdown of AMQP connection
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
