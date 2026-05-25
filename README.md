# Import & GST Tools Portal

A single-page dashboard that gives you access to all your Python import/GST tools through **one URL** — no need to remember ports or run scripts separately.

---

## Architecture

```
Browser (port 80)
      │
   nginx  (reverse proxy)
      │
      ├── /          →  Portal Dashboard     (localhost:8080)
      ├── /gst/      →  GST Reconciliation   (localhost:5001)
      ├── /boe/      →  PI→BOE Calculator    (localhost:5002)
      └── /landing/  →  Landing Cost Tool    (localhost:5003)
```

All 4 services run as **gunicorn** WSGI servers. The original Python scripts are **not modified**.

---

## Files

```
import-tools-portal/
├── portal.py               ← Dashboard (port 8080)
├── gst_wrapper.py          ← Imports GST script for gunicorn
├── boe_wrapper.py          ← Imports BOE script for gunicorn
├── landing_cost_flask.py   ← Web version of the Tkinter landing cost app (port 5003)
├── nginx.conf              ← Nginx reverse proxy config
├── setup.sh                ← One-time setup (run once)
├── start_services.sh       ← Start all 4 services
├── stop_services.sh        ← Stop all services
├── requirements.txt        ← Python dependencies
└── tools/                  ← Place your original Python scripts here
    ├── GST-Monthly-Purchase-Data_Compair-GSTN-Vs-Tally.py
    ├── Import_BOE_to_Tally_GST_Entry.py
    └── Import_Items_Landing_Cost_to_Factory.py   (optional, Tkinter — not used on server)
```

---

## Setup (First Time)

### Step 1: Copy files to your server
```bash
scp -r import-tools-portal/ user@your-server:~/
```

### Step 2: Copy your Python scripts into the tools/ folder
```bash
cp "GST-Monthly-Purchase-Data_Compair-GSTN-Vs-Tally.py" ~/import-tools-portal/tools/
cp "Import_BOE_to_Tally_GST_Entry.py"                   ~/import-tools-portal/tools/
cp "Import_Items_Landing_Cost_to_Factory.py"             ~/import-tools-portal/tools/
```

### Step 3: Run the setup script
```bash
cd ~/import-tools-portal
bash setup.sh
```

This will:
- Install Python3, nginx via apt
- Create a Python virtual environment
- Install all pip dependencies (flask, gunicorn, pandas, openpyxl, google-generativeai)
- Configure nginx as reverse proxy
- Create a systemd service for auto-start on boot

### Step 4: Start the services
```bash
source venv/bin/activate
bash start_services.sh
```

### Step 5: Open in browser
```
http://YOUR_SERVER_IP/
```

---

## Daily Use

```bash
# Start all tools
bash ~/import-tools-portal/start_services.sh

# Stop all tools
bash ~/import-tools-portal/stop_services.sh

# View logs
tail -f ~/import-tools-portal/logs/gst_error.log
tail -f ~/import-tools-portal/logs/boe_error.log
tail -f ~/import-tools-portal/logs/landing_error.log
tail -f ~/import-tools-portal/logs/portal_error.log
```

---

## Notes

- **Firewall**: Only port 80 (and 22 for SSH) needs to be open externally. All tool ports (5001-5003, 8080) are internal only.
- **Tkinter script**: The original `Import_Items_Landing_Cost_to_Factory.py` uses Tkinter (desktop GUI) and cannot run on a headless server. `landing_cost_flask.py` is a new web version with identical functionality — the Tkinter file is not touched.
- **Script files**: `gst_wrapper.py` and `boe_wrapper.py` use Python's `importlib` to load the original scripts (which have hyphens in filenames, making direct Python import impossible). The original scripts are **unchanged**.
- **Gemini API Key**: Required for the AI invoice scanning features in the BOE and Landing Cost tools. Enter it in the tool's interface each session.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Tool shows "Offline" on dashboard | Check `logs/NAME_error.log`, make sure scripts are in `tools/` |
| nginx error on setup | Run `sudo nginx -t` to see config errors |
| Port already in use | Run `stop_services.sh` first, then `start_services.sh` |
| File upload fails | Check `client_max_body_size` in nginx.conf (default 50MB) |
