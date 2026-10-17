from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient

from backend.api.main import app
from backend.database.connection import get_session


def test_request_id_generated_when_missing():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 10


def test_request_id_preserved_when_provided():
    custom_id = "test-custom-trace-id-12345"
    with TestClient(app) as client:
        response = client.get("/health", headers={"x-request-id": custom_id})
        assert response.status_code == 200
        assert response.headers["x-request-id"] == custom_id


def test_request_id_crlf_injection_sanitized():
    malicious_id = "attack\r\nInjected-Header: evil\nLog-Forging"
    with TestClient(app) as client:
        response = client.get("/health", headers={"x-request-id": malicious_id})
        assert response.status_code == 200
        resp_id = response.headers["x-request-id"]
        assert resp_id != malicious_id
        assert "\r" not in resp_id and "\n" not in resp_id
        assert len(resp_id) > 10


def test_metrics_endpoint_telemetry():
    with TestClient(app) as client:
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "requests" in data
        assert "total" in data["requests"]
        assert "status_codes" in data["requests"]
        assert "cache" in data
        assert "background_tasks" in data


def test_health_ready_healthy():
    # Mock healthy DB session
    async def mock_db():
        m = AsyncMock()
        scalar_mock = MagicMock()
        scalar_mock.scalar.return_value = 1
        m.execute.return_value = scalar_mock
        yield m

    app.dependency_overrides[get_session] = mock_db

    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.aclose.return_value = None

    mock_chroma = MagicMock()
    mock_chroma.collection.count.return_value = 42

    try:
        with (
            patch("redis.asyncio.from_url", return_value=mock_redis),
            patch("backend.api.health.ChromaRepository", return_value=mock_chroma),
        ):
            with TestClient(app) as client:
                response = client.get("/health/ready")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["ready"] is True
                assert data["components"]["database"]["status"] == "healthy"
                assert data["components"]["redis"]["status"] == "healthy"
                assert data["components"]["chromadb"]["status"] == "healthy"
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_health_ready_unhealthy_when_database_down():
    async def mock_failing_db():
        m = AsyncMock()
        m.execute.side_effect = Exception("Database connection failure")
        yield m

    app.dependency_overrides[get_session] = mock_failing_db

    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.aclose.return_value = None

    mock_chroma = MagicMock()
    mock_chroma.collection.count.return_value = 10

    try:
        with (
            patch("redis.asyncio.from_url", return_value=mock_redis),
            patch("backend.api.health.ChromaRepository", return_value=mock_chroma),
        ):
            with TestClient(app) as client:
                response = client.get("/health/ready")
                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "degraded"
                assert data["ready"] is False
                assert data["components"]["database"]["status"] == "unhealthy"
    finally:
        app.dependency_overrides.pop(get_session, None)
