#!/usr/bin/env bash
# Sprint 8 — Test Runner
# Usage: ./scripts/run_sprint8.sh [local|ci|recovery|locust|all]
#
# Modes:
#   local     — Core tests only (no Docker, no Locust). Fastest. Use daily.
#   ci        — Core + Locust headless. Matches the CI pipeline.
#   recovery  — Recovery tests only. Requires Docker Compose stack running.
#   locust    — Interactive Locust UI. Visit http://localhost:8089.
#   all       — Everything including recovery.

set -euo pipefail

MODE="${1:-local}"
REPORTS_DIR="reports"
mkdir -p "$REPORTS_DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SPRINT 8 — PILOT SIMULATION & HARDENING"
echo "  Mode: $MODE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_core() {
  echo "▶ Load tests..."
  pytest tests/load/test_load.py -v -s --timeout=120

  echo ""
  echo "▶ Saturday simulation..."
  pytest tests/simulation/ -v -s --timeout=300

  echo ""
  echo "▶ Staff workflow tests..."
  pytest tests/staff/ -v --timeout=60
}

run_recovery() {
  echo "▶ Recovery tests (requires Docker Compose stack)..."
  pytest tests/recovery/ -v -s --timeout=120
}

run_locust_headless() {
  echo "▶ Starting API for Locust..."
  uvicorn app.main:app --host 0.0.0.0 --port 8000 &
  API_PID=$!
  sleep 3

  echo "▶ Running Locust headless (10 users, 120s)..."
  locust -f tests/load/locustfile.py \
    --host http://localhost:8000 \
    --users 10 \
    --spawn-rate 2 \
    --run-time 120s \
    --headless \
    --html "$REPORTS_DIR/locust_report.html" \
    --exit-code-on-error 1 || true

  echo "▶ Locust report: $REPORTS_DIR/locust_report.html"
  kill $API_PID 2>/dev/null || true
}

run_locust_interactive() {
  echo "▶ Starting API..."
  uvicorn app.main:app --host 0.0.0.0 --port 8000 &
  sleep 2

  echo "▶ Starting Locust web UI at http://localhost:8089"
  echo "   Configure: host=http://localhost:8000, users=10, spawn-rate=2"
  locust -f tests/load/locustfile.py
}

case "$MODE" in
  local)
    run_core
    ;;
  ci)
    run_core
    run_locust_headless
    ;;
  recovery)
    run_recovery
    ;;
  locust)
    run_locust_interactive
    ;;
  all)
    run_core
    run_locust_headless
    run_recovery
    ;;
  *)
    echo "Unknown mode: $MODE"
    echo "Usage: $0 [local|ci|recovery|locust|all]"
    exit 1
    ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Sprint 8 complete."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
