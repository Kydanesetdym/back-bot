import importlib

import pytest
from fastapi.testclient import TestClient

from server import storage
from server.storage import User


@pytest.fixture()
def client(monkeypatch):
    # prevent real bot/webhook side effects during app import/startup
    monkeypatch.setenv("BOT_TOKEN", "")
    monkeypatch.setenv("BASE_URL", "")
    # reload config and main to pick env
    import server.config as config
    importlib.reload(config)
    import server.main as main
    importlib.reload(main)
    storage.clear_all()
    with TestClient(main.app) as c:
        yield c
    storage.clear_all()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_auth_success(client):
    user = User(first_name="Ivan", last_name="Petrov", username="ivan", avatar=None)
    pin = storage.create_pin_for_user(user, ttl_seconds=120, length=4, now=1000.0)
    # consume_pin uses current time; set entry to far future by recreating
    storage.clear_all()
    import time
    pin = storage.create_pin_for_user(user, ttl_seconds=120, length=4, now=time.time())
    r = client.post("/auth", json={"key": pin})
    assert r.status_code == 200
    data = r.json()
    assert data["first_name"] == "Ivan"
    assert data["last_name"] == "Petrov"
    assert data["username"] == "ivan"
    assert data["avatar"] is None


def test_auth_invalid_pin(client):
    r = client.post("/auth", json={"key": "9999"})
    assert r.status_code == 401


def test_auth_expired_pin(client):
    import time
    user = User(first_name="A", last_name=None, username=None, avatar=None)
    pin = storage.create_pin_for_user(user, ttl_seconds=0, length=4, now=time.time() - 1)
    r = client.post("/auth", json={"key": pin})
    assert r.status_code == 401


def test_auth_validation(client):
    r = client.post("/auth", json={"key": "12"})
    assert r.status_code == 422
    r = client.post("/auth", json={"key": "abcd"})
    assert r.status_code == 422

def test_auth_rate_limit(client):
    for _ in range(5):
        assert client.post("/auth", json={"key": "9999"}).status_code == 401
    r = client.post("/auth", json={"key": "9999"})
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_auth_blocked_even_with_valid_pin(client):
    import time
    for _ in range(5):
        client.post("/auth", json={"key": "9999"})
    user = User(first_name="A", last_name=None, username=None, avatar=None)
    pin = storage.create_pin_for_user(user, ttl_seconds=120, length=4, now=time.time())
    assert client.post("/auth", json={"key": pin}).status_code == 429

def test_webhook_rejects_without_secret(client):
    import server.config as config
    r = client.post(config.WEBHOOK_PATH, json={})
    assert r.status_code == 403


def test_webhook_rejects_wrong_secret(client):
    import server.config as config
    r = client.post(
        config.WEBHOOK_PATH, json={},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert r.status_code == 403