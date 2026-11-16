"""
Deploy the current origin/main to the production server over SSH (key auth).

    python deploy.py

Steps on the server: back up the live DB, fast-forward pull, install
requirements, syntax-check, restart only the purchase_order PM2 app, then
verify it answers. Stops at the first failing step.

Requires an SSH key authorised on the server (password login is disabled).
Override the target with DEPLOY_HOST / DEPLOY_USER env vars if needed.
"""
import os
import subprocess
import sys

HOST = os.environ.get("DEPLOY_HOST", "116.74.77.22")
USER = os.environ.get("DEPLOY_USER", "dckakadia")
APP_DIR = "~/purchase_order"

REMOTE_SCRIPT = f"""
set -e
cd {APP_DIR}
ts=$(date +%Y%m%d_%H%M%S)
cp -p data/po/database.db data/po/backup_before_deploy_$ts.db
echo "[1/5] DB backed up -> data/po/backup_before_deploy_$ts.db"
git pull --ff-only origin main
echo "[2/5] now at $(git log --oneline -1)"
venv/bin/pip install -q -r requirements.txt
echo "[3/5] requirements installed"
venv/bin/python -m py_compile purchase_order_app.py database.py
echo "[4/5] syntax OK"
pm2 restart purchase_order --update-env > /dev/null
sleep 4
code=$(curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1:8090/login)
if [ "$code" != "200" ]; then
  echo "[5/5] HEALTH CHECK FAILED (/login returned $code). Recent errors:"
  tail -n 30 logs/purchase_order_error.log
  echo "Roll back with: git reset --hard HEAD@{{1}} && pm2 restart purchase_order"
  exit 1
fi
echo "[5/5] purchase_order restarted and healthy"
"""


def main():
    unpushed = subprocess.run(["git", "log", "origin/main..HEAD", "--oneline"],
                              capture_output=True, text=True).stdout.strip()
    if unpushed:
        print("Local commits not pushed yet - run 'git push origin main' first:\n" + unpushed)
        return 1
    print(f"Deploying origin/main to {USER}@{HOST} ...")
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", f"{USER}@{HOST}", "bash -s"],
        input=REMOTE_SCRIPT, text=True,
    )
    print("Deploy finished." if result.returncode == 0 else "Deploy FAILED - see output above.")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
