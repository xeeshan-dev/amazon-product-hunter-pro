"""create canonical application tables

Revision ID: 20260821_0001
Revises:
Create Date: 2026-08-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260821_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("plan", sa.String(length=50), server_default="FREE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asin", sa.String(length=20), nullable=False),
        sa.Column("marketplace", sa.String(length=10), server_default="US", nullable=False),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("image_url", sa.String(length=1000), nullable=True),
        sa.Column("product_url", sa.String(length=1000), nullable=True),
        sa.Column("source", sa.String(length=100), server_default="amazon_html", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("asin", "marketplace", name="uq_products_asin_marketplace"),
    )
    op.create_index("ix_products_asin", "products", ["asin"])
    op.create_index("ix_products_brand", "products", ["brand"])
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_marketplace", "products", ["marketplace"])

    op.create_table(
        "keywords",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("marketplace", sa.String(length=10), server_default="US", nullable=False),
        sa.Column("source", sa.String(length=100), server_default="amazon_autocomplete", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("keyword", "marketplace", name="uq_keywords_keyword_marketplace"),
    )
    op.create_index("ix_keywords_keyword", "keywords", ["keyword"])

    op.create_table(
        "searches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("marketplace", sa.String(length=10), server_default="US", nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="completed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_searches_keyword", "searches", ["keyword"])
    op.create_index("ix_searches_user_id", "searches", ["user_id"])

    op.create_table(
        "product_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("source", sa.String(length=100), server_default="amazon_html", nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("reviews", sa.Integer(), nullable=True),
        sa.Column("bsr", sa.Integer(), nullable=True),
        sa.Column("seller_count", sa.Integer(), nullable=True),
        sa.Column("estimated_sales", sa.Integer(), nullable=True),
        sa.Column("estimated_revenue", sa.Float(), nullable=True),
        sa.Column("estimated_profit", sa.Float(), nullable=True),
        sa.Column("margin", sa.Float(), nullable=True),
        sa.Column("opportunity_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
    )
    op.create_index("ix_product_snapshots_product_id", "product_snapshots", ["product_id"])
    op.create_index("ix_product_snapshots_recorded_at", "product_snapshots", ["recorded_at"])

    op.create_table(
        "keyword_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("keyword_id", sa.Integer(), sa.ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("relevance", sa.Float(), nullable=True),
        sa.Column("estimated_competition", sa.String(length=50), nullable=True),
        sa.Column("search_volume", sa.Integer(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
    )
    op.create_index("ix_keyword_snapshots_keyword_id", "keyword_snapshots", ["keyword_id"])
    op.create_index("ix_keyword_snapshots_recorded_at", "keyword_snapshots", ["recorded_at"])

    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "product_id", name="uq_watchlists_user_product"),
    )
    op.create_index("ix_watchlists_product_id", "watchlists", ["product_id"])
    op.create_index("ix_watchlists_user_id", "watchlists", ["user_id"])

    op.create_table(
        "tracked_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("alert_settings", sa.JSON(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "product_id", name="uq_tracked_products_user_product"),
    )
    op.create_index("ix_tracked_products_product_id", "tracked_products", ["product_id"])
    op.create_index("ix_tracked_products_user_id", "tracked_products", ["user_id"])

    op.create_table(
        "search_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("search_id", sa.Integer(), sa.ForeignKey("searches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_snapshot_id", sa.Integer(), sa.ForeignKey("product_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("recommendation", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("search_id", "product_id", name="uq_search_results_search_product"),
    )
    op.create_index("ix_search_results_product_id", "search_results", ["product_id"])
    op.create_index("ix_search_results_search_id", "search_results", ["search_id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tracked_product_id", sa.Integer(), sa.ForeignKey("tracked_products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("old_value", sa.Float(), nullable=True),
        sa.Column("new_value", sa.Float(), nullable=True),
        sa.Column("change_pct", sa.Float(), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_emailed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_alerts_tracked_product_id", "alerts", ["tracked_product_id"])

    op.create_table(
        "usage_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_usage_events_created_at", "usage_events", ["created_at"])
    op.create_index("ix_usage_events_event_type", "usage_events", ["event_type"])
    op.create_index("ix_usage_events_user_id", "usage_events", ["user_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan", sa.String(length=50), server_default="FREE", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("plan in ('FREE', 'STARTER', 'PRO')", name="ck_subscriptions_plan"),
        sa.CheckConstraint("status in ('active', 'trialing', 'past_due', 'canceled')", name="ck_subscriptions_status"),
    )
    op.create_index("ix_subscriptions_provider_subscription_id", "subscriptions", ["provider_subscription_id"], unique=True)
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_provider_subscription_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_usage_events_user_id", table_name="usage_events")
    op.drop_index("ix_usage_events_event_type", table_name="usage_events")
    op.drop_index("ix_usage_events_created_at", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_index("ix_alerts_tracked_product_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_search_results_search_id", table_name="search_results")
    op.drop_index("ix_search_results_product_id", table_name="search_results")
    op.drop_table("search_results")
    op.drop_index("ix_tracked_products_user_id", table_name="tracked_products")
    op.drop_index("ix_tracked_products_product_id", table_name="tracked_products")
    op.drop_table("tracked_products")
    op.drop_index("ix_watchlists_user_id", table_name="watchlists")
    op.drop_index("ix_watchlists_product_id", table_name="watchlists")
    op.drop_table("watchlists")
    op.drop_index("ix_keyword_snapshots_recorded_at", table_name="keyword_snapshots")
    op.drop_index("ix_keyword_snapshots_keyword_id", table_name="keyword_snapshots")
    op.drop_table("keyword_snapshots")
    op.drop_index("ix_product_snapshots_recorded_at", table_name="product_snapshots")
    op.drop_index("ix_product_snapshots_product_id", table_name="product_snapshots")
    op.drop_table("product_snapshots")
    op.drop_index("ix_searches_user_id", table_name="searches")
    op.drop_index("ix_searches_keyword", table_name="searches")
    op.drop_table("searches")
    op.drop_index("ix_keywords_keyword", table_name="keywords")
    op.drop_table("keywords")
    op.drop_index("ix_products_marketplace", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_brand", table_name="products")
    op.drop_index("ix_products_asin", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
