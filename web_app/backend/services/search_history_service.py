"""User-scoped read models for persisted search history."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from web_app.backend.db.models import Alert, Search, SearchResult, TrackedProduct


class SearchNotFoundError(RuntimeError):
    """Raised when a search does not belong to the requesting user."""


class SearchHistoryService:
    """Build search-history and dashboard contracts from canonical records."""

    def list_searches(
        self, db: Session, user_id: int, limit: int = 20, offset: int = 0
    ) -> Dict[str, Any]:
        query = db.query(Search).filter(Search.user_id == user_id)
        total = query.count()
        searches = query.order_by(Search.created_at.desc(), Search.id.desc()).offset(offset).limit(limit).all()
        return {
            "searches": [self._serialize_search(db, search) for search in searches],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_search(self, db: Session, user_id: int, search_id: int) -> Dict[str, Any]:
        return self._serialize_search(db, self._get_owned_search(db, user_id, search_id))

    def get_results(
        self, db: Session, user_id: int, search_id: int, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        self._get_owned_search(db, user_id, search_id)
        query = db.query(SearchResult).options(
            joinedload(SearchResult.product), joinedload(SearchResult.product_snapshot)
        ).filter(SearchResult.search_id == search_id)
        total = query.count()
        results = query.order_by(SearchResult.rank.asc(), SearchResult.id.asc()).offset(offset).limit(limit).all()
        return {
            "search_id": search_id,
            "results": [self._serialize_result(result) for result in results],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_dashboard(self, db: Session, user_id: int) -> Dict[str, Any]:
        recent = self.list_searches(db, user_id, limit=5)["searches"]
        tracked = db.query(TrackedProduct).filter(
            TrackedProduct.user_id == user_id, TrackedProduct.is_active.is_(True)
        ).count()
        alerts = db.query(Alert).join(TrackedProduct).filter(
            TrackedProduct.user_id == user_id, Alert.is_read.is_(False)
        ).count()
        strong_opportunities = db.query(SearchResult).join(Search).filter(
            Search.user_id == user_id, SearchResult.score >= 80
        ).count()
        return {
            "recent_searches": recent,
            "tracked_products": tracked,
            "unread_alerts": alerts,
            "strong_opportunities": strong_opportunities,
        }

    @staticmethod
    def _get_owned_search(db: Session, user_id: int, search_id: int) -> Search:
        search = db.query(Search).filter(
            Search.id == search_id, Search.user_id == user_id
        ).first()
        if search is None:
            raise SearchNotFoundError("Search not found")
        return search

    def _serialize_search(self, db: Session, search: Search) -> Dict[str, Any]:
        result_count = db.query(SearchResult).filter(SearchResult.search_id == search.id).count()
        return {
            "id": search.id,
            "keyword": search.keyword,
            "marketplace": search.marketplace,
            "filters": search.filters or {},
            "status": search.status,
            "result_count": result_count,
            "created_at": self._isoformat(search.created_at),
            "updated_at": self._isoformat(search.updated_at),
        }

    @staticmethod
    def _serialize_result(result: SearchResult) -> Dict[str, Any]:
        product = result.product
        snapshot = result.product_snapshot
        return {
            "id": result.id,
            "rank": result.rank,
            "score": result.score,
            "recommendation": result.recommendation,
            "product": {
                "asin": product.asin,
                "marketplace": product.marketplace,
                "title": product.title,
                "brand": product.brand,
                "category": product.category,
                "image_url": product.image_url,
                "product_url": product.product_url,
            },
            "snapshot": None if snapshot is None else {
                "price": snapshot.price,
                "rating": snapshot.rating,
                "reviews": snapshot.reviews,
                "bsr": snapshot.bsr,
                "seller_count": snapshot.seller_count,
                "estimated_sales": snapshot.estimated_sales,
                "estimated_revenue": snapshot.estimated_revenue,
                "estimated_profit": snapshot.estimated_profit,
                "margin": snapshot.margin,
                "opportunity_score": snapshot.opportunity_score,
                "confidence": snapshot.confidence,
                "source": snapshot.source,
                "recorded_at": SearchHistoryService._isoformat(snapshot.recorded_at),
            },
        }

    @staticmethod
    def _isoformat(value) -> Optional[str]:
        return value.isoformat() if value else None
