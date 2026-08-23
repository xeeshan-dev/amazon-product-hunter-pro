"""Historical product intelligence derived from immutable snapshots."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from analytics.trends import classify_trend
from config.settings import get_settings
from web_app.backend.db.models import ProductSnapshot


class HistoryService:
    """Read product observations without embedding database queries in routes."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    def get_product_timeline(
        self, db: Session, product_id: int, days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        snapshots = self._get_snapshots(db, product_id, days)
        return [self._serialize_snapshot(snapshot) for snapshot in snapshots]

    def get_price_history(self, db: Session, product_id: int, days: Optional[int] = None):
        return self._metric_history(db, product_id, "price", days)

    def get_bsr_history(self, db: Session, product_id: int, days: Optional[int] = None):
        return self._metric_history(db, product_id, "bsr", days)

    def get_review_history(self, db: Session, product_id: int, days: Optional[int] = None):
        return self._metric_history(db, product_id, "reviews", days)

    def get_sales_history(self, db: Session, product_id: int, days: Optional[int] = None):
        return self._metric_history(db, product_id, "estimated_sales", days)

    def get_margin_history(self, db: Session, product_id: int, days: Optional[int] = None):
        return self._metric_history(db, product_id, "margin", days)

    def get_score_history(self, db: Session, product_id: int, days: Optional[int] = None):
        return self._metric_history(db, product_id, "opportunity_score", days)

    def get_observation_history_for_asin(
        self,
        db: Session,
        asin: str,
        marketplace: str = "US",
        days: Optional[int] = 30,
    ) -> Optional[Dict[str, List[Optional[float]]]]:
        """Return chronological metric series for one ASIN, or None.

        Series are ordered oldest-first so downstream trend classification can
        compare first-to-last movement directly. This is a read-only lookup;
        callers must not rely on it to create products or snapshots.
        """
        from web_app.backend.db.models import Product

        normalized_asin = (asin or "").strip().upper()
        normalized_marketplace = (marketplace or "US").strip().upper()
        product = (
            db.query(Product)
            .filter(
                Product.asin == normalized_asin,
                Product.marketplace == normalized_marketplace,
            )
            .first()
        )
        if product is None:
            return None

        snapshots = self._get_snapshots(db, product.id, days)
        if not snapshots:
            return None

        def series(field: str) -> List[Optional[float]]:
            return [
                getattr(snapshot, field)
                for snapshot in snapshots
                if getattr(snapshot, field) is not None
            ]

        history = {
            "price": series("price"),
            "bsr": series("bsr"),
            "reviews": series("reviews"),
        }
        return {name: values for name, values in history.items() if values} or None

    def get_product_intelligence(
        self, db: Session, product_id: int, days: Optional[int] = None
    ) -> Dict[str, Any]:
        snapshots = self._get_snapshots(db, product_id, days)
        return {
            "price": self._price_metrics(snapshots),
            "bsr": self._bsr_metrics(snapshots),
            "reviews": self._review_metrics(snapshots),
            "opportunity_score": self._score_metrics(snapshots),
            "freshness": self._freshness(snapshots[-1] if snapshots else None),
        }

    @staticmethod
    def _get_snapshots(
        db: Session, product_id: int, days: Optional[int]
    ) -> List[ProductSnapshot]:
        query = db.query(ProductSnapshot).filter(ProductSnapshot.product_id == product_id)
        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(ProductSnapshot.recorded_at >= cutoff)
        return query.order_by(ProductSnapshot.recorded_at.asc(), ProductSnapshot.id.asc()).all()

    def _metric_history(
        self, db: Session, product_id: int, field: str, days: Optional[int]
    ) -> List[Dict[str, Any]]:
        return [
            {
                "value": getattr(snapshot, field),
                "observed_at": self._isoformat(snapshot.recorded_at),
                "source": snapshot.source,
                "confidence": snapshot.confidence,
            }
            for snapshot in self._get_snapshots(db, product_id, days)
            if getattr(snapshot, field) is not None
        ]

    @staticmethod
    def _price_metrics(snapshots: List[ProductSnapshot]) -> Dict[str, Any]:
        values = [snapshot.price for snapshot in snapshots if snapshot.price is not None]
        return {
            "current": values[-1] if values else None,
            "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
            "average": mean(values) if values else None,
            "change_pct": HistoryService._change_pct(values[0], values[-1]) if len(values) > 1 else None,
            "volatility": (pstdev(values) / mean(values)) * 100 if len(values) > 1 and mean(values) else None,
            "trend": classify_trend(values).value,
        }

    @staticmethod
    def _bsr_metrics(snapshots: List[ProductSnapshot]) -> Dict[str, Any]:
        values = [snapshot.bsr for snapshot in snapshots if snapshot.bsr is not None]
        current = values[-1] if values else None
        previous = values[-2] if len(values) > 1 else None
        absolute_change = current - previous if current is not None and previous is not None else None
        change_pct = HistoryService._change_pct(previous, current)
        return {
            "current": current,
            "previous": previous,
            "absolute_change": absolute_change,
            "change_pct": change_pct,
            "trend": classify_trend(values, lower_is_better=True).value,
            "improvement": absolute_change < 0 if absolute_change is not None else None,
        }

    @staticmethod
    def _review_metrics(snapshots: List[ProductSnapshot]) -> Dict[str, Any]:
        observed = [snapshot for snapshot in snapshots if snapshot.reviews is not None]
        values = [snapshot.reviews for snapshot in observed]
        gained = values[-1] - values[0] if len(values) > 1 else None
        elapsed_days = (
            (HistoryService._as_utc(observed[-1].recorded_at) - HistoryService._as_utc(observed[0].recorded_at)).total_seconds() / 86400
            if len(observed) > 1
            else 0
        )
        return {
            "current": values[-1] if values else None,
            "gained": gained,
            "velocity_per_day": gained / elapsed_days if gained is not None and elapsed_days > 0 else None,
            "growth_pct": HistoryService._change_pct(values[0], values[-1]) if len(values) > 1 else None,
            "trend": classify_trend(values).value,
        }

    @staticmethod
    def _score_metrics(snapshots: List[ProductSnapshot]) -> Dict[str, Any]:
        values = [snapshot.opportunity_score for snapshot in snapshots if snapshot.opportunity_score is not None]
        current = values[-1] if values else None
        previous = values[-2] if len(values) > 1 else None
        return {
            "current": current,
            "previous": previous,
            "change": current - previous if current is not None and previous is not None else None,
            "trend": classify_trend(values).value,
        }

    def _freshness(self, snapshot: Optional[ProductSnapshot]) -> Dict[str, Any]:
        if snapshot is None:
            return {"status": "Unavailable", "last_observed_at": None, "source": None, "age_seconds": None, "confidence": None}
        age_seconds = max(0, (datetime.now(timezone.utc) - self._as_utc(snapshot.recorded_at)).total_seconds())
        fresh_limit = self.settings.OBSERVATION_FRESH_HOURS * 3600
        stale_limit = self.settings.OBSERVATION_STALE_HOURS * 3600
        status = "Fresh" if age_seconds <= fresh_limit else "Aging" if age_seconds <= stale_limit else "Stale"
        return {
            "status": status,
            "last_observed_at": self._isoformat(snapshot.recorded_at),
            "source": snapshot.source,
            "age_seconds": round(age_seconds),
            "confidence": snapshot.confidence,
        }

    @staticmethod
    def _serialize_snapshot(snapshot: ProductSnapshot) -> Dict[str, Any]:
        return {
            "id": snapshot.id,
            "product_id": snapshot.product_id,
            "price": snapshot.price,
            "bsr": snapshot.bsr,
            "reviews": snapshot.reviews,
            "rating": snapshot.rating,
            "estimated_sales": snapshot.estimated_sales,
            "margin": snapshot.margin,
            "opportunity_score": snapshot.opportunity_score,
            "confidence": snapshot.confidence,
            "source": snapshot.source,
            "recorded_at": HistoryService._isoformat(snapshot.recorded_at),
        }

    @staticmethod
    def _change_pct(previous: Optional[float], current: Optional[float]) -> Optional[float]:
        if previous is None or current is None or previous == 0:
            return None
        return ((current - previous) / abs(previous)) * 100

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    @staticmethod
    def _isoformat(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None
