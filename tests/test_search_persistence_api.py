"""API ownership and safe-error tests for persisted searches."""

from uuid import uuid4
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from web_app.backend.db.models import Base, Search
from web_app.backend.db.session import SessionLocal, engine
from web_app.backend.services.search_persistence_service import SearchPersistenceError

pytestmark = pytest.mark.api


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from web_app.backend.main import app

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


def product(asin="B0APISEARCH"):
    return {
        "asin": asin,
        "title": "API Persistence Product",
        "brand": "Example Brand",
        "category": "Home & Kitchen",
        "price": 25.0,
        "rating": 4.5,
        "reviews": 150,
        "bsr": 5000,
        "estimated_sales": 100,
        "url": f"https://www.amazon.com/dp/{asin}",
    }


def search_payload():
    return {
        "keyword": "storage bins",
        "min_sales": 0,
        "min_margin": 0,
        "skip_amazon_seller": False,
        "skip_brand_seller": False,
    }


@patch("scraper.amazon_scraper.AmazonScraper.search_products")
def test_authenticated_search_is_persisted_for_the_token_user(mock_search, client):
    mock_search.return_value = [product()]
    registration = client.post(
        "/api/auth/register",
        json={
            "email": f"search-{uuid4().hex}@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert registration.status_code == 201

    response = client.post(
        "/api/search",
        json=search_payload(),
        headers={"Authorization": f"Bearer {registration.json()['access_token']}"},
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        search = db.query(Search).one()
        assert search.user_id == registration.json()["user"]["id"]
        assert search.keyword == "storage bins"
    finally:
        db.close()


@patch("scraper.amazon_scraper.AmazonScraper.search_products")
def test_persistence_error_returns_a_safe_api_message(mock_search, client):
    mock_search.return_value = [product()]
    from web_app.backend.main import tools

    with patch.object(
        tools["search_pipeline"].persistence_service,
        "persist",
        side_effect=SearchPersistenceError("driver detail must not be exposed"),
    ):
        response = client.post("/api/search", json=search_payload())

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to save search results"}
