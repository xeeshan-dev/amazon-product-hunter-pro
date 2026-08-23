"""Aggregate canonical product observations into conservative market views."""
from __future__ import annotations

from statistics import mean, median
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from web_app.backend.db.models import Product, ProductSnapshot


class MarketIntelligenceService:
    def list_categories(self, db: Session) -> List[Dict[str, Any]]:
        categories = sorted({category for (category,) in db.query(Product.category).filter(Product.category.isnot(None)).all() if category})
        return [self.category_summary(db, category) for category in categories]

    def category_summary(self, db: Session, category: str) -> Dict[str, Any]:
        products = db.query(Product).filter(Product.category == category).all()
        snapshots = [self._latest_snapshot(db, product.id) for product in products]
        snapshots = [snapshot for snapshot in snapshots if snapshot is not None]
        prices = self._values(snapshots, "price")
        reviews = self._values(snapshots, "reviews")
        scores = self._values(snapshots, "opportunity_score")
        revenues = self._values(snapshots, "estimated_revenue")
        sellers = self._values(snapshots, "seller_count")
        return {
            "category": category,
            "product_count": len(products),
            "observed_product_count": len(snapshots),
            "median_price": self._median(prices),
            "average_reviews": self._average(reviews),
            "average_opportunity_score": self._average(scores),
            "median_estimated_revenue": self._median(revenues),
            "average_seller_count": self._average(sellers),
            "data_notice": "Aggregates reflect only canonical observations currently stored by this application.",
        }

    @staticmethod
    def _latest_snapshot(db: Session, product_id: int) -> Optional[ProductSnapshot]:
        return db.query(ProductSnapshot).filter(ProductSnapshot.product_id == product_id).order_by(
            ProductSnapshot.recorded_at.desc(), ProductSnapshot.id.desc()
        ).first()

    @staticmethod
    def _values(snapshots: List[ProductSnapshot], field: str) -> List[float]:
        return [getattr(snapshot, field) for snapshot in snapshots if getattr(snapshot, field) is not None]

    @staticmethod
    def _average(values: List[float]) -> Optional[float]:
        return round(mean(values), 2) if values else None

    @staticmethod
    def _median(values: List[float]) -> Optional[float]:
        return round(median(values), 2) if values else None
