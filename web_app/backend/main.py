import logging
import os
import sys
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

# Add src path to system path to import existing modules.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
src_path = os.path.join(parent_dir, "src")
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, src_path)

from analysis.enhanced_scoring import EnhancedOpportunityScorer
from analysis.fba_calculator import FBAFeeCalculator
from analysis.keyword_tool import FreeKeywordTool
from analytics.profitability import ProfitabilityAnalyzer
from analytics.risk import ProductRiskAnalyzer
from config.settings import get_settings
from risk.brand_risk import BrandRiskChecker
from risk.hazmat_detector import HazmatDetector
from providers.amazon_html_provider import AmazonHTMLProvider
from web_app.backend.services.auth_service import AuthService
from web_app.backend.services.canonical_tracking_service import CanonicalTrackingService
from web_app.backend.services.llm_service import LLMService
from web_app.backend.services.search_pipeline import SearchPipeline
from web_app.backend.services.search_persistence_service import (
    SearchPersistenceError,
    SearchPersistenceService,
)
from web_app.backend.services.product_analyzer_service import (
    ProductAnalyzerService,
    ProductNotFoundError,
)
from web_app.backend.services.history_service import HistoryService
from web_app.backend.services.search_history_service import (
    SearchHistoryService,
    SearchNotFoundError,
)
from web_app.backend.services.usage_service import UsageService
from web_app.backend.services.plan_service import PlanService
from web_app.backend.services.market_intelligence_service import MarketIntelligenceService
from web_app.backend.db.models import User
from web_app.backend.db.session import get_db

settings = get_settings()
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("api")

app = FastAPI(title="Amazon Hunter API", version=settings.APP_VERSION)


def get_allowed_origins() -> List[str]:
    return settings.allowed_origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tools = {
    "product_provider": AmazonHTMLProvider(),
    "scorer": EnhancedOpportunityScorer(),
    "fee_calc": FBAFeeCalculator(),
    "brand_checker": BrandRiskChecker(),
    "hazmat": HazmatDetector(),
    "keyword_tool": FreeKeywordTool(),
    "llm": LLMService(),
    "auth": AuthService(),
    "usage": UsageService(),
    "plans": PlanService(),
    "market_intelligence": MarketIntelligenceService(),
}
tools["tracking"] = CanonicalTrackingService(provider=tools["product_provider"])
tools["history"] = HistoryService()
tools["search_pipeline"] = SearchPipeline(
    scorer=tools["scorer"],
    profitability=ProfitabilityAnalyzer(tools["fee_calc"]),
    risk_analyzer=ProductRiskAnalyzer(tools["brand_checker"], tools["hazmat"]),
    persistence_service=SearchPersistenceService(),
    history_service=tools["history"],
)
tools["product_analyzer"] = ProductAnalyzerService(
    provider=tools["product_provider"],
    pipeline=tools["search_pipeline"],
    history_service=tools["history"],
)
tools["search_history"] = SearchHistoryService()
bearer_scheme = HTTPBearer(auto_error=False)


class SearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=120)
    marketplace: Literal["US", "UK", "DE"] = "US"
    pages: int = Field(1, ge=1, le=5)
    min_rating: float = Field(3.0, ge=0, le=5)
    skip_risky_brands: bool = True
    skip_hazmat: bool = True
    skip_amazon_seller: bool = True
    skip_brand_seller: bool = True
    min_margin: float = Field(20.0, ge=-100, le=100)
    min_sales: int = Field(50, ge=0)
    max_sales: int = Field(1000, ge=0)
    fetch_seller_info: bool = True


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=12, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        local_part, separator, domain = normalized.partition("@")
        if not separator or not local_part or "." not in domain:
            raise ValueError("A valid email address is required")
        return normalized


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class TrackingAddRequest(BaseModel):
    asin: str
    product_data: Dict[str, Any]
    marketplace: str = "US"
    user_email: Optional[str] = None
    alert_settings: Optional[Dict[str, Any]] = None


class TrackingSettingsRequest(BaseModel):
    price_drop_pct: Optional[float] = None
    bsr_improve_pct: Optional[float] = None
    review_increase: Optional[int] = None
    user_email: Optional[str] = None
    notes: Optional[str] = None


def serialize_user(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "plan": user.plan,
    }


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return tools["auth"].get_user_from_token(db, credentials.credentials)


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Resolve a supplied bearer token without requiring one for public search."""
    if credentials is None:
        return None
    return tools["auth"].get_user_from_token(db, credentials.credentials)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    user = tools["auth"].register_user(
        db=db,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
    )
    return {
        "access_token": tools["auth"].create_access_token(user),
        "token_type": "bearer",
        "user": serialize_user(user),
    }


@app.post("/api/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = tools["auth"].authenticate(db, request.email, request.password)
    return {
        "access_token": tools["auth"].create_access_token(user),
        "token_type": "bearer",
        "user": serialize_user(user),
    }


@app.get("/api/auth/me")
async def current_user(user: User = Depends(get_current_user)):
    return {"user": serialize_user(user)}


@app.get("/api/account")
async def get_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"user": serialize_user(user), "usage": tools["usage"].summary(db, user.id), "limits": tools["plans"].limits_for(user.plan)}


@app.post("/api/search")
async def search_products(
    request: SearchRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    try:
        response = await tools["search_pipeline"].run(
            request,
            db=db,
            user_id=user.id if user is not None else None,
        )
        tools["usage"].record(db, "search", user.id if user else None, {"marketplace": request.marketplace})
        return response
    except SearchPersistenceError as exc:
        logger.error("Search persistence failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to save search results")
    except Exception:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail="Search failed")


@app.get("/api/products/{asin}")
async def get_product_analysis(
    asin: str,
    marketplace: Literal["US", "UK", "DE"] = "US",
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    try:
        response = await tools["product_analyzer"].analyze(db, asin, marketplace)
        tools["usage"].record(
            db,
            "product_analysis",
            user.id if user else None,
            {"asin": asin, "marketplace": marketplace},
        )
        return response
    except ProductNotFoundError:
        raise HTTPException(status_code=404, detail="Product not found")
    except Exception:
        db.rollback()
        logger.exception("Product analysis failed for %s", asin)
        raise HTTPException(status_code=500, detail="Product analysis failed")


@app.get("/api/products/{asin}/history")
async def get_product_history(
    asin: str,
    marketplace: Literal["US", "UK", "DE"] = "US",
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    try:
        return tools["product_analyzer"].get_history(db, asin, marketplace, days)
    except ProductNotFoundError:
        raise HTTPException(status_code=404, detail="Product not found")
    except Exception:
        logger.exception("Product history failed for %s", asin)
        raise HTTPException(status_code=500, detail="Product history failed")


@app.get("/api/market/categories")
async def get_market_categories(db: Session = Depends(get_db)):
    return {"categories": tools["market_intelligence"].list_categories(db)}


@app.get("/api/market/categories/{category}")
async def get_market_category(category: str, db: Session = Depends(get_db)):
    return tools["market_intelligence"].category_summary(db, category)


@app.get("/api/search/history")
async def get_search_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return tools["search_history"].list_searches(db, user.id, limit, offset)


@app.get("/api/search/{search_id}")
async def get_search_detail(
    search_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return tools["search_history"].get_search(db, user.id, search_id)
    except SearchNotFoundError:
        raise HTTPException(status_code=404, detail="Search not found")


@app.get("/api/search/{search_id}/results")
async def get_search_results(
    search_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return tools["search_history"].get_results(db, user.id, search_id, limit, offset)
    except SearchNotFoundError:
        raise HTTPException(status_code=404, detail="Search not found")


@app.get("/api/dashboard")
async def get_dashboard_data(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return tools["search_history"].get_dashboard(db, user.id)


@app.get("/api/keywords")
async def get_keywords(q: str):
    try:
        suggestions = tools["keyword_tool"].get_autocomplete_suggestions(q)
        return {
            "keyword": q,
            "suggestions": [
                {
                    "keyword": suggestion.keyword,
                    "source": suggestion.source,
                    "relevance": suggestion.relevance_score,
                }
                for suggestion in suggestions
            ],
        }
    except Exception as exc:
        logger.error("Keyword search failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    try:
        response = await tools["llm"].get_chat_response(request.messages)
        return {"response": response}
    except Exception as exc:
        logger.error("Chat failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/tracking/products")
async def get_tracked_products(
    active_only: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        products = tools["tracking"].get_tracked_products(db, user, active_only=active_only)
        return {"products": products}
    except Exception as exc:
        logger.error("Failed to fetch tracked products: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/tracking/add")
async def add_tracked_product(
    request: TrackingAddRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        product = tools["tracking"].add_product(
            db=db,
            user=user,
            asin=request.asin,
            product_data=request.product_data,
            marketplace=request.marketplace,
            alert_settings=request.alert_settings,
        )
        tools["usage"].record(db, "tracking_add", user.id, {"asin": request.asin})
        return {"success": True, "product": product}
    except Exception as exc:
        logger.error(
            "Failed to add tracked product %s: %s",
            request.asin,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/api/tracking/{asin}")
async def remove_tracked_product(
    asin: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        removed = tools["tracking"].remove_product(db, user, asin)
        if not removed:
            raise HTTPException(status_code=404, detail="Tracked product not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to remove tracked product %s: %s", asin, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/tracking/{asin}/history")
async def get_tracking_history(
    asin: str,
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        history = tools["tracking"].get_product_history(db, user, asin, days=days)
        return {"asin": asin, "history": history}
    except Exception as exc:
        logger.error(
            "Failed to fetch tracking history for %s: %s",
            asin,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc))


@app.put("/api/tracking/{asin}/settings")
async def update_tracking_settings(
    asin: str,
    request: TrackingSettingsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        alert_settings = request.model_dump(exclude_none=True)
        updated = tools["tracking"].update_alert_settings(db, user, asin, alert_settings)
        if not updated:
            raise HTTPException(status_code=404, detail="Tracked product not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to update tracking settings for %s: %s",
            asin,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/tracking/alerts")
async def get_tracking_alerts(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        alerts = tools["tracking"].get_alerts(
            db, user, unread_only=unread_only, limit=limit
        )
        return {"alerts": alerts}
    except Exception as exc:
        logger.error("Failed to fetch tracking alerts: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/tracking/alerts/read")
async def mark_tracking_alerts_read(
    alert_ids: List[int],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        updated = tools["tracking"].mark_alerts_read(db, user, alert_ids)
        return {"success": True, "updated": updated}
    except Exception as exc:
        logger.error("Failed to mark alerts read: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/tracking/check")
async def check_tracked_products(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return await tools["tracking"].check_products(db, user)
    except Exception as exc:
        logger.error("Failed to check tracked products: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/tracking/stats")
async def get_tracking_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return tools["tracking"].get_tracking_stats(db, user)
    except Exception as exc:
        logger.error("Failed to fetch tracking stats: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
