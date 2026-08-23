"""Tests for the canonical persistent search data pipeline."""

from types import SimpleNamespace

import pytest
from sqlalchemy import event

from web_app.backend.db.models import Base, Product, ProductSnapshot, Search, SearchResult, User
from web_app.backend.db.session import SessionLocal, engine
from web_app.backend.services.search_persistence_service import (
    SearchPersistenceError,
    SearchPersistenceService,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def make_request(**overrides):
    values = {
        "keyword": "protein powder",
        "marketplace": "US",
        "pages": 1,
        "min_rating": 3.0,
        "skip_risky_brands": True,
        "skip_hazmat": True,
        "skip_amazon_seller": True,
        "skip_brand_seller": True,
        "min_margin": 20.0,
        "min_sales": 50,
        "max_sales": 1000,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_result(asin="B0SEARCH01", price=19.99, **overrides):
    result = {
        "asin": asin,
        "title": "Example Product",
        "brand": "Example Brand",
        "category": "Health & Household",
        "url": f"https://www.amazon.com/dp/{asin}",
        "price": price,
        "rating": 4.4,
        "reviews": 210,
        "bsr": 4500,
        "estimated_sales": 175,
        "est_revenue": price * 175,
        "est_profit": 600.0,
        "margin": 31.5,
        "enhanced_score": 76.0,
        "_search_confidence": 0.82,
        "_search_recommendation": "Strong demand with manageable competition",
        "seller_info": {"total_sellers": 3, "amazon_seller": False},
    }
    result.update(overrides)
    return result


def test_persist_creates_products_snapshots_search_and_ranked_results(db):
    service = SearchPersistenceService()
    search = service.persist(
        db,
        make_request(),
        [make_result(), make_result("B0SEARCH02", price=24.99)],
    )

    assert search.id is not None
    assert db.query(Product).count() == 2
    assert db.query(ProductSnapshot).count() == 2
    assert db.query(Search).one().user_id is None
    assert db.query(Search).one().filters["min_margin"] == 20.0

    results = db.query(SearchResult).order_by(SearchResult.rank).all()
    assert [result.rank for result in results] == [1, 2]
    assert results[0].score == 76.0
    assert results[0].recommendation == "Strong demand with manageable competition"
    assert results[0].product_snapshot.seller_count == 3
    assert results[0].product_snapshot.raw_data["price"] == 19.99


def test_repeated_search_reuses_product_and_creates_immutable_snapshots(db):
    service = SearchPersistenceService()

    service.persist(db, make_request(), [make_result(price=19.99)])
    service.persist(db, make_request(keyword="whey protein"), [make_result(price=23.49)])

    assert db.query(Product).count() == 1
    snapshots = db.query(ProductSnapshot).order_by(ProductSnapshot.id).all()
    assert [snapshot.price for snapshot in snapshots] == [19.99, 23.49]
    assert db.query(Search).count() == 2
    assert db.query(SearchResult).count() == 2


def test_same_asin_in_different_marketplaces_creates_distinct_products(db):
    service = SearchPersistenceService()

    service.persist(db, make_request(marketplace="US"), [make_result()])
    service.persist(db, make_request(marketplace="UK"), [make_result()])

    products = db.query(Product).order_by(Product.marketplace).all()
    assert [(product.asin, product.marketplace) for product in products] == [
        ("B0SEARCH01", "UK"),
        ("B0SEARCH01", "US"),
    ]


def test_authenticated_search_stores_user_ownership(db):
    user = User(email="owner@example.com", password_hash="not-used-by-this-test")
    db.add(user)
    db.commit()

    search = SearchPersistenceService().persist(
        db,
        make_request(),
        [make_result()],
        user_id=user.id,
    )

    assert search.user_id == user.id


def test_duplicate_product_is_written_once_per_search(db):
    SearchPersistenceService().persist(
        db,
        make_request(),
        [make_result(), make_result(price=22.00)],
    )

    assert db.query(Product).count() == 1
    assert db.query(ProductSnapshot).count() == 1
    results = db.query(SearchResult).all()
    assert len(results) == 1
    assert results[0].rank == 1


def test_failure_rolls_back_all_writes(db):
    def fail_result_insert(*_args, **_kwargs):
        raise RuntimeError("database write failed")

    event.listen(SearchResult, "before_insert", fail_result_insert)
    try:
        with pytest.raises(SearchPersistenceError):
            SearchPersistenceService().persist(db, make_request(), [make_result()])
    finally:
        event.remove(SearchResult, "before_insert", fail_result_insert)

    assert db.query(Product).count() == 0
    assert db.query(ProductSnapshot).count() == 0
    assert db.query(Search).count() == 0
    assert db.query(SearchResult).count() == 0
