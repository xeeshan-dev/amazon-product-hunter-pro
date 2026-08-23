"""Provider-boundary tests for canonical tracking refreshes."""

import pytest

from web_app.backend.db.models import Base, ProductSnapshot, User
from web_app.backend.db.session import SessionLocal, engine
from web_app.backend.services.canonical_tracking_service import CanonicalTrackingService

pytestmark = pytest.mark.unit


class FakeProductProvider:
    def __init__(self):
        self.requested_asins = []

    async def get_product(self, asin):
        self.requested_asins.append(asin)
        return {
            "asin": asin,
            "title": "Refreshed Product",
            "price": 18.0,
            "bsr": 800,
            "reviews": 130,
            "rating": 4.6,
            "estimated_sales": 120,
            "est_revenue": 2160.0,
            "est_profit": 500.0,
            "margin": 28.0,
            "enhanced_score": 72.0,
        }


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


@pytest.mark.asyncio
async def test_tracking_refresh_uses_product_provider_and_records_snapshot(db):
    user = User(email="provider@example.com", password_hash="not-used")
    db.add(user)
    db.commit()
    provider = FakeProductProvider()
    service = CanonicalTrackingService(provider=provider)
    service.add_product(
        db,
        user,
        "B0TRACKPROVIDER",
        {"title": "Initial Product", "price": 20.0, "bsr": 1000, "reviews": 100},
        alert_settings={
            "price_drop_pct": 100.0,
            "bsr_improve_pct": 100.0,
            "review_increase": 100,
        },
    )

    result = await service.check_products(db, user)

    assert result == {"checked": 1, "updated": 1, "alerts_generated": 0, "errors": 0}
    assert provider.requested_asins == ["B0TRACKPROVIDER"]
    snapshots = db.query(ProductSnapshot).order_by(ProductSnapshot.id).all()
    assert [snapshot.price for snapshot in snapshots] == [20.0, 18.0]
    assert snapshots[-1].opportunity_score == 72.0
