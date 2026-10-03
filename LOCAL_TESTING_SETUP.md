# Nexora Core - Local Testing Setup Guide

**Complete step-by-step guide to test Nexora Core locally on your development machine**

---

## Prerequisites

### System Requirements

```bash
# Verify you have:
python3 --version      # Should be 3.12+
psql --version         # Should be PostgreSQL 14+
redis-cli --version    # Should be Redis 7+
```

### Install Missing Components (Ubuntu/Debian)

```bash
# PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Redis
sudo apt-get install redis-server

# Python development tools
sudo apt-get install python3-venv python3-dev build-essential
```

### Install Missing Components (macOS)

```bash
# Using Homebrew
brew install postgresql redis python@3.12
```

### Install Missing Components (Windows)

- **PostgreSQL**: Download from https://www.postgresql.org/download/windows/
- **Redis**: Use Windows Subsystem for Linux (WSL2) or Docker
- **Python**: Download from https://www.python.org/downloads/

---

## Step 1: Setup Python Virtual Environment

```bash
cd /home/jagman/Projects/nexora/backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Verify activation (should show venv prefix in terminal)
which python  # or 'where python' on Windows
```

---

## Step 2: Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
pip list | grep -E "FastAPI|SQLAlchemy|Pydantic|pytest"
```

---

## Step 3: Setup Local PostgreSQL Database

```bash
# Create database
createdb nexora_dev

# Verify database created
psql -l | grep nexora_dev

# (Optional) If you need to use a password, export connection string:
export DATABASE_URL="postgresql://username:password@localhost:5432/nexora_dev"

# Without password (using peer authentication):
export DATABASE_URL="postgresql://localhost/nexora_dev"
```

---

## Step 4: Setup Local Redis

### Option A: Using System Redis

```bash
# Start Redis service
sudo systemctl start redis-server

# Verify it's running
redis-cli ping
# Should return: PONG

# Set Redis URL
export REDIS_URL="redis://localhost:6379/0"
```

### Option B: Using Docker (If you have Docker)

```bash
# Run Redis in container
docker run -d -p 6379:6379 --name redis-nexora redis:7-alpine

# Verify
redis-cli ping
# Should return: PONG
```

### Option C: Skip Redis for Testing

Some tests may not require Redis. You can set a dummy URL:
```bash
export REDIS_URL="redis://localhost:6379/0"
# Tests will fail if they require Redis, but you'll see which ones do
```

---

## Step 5: Generate Required Secrets

```bash
# Generate JWT_SECRET (32+ character random string)
export JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Generate ENCRYPTION_KEY (Fernet format)
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Verify they are set
echo "JWT_SECRET: $JWT_SECRET"
echo "ENCRYPTION_KEY: $ENCRYPTION_KEY"
```

---

## Step 6: Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with local settings
cat > .env << 'ENVFILE'
# Application
ENVIRONMENT=development
DEBUG=true
APP_NAME=Nexora Core
API_V1_PREFIX=/api/v1

# Database (from Step 3)
DATABASE_URL=postgresql://localhost/nexora_dev
DATABASE_ECHO=false

# Redis (from Step 4)
REDIS_URL=redis://localhost:6379/0

# JWT (from Step 5)
JWT_SECRET=<paste your JWT_SECRET here>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption (from Step 5)
ENCRYPTION_KEY=<paste your ENCRYPTION_KEY here>

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Optional (for email/SMS if testing)
EMAIL_PROVIDER=console
SMS_PROVIDER=console
STORAGE_PROVIDER=local

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
WORKERS=1
ENVFILE

# Make sure to fill in JWT_SECRET and ENCRYPTION_KEY from Step 5!
nano .env
```

---

## Step 7: Run Database Migrations

```bash
# Verify Alembic is installed
pip show alembic

# Run all migrations
alembic upgrade head

# Check current migration version
alembic current

# (Optional) See migration history
alembic history --rev-range 1:
```

---

## Step 8: Verify Database Setup

```bash
# Connect to database
psql nexora_dev

# List tables (should see 26 tables)
\dt

# Check row counts
SELECT 'tenants'::regclass, COUNT(*) FROM tenants
UNION ALL
SELECT 'users'::regclass, COUNT(*) FROM users
UNION ALL
SELECT 'roles'::regclass, COUNT(*) FROM roles;

# Exit
\q
```

---

## Step 9: Run All Tests

### Run Complete Test Suite

```bash
# Make sure venv is activated
source venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run specific test function
pytest tests/test_auth.py::test_login_success -v
```

### Expected Output

```
======================== test session starts =========================
collected 150+ items

tests/test_auth.py ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓       [10%]
tests/test_users.py ✓ ✓ ✓ ✓ ✓            [20%]
tests/test_rbac.py ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓      [35%]
tests/test_billing.py ✓ ✓ ✓ ✓ ✓ ✓ ✓    [50%]
tests/test_webhooks.py ✓ ✓ ✓ ✓ ✓       [65%]
tests/test_audit.py ✓ ✓ ✓ ✓ ✓ ✓ ✓     [80%]
tests/test_phase7_advanced.py ✓ ✓ ✓ ✓  [95%]
tests/test_phase9_integration.py ✓ ✓ ✓  [100%]

======================== 150+ passed in 30s =========================
======================== Coverage: 85%+ =============================
```

---

## Step 10: Start Development Server

```bash
# Make sure venv is activated
source venv/bin/activate

# Start with auto-reload
uvicorn app.main:app --reload

# OR with custom host/port
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

---

## Step 11: Access the Application

### In Your Browser

1. **API Documentation (Swagger UI)**
   - Open: http://localhost:8000/docs
   - Interactive API explorer

2. **Alternative Documentation (ReDoc)**
   - Open: http://localhost:8000/redoc
   - Beautiful API reference

3. **OpenAPI Schema**
   - Open: http://localhost:8000/openapi.json
   - Raw schema in JSON format

### Health Check Endpoint

```bash
# In terminal (while server is running)
curl http://localhost:8000/health

# Response:
# {"status":"healthy","service":"Nexora Core"}
```

---

## Step 12: Test API Endpoints

### Signup (Create User)

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPassword123!",
    "name": "Test User",
    "company": "Test Company"
  }'

# Response:
# {
#   "id": "usr_xxxxx",
#   "email": "testuser@example.com",
#   "name": "Test User",
#   "status": "active"
# }
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPassword123!"
  }'

# Response (save the access_token):
# {
#   "access_token": "eyJhbGc...",
#   "refresh_token": "eyJhbGc...",
#   "token_type": "bearer",
#   "expires_in": 900
# }
```

### Get User (Authenticated)

```bash
# Replace TOKEN with actual access_token from login response
TOKEN="your_access_token_here"

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/users/me

# Response:
# {
#   "id": "usr_xxxxx",
#   "email": "testuser@example.com",
#   "name": "Test User"
# }
```

### List Users

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/users

# Response:
# {
#   "total": 1,
#   "items": [{ user object }]
# }
```

---

## Step 13: Complete Testing Checklist

### ✅ Authentication Testing

```bash
# Test signup
# Test login
# Test refresh token
# Test logout
# Test invalid credentials
# Test expired token
```

### ✅ CRUD Operations Testing

```bash
# Test create user
# Test read user
# Test update user
# Test delete user
# Test list users
# Test pagination
```

### ✅ RBAC Testing

```bash
# Test role creation
# Test role assignment
# Test permission validation
# Test unauthorized access
```

### ✅ Billing Testing

```bash
# Test subscription creation
# Test plan listing
# Test invoice generation
# Test payment processing
```

### ✅ Advanced Features Testing

```bash
# Test webhook creation
# Test audit log recording
# Test data export creation
# Test webhook delivery
```

---

## Complete Local Test Command

```bash
#!/bin/bash
# Save as local_test.sh and run: bash local_test.sh

echo "🚀 Starting Nexora Core Local Test Suite"
echo ""

# Activate venv
source venv/bin/activate

echo "✅ Step 1: Running database migrations..."
alembic upgrade head

echo ""
echo "✅ Step 2: Running complete test suite..."
pytest -v --cov=app --cov-report=html

echo ""
echo "✅ Step 3: Starting development server..."
echo "   🌐 API Docs: http://localhost:8000/docs"
echo "   📊 Coverage Report: ./htmlcov/index.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Troubleshooting

### Database Connection Error

```
Error: could not connect to server: No such file or directory

Solution:
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL if not running
sudo systemctl start postgresql

# Verify database exists
psql -l | grep nexora_dev
```

### Redis Connection Error

```
Error: ConnectionError: Error 111 connecting to localhost:6379

Solution:
# Check if Redis is running
redis-cli ping

# Start Redis if not running
sudo systemctl start redis-server

# Or start with Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### Migration Error

```
Error: Target database is not up to date

Solution:
# Check current version
alembic current

# Upgrade to head
alembic upgrade head

# Or reset (WARNING: deletes data)
alembic downgrade base
alembic upgrade head
```

### Import Errors

```
Error: ModuleNotFoundError: No module named 'app'

Solution:
# Make sure you're in the correct directory
cd /home/jagman/Projects/nexora/backend

# Verify venv is activated (should show venv in prompt)
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Port Already in Use

```
Error: Address already in use

Solution:
# Use different port
uvicorn app.main:app --reload --port 8001

# Or find and kill process using port 8000
lsof -i :8000
kill -9 <PID>
```

---

## Performance Testing Locally

### Load Testing with Locust

```bash
# Install locust
pip install locust

# Create load_test.py (see project root)
# Run load test
locust -f load_test.py -u 100 -r 10 --run-time 5m -H http://localhost:8000
```

### Profiling

```bash
# Install profiling tools
pip install py-spy

# Run server with profiling
python -m cProfile -o profile.stats -m uvicorn app.main:app

# View results
pip install snakeviz
snakeviz profile.stats
```

---

## Quick Start Bash Script

Save this as `quick_start.sh`:

```bash
#!/bin/bash
set -e

cd /home/jagman/Projects/nexora/backend

echo "🚀 Nexora Core - Quick Local Setup"
echo ""

# Step 1: Virtual Environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Step 2: Dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Step 3: Database
echo "🗄️  Setting up database..."
createdb nexora_dev 2>/dev/null || echo "Database already exists"

# Step 4: Migrations
echo "🔄 Running migrations..."
alembic upgrade head

# Step 5: Secrets
echo "🔐 Generating secrets..."
export JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Step 6: Tests
echo ""
echo "🧪 Running tests..."
pytest -q

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start development server:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo "Open browser to: http://localhost:8000/docs"
```

Make it executable and run:
```bash
chmod +x quick_start.sh
./quick_start.sh
```

---

## Next Steps After Local Testing

✅ All tests pass locally  
↓  
✅ API works in local environment  
↓  
✅ Database and Redis configured correctly  
↓  
→ **Ready for production deployment!**

See DEPLOYMENT_GUIDE.md for production deployment options.

---

**Questions?** Check the troubleshooting section above or see DEPLOYMENT_GUIDE.md for more details.
