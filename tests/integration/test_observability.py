"""
Integration tests for observability endpoints.

Covers TS scenarios: TS-001-056, TS-001-057, TS-001-058
"""

import pytest
from httpx import AsyncClient


# ─── TS-001-056 ──────────────────────────────────────────────────────────────


async def test_ts_001_056_health_returns_200(client: AsyncClient) -> None:
    """
    TS-001-056: inventory-service GET /health returns 200.
    Action: GET /health
    Expected: HTTP 200; body {"status": "ok"}
    """
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


# ─── TS-001-057 ──────────────────────────────────────────────────────────────


async def test_ts_001_057_ready_returns_200_when_db_healthy(client: AsyncClient) -> None:
    """
    TS-001-057: inventory-service GET /ready returns 200.
    Preconditions: inventory-service running; DB connection healthy
    Action: GET /ready
    Expected: HTTP 200; body contains "status": "ready"
    """
    response = await client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"


# ─── TS-001-058 ──────────────────────────────────────────────────────────────


async def test_ts_001_058_metrics_returns_prometheus_format(client: AsyncClient) -> None:
    """
    TS-001-058: inventory-service GET /metrics returns Prometheus format.
    Action: GET /metrics
    Expected: HTTP 200; Content-Type contains text/plain; body contains Prometheus metrics
    """
    response = await client.get("/metrics")

    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/plain" in content_type
    # Prometheus format — body should contain metric lines
    body = response.text
    assert len(body) > 0
    # Basic Prometheus format check — lines should have metric name patterns
    assert "#" in body or "http" in body.lower() or "python" in body.lower()
