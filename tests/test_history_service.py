"""Deterministic historical-intelligence tests."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from web_app.backend.db.models import Base, Product, ProductSnapshot
from web_app.backend.db.session import SessionLocal, engine
from web_app.backend.services.history_service import HistoryService

pytestmark = pytest.mark.unit


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


def add_snapshot(db, product, observed_at, price, bsr, reviews, score):
    db.add(
        ProductSnapshot(
            product_id=product.id,
            recorded_at=observed_at,
            source="amazon_html",
            price=price,
            bsr=bsr,
            reviews=reviews,
            estimated_sales=100,
            margin=30.0,
            opportunity_score=score,
            confidence=0.8,
        )
    )


def test_history_service_returns_metrics_trends_and_freshness(db):
    product = Product(asin="B0HISTORY1", marketplace="US", title="History Product")
    db.add(product)
    db.flush()
    now = datetime.now(timezone.utc)
    add_snapshot(db, product, now - timedelta(days=2), 10.0, 12000, 100, 60.0)
    add_snapshot(db, product, now - timedelta(days=1), 15.0, 10000, 130, 65.0)
    add_snapshot(db, product, now, 12.0, 8000, 160, 70.0)
    db.commit()

    service = HistoryService()
    intelligence = service.get_product_intelligence(db, product.id)

    assert intelligence["price"] == {
        "current": 12.0,
        "minimum": 10.0,
        "maximum": 15.0,
        "average": 12.333333333333334,
        "change_pct": 20.0,
        "volatility": 16.660578386402637,
        "trend": "Improving",
    }
    assert intelligence["bsr"]["current"] == 8000
    assert intelligence["bsr"]["previous"] == 10000
    assert intelligence["bsr"]["absolute_change"] == -2000
    assert intelligence["bsr"]["trend"] == "Improving"
    assert intelligence["bsr"]["improvement"] is True
    assert intelligence["reviews"]["gained"] == 60
    assert intelligence["reviews"]["velocity_per_day"] == pytest.approx(30.0)
    assert intelligence["opportunity_score"]["change"] == 5.0
    assert intelligence["opportunity_score"]["trend"] == "Improving"
    assert intelligence["freshness"]["status"] == "Fresh"
    assert intelligence["freshness"]["source"] == "amazon_html"


def test_history_service_reports_insufficient_data_and_aging_observation(db):
    product = Product(asin="B0HISTORY2", marketplace="US", title="Limited History")
    db.add(product)
    db.flush()
    now = datetime.now(timezone.utc)
    add_snapshot(db, product, now - timedelta(hours=8), 10.0, 10000, 10, 50.0)
    add_snapshot(db, product, now - timedelta(hours=7), 9.0, 9000, 15, 55.0)
    db.commit()

    service = HistoryService(
        settings=SimpleNamespace(OBSERVATION_FRESH_HOURS=6, OBSERVATION_STALE_HOURS=48)
    )
    intelligence = service.get_product_intelligence(db, product.id)

    assert intelligence["price"]["trend"] == "Insufficient Data"
    assert intelligence["bsr"]["trend"] == "Insufficient Data"
    assert intelligence["reviews"]["trend"] == "Insufficient Data"
    assert intelligence["opportunity_score"]["trend"] == "Insufficient Data"
    assert intelligence["freshness"]["status"] == "Aging"
    assert len(service.get_price_history(db, product.id)) == 2
    assert len(service.get_product_timeline(db, product.id, days=1)) == 2
