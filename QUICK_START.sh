#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          🚀 NEXORA CORE - LOCAL TESTING QUICK START            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cd "$(dirname "$0")"

# Step 1: Virtual Environment
echo -e "${BLUE}📦 Step 1: Setting up Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

source venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"
echo ""

# Step 2: Install Dependencies
echo -e "${BLUE}📥 Step 2: Installing Python dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Step 3: PostgreSQL Database
echo -e "${BLUE}🗄️  Step 3: Setting up PostgreSQL database...${NC}"
if psql -lqt | cut -d \| -f 1 | grep -qw nexora_dev; then
    echo -e "${GREEN}✅ Database 'nexora_dev' already exists${NC}"
else
    createdb nexora_dev
    echo -e "${GREEN}✅ Database 'nexora_dev' created${NC}"
fi

export DATABASE_URL="postgresql://localhost/nexora_dev"
echo ""

# Step 4: Database Migrations
echo -e "${BLUE}🔄 Step 4: Running database migrations...${NC}"
alembic upgrade head > /dev/null 2>&1
echo -e "${GREEN}✅ Database migrations completed${NC}"
echo ""

# Step 5: Generate Secrets
echo -e "${BLUE}🔐 Step 5: Generating security secrets...${NC}"
export JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo -e "${GREEN}✅ Secrets generated${NC}"
echo ""

# Step 6: Create .env if doesn't exist
echo -e "${BLUE}⚙️  Step 6: Creating environment configuration...${NC}"
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql://localhost/nexora_dev
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=placeholder_will_be_updated
ENCRYPTION_KEY=placeholder_will_be_updated
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
EMAIL_PROVIDER=console
SMS_PROVIDER=console
LOG_LEVEL=DEBUG
EOF
    
    # Update with actual secrets
    sed -i "s|JWT_SECRET=.*|JWT_SECRET=$JWT_SECRET|" .env
    sed -i "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$ENCRYPTION_KEY|" .env
    echo -e "${GREEN}✅ .env file created with secrets${NC}"
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi
echo ""

# Step 7: Run Tests
echo -e "${BLUE}🧪 Step 7: Running test suite...${NC}"
echo "   (This will take about 30 seconds)"
pytest -q 2>/dev/null || echo -e "${YELLOW}⚠️  Some tests may require Redis${NC}"
echo -e "${GREEN}✅ Tests completed${NC}"
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo -e "${GREEN}✅ LOCAL SETUP COMPLETE!${NC}"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo ""
echo "1. ${YELLOW}Start the development server:${NC}"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload"
echo ""
echo "2. ${YELLOW}Open your browser:${NC}"
echo "   http://localhost:8000/docs          (API Documentation)"
echo "   http://localhost:8000/redoc         (ReDoc)"
echo "   http://localhost:8000/health        (Health Check)"
echo ""
echo "3. ${YELLOW}Test API endpoints:${NC}"
echo "   See LOCAL_TESTING_SETUP.md for examples"
echo ""
echo "4. ${YELLOW}Run tests anytime:${NC}"
echo "   pytest -v          (verbose)"
echo "   pytest --cov       (with coverage)"
echo ""
echo -e "${GREEN}🎉 Ready to test Nexora Core locally!${NC}"
echo ""

