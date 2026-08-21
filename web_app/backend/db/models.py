"""Canonical application data models.

These models describe the target PostgreSQL-backed application data store.
Legacy SQLite tracking models remain in `web_app.backend.models.database`
until the tracking service is migrated.
"""
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, nullable=False, server_default="true")
    plan = Column(String(50), nullable=False, server_default="FREE")

    searches = relationship("Search", back_populates="user")
    watchlist_items = relationship("Watchlist", back_populates="user")
    tracked_products = relationship("TrackedProduct", back_populates="user")
    usage_events = relationship("UsageEvent", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("asin", "marketplace", name="uq_products_asin_marketplace"),
    )

    id = Column(Integer, primary_key=True)
    asin = Column(String(20), nullable=False, index=True)
    marketplace = Column(String(10), nullable=False, server_default="US", index=True)
    title = Column(String(1000), nullable=False)
    brand = Column(String(255), index=True)
    category = Column(String(255), index=True)
    image_url = Column(String(1000))
    product_url = Column(String(1000))
    source = Column(String(100), nullable=False, server_default="amazon_html")

    snapshots = relationship("ProductSnapshot", back_populates="product")
    search_results = relationship("SearchResult", back_populates="product")
    watchlist_items = relationship("Watchlist", back_populates="product")
    tracked_entries = relationship("TrackedProduct", back_populates="product")


class ProductSnapshot(Base):
    __tablename__ = "product_snapshots"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    source = Column(String(100), nullable=False, server_default="amazon_html")

    price = Column(Float)
    rating = Column(Float)
    reviews = Column(Integer)
    bsr = Column(Integer)
    seller_count = Column(Integer)
    estimated_sales = Column(Integer)
    estimated_revenue = Column(Float)
    estimated_profit = Column(Float)
    margin = Column(Float)
    opportunity_score = Column(Float)
    confidence = Column(Float)
    raw_data = Column(JSON)

    product = relationship("Product", back_populates="snapshots")


class Search(Base, TimestampMixin):
    __tablename__ = "searches"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    keyword = Column(String(255), nullable=False, index=True)
    marketplace = Column(String(10), nullable=False, server_default="US")
    filters = Column(JSON)
    status = Column(String(50), nullable=False, server_default="completed")

    user = relationship("User", back_populates="searches")
    results = relationship("SearchResult", back_populates="search")


class SearchResult(Base):
    __tablename__ = "search_results"
    __table_args__ = (
        UniqueConstraint("search_id", "product_id", name="uq_search_results_search_product"),
    )

    id = Column(Integer, primary_key=True)
    search_id = Column(Integer, ForeignKey("searches.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    product_snapshot_id = Column(Integer, ForeignKey("product_snapshots.id", ondelete="SET NULL"))
    rank = Column(Integer)
    score = Column(Float)
    recommendation = Column(String(255))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    search = relationship("Search", back_populates="results")
    product = relationship("Product", back_populates="search_results")
    product_snapshot = relationship("ProductSnapshot")


class Keyword(Base, TimestampMixin):
    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("keyword", "marketplace", name="uq_keywords_keyword_marketplace"),
    )

    id = Column(Integer, primary_key=True)
    keyword = Column(String(255), nullable=False, index=True)
    marketplace = Column(String(10), nullable=False, server_default="US")
    source = Column(String(100), nullable=False, server_default="amazon_autocomplete")

    snapshots = relationship("KeywordSnapshot", back_populates="keyword_ref")


class KeywordSnapshot(Base):
    __tablename__ = "keyword_snapshots"

    id = Column(Integer, primary_key=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    relevance = Column(Float)
    estimated_competition = Column(String(50))
    search_volume = Column(Integer)
    raw_data = Column(JSON)

    keyword_ref = relationship("Keyword", back_populates="snapshots")


class Watchlist(Base, TimestampMixin):
    __tablename__ = "watchlists"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_watchlists_user_product"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    notes = Column(Text)

    user = relationship("User", back_populates="watchlist_items")
    product = relationship("Product", back_populates="watchlist_items")


class TrackedProduct(Base, TimestampMixin):
    __tablename__ = "tracked_products"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_tracked_products_user_product"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    alert_settings = Column(JSON)
    last_checked_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="tracked_products")
    product = relationship("Product", back_populates="tracked_entries")
    alerts = relationship("Alert", back_populates="tracked_product")


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    tracked_product_id = Column(Integer, ForeignKey("tracked_products.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    old_value = Column(Float)
    new_value = Column(Float)
    change_pct = Column(Float)
    is_read = Column(Boolean, nullable=False, server_default="false")
    is_emailed = Column(Boolean, nullable=False, server_default="false")

    tracked_product = relationship("TrackedProduct", back_populates="alerts")


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    event_type = Column(String(100), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, server_default="1")
    metadata_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    user = relationship("User", back_populates="usage_events")


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("plan in ('FREE', 'STARTER', 'PRO')", name="ck_subscriptions_plan"),
        CheckConstraint("status in ('active', 'trialing', 'past_due', 'canceled')", name="ck_subscriptions_status"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan = Column(String(50), nullable=False, server_default="FREE")
    status = Column(String(50), nullable=False, server_default="active")
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    provider = Column(String(100))
    provider_subscription_id = Column(String(255), unique=True)

    user = relationship("User", back_populates="subscriptions")
