#!/bin/bash
# Quick Testing Script for Last Mile Justice Navigator

echo "🧪 LAST MILE JUSTICE NAVIGATOR - TESTING SUITE"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if venv is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated. Activating...${NC}"
    source venv/Scripts/activate
fi

echo -e "${BLUE}📦 Installing test dependencies...${NC}"
pip install pytest pytest-asyncio pytest-cov -q

echo ""
echo -e "${BLUE}🧪 Running Unit Tests...${NC}"
echo "========================"
pytest backend/tests/test_legal_agent.py -v --tb=short

echo ""
echo -e "${BLUE}🏠 Running Shelter Agent Tests...${NC}"
echo "===================================="
pytest backend/tests/test_shelter_agent.py -v --tb=short

echo ""
echo -e "${BLUE}🔄 Running CLI Integration Test...${NC}"
echo "===================================="
cd backend && python test_cli.py && cd ..

echo ""
echo -e "${BLUE}📊 Running Coverage Report...${NC}"
echo "=============================="
pytest backend/tests/ --cov=backend/agents --cov=backend/core --cov=backend/models --cov-report=html

echo ""
echo -e "${GREEN}✅ Testing Complete!${NC}"
echo ""
echo "📋 Test Results:"
echo "  - Unit Tests: See output above"
echo "  - Integration: See test_cli.py output"
echo "  - Coverage Report: htmlcov/index.html"
echo ""
