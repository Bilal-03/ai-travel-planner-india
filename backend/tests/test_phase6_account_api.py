"""HTTP contract checks for Phase 6 anonymous/account controls."""

from fastapi.testclient import TestClient

from main import app


def test_anonymous_upgrade_preferences_and_delete_flow():
    with TestClient(app) as client:
        anonymous = client.post("/api/account/anonymous")
        assert anonymous.status_code == 200
        token = anonymous.json()["access_token"]
        assert anonymous.headers.get("X-Yatra-Account-Token") == token

        registered = client.post(
            "/api/account/register",
            headers={"X-Yatra-Account-Token": token},
            json={"email": "phase6-http@example.com", "display_name": "HTTP test"},
        )
        assert registered.status_code == 200
        account_token = registered.json()["access_token"]
        assert registered.json()["account"]["is_anonymous"] is False

        updated = client.put(
            "/api/account/preferences",
            headers={"X-Yatra-Account-Token": account_token},
            json={"preferred_transport": "train", "typical_budget_min": 12000},
        )
        assert updated.status_code == 200
        assert updated.json()["preferred_transport"] == "train"

        disabled = client.post(
            "/api/account/preferences/disable",
            headers={"X-Yatra-Account-Token": account_token},
        )
        assert disabled.status_code == 200
        assert disabled.json()["memory_enabled"] is False

        deleted = client.delete("/api/account/me", headers={"X-Yatra-Account-Token": account_token})
        assert deleted.status_code == 200
        assert deleted.json() == {"deleted": True}

