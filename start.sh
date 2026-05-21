#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/kastra-backend"
FRONTEND="$ROOT/kastra-frontend"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo -e "${YELLOW}Stopping servers...${NC}"
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  echo -e "${YELLOW}All stopped.${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  Kastra — Starting Dev Environment  ${NC}"
echo -e "${GREEN}=====================================${NC}"

# ── Backend ────────────────────────────────────────────────────
echo -e "\n${BLUE}[backend]${NC} Starting FastAPI..."

if [[ ! -f "$BACKEND/.env" ]]; then
  echo -e "${YELLOW}[backend] WARNING: .env not found — copying .env.example${NC}"
  cp "$BACKEND/.env.example" "$BACKEND/.env"
fi

# Activate virtualenv — prefer local venv, then pipenv, then system
if [[ -f "$BACKEND/venv/bin/activate" ]]; then
  source "$BACKEND/venv/bin/activate"
elif [[ -f "$BACKEND/.venv/bin/activate" ]]; then
  source "$BACKEND/.venv/bin/activate"
else
  # Locate the pipenv virtualenv for this project
  PIPENV_VENV=$(cd "$BACKEND" && pipenv --venv 2>/dev/null || true)
  if [[ -n "$PIPENV_VENV" && -f "$PIPENV_VENV/bin/activate" ]]; then
    source "$PIPENV_VENV/bin/activate"
    echo -e "${BLUE}[backend]${NC} Using pipenv virtualenv: $PIPENV_VENV"
  fi
fi

cd "$BACKEND"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080 \
  --log-level info 2>&1 | sed "s/^/$(echo -e "${BLUE}[backend]${NC}") /" &
BACKEND_PID=$!

# Wait for backend to accept connections before starting frontend
echo -e "${BLUE}[backend]${NC} Waiting for API to be ready..."
until curl -sf http://localhost:8080/health > /dev/null 2>&1; do
  sleep 0.5
done
echo -e "${BLUE}[backend]${NC} API is ready."

# ── Frontend ───────────────────────────────────────────────────
echo -e "${BLUE}[frontend]${NC} Starting Vite..."

if [[ ! -f "$FRONTEND/.env" ]]; then
  echo -e "${YELLOW}[frontend] WARNING: .env not found — copying .env.example${NC}"
  cp "$FRONTEND/.env.example" "$FRONTEND/.env"
fi

cd "$FRONTEND"
npm run dev 2>&1 | sed "s/^/$(echo -e "${GREEN}[frontend]${NC}") /" &
FRONTEND_PID=$!

# ── Info ───────────────────────────────────────────────────────
echo ""
echo -e "  Frontend  → ${GREEN}http://localhost:5200${NC}"
echo -e "  API       → ${BLUE}http://localhost:8080${NC}"
echo -e "  API Docs  → ${BLUE}http://localhost:8080/docs${NC}"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop both servers"
echo ""

wait
