"""Canonical API contract tests for the active FastAPI runtime."""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.api

# Set environment before imports
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-characters-long"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-minimum-32-characters"


@pytest.fixture
def client():
    """Create a test client for the canonical backend."""
    with patch("redis.from_url") as mock_redis:
        redis_mock = MagicMock()
        redis_mock.ping.return_value = True
        redis_mock.incr.return_value = 1
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.info.return_value = {
            "connected_clients": 1,
            "used_memory_human": "1M",
            "total_commands_processed": 100,
        }
        mock_redis.return_value = redis_mock

        from web_app.backend.main import app

        with TestClient(app) as test_client:
            yield test_client


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_search_validation(client):
    response = client.post("/api/search", json={})
    assert response.status_code == 422

    response = client.post(
        "/api/search",
        json={
            "keyword": "test",
            "marketplace": "INVALID",
        },
    )
    assert response.status_code == 422

    response = client.post(
        "/api/search",
        json={
            "keyword": "test",
            "min_rating": 6.0,
        },
    )
    assert response.status_code == 422


@patch("scraper.amazon_scraper.AmazonScraper.search_products")
def test_search_success(mock_search, client, sample_search_results):
    mock_search.return_value = sample_search_results

    response = client.post(
        "/api/search",
        json={
            "keyword": "yoga mat",
            "marketplace": "US",
            "pages": 1,
            "min_sales": 0,
            "skip_amazon_seller": False,
            "skip_brand_seller": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "results" in data
    assert "metadata" in data


def test_keywords_endpoint(client):
    with patch(
        "analysis.keyword_tool.FreeKeywordTool.get_autocomplete_suggestions"
    ) as mock_keywords:
        from analysis.keyword_tool import KeywordSuggestion

        mock_keywords.return_value = [
            KeywordSuggestion(
                keyword="test keyword 1",
                source="amazon",
                estimated_competition="unknown",
                relevance_score=0.9,
            ),
            KeywordSuggestion(
                keyword="test keyword 2",
                source="amazon",
                estimated_competition="unknown",
                relevance_score=0.8,
            ),
        ]

        response = client.get("/api/keywords?q=test")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) == 2
