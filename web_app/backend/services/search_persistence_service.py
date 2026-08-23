"""Persistence for analyzed search results.

This service owns canonical database writes. Providers, scrapers, and analytics
remain independent of SQLAlchemy persistence.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from web_app.backend.db.models import Product, ProductSnapshot, Search, SearchResult

logger = logging.getLogger(__name__)


class SearchPersistenceError(RuntimeError):
    """Raised when a complete search result cannot be persisted."""


class SearchPersistenceService:
    """Persist canonical products, observations, searches, and search results."""

    PRODUCT_SOURCE = "amazon_html"

    def persist(
        self,
        db: Session,
        request,
        products: Iterable[Dict[str, Any]],
        user_id: Optional[int] = None,
    ) -> Search:
        """Persist a completed search in one transaction.

        The supplied products must already be normalized and analyzed by the
        search pipeline. No provider or analytics work occurs in this service.
        """
        try:
            search = Search(
                user_id=user_id,
                keyword=request.keyword,
                marketplace=request.marketplace,
                filters=self._filters_from_request(request),
                status="completed",
            )
            db.add(search)
            db.flush()

            persisted_product_ids = set()
            result_rank = 0
            for result in products:
                product = self._upsert_product(db, result, request.marketplace)
                if product.id in persisted_product_ids:
                    logger.warning(
                        "Skipping duplicate product %s in search %s",
                        product.asin,
                        search.id,
                    )
                    continue

                snapshot = self._create_snapshot(db, product, result)
                result_rank += 1
                db.add(
                    SearchResult(
                        search_id=search.id,
                        product_id=product.id,
                        product_snapshot_id=snapshot.id,
                        rank=result_rank,
                        score=self._float_or_none(result.get("enhanced_score")),
                        recommendation=result.get("_search_recommendation"),
                    )
                )
                persisted_product_ids.add(product.id)

            db.commit()
            return search
        except (SQLAlchemyError, ValueError, TypeError) as exc:
            db.rollback()
            logger.exception(
                "Search persistence failed for keyword '%s'",
                getattr(request, "keyword", "<unknown>"),
            )
            raise SearchPersistenceError("Unable to save search results") from exc
        except Exception as exc:
            db.rollback()
            logger.exception(
                "Unexpected search persistence failure for keyword '%s'",
                getattr(request, "keyword", "<unknown>"),
            )
            raise SearchPersistenceError("Unable to save search results") from exc

    def create_observation(
        self, db: Session, result: Dict[str, Any], marketplace: str
    ) -> tuple[Product, ProductSnapshot]:
        """Stage one canonical product observation in the caller transaction."""
        product = self._upsert_product(db, result, marketplace)
        snapshot = self._create_snapshot(db, product, result)
        return product, snapshot

    def _upsert_product(
        self, db: Session, result: Dict[str, Any], marketplace: str
    ) -> Product:
        asin = str(result.get("asin") or "").strip().upper()
        if not asin:
            raise ValueError("Search result is missing an ASIN")

        normalized_marketplace = marketplace.strip().upper()
        product = (
            db.query(Product)
            .filter(
                Product.asin == asin,
                Product.marketplace == normalized_marketplace,
            )
            .first()
        )
        if product is None:
            product = Product(
                asin=asin,
                marketplace=normalized_marketplace,
                title=result.get("title") or asin,
                brand=result.get("brand") or None,
                category=result.get("category") or None,
                image_url=result.get("image_url") or None,
                product_url=result.get("url") or result.get("product_url") or None,
                source=self.PRODUCT_SOURCE,
            )
            db.add(product)
            db.flush()
            return product

        self._update_stable_product_fields(product, result)
        return product

    @staticmethod
    def _update_stable_product_fields(
        product: Product, result: Dict[str, Any]
    ) -> None:
        fields = {
            "title": result.get("title"),
            "brand": result.get("brand"),
            "category": result.get("category"),
            "image_url": result.get("image_url"),
            "product_url": result.get("url") or result.get("product_url"),
        }
        for field, value in fields.items():
            if value:
                setattr(product, field, value)

    def _create_snapshot(
        self, db: Session, product: Product, result: Dict[str, Any]
    ) -> ProductSnapshot:
        seller_info = result.get("seller_info") or {}
        raw_data = {
            key: value
            for key, value in result.items()
            if not key.startswith("_search_")
        }
        snapshot = ProductSnapshot(
            product_id=product.id,
            source=self.PRODUCT_SOURCE,
            price=self._float_or_none(result.get("price")),
            rating=self._float_or_none(result.get("rating")),
            reviews=self._int_or_none(result.get("reviews")),
            bsr=self._int_or_none(result.get("bsr")),
            seller_count=self._int_or_none(seller_info.get("total_sellers")),
            estimated_sales=self._int_or_none(result.get("estimated_sales")),
            estimated_revenue=self._float_or_none(result.get("est_revenue")),
            estimated_profit=self._float_or_none(result.get("est_profit")),
            margin=self._float_or_none(result.get("margin")),
            opportunity_score=self._float_or_none(result.get("enhanced_score")),
            confidence=self._float_or_none(result.get("_search_confidence")),
            raw_data=raw_data,
        )
        db.add(snapshot)
        db.flush()
        return snapshot

    @staticmethod
    def _filters_from_request(request) -> Dict[str, Any]:
        if hasattr(request, "model_dump"):
            return request.model_dump()
        return {
            key: value
            for key, value in vars(request).items()
            if not key.startswith("_")
        }

    @staticmethod
    def _float_or_none(value: Any) -> Optional[float]:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int_or_none(value: Any) -> Optional[int]:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None
