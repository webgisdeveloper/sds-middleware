import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_localhost_request_no_auth_required():
    """Test that localhost requests don't require client secret."""
    # Simulate localhost request
    response = client.get("/", headers={"X-Forwarded-For": "127.0.0.1"})
    assert response.status_code == 200
    

def test_external_request_requires_auth():
    """Test that external requests require client secret."""
    # Simulate external request without client secret
    response = client.get("/", headers={"X-Forwarded-For": "192.168.1.100"})
    assert response.status_code == 401
    assert "Missing or invalid client secret" in response.text


def test_external_request_with_default_client_secret():
    """Test that external requests with default client secret are allowed."""
    response = client.get(
        "/",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "Authorization": f"Bearer {settings.webserver.client_secret}"
        }
    )
    assert response.status_code == 200


def test_site1_request_with_site_specific_secret():
    """Test that site1 requests with site-specific secret are allowed."""
    site1_secret = settings.webserver.site_secrets.get("site1")
    if site1_secret:
        response = client.get(
            "/",
            headers={
                "X-Forwarded-For": "192.168.1.100",
                "X-Site": "site1",
                "X-Client-Secret": site1_secret
            }
        )
        assert response.status_code == 200


def test_site2_request_with_site_specific_secret():
    """Test that site2 requests with site-specific secret are allowed."""
    site2_secret = settings.webserver.site_secrets.get("site2")
    if site2_secret:
        response = client.get(
            "/",
            headers={
                "X-Forwarded-For": "192.168.1.100",
                "X-Site": "site2",
                "Authorization": f"Bearer {site2_secret}"
            }
        )
        assert response.status_code == 200


def test_site3_request_with_site_specific_secret():
    """Test that site3 requests with site-specific secret are allowed."""
    site3_secret = settings.webserver.site_secrets.get("site3")
    if site3_secret:
        response = client.get(
            f"/?site=site3&client_secret={site3_secret}",
            headers={"X-Forwarded-For": "192.168.1.100"}
        )
        assert response.status_code == 200


def test_site_request_with_wrong_secret():
    """Test that site requests with wrong secret are rejected."""
    response = client.get(
        "/",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Site": "site1",
            "X-Client-Secret": "wrong-secret"
        }
    )
    assert response.status_code == 401
    assert "Missing or invalid client secret" in response.text


def test_site_request_with_default_secret_should_fail():
    """Test that site requests with default secret should fail if site has its own secret."""
    site1_secret = settings.webserver.site_secrets.get("site1")
    if site1_secret and site1_secret != settings.webserver.client_secret:
        response = client.get(
            "/",
            headers={
                "X-Forwarded-For": "192.168.1.100",
                "X-Site": "site1",
                "X-Client-Secret": settings.webserver.client_secret
            }
        )
        assert response.status_code == 401


def test_unknown_site_uses_default_secret():
    """Test that unknown sites use the default client secret."""
    response = client.get(
        "/",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Site": "unknown_site",
            "X-Client-Secret": settings.webserver.client_secret
        }
    )
    assert response.status_code == 200


def test_external_request_with_valid_auth_header():
    """Test that external requests with valid Authorization header are allowed."""
    response = client.get(
        "/",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "Authorization": f"Bearer {settings.webserver.client_secret}"
        }
    )
    assert response.status_code == 200


def test_external_request_with_valid_client_secret_header():
    """Test that external requests with valid X-Client-Secret header are allowed."""
    response = client.get(
        "/",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Client-Secret": settings.webserver.client_secret
        }
    )
    assert response.status_code == 200


def test_external_request_with_valid_query_param():
    """Test that external requests with valid client_secret query parameter are allowed."""
    response = client.get(
        f"/?client_secret={settings.webserver.client_secret}",
        headers={"X-Forwarded-For": "192.168.1.100"}
    )
    assert response.status_code == 200


def test_external_request_with_invalid_client_secret():
    """Test that external requests with invalid client secret are rejected."""
    response = client.get(
        "/",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Client-Secret": "invalid-secret"
        }
    )
    assert response.status_code == 401
    assert "Missing or invalid client secret" in response.text


def test_config_endpoint_security():
    """Test that the config endpoint also requires authentication for external requests."""
    # External request without auth should fail
    response = client.get("/config", headers={"X-Forwarded-For": "192.168.1.100"})
    assert response.status_code == 401
    
    # External request with valid auth should succeed
    response = client.get(
        "/config",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Client-Secret": settings.webserver.client_secret
        }
    )
    assert response.status_code == 200
