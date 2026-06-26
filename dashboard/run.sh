#!/bin/bash
set -euo pipefail
# Backlog-health dashboard + human-in-the-loop review queue.
cd "$(dirname "$0")/.."
python dashboard/seed_backlog.py
echo ""
echo "Starting dashboard at http://127.0.0.1:8000  (Ctrl+C to stop)"
uvicorn dashboard.app:app --host 127.0.0.1 --port 8000
