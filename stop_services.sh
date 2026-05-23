#!/bin/bash
# ============================================================
# stop_services.sh  —  Stop all Import Tools Portal services
# ============================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
LOGS="$DIR/logs"

echo "Stopping Import Tools Portal services..."

for PIDFILE in "$LOGS"/*.pid; do
    [ -f "$PIDFILE" ] || continue
    NAME=$(basename "$PIDFILE" .pid)
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "  [$NAME]  stopped (PID $PID)"
    else
        echo "  [$NAME]  was not running"
    fi
    rm -f "$PIDFILE"
done

echo "Done."
