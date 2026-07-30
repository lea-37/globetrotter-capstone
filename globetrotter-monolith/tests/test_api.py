"""
Tests for the Phase 1 monolith.

Each test run points DATA_FILE at a fresh temp file (see the fixture below)
so tests don't stomp on your real data/data.json or on each other.
"""

import importlib
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def client(tmp_path, monkeypatch):
    temp_data_file = tmp_path / "data.json"
    seed = {
        "users": [],
        "destinations": [
            {"id": 1, "name": "Kribi", "region": "Cameroon", "tags": ["beach"], "popularity_score": 4},
            {"id": 2, "name": "Paris", "region": "France", "tags": ["city", "cultural"], "popularity_score": 5},
        ],
        "itineraries": [],
        "next_user_id": 1,
        "next_itinerary_id": 1,
    }
    temp_data_file.write_text(json.dumps(seed))
    monkeypatch.setenv("DATA_FILE", str(temp_data_file))

    # Reimport modules fresh so they pick up the patched DATA_FILE env var
    for mod_name in ["data_access", "business_logic", "auth", "app"]:
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])
        else:
            importlib.import_module(mod_name)

    import app as app_module
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


def register(client, username="lea", email="lea@example.com", password="secret123", preferences=None):
    return client.post("/register", json={
        "username": username,
        "email": email,
        "password": password,
        "preferences": preferences or [],
    })


def login(client, email="lea@example.com", password="secret123"):
    return client.post("/login", json={"email": email, "password": password})


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_register_creates_user(client):
    resp = register(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["email"] == "lea@example.com"
    assert "password_hash" not in body  # never leak the hash


def test_register_duplicate_email_rejected(client):
    register(client)
    resp = register(client)
    assert resp.status_code == 409


def test_login_success_returns_token(client):
    register(client)
    resp = login(client)
    assert resp.status_code == 200
    assert "token" in resp.get_json()


def test_login_wrong_password_rejected(client):
    register(client)
    resp = login(client, password="wrongpassword")
    assert resp.status_code == 401


def test_destinations_public_endpoint(client):
    resp = client.get("/destinations")
    assert resp.status_code == 200
    names = [d["name"] for d in resp.get_json()]
    assert "Kribi" in names
    assert "Paris" in names


def test_destinations_filter_by_tag(client):
    resp = client.get("/destinations?tag=city")
    assert resp.status_code == 200
    names = [d["name"] for d in resp.get_json()]
    assert names == ["Paris"]


def test_recommendations_requires_auth(client):
    resp = client.get("/recommendations")
    assert resp.status_code == 401


def test_recommendations_with_valid_token(client):
    register(client, preferences=["beach"])
    token = login(client).get_json()["token"]
    resp = client.get("/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    results = resp.get_json()
    assert len(results) > 0
    # Kribi has the "beach" tag matching the user's stated preference,
    # so it should be scored above Paris.
    assert results[0]["name"] == "Kribi"


def test_create_and_list_itinerary(client):
    register(client)
    token = login(client).get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = client.post("/itineraries", headers=headers, json={
        "name": "Summer trip",
        "destination_id": 1,
        "start_date": "2026-08-01",
        "end_date": "2026-08-10",
    })
    assert create_resp.status_code == 201

    list_resp = client.get("/itineraries", headers=headers)
    assert list_resp.status_code == 200
    itineraries = list_resp.get_json()
    assert len(itineraries) == 1
    assert itineraries[0]["name"] == "Summer trip"


def test_create_itinerary_unknown_destination_rejected(client):
    register(client)
    token = login(client).get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/itineraries", headers=headers, json={
        "name": "Bad trip",
        "destination_id": 999,
        "start_date": "2026-08-01",
        "end_date": "2026-08-10",
    })
    assert resp.status_code == 400
