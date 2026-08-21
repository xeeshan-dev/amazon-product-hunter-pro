"""Authentication API contract tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from web_app.backend.db.models import Base
from web_app.backend.db.session import engine


pytestmark = pytest.mark.api


@pytest.fixture
def auth_client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    from web_app.backend.main import app

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


def register_payload():
    return {
        "email": f"user-{uuid4().hex}@example.com",
        "password": "correct-horse-battery-staple",
        "full_name": "Test User",
    }


def test_register_login_and_current_user(auth_client):
    payload = register_payload()
    response = auth_client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    registered = response.json()
    assert registered["token_type"] == "bearer"
    assert registered["user"]["email"] == payload["email"]
    assert "password" not in registered["user"]

    response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == payload["email"]

    response = auth_client.post(
        "/api/auth/login",
        json={"email": payload["email"].upper(), "password": payload["password"]},
    )
    assert response.status_code == 200
    assert response.json()["user"]["id"] == registered["user"]["id"]


def test_registration_rejects_duplicate_email(auth_client):
    payload = register_payload()
    assert auth_client.post("/api/auth/register", json=payload).status_code == 201

    response = auth_client.post("/api/auth/register", json=payload)
    assert response.status_code == 409


def test_current_user_requires_a_valid_token(auth_client):
    assert auth_client.get("/api/auth/me").status_code == 401

    response = auth_client.get(
        "/api/auth/me", headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401
