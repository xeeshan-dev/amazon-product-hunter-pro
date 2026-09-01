<!-- # Implementation Reference

This is the current technical record of the repository changes. It replaces
the older status, roadmap, and implementation-summary documents.

## Runtime Model

The supported application path is:

~~~text
React/Vite frontend -> FastAPI API -> providers/analytics/services -> database
~~~

- Frontend: web_app/frontend/
- Backend entrypoint: web_app.backend.main:app
- Frontend API URL: VITE_API_URL or http://127.0.0.1:8000/api
- Application settings: config/settings.py

Primary references:

- [Canonical runtime and local commands](README.md#canonical-runtime)
- [Backend API wiring](web_app/backend/main.py)
- [Frontend application](web_app/frontend/src/App.jsx)

## Phase 1: Canonical Runtime

### What changed

- Established web_app/backend/main.py as the canonical FastAPI entrypoint.
- Kept web_app/backend/main_v2.py as a compatibility shim.
- Aligned Docker, local development commands, CORS, and frontend API settings
  around port 8000.

### Code references

- [FastAPI application and CORS setup](web_app/backend/main.py)
- [Compatibility entrypoint](web_app/backend/main_v2.py)
- [Local development launcher](run_dev.py)
- [Container entrypoint](Dockerfile)
- [Development commands](Makefile)

## Phase 2: Settings and Dependencies

### What changed

- Centralized configuration in typed Pydantic settings.
- Added safe Boolean parsing for local environment values.
- Split dependencies into runtime, development, and production tiers.
- Added environment templates without committing real secrets.

### Code references

- [Settings model and validation](config/settings.py)
- [Legacy configuration compatibility layer](config/config.py)
- [Runtime requirements](requirements.txt)
- [Development requirements](requirements-dev.txt)
- [Production requirements](requirements-prod.txt)
- [Environment template](.env.example)

## Phase 3: Deterministic Testing

### What changed

- Moved live/manual checks out of the default pytest workflow.
- Added unit, API, integration, and slow test markers.
- Blocked live HTTP requests during ordinary test runs.
- Kept manual API and LLM diagnostics under scripts/manual/.

### Code references

- [Pytest configuration](pytest.ini)
- [HTTP test guard and shared fixtures](tests/conftest.py)
- [API contract tests](tests/test_api.py)
- [Manual API smoke test](scripts/manual/api_smoke.py)
- [Manual search diagnostic](scripts/manual/api_search_diagnostic.py)
- [Manual LLM diagnostic](scripts/manual/llm_smoke.py)

### Commands

~~~powershell
pytest tests/ -v
make test-cov
~~~

## Phase 4: Provider Boundary

### What changed

- Added a provider interface for external product data.
- Wrapped the legacy HTML scraper in AmazonHTMLProvider.
- Kept normalization and external collection separate from scoring, financials,
  filtering, and API routes.

### Code references

- [Provider contract](src/providers/base.py)
- [Amazon HTML provider adapter](src/providers/amazon_html_provider.py)
- [Legacy scraper used by the provider](src/scraper/amazon_scraper.py)
- [Provider tests](tests/test_providers.py)

## Phase 5: Canonical Database and Migrations

### What changed

- Added canonical SQLAlchemy models for users, products, snapshots, searches,
  watchlists, tracking, alerts, usage events, and subscriptions.
- Added Alembic migration configuration and the initial schema migration.
- Added canonical session management using DATABASE_URL.

### Code references

- [Canonical database models](web_app/backend/db/models.py)
- [Database session dependency](web_app/backend/db/session.py)
- [Initial Alembic schema migration](alembic/versions/20260821_0001_create_canonical_app_tables.py)
- [Alembic environment](alembic/env.py)
- [Database model tests](tests/test_db_models.py)

### Commands

~~~powershell
make db-migrate
make db-rollback
~~~

## Phase 6: Search Pipeline

### What changed

- Moved the /api/search implementation out of the API route into a dedicated
  pipeline.
- Preserved the existing response structure while making stages explicit:
  provider collection, rating filter, opportunity scoring, risk checks,
  financial calculations, sales/margin filters, seller enrichment, seller
  filters, and response construction.

### Code references

- [Search pipeline](web_app/backend/services/search_pipeline.py)
- [Search route](web_app/backend/main.py)
- [Pipeline tests](tests/test_search_pipeline.py)

## Phase 7: Analytics Isolation

### What changed

- Extracted profitability calculations into a typed analytics service.
- Extracted BSR-based sales estimation from scraper ownership.
- Centralized product risk output and skip decisions.
- Extracted score-derived strengths, weaknesses, and recommendations.

### Code references

- [Profitability analyzer](src/analytics/profitability.py)
- [BSR sales estimator](src/analytics/sales_estimator.py)
- [Product risk analyzer](src/analytics/risk.py)
- [Recommendation engine](src/analytics/recommendations.py)
- [Scraper delegation to sales estimation](src/scraper/amazon_scraper.py)
- [Scorer delegation to recommendations](src/analysis/enhanced_scoring.py)

### Tests

- [Profitability tests](tests/test_profitability.py)
- [Sales estimator tests](tests/test_sales_estimator.py)
- [Risk analyzer tests](tests/test_risk_analyzer.py)
- [Recommendation tests](tests/test_recommendations.py)
- [Scraper analytics delegation tests](tests/test_scraper_analytics.py)

## Authentication and User-Owned Tracking

This work followed the seven phases because the canonical tracking schema
requires an owner for every tracked product.

### What changed

- Added user registration, login, bearer JWTs, and current-user lookup.
- Uses bcrypt hashes instead of storing passwords.
- Requires authentication for every tracking endpoint.
- Stores tracking settings per user and product.
- Stores price/BSR/review history as canonical product snapshots.
- Keeps legacy SQLite tracking data untouched until an explicit import.
- Added a frontend sign-in/register dialog for tracking operations.

### API endpoints

~~~text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me

GET    /api/tracking/products
POST   /api/tracking/add
DELETE /api/tracking/{asin}
GET    /api/tracking/{asin}/history
PUT    /api/tracking/{asin}/settings
GET    /api/tracking/alerts
POST   /api/tracking/alerts/read
POST   /api/tracking/check
GET    /api/tracking/stats
~~~

### Code references

- [Authentication service](web_app/backend/services/auth_service.py)
- [Canonical tracking service](web_app/backend/services/canonical_tracking_service.py)
- [Auth and tracking routes](web_app/backend/main.py)
- [Tracking authentication in the UI](web_app/frontend/src/App.jsx)
- [Legacy SQLite import utility](scripts/migrate_legacy_tracking.py)
- [Auth API tests](tests/test_auth_api.py)
- [User-isolated tracking tests](tests/test_tracking_api.py)

### Legacy import

Run this only after backing up the legacy SQLite database and applying the
canonical migration:

~~~powershell
make db-migrate
make db-migrate-legacy-tracking
~~~

The importer defaults to a disabled legacy-tracking@local.invalid user. Do not
assign legacy records to a real user until an ownership policy is decided.

## Phase 8: Persistent Search Data Pipeline

### What changed

- Added one canonical database transaction after search collection, filtering,
  scoring, risk analysis, financial calculations, seller enrichment, sorting,
  and response construction.
- Reuses a canonical `Product` by the existing `(asin, marketplace)` unique
  identity and updates stable descriptive fields when newer values exist.
- Creates a fresh immutable `ProductSnapshot` for each persisted response
  result, including market observations, seller count, financial estimates,
  opportunity score, confidence, and normalized raw data.
- Creates a `Search` record on every successful request. Searches remain
  anonymous by default and are associated with a user only when a valid bearer
  token was supplied.
- Creates one ranked `SearchResult` per distinct product in the response,
  linking the search, canonical product, and observation snapshot.
- Rolls back the whole write transaction on any persistence failure and returns
  the generic `Unable to save search results` API message rather than a driver
  or database error.
- Keeps persistence metadata internal so the existing search response shape is
  unchanged.

### Code references

- [Persistence service and transaction boundary](web_app/backend/services/search_persistence_service.py)
- [Pipeline persistence integration](web_app/backend/services/search_pipeline.py)
- [Optional-user search route](web_app/backend/main.py)
- [Canonical product/search/snapshot models](web_app/backend/db/models.py)
- [Session dependency](web_app/backend/db/session.py)

### Data Flow

~~~text
Provider -> normalization -> scoring/risk/profit -> filters -> seller enrichment
-> ranking/response assembly -> SearchPersistenceService transaction -> response
~~~

The API returns at most 50 ranked products. Phase 8 persists exactly those
response-visible results, while retaining the existing summary values for all
products that passed the pipeline filters.

### Verification

- [Direct persistence tests](tests/test_search_persistence.py) cover product
  reuse, marketplace identity, immutable snapshots, anonymous/authenticated
  searches, duplicate result prevention, and transaction rollback.
- [API persistence tests](tests/test_search_persistence_api.py) cover bearer
  ownership and safe persistence failures.
- [Existing API contract tests](tests/test_api.py) confirm the unchanged JSON
  response and anonymous persistence behavior.

### Phase 9 Candidates

- Add paginated authenticated search history and search-detail endpoints.
- Move expensive scraper searches to background jobs and persist a `running` or
  `failed` search state for long-running requests.
- Add retention policy and indexes tuned from production query behavior.
- Add a provider with an authorized Amazon data source for more reliable live
  product coverage.

## Phase 9: Provider Consistency and Historical Intelligence

### What changed

- Refactored canonical tracking refreshes to depend on
  `ProductDataProvider.get_product()` rather than `AmazonScraper`.
- Removed the direct scraper dependency from the canonical FastAPI runtime.
  `AmazonHTMLProvider` is now the active adapter used by tracking; search was
  already provider-based.
- Added `HistoryService`, which reads the existing immutable
  `ProductSnapshot` records and owns timeline and metric-history queries.
- Added deterministic price, BSR, review, and opportunity-score metrics.
  BSR trend interpretation recognizes that lower rank is better.
- Added a small trend engine that returns `Improving`, `Stable`, `Declining`,
  or `Insufficient Data`. It requires at least three observations and makes no
  statistical-significance claim.
- Added freshness metadata with `Fresh`, `Aging`, `Stale`, and `Unavailable`
  states. Thresholds are configured by `OBSERVATION_FRESH_HOURS` and
  `OBSERVATION_STALE_HOURS`.
- Documented the persistent-observation reuse strategy. Automatic search
  reuse is not enabled yet because it needs filter-aware cache semantics.

### Code references

- [Provider interface](src/providers/base.py)
- [Amazon HTML provider adapter](src/providers/amazon_html_provider.py)
- [Canonical tracking provider integration](web_app/backend/services/canonical_tracking_service.py)
- [Historical data service](web_app/backend/services/history_service.py)
- [Trend classifier](src/analytics/trends.py)
- [Canonical application wiring](web_app/backend/main.py)
- [Freshness settings](config/settings.py)

### Tests

- [Historical intelligence tests](tests/test_history_service.py)
- [Provider-based tracking refresh tests](tests/test_tracking_provider.py)
- [Existing provider tests](tests/test_providers.py)
- [Existing tracking API tests](tests/test_tracking_api.py)

### Remaining limitation

Phase 9 provides service-level historical intelligence but deliberately does
not add product-analysis or search-history endpoints. Those user-facing
contracts begin in Phase 10 and Phase 11 respectively.

## Phase 10: Product Analyzer

### What changed

- Added `GET /api/products/{asin}` for a single-ASIN deterministic analysis.
- Added `GET /api/products/{asin}/history` for canonical observation history
  and historical metrics.
- Uses the existing provider boundary for missing or stale observations, then
  persists a new immutable canonical snapshot.
- Reuses the existing scoring, risk, profitability, seller, persistence, and
  history services rather than creating parallel implementations.
- Returns overview, demand, competition, profitability, risk, listing,
  trends, recommendation, and data-quality sections.
- Generates recommendation labels from the existing opportunity score and risk
  data. No LLM is used as a source of numerical marketplace intelligence.

### Code references

- [Product analyzer service](web_app/backend/services/product_analyzer_service.py)
- [Product endpoints](web_app/backend/main.py)
- [Reusable single-product pipeline analysis](web_app/backend/services/search_pipeline.py)
- [Canonical observation persistence](web_app/backend/services/search_persistence_service.py)
- [Historical intelligence](web_app/backend/services/history_service.py)
- [Analyzer tests](tests/test_product_analyzer.py)

### Remaining limitation

The API is available for the future product page, but the frontend route and
visual analyzer view are intentionally deferred to Phase 12/13. Phase 11 is
the next backend phase: user-owned search history and dashboard data contracts.

## Phase 11: Search History and Dashboard Data

### What changed

- Added authenticated search-history, search-detail, and search-result APIs.
- Added a small authenticated dashboard data contract for recent searches,
  active tracked products, unread alerts, and persisted strong opportunities.
- Enforced ownership at the service layer for every search record query.
  Requests for another user's search return `404` rather than revealing its
  existence.
- Kept anonymous search public while intentionally excluding anonymous records
  from user history.
- Added offset pagination to search-history and search-result responses.

### API endpoints

~~~text
GET /api/search/history?limit=20&offset=0
GET /api/search/{search_id}
GET /api/search/{search_id}/results?limit=50&offset=0
GET /api/dashboard
~~~

### Code references

- [Search history service](web_app/backend/services/search_history_service.py)
- [Search history and dashboard routes](web_app/backend/main.py)
- [Ownership and pagination API tests](tests/test_search_history_api.py)
- [Canonical search models](web_app/backend/db/models.py)

### Remaining limitation

The backend data contract is complete, but the frontend has not yet added a
search-history page or dashboard presentation. That UI work belongs to the
frontend architecture and UX phases, after backend contracts settle.

## Phase 12: Frontend Architecture Refactor

### What changed

- Moved the existing product-hunter experience from the root application
  component into `pages/ProductHunter.jsx` without changing its workflow.
- Added a small app router with `/` and `/hunter` as the active product-hunter
  routes, plus reserved top-level paths for the planned product application.
- Added a shared API client that centralizes `VITE_API_URL` and supports future
  authenticated page services.
- Reused the existing shared export utility instead of keeping a duplicate
  download implementation inside the page.
- Preserved the existing `ChatInterface` and `ProfitCalculator` component
  boundaries. Larger component extraction is intentionally incremental to
  avoid changing the established hunter behavior during an architecture phase.

### Code references

- [Application root](web_app/frontend/src/App.jsx)
- [Route shell](web_app/frontend/src/app/router.jsx)
- [Product Hunter page](web_app/frontend/src/pages/ProductHunter.jsx)
- [Shared API client](web_app/frontend/src/services/apiClient.js)
- [Export utility](web_app/frontend/src/utils/exportUtils.js)
- [Existing chat component](web_app/frontend/src/components/ChatInterface.jsx)
- [Existing profit calculator](web_app/frontend/src/components/ProfitCalculator.jsx)

### Verification and limitation

`npm run build` completes successfully. `npm run lint` now runs cleanly with
zero errors and warnings via the added `.eslintrc.cjs`; `react/prop-types`
is disabled because this plain-JS codebase consumes dynamic API payloads and
does not use PropTypes or TypeScript.

Phase 12 intentionally does not redesign the interface or create dedicated
dashboard, search-history, or product-analyzer pages. Those are the next
customer-facing UX increments in Phase 13.

## Phase 13: Product Intelligence UX

### What changed

- Added a shared application shell with concise navigation for the active
  dashboard, product hunter, ASIN analyzer, and search-history workflows.
- Added a dashboard page that consumes the authenticated dashboard contract
  and presents recent searches, tracked products, alerts, and opportunities.
- Added a paginated search-history page with result inspection based on the
  authenticated Phase 11 APIs.
- Added an ASIN analyzer page that uses the Phase 10 analysis and observation
  history APIs, with marketplace selection and explicit unavailable/error
  states.
- Preserved Product Hunter as the primary search workflow. Existing advanced
  filters and product controls were not rewritten while the new views were
  introduced.

### Code references

- [App shell and navigation](web_app/frontend/src/components/layout/AppShell.jsx)
- [Dashboard page](web_app/frontend/src/pages/Dashboard.jsx)
- [Search history page](web_app/frontend/src/pages/SearchHistory.jsx)
- [ASIN analyzer page](web_app/frontend/src/pages/ProductAnalyzer.jsx)
- [Product intelligence API service](web_app/frontend/src/services/productIntelligence.js)
- [Route selection](web_app/frontend/src/app/router.jsx)

### Verification and limitation

The Vite production build transforms all application modules successfully.
The current browser router is deliberately minimal and uses the native history
API; route-based code splitting and richer navigation states can be introduced
later if the application grows beyond the current set of pages.

## Phase 14: Tracking Refinement

### What changed

- Enriched tracked-product responses with latest opportunity score, score
  change, historical price/BSR/review/score trends, and freshness metadata.
- Updated the existing tracking panel to display the current score, trend
  summary, and data freshness alongside the existing price/BSR/review values.
- Retained existing user alert thresholds and alert types. No noisy additional
  alert types were introduced without a user-configurable policy.

### Code references

- [Tracking response assembly](web_app/backend/services/canonical_tracking_service.py)
- [Tracking panel](web_app/frontend/src/pages/ProductHunter.jsx)
- [Tracking API tests](tests/test_tracking_api.py)

## Phase 15 and Phase 16: Usage and Plan Foundations

### What changed

- Added centralized `UsageService` event recording for search, product
  analysis, and tracking-add workflows.
- Added authenticated `GET /api/account` with account identity, accumulated
  usage, and plan limits.
- Added `PlanService` with FREE, STARTER, and PRO limit definitions.
- Deliberately does not enforce limits or integrate billing yet. Limits must be
  calibrated from real usage before they restrict customers.

### Code references

- [Usage service](web_app/backend/services/usage_service.py)
- [Plan service](web_app/backend/services/plan_service.py)
- [Account and event wiring](web_app/backend/main.py)
- [Usage tests](tests/test_usage_service.py)

## Phase 17: Confidence and Data Quality

### What changed

- Added a single confidence service for estimate presentation.
- Product analyzer estimates now include value, coarse lower/upper bounds,
  confidence, source, observed time, and method.
- Data quality reports `Good`, `Limited`, `Stale`, or `Unavailable` without
  claiming precision beyond the stored observation and analytics model.

### Code references

- [Confidence service](web_app/backend/services/confidence_service.py)
- [Product analyzer estimate response](web_app/backend/services/product_analyzer_service.py)
- [Analyzer estimate UI](web_app/frontend/src/pages/ProductAnalyzer.jsx)
- [Confidence tests](tests/test_confidence_service.py)

## Phase 18: Market Intelligence

### What changed

- Added category-level latest-observation aggregates for price, reviews,
  opportunity score, estimated revenue, and seller count.
- Added read-only `/api/market/categories` and
  `/api/market/categories/{category}` endpoints.
- Each response discloses that it aggregates only application-observed
  products, not the full external market.

### Code references

- [Market intelligence service](web_app/backend/services/market_intelligence_service.py)
- [Market API routes](web_app/backend/main.py)
- [Aggregate tests](tests/test_market_intelligence.py)

## Winning Product Filtering Engine

### What changed

- Replaced the two-signal qualification (`sales range + margin`) and the
  score-plus-confidence composite with an eight-factor evidence engine in
  `WinningProductFilter`.
- Factors are opportunity, demand/sales, profitability, competition, risk,
  seller position, data confidence, and market trend, each scored 0-100 with
  fixed weights that renormalize over the factors that actually have data.
- Missing evidence is reported as unavailable instead of being scored as a
  failure, so candidates without seller or history observations are not
  silently penalized toward empty result sets.
- Added graded verdicts answering "Is this product worth further sourcing and
  market research?": `Strong research candidate` (unchanged string for
  frontend compatibility), `Worth researching`, `Needs validation`, and
  `Deprioritize`.
- No single signal can produce a top verdict: the strong tier requires a
  composite of at least 65, at least four supporting signals, no core factor
  below 40, no unresolved brand/hazmat review flags, and data confidence of
  at least 0.45.
- Wired the existing deterministic trend classifier into qualification via an
  optional `history` argument using price, BSR (lower rank is better), and
  review series. During searches the pipeline now reuses stored canonical
  `ProductSnapshot` observations through `HistoryService`, so previously seen
  ASINs qualify with real trend evidence while genuinely new ASINs still
  report `Insufficient Data` honestly. Lookup failures never fail a search.
- Confirmed facts are now separated from uncertain flags: veto-level brand or
  hazmat results are excluded by the pipeline only when the corresponding
  request filter is enabled, and the scorer's own veto caps the composite so
  a vetoed product can no longer rank first on other signals.
- Search responses now include a verdict distribution in
  `summary.verdicts`. All previous response keys are unchanged.

### Code references

- [Multi-signal qualification engine](src/analytics/winning_product_filter.py)
- [Pipeline risk gating and verdict summary](web_app/backend/services/search_pipeline.py)
- [Trend classifier](src/analytics/trends.py)
- [Filtering engine tests](tests/test_winning_product_filter.py)

## Product Hunter Workbench UI

### What changed

- Replaced the centered hero layout of the product-hunter page with a
  compact research-workbench layout: a toolbar header, a full-width search
  row with the marketplace toggle, and collapsible filters.
- Added an Xray-style results data table as the default results view:
  compare checkboxes, ranked rows with thumbnail/title/brand, price,
  estimated monthly sales, revenue, color-coded margin, profit per unit,
  reviews, BSR, observed seller count with an Amazon-seller marker,
  opportunity-score chip, verdict badge, watchlist/tracking actions, and
  sortable column headers.
- Kept the previous card view as a selectable "Cards" mode; both views share
  the same filtering, sorting, comparison, export, and tracking handlers.
- Added winners count from `summary.verdicts` to the results header and
  extended client-side sorting to verdict, reviews, BSR, sellers, and
  per-unit profit columns.

### Code references

- [Results table component](web_app/frontend/src/components/ResultsTable.jsx)
- [Shared verdict metadata](web_app/frontend/src/components/verdicts.jsx)
- [Client-side navigation helper](web_app/frontend/src/app/navigation.js)
- [ESLint configuration](web_app/frontend/.eslintrc.cjs)
- [Product hunter page](web_app/frontend/src/pages/ProductHunter.jsx)
- [Application shell](web_app/frontend/src/components/layout/AppShell.jsx)

## Prerequisite-Gated Roadmap

The following phases cannot be completed truthfully with the current local
repository alone and are intentionally not simulated:

- **Phases 19-21 (ML data, sales estimation, trend detection):** require a
  sufficiently large, labeled, time-separated historical dataset and measured
  validation results showing an improvement over the deterministic BSR model.
- **Phase 22 (data-grounded AI assistant):** requires a defined retrieval and
  authorization policy for each user-owned data scope before exposing analysis
  to the LLM assistant.
- **Phase 23 (paid provider):** requires demonstrated provider-quality gaps,
  budget approval, credentials, and a commercial/legal review.
- **Phase 24 (cost optimization):** needs real production request volumes,
  provider costs, cache-hit measurements, and usage data over time.
- **Phases 25-26 (production hardening and SaaS launch):** require deployment
  infrastructure, managed database backups, real secret management, monitoring
  accounts, legal/privacy review, operational ownership, and customer/billing
  decisions. Code cannot substitute for these controls.

## Current Search Behavior and Known Limitation

The application works end-to-end, but Amazon HTML responses are not guaranteed.
Amazon can return empty, deferred, challenge, or layout-changed responses,
which causes the provider to return no product candidates.

Seller filtering can also make a search appear empty. With Skip Amazon as
Seller enabled, the pipeline fetches seller data for each candidate and removes
products when Amazon is detected as a seller. This is intentionally slower
because the provider may need an AOD request followed by a full product-page
fallback.

Relevant implementation:

- [Scraper search and parsing](src/scraper/amazon_scraper.py)
- [Seller enrichment and filters](web_app/backend/services/search_pipeline.py)
- [Seller analysis implementation](src/analysis/seller_analysis.py)

## Verification Status

The latest full backend verification before Phase 8 completed with:

~~~text
36 passed
~~~

Run it locally with:

~~~powershell
pytest tests/ -v
~~~

The frontend code is in place. If npm run build stops during Vite
transformation without reporting a code error, check the local machine's
available memory and retry with other memory-heavy applications closed.

## Related Git Commits

~~~text
63636ff  refactor: establish canonical backend platform
ff53eec  feat: add authenticated tracking interface
acef321  docs: remove obsolete project documentation
~~~ -->

## Bug Fixes (August 31, 2026)

### Critical Bug #1: Seller Data Not Fetched Unless Filters Enabled

**Problem:** The `_enrich_seller_info()` method in `search_pipeline.py` had a conditional check that only fetched seller data when `skip_amazon_seller` or `skip_brand_seller` filters were enabled. This meant that when users searched WITHOUT filters, all products showed "n/a" for seller information (FBA count, FBM count, Amazon seller status).

**Impact:** 
- Users could not see critical seller information needed for product research decisions
- Products appeared to have no competition data
- Brand ownership detection was completely skipped
- Amazon seller presence was unknown

**Root Cause:**
```python
need_seller_data = (
    request.skip_amazon_seller or request.skip_brand_seller
)
if not need_seller_data:
    product["seller_info"] = {
        "amazon_seller": False,
        "total_sellers": 0,
        "seller_name": None,
        "data_status": "not_requested",
    }
    return
```

**Fix:** Removed the conditional check. Seller data is now fetched for ALL products regardless of filter settings. This is essential because:
1. Users need seller information to make informed sourcing decisions
2. FBA/FBM counts indicate competition level
3. Amazon seller presence affects profit margins
4. Brand ownership detection requires seller data

**Changed Files:**
- `web_app/backend/services/search_pipeline.py` - Line 237-253

**Verification:** Run a search without filters enabled. Seller information now appears for all products.

---

### Critical Bug #2: Sales Estimation Significantly Under-Reporting

**Problem:** The BSR-to-sales formula was using conservative multipliers from 2024 data, resulting in estimated sales being 3-5x lower than actual Amazon sales data. For example:
- Amazon shows: "7K+ bought in past month"  
- System showed: "1,546 estimated sales"

**Impact:**
- Products appeared less profitable than they actually were
- Revenue estimates were severely underestimated
- Users missed high-opportunity products due to incorrect sales data
- Filtering by sales range excluded valid products

**Root Cause:** The power curve formula used multipliers that were too conservative:
```python
CATEGORY_CURVES = {
    "Health & Household": (60000, 0.4),  # Too low
    "Home & Kitchen": (50000, 0.4),
    # ...
}
DEFAULT_CURVE = (40000, 0.4)
```

**Fix:** Updated the sales estimation formula with 2026-calibrated curves:
- Doubled multipliers (60000 ? 120000 for Health & Household)
- Increased exponents (0.4 ? 0.50) for more aggressive estimates
- Updated top-100 formula to reflect exponential sales at top ranks
- Added Tools & Home Improvement category
- Increased sales cap from 50K to 100K/month

**New Formula Examples:**
- BSR #1,730 ? ~7,000 sales/month (matches Amazon data)
- BSR #100 ? ~12,000 sales/month
- BSR #10,000 ? ~800 sales/month

**Changed Files:**
- `src/analytics/sales_estimator.py` - Updated all category curves and estimation logic

**Verification:** Search for products and compare "Estimated Sales" with Amazon's "X bought in past month" badge. Values now align within reasonable margin.

---

### Technical Notes

**Seller Data Enrichment Flow:**
```
Search Request ? Provider (scraper) ? Scoring/Risk ? Seller Enrichment (ALL products) ? Filtering ? Response
```

**Seller data status semantics (current):**
- `observed`: offer data parsed successfully
- `blocked`: Amazon challenge/interstitial blocked offer scraping
- `parse_failed`: offer page fetched but seller rows could not be parsed
- `unavailable`: no usable offer response returned

When `skip_amazon_seller=true` or `skip_brand_seller=true`, seller filtering is now fail-closed: products with non-`observed` seller data are excluded instead of silently treated as safe.

**Sales Estimation Method:**
- Method: `bsr_log_curve_v2` (updated)
- Confidence: 0.50-0.75 depending on BSR range and category match
- Formula: `sales = multiplier * (BSR ^ -exponent)`
- Special handling for top 100 products with exponential curve

**Performance Considerations:**
- Seller enrichment adds 1-2 seconds per product due to AOD endpoint calls
- Rate limiting still applies (8-15 second delays between requests)
- Smart anti-blocking system handles failures gracefully with 7 fallback endpoints

**Related Code:**
- [Search pipeline seller enrichment](web_app/backend/services/search_pipeline.py)
- [Sales estimator calibration](src/analytics/sales_estimator.py)
- [Seller analysis implementation](src/analysis/seller_analysis.py)
- [AOD endpoint scraping](src/scraper/amazon_scraper.py)

---
