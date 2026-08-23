"""Single-ASIN analyzer service tests."""

import pytest

from web_app.backend.db.models import Base, Product, ProductSnapshot
from web_app.backend.db.session import SessionLocal, engine
from web_app.backend.services.product_analyzer_service import (
    ProductAnalyzerService,
    ProductNotFoundError,
)

pytestmark = pytest.mark.unit


class FakeProvider:
    def __init__(self, product=None):
        self.product = product
        self.calls = []

    async def get_product(self, asin):
        self.calls.append(asin)
        return self.product


class FakePipeline:
    async def analyze_product(self, product, provider):
        return {
            **product,
            "est_revenue": 2000.0,
            "est_profit": 400.0,
            "margin": 25.0,
            "enhanced_score": 82.0,
            "_search_confidence": 0.8,
            "risks": {"brand_risk": "SAFE", "hazmat": False},
            "seller_info": {"total_sellers": 3, "amazon_seller": False},
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
async def test_analyzer_fetches_missing_asin_and_persists_observation(db):
    provider = FakeProvider({
        "asin": "B0ANALYZER", "title": "Analyzer Product", "price": 20.0,
        "rating": 4.5, "reviews": 120, "bsr": 4000, "estimated_sales": 100,
    })
    service = ProductAnalyzerService(provider, FakePipeline())

    result = await service.analyze(db, "b0analyzer", "US")

    assert provider.calls == ["B0ANALYZER"]
    assert result["overview"]["asin"] == "B0ANALYZER"
    assert result["recommendation"] == {"label": "Strong Opportunity", "score": 82.0, "warnings": []}
    assert result["data_quality"]["confidence"] == 0.8
    assert db.query(Product).count() == 1
    assert db.query(ProductSnapshot).count() == 1


@pytest.mark.asyncio
async def test_analyzer_uses_canonical_product_and_history_for_marketplace(db):
    product = Product(asin="B0CACHED", marketplace="UK", title="Cached Product")
    db.add(product)
    db.flush()
    db.add(ProductSnapshot(product_id=product.id, price=15.0, bsr=3000, reviews=20, opportunity_score=65.0, source="amazon_html"))
    db.commit()
    provider = FakeProvider()
    service = ProductAnalyzerService(provider, FakePipeline())

    result = await service.analyze(db, "B0CACHED", "UK")
    history = service.get_history(db, "B0CACHED", "UK", 30)

    assert provider.calls == []
    assert result["overview"]["marketplace"] == "UK"
    assert result["recommendation"]["label"] == "Worth Validating"
    assert len(history["history"]) == 1


@pytest.mark.asyncio
async def test_analyzer_reports_missing_product_when_provider_has_no_result(db):
    service = ProductAnalyzerService(FakeProvider(), FakePipeline())

    with pytest.raises(ProductNotFoundError):
        await service.analyze(db, "B0MISSING", "US")
