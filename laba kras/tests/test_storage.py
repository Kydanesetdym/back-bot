import time

from server import storage
from server.storage import User


def setup_function():
    storage.clear_all()


def teardown_function():
    storage.clear_all()


def test_generate_pin_is_4_digits():
    pin = storage.generate_pin(length=4)
    assert len(pin) == 4
    assert pin.isdigit()


def test_create_and_consume_pin_success():
    user = User(first_name="Ivan", last_name="Petrov", username="ivan", avatar=None)
    now = 1000.0
    pin = storage.create_pin_for_user(user, ttl_seconds=120, length=4, now=now)
    assert len(pin) == 4 and pin.isdigit()
    got = storage.consume_pin(pin, now=now + 10)
    assert got is not None
    assert got.first_name == "Ivan"
    assert got.last_name == "Petrov"
    assert got.username == "ivan"


def test_pin_is_one_time():
    user = User(first_name="A", last_name=None, username=None, avatar=None)
    now = 1000.0
    pin = storage.create_pin_for_user(user, ttl_seconds=120, length=4, now=now)
    assert storage.consume_pin(pin, now=now + 1) is not None
    assert storage.consume_pin(pin, now=now + 2) is None


def test_pin_expires_after_ttl():
    user = User(first_name="A", last_name=None, username=None, avatar=None)
    now = 1000.0
    pin = storage.create_pin_for_user(user, ttl_seconds=120, length=4, now=now)
    assert storage.consume_pin(pin, now=now + 121) is None


def test_invalid_pin_returns_none():
    assert storage.consume_pin("0000", now=1000.0) is None


def test_cleanup_removes_expired():
    user = User(first_name="A", last_name=None, username=None, avatar=None)
    pin = storage.create_pin_for_user(user, ttl_seconds=10, length=4, now=1000.0)
    assert storage.active_count(now=1005.0) == 1
    assert storage.active_count(now=1011.0) == 0
    assert storage.consume_pin(pin, now=1011.0) is None
