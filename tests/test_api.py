import os
import pytest

# Set up test environment
os.environ["SENTINEL_API_KEY"] = "test-secret-key"

pytestmark = pytest.mark.asyncio


async def test_health_endpoint(client):
    """Test that the read-only /health endpoint works without an API key."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded")


async def test_metrics_endpoint(client):
    """Test that the read-only /metrics endpoint works without an API key."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "memory" in data


async def test_create_alert_requires_auth(client):
    """Test that creating an alert without an API key fails."""
    response = await client.post(
        "/alerts",
        json={
            "title": "CPU High",
            "message": "CPU is at 99%",
            "severity": "critical",
            "source": "test",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid or missing API key"


async def test_create_alert_with_auth(client):
    """Test that an alert can be created with a valid API key."""
    headers = {"X-API-Key": "test-secret-key"}
    response = await client.post(
        "/alerts",
        headers=headers,
        json={
            "title": "CPU High",
            "message": "CPU is at 99%",
            "severity": "critical",
            "source": "test",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "CPU High"
    assert data["resolved"] is False
    assert "id" in data


async def test_resolve_and_delete_alert(client):
    """Test the full lifecycle of an alert (Create -> Resolve -> Delete)."""
    headers = {"X-API-Key": "test-secret-key"}
    
    # 1. Create
    create_resp = await client.post(
        "/alerts",
        headers=headers,
        json={
            "title": "Disk Full",
            "message": "Disk usage at 98%",
            "severity": "warning",
            "source": "test",
        },
    )
    assert create_resp.status_code == 201
    alert_id = create_resp.json()["id"]

    # 2. Get list of alerts
    list_resp = await client.get("/alerts")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] == 1

    # 3. Resolve
    resolve_resp = await client.patch(
        f"/alerts/{alert_id}/resolve", headers=headers
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["resolved"] is True
    assert resolve_resp.json()["resolved_at"] is not None

    # 4. Delete
    delete_resp = await client.delete(
        f"/alerts/{alert_id}", headers=headers
    )
    assert delete_resp.status_code == 204

    # 5. Verify it's gone
    get_resp = await client.get(f"/alerts/{alert_id}")
    assert get_resp.status_code == 404
