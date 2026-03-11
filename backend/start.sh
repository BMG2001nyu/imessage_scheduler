#!/usr/bin/env bash
# Start API and Gateway from backend/ with one venv. Run from repo root or backend/.
set -e
cd "$(dirname "$0")"
REPO_ROOT="$(cd .. && pwd)"

# Ensure PostgreSQL is running locally (default port 5432; set DATABASE_URL in .env if different)
if [[ ! -d .venv ]]; then
  echo "Creating .venv and installing dependencies..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  echo "Run 'alembic upgrade head' from backend/api if using the API DB."
else
  source .venv/bin/activate
fi

# API on 8002, Gateway on 8001 (set DRY_RUN=true in .env to simulate sends only)
(cd api && uvicorn app.main:app --reload --port 8002) &
(cd gateway && DRY_RUN=${DRY_RUN:-false} uvicorn app.main:app --reload --port 8001) &
wait
