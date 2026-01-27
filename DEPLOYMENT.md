# Deployment Guide 🚀

Complete guide for deploying Amazon Hunter Pro to production.

## Pre-Deployment Checklist

### 1. Security Configuration ✅

```bash
# Generate strong secrets (32+ characters)
openssl rand -base64 32  # For SECRET_KEY
openssl rand -base64 32  # For JWT_SECRET_KEY

# Update .env file
SECRET_KEY=<generated-secret>
JWT_SECRET_KEY=<generated-jwt-secret>
ENVIRONMENT=production
DEBUG=false
```

### 2. Database Setup ✅

```bash
# PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/amazon_hunter

# Run migrations (if using Alembic)
alembic upgrade head
```

### 3. Redis Configuration ✅

```bash
# Production Redis with password
REDIS_URL=redis://:password@host:6379/0

# Or use Redis Cluster for high availability
```

### 4. CORS Configuration ✅

```bash
# Set actual domains
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 5. Rate Limiting ✅

```bash
# Adjust based on your needs
RATE_LIMIT_PER_MINUTE=20
RATE_LIMIT_PER_HOUR=500
```

## Deployment Options

### Option 1: Docker Compose (Simple)

Best for: Small to medium deployments, single server

```bash
# 1. Clone repository
git clone <repo>
cd amazon_hunter

# 2. Configure environment
cp .env.example .env
nano .env  # Edit with production values

# 3. Build and start
docker-compose -f docker-compose.prod.yml up -d

# 4. Check health
curl http://localhost/health
```

### Option 2: Kubernetes (Scalable)

Best for: Large deployments, high availability

#### Prerequisites
- Kubernetes cluster (EKS, GKE, AKS, or self-hosted)
- kubectl configured
- Helm (optional but recommended)

#### Steps

1. **Create Namespace**
```bash
kubectl create namespace amazon-hunter
```

2. **Create Secrets**
```bash
kubectl create secret generic amazon-hunter-secrets \
  --from-literal=SECRET_KEY=<your-secret> \
  --from-literal=JWT_SECRET_KEY=<your-jwt-secret> \
  --from-literal=REDIS_PASSWORD=<redis-password> \
  --from-literal=POSTGRES_PASSWORD=<postgres-password> \
  -n amazon-hunter
```

3. **Deploy PostgreSQL**
```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: amazon-hunter
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: amazon_hunter
        - name: POSTGRES_USER
          value: amazon_hunter
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: amazon-hunter-secrets
              key: POSTGRES_PASSWORD
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 20Gi
```

4. **Deploy Redis**
```yaml
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: amazon-hunter
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server", "--requirepass", "$(REDIS_PASSWORD)"]
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: amazon-hunter-secrets
              key: REDIS_PASSWORD
        ports:
        - containerPort: 6379
```

5. **Deploy API**
```yaml
# k8s/api.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: amazon-hunter
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: your-registry/amazon-hunter:latest
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: amazon-hunter-secrets
              key: SECRET_KEY
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: amazon-hunter-secrets
              key: JWT_SECRET_KEY
        - name: DATABASE_URL
          value: "postgresql://amazon_hunter:$(POSTGRES_PASSWORD)@postgres:5432/amazon_hunter"
        - name: REDIS_URL
          value: "redis://:$(REDIS_PASSWORD)@redis:6379/0"
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

6. **Deploy Ingress**
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: amazon-hunter
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "20"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: api-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api
            port:
              number: 8000
```

7. **Apply Manifests**
```bash
kubectl apply -f k8s/
```

### Option 3: Cloud Platforms

#### AWS (ECS/Fargate)

1. **Build and Push Image**
```bash
# Build
docker build -t amazon-hunter .

# Tag
docker tag amazon-hunter:latest <account-id>.dkr.ecr.<region>.amazonaws.com/amazon-hunter:latest

# Push to ECR
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/amazon-hunter:latest
```

2. **Create ECS Task Definition**
```json
{
  "family": "amazon-hunter",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "<account-id>.dkr.ecr.<region>.amazonaws.com/amazon-hunter:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"}
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:amazon-hunter/SECRET_KEY"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/amazon-hunter",
          "awslogs-region": "<region>",
          "awslogs-stream-prefix": "api"
        }
      }
    }
  ]
}
```

3. **Create ECS Service**
```bash
aws ecs create-service \
  --cluster amazon-hunter-cluster \
  --service-name api \
  --task-definition amazon-hunter \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

#### Google Cloud (Cloud Run)

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/<project-id>/amazon-hunter
gcloud run deploy amazon-hunter \
  --image gcr.io/<project-id>/amazon-hunter \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets SECRET_KEY=amazon-hunter-secret:latest
```

## Post-Deployment

### 1. Monitoring Setup

#### Sentry (Error Tracking)
```bash
# Add to .env
SENTRY_DSN=https://xxx@sentry.io/xxx
```

#### Prometheus + Grafana
```bash
# Add metrics endpoint
# Already available at /metrics

# Configure Prometheus scraping
# Configure Grafana dashboards
```

### 2. SSL/TLS Configuration

#### Let's Encrypt (Free)
```bash
# Using Certbot
certbot --nginx -d api.yourdomain.com

# Or use cert-manager in Kubernetes
```

### 3. Backup Strategy

#### PostgreSQL Backups
```bash
# Daily backups
0 2 * * * pg_dump -U amazon_hunter amazon_hunter > /backups/db_$(date +\%Y\%m\%d).sql

# Or use AWS RDS automated backups
```

#### Redis Persistence
```bash
# Enable AOF in redis.conf
appendonly yes
appendfsync everysec
```

### 4. Log Aggregation

#### ELK Stack
```bash
# Configure Filebeat to ship logs
# Set up Elasticsearch and Kibana
```

#### CloudWatch (AWS)
```bash
# Already configured in ECS task definition
# View logs in CloudWatch Logs
```

### 5. Performance Tuning

#### Nginx
```nginx
# Increase worker connections
worker_connections 2048;

# Enable caching
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;
```

#### PostgreSQL
```sql
-- Increase connection pool
max_connections = 200

-- Tune memory
shared_buffers = 256MB
effective_cache_size = 1GB
```

#### Redis
```bash
# Increase max memory
maxmemory 2gb
maxmemory-policy allkeys-lru
```

## Scaling

### Horizontal Scaling
```bash
# Kubernetes
kubectl scale deployment api --replicas=10 -n amazon-hunter

# Docker Compose
docker-compose up -d --scale api=5
```

### Vertical Scaling
```bash
# Increase resources in deployment
resources:
  requests:
    memory: "2Gi"
    cpu: "2000m"
```

### Database Scaling
- Read replicas for PostgreSQL
- Redis Cluster for distributed caching
- Connection pooling (PgBouncer)

## Troubleshooting

### Check Logs
```bash
# Docker
docker-compose logs -f api

# Kubernetes
kubectl logs -f deployment/api -n amazon-hunter

# Follow specific pod
kubectl logs -f pod/<pod-name> -n amazon-hunter
```

### Health Check
```bash
curl http://your-domain/health
curl http://your-domain/ready
```

### Database Connection
```bash
# Test PostgreSQL
psql -h host -U user -d amazon_hunter

# Test Redis
redis-cli -h host -a password ping
```

### Performance Issues
```bash
# Check metrics
curl http://your-domain/metrics

# Monitor resources
kubectl top pods -n amazon-hunter
```

## Rollback

### Docker Compose
```bash
# Pull previous image
docker-compose pull
docker-compose up -d
```

### Kubernetes
```bash
# Rollback to previous version
kubectl rollout undo deployment/api -n amazon-hunter

# Rollback to specific revision
kubectl rollout undo deployment/api --to-revision=2 -n amazon-hunter
```

## Security Hardening

1. **Enable HTTPS only**
2. **Set up WAF (Web Application Firewall)**
3. **Configure DDoS protection**
4. **Regular security updates**
5. **Implement API authentication**
6. **Set up intrusion detection**
7. **Regular security audits**

## Maintenance

### Regular Tasks
- [ ] Weekly: Review logs for errors
- [ ] Weekly: Check disk space
- [ ] Monthly: Update dependencies
- [ ] Monthly: Review security advisories
- [ ] Quarterly: Load testing
- [ ] Quarterly: Disaster recovery drill

---

**Need Help?** Check the main README or open an issue.
