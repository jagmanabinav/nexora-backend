# Backend Testing

## Run the suite

Activate the project environment and run:

```bash
source .venv/bin/activate
python -m pytest
```

Run one test group or function with:

```bash
python -m pytest tests/test_api.py -k authentication
python -m pytest tests/test_api.py::test_billing_plan_subscription_usage_and_invoice_endpoints
python -m pytest --cov=app --cov-report=term-missing
```

## Test design

`tests/test_api.py` exercises the FastAPI routes end-to-end through `TestClient`. It covers health/readiness, authentication and refresh-token rotation, RBAC, applications, API keys, OAuth, billing, subscriptions, invoices, usage, payment methods, webhooks, audit logs, and data exports.

`tests/conftest.py` creates an in-memory SQLite database using the production SQLAlchemy metadata. PostgreSQL UUID and JSONB types are adapted for SQLite in the test process only. Both database dependencies are overridden, and each test rolls back its isolated transaction. The suite does not connect to or modify the developer's PostgreSQL database and does not require the local `.env` secrets.

The API tests generate test-only JWT and encryption keys if those environment variables are not already set. Data-export files created by tests use pytest's temporary directory and are cleaned up automatically.

## Adding tests

- Prefer API-level tests that verify HTTP status codes and response bodies for user-visible behavior.
- Create all test records through fixtures or the provided database session; do not depend on seed data or test order.
- Keep IDs, emails, slugs, and other unique values local to each test.
- Assert expected error cases as well as successful requests.
- Do not point tests at the local PostgreSQL database. Use a dedicated disposable test database if PostgreSQL-specific integration behavior needs separate verification.
