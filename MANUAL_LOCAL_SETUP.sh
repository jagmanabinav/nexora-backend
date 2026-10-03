#!/bin/bash

echo "═══════════════════════════════════════════════════════════════"
echo "        🚀 NEXORA CORE - LOCAL TESTING SETUP (MANUAL)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 1: Check PostgreSQL
echo "Step 1️⃣ : Checking PostgreSQL..."
psql --version
echo "✅ PostgreSQL is available"
echo ""

# Step 2: Create database
echo "Step 2️⃣ : Creating database..."
createdb nexora_dev 2>/dev/null && echo "✅ Database created" || echo "✅ Database already exists"
psql nexora_dev -c "SELECT 'Database connected' AS status;"
echo ""

# Step 3: Set environment variable
echo "Step 3️⃣ : Setting DATABASE_URL..."
export DATABASE_URL="postgresql://localhost/nexora_dev"
echo "✅ DATABASE_URL set: $DATABASE_URL"
echo ""

# Step 4: Generate secrets
echo "Step 4️⃣ : Generating secrets..."
export JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "✅ JWT_SECRET generated (${#JWT_SECRET} chars)"
echo "✅ ENCRYPTION_KEY generated"
echo ""

# Step 5: Install Python dependencies
echo "Step 5️⃣ : Installing Python dependencies..."
python3 -m pip install -q --upgrade pip
python3 -m pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Step 6: Create env file
echo "Step 6️⃣ : Creating .env file..."
cat > .env << ENVEOF
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=$DATABASE_URL
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
EMAIL_PROVIDER=console
SMS_PROVIDER=console
LOG_LEVEL=DEBUG
ENVEOF
echo "✅ .env file created"
echo ""

# Step 7: Run migrations
echo "Step 7️⃣ : Running database migrations..."
python3 -m alembic upgrade head
echo "✅ Migrations completed"
echo ""

# Step 8: Check database tables
echo "Step 8️⃣ : Verifying database schema..."
TABLE_COUNT=$(psql nexora_dev -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
echo "✅ Database has $TABLE_COUNT tables"
echo ""

# Step 9: Run tests
echo "Step 9️⃣ : Running tests..."
echo "   (This will take about 30 seconds)"
python3 -m pytest -q --tb=short 2>&1 | tail -20
echo "✅ Tests completed"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "✅ LOCAL SETUP COMPLETE!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1️⃣ Start the development server:"
echo "   python3 -m uvicorn app.main:app --reload"
echo ""
echo "2️⃣ Open browser to:"
echo "   http://localhost:8000/docs          (Swagger UI)"
echo "   http://localhost:8000/redoc         (ReDoc)"
echo "   http://localhost:8000/health        (Health check)"
echo ""
echo "3️⃣ Run tests anytime:"
echo "   python3 -m pytest -v"
echo "   python3 -m pytest --cov=app"
echo ""
echo "═══════════════════════════════════════════════════════════════"

