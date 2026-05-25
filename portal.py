from flask import Flask, jsonify, render_template_string, request, session, redirect
from functools import wraps
import socket
import os

app = Flask(__name__)
app.secret_key = os.environ.get('PORTAL_SECRET', 'gw-portal-s3cr3t-k3y-2026')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False

# ── CREDENTIALS ───────────────────────────────────────────────────────────────
PORTAL_USER     = "dckakadia"
PORTAL_PASSWORD = "Devin@404404"
# ─────────────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        'id': 'gst',
        'name': 'GST_BOE_Landing Cost',
        'description': 'Unified access to GST Reconciliation, PI -> BOE Calculations, and Import Landing Cost.',
        'port': 5001, 'path': '/gst/', 'tag': 'IMPORT', 'color_var': 'blue',
    },
    
    
    {
        'id': 'po',
        'name': 'Purchase Order Tool',
        'description': 'Draft professional POs for China suppliers. Manages supplier details and generates PDFs.',
        'port': 5005, 'path': '/po/', 'tag': 'ORDERS', 'color_var': 'amber',
        },
        {
            'id': 'spa',
            'name': 'SpaTrack Pro',
            'description': 'Manufacturing cost manager. Track items, products, BOM and cost sheets for spa manufacturing.',
            'port': 8081, 'path': '/spa/', 'tag': 'SPA', 'color_var': 'pink',
        },
]


def check_port(port: int) -> bool:
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.5):
            return True
    except Exception:
        return False


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


# ── AUTH CHECK ENDPOINT (used by nginx auth_request) ─────────────────────────
# Returns 200 if logged in, 401 if not. nginx checks this before every tool.

@app.route('/auth')
def auth():
    if session.get('logged_in'):
        return '', 200
    return '', 401


# ── LOGIN ─────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect('/')
    error = None
    if request.method == 'POST':
        u = request.form.get('username', '').strip()
        p = request.form.get('password', '').strip()
        if u == PORTAL_USER and p == PORTAL_PASSWORD:
            session['logged_in'] = True
            return redirect('/')
        error = 'Invalid username or password.'
    return render_template_string(LOGIN_HTML, error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ── PROTECTED ROUTES ──────────────────────────────────────────────────────────

@app.route('/api/status')
@login_required
def api_status():
    return jsonify({t['id']: check_port(t['port']) for t in TOOLS})


@app.route('/')
@login_required
def index():
    return render_template_string(PORTAL_HTML, tools=TOOLS)


# ── LOGIN PAGE HTML ───────────────────────────────────────────────────────────

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login — Business Tools Portal</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root { --bg:#0b0e17; --card:#181c2e; --border:#252a42; --text:#e8ecf5; --muted:#6b7499; --blue:#4f8ef7; --violet:#a78bfa; --amber:#fbbf24; --red:#f87171; --font-ui:'Syne',sans-serif; --font-mono:'DM Mono',monospace; }
    * { box-sizing:border-box; margin:0; padding:0; }
    body { font-family:var(--font-ui); background:var(--bg); color:var(--text); min-height:100vh; display:flex; align-items:center; justify-content:center; }
    .login-wrap { width:100%; max-width:420px; padding:24px; }
    .login-card { background:var(--card); border:1px solid var(--border); border-radius:16px; padding:40px 36px; }
    .brand { font-family:var(--font-mono); font-size:11px; color:var(--amber); letter-spacing:.1em; margin-bottom:10px; }
    .login-title { font-size:26px; font-weight:800; color:#fff; margin-bottom:6px; }
    .login-title span { background:linear-gradient(90deg,var(--blue),var(--violet)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
    .login-sub { font-size:12px; color:var(--muted); margin-bottom:32px; }
    label { display:block; font-family:var(--font-mono); font-size:10px; letter-spacing:.08em; color:var(--muted); margin-bottom:6px; text-transform:uppercase; }
    input { width:100%; background:#0f1320; border:1px solid var(--border); border-radius:8px; color:var(--text); font-family:var(--font-mono); font-size:14px; padding:11px 14px; margin-bottom:20px; outline:none; transition:.2s; }
    input:focus { border-color:var(--blue); }
    .btn-login { width:100%; padding:12px; background:linear-gradient(90deg,var(--blue),var(--violet)); border:none; border-radius:8px; color:#fff; font-family:var(--font-ui); font-size:15px; font-weight:700; cursor:pointer; margin-top:4px; transition:.15s; }
    .btn-login:hover { opacity:.9; transform:translateY(-1px); }
    .error { background:rgba(248,113,113,.12); border:1px solid var(--red); border-radius:8px; padding:10px 14px; font-size:12px; color:var(--red); margin-bottom:20px; font-family:var(--font-mono); }
    .lock-icon { font-size:36px; margin-bottom:20px; }
    .footer-note { text-align:center; margin-top:20px; font-size:11px; color:var(--muted); font-family:var(--font-mono); }
  </style>
</head>
<body>
  <div class="login-wrap">
    <div class="login-card">
      <div class="lock-icon">🔐</div>
      <div class="brand">IMPORT & GST SUITE</div>
      <div class="login-title">Business <span>Tools</span> Portal</div>
      <div class="login-sub">// Authorised access only — enter your credentials</div>
      {% if error %}<div class="error">⚠ {{ error }}</div>{% endif %}
      <form method="POST">
        <label>Username</label>
        <input type="text" name="username" autofocus autocomplete="username" placeholder="Enter username">
        <label>Password</label>
        <input type="password" name="password" autocomplete="current-password" placeholder="Enter password">
        <button type="submit" class="btn-login">Sign In →</button>
      </form>
    </div>
    <div class="footer-note">Greenwave Traders Pvt Ltd · Internal Portal</div>
  </div>
</body>
</html>"""


# ── PORTAL DASHBOARD HTML ─────────────────────────────────────────────────────

PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Import & GST Tools — Portal</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root { --bg:#0b0e17; --surface:#121520; --card:#181c2e; --border:#252a42; --text:#e8ecf5; --muted:#6b7499; --blue:#4f8ef7; --violet:#a78bfa; --emerald:#34d399; --amber:#fbbf24; --pink:#f472b6; --green:#4ade80; --red:#f87171; --radius:14px; --font-ui:'Syne',sans-serif; --font-mono:'DM Mono',monospace; }
    * { box-sizing:border-box; margin:0; padding:0; }
    body { font-family:var(--font-ui); background:var(--bg); color:var(--text); min-height:100vh; padding:0 28px; }
    .wrapper { max-width:1180px; margin:0 auto; }
    header { padding:44px 0 36px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:flex-end; }
    h1 span { background:linear-gradient(90deg,var(--blue),var(--violet)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
    .logout-btn { font-family:var(--font-mono); font-size:11px; background:rgba(248,113,113,.1); border:1px solid rgba(248,113,113,.3); color:var(--red); padding:7px 16px; border-radius:6px; text-decoration:none; transition:.15s; }
    .logout-btn:hover { background:rgba(248,113,113,.2); }
    .tools-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:20px; padding:40px 0; }
    .tool-card { background:var(--card); border:1px solid var(--border); border-radius:var(--radius); display:flex; flex-direction:column; transition:.2s; }
    .tool-card:hover { transform:translateY(-3px); }
    .card-strip { height:3px; border-radius:var(--radius) var(--radius) 0 0; }
    .card-strip.blue    { background:var(--blue); }
    .card-strip.violet  { background:var(--violet); }
    .card-strip.emerald { background:var(--emerald); }
    .card-strip.amber   { background:var(--amber); }
    .card-strip.pink    { background:#f472b6; }
    .card-body { padding:24px; flex:1; }
    .card-tag { font-family:var(--font-mono); font-size:10px; padding:3px 8px; border-radius:4px; background:rgba(255,255,255,.05); letter-spacing:.06em; }
    .card-name { font-size:18px; font-weight:700; margin:14px 0 6px; color:#fff; }
    .card-desc { font-size:13px; color:var(--muted); line-height:1.6; }
    .status-badge { font-family:var(--font-mono); font-size:11px; padding:12px 24px; border-top:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; }
    .open-btn { color:white; text-decoration:none; padding:8px 18px; border-radius:6px; font-weight:700; font-size:13px; transition:.15s; }
    .open-btn.blue    { background:var(--blue); }
    .open-btn.violet  { background:var(--violet); }
    .open-btn.emerald { background:var(--emerald); color:#0b0e17; }
    .open-btn.amber   { background:var(--amber); color:#0b0e17; }
    .open-btn.pink    { background:#f472b6; color:#fff; }
    .open-btn.disabled { background:#333; pointer-events:none; opacity:.45; color:#888; }
    .stats-bar { display:flex; gap:20px; padding-bottom:40px; }
    .stat-item { background:var(--surface); border:1px solid var(--border); padding:16px 20px; border-radius:10px; min-width:150px; }
    .stat-label { font-family:var(--font-mono); font-size:10px; color:var(--muted); margin-bottom:6px; letter-spacing:.06em; }
    .stat-val { font-size:24px; font-weight:800; color:#fff; }
  </style>
</head>
<body>
<div class="wrapper">
  <header>
    <div>
      <div style="color:var(--amber);font-family:var(--font-mono);font-size:11px;margin-bottom:6px;letter-spacing:.08em">IMPORT & GST SUITE</div>
      <h1>Business <span>Tools</span> Portal</h1>
      <p style="color:var(--muted);font-family:var(--font-mono);font-size:11px;margin-top:6px">// All your tools — one dashboard</p>
    </div>
    <a href="/logout" class="logout-btn">⬡ Sign Out</a>
  </header>
  <div class="tools-grid">
    {% for t in tools %}
    <div class="tool-card">
      <div class="card-strip {{ t.color_var }}"></div>
      <div class="card-body">
        <span class="card-tag">{{ t.tag }}</span>
        <div class="card-name">{{ t.name }}</div>
        <div class="card-desc">{{ t.description }}</div>
      </div>
      <div class="status-badge">
        <span id="status-{{ t.id }}" style="color:var(--muted)">● Checking…</span>
        <a href="{{ t.path }}" id="btn-{{ t.id }}" class="open-btn {{ t.color_var }} disabled">Open Tool</a>
      </div>
    </div>
    {% endfor %}
  </div>
  <div class="stats-bar">
    <div class="stat-item"><div class="stat-label">TOTAL TOOLS</div><div class="stat-val">{{ tools|length }}</div></div>
    <div class="stat-item"><div class="stat-label">ONLINE</div><div id="onlineCount" class="stat-val" style="color:var(--green)">--</div></div>
    <div class="stat-item"><div class="stat-label">PLATFORM</div><div class="stat-val" style="font-size:16px;padding-top:4px">Ubuntu 24</div></div>
  </div>
</div>
<script>
  async function checkStatus() {
    try {
      const data = await fetch('/api/status').then(r => r.json());
      let online = 0;
      for (const [id, up] of Object.entries(data)) {
        const badge = document.getElementById('status-' + id);
        const btn   = document.getElementById('btn-' + id);
        if (!badge) continue; if (up) { badge.innerText = '● Online'; badge.style.color = '#4ade80'; btn.classList.remove('disabled'); online++; }
        else    { badge.innerText = '○ Offline'; badge.style.color = '#6b7499'; btn.classList.add('disabled'); }
      }
      document.getElementById('onlineCount').textContent = online;
    } catch(e) {}
  }
  checkStatus(); setInterval(checkStatus, 15000);
</script>
</body>
</html>"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
