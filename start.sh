#!/usr/bin/env sh
set -e
cd "$(dirname "$0")"
.venv/bin/python realtime_simulation.py &
SIM_PID=$!
.venv/bin/python realtime_terminal.py &
TERM_PID=$!
trap 'kill "$SIM_PID" "$TERM_PID" 2>/dev/null || true' INT TERM
.venv/bin/python scientific_ui.py
kill "$SIM_PID" "$TERM_PID" 2>/dev/null || true
