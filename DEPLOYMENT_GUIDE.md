# Nexora Core - Deployment Guide

**Complete guide for deploying Nexora to production environments.**

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Code & Testing

- [ ] All tests passing (`pytest`)
- [ ] Code coverage ≥85%
- [ ] No critical security issues
- [ ] Dependencies updated
- [ ] Migrations tested locally

### Configuration

- [ ] JWT_SECRET generated (32+ chars)
- [ ] ENCRYPTION_KEY generated (Fernet format)
- [ ] ENVIRONMENT set to production
- [ ] DEBUG set to false
- [ ] Database URL verified
- [ ] Redis URL verified
- [ ] CORS_ORIGINS configured

### Security

- [ ] SSL/TLS certificates obtained
- [ ] Rate limiting configured
- [ ] CORS headers set
- [ ] Security headers configured
- [ ] API keys and secrets managed
- [ ] Audit logging enabled
- [ ] Monitoring configured
- [ ] Alerting setup

### Infrastructure

- [ ] PostgreSQL 14+ installed
- [ ] Redis 7+ installed
- [ ] Nginx/reverse proxy configured
- [ ] Load balancer configured
- [ ] Backup strategy implemented
- [ ] Disaster recovery plan documented

### Operations

- [ ] On-call team briefed
- [ ] Incident response plan ready
- [ ] Rollback procedure documented
- [ ] Monitoring dashboards created
- [ ] Log aggregation setup
- [ ] Health checks configured

---

## Local Development

### Quick Setup

```bash
# 1. Install dependencies
cd nexora/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Set environment variables
export DATABASE_URL=postgresql://localhost/nexora_dev
export REDIS_URL=redis://localhost:6379/0
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export ENVIRONMENT=development

# 3. Initialize database
alembic upgrade head

# 4. Run tests
pytest

# 5. Start development server
uvicorn app.main:app --reload
```

### Database Setup

```bash
# Create database
createdb nexora_dev

# Run migrations
alembic upgrade head

# Verify tables created
psql -d nexora_dev -c "\dt"
```

### Seeding Initial Data

```bash
# Create admin user and roles
python -c "from app.services.seed import seed_database; seed_database()"
```

---

## Docker Deployment

### Build Image

```bash
# Build for development
docker build -t nexora:dev .

# Build for production
docker build -t nexora:1.0.0 .

# Push to registry
docker tag nexora:1.0.0 docker.io/yourorg/nexora:1.0.0
docker push docker.io/yourorg/nexora:1.0.0
```

### Run Container

```bash
# Generate secrets first
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Run container
docker run -d \
  --name nexora-api \
  -e ENVIRONMENT=production \
  -e DATABASE_URL=postgresql://user:pass@db-host:5432/nexora \
  -e REDIS_URL=redis://redis-host:6379/0 \
  -e JWT_SECRET=$JWT_SECRET \
  -e ENCRYPTION_KEY=$ENCRYPTION_KEY \
  -e CORS_ORIGINS=https://app.example.com \
  -p 8000:8000 \
  nexora:1.0.0

# Check logs
docker logs -f nexora-api

# Stop container
docker stop nexora-api
```

### Docker Compose (Multi-Service)

```bash
# Copy example compose file
cp docker-compose.example.yml docker-compose.yml

# Edit with your configuration
nano docker-compose.yml

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f nexora-api

# Stop services
docker-compose down
```

**docker-compose.yml** structure:

```yaml
services:
  nexora-api:
    image: nexora:1.0.0
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://nexora:password@postgres:5432/nexora
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET: ${JWT_SECRET}
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: nexora
      POSTGRES_USER: nexora
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nexora"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

---

## Production Deployment

### Environment Setup

```bash
# Generate secure secrets
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Store in environment or secrets manager
export JWT_SECRET=$JWT_SECRET
export ENCRYPTION_KEY=$ENCRYPTION_KEY
export ENVIRONMENT=production
export DEBUG=false
export DATABASE_URL=postgresql://prod_user:${DB_PASSWORD}@prod-db.example.com:5432/nexora
export REDIS_URL=redis://prod-redis.example.com:6379/0
export CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

### Database Initialization

```bash
# Create database (if not exists)
createdb nexora_prod

# Run migrations
ENVIRONMENT=production alembic upgrade head

# Verify schema
psql $DATABASE_URL -c "\dt"
```

### Application Startup

**Option 1: Gunicorn (Recommended)**

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

**Option 2: Uvicorn with Supervisor**

```bash
# Create supervisor config
cat > /etc/supervisor/conf.d/nexora.conf << EOF
[program:nexora]
command=/opt/nexora/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
directory=/opt/nexora/backend
user=nexora
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/nexora/nexora.log
EOF

# Start service
supervisorctl reread
supervisorctl update
supervisorctl start nexora
```

### Nginx Configuration

```nginx
upstream nexora_backend {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/api.example.com.crt;
    ssl_certificate_key /etc/ssl/private/api.example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=100 nodelay;

    # Proxy Configuration
    location / {
        proxy_pass http://nexora_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
    }

    # Health Check Endpoint
    location /health {
        access_log off;
        proxy_pass http://nexora_backend;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}
```

### SSL/TLS Certificate Setup

```bash
# Using Let's Encrypt with Certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --nginx -d api.example.com

# Auto-renew
sudo certbot renew --dry-run
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Docker image pushed to registry

### Namespace Setup

```bash
kubectl create namespace nexora
kubectl config set-context --current --namespace=nexora
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nexora-config
  namespace: nexora
data:
  ENVIRONMENT: production
  DEBUG: "false"
  JWT_ALGORITHM: "HS256"
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES: "15"
  LOG_LEVEL: "INFO"
  CORS_ORIGINS: "https://app.example.com,https://admin.example.com"
```

### Secrets

```bash
# Generate secrets
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Create secret
kubectl create secret generic nexora-secrets \
  --from-literal=JWT_SECRET=$JWT_SECRET \
  --from-literal=ENCRYPTION_KEY=$ENCRYPTION_KEY \
  --from-literal=DATABASE_URL=postgresql://... \
  --from-literal=REDIS_URL=redis://... \
  -n nexora
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexora-api
  namespace: nexora
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nexora-api
  template:
    metadata:
      labels:
        app: nexora-api
    spec:
      containers:
      - name: nexora-api
        image: docker.io/yourorg/nexora:1.0.0
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: nexora-config
        - secretRef:
            name: nexora-secrets
        livenessProbe:
          httpGet:
            path: /live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nexora-api
  namespace: nexora
spec:
  selector:
    app: nexora-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Check status
kubectl get pods -n nexora
kubectl get svc -n nexora

# Scale deployment
kubectl scale deployment/nexora-api --replicas=5 -n nexora

# View logs
kubectl logs -f deployment/nexora-api -n nexora
```

---

## Post-Deployment Verification

### Health Checks

```bash
# API health
curl https://api.example.com/health
# Response: {"status": "healthy"}

# Readiness probe
curl https://api.example.com/ready
# Response: {"status": "ready"}

# Database connection
curl -H "Authorization: Bearer $TOKEN" https://api.example.com/api/v1/users
# Response: {"total": 0, "items": []}
```

### Database Verification

```bash
# Connect to database
psql $DATABASE_URL

# Check tables
\dt

# Check data
SELECT COUNT(*) FROM tenants;
SELECT COUNT(*) FROM users;

# Exit
\q
```

### Performance Testing

```bash
# Install load testing tool
pip install locust

# Run load test
locust -f load_test.py -u 100 -r 10 -t 5m -H https://api.example.com
```

### Security Verification

```bash
# Check security headers
curl -I https://api.example.com
# Verify Strict-Transport-Security, X-Content-Type-Options, etc.

# Test rate limiting
for i in {1..150}; do curl https://api.example.com/health; done

# Verify SSL/TLS
openssl s_client -connect api.example.com:443 -tls1_2
```

### Monitoring Setup

```bash
# Health check endpoint for load balancer
https://api.example.com/health

# Metrics endpoint for Prometheus
https://api.example.com/metrics

# Structured logs (check ELK/Datadog)
tail -f /var/log/nexora/nexora.log | jq .
```

---

## Troubleshooting

### Common Issues

**Issue: JWT_SECRET not set**
```
Error: JWT_SECRET must be set
Solution:
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

**Issue: Database connection timeout**
```
Error: could not connect to server
Solution:
1. Verify DATABASE_URL is correct
2. Check PostgreSQL is running
3. Check firewall rules
4. Verify network connectivity
psql $DATABASE_URL -c "SELECT 1;"
```

**Issue: Migrations fail**
```
Error: FAILED [alembic.command] Can't locate revision
Solution:
# Check migration status
alembic current
# Upgrade to head
alembic upgrade head
```

**Issue: High memory usage**
```
Solution:
1. Check for connection leaks: SELECT count(*) FROM pg_stat_activity;
2. Monitor cache size: redis-cli INFO memory
3. Restart application
4. Check for query issues: EXPLAIN ANALYZE
```

**Issue: Slow API responses**
```
Solution:
1. Check database query performance: EXPLAIN ANALYZE
2. Verify indexes exist: SELECT * FROM pg_indexes;
3. Check Redis connectivity: redis-cli ping
4. Review application logs: tail -f /var/log/nexora/nexora.log
```

### Rollback Procedure

```bash
# 1. Stop current deployment
kubectl set image deployment/nexora-api nexora-api=nexora:1.0.0-previous -n nexora

# 2. Verify rollback
kubectl get pods -n nexora

# 3. Check logs
kubectl logs -f deployment/nexora-api -n nexora

# 4. Verify health
curl https://api.example.com/health
```

### Recovery Procedures

**Database Corruption**
```bash
# Stop application
docker stop nexora-api

# Restore from backup
pg_restore -d nexora_prod backup.sql

# Restart application
docker start nexora-api
```

**Redis Connection Loss**
```bash
# Check Redis status
redis-cli ping

# Restart Redis
docker restart nexora-redis

# Verify connection
redis-cli INFO server
```

**Disk Space Issues**
```bash
# Check disk usage
df -h

# Clean logs if necessary
find /var/log/nexora -type f -mtime +30 -delete

# Vacuum database
psql $DATABASE_URL -c "VACUUM ANALYZE;"
```

---

## Monitoring & Alerts

### Key Metrics to Monitor

- **API Response Time**: P99 should be <500ms
- **Error Rate**: Should be <0.1%
- **Database Connections**: Monitor pool usage
- **Redis Memory**: Should not exceed limits
- **CPU Usage**: Should stay <80%
- **Memory Usage**: Should stay <70%
- **Disk Space**: Alert at 80% full

### Recommended Monitoring Stack

- **Metrics**: Prometheus + Grafana
- **Logs**: ELK Stack or Datadog
- **Tracing**: Jaeger
- **Alerting**: AlertManager
- **Error Tracking**: Sentry

### Health Check Endpoints

```
GET /health          - Basic health check
GET /ready           - Readiness probe (Kubernetes)
GET /live            - Liveness probe (Kubernetes)
GET /metrics         - Prometheus metrics
```

---

## Maintenance

### Regular Tasks

**Daily**:
- Monitor application logs
- Check error rates
- Verify backups completed

**Weekly**:
- Review performance metrics
- Check security alerts
- Update dependencies

**Monthly**:
- Security audit
- Performance analysis
- Capacity planning

### Backup Strategy

```bash
# Daily database backup
0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/nexora_$(date +\%Y\%m\%d).sql.gz

# Store in secure location
# AWS S3, Azure Blob Storage, or on-premises

# Test restore procedure monthly
pg_restore -d nexora_test /backups/nexora_latest.sql.gz
```

### Update Procedure

```bash
# 1. Tag new version
git tag v1.0.1
git push --tags

# 2. Build and test
docker build -t nexora:1.0.1 .
pytest

# 3. Push to registry
docker push docker.io/yourorg/nexora:1.0.1

# 4. Update deployment
kubectl set image deployment/nexora-api \
  nexora-api=docker.io/yourorg/nexora:1.0.1 -n nexora

# 5. Monitor rollout
kubectl rollout status deployment/nexora-api -n nexora

# 6. Verify
curl https://api.example.com/health
```

---

**Deployment Guide Complete**

For additional support, see:
- [README.md](./README.md) - Main documentation
- [PHASE10_RELEASE.md](./PHASE10_RELEASE.md) - Complete release guide
- [API_REFERENCE.md](./API_REFERENCE.md) - API documentation
