"""Canonical user-owned tracking API tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from web_app.backend.db.models import Base
from web_app.backend.db.session import engine


pytestmark = pytest.mark.api


@pytest.fixture
def tracking_client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    from web_app.backend.main import app

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


def register_and_authorize(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": f"tracking-{uuid4().hex}@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_tracking_requires_authentication(tracking_client):
    response = tracking_client.get("/api/tracking/products")
    assert response.status_code == 401


def test_tracking_is_scoped_to_the_authenticated_user(tracking_client):
    first_user_headers = register_and_authorize(tracking_client)
    second_user_headers = register_and_authorize(tracking_client)
    product = {
        "title": "Canonical Test Product",
        "price": 25.0,
        "bsr": 1200,
        "reviews": 100,
        "rating": 4.5,
        "image_url": "https://example.com/product.jpg",
    }

    response = tracking_client.post(
        "/api/tracking/add",
        headers=first_user_headers,
        json={
            "asin": "B08TRACK01",
            "marketplace": "US",
            "product_data": product,
            "alert_settings": {"price_drop_pct": 8.0, "notes": "Watch price"},
        },
    )
    assert response.status_code == 200
    tracked = response.json()["product"]
    assert tracked["asin"] == "B08TRACK01"
    assert tracked["alert_settings"]["price_drop_pct"] == 8.0
    assert tracked["notes"] == "Watch price"
    assert tracked["current_opportunity_score"] is None
    assert tracked["trends"]["price"] == "Insufficient Data"
    assert tracked["data_quality"]["status"] == "Fresh"

    response = tracking_client.get(
        "/api/tracking/products", headers=second_user_headers
    )
    assert response.status_code == 200
    assert response.json()["products"] == []

    response = tracking_client.get(
        "/api/tracking/B08TRACK01/history", headers=first_user_headers
    )
    assert response.status_code == 200
    assert len(response.json()["history"]) == 1

    response = tracking_client.put(
        "/api/tracking/B08TRACK01/settings",
        headers=first_user_headers,
        json={"review_increase": 25},
    )
    assert response.status_code == 200

    response = tracking_client.get("/api/tracking/stats", headers=first_user_headers)
    assert response.status_code == 200
    assert response.json() == {
        "total_products": 1,
        "active_products": 1,
        "unread_alerts": 0,
    }
