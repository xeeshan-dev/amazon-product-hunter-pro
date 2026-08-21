# Amazon Hunter Pro 🚀

Amazon FBA product research platform with a React/Vite frontend and FastAPI backend for scraping, scoring, keyword research, and tracking workflows.

## Canonical Runtime

- **Frontend**: `web_app/frontend/`
- **Backend**: `web_app.backend.main:app`
- **Local API command**: `make dev`
- **Local frontend command**: `cd web_app/frontend && npm run dev`
- **Docker API entrypoint**: `uvicorn web_app.backend.main:app --host 0.0.0.0 --port 8000`

`web_app/backend/main_simple.py` is a development/reference implementation. `web_app/backend/main_v2.py` is only a temporary compatibility shim and is not the canonical entrypoint.

## ⚡ Features

### Core Analysis
- **3-Pillar Opportunity Scoring** - Demand (40%), Competition (35%), Profit (25%)
- **Accurate FBA Fee Calculator** - 2024 rates with dimensional weight
- **Market Analysis** - BSR-to-sales estimation, profit margins, competition scoring
- **BSR Tracking** - Build your own historical database

### Risk Detection
- **Brand Risk Checker** - IP claim detection with 500+ risky brands
- **Hazmat Detector** - Keyword-based hazmat screening
- **Veto Logic** - Auto-reject high-risk products

### Data Intelligence
- **Free Keyword Research** - Amazon autocomplete API
- **Price History** - CamelCamelCamel integration
- **Seller Analysis** - FBA/FBM counts, Amazon presence detection

### Production Infrastructure
- **Redis Caching** - Fast response times
- **Rate Limiting** - Distributed rate limiting with Redis
- **Structured Logging** - JSON logs with rotation
- **Docker Support** - Full containerization
- **Health Checks** - Kubernetes-ready endpoints
- **CI/CD Pipeline** - Automated testing and deployment

## 🏗️ Architecture

```
amazon_hunter/
├── src/                    # Core analysis modules
│   ├── scraper/           # Amazon scraping
│   ├── providers/         # Provider boundary for product data collection
│   ├── analysis/          # Scoring, FBA calc, market analysis
│   └── risk/              # Brand risk, hazmat detection
├── web_app/
│   ├── backend/           # FastAPI REST API
│   └── frontend/          # React UI
├── core/                  # Infrastructure
│   ├── cache.py          # Redis caching
│   ├── rate_limiter.py   # Rate limiting
│   └── logging_config.py # Structured logging
├── config/               # Configuration management
├── tests/                # Test suite
└── docker-compose.yml    # Multi-service orchestration
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Redis (or use Docker)
- PostgreSQL (or use Docker)

### 1. Clone & Setup

```bash
git clone <repository>
cd amazon_hunter

# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Run with Docker (Recommended)

```bash
# Build and start all services
make docker-up

# Or manually:
docker-compose up -d

# Check logs
make logs
```

Services will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 3. Run Locally (Development)

```bash
# Install dependencies
make install

# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Run backend development server
make dev

# In another terminal, run the canonical frontend
cd web_app/frontend
npm install
npm run dev
```

### Provider Boundary

Product data collection is routed through `src/providers/`.

- `ProductDataProvider` defines the provider contract.
- `AmazonHTMLProvider` adapts the existing Amazon HTML scraper.
- Providers collect and normalize external product data.
- Scoring, profitability, risk checks, recommendations, filtering, and user-specific decisions stay outside the provider.

The current Amazon scraper still produces some legacy estimate fields for compatibility. Those calculations are isolated behind the provider boundary now and can be moved into analytics services in the next refactor without changing the API entrypoint again.

### Search Pipeline

`POST /api/search` delegates to `web_app/backend/services/search_pipeline.py`.

The current synchronous request path is organized into explicit stages:

1. Collect normalized products through the provider.
2. Apply cheap request filters such as rating.
3. Apply existing opportunity scoring.
4. Apply existing brand and hazmat risk checks.
5. Calculate current fee/profit/revenue fields.
6. Apply margin and sales filters.
7. Enrich seller data only when seller filters require it.
8. Apply seller filters.
9. Build summary, market share, sorting, and the existing response schema.

The API response shape and scoring weights are intentionally preserved. Fee/profit, sales estimation, risk, and opportunity recommendations are now isolated behind analytics services.

### Analytics Services

Analytics services live in `src/analytics/` and are kept independent from FastAPI and frontend code.

Current isolated analytics:

- `ProfitabilityAnalyzer`: calculates revenue, Amazon fees, COGS, net profit, and margin using typed input/output models.
- `BSRSalesEstimator`: estimates monthly unit sales from BSR and category using the existing logarithmic category curves, with bounds and confidence metadata.
- `ProductRiskAnalyzer`: evaluates brand and hazmat risk, preserving the existing API `risks` response shape while centralizing veto/filter decisions.
- `OpportunityRecommendationEngine`: derives strengths, weaknesses, and sourcing recommendations from the three opportunity-score pillars without changing existing messages.

The analyzer preserves the current default COGS assumption of 25% of selling price. Later phases should move this assumption into user/configurable inputs.

The active Amazon scraper now delegates BSR sales estimation to `BSRSalesEstimator` through a compatibility wrapper. The provider still supplies the runtime `estimated_sales` field, but the formula is no longer owned by scraper parsing code.

## 📚 API Documentation

### Authentication
```bash
# Create an account. The response includes a bearer access token.
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "use-a-long-unique-password",
  "full_name": "Example User"
}

# Obtain a new token with existing credentials.
POST /api/auth/login

# Read the authenticated user.
GET /api/auth/me
Authorization: Bearer <access_token>
```

Apply the canonical migrations before using authentication against a new database:
`make db-migrate`.

### Search Products
```bash
POST /api/search
{
  "keyword": "yoga mat",
  "marketplace": "US",
  "pages": 2,
  "min_rating": 3.0,
  "skip_risky_brands": true,
  "skip_hazmat": true
}
```

### Keyword Suggestions
```bash
GET /api/keywords?q=yoga
```

### Health Check
```bash
GET /health
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run only unit tests
pytest tests/ -m unit

# Run only FastAPI contract tests
pytest tests/ -m api

# Run with coverage
make test-cov

# Run specific test
pytest tests/test_api.py -v
```

Automated tests are deterministic and block live HTTP requests by default. Any
test that intentionally performs live I/O must be marked `integration` and
should not be part of the default `make test` path.

Manual live checks are kept outside pytest:

```bash
python scripts/manual/api_smoke.py --api-url http://127.0.0.1:8000
python scripts/manual/api_search_diagnostic.py --api-url http://127.0.0.1:8000
python scripts/manual/llm_smoke.py
```

## 🔒 Security Features

- **Environment-based Configuration** - No hardcoded secrets
- **Input Validation** - Pydantic models with XSS prevention
- **Rate Limiting** - Per-IP and per-user limits
- **CORS Protection** - Configurable allowed origins
- **Security Headers** - X-Frame-Options, CSP, etc.
- **Non-root Docker User** - Container security
- **Health Checks** - Liveness and readiness probes

## 📊 Monitoring

### Health Endpoints
- `/health` - Overall system health
- `/ready` - Readiness for traffic
- `/metrics` - Basic metrics (Redis stats)

### Logging
Logs are written to:
- Console (stdout)
- `logs/app.log` (rotating, 10MB, 5 backups)
- `logs/error.log` (errors only)

JSON logging in production for easy parsing.

## 🐳 Docker Commands

```bash
# Build images
make docker-build

# Start services
make docker-up

# Stop services
make docker-down

# View logs
make logs

# Shell into API container
make shell

# Redis CLI
make redis-cli

# PostgreSQL CLI
make psql
```

## 🔧 Configuration

### Dependency Files

- `requirements.txt` contains the canonical backend/runtime dependencies.
- `requirements-dev.txt` includes runtime dependencies plus tests, code quality tools, docs, and the legacy Streamlit UI.
- `requirements-prod.txt` includes runtime dependencies plus production deployment integrations such as PostgreSQL, Redis, Celery, monitoring, and security packages.
- `web_app/backend/requirements.txt` is only a backend-local convenience wrapper that points back to the root runtime file.

Use `make install` for local development. Docker installs `requirements-prod.txt`.

### Settings

Backend settings are centralized in `config/settings.py` and loaded from the project-root `.env` file plus environment variables. `config/config.py` remains only as a compatibility re-export for older imports.

Key environment variables:

```bash
# Application
ENVIRONMENT=production  # development, staging, production
DEBUG=false

# Security
SECRET_KEY=<32+ character secret>
JWT_SECRET_KEY=<32+ character secret>
ALLOWED_ORIGINS=https://yourdomain.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=20
RATE_LIMIT_PER_HOUR=500

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
TRACKING_DATABASE_URL=sqlite:///./web_app/backend/data/amazon_hunter.db
REDIS_URL=redis://host:6379/0

# Scraping
SCRAPING_ENABLED=true
MAX_CONCURRENT_REQUESTS=5
REQUEST_TIMEOUT=30

# Optional LLM assistant
GROQ_API_KEY=
LLM_MODEL=llama-3.3-70b-versatile

# Frontend
VITE_API_URL=http://127.0.0.1:8000/api
```

### Database Migrations

Canonical application data models live in `web_app/backend/db/` and are managed by Alembic:

```bash
# Apply migrations locally using DATABASE_URL
make db-migrate

# Roll back one migration locally
make db-rollback

# Apply migrations inside Docker
make docker-db-migrate
```

Tracking API endpoints now require a bearer token and use the canonical user-owned `tracked_products`, `product_snapshots`, and `alerts` tables. Existing legacy SQLite tracking data is not imported automatically. After applying the canonical schema migration, import it explicitly into a disabled audit account with:

```bash
make db-migrate
make db-migrate-legacy-tracking
```

The importer reads `TRACKING_DATABASE_URL`, writes to `DATABASE_URL`, and defaults to the disabled owner `legacy-tracking@local.invalid`. Use `python scripts/migrate_legacy_tracking.py --owner-email your-address@example.com` only when you have deliberately prepared that ownership policy.

## 📈 Performance

- **Caching**: Redis-backed with configurable TTL
- **Rate Limiting**: Distributed across instances
- **Connection Pooling**: PostgreSQL and Redis
- **Async Operations**: FastAPI async endpoints
- **Compression**: GZip middleware

## ⚠️ Legal Disclaimer

**Important**: This tool scrapes Amazon.com which may violate their Terms of Service. Use at your own risk.

**Recommended Alternatives**:
- Amazon Product Advertising API (PA-API 5.0)
- Amazon Selling Partner API (SP-API)
- Third-party data providers (Keepa, Jungle Scout)

## 🛠️ Development

### Code Quality
```bash
# Lint code
make lint

# Format code
make format

# Clean cache
make clean
```

### Adding Features
1. Create feature branch
2. Add tests in `tests/`
3. Update documentation
4. Submit PR

## 📦 Deployment

### Production Checklist
- [ ] Set strong `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Configure `ALLOWED_ORIGINS` with actual domains
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure SSL/TLS certificates in Nginx
- [ ] Set up monitoring (Sentry, Prometheus)
- [ ] Configure backup strategy for PostgreSQL
- [ ] Set up log aggregation (ELK, Datadog)
- [ ] Configure firewall rules
- [ ] Set up CI/CD pipeline

### Kubernetes Deployment
```bash
# Apply manifests (create these based on your needs)
kubectl apply -f k8s/

# Check status
kubectl get pods
kubectl get services
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is for educational purposes only. Use responsibly and at your own risk.

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: `/docs` endpoint when running
- **Health Check**: `/health` endpoint

## 🎯 Roadmap

- [ ] Amazon PA-API integration
- [ ] WebSocket support for real-time updates
- [ ] Advanced analytics dashboard
- [ ] Machine learning price predictions
- [ ] Multi-marketplace comparison
- [ ] Automated report generation
- [ ] Mobile app

---

**Built with** ❤️ **for Amazon sellers**
