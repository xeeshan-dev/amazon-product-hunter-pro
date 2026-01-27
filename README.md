# Amazon Hunter Pro 🚀

Production-grade Amazon FBA product research platform with advanced analytics, risk detection, and market intelligence.

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

# Run development server
make dev
```

## 📚 API Documentation

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

### Get Product Details
```bash
GET /api/product/{asin}
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

# Run with coverage
make test-cov

# Run specific test
pytest tests/test_api.py -v
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
REDIS_URL=redis://host:6379/0

# Scraping
SCRAPING_ENABLED=true
MAX_CONCURRENT_REQUESTS=5
REQUEST_TIMEOUT=30
```

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
