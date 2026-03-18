#!/bin/bash
# Axiom OS v2 — Startup Script
# Usage: ./start.sh

set -e
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
echo "  ╔═══════════════════════════════════╗"
echo "  ║   AXIOM OS v2 — Lamora Healthcare ║"
echo "  ║   AI Lead Generation Platform     ║"
echo "  ╚═══════════════════════════════════╝"
echo -e "${NC}"

# Check .env
if [ ! -f "backend/.env" ]; then
  echo -e "${YELLOW}⚠  backend/.env not found — copying from example${NC}"
  cp backend/.env.example backend/.env
  echo -e "${RED}   → Fill in ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY in backend/.env${NC}"
fi

# Check frontend .env
if [ ! -f "frontend/.env.local" ]; then
  echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
  echo -e "${GREEN}✓  frontend/.env.local created${NC}"
fi

# Install backend deps
echo -e "${BLUE}→ Installing Python dependencies...${NC}"
cd backend && pip install -r requirements.txt --break-system-packages -q
playwright install chromium 2>/dev/null || true
cd ..

# Install frontend deps
echo -e "${BLUE}→ Installing Node dependencies...${NC}"
cd frontend && npm install --silent
cd ..

# Check Redis
if command -v redis-cli &>/dev/null && redis-cli ping &>/dev/null; then
  echo -e "${GREEN}✓  Redis is running${NC}"
else
  echo -e "${YELLOW}⚠  Redis not detected — starting without job queues${NC}"
  echo "   Install: brew install redis && brew services start redis (Mac)"
  echo "            sudo apt install redis-server && sudo service redis start (Linux)"
fi

echo ""
echo -e "${GREEN}Starting Axiom OS...${NC}"
echo ""

# Start backend
echo -e "${BLUE}→ Starting FastAPI backend on :8000${NC}"
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..
sleep 2

# Start frontend
echo -e "${BLUE}→ Starting Next.js frontend on :3000${NC}"
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ Axiom OS is running${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "  Frontend:  ${BLUE}http://localhost:3000${NC}"
echo -e "  API:       ${BLUE}http://localhost:8000${NC}"
echo -e "  API Docs:  ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "${YELLOW}  Press Ctrl+C to stop all services${NC}"
echo ""

# Wait and cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" SIGINT SIGTERM
wait
