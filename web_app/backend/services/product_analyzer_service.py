"""Single-ASIN analysis built from providers and canonical observations."""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from web_app.backend.db.models import Product, ProductSnapshot
from web_app.backend.services.history_service import HistoryService
from web_app.backend.services.search_persistence_service import SearchPersistenceService
from web_app.backend.services.confidence_service import ConfidenceService


class ProductNotFoundError(RuntimeError):
    """Raised when neither canonical data nor the provider can find an ASIN."""


class ProductAnalyzerService:
    def __init__(self, provider, pipeline, history_service: Optional[HistoryService] = None, confidence_service: Optional[ConfidenceService] = None):
        self.provider = provider
        self.pipeline = pipeline
        self.history_service = history_service or HistoryService()
        self.persistence = SearchPersistenceService()
        self.confidence_service = confidence_service or ConfidenceService()

    async def analyze(self, db: Session, asin: str, marketplace: str = "US") -> Dict[str, Any]:
        product = self._find_product(db, asin, marketplace)
        intelligence = self.history_service.get_product_intelligence(db, product.id) if product else None
        if product is None or intelligence["freshness"]["status"] == "Stale":
            fetched = await self.provider.get_product(asin.strip().upper())
            if fetched:
                analyzed = await self.pipeline.analyze_product(fetched, self.provider)
                product, snapshot = self.persistence.create_observation(db, analyzed, marketplace)
                db.commit()
                intelligence = self.history_service.get_product_intelligence(db, product.id)
                return self._serialize(product, snapshot, intelligence, analyzed)
            if product is None:
                raise ProductNotFoundError("Product was not found")

        snapshot = self._latest_snapshot(db, product.id)
        return self._serialize(product, snapshot, intelligence, snapshot.raw_data or {})

    def get_history(self, db: Session, asin: str, marketplace: str, days: int) -> Dict[str, Any]:
        product = self._find_product(db, asin, marketplace)
        if product is None:
            raise ProductNotFoundError("Product was not found")
        return {
            "asin": product.asin,
            "marketplace": product.marketplace,
            "history": self.history_service.get_product_timeline(db, product.id, days),
            "metrics": self.history_service.get_product_intelligence(db, product.id, days),
        }

    @staticmethod
    def _find_product(db: Session, asin: str, marketplace: str) -> Optional[Product]:
        return db.query(Product).filter(
            Product.asin == asin.strip().upper(),
            Product.marketplace == marketplace.strip().upper(),
        ).first()

    @staticmethod
    def _latest_snapshot(db: Session, product_id: int) -> Optional[ProductSnapshot]:
        return db.query(ProductSnapshot).filter(ProductSnapshot.product_id == product_id).order_by(
            ProductSnapshot.recorded_at.desc(), ProductSnapshot.id.desc()
        ).first()

    def _serialize(self, product, snapshot, intelligence, data):
        score = snapshot.opportunity_score if snapshot else None
        quality = self.confidence_service.data_quality(intelligence["freshness"], snapshot)
        return {
            "overview": {"asin": product.asin, "marketplace": product.marketplace, "title": product.title, "brand": product.brand, "category": product.category, "image_url": product.image_url, "product_url": product.product_url},
            "demand": {"bsr": snapshot.bsr if snapshot else None, "estimated_sales": snapshot.estimated_sales if snapshot else None, "estimated_revenue": snapshot.estimated_revenue if snapshot else None},
            "competition": {"reviews": snapshot.reviews if snapshot else None, "rating": snapshot.rating if snapshot else None, "seller_count": snapshot.seller_count if snapshot else None, "amazon_seller": (data.get("seller_info") or {}).get("amazon_seller")},
            "profitability": {"price": snapshot.price if snapshot else None, "estimated_profit": snapshot.estimated_profit if snapshot else None, "margin": snapshot.margin if snapshot else None},
            "risk": data.get("risks") or {},
            "listing": {"source": snapshot.source if snapshot else None, "recorded_at": snapshot.recorded_at.isoformat() if snapshot else None},
            "trends": intelligence,
            "recommendation": self._recommendation(score, data.get("risks") or {}),
            "data_quality": quality,
            "estimates": {
                "monthly_sales": self.confidence_service.estimate(snapshot.estimated_sales if snapshot else None, snapshot, "BSR + category model"),
                "monthly_revenue": self.confidence_service.estimate(snapshot.estimated_revenue if snapshot else None, snapshot, "selling price x estimated monthly sales"),
                "profit_per_unit": self.confidence_service.estimate(snapshot.estimated_profit if snapshot else None, snapshot, "FBA fee and COGS model"),
                "margin": self.confidence_service.estimate(snapshot.margin if snapshot else None, snapshot, "FBA fee and COGS model"),
            },
        }

    @staticmethod
    def _recommendation(score, risks):
        if score is None:
            return {"label": "Insufficient Data", "score": None, "warnings": ["No opportunity score is available yet."]}
        if risks.get("brand_risk") not in (None, "SAFE") or risks.get("hazmat"):
            label = "Validate Risk"
        elif score >= 80:
            label = "Strong Opportunity"
        elif score >= 60:
            label = "Worth Validating"
        else:
            label = "Low Opportunity"
        return {"label": label, "score": score, "warnings": []}
