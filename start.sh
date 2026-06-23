#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "⚽ WC 2026 Simulator"
echo ""
echo "Starting backend on :8000…"
cd "$ROOT/backend" && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND=$!

echo "Starting frontend on :3000…"
cd "$ROOT/frontend" && npm run dev -- --port 3000 &
FRONTEND=$!

echo ""
echo "  Backend:   http://localhost:8000"
echo "  Frontend:  http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both."
trap "kill $BACKEND $FRONTEND 2>/dev/null; exit 0" SIGINT SIGTERM
wait
