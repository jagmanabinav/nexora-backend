# Nexora Backend - Comprehensive Testing Guide

## Overview

This guide covers complete testing of the Nexora Backend FastAPI service with:
- **58 API Endpoints** across 5 modules
- **Role-Based Access Control (RBAC)**
- **Full Test Data Setup**
- **Automated Test Suite**
- **Manual Testing Scripts**

---

## API Modules & Endpoints

### 1. Authentication Module (5 endpoints)
**Prefix:** `/api/v1/auth`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/register` | Register new user and create tenant |
| POST | `/login` | Authenticate user and get tokens |
| POST | `/refresh` | Refresh access token using refresh token |
| POST | `/logout` | Logout user and revoke tokens |
| GET | `/me` | Get current authenticated user info |

### 2. RBAC Module (8 endpoints)
**Prefix:** `/api/v1`

| Method | Endpoint | Purpose | Required Role |
|--------|----------|---------|----------------|
| GET | `/roles` | List all roles | Admin |
| POST | `/roles` | Create new role | Admin |
| GET | `/roles/{role_id}` | Get role details | Admin |
| PUT | `/roles/{role_id}` | Update role | Admin |
| DELETE | `/roles/{role_id}` | Delete role | Admin |
| GET | `/permissions` | List all permissions | Admin |
| POST | `/roles/{role_id}/permissions` | Assign permission to role | Admin |
| DELETE | `/roles/{role_id}/permissions/{permission_id}` | Remove permission from role | Admin |

### 3. Applications Module (12 endpoints)
**Prefix:** `/api/v1`

| Method | Endpoint | Purpose | Required Role |
|--------|----------|---------|----------------|
| GET | `/applications` | List all applications | Admin |
| POST | `/applications` | Create new application | Admin |
| GET | `/applications/{app_id}` | Get application details | Admin |
| PUT | `/applications/{app_id}` | Update application | Admin |
| DELETE | `/applications/{app_id}` | Delete application | Admin |
| POST | `/applications/{app_id}/activate` | Activate application | Admin |
| POST | `/applications/{app_id}/suspend` | Suspend application | Admin |
| GET | `/applications/{app_id}/api-keys` | List API keys for app | Admin |
| POST | `/applications/{app_id}/api-keys` | Generate API key | Admin |
| DELETE | `/api-keys/{key_id}` | Revoke API key | Admin |
| GET | `/applications/{app_id}/oauth-providers` | List OAuth providers | Admin |
| POST | `/applications/{app_id}/oauth-providers` | Add OAuth provider | Admin |

### 4. Billing Module (20 endpoints)
**Prefix:** `/api/v1`

| Method | Endpoint | Purpose | Required Role |
|--------|----------|---------|----------------|
| GET | `/plans` | List billing plans | Public/Authenticated |
| GET | `/plans/{plan_id}` | Get plan details | Public/Authenticated |
| POST | `/plans` | Create billing plan | Billing Admin |
| PUT | `/plans/{plan_id}` | Update billing plan | Billing Admin |
| POST | `/subscriptions` | Create subscription | Tenant Admin |
| GET | `/subscriptions` | Get tenant subscription | Tenant Admin |
| PUT | `/subscriptions` | Update subscription | Tenant Admin |
| POST | `/subscriptions/upgrade` | Upgrade subscription | Tenant Admin |
| POST | `/subscriptions/downgrade` | Downgrade subscription | Tenant Admin |
| POST | `/subscriptions/cancel` | Cancel subscription | Tenant Admin |
| GET | `/invoices` | List invoices | Tenant Admin |
| GET | `/invoices/{invoice_id}` | Get invoice details | Tenant Admin |
| POST | `/invoices/{invoice_id}/payment` | Process payment | Tenant Admin |
| POST | `/invoices/{invoice_id}/retry` | Retry failed payment | Tenant Admin |
| GET | `/usage` | Get current usage metrics | Authenticated |
| POST | `/usage/track` | Track usage | Application |
| GET | `/usage/limits` | Get usage limits | Authenticated |
| GET | `/billing/overview` | Get billing overview | Tenant Admin |
| GET | `/payment-methods` | List payment methods | Tenant Admin |
| POST | `/payment-methods/{method_id}/default` | Set default payment method | Tenant Admin |

### 5. Advanced Module (13 endpoints)
**Prefix:** `/api/v1`

| Method | Endpoint | Purpose | Required Role |
|--------|----------|---------|----------------|
| POST | `/webhooks` | Create webhook endpoint | Admin |
| GET | `/webhooks` | List webhooks | Admin |
| GET | `/webhooks/{endpoint_id}` | Get webhook details | Admin |
| PUT | `/webhooks/{endpoint_id}` | Update webhook | Admin |
| DELETE | `/webhooks/{endpoint_id}` | Delete webhook | Admin |
| GET | `/webhooks/{endpoint_id}/deliveries` | Get webhook deliveries | Admin |
| GET | `/audit-logs` | List audit logs | Admin |
| GET | `/audit-logs/{audit_id}` | Get audit log details | Admin |
| POST | `/data-exports` | Create data export | Tenant Admin |
| GET | `/data-exports` | List data exports | Tenant Admin |
| GET | `/data-exports/{export_id}` | Get export details | Tenant Admin |
| GET | `/data-exports/{export_id}/download-url` | Get download URL | Tenant Admin |
| DELETE | `/data-exports/{export_id}` | Delete export | Tenant Admin |

---

## Test User Roles

### Role Hierarchy

```
Super Admin (Full Access)
├── Tenant Admin (Tenant-scoped)
├── Application Manager (Apps & API Keys)
├── Billing Manager (Billing & Invoices)
└── Regular User (Read-only, Limited Access)
```

### Test Credentials

Create these users for testing:

| Role | Email | Password | Permissions |
|------|-------|----------|-------------|
| Super Admin | `superadmin@nexora.io` | `SuperAdmin@12345` | All endpoints |
| Tenant Admin | `tenant-admin@nexora.io` | `TenantAdmin@12345` | Tenant management, billing |
| App Manager | `app-manager@nexora.io` | `AppManager@12345` | Applications, API keys |
| Billing Manager | `billing-manager@nexora.io` | `BillingMgr@12345` | Plans, subscriptions, invoices |
| Regular User | `user@nexora.io` | `User@12345` | Limited read-only |

---

## Quick Start Testing

### 1. Start Backend Services

```bash
# Using Docker Compose
docker-compose up -d

# Or standalone
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Backend runs on: `http://localhost:8000`
API Docs: `http://localhost:8000/docs`
Admin Docs: `http://localhost:8000/admin/docs`

### 2. Run Automated Tests

```bash
# Run comprehensive test suite
python tests/automated/test_all_endpoints.py

# Run specific module tests
python tests/automated/test_auth.py
python tests/automated/test_rbac.py
python tests/automated/test_applications.py
python tests/automated/test_billing.py
python tests/automated/test_advanced.py

# Run with pytest
pytest tests/ -v --tb=short
```

### 3. Manual Testing with cURL

#### Authentication Tests

```bash
# Register new user
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
  -d '{
    "email": "test@nexora.io",
    "password": "Test@12345"
  }'

# Get current user (use token from login)
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Logout
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### RBAC Tests

```bash
# List permissions
curl -X GET http://localhost:8000/api/v1/permissions \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Create role
curl -X POST http://localhost:8000/api/v1/roles \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Custom Role",
    "description": "Description of custom role"
  }'

# Assign permission to role
curl -X POST http://localhost:8000/api/v1/roles/{role_id}/permissions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "permission_id": "PERMISSION_ID"
  }'
```

#### Application Tests

```bash
# List applications
curl -X GET http://localhost:8000/api/v1/applications \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Create application
curl -X POST http://localhost:8000/api/v1/applications \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "My App",
    "description": "My application",
    "website_url": "https://example.com"
  }'

# Get application details
curl -X GET http://localhost:8000/api/v1/applications/{app_id} \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Generate API key
curl -X POST http://localhost:8000/api/v1/applications/{app_id}/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"name": "Test Key"}'
```

#### Billing Tests

```bash
# List plans
curl -X GET http://localhost:8000/api/v1/plans \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Create plan
curl -X POST http://localhost:8000/api/v1/plans \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Premium Plan",
    "price": 99.99,
    "currency": "USD",
    "billing_period": "monthly",
    "features": ["Feature1", "Feature2"]
  }'

# Create subscription
curl -X POST http://localhost:8000/api/v1/subscriptions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "plan_id": "PLAN_ID"
  }'

# Get subscription
curl -X GET http://localhost:8000/api/v1/subscriptions \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Get usage metrics
curl -X GET http://localhost:8000/api/v1/usage \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# List invoices
curl -X GET http://localhost:8000/api/v1/invoices \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Advanced Features Tests

```bash
# Create webhook
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "url": "https://example.com/webhook",
    "events": ["user.created", "user.updated"],
    "active": true
  }'

# Get audit logs
curl -X GET http://localhost:8000/api/v1/audit-logs \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Create data export
curl -X POST http://localhost:8000/api/v1/data-exports \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "format": "json"
  }'
```

---

## Authorization Testing Matrix

### Test Cases for Each Role

```
┌─────────────────────────┬────────────┬───────────┬──────────┬──────────┬──────────┐
│ Endpoint                │ Super Admin│Tenant Adm │App Mgr   │Bill Mgr  │User      │
├─────────────────────────┼────────────┼───────────┼──────────┼──────────┼──────────┤
│ GET /roles              │ ✅ 200     │ ❌ 403    │ ❌ 403   │ ❌ 403   │ ❌ 403   │
│ POST /roles             │ ✅ 201     │ ❌ 403    │ ❌ 403   │ ❌ 403   │ ❌ 403   │
│ GET /applications       │ ✅ 200     │ ✅ 200    │ ✅ 200   │ ❌ 403   │ ❌ 403   │
│ POST /applications      │ ✅ 201     │ ✅ 201    │ ✅ 201   │ ❌ 403   │ ❌ 403   │
│ GET /plans              │ ✅ 200     │ ✅ 200    │ ✅ 200   │ ✅ 200   │ ✅ 200   │
│ POST /plans             │ ✅ 201     │ ❌ 403    │ ❌ 403   │ ✅ 201   │ ❌ 403   │
│ GET /subscriptions      │ ✅ 200     │ ✅ 200    │ ❌ 403   │ ✅ 200   │ ❌ 403   │
│ POST /subscriptions     │ ✅ 201     │ ✅ 201    │ ❌ 403   │ ✅ 201   │ ❌ 403   │
│ GET /invoices           │ ✅ 200     │ ✅ 200    │ ❌ 403   │ ✅ 200   │ ❌ 403   │
│ GET /audit-logs         │ ✅ 200     │ ✅ 200    │ ❌ 403   │ ❌ 403   │ ❌ 403   │
│ POST /webhooks          │ ✅ 201     │ ❌ 403    │ ❌ 403   │ ❌ 403   │ ❌ 403   │
│ GET /auth/me            │ ✅ 200     │ ✅ 200    │ ✅ 200   │ ✅ 200   │ ✅ 200   │
└─────────────────────────┴────────────┴───────────┴──────────┴──────────┴──────────┘
```

---

## Test Data Setup

### Initial Database State

1. **Tenants**: 3 test tenants
   - Nexora (Main Platform)
   - TechCorp (Business)
   - StartupXYZ (Startup)

2. **Users**: 5 users per tenant (15 total)
   - 1 Super Admin
   - 1 Tenant Admin
   - 1 App Manager
   - 1 Billing Manager
   - 1 Regular User

3. **Applications**: 2 per tenant (6 total)

4. **Billing Plans**: 3 plans
   - Free Plan ($0)
   - Pro Plan ($99/month)
   - Enterprise Plan ($999/month)

5. **Permissions**: 10+ permissions
   - user.create, user.read, user.update, user.delete
   - application.* (CRUD)
   - billing.* (read/write)
   - webhook.manage
   - audit.view

---

## Validation Checklist

### Authentication
- [ ] User registration with valid data (success)
- [ ] User registration with duplicate email (409 conflict)
- [ ] User registration with weak password (422 validation)
- [ ] Login with valid credentials (success)
- [ ] Login with invalid credentials (401 unauthorized)
- [ ] Login with non-existent user (401 unauthorized)
- [ ] Token refresh with valid token (success)
- [ ] Token refresh with invalid token (401 unauthorized)
- [ ] Get current user without token (401 unauthorized)
- [ ] Get current user with valid token (success)
- [ ] Logout without token (401 unauthorized)
- [ ] Logout with valid token (success)

### RBAC
- [ ] List roles (admin only)
- [ ] Create role with unique name (success)
- [ ] Create role with duplicate name (422 validation)
- [ ] Get role details (success)
- [ ] Update role (success)
- [ ] Delete role (success)
- [ ] List permissions (success)
- [ ] Assign permission to role (success)
- [ ] Remove permission from role (success)

### Applications
- [ ] Create application (success)
- [ ] List applications (success)
- [ ] Get application details (success)
- [ ] Update application (success)
- [ ] Delete application (success)
- [ ] Activate application (success)
- [ ] Suspend application (success)
- [ ] Generate API key (success)
- [ ] List API keys (success)
- [ ] Revoke API key (success)
- [ ] Add OAuth provider (success)
- [ ] List OAuth providers (success)

### Billing
- [ ] Create billing plan (success)
- [ ] List plans (success)
- [ ] Get plan details (success)
- [ ] Update plan (success)
- [ ] Create subscription (success)
- [ ] Get subscription (success)
- [ ] Upgrade subscription (success)
- [ ] Downgrade subscription (success)
- [ ] Cancel subscription (success)
- [ ] Track usage (success)
- [ ] Get usage metrics (success)
- [ ] List invoices (success)
- [ ] Get invoice details (success)
- [ ] Process payment (success)
- [ ] Retry failed payment (success)

### Advanced
- [ ] Create webhook (success)
- [ ] List webhooks (success)
- [ ] Get webhook details (success)
- [ ] Update webhook (success)
- [ ] Delete webhook (success)
- [ ] Get webhook deliveries (success)
- [ ] List audit logs (success)
- [ ] Get audit log details (success)
- [ ] Create data export (success)
- [ ] List data exports (success)
- [ ] Get export details (success)
- [ ] Get download URL (success)
- [ ] Delete export (success)

### Authorization
- [ ] Super Admin has access to all endpoints
- [ ] Tenant Admin can only access tenant resources
- [ ] App Manager cannot access billing (403)
- [ ] Billing Manager cannot manage users (403)
- [ ] Regular User cannot access admin endpoints (403)
- [ ] Unauthenticated requests return 401

---

## Performance Benchmarks

Target response times (P95):

| Category | Target | Max |
|----------|--------|-----|
| Auth endpoints | 200ms | 500ms |
| RBAC endpoints | 150ms | 400ms |
| Application endpoints | 200ms | 600ms |
| Billing endpoints | 300ms | 800ms |
| Advanced endpoints | 250ms | 700ms |

---

## Common Issues & Troubleshooting

### Issue: 404 Not Found
**Cause**: Wrong endpoint path or version prefix
**Solution**: Verify `/api/v1` prefix and exact endpoint path from OpenAPI docs

### Issue: 401 Unauthorized
**Cause**: Missing or invalid token
**Solution**: Ensure Bearer token is included in Authorization header

### Issue: 403 Forbidden
**Cause**: User lacks permissions for endpoint
**Solution**: Check user role and RBAC permissions matrix above

### Issue: 422 Validation Error
**Cause**: Invalid request body
**Solution**: Verify request data against endpoint schema in `/docs`

### Issue: 500 Internal Server Error
**Cause**: Database or logic error
**Solution**: Check backend logs: `docker logs nexora-backend`

---

## Documentation & References

- **API Reference**: See [API_REFERENCE.md](./API_REFERENCE.md)
- **Local Setup**: See [LOCAL_TESTING_SETUP.md](./LOCAL_TESTING_SETUP.md)
- **Deployment**: See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **OpenAPI Docs**: http://localhost:8000/docs
- **Admin Docs**: http://localhost:8000/admin/docs

---

## Next Steps

1. ✅ Start backend services
2. ✅ Create test users
3. ✅ Run automated tests
4. ✅ Validate authorization matrix
5. ✅ Performance test
6. ✅ Load test
7. ✅ Security audit

---

**Last Updated**: October 3, 2026
**Status**: Ready for comprehensive testing
