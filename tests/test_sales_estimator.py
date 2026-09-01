from analytics.sales_estimator import BSRSalesEstimator, SalesEstimateInput


def test_bsr_sales_estimator_matches_current_category_curve():
    estimator = BSRSalesEstimator()

    result = estimator.estimate(
        SalesEstimateInput(bsr=10_000, category="Home & Kitchen")
    )

    assert result.monthly_sales == 1202
    assert result.lower_bound == 841
    assert result.upper_bound == 1563
    assert result.confidence == 0.65
    assert result.method == "bsr_log_curve_v2"


def test_bsr_sales_estimator_handles_top_100_bsr():
    estimator = BSRSalesEstimator()

    result = estimator.estimate(SalesEstimateInput(bsr=50, category="Electronics"))

    assert result.monthly_sales == 12500
    assert result.confidence == 0.75


def test_bsr_sales_estimator_handles_invalid_bsr():
    estimator = BSRSalesEstimator()

    result = estimator.estimate(SalesEstimateInput(bsr=0, category="Home & Kitchen"))

    assert result.monthly_sales == 0
    assert result.lower_bound == 0
    assert result.upper_bound == 0
    assert result.confidence == 0.0


def test_bsr_sales_estimator_uses_lower_confidence_for_unknown_categories():
    estimator = BSRSalesEstimator()

    result = estimator.estimate(SalesEstimateInput(bsr=250_000, category="Unknown"))

    assert result.monthly_sales > 0
    assert result.confidence == 0.35
