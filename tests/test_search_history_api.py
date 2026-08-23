"""User-owned search history and dashboard contract tests."""

from uuid import uuid4
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from web_app.backend.db.models import Base
from web_app.backend.db.session import engine

pytestmark = pytest.mark.api


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from web_app.backend.main import app

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


def register(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": f"history-{uuid4().hex}@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def provider_product(asin="B0HISTORYAPI"):
    return {
        "asin": asin,
        "title": "Search History Product",
        "brand": "History Brand",
        "category": "Home & Kitchen",
        "price": 24.0,
        "rating": 4.5,
        "reviews": 125,
        "bsr": 5000,
        "estimated_sales": 100,
        "url": f"https://www.amazon.com/dp/{asin}",
    }


def search_payload(keyword="storage bins"):
    return {
        "keyword": keyword,
        "min_sales": 0,
        "min_margin": 0,
        "skip_amazon_seller": False,
        "skip_brand_seller": False,
    }


@patch("scraper.amazon_scraper.AmazonScraper.search_products")
def test_search_history_detail_results_and_dashboard_are_user_scoped(mock_search, client):
    mock_search.return_value = [provider_product()]
    first_user = register(client)
    second_user = register(client)

    created = client.post("/api/search", json=search_payload(), headers=first_user)
    assert created.status_code == 200

    anonymous = client.get("/api/search/history")
    assert anonymous.status_code == 401

    history = client.get("/api/search/history", headers=first_user)
    assert history.status_code == 200
    body = history.json()
    assert body["total"] == 1
    assert body["searches"][0]["keyword"] == "storage bins"
    assert body["searches"][0]["result_count"] == 1
    search_id = body["searches"][0]["id"]

    detail = client.get(f"/api/search/{search_id}", headers=first_user)
    assert detail.status_code == 200
    assert detail.json()["filters"]["min_sales"] == 0

    results = client.get(f"/api/search/{search_id}/results", headers=first_user)
    assert results.status_code == 200
    result = results.json()["results"][0]
    assert result["product"]["asin"] == "B0HISTORYAPI"
    assert result["snapshot"]["price"] == 24.0
    assert result["snapshot"]["opportunity_score"] is not None

    hidden = client.get(f"/api/search/{search_id}", headers=second_user)
    assert hidden.status_code == 404
    assert client.get(f"/api/search/{search_id}/results", headers=second_user).status_code == 404

    dashboard = client.get("/api/dashboard", headers=first_user)
    assert dashboard.status_code == 200
    assert dashboard.json()["recent_searches"][0]["id"] == search_id
    assert dashboard.json()["strong_opportunities"] >= 0


@patch("scraper.amazon_scraper.AmazonScraper.search_products")
def test_search_history_paginates_only_the_current_users_searches(mock_search, client):
    mock_search.return_value = [provider_product()]
    headers = register(client)
    for keyword in ("first search", "second search"):
        assert client.post("/api/search", json=search_payload(keyword), headers=headers).status_code == 200

    response = client.get("/api/search/history?limit=1&offset=1", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["searches"]) == 1
    assert response.json()["limit"] == 1
    assert response.json()["offset"] == 1
