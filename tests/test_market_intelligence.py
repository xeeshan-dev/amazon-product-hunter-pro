"""Market aggregate tests over canonical latest observations."""

import pytest

from web_app.backend.db.models import Base, Product, ProductSnapshot
from web_app.backend.db.session import SessionLocal, engine
from web_app.backend.services.market_intelligence_service import MarketIntelligenceService

pytestmark = pytest.mark.unit


@pytest.fixture
def db():
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try: yield session
    finally: session.close(); Base.metadata.drop_all(bind=engine)


def test_category_summary_uses_only_each_products_latest_snapshot(db):
    first = Product(asin="B0MARKET1", marketplace="US", title="First", category="Kitchen")
    second = Product(asin="B0MARKET2", marketplace="US", title="Second", category="Kitchen")
    db.add_all([first, second]); db.flush()
    db.add_all([
        ProductSnapshot(product_id=first.id, price=10, reviews=10, opportunity_score=50, estimated_revenue=100, seller_count=1),
        ProductSnapshot(product_id=first.id, price=30, reviews=30, opportunity_score=70, estimated_revenue=300, seller_count=3),
        ProductSnapshot(product_id=second.id, price=20, reviews=20, opportunity_score=90, estimated_revenue=200, seller_count=5),
    ]); db.commit()

    summary = MarketIntelligenceService().category_summary(db, "Kitchen")
    assert summary["product_count"] == 2
    assert summary["observed_product_count"] == 2
    assert summary["median_price"] == 25.0
    assert summary["average_reviews"] == 25.0
    assert summary["average_opportunity_score"] == 80.0
    assert summary["average_seller_count"] == 4.0
