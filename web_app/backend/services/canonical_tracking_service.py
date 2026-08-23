"""User-owned tracking backed by the canonical application database."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from providers.base import ProductDataProvider
from web_app.backend.db.models import Alert, Product, ProductSnapshot, TrackedProduct, User
from web_app.backend.services.history_service import HistoryService

DEFAULT_ALERT_SETTINGS = {
    "price_drop_pct": 5.0,
    "bsr_improve_pct": 10.0,
    "review_increase": 50,
}


class CanonicalTrackingService:
    """Manage product tracking data for a single authenticated user."""

    def __init__(
        self,
        provider: Optional[ProductDataProvider] = None,
        history_service: Optional[HistoryService] = None,
    ):
        self.provider = provider
        self.history_service = history_service or HistoryService()

    def add_product(self, db: Session, user: User, asin: str,
                    product_data: Dict[str, Any], marketplace: str = "US",
                    alert_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        product = self._get_or_create_product(db, asin, marketplace, product_data)
        tracked = self._find_tracked(db, user.id, product.id)
        if tracked:
            if not tracked.is_active:
                tracked.is_active = True
                tracked.last_checked_at = datetime.now(timezone.utc)
                db.commit()
            return self._serialize_tracked(db, tracked)

        tracked = TrackedProduct(
            user_id=user.id,
            product_id=product.id,
            is_active=True,
            alert_settings=self._merge_settings(alert_settings),
        )
        db.add(tracked)
        db.flush()
        self._record_snapshot(db, product, product_data)
        db.commit()
        db.refresh(tracked)
        return self._serialize_tracked(db, tracked)

    def remove_product(self, db: Session, user: User, asin: str) -> bool:
        tracked = self._find_user_asin(db, user.id, asin)
        if not tracked:
            return False
        tracked.is_active = False
        db.commit()
        return True

    def get_tracked_products(self, db: Session, user: User,
                             active_only: bool = True) -> List[Dict[str, Any]]:
        query = db.query(TrackedProduct).filter(TrackedProduct.user_id == user.id)
        if active_only:
            query = query.filter(TrackedProduct.is_active.is_(True))
        return [
            self._serialize_tracked(db, tracked)
            for tracked in query.order_by(TrackedProduct.created_at.desc()).all()
        ]

    def get_product_history(self, db: Session, user: User, asin: str,
                            days: int = 30) -> List[Dict[str, Any]]:
        tracked = self._find_user_asin(db, user.id, asin)
        if not tracked:
            return []
        return self.history_service.get_product_timeline(
            db, tracked.product_id, days=days
        )

    def get_alerts(self, db: Session, user: User, unread_only: bool = False,
                   limit: int = 50) -> List[Dict[str, Any]]:
        query = db.query(Alert).join(TrackedProduct).filter(
            TrackedProduct.user_id == user.id
        )
        if unread_only:
            query = query.filter(Alert.is_read.is_(False))
        return [
            self._serialize_alert(alert)
            for alert in query.order_by(Alert.created_at.desc()).limit(limit).all()
        ]

    def mark_alerts_read(self, db: Session, user: User, alert_ids: List[int]) -> int:
        if not alert_ids:
            return 0
        alerts = (
            db.query(Alert)
            .join(TrackedProduct)
            .filter(
                TrackedProduct.user_id == user.id,
                Alert.id.in_(alert_ids),
            )
            .all()
        )
        for alert in alerts:
            alert.is_read = True
        db.commit()
        return len(alerts)

    def update_alert_settings(self, db: Session, user: User, asin: str,
                              settings: Dict[str, Any]) -> bool:
        tracked = self._find_user_asin(db, user.id, asin)
        if not tracked:
            return False
        tracked.alert_settings = self._merge_settings(
            settings, existing=tracked.alert_settings
        )
        db.commit()
        return True

    def get_tracking_stats(self, db: Session, user: User) -> Dict[str, int]:
        total = db.query(TrackedProduct).filter(TrackedProduct.user_id == user.id).count()
        active = db.query(TrackedProduct).filter(
            TrackedProduct.user_id == user.id,
            TrackedProduct.is_active.is_(True),
        ).count()
        unread_alerts = db.query(Alert).join(TrackedProduct).filter(
            TrackedProduct.user_id == user.id,
            Alert.is_read.is_(False),
        ).count()
        return {
            "total_products": total,
            "active_products": active,
            "unread_alerts": unread_alerts,
        }

    async def check_products(self, db: Session, user: User) -> Dict[str, int]:
        if not self.provider:
            raise ValueError("Product provider not configured for tracking service")

        results = {"checked": 0, "updated": 0, "alerts_generated": 0, "errors": 0}
        tracked_products = db.query(TrackedProduct).filter(
            TrackedProduct.user_id == user.id,
            TrackedProduct.is_active.is_(True),
        ).all()
        for tracked in tracked_products:
            try:
                current_data = await self.provider.get_product(tracked.product.asin)
                if not current_data:
                    continue
                previous = self._latest_snapshot(db, tracked.product_id)
                self._update_product(tracked.product, current_data)
                self._record_snapshot(db, tracked.product, current_data)
                tracked.last_checked_at = datetime.now(timezone.utc)
                results["checked"] += 1
                results["updated"] += 1
                results["alerts_generated"] += self._create_alerts(
                    db, tracked, previous, current_data
                )
            except Exception:
                results["errors"] += 1
        db.commit()
        return results

    def _get_or_create_product(self, db: Session, asin: str, marketplace: str,
                               product_data: Dict[str, Any]) -> Product:
        asin = asin.strip().upper()
        marketplace = marketplace.strip().upper()
        product = db.query(Product).filter(
            Product.asin == asin,
            Product.marketplace == marketplace,
        ).first()
        if product:
            self._update_product(product, product_data)
            return product
        product = Product(
            asin=asin,
            marketplace=marketplace,
            title=product_data.get("title") or asin,
            brand=product_data.get("brand"),
            category=product_data.get("category"),
            image_url=product_data.get("image_url"),
            product_url=product_data.get("url") or product_data.get("product_url"),
        )
        db.add(product)
        db.flush()
        return product

    @staticmethod
    def _update_product(product: Product, data: Dict[str, Any]) -> None:
        fields = {
            "title": data.get("title"),
            "brand": data.get("brand"),
            "category": data.get("category"),
            "image_url": data.get("image_url"),
            "product_url": data.get("url") or data.get("product_url"),
        }
        for field, value in fields.items():
            if value:
                setattr(product, field, value)

    @staticmethod
    def _record_snapshot(db: Session, product: Product,
                         data: Dict[str, Any]) -> ProductSnapshot:
        seller_info = data.get("seller_info") or {}
        snapshot = ProductSnapshot(
            product_id=product.id,
            source=data.get("source") or "amazon_html",
            price=data.get("price"),
            rating=data.get("rating"),
            reviews=data.get("reviews"),
            bsr=data.get("bsr"),
            seller_count=seller_info.get("total_sellers"),
            estimated_sales=data.get("estimated_sales"),
            estimated_revenue=data.get("est_revenue"),
            estimated_profit=data.get("est_profit"),
            margin=data.get("margin"),
            opportunity_score=data.get("enhanced_score"),
            confidence=data.get("confidence") or data.get("_search_confidence"),
            raw_data=data,
        )
        db.add(snapshot)
        db.flush()
        return snapshot

    @staticmethod
    def _find_tracked(db: Session, user_id: int,
                      product_id: int) -> Optional[TrackedProduct]:
        return db.query(TrackedProduct).filter(
            TrackedProduct.user_id == user_id,
            TrackedProduct.product_id == product_id,
        ).first()

    def _find_user_asin(self, db: Session, user_id: int,
                        asin: str) -> Optional[TrackedProduct]:
        return db.query(TrackedProduct).join(Product).filter(
            TrackedProduct.user_id == user_id,
            Product.asin == asin.strip().upper(),
        ).first()

    @staticmethod
    def _latest_snapshot(db: Session, product_id: int) -> Optional[ProductSnapshot]:
        return db.query(ProductSnapshot).filter(
            ProductSnapshot.product_id == product_id
        ).order_by(
            ProductSnapshot.recorded_at.desc(), ProductSnapshot.id.desc()
        ).first()

    @staticmethod
    def _merge_settings(settings: Optional[Dict[str, Any]],
                        existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        merged = {**DEFAULT_ALERT_SETTINGS, **(existing or {})}
        for key in (*DEFAULT_ALERT_SETTINGS, "notes"):
            if settings and key in settings:
                merged[key] = settings[key]
        return merged

    def _serialize_tracked(self, db: Session,
                           tracked: TrackedProduct) -> Dict[str, Any]:
        latest = self._latest_snapshot(db, tracked.product_id)
        initial = db.query(ProductSnapshot).filter(
            ProductSnapshot.product_id == tracked.product_id
        ).order_by(
            ProductSnapshot.recorded_at.asc(), ProductSnapshot.id.asc()
        ).first()
        settings = self._merge_settings(None, tracked.alert_settings)
        check_count = db.query(ProductSnapshot).filter(
            ProductSnapshot.product_id == tracked.product_id
        ).count()
        intelligence = self.history_service.get_product_intelligence(
            db, tracked.product_id
        )
        return {
            "id": tracked.id,
            "asin": tracked.product.asin,
            "title": tracked.product.title,
            "image_url": tracked.product.image_url,
            "current_price": latest.price if latest else None,
            "current_bsr": latest.bsr if latest else None,
            "current_reviews": latest.reviews if latest else None,
            "current_rating": latest.rating if latest else None,
            "current_opportunity_score": latest.opportunity_score if latest else None,
            "initial_price": initial.price if initial else None,
            "initial_bsr": initial.bsr if initial else None,
            "initial_reviews": initial.reviews if initial else None,
            "marketplace": tracked.product.marketplace,
            "created_at": self._isoformat(tracked.created_at),
            "last_checked": self._isoformat(tracked.last_checked_at),
            "check_count": check_count,
            "is_active": tracked.is_active,
            "alert_settings": {
                "price_drop_pct": settings["price_drop_pct"],
                "bsr_improve_pct": settings["bsr_improve_pct"],
                "review_increase": settings["review_increase"],
            },
            "user_email": tracked.user.email,
            "notes": settings.get("notes"),
            "price_change_pct": self._calculate_change(
                initial.price if initial else None, latest.price if latest else None
            ),
            "bsr_change_pct": self._calculate_change(
                initial.bsr if initial else None,
                latest.bsr if latest else None,
                invert=True,
            ),
            "review_change": (
                (latest.reviews or 0) - (initial.reviews or 0)
                if latest and initial else 0
            ),
            "score_change": intelligence["opportunity_score"]["change"],
            "trends": {
                "price": intelligence["price"]["trend"],
                "bsr": intelligence["bsr"]["trend"],
                "reviews": intelligence["reviews"]["trend"],
                "opportunity_score": intelligence["opportunity_score"]["trend"],
            },
            "data_quality": intelligence["freshness"],
        }

    def _create_alerts(self, db: Session, tracked: TrackedProduct,
                       previous: Optional[ProductSnapshot],
                       current_data: Dict[str, Any]) -> int:
        if not previous:
            return 0
        settings = self._merge_settings(None, tracked.alert_settings)
        specs = []
        price = current_data.get("price")
        if previous.price and price:
            change = ((previous.price - price) / previous.price) * 100
            if change >= settings["price_drop_pct"]:
                specs.append((
                    "price_drop",
                    "Price dropped {:.1f}% from ${:.2f} to ${:.2f}".format(
                        change, previous.price, price
                    ),
                    previous.price, price, change,
                ))
        bsr = current_data.get("bsr")
        if previous.bsr and bsr:
            change = ((previous.bsr - bsr) / previous.bsr) * 100
            if change >= settings["bsr_improve_pct"]:
                specs.append((
                    "bsr_improve",
                    f"BSR improved {change:.1f}% from #{previous.bsr:,} to #{bsr:,}",
                    previous.bsr, bsr, change,
                ))
        reviews = current_data.get("reviews")
        if previous.reviews and reviews:
            increase = reviews - previous.reviews
            if increase >= settings["review_increase"]:
                specs.append((
                    "review_increase",
                    f"Reviews increased by {increase} from {previous.reviews:,} to {reviews:,}",
                    previous.reviews, reviews,
                    (increase / previous.reviews) * 100,
                ))
        for alert_type, message, old_value, new_value, change_pct in specs:
            db.add(Alert(
                tracked_product_id=tracked.id,
                alert_type=alert_type,
                message=message,
                old_value=old_value,
                new_value=new_value,
                change_pct=change_pct,
            ))
        return len(specs)

    @staticmethod
    def _serialize_snapshot(snapshot: ProductSnapshot) -> Dict[str, Any]:
        return {
            "id": snapshot.id,
            "product_id": snapshot.product_id,
            "price": snapshot.price,
            "bsr": snapshot.bsr,
            "reviews": snapshot.reviews,
            "rating": snapshot.rating,
            "recorded_at": CanonicalTrackingService._isoformat(snapshot.recorded_at),
        }

    @staticmethod
    def _serialize_alert(alert: Alert) -> Dict[str, Any]:
        product = alert.tracked_product.product
        return {
            "id": alert.id,
            "product_id": alert.tracked_product_id,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "old_value": alert.old_value,
            "new_value": alert.new_value,
            "change_pct": alert.change_pct,
            "created_at": CanonicalTrackingService._isoformat(alert.created_at),
            "is_read": alert.is_read,
            "is_emailed": alert.is_emailed,
            "product": {"asin": product.asin, "title": product.title},
        }

    @staticmethod
    def _calculate_change(initial, current, invert: bool = False) -> float:
        if not initial or not current:
            return 0
        change = ((current - initial) / initial) * 100
        return -change if invert else change

    @staticmethod
    def _isoformat(value) -> Optional[str]:
        return value.isoformat() if value else None
