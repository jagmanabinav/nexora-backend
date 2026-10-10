# Nexora Backend

FastAPI-based multi-tenant SaaS platform backend for fabric washing factory management.

## 📋 Overview

A production-ready FastAPI backend with:
- ✅ **58 REST API Endpoints** (5 modules)
- ✅ **Role-Based Access Control (RBAC)**
- ✅ **Multi-Tenant Architecture**
- ✅ **JWT Authentication**
- ✅ **PostgreSQL Database**
- ✅ **Redis Caching**
- ✅ **Comprehensive Testing Suite**
- ✅ **Docker Support**
- ✅ **OpenAPI Documentation**

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 13+
- Redis 6+
- Docker & Docker Compose (optional)

### Installation

**Option 1: Docker (Recommended)**
```bash
docker-compose up -d
```

**Option 2: Local Setup**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend
python -m uvicorn app.main:app --reload
```

### Access Points
- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **ReDoc Docs**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 📁 Project Structure

```
nexora-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py              # Authentication endpoints
│   │       ├── rbac.py              # RBAC endpoints
│   │       ├── applications.py      # Application management
│   │       ├── billing.py           # Billing & subscriptions
│   │       ├── advanced.py          # Webhooks, audit logs, exports
│   │       └── router.py            # Route aggregation
│   ├── models/
│   │   ├── user.py
│   │   ├── tenant.py
│   │   ├── role.py
│   │   ├── permission.py
│   │   ├── application.py
│   │   ├── subscription.py
│   │   └── ...
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── rbac.py
│   │   └── ...
│   ├── services/
│   │   ├── authentication.py
│   │   ├── role.py
│   │   └── ...
│   ├── repositories/
│   │   ├── user.py
│   │   ├── role.py
│   │   └── ...
│   ├── core/
│   │   ├── config.py               # Configuration
│   │   ├── security.py             # Security utilities
│   │   ├── dependencies.py         # FastAPI dependencies
│   │   └── exceptions.py           # Custom exceptions
│   ├── middleware/
│   │   ├── error_handler.py        # Error handling
│   │   └── logging.py              # Structured logging
│   ├── database/
│   │   └── connection.py           # Database connection
│   └── main.py                     # FastAPI app initialization
├── tests/
│   ├── conftest.py                # Isolated test database and API fixtures
│   └── test_api.py                # API integration tests
├── scripts/
│   ├── seed_data.py               # Initial data seeding
│   └── ...
├── TESTING_GUIDE.md               # Complete testing documentation
├── DEPLOYMENT_GUIDE.md            # Production deployment
├── API_REFERENCE.md               # Endpoint reference
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── README.md (this file)
```

## 🔐 API Endpoints

### Authentication (5)
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Current user info

### RBAC (8)
- `GET /api/v1/roles` - List roles
- `POST /api/v1/roles` - Create role
- `GET /api/v1/permissions` - List permissions
- `POST /api/v1/roles/{role_id}/permissions` - Assign permission
- And more...

### Applications (12)
- `GET/POST /api/v1/applications` - Manage applications
- `POST /api/v1/applications/{app_id}/api-keys` - Generate API keys
- `POST /api/v1/applications/{app_id}/oauth-providers` - OAuth setup
- And more...

### Billing (20)
- `GET/POST /api/v1/plans` - Manage billing plans
- `GET/POST /api/v1/subscriptions` - Manage subscriptions
- `GET /api/v1/invoices` - View invoices
- `POST /api/v1/usage/track` - Track usage metrics
- And more...

### Advanced (13)
- `POST /api/v1/webhooks` - Create webhooks
- `GET /api/v1/audit-logs` - View audit logs
- `POST /api/v1/data-exports` - Export data
- And more...

**See [API_REFERENCE.md](./API_REFERENCE.md) for complete documentation**

## 🧪 Testing

### Automated Test Suite
```bash
# Run the API integration suite
python -m pytest

# Run a focused test group
python -m pytest tests/test_api.py -k authentication
```

### Manual Testing with cURL
```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@nexora.io",
    "password": "Test@12345",
    "first_name": "Test",
    "last_name": "User",
    "tenant_name": "Test Company",
    "tenant_slug": "test-company"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@nexora.io", "password": "Test@12345"}'
```

**See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for comprehensive testing documentation**

## 🗄️ Database

### Schema
- **21 tables** with proper relationships
- UUID primary keys
- Tenant-scoped data isolation
- Audit trail support
- Cascade deletes configured

### Initial Setup
```bash
# Run migrations
alembic upgrade head

# Seed test data
python scripts/seed_data.py
```

## 🔒 Authentication & Authorization

### JWT Tokens
- Access tokens: 15 minutes expiry
- Refresh tokens: 30 days expiry
- Token stored in Authorization header: `Bearer {token}`

### Roles
1. **Super Admin** - Full platform access
2. **Tenant Admin** - Tenant-scoped access
3. **Application Manager** - Application management
4. **Billing Manager** - Billing operations
5. **Regular User** - Limited read-only access

## 📊 Database Models

- **Users** - User accounts with authentication
- **Tenants** - Multi-tenant isolation
- **Roles** - RBAC roles
- **Permissions** - Granular permissions
- **Applications** - Third-party applications
- **Subscriptions** - Billing subscriptions
- **Invoices** - Invoice management
- **Plans** - Billing plans
- **API Keys** - Application API keys
- **Webhooks** - Event webhooks
- **Audit Logs** - Audit trail
- **Usage Records** - Usage tracking
- **And more...**

## ⚙️ Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/nexora_db

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# API
API_V1_PREFIX=/api/v1
LOG_LEVEL=INFO
```

See `.env.example` for all available variables.

## 🐳 Docker

### Build
```bash
docker build -t nexora-backend .
```

### Run
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  nexora-backend
```

### Docker Compose
```bash
docker-compose up
```

## 📝 Logging & Monitoring

- **Structured JSON logging** with timestamps
- **Request/Response tracking** with unique request IDs
- **Error tracking** with full stack traces
- **Performance metrics** (response times)
- **Audit logs** for security compliance

## 🚨 Error Handling

Standard HTTP status codes:
- `200` - OK
- `201` - Created
- `204` - No Content
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `422` - Validation Error
- `500` - Internal Server Error

All errors return JSON response:
```json
{
  "detail": "Error message",
  "status_code": 422,
  "validation_errors": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

## 🔧 Development

### Code Style
- PEP 8 compliant
- Type hints throughout
- Docstrings for all functions
- Black formatter (88 char lines)

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Running Locally
```bash
# Watch mode with auto-reload
python -m uvicorn app.main:app --reload

# Production mode
python -m uvicorn app.main:app --workers 4
```

## 📦 Dependencies

- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **Pydantic** - Data validation
- **Python-jose** - JWT handling
- **Passlib** - Password hashing
- **PostgreSQL** - Database driver
- **Redis** - Caching
- **Pytest** - Testing
- **See requirements.txt for full list**

## 🚀 Deployment

### Production Deployment
```bash
# Build image
docker build -t nexora-backend:latest .

# Push to registry
docker tag nexora-backend:latest registry.example.com/nexora-backend:latest
docker push registry.example.com/nexora-backend:latest

# Deploy to Kubernetes/Docker Swarm/etc
```

**See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for detailed deployment instructions**

## 📞 Support & Documentation

- **API Reference**: [API_REFERENCE.md](./API_REFERENCE.md)
- **Testing Guide**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)
- **Deployment**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **Local Setup**: See the [README.md](./README.md#local-quick-start)
- **OpenAPI Docs**: http://localhost:8000/docs

## 📄 License

Proprietary - Nexora

## 👥 Development Team

Backend Service for Nexora SaaS Platform

---

**Status**: Production Ready ✅
**Last Updated**: October 3, 2026
**Version**: 1.0.0
