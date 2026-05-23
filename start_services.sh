#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
LOGS="$DIR/logs"
GUNICORN="$DIR/venv/bin/gunicorn"
mkdir -p "$LOGS"

chown -R dckakadia:dckakadia /home/dckakadia/import-tools-portal/data/
chmod -R 775 /home/dckakadia/import-tools-portal/data/
echo "=============================================="
echo "  Import Tools Portal — Starting Services"
chown -R dckakadia:dckakadia /home/dckakadia/import-tools-portal/data/
chmod -R 775 /home/dckakadia/import-tools-portal/data/
echo "=============================================="

echo "  Cleaning up old processes..."
for PORT in 8000 5001 5002 5003 5004 5005; do
    fuser -k ${PORT}/tcp 2>/dev/null && echo "  Killed process on port $PORT" || true
done
sleep 2

rm -f "$LOGS"/*.pid
rm -f "$DIR/gunicorn.ctl"
chown -R dckakadia:dckakadia /home/dckakadia/import-tools-portal/data/
chmod -R 775 /home/dckakadia/import-tools-portal/data/
echo "  Cleared stale PID files and sockets"

if [ ! -f "$GUNICORN" ]; then
    echo "[ERROR] gunicorn not found at $GUNICORN"
    exit 1
fi

cd "$DIR"

start_service() {
    local NAME="$1"
    local MODULE="$2"
    local PORT="$3"
    local PIDFILE="$LOGS/${NAME}.pid"

    $GUNICORN \
        --bind "0.0.0.0:${PORT}" \
        --workers 2 \
        --timeout 120 \
        --access-logfile "$LOGS/${NAME}_access.log" \
        --error-logfile  "$LOGS/${NAME}_error.log" \
        --pid            "$PIDFILE" \
        --chdir          "$DIR" \
        --daemon \
        "$MODULE"
    sleep 1
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "  [$NAME]  started on port $PORT  (PID $(cat "$PIDFILE"))"
    else
        echo "  [$NAME]  FAILED — check $LOGS/${NAME}_error.log"
    fi
}

start_service "portal"   "portal:app"             8000
start_service "gst"      "gst_wrapper:app"        5001
start_service "boe"      "boe_wrapper:app"        5002
start_service "landing"  "landing_cost_flask:app" 5003
start_service "po"       "po_flask:app"           5005

echo ""
echo "  Dashboard  →  http://$(hostname -I | awk '{print $1}'):8080"
chown -R dckakadia:dckakadia /home/dckakadia/import-tools-portal/data/
chmod -R 775 /home/dckakadia/import-tools-portal/data/
echo "=============================================="
