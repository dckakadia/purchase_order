#!/bin/bash
# ============================================================
# setup.sh — One-time setup for Import Tools Portal
# Run as: bash setup.sh
# ============================================================

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=============================================="
echo "  Import Tools Portal — Setup"
echo "=============================================="

# ── 1. System packages ───────────────────────────────────────────
echo "[1/6] Installing system packages..."
sudo apt-get update -q
sudo apt-get install -y python3 python3-pip python3-venv nginx

# ── 2. Python virtualenv ─────────────────────────────────────────
echo "[2/6] Creating Python virtual environment..."
python3 -m venv "$DIR/venv"
source "$DIR/venv/bin/activate"

# ── 3. Python dependencies ────────────────────────────────────────
echo "[3/6] Installing Python dependencies..."
pip install --upgrade pip -q
pip install \
    flask \
    gunicorn \
    pandas \
    openpyxl \
    google-generativeai \
    -q

# ── 4. Check scripts exist ────────────────────────────────────────
echo "[4/6] Checking tool scripts..."
MISSING=0
for f in \
    "GST-Monthly-Purchase-Data_Compair-GSTN-Vs-Tally.py" \
    "Import_BOE_to_Tally_GST_Entry.py" \
    "Import_Items_Landing_Cost_to_Factory.py"; do
    if [ ! -f "$DIR/tools/$f" ]; then
        echo "  [MISSING] tools/$f"
        MISSING=$((MISSING+1))
    else
        echo "  [OK]      tools/$f"
    fi
done

if [ "$MISSING" -gt 0 ]; then
    echo ""
    echo "  ⚠  Copy the $MISSING missing script(s) into: $DIR/tools/"
    echo "     GST and BOE scripts are required."
    echo "     The Tkinter landing cost script is optional (web version is used instead)."
fi

# ── 5. Nginx configuration ────────────────────────────────────────
echo "[5/6] Configuring nginx..."
sudo cp "$DIR/nginx.conf" /etc/nginx/sites-available/import-tools
sudo ln -sf /etc/nginx/sites-available/import-tools /etc/nginx/sites-enabled/import-tools
sudo rm -f /etc/nginx/sites-enabled/default  # remove default nginx page
sudo nginx -t && sudo systemctl reload nginx
echo "  nginx configured and reloaded."

# ── 6. Create systemd service (optional auto-start) ──────────────
echo "[6/6] Creating systemd service for auto-start on boot..."
VENV_PYTHON="$DIR/venv/bin/python"
GUNICORN="$DIR/venv/bin/gunicorn"

sudo tee /etc/systemd/system/import-tools.service > /dev/null <<EOF
[Unit]
Description=Import Tools Portal
After=network.target

[Service]
Type=forking
User=$USER
WorkingDirectory=$DIR
ExecStart=$DIR/start_services.sh
ExecStop=$DIR/stop_services.sh
Restart=on-failure
Environment="PATH=$DIR/venv/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable import-tools
echo "  Systemd service created. Will auto-start on reboot."

echo ""
echo "=============================================="
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Copy your scripts to: $DIR/tools/"
echo "  2. Activate venv:  source $DIR/venv/bin/activate"
echo "  3. Start services: bash start_services.sh"
echo "  4. Open browser:   http://$(hostname -I | awk '{print $1}')/"
echo "=============================================="
