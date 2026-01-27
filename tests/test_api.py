"""
API endpoint tests
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Set environment before imports
os.environ['ENVIRONMENT'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key-minimum-32-characters-long'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key-minimum-32-characters'


@pytest.fixture
def client():
    """Create test client"""
    with patch('redis.from_url') as mock_redis:
        # Mock Redis
        redis_mock = MagicMock()
        redis_mock.ping.return_value = True
        redis_mock.incr.return_value = 1
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.info.return_value = {
            'connected_clients': 1,
            'used_memory_human': '1M',
            'total_commands_processed': 100
        }
        mock_redis.return_value = redis_mock
        
        from web_app.backend.main_v2 import app
        with TestClient(app) as test_client:
            yield test_client


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] in ['healthy', 'degraded']
    assert 'version' in data
    assert 'services' in data


def test_readiness_check(client):
    """Test readiness endpoint"""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()['status'] == 'ready'


def test_metrics_endpoint(client):
    """Test metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert 'redis' in data


def test_search_validation(client):
    """Test search request validation"""
    # Missing keyword
    response = client.post("/api/search", json={})
    assert response.status_code == 422
    
    # Invalid marketplace
    response = client.post("/api/search", json={
        "keyword": "test",
        "marketplace": "INVALID"
    })
    assert response.status_code == 422
    
    # Invalid rating
    response = client.post("/api/search", json={
        "keyword": "test",
        "min_rating": 6.0
    })
    assert response.status_code == 422


@patch('scraper.amazon_scraper.AmazonScraper.search_products')
def test_search_success(mock_search, client, sample_search_results):
    """Test successful search"""
    mock_search.return_value = sample_search_results
    
    response = client.post("/api/search", json={
        "keyword": "yoga mat",
        "marketplace": "US",
        "pages": 1
    })
    
    assert response.status_code == 200
    data = response.json()
    assert 'summary' in data
    assert 'results' in data
    assert 'metadata' in data


def test_keywords_endpoint(client):
    """Test keywords endpoint"""
    with patch('analysis.keyword_tool.FreeKeywordTool.get_autocomplete_suggestions') as mock_keywords:
        from analysis.keyword_tool import KeywordSuggestion
        mock_keywords.return_value = [
            KeywordSuggestion(keyword="test keyword 1", source="amazon", relevance_score=0.9),
            KeywordSuggestion(keyword="test keyword 2", source="amazon", relevance_score=0.8)
        ]
        
        response = client.get("/api/keywords?q=test")
        assert response.status_code == 200
        data = response.json()
        assert 'suggestions' in data
        assert len(data['suggestions']) == 2


def test_product_detail_invalid_asin(client):
    """Test product detail with invalid ASIN"""
    response = client.get("/api/product/INVALID")
    assert response.status_code == 422  # Validation error


@patch('scraper.amazon_scraper.AmazonScraper.get_product_details')
def test_product_detail_not_found(mock_get_product, client):
    """Test product detail when product not found"""
    mock_get_product.return_value = None
    
    response = client.get("/api/product/B08TEST123")
    assert response.status_code == 404


@patch('scraper.amazon_scraper.AmazonScraper.get_product_details')
def test_product_detail_success(mock_get_product, client, sample_product):
    """Test successful product detail fetch"""
    mock_get_product.return_value = sample_product
    
    response = client.get("/api/product/B08TEST123")
    assert response.status_code == 200
    data = response.json()
    assert data['asin'] == 'B08TEST123'
    assert 'enhanced_score' in data
