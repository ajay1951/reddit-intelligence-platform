from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from backend.api.auth import create_access_token, get_current_user, require_admin
from backend.api.main import app
from backend.config import Settings, settings


@pytest.fixture(autouse=True)
def disable_scheduler_for_tests(monkeypatch):
    monkeypatch.setattr(settings, "scheduler_enabled", False)
    monkeypatch.setattr("backend.api.main.start_scheduler", lambda: None)


def test_jwt_creation_and_payload_claims():

    """Verify standard claims: sub, exp, role, iat are embedded."""
    token = create_access_token(
        data={"sub": "researcher_1"},
        expires_delta=timedelta(minutes=15),
        role="user"
    )
    assert isinstance(token, str)
    assert len(token) > 50

    from jose import jwt
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == "researcher_1"
    assert payload["role"] == "user"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_expired_token_rejected():
    """Ensure expired tokens are rejected with a 401 Unauthorized status."""
    expired_token = create_access_token(
        data={"sub": "old_user"},
        expires_delta=timedelta(seconds=-10),
        role="user"
    )
    with TestClient(app) as client:
        response = client.get(
            "/schedule/jobs",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
    assert response.status_code == 401
    assert "expired" in response.json().get("detail", "").lower()


def test_jwt_invalid_signature_rejected():
    """Ensure tokens signed with a foreign key fail validation."""
    from jose import jwt
    fake_token = jwt.encode(
        {"sub": "attacker", "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
        "completely-different-signing-key-0123456789",
        algorithm="HS256"
    )
    with TestClient(app) as client:
        response = client.get(
            "/schedule/jobs",
            headers={"Authorization": f"Bearer {fake_token}"}
        )
    assert response.status_code == 401
    assert "could not validate credentials" in response.json().get("detail", "").lower()


def test_missing_token_on_protected_endpoints():
    """Protected endpoints must reject requests lacking credentials with 401."""
    with TestClient(app) as client:
        # Schedule jobs list (authenticated)
        res_jobs = client.get("/schedule/jobs")
        assert res_jobs.status_code == 401

        # Batch scrape dispatch (admin only)
        res_scrape = client.post("/scrape/batch", json={"subreddits": ["python"]})
        assert res_scrape.status_code == 401

        # Deep research (authenticated)
        res_deep = client.post("/deep-research", json={"topic": "distributed systems"})
        assert res_deep.status_code == 401

        # Reindex vectors (admin only)
        res_reindex = client.post("/search/reindex")
        assert res_reindex.status_code == 401


def test_insufficient_permissions_on_admin_endpoint():
    """Non-admin user token accessing admin endpoints must be rejected with 403 Forbidden."""
    user_token = create_access_token(data={"sub": "standard_user"}, role="user")

    with TestClient(app) as client:
        response = client.post(
            "/scrape/batch",
            json={"subreddits": ["python"]},
            headers={"Authorization": f"Bearer {user_token}"}
        )
    assert response.status_code == 403
    assert "admin role required" in response.json().get("detail", "").lower()


def test_admin_token_allows_protected_action(monkeypatch):
    """Admin token passes require_admin guard."""
    admin_token = create_access_token(data={"sub": "admin_user"}, role="admin")

    # Mock the celery delay call to avoid needing live Redis in unit test
    class DummyTask:
        id = "mock-task-id-12345"

    monkeypatch.setattr(
        "backend.etl.tasks.run_batch_scrape_task.delay",
        lambda *args, **kwargs: DummyTask(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/scrape/batch",
            json={"subreddits": ["python"], "post_limit": 5, "comment_limit": 1},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    assert response.status_code == 200
    assert response.json()["status"] == "dispatched"
    assert response.json()["task_id"] == "mock-task-id-12345"


def test_m2m_admin_key_header_authorization(monkeypatch):
    """Machine-to-machine X-Admin-Key header grants admin privileges when configured."""
    monkeypatch.setattr(settings, "admin_api_key", "super-secret-m2m-admin-key-999")

    class DummyTask:
        id = "mock-task-id-admin-key"

    monkeypatch.setattr(
        "backend.etl.tasks.run_batch_scrape_task.delay",
        lambda *args, **kwargs: DummyTask(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/scrape/batch",
            json={"subreddits": ["python"]},
            headers={"X-Admin-Key": "super-secret-m2m-admin-key-999"}
        )
    assert response.status_code == 200
    assert response.json()["task_id"] == "mock-task-id-admin-key"


def test_cors_preflight_and_origin_allowlist():
    """Verify that configured origins receive proper CORS headers and disallowed origins do not."""
    with TestClient(app) as client:
        # Allowed origin
        allowed_res = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert allowed_res.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert allowed_res.headers.get("access-control-allow-credentials") == "true"

        # Disallowed malicious origin
        disallowed_res = client.options(
            "/health",
            headers={
                "Origin": "https://malicious-phishing-site.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert disallowed_res.headers.get("access-control-allow-origin") is None


def test_production_config_validation():
    """Test that production environment refuses startup on weak/default secrets or wildcard CORS."""
    # 1. Weak/default JWT secret rejection
    with pytest.raises(ValueError, match="JWT_SECRET_KEY must be configured in production"):
        Settings(
            app_env="production",
            postgres_user="u",
            postgres_password="p",
            postgres_db="db",
            postgres_host="h",
            postgres_port=5432,
            app_host="0.0.0.0",
            app_port=8000,
            log_level="INFO",
            scraper_concurrency=1,
            scraper_rate_limit_per_sec=1,
            jwt_secret_key="dev-insecure-secret-key-change-in-production-min-32-chars",
        )

    # 2. Wildcard CORS rejection in production
    with pytest.raises(ValueError, match="CORS_ORIGINS cannot contain wildcard"):
        Settings(
            app_env="production",
            postgres_user="u",
            postgres_password="p",
            postgres_db="db",
            postgres_host="h",
            postgres_port=5432,
            app_host="0.0.0.0",
            app_port=8000,
            log_level="INFO",
            scraper_concurrency=1,
            scraper_rate_limit_per_sec=1,
            jwt_secret_key="c8f1e0d3b4a596877899aabbccddeeff00112233445566778899aabbccddeeff",
            cors_origins="http://localhost:5173, *",
        )


def test_admin_login_success_with_valid_credentials():
    """Verify that POST /auth/login returns a valid admin token when credentials match."""
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"username": settings.admin_username, "password": settings.admin_password}
        )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify token payload
    from jose import jwt
    payload = jwt.decode(data["access_token"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == settings.admin_username
    assert payload["role"] == "admin"


def test_admin_login_fails_with_invalid_credentials():
    """Verify that POST /auth/login rejects incorrect passwords with 401 Unauthorized."""
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"username": settings.admin_username, "password": "wrong-password-123"}
        )
    assert response.status_code == 401
    assert "Invalid username or password" in response.json().get("detail", "")


def test_token_endpoint_rejects_admin_role_without_valid_secret():
    """Verify that POST /auth/token strictly rejects admin role requests without verified ADMIN_API_KEY."""
    with TestClient(app) as client:
        # 1. No secret supplied
        res1 = client.post(
            "/auth/token",
            json={"username": "malicious_actor", "role": "admin"}
        )
        assert res1.status_code == 403
        assert "Invalid admin credentials" in res1.json().get("detail", "")

        # 2. Using JWT secret as password/secret is rejected
        res2 = client.post(
            "/auth/token",
            json={"username": "malicious_actor", "role": "admin", "secret": settings.jwt_secret_key}
        )
        assert res2.status_code == 403

        # 3. Standard user role request succeeds
        res3 = client.post(
            "/auth/token",
            json={"username": "standard_user", "role": "user"}
        )
        assert res3.status_code == 200
        assert "access_token" in res3.json()


def test_login_rejects_jwt_secret_as_password():
    """Ensure JWT_SECRET_KEY cannot be reused as an admin login password."""
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"username": settings.admin_username, "password": settings.jwt_secret_key}
        )
    assert response.status_code == 401


def test_production_rejects_default_admin_password():
    """Ensure Settings validation raises error in production when admin_password is default."""
    with pytest.raises(ValueError, match="ADMIN_PASSWORD must be configured in production"):
        Settings(
            app_env="production",
            postgres_user="u",
            postgres_password="strong-production-postgres-pass",
            postgres_db="db",
            postgres_host="h",
            postgres_port=5432,
            app_host="0.0.0.0",
            app_port=8000,
            log_level="INFO",
            scraper_concurrency=1,
            scraper_rate_limit_per_sec=1,
            jwt_secret_key="c8f1e0d3b4a596877899aabbccddeeff00112233445566778899aabbccddeeff",
            admin_password="admin123",
        )


def test_subreddit_input_sanitization():
    """Ensure malicious subreddit identifiers with traversal or special chars are rejected."""
    admin_token = create_access_token(data={"sub": "admin_user"}, role="admin")
    with TestClient(app) as client:
        # Path traversal in batch scrape
        res_batch = client.post(
            "/scrape/batch",
            json={"subreddits": ["../../etc/passwd"]},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_batch.status_code == 422

        # Special characters in single scrape endpoint
        res_single = client.post(
            "/scrape/@malicious.com",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_single.status_code == 400




