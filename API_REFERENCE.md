# Nexora Core - API Reference Documentation

**API Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: 2024-10-02  

---

## Table of Contents

1. [Authentication](#authentication)
2. [Users](#users)
3. [Roles & Permissions](#roles--permissions)
4. [Applications](#applications)
5. [Billing](#billing)
6. [Infrastructure Services](#infrastructure-services)
7. [Advanced Features](#advanced-features)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)

---

## Authentication

### Login

Create a new authentication session and receive JWT token.

**Endpoint**: `POST /api/v1/auth/login`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "usr_123abc",
    "email": "user@example.com",
    "name": "John Doe",
    "status": "active"
  }
}
```

**Errors**:
- 401 Unauthorized: Invalid credentials
- 429 Too Many Requests: Rate limited after 5 failed attempts

---

### Signup

Register a new user account.

**Endpoint**: `POST /api/v1/auth/signup`

**Request**:
```json
{
  "email": "newuser@example.com",
  "password": "SecurePassword123!",
  "name": "Jane Smith",
  "company": "Acme Corp"
}
```

**Response** (201 Created):
```json
{
  "id": "usr_456def",
  "email": "newuser@example.com",
  "name": "Jane Smith",
  "status": "active",
  "created_at": "2024-10-02T12:00:00Z"
}
```

**Validation**:
- Email must be valid format
- Password: 12+ chars, uppercase, lowercase, number, special char
- Name: 2-100 characters

---

### Refresh Token

Refresh expired access token.

**Endpoint**: `POST /api/v1/auth/refresh`

**Headers**:
```
Authorization: Bearer <refresh_token>
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### Logout

Invalidate current session.

**Endpoint**: `POST /api/v1/auth/logout`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (204 No Content)

---

## Users

### List Users

Retrieve all users in tenant (paginated).

**Endpoint**: `GET /api/v1/users`

**Query Parameters**:
- `skip` (int): Offset - default: 0
- `limit` (int): Page size - default: 50, max: 100
- `status` (string): Filter by status (active, inactive, deleted)
- `sort` (string): Sort field (email, name, created_at)
- `order` (string): Sort order (asc, desc)

**Example**:
```
GET /api/v1/users?skip=0&limit=10&sort=created_at&order=desc
```

**Response** (200 OK):
```json
{
  "total": 150,
  "skip": 0,
  "limit": 10,
  "items": [
    {
      "id": "usr_123abc",
      "email": "user@example.com",
      "name": "John Doe",
      "status": "active",
      "created_at": "2024-10-01T10:00:00Z",
      "updated_at": "2024-10-02T11:30:00Z"
    }
  ]
}
```

---

### Get User

Retrieve specific user by ID.

**Endpoint**: `GET /api/v1/users/{user_id}`

**Response** (200 OK):
```json
{
  "id": "usr_123abc",
  "email": "user@example.com",
  "name": "John Doe",
  "status": "active",
  "roles": [
    {
      "id": "role_admin",
      "name": "Admin",
      "permissions": ["read:users", "write:users", "delete:users"]
    }
  ],
  "created_at": "2024-10-01T10:00:00Z",
  "updated_at": "2024-10-02T11:30:00Z"
}
```

---

### Create User

Create new user in tenant.

**Endpoint**: `POST /api/v1/users`

**Request**:
```json
{
  "email": "newuser@example.com",
  "password": "SecurePassword123!",
  "name": "Jane Smith",
  "status": "active"
}
```

**Response** (201 Created):
```json
{
  "id": "usr_456def",
  "email": "newuser@example.com",
  "name": "Jane Smith",
  "status": "active",
  "created_at": "2024-10-02T12:00:00Z"
}
```

---

### Update User

Modify user information.

**Endpoint**: `PUT /api/v1/users/{user_id}`

**Request**:
```json
{
  "name": "Jane Doe",
  "status": "active"
}
```

**Response** (200 OK):
```json
{
  "id": "usr_456def",
  "email": "jane@example.com",
  "name": "Jane Doe",
  "status": "active",
  "updated_at": "2024-10-02T13:00:00Z"
}
```

---

### Delete User

Soft-delete user (account preserved, access revoked).

**Endpoint**: `DELETE /api/v1/users/{user_id}`

**Response** (204 No Content)

---

## Roles & Permissions

### List Roles

**Endpoint**: `GET /api/v1/roles`

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "role_admin",
      "name": "Admin",
      "description": "Full system access",
      "permissions": ["*"],
      "user_count": 2,
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "id": "role_user",
      "name": "User",
      "description": "Basic user access",
      "permissions": ["read:apps", "write:own_apps"],
      "user_count": 48,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### Create Role

**Endpoint**: `POST /api/v1/roles`

**Request**:
```json
{
  "name": "Manager",
  "description": "Application manager",
  "permissions": ["read:users", "read:apps", "write:apps"]
}
```

**Response** (201 Created):
```json
{
  "id": "role_manager",
  "name": "Manager",
  "description": "Application manager",
  "permissions": ["read:users", "read:apps", "write:apps"],
  "created_at": "2024-10-02T12:00:00Z"
}
```

---

### Assign Role to User

**Endpoint**: `POST /api/v1/role-assignments`

**Request**:
```json
{
  "user_id": "usr_123abc",
  "role_id": "role_manager"
}
```

**Response** (201 Created):
```json
{
  "id": "ra_789xyz",
  "user_id": "usr_123abc",
  "role_id": "role_manager",
  "assigned_at": "2024-10-02T12:00:00Z"
}
```

---

### List Permissions

**Endpoint**: `GET /api/v1/permissions`

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "perm_read_users",
      "name": "read:users",
      "description": "Read user data",
      "category": "users"
    },
    {
      "id": "perm_write_users",
      "name": "write:users",
      "description": "Modify user data",
      "category": "users"
    }
  ]
}
```

---

## Applications

### List Applications

**Endpoint**: `GET /api/v1/applications`

**Query Parameters**:
- `skip` (int): Offset
- `limit` (int): Page size
- `status` (string): Filter by status

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "app_123",
      "name": "Production API",
      "description": "Main production application",
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### Create Application

**Endpoint**: `POST /api/v1/applications`

**Request**:
```json
{
  "name": "Staging API",
  "description": "Staging environment",
  "status": "active"
}
```

**Response** (201 Created):
```json
{
  "id": "app_456",
  "name": "Staging API",
  "description": "Staging environment",
  "status": "active",
  "api_key": "sk_test_51HfPm...",
  "created_at": "2024-10-02T12:00:00Z"
}
```

---

## Billing

### List Plans

**Endpoint**: `GET /api/v1/plans`

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "plan_starter",
      "name": "Starter",
      "description": "For small teams",
      "price": 29.99,
      "currency": "USD",
      "billing_cycle": "monthly",
      "features": ["users_5", "api_calls_10k", "support_email"],
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### Create Subscription

**Endpoint**: `POST /api/v1/subscriptions`

**Request**:
```json
{
  "plan_id": "plan_starter",
  "billing_cycle": "monthly",
  "payment_method_id": "pm_123"
}
```

**Response** (201 Created):
```json
{
  "id": "sub_123",
  "plan_id": "plan_starter",
  "status": "trial",
  "trial_ends_at": "2024-10-16T12:00:00Z",
  "current_period_start": "2024-10-02T12:00:00Z",
  "current_period_end": "2024-11-02T12:00:00Z",
  "created_at": "2024-10-02T12:00:00Z"
}
```

---

### Upgrade Subscription

**Endpoint**: `POST /api/v1/subscriptions/{subscription_id}/upgrade`

**Request**:
```json
{
  "plan_id": "plan_pro"
}
```

**Response** (200 OK):
```json
{
  "id": "sub_123",
  "plan_id": "plan_pro",
  "status": "active",
  "proration_credit": 15.50,
  "current_period_end": "2024-11-02T12:00:00Z",
  "updated_at": "2024-10-02T13:00:00Z"
}
```

---

### List Invoices

**Endpoint**: `GET /api/v1/invoices`

**Query Parameters**:
- `status` (string): pending, paid, failed, overdue
- `skip` (int): Offset
- `limit` (int): Page size

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "inv_123",
      "number": "INV-PREFIX-1704153600000",
      "amount": 29.99,
      "currency": "USD",
      "status": "paid",
      "due_date": "2024-11-01",
      "paid_at": "2024-10-02T12:00:00Z",
      "created_at": "2024-10-01T00:00:00Z"
    }
  ]
}
```

---

### Pay Invoice

**Endpoint**: `POST /api/v1/invoices/{invoice_id}/pay`

**Request**:
```json
{
  "payment_method_id": "pm_123"
}
```

**Response** (200 OK):
```json
{
  "id": "inv_123",
  "status": "paid",
  "paid_at": "2024-10-02T13:00:00Z",
  "payment_id": "py_456"
}
```

---

## Infrastructure Services

### Send Email

**Endpoint**: `POST /api/v1/emails/send`

**Request**:
```json
{
  "to": "user@example.com",
  "subject": "Welcome!",
  "template": "welcome",
  "variables": {
    "first_name": "John"
  }
}
```

**Response** (202 Accepted):
```json
{
  "id": "email_123",
  "status": "sent",
  "created_at": "2024-10-02T12:00:00Z"
}
```

---

### Send SMS

**Endpoint**: `POST /api/v1/sms/send`

**Request**:
```json
{
  "phone": "+1234567890",
  "message": "Your verification code is 123456"
}
```

**Response** (202 Accepted):
```json
{
  "id": "sms_123",
  "status": "sent",
  "created_at": "2024-10-02T12:00:00Z"
}
```

---

## Advanced Features

### Webhooks

#### List Webhooks

**Endpoint**: `GET /api/v1/webhooks`

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "wh_123",
      "url": "https://example.com/webhooks",
      "events": ["subscription.created", "invoice.paid"],
      "active": true,
      "created_at": "2024-10-01T00:00:00Z"
    }
  ]
}
```

---

#### Create Webhook

**Endpoint**: `POST /api/v1/webhooks`

**Request**:
```json
{
  "url": "https://example.com/webhooks",
  "events": ["subscription.created", "subscription.cancelled", "invoice.paid"],
  "active": true
}
```

**Response** (201 Created):
```json
{
  "id": "wh_456",
  "url": "https://example.com/webhooks",
  "events": ["subscription.created", "subscription.cancelled", "invoice.paid"],
  "secret": "whsec_xxxxxxxxxxxxxx",
  "active": true,
  "created_at": "2024-10-02T12:00:00Z"
}
```

---

#### Webhook Signature Verification

Each webhook request includes an `X-Webhook-Signature` header:

```
X-Webhook-Signature: sha256=abcdef0123456789...
```

To verify:

```python
import hmac
import hashlib

def verify_webhook_signature(request_body, signature_header, secret):
    expected = "sha256=" + hmac.new(
        secret.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature_header, expected)
```

---

### Audit Logs

#### List Audit Logs

**Endpoint**: `GET /api/v1/audit-logs`

**Query Parameters**:
- `action` (string): Filter by action type
- `user_id` (string): Filter by user
- `resource_type` (string): Filter by resource type
- `skip` (int): Offset
- `limit` (int): Page size

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "audit_123",
      "action": "user.created",
      "user_id": "usr_admin",
      "resource_type": "user",
      "resource_id": "usr_456",
      "changes": {
        "email": ["", "newuser@example.com"],
        "status": ["", "active"]
      },
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2024-10-02T12:00:00Z"
    }
  ]
}
```

---

### Data Exports

#### Create Export

**Endpoint**: `POST /api/v1/data-exports`

**Request**:
```json
{
  "resource_type": "users",
  "format": "csv",
  "filters": {
    "status": "active"
  }
}
```

**Response** (202 Accepted):
```json
{
  "id": "export_123",
  "status": "processing",
  "resource_type": "users",
  "format": "csv",
  "created_at": "2024-10-02T12:00:00Z"
}
```

---

#### Get Export

**Endpoint**: `GET /api/v1/data-exports/{export_id}`

**Response** (200 OK):
```json
{
  "id": "export_123",
  "status": "completed",
  "resource_type": "users",
  "format": "csv",
  "file_size": 15234,
  "row_count": 150,
  "download_url": "https://api.example.com/v1/data-exports/export_123/download?token=...",
  "expires_at": "2024-10-09T12:00:00Z",
  "created_at": "2024-10-02T12:00:00Z"
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "email",
        "issue": "Invalid email format"
      }
    ]
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 422 | Request validation failed |
| AUTHENTICATION_FAILED | 401 | Invalid credentials or token |
| AUTHORIZATION_FAILED | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Resource already exists |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |

---

## Rate Limiting

### Limits

- **Per Minute**: 100 requests
- **Per Hour**: 1000 requests
- **Per Day**: 10,000 requests

### Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1695399600
```

### Rate Limit Response

When rate limited (429 Too Many Requests):

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Try again in 60 seconds.",
    "retry_after": 60
  }
}
```

---

## Pagination

All list endpoints support pagination:

**Query Parameters**:
- `skip` (int): Number of items to skip - default: 0
- `limit` (int): Number of items to return - default: 50, max: 100

**Response**:
```json
{
  "total": 500,
  "skip": 0,
  "limit": 50,
  "items": [...]
}
```

---

## Versioning

API version is specified in URL: `/api/v1/...`

Current version: **1.0.0**

---

**Generated**: 2024-10-02  
**Status**: Complete and tested  
**For support**: See [Support & Community](#support--community) in Phase 10 guide
