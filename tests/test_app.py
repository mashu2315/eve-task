from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

import app.main as main_module

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[main_module.get_db] = override_get_db
app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=engine)
main_module.Base.metadata.create_all(bind=engine)

client = TestClient(app)


@pytest.fixture
def auth_headers():
    email = f"test-{uuid4().hex[:8]}@example.com"
    signup = client.post("/auth/signup", json={
        "full_name": "Test User",
        "email": email,
        "password": "password123",
    })
    assert signup.status_code == 201

    login = client.post("/auth/login", json={
        "email": email,
        "password": "password123",
    })
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def created_centre_and_test():
    centre = client.post("/centres/", json={
        "name": "City Lab",
        "location": "Downtown",
        "phone": "123456"
    })
    assert centre.status_code == 201
    centre_id = centre.json()["id"]

    test = client.post(f"/centres/{centre_id}/tests/", json={
        "name": "Blood Test",
        "description": "Routine blood analysis",
        "price": 120.0,
    })
    assert test.status_code == 201
    return centre_id, test.json()["id"]


def test_signup_login_and_auth():
    response = client.post("/auth/signup", json={
        "full_name": "Alice User",
        "email": "alice@example.com",
        "password": "Password123!",
    })
    assert response.status_code == 201

    login = client.post("/auth/login", json={
        "email": "alice@example.com",
        "password": "Password123!",
    })
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_create_booking_and_payment_flow(auth_headers, created_centre_and_test):
    centre_id, test_id = created_centre_and_test

    booking = client.post(
        "/bookings/",
        json={
            "test_id": test_id,
            "centre_id": centre_id,
            "appointment_datetime": (datetime.utcnow() + timedelta(days=2)).isoformat(),
        },
        headers=auth_headers,
    )
    assert booking.status_code == 201, booking.text
    booking_id = booking.json()["id"]

    payment = client.post(
        "/payments/",
        json={
            "booking_id": booking_id,
            "amount": 120.0,
            "provider": "mock-provider",
        },
        headers=auth_headers,
    )
    assert payment.status_code == 201, payment.text
    assert payment.json()["status"] in {"SUCCESS", "FAILED"}


def test_webhook_is_idempotent(auth_headers, created_centre_and_test):
    centre_id, test_id = created_centre_and_test

    booking = client.post(
        "/bookings/",
        json={
            "test_id": test_id,
            "centre_id": centre_id,
            "appointment_datetime": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        },
        headers=auth_headers,
    )
    booking_id = booking.json()["id"]

    payload = {
        "event_id": "evt-123",
        "event_type": "payment.success",
        "booking_id": booking_id,
        "status": "SUCCESS",
        "external_reference": "ext-123",
        "provider": "mock-provider",
    }

    first = client.post("/payments/webhook/", json=payload)
    assert first.status_code == 200
    assert first.json()["processed"] is True

    second = client.post("/payments/webhook/", json=payload)
    assert second.status_code == 200
    assert second.json()["idempotent"] is True


def test_invalid_booking_id_returns_404(auth_headers):
    response = client.post(
        "/payments/",
        json={"booking_id": 9999, "amount": 100.0},
        headers=auth_headers,
    )
    assert response.status_code == 404
