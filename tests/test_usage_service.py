"""Usage-event and account contract tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from web_app.backend.db.models import Base, User
from web_app.backend.db.session import SessionLocal, engine
from web_app.backend.services.plan_service import PlanService
from web_app.backend.services.usage_service import UsageService

pytestmark = pytest.mark.api


@pytest.fixture
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_usage_service_summarizes_known_events_and_plan_limits(db):
    user = User(email="usage@example.com", password_hash="unused")
    db.add(user)
    db.commit()
    usage = UsageService()
    usage.record(db, "search", user.id)
    usage.record(db, "search", user.id)
    usage.record(db, "tracking_add", user.id, {"asin": "B0USAGE"})

    assert usage.summary(db, user.id) == {
        "search": 2,
        "product_analysis": 0,
        "keyword_search": 0,
        "export": 0,
        "tracking_add": 1,
    }
    assert PlanService().limits_for("FREE")["tracking_add"] == 25
    assert PlanService().limits_for("unknown") == PlanService().limits_for("FREE")


def test_account_endpoint_returns_user_usage_and_limits():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from web_app.backend.main import app, tools

    with TestClient(app) as client:
        registration = client.post(
            "/api/auth/register",
            json={
                "email": f"account-{uuid4().hex}@example.com",
                "password": "correct-horse-battery-staple",
            },
        )
        assert registration.status_code == 201
        token = registration.json()["access_token"]
        user_id = registration.json()["user"]["id"]
        session = SessionLocal()
        try:
            tools["usage"].record(session, "search", user_id)
        finally:
            session.close()
        response = client.get("/api/account", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["usage"]["search"] == 1
    assert response.json()["limits"]["tracking_add"] == 25
    Base.metadata.drop_all(bind=engine)
