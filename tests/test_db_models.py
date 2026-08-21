"""Tests for canonical application database models."""

import pytest
from sqlalchemy import create_engine, inspect

from web_app.backend.db.models import Base

pytestmark = pytest.mark.unit


def test_canonical_metadata_contains_phase_5_tables():
    expected_tables = {
        "users",
        "products",
        "product_snapshots",
        "searches",
        "search_results",
        "keywords",
        "keyword_snapshots",
        "watchlists",
        "tracked_products",
        "alerts",
        "usage_events",
        "subscriptions",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))


def test_canonical_schema_can_create_all_tables_in_sqlite():
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    assert set(Base.metadata.tables).issubset(set(inspector.get_table_names()))
    assert inspector.get_unique_constraints("products")[0]["name"] == (
        "uq_products_asin_marketplace"
    )
