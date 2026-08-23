"""Centralized usage-event recording and account usage summaries."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from web_app.backend.db.models import UsageEvent


class UsageService:
    def record(self, db: Session, event_type: str, user_id: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        db.add(UsageEvent(user_id=user_id, event_type=event_type, metadata_json=metadata or {}))
        db.commit()

    def summary(self, db: Session, user_id: int) -> Dict[str, int]:
        rows = db.query(UsageEvent.event_type).filter(UsageEvent.user_id == user_id).all()
        counts = Counter(event_type for (event_type,) in rows)
        return {event_type: counts.get(event_type, 0) for event_type in (
            "search", "product_analysis", "keyword_search", "export", "tracking_add"
        )}
