"""
Pytest configuration and fixtures
"""
import pytest
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(project_root))

# Set test environment
os.environ['ENVIRONMENT'] = 'testing'
os.environ['DEBUG'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key-minimum-32-characters-long'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key-minimum-32-characters'
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'
os.environ['REDIS_URL'] = 'redis://localhost:6379/15'  # Use different DB for tests


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    from unittest.mock import MagicMock
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = True
    redis_mock.incr.return_value = 1
    return redis_mock


@pytest.fixture
def sample_product():
    """Sample product data for testing"""
    return {
        'asin': 'B08TEST123',
        'title': 'Test Product - High Quality Widget',
        'price': 29.99,
        'rating': 4.5,
        'reviews': 250,
        'bsr': 5000,
        'brand': 'TestBrand',
        'category': 'Home & Kitchen',
        'url': 'https://www.amazon.com/dp/B08TEST123',
        'seller_info': {
            'fba_count': 5,
            'fbm_count': 2,
            'amazon_seller': False,
            'total_sellers': 7,
            'prices': {
                'fba': [29.99, 30.99, 31.99],
                'fbm': [28.99, 32.99]
            }
        }
    }


@pytest.fixture
def sample_search_results():
    """Sample search results for testing"""
    return [
        {
            'asin': f'B08TEST{i:03d}',
            'title': f'Test Product {i}',
            'price': 20.0 + i,
            'rating': 4.0 + (i * 0.1),
            'reviews': 100 + (i * 10),
            'bsr': 1000 * i,
            'url': f'https://www.amazon.com/dp/B08TEST{i:03d}'
        }
        for i in range(1, 11)
    ]
