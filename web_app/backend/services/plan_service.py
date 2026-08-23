"""Plan definitions and limit lookup, intentionally independent of routes."""
from __future__ import annotations

from typing import Dict, Optional


DEFAULT_PLAN_LIMITS: Dict[str, Dict[str, Optional[int]]] = {
    "FREE": {"search": None, "product_analysis": None, "keyword_search": None, "tracking_add": 25, "export": None},
    "STARTER": {"search": None, "product_analysis": None, "keyword_search": None, "tracking_add": 100, "export": None},
    "PRO": {"search": None, "product_analysis": None, "keyword_search": None, "tracking_add": None, "export": None},
}


class PlanService:
    def limits_for(self, plan: str) -> Dict[str, Optional[int]]:
        return DEFAULT_PLAN_LIMITS.get((plan or "FREE").upper(), DEFAULT_PLAN_LIMITS["FREE"]).copy()
