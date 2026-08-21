"""Import legacy SQLite tracking data into the canonical application database.

Run this only after applying the Alembic migrations. The importer creates a
disabled legacy owner account by default, making imported records auditable
without granting anyone automatic access.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "web_app" / "backend"))

from web_app.backend.db.models import Alert, Product, ProductSnapshot, TrackedProduct, User
from web_app.backend.db.session import SessionLocal
from web_app.backend.services.auth_service import AuthService
from web_app.backend.models.database import (
    ProductAlert as LegacyAlert,
    ProductHistory as LegacyHistory,
    TrackedProduct as LegacyTrackedProduct,
    get_session as get_legacy_session,
)

DEFAULT_OWNER_EMAIL = "legacy-tracking@local.invalid"


def get_or_create_owner(db, email: str) -> User:
    owner = db.query(User).filter(User.email == email).first()
    if owner:
        return owner

    owner = User(
        email=email,
        full_name="Legacy Tracking Import",
        password_hash=AuthService.hash_password("legacy-import-account-disabled"),
        is_active=False,
    )
    db.add(owner)
    db.flush()
    return owner


def upsert_product(db, legacy_product: LegacyTrackedProduct) -> Product:
    product = db.query(Product).filter(
        Product.asin == legacy_product.asin,
        Product.marketplace == (legacy_product.marketplace or "US"),
    ).first()
    if product:
        return product

    product = Product(
        asin=legacy_product.asin,
        marketplace=legacy_product.marketplace or "US",
        title=legacy_product.title or legacy_product.asin,
        image_url=legacy_product.image_url,
        source="legacy_tracking_import",
    )
    db.add(product)
    db.flush()
    return product


def import_tracking(owner_email: str) -> Dict[str, int]:
    legacy_db = get_legacy_session()
    canonical_db = SessionLocal()
    counts = {"products": 0, "snapshots": 0, "alerts": 0}

    try:
        owner = get_or_create_owner(canonical_db, owner_email)
        tracking_by_legacy_id: Dict[int, Tuple[TrackedProduct, Product]] = {}

        for legacy in legacy_db.query(LegacyTrackedProduct).all():
            product = upsert_product(canonical_db, legacy)
            tracked = canonical_db.query(TrackedProduct).filter(
                TrackedProduct.user_id == owner.id,
                TrackedProduct.product_id == product.id,
            ).first()
            if not tracked:
                tracked = TrackedProduct(
                    user_id=owner.id,
                    product_id=product.id,
                    is_active=legacy.is_active,
                    alert_settings={
                        "price_drop_pct": legacy.alert_on_price_drop_pct,
                        "bsr_improve_pct": legacy.alert_on_bsr_improve_pct,
                        "review_increase": legacy.alert_on_review_increase,
                        "notes": legacy.notes,
                    },
                    last_checked_at=legacy.last_checked,
                    created_at=legacy.created_at,
                )
                canonical_db.add(tracked)
                canonical_db.flush()
                counts["products"] += 1
            tracking_by_legacy_id[legacy.id] = (tracked, product)

            histories = legacy_db.query(LegacyHistory).filter(
                LegacyHistory.product_id == legacy.id
            ).all()
            if not histories:
                histories = [
                    LegacyHistory(
                        price=legacy.current_price,
                        bsr=legacy.current_bsr,
                        reviews=legacy.current_reviews,
                        rating=legacy.current_rating,
                        recorded_at=legacy.last_checked or legacy.created_at,
                    )
                ]

            for history in histories:
                exists = canonical_db.query(ProductSnapshot).filter(
                    ProductSnapshot.product_id == product.id,
                    ProductSnapshot.recorded_at == history.recorded_at,
                    ProductSnapshot.source == "legacy_tracking_import",
                ).first()
                if exists:
                    continue
                canonical_db.add(ProductSnapshot(
                    product_id=product.id,
                    recorded_at=history.recorded_at,
                    source="legacy_tracking_import",
                    price=history.price,
                    bsr=history.bsr,
                    reviews=history.reviews,
                    rating=history.rating,
                ))
                counts["snapshots"] += 1

        for legacy_alert in legacy_db.query(LegacyAlert).all():
            tracked_pair = tracking_by_legacy_id.get(legacy_alert.product_id)
            if not tracked_pair:
                continue
            tracked, _ = tracked_pair
            exists = canonical_db.query(Alert).filter(
                Alert.tracked_product_id == tracked.id,
                Alert.alert_type == legacy_alert.alert_type,
                Alert.message == legacy_alert.message,
                Alert.created_at == legacy_alert.created_at,
            ).first()
            if exists:
                continue
            canonical_db.add(Alert(
                tracked_product_id=tracked.id,
                alert_type=legacy_alert.alert_type,
                message=legacy_alert.message or "Legacy tracking alert",
                old_value=legacy_alert.old_value,
                new_value=legacy_alert.new_value,
                change_pct=legacy_alert.change_pct,
                is_read=legacy_alert.is_read,
                is_emailed=legacy_alert.is_emailed,
                created_at=legacy_alert.created_at,
            ))
            counts["alerts"] += 1

        canonical_db.commit()
        return counts
    except Exception:
        canonical_db.rollback()
        raise
    finally:
        legacy_db.close()
        canonical_db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-email", default=DEFAULT_OWNER_EMAIL)
    args = parser.parse_args()
    counts = import_tracking(args.owner_email.strip().lower())
    print(
        "Imported {products} tracked products, {snapshots} snapshots, and "
        "{alerts} alerts.".format(**counts)
    )


if __name__ == "__main__":
    main()
