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
from scraper.amazon_scraper import AmazonScraper
from services.auth_service import AuthService
from services.canonical_tracking_service import CanonicalTrackingService
from services.llm_service import LLMService
from services.search_pipeline import SearchPipeline
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
    "scraper": AmazonScraper(),
    "scorer": EnhancedOpportunityScorer(),
    "fee_calc": FBAFeeCalculator(),
    "brand_checker": BrandRiskChecker(),
    "hazmat": HazmatDetector(),
    "keyword_tool": FreeKeywordTool(),
    "llm": LLMService(),
    "tracking": CanonicalTrackingService(),
    "auth": AuthService(),
}
tools["search_pipeline"] = SearchPipeline(
    scorer=tools["scorer"],
    profitability=ProfitabilityAnalyzer(tools["fee_calc"]),
    risk_analyzer=ProductRiskAnalyzer(tools["brand_checker"], tools["hazmat"]),
)
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


@app.post("/api/search")
async def search_products(request: SearchRequest):
    try:
        return await tools["search_pipeline"].run(request)
    except Exception as exc:
        logger.error("Search failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


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
        tracker = CanonicalTrackingService(scraper=tools["scraper"])
        return tracker.check_products(db, user)
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
