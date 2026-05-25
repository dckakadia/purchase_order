"""
Import Landing Cost Calculator — Flask Web Version
Replicates the functionality of Import_Items_Landing_Cost_to_Factory.py
as a web app so it can run on a headless Ubuntu server.

The original Tkinter script is NOT modified — this is a separate new file.
"""
import base64
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent?key={key}"
)


def fmt_inr(n: float) -> str:
    return "₹" + f"{int(round(n)):,}"


def fmt_usd(n: float) -> str:
    return f"${n:.2f}"


def fmt_cur(n: float, currency: str) -> str:
    """Format value in given currency (USD or RMB)."""
    symbol = "¥" if currency == "RMB" else "$"
    return f"{symbol}{n:.2f}"


def calc_landed(items, rate, bank, ship, duty, trans):
    """Core calculation — mirrors the Tkinter _recalc() logic."""
    total_addl = bank + ship + duty + trans
    inv_usd    = sum(it["qty"] * it["unitPrice"] for it in items)
    inv_inr    = inv_usd * rate
    grand      = inv_inr + total_addl

    result = []
    for it in items:
        item_inr   = it["qty"] * it["unitPrice"] * rate
        share      = (item_inr / inv_inr) if inv_inr > 0 else 0
        addl_share = total_addl * share
        total_item = item_inr + addl_share
        per_unit   = (total_item / it["qty"]) if it["qty"] > 0 else 0
        result.append({
            **it,
            "item_inr":   round(item_inr, 2),
            "share":      round(share * 100, 2),
            "addl_share": round(addl_share, 2),
            "total_item": round(total_item, 2),
            "per_unit":   round(per_unit, 2),
            "bank_s":     round(bank * share, 2),
            "ship_s":     round(ship * share, 2),
            "duty_s":     round(duty * share, 2),
            "trans_s":    round(trans * share, 2),
        })

    return {
        "items":       result,
        "inv_usd":     round(inv_usd, 2),
        "inv_inr":     round(inv_inr, 2),
        "total_addl":  round(total_addl, 2),
        "grand":       round(grand, 2),
        "bank":        round(bank, 2),
        "ship":        round(ship, 2),
        "duty":        round(duty, 2),
        "trans":       round(trans, 2),
        "rate":        rate,
    }


# ── Routes ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    data     = request.get_json(force=True)
    items    = data.get('items', [])
    currency = data.get('currency', 'USD')
    # Pick rate based on selected currency
    if currency == 'RMB':
        rate = float(data.get('rmbRate', 11.5))
    else:
        rate = float(data.get('rate', 84))
    bank  = float(data.get('bank', 0))
    ship  = float(data.get('ship', 0))
    duty  = float(data.get('duty', 0))
    trans = float(data.get('trans', 0))
    return jsonify(calc_landed(items, rate, bank, ship, duty, trans))


@app.route('/api/parse-invoice', methods=['POST'])
def api_parse_invoice():
    """Call Gemini to extract items from a PI image/PDF."""
    api_key = request.form.get('api_key', '').strip()
    if not api_key:
        return jsonify({'error': 'Gemini API key is required'}), 400

    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file uploaded'}), 400

    fname = f.filename.lower()
    ext_map = {'.pdf': 'application/pdf', '.jpg': 'image/jpeg',
               '.jpeg': 'image/jpeg', '.png': 'image/png'}
    ext   = os.path.splitext(fname)[1]
    mime  = ext_map.get(ext, 'application/octet-stream')
    b64   = base64.b64encode(f.read()).decode()

    prompt = (
        'Extract all line items from this commercial invoice. '
        'Return ONLY valid JSON, no markdown, no explanation:\n'
        '{"invoiceRef": "invoice number or empty string", '
        '"invoiceDate": "date in YYYY-MM-DD format or empty string", '
        '"currency": "USD or RMB", '
        '"items": [{"name": "item description", "qty": number, "unitPrice": number}]}\n'
        'Rules:\n'
        '- unitPrice = per unit price in the invoice currency\n'
        '- If only total price given, divide by qty to get unitPrice\n'
        '- qty = numeric value only (no units)\n'
        '- currency: return "RMB" if invoice is in CNY/RMB/Yuan, otherwise "USD"'
    )

    payload = json.dumps({
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": mime, "data": b64}},
                {"text": prompt}
            ]
        }]
    }).encode()

    url = GEMINI_URL.format(key=api_key)
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        raw = result["candidates"][0]["content"]["parts"][0]["text"]
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        return jsonify(parsed)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            msg = json.loads(body)["error"]["message"]
        except Exception:
            msg = body[:300]
        return jsonify({'error': f'Gemini API error {e.code}: {msg}'}), 500
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/api/report', methods=['POST'])
def api_report():
    """Generate and return the full HTML landed cost report."""
    data         = request.get_json(force=True)
    items        = data.get('items', [])
    currency     = data.get('currency', 'USD')
    inv_ref      = data.get('invoiceRef', '')
    inv_date     = data.get('invoiceDate', '')
    # Pick rate based on currency
    if currency == 'RMB':
        rate = float(data.get('rmbRate', 11.5))
    else:
        rate = float(data.get('rate', 84))
    bank  = float(data.get('bank', 0))
    ship  = float(data.get('ship', 0))
    duty  = float(data.get('duty', 0))
    trans = float(data.get('trans', 0))

    calc = calc_landed(items, rate, bank, ship, duty, trans)
    c    = calc

    cur_symbol   = "¥" if currency == "RMB" else "$"
    cur_label    = "RMB" if currency == "RMB" else "USD"
    rate_label   = f"1 {cur_label} = ₹{rate:.2f}"

    def summary_box(lbl, val, sub, col, pct):
        return f"""
        <div class="summary-box">
          <div class="s-label">{lbl}</div>
          <div class="s-value" style="color:{col}">{val}</div>
          <div class="s-sub">{sub} <span class="badge" style="background:{col}22;color:{col}">{pct}%</span></div>
        </div>"""

    grand = c['grand']
    summaries = "".join([
        summary_box(f"Invoice Value",   fmt_inr(c['inv_inr']),
                    fmt_cur(c['inv_usd'], currency), "#b8860b",
                    f"{c['inv_inr']/grand*100:.1f}" if grand else "0"),
        summary_box("Bank + Shipping",  fmt_inr(c['bank']+c['ship']),
                    "Bank & Shipping", "#1565c0",
                    f"{(c['bank']+c['ship'])/grand*100:.1f}" if grand else "0"),
        summary_box("Duty + Transport", fmt_inr(c['duty']+c['trans']),
                    "Custom & Local",  "#7b1fa2",
                    f"{(c['duty']+c['trans'])/grand*100:.1f}" if grand else "0"),
        summary_box("Total Landed",     fmt_inr(grand),
                    "Factory Delivered","#c8602a", "100.0"),
    ])

    rows = ""
    for i, it in enumerate(c['items']):
        bg = "#fff" if i % 2 == 0 else "#faf7f2"
        rows += f"""
        <tr style="background:{bg}">
          <td style="text-align:center;color:#7a6e60">{i+1}</td>
          <td style="font-weight:600">{it.get('name') or f'Item {i+1}'}</td>
          <td style="text-align:center">{it['qty']}</td>
          <td style="text-align:center;color:#1565c0">{fmt_cur(it['unitPrice'], currency)}</td>
          <td style="text-align:center;color:#b8860b">{fmt_inr(it['item_inr'])}</td>
          <td style="text-align:center"><span class="badge" style="background:#c8602a22;color:#c8602a">{it['share']:.1f}%</span></td>
          <td style="text-align:center;color:#1565c0">{fmt_inr(it['bank_s'])}</td>
          <td style="text-align:center;color:#1565c0">{fmt_inr(it['ship_s'])}</td>
          <td style="text-align:center;color:#1565c0">{fmt_inr(it['duty_s'])}</td>
          <td style="text-align:center;color:#1565c0">{fmt_inr(it['trans_s'])}</td>
          <td style="text-align:center;font-weight:700;border-right:2px solid #c8602a">{fmt_inr(it['addl_share'])}</td>
          <td style="text-align:center;background:#fff3e0"><strong style="color:#c8602a;font-size:13px">{fmt_inr(it['total_item'])}</strong></td>
          <td style="text-align:center;background:#fff8f0"><strong style="color:#c8602a;font-size:14px">{fmt_inr(it['per_unit'])}</strong><br><span style="color:#7a6e60;font-size:9px">per unit</span></td>
        </tr>"""

    today = date.today().strftime("%d-%m-%Y")
    # Format invoice date for display
    inv_date_display = ''
    if inv_date:
        try:
            from datetime import datetime
            inv_date_display = datetime.strptime(inv_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        except Exception:
            inv_date_display = inv_date

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Landed Cost Report{' — ' + inv_ref if inv_ref else ''}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Fraunces:wght@400;700&display=swap');
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'DM Mono',Courier,monospace;font-size:11px;color:#2d2520;background:#fff;padding:24px;}}
  h1{{font-family:'Fraunces',Georgia,serif;font-size:20px;font-weight:800;color:#2d2520;letter-spacing:-0.5px;}}
  .header{{display:flex;justify-content:space-between;align-items:flex-start;
           border-bottom:2.5px solid #2d2520;padding-bottom:10px;margin-bottom:14px;}}
  .header-right{{text-align:right;color:#7a6e60;font-size:10px;line-height:1.7;}}
  .header-right strong{{color:#2d2520;font-size:12px;}}
  .cost-grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:14px;}}
  .cost-box{{border:1px solid #e2d9c8;border-radius:5px;padding:7px 9px;background:#faf7f2;}}
  .cost-box .lbl{{font-size:8px;color:#7a6e60;margin-bottom:3px;}}
  .cost-box .val{{font-size:12px;font-weight:700;}}
  .summary-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:16px 0;}}
  .summary-box{{border:1px solid #e2d9c8;border-radius:7px;padding:10px 12px;}}
  .s-label{{font-size:9px;color:#7a6e60;letter-spacing:.8px;margin-bottom:4px;text-transform:uppercase;}}
  .s-value{{font-size:16px;font-weight:700;margin-bottom:3px;}}
  .s-sub{{font-size:9px;color:#7a6e60;display:flex;justify-content:space-between;align-items:center;}}
  .badge{{padding:1px 7px;border-radius:20px;font-size:9px;font-weight:600;}}
  table{{width:100%;border-collapse:collapse;font-size:10px;}}
  th{{background:#2d2520;color:#ccc;padding:7px 6px;font-size:9px;font-weight:600;letter-spacing:.5px;white-space:nowrap;}}
  th.hi{{color:#e8845a;font-weight:800;}}
  td{{padding:5px 6px;border-bottom:1px solid #e2d9c8;}}
  tfoot td{{background:#2d2520!important;color:#fff;font-weight:700;padding:8px 6px;}}
  tfoot .grand{{background:#c8602a!important;text-align:center;}}
  tfoot .grand .g-val{{font-size:14px;font-weight:800;color:#fff;}}
  tfoot .grand .g-sub{{font-size:8px;color:#ffd54f;margin-top:2px;}}
  .footer{{margin-top:10px;border-top:1px solid #e2d9c8;padding-top:6px;
           display:flex;justify-content:space-between;font-size:8.5px;color:#7a6e60;}}
  .no-print{{margin-bottom:16px;text-align:center;}}
  .print-btn{{background:#c8602a;color:#fff;border:none;border-radius:7px;
              padding:10px 28px;font-size:14px;cursor:pointer;font-family:inherit;font-weight:600;}}
  .print-btn:hover{{background:#a0491e;}}
  @media print{{.no-print{{display:none!important;}}@page{{margin:1cm;size:A4 landscape;}}}}
</style>
</head>
<body>
<div class="no-print"><button class="print-btn" onclick="window.print()">🖨 &nbsp;Print / Save as PDF</button></div>
<div class="header">
  <div>
    <div style="font-size:10px;color:#c8602a;letter-spacing:2px;margin-bottom:4px">IMPORT COST CALCULATOR</div>
    <h1>China → India Landed Cost Report</h1>
    <div style="font-size:9px;color:#7a6e60;margin-top:3px">Item-Wise Breakdown with Proportional Cost Allocation</div>
  </div>
  <div class="header-right">
    {'<strong>Invoice Ref: ' + inv_ref + '</strong><br>' if inv_ref else ''}
    {'Invoice Date: ' + inv_date_display + '<br>' if inv_date_display else ''}
    Report Date: {today}<br>
    Currency: {cur_label} &nbsp;|&nbsp; {rate_label}
  </div>
</div>
<div class="cost-grid">
  {''.join(f'<div class="cost-box"><div class="lbl">{l}</div><div class="val">{v}</div></div>' for l,v in [
    (f"Invoice Value ({cur_label})", fmt_cur(c['inv_usd'], currency)),
    ("Invoice Value (INR)",          fmt_inr(c['inv_inr'])),
    ("Bank Charges",                 fmt_inr(c['bank'])),
    ("Shipping Cost",                fmt_inr(c['ship'])),
    ("Custom Duty",                  fmt_inr(c['duty'])),
    ("Local Transport",              fmt_inr(c['trans'])),
  ])}
</div>
<table>
  <thead>
    <tr>
      <th>#</th><th style="text-align:left">Item / Description</th><th>Qty</th>
      <th>Unit Price ({cur_label})</th><th>Invoice Value (INR)</th><th>Share</th>
      <th>Bank Charges</th><th>Shipping</th><th>Custom Duty</th><th>Local Trans.</th>
      <th style="border-right:2px solid #c8602a">Total Addl.</th>
      <th class="hi">TOTAL LANDED (INR)</th>
      <th class="hi">PER UNIT (INR)</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
  <tfoot>
    <tr>
      <td colspan="4" style="color:#fff;font-weight:700">GRAND TOTAL</td>
      <td style="text-align:center;color:#ffd54f;font-weight:700">{fmt_inr(c['inv_inr'])}</td>
      <td style="text-align:center;color:#aaa">100%</td>
      <td style="text-align:center;color:#90caf9">{fmt_inr(c['bank'])}</td>
      <td style="text-align:center;color:#90caf9">{fmt_inr(c['ship'])}</td>
      <td style="text-align:center;color:#90caf9">{fmt_inr(c['duty'])}</td>
      <td style="text-align:center;color:#90caf9">{fmt_inr(c['trans'])}</td>
      <td style="text-align:center;color:#fff;font-weight:700;border-right:2px solid #c8602a">{fmt_inr(c['total_addl'])}</td>
      <td colspan="2" class="grand">
        <div class="g-val">{fmt_inr(grand)}</div>
        <div class="g-sub">TOTAL LANDED COST</div>
      </td>
    </tr>
  </tfoot>
</table>
<div class="summary-grid">{summaries}</div>
<div class="footer">
  <span>Additional costs allocated proportionally by invoice value share.</span>
  <strong style="color:#2d2520">Total Landed: {fmt_inr(grand)} &nbsp;|&nbsp; Invoice: {fmt_cur(c['inv_usd'], currency)} @ ₹{rate:.2f}</strong>
</div>
</body></html>"""

    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


# ── Frontend HTML ─────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Import Landing Cost Calculator</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Courier New',monospace;background:#f5f0e8;color:#2d2520;min-height:100vh;padding:20px;}
.top-bar{display:flex;align-items:center;justify-content:space-between;max-width:1400px;margin:0 auto 16px;padding:10px 16px;background:#fff;border:2px solid #2d2520;border-radius:4px;}
.top-bar a{font-size:12px;color:#7a6e60;text-decoration:none;border:1px solid #e2d9c8;padding:5px 12px;border-radius:3px;}
.top-bar a:hover{background:#f0ebe0;}
.top-bar h2{font-size:14px;letter-spacing:1px;color:#c8602a;}
.container{max-width:1400px;margin:0 auto;}
.header{text-align:center;margin-bottom:24px;border-bottom:2px solid #2d2520;padding-bottom:16px;}
.header h1{font-size:24px;margin-bottom:4px;}
.header p{font-size:12px;color:#7a6e60;}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px;}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}
.card{border:2px solid #2d2520;background:#fff;padding:18px;}
.card-title{font-size:13px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #e2d9c8;padding-bottom:8px;margin-bottom:14px;color:#2d2520;}
.form-group{margin-bottom:12px;}
label{display:block;font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;color:#7a6e60;}
input[type=text],input[type=number],input[type=date],select{width:100%;border:2px solid #2d2520;padding:8px 10px;font-family:'Courier New',monospace;font-size:13px;background:#fff;outline:none;}
input[type=text]:focus,input[type=number]:focus,input[type=date]:focus,select:focus{border-color:#c8602a;}
input.red-val{color:#c62828;font-weight:bold;}
select{cursor:pointer;}
button{background:#fff;border:2px solid #2d2520;padding:9px 16px;font-family:'Courier New',monospace;font-size:13px;cursor:pointer;margin:3px;}
button:hover{background:#2d2520;color:#fff;}
button.primary{background:#2d2520;color:#fff;font-weight:bold;}
button.primary:hover{background:#444;}
button.danger{border-color:#c62828;color:#c62828;}
button.danger:hover{background:#c62828;color:#fff;}
button.success{border-color:#2e7d32;color:#2e7d32;}
button.success:hover{background:#2e7d32;color:#fff;}
button.orange{border-color:#c8602a;color:#c8602a;}
button.orange:hover{background:#c8602a;color:#fff;}
.file-drop{border:2px dashed #c8602a;padding:16px;text-align:center;cursor:pointer;color:#7a6e60;font-size:12px;background:#fdf9f5;transition:.2s;}
.file-drop:hover{background:#f5ede3;}
.file-drop input{display:none;}
table{width:100%;border-collapse:collapse;margin-top:10px;font-size:12px;}
th{background:#2d2520;color:#e8d8c0;padding:8px 6px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;}
td{border-bottom:1px solid #e2d9c8;padding:7px 6px;}
tr:nth-child(even) td{background:#faf7f2;}
td input{border:1px solid #ccc;padding:4px 6px;width:100%;font-family:'Courier New',monospace;font-size:12px;}
.result-box{background:#f9f6ef;border:2px solid #2d2520;padding:16px;margin-top:10px;}
.result-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:12px;}
.r-item{border:1px solid #e2d9c8;padding:10px 12px;background:#fff;}
.r-label{font-size:10px;color:#7a6e60;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px;}
.r-value{font-size:18px;font-weight:700;color:#2d2520;}
.r-value.orange{color:#c8602a;}
.r-value.blue{color:#1565c0;}
.r-value.green{color:#2e7d32;}
.msg{padding:10px 14px;margin:8px 0;font-size:12px;border-left:4px solid;}
.msg.info{background:#e3f2fd;border-color:#1565c0;color:#1565c0;}
.msg.error{background:#ffebee;border-color:#c62828;color:#c62828;}
.msg.ok{background:#e8f5e9;border-color:#2e7d32;color:#2e7d32;}
.calc-table-wrap{overflow-x:auto;}
.calc-table th{background:#2d2520;white-space:nowrap;}
.calc-table td{white-space:nowrap;}
.calc-table tfoot td{background:#2d2520;color:#ffd54f;font-weight:700;font-size:12px;}
.calc-table tfoot td.grand-cell{background:#c8602a;color:#fff;text-align:center;}
#statusMsg{min-height:28px;}
</style>
</head>
<body>

<div class="top-bar">
  <a href="/">← Portal</a>
  <h2>🏭 Import Landing Cost Calculator</h2>
  <span style="font-size:12px;color:#7a6e60">China → India</span>
</div>

<div class="container">
  <div class="header">
    <h1>China → India Import Cost Calculator</h1>
    <p>Calculates item-wise landed cost with proportional allocation of bank charges, shipping, duty &amp; transport</p>
  </div>

  <!-- Row 1: Rate + Additional Costs -->
  <div class="grid-3">
    <!-- Exchange & Invoice -->
    <div class="card">
      <div class="card-title">Exchange &amp; Invoice</div>
      <div class="form-group">
        <label>Invoice Reference</label>
        <input type="text" id="invoiceRef" placeholder="e.g. PI-2024-001">
      </div>
      <div class="form-group">
        <label>Invoice Date</label>
        <input type="date" id="invoiceDate">
      </div>
      <div class="form-group">
        <label>Currency</label>
        <select id="currency" onchange="onCurrencyChange()">
          <option value="USD">USD — US Dollar</option>
          <option value="RMB">RMB — Chinese Yuan (CNY)</option>
        </select>
      </div>
      <div class="form-group" id="row-usd">
        <label>USD → INR Rate</label>
        <input type="number" id="usdRate" class="red-val" value="84.00" step="0.01">
      </div>
      <div class="form-group" id="row-rmb" style="display:none">
        <label>RMB → INR Rate</label>
        <input type="number" id="rmbRate" class="red-val" value="11.50" step="0.01">
      </div>
    </div>

    <!-- Additional Costs -->
    <div class="card">
      <div class="card-title">Additional Costs (₹ INR)</div>
      <div class="form-group">
        <label>Bank Charges (₹)</label>
        <input type="number" id="bankCharges" class="red-val" value="0" step="1">
      </div>
      <div class="form-group">
        <label>Shipping Cost (₹)</label>
        <input type="number" id="shipping" class="red-val" value="0" step="1">
      </div>
    </div>

    <div class="card">
      <div class="card-title">Duty &amp; Transport (₹ INR)</div>
      <div class="form-group">
        <label>Custom Duty (₹)</label>
        <input type="number" id="customDuty" class="red-val" value="0" step="1">
      </div>
      <div class="form-group">
        <label>Local Transport (₹)</label>
        <input type="number" id="localTrans" class="red-val" value="0" step="1">
      </div>
    </div>
  </div>

  <!-- Row 2: AI Scanner + Summary -->
  <div class="grid-2">
    <!-- AI Scanner -->
    <div class="card">
      <div class="card-title">🤖 AI Invoice Scanner (Gemini)</div>
      <div class="form-group">
        <label>Gemini API Key</label>
        <input type="text" id="geminiKey" placeholder="AIzaSy...">
      </div>
      <div class="file-drop" onclick="document.getElementById('piFile').click()">
        <input type="file" id="piFile" accept=".pdf,.jpg,.jpeg,.png" onchange="handleFileSelect(this)">
        <div id="fileLabel">📄 Click to upload PI (PDF / JPG / PNG)</div>
      </div>
      <div style="margin-top:10px;">
        <button class="orange" onclick="scanInvoice()">🤖 Scan &amp; Auto-Fill Items</button>
      </div>
      <div id="scanMsg"></div>
    </div>

    <!-- Summary -->
    <div class="card">
      <div class="card-title">📊 Cost Summary</div>
      <div class="result-grid" id="summaryGrid">
        <div class="r-item"><div class="r-label" id="labelInvoiceCur">Invoice (USD)</div><div class="r-value blue" id="s-inv-usd">$0.00</div></div>
        <div class="r-item"><div class="r-label">Invoice (INR)</div><div class="r-value" id="s-inv-inr">₹0</div></div>
        <div class="r-item"><div class="r-label">Additional Costs</div><div class="r-value blue" id="s-addl">₹0</div></div>
        <div class="r-item"><div class="r-label">Total Landed Cost</div><div class="r-value orange" id="s-grand">₹0</div></div>
      </div>
      <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap;">
        <button class="primary" onclick="calculate()">⚡ Calculate</button>
        <button class="success" onclick="openReport()">📄 View Report</button>
      </div>
      <div id="statusMsg"></div>
    </div>
  </div>

  <!-- Items Table -->
  <div class="card" style="margin-bottom:16px;">
    <div class="card-title" style="display:flex;align-items:center;justify-content:space-between;">
      Invoice Items
      <div>
        <button onclick="addRow()">+ Add Item</button>
        <button class="danger" onclick="clearItems()">✕ Clear All</button>
      </div>
    </div>
    <table id="itemsTable">
      <thead>
        <tr>
          <th>#</th><th>Item Description</th><th>Qty</th><th id="thUnitPrice">Unit Price (USD)</th><th>Value (INR)</th><th>Action</th>
        </tr>
      </thead>
      <tbody id="itemsBody">
      </tbody>
    </table>
  </div>

  <!-- Calculation Result Table -->
  <div class="card calc-table-wrap" id="resultSection" style="display:none;margin-bottom:20px;">
    <div class="card-title">Landed Cost Breakdown</div>
    <table class="calc-table">
      <thead>
        <tr>
          <th>#</th><th>Item</th><th>Qty</th><th id="thCalcUnitPrice">Unit (USD)</th><th>Invoice ₹</th><th>Share%</th>
          <th>Bank</th><th>Shipping</th><th>Duty</th><th>Transport</th><th>Total Addl.</th>
          <th style="color:#e8845a">Total Landed ₹</th><th style="color:#e8845a">Per Unit ₹</th>
        </tr>
      </thead>
      <tbody id="calcBody"></tbody>
      <tfoot id="calcFoot"></tfoot>
    </table>
  </div>

</div><!-- /container -->

<script>
let items = [];
let lastCalc = null;

// ── helpers ──────────────────────────────────────────────────────
const fmtInr = n => '₹' + Math.round(n).toLocaleString('en-IN');
const fmtUsd = n => '$' + Number(n).toFixed(2);
const fmtCur = (n, cur) => (cur === 'RMB' ? '¥' : '$') + Number(n).toFixed(2);
const v = id  => parseFloat(document.getElementById(id).value) || 0;
const msg = (id, text, type) => {
  const el = document.getElementById(id);
  el.innerHTML = text ? `<div class="msg ${type}">${text}</div>` : '';
};

function getCurrency() {
  return document.getElementById('currency').value;
}

function getRate() {
  return getCurrency() === 'RMB' ? v('rmbRate') : v('usdRate');
}

function getInputs() {
  return {
    currency: getCurrency(),
    rate:     v('usdRate'),
    rmbRate:  v('rmbRate'),
    bank:     v('bankCharges'),
    ship:     v('shipping'),
    duty:     v('customDuty'),
    trans:    v('localTrans')
  };
}

// ── Currency toggle ───────────────────────────────────────────────
function onCurrencyChange() {
  const cur   = getCurrency();
  const isUSD = cur === 'USD';
  const sym   = isUSD ? '$' : '¥';

  document.getElementById('row-usd').style.display = isUSD ? '' : 'none';
  document.getElementById('row-rmb').style.display = isUSD ? 'none' : '';

  // Update summary label
  document.getElementById('labelInvoiceCur').textContent = `Invoice (${cur})`;

  // Update items table header
  document.getElementById('thUnitPrice').textContent    = `Unit Price (${cur})`;
  document.getElementById('thCalcUnitPrice').textContent = `Unit (${cur})`;

  // Refresh live values
  quickUpdate();
}

// ── Item table ────────────────────────────────────────────────────
function renderTable() {
  const tbody = document.getElementById('itemsBody');
  const rate  = getRate();
  const cur   = getCurrency();
  tbody.innerHTML = items.map((it, i) => {
    const val = it.qty * it.unitPrice * rate;
    return `<tr>
      <td style="text-align:center;color:#7a6e60">${i+1}</td>
      <td><input value="${escHtml(it.name)}" onchange="items[${i}].name=this.value" style="min-width:180px;"></td>
      <td><input type="number" value="${it.qty}" onchange="items[${i}].qty=+this.value;quickUpdate()" style="width:70px;text-align:center;"></td>
      <td><input type="number" value="${it.unitPrice}" step="0.01" onchange="items[${i}].unitPrice=+this.value;quickUpdate()" style="width:100px;text-align:center;color:#1565c0;font-weight:bold;"></td>
      <td style="color:#b8860b;font-weight:600;text-align:center;">${fmtInr(val)}</td>
      <td><button class="danger" onclick="removeRow(${i})">✕</button></td>
    </tr>`;
  }).join('');
}

function escHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function addRow() {
  items.push({name: `Item ${items.length + 1}`, qty: 1, unitPrice: 0});
  renderTable();
}

function removeRow(i) { items.splice(i, 1); renderTable(); quickUpdate(); }
function clearItems() { items = []; renderTable(); quickUpdate(); document.getElementById('resultSection').style.display='none'; }

function quickUpdate() {
  const inp    = getInputs();
  const rate   = getRate();
  const cur    = getCurrency();
  const sym    = cur === 'RMB' ? '¥' : '$';
  const invUsd = items.reduce((s,it) => s + it.qty * it.unitPrice, 0);
  const invInr = invUsd * rate;
  const addl   = inp.bank + inp.ship + inp.duty + inp.trans;
  const grand  = invInr + addl;

  document.getElementById('s-inv-usd').textContent = fmtCur(invUsd, cur);
  document.getElementById('s-inv-inr').textContent = fmtInr(invInr);
  document.getElementById('s-addl').textContent    = fmtInr(addl);
  document.getElementById('s-grand').textContent   = fmtInr(grand);
  renderTable();
}

// Auto-update on input change
['usdRate','rmbRate','bankCharges','shipping','customDuty','localTrans'].forEach(id => {
  document.getElementById(id).addEventListener('input', quickUpdate);
});

// ── Calculate ─────────────────────────────────────────────────────
async function calculate() {
  if (!items.length) { msg('statusMsg','Add at least one item first.','error'); return; }
  const inp     = getInputs();
  const payload = { items, ...inp };
  try {
    const res  = await fetch('/api/calculate', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const data = await res.json();
    lastCalc = data;
    renderCalcTable(data);
    msg('statusMsg','Calculation complete. Click "View Report" for printable output.','ok');
  } catch(e) { msg('statusMsg','Calculation error: '+e.message,'error'); }
}

function renderCalcTable(d) {
  const sec  = document.getElementById('resultSection');
  const body = document.getElementById('calcBody');
  const foot = document.getElementById('calcFoot');
  const cur  = getCurrency();
  sec.style.display = '';

  body.innerHTML = d.items.map((it,i) => {
    const bg = i%2===0 ? '#fff' : '#faf7f2';
    return `<tr style="background:${bg}">
      <td style="text-align:center;color:#7a6e60">${i+1}</td>
      <td style="font-weight:600">${escHtml(it.name||'Item '+(i+1))}</td>
      <td style="text-align:center">${it.qty}</td>
      <td style="text-align:center;color:#1565c0">${fmtCur(it.unitPrice, cur)}</td>
      <td style="text-align:center;color:#b8860b">${fmtInr(it.item_inr)}</td>
      <td style="text-align:center"><span style="background:#c8602a22;color:#c8602a;padding:1px 6px;border-radius:10px;">${it.share.toFixed(1)}%</span></td>
      <td style="text-align:center;color:#1565c0">${fmtInr(it.bank_s)}</td>
      <td style="text-align:center;color:#1565c0">${fmtInr(it.ship_s)}</td>
      <td style="text-align:center;color:#1565c0">${fmtInr(it.duty_s)}</td>
      <td style="text-align:center;color:#1565c0">${fmtInr(it.trans_s)}</td>
      <td style="text-align:center;font-weight:700;border-right:2px solid #c8602a">${fmtInr(it.addl_share)}</td>
      <td style="text-align:center;background:#fff3e0"><strong style="color:#c8602a">${fmtInr(it.total_item)}</strong></td>
      <td style="text-align:center;background:#fff8f0"><strong style="color:#c8602a">${fmtInr(it.per_unit)}</strong><br><span style="color:#7a6e60;font-size:9px">per unit</span></td>
    </tr>`;
  }).join('');

  foot.innerHTML = `<tr>
    <td colspan="4" style="color:#fff">GRAND TOTAL</td>
    <td style="text-align:center;color:#ffd54f">${fmtInr(d.inv_inr)}</td>
    <td style="text-align:center;color:#aaa">100%</td>
    <td style="text-align:center;color:#90caf9">${fmtInr(d.bank)}</td>
    <td style="text-align:center;color:#90caf9">${fmtInr(d.ship)}</td>
    <td style="text-align:center;color:#90caf9">${fmtInr(d.duty)}</td>
    <td style="text-align:center;color:#90caf9">${fmtInr(d.trans)}</td>
    <td style="text-align:center;color:#fff;font-weight:700;border-right:2px solid #c8602a">${fmtInr(d.total_addl)}</td>
    <td colspan="2" class="grand-cell"><div style="font-size:14px;font-weight:800">${fmtInr(d.grand)}</div><div style="font-size:9px;color:#ffd54f">TOTAL LANDED COST</div></td>
  </tr>`;
}

// ── Report ────────────────────────────────────────────────────────
async function openReport() {
  if (!items.length) { msg('statusMsg','Add items first.','error'); return; }
  const inp     = getInputs();
  const payload = {
    items,
    ...inp,
    invoiceRef:  document.getElementById('invoiceRef').value,
    invoiceDate: document.getElementById('invoiceDate').value,
  };
  const res  = await fetch('/api/report', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const html = await res.text();
  const w = window.open('', '_blank');
  w.document.write(html);
  w.document.close();
}

// ── AI Scanner ────────────────────────────────────────────────────
function handleFileSelect(inp) {
  if (inp.files[0]) {
    document.getElementById('fileLabel').textContent = '📎 ' + inp.files[0].name;
  }
}

async function scanInvoice() {
  const keyEl  = document.getElementById('geminiKey');
  const fileEl = document.getElementById('piFile');
  if (!keyEl.value.trim()) { msg('scanMsg','Enter your Gemini API key first.','error'); return; }
  if (!fileEl.files[0])    { msg('scanMsg','Select a PI file first.','error'); return; }

  msg('scanMsg','🤖 Sending to Gemini AI… please wait','info');
  const fd = new FormData();
  fd.append('api_key', keyEl.value.trim());
  fd.append('file', fileEl.files[0]);

  try {
    const res  = await fetch('/api/parse-invoice', {method:'POST', body:fd});
    const data = await res.json();
    if (data.error) { msg('scanMsg','Error: '+data.error,'error'); return; }

    if (data.invoiceRef)  document.getElementById('invoiceRef').value  = data.invoiceRef;
    if (data.invoiceDate) document.getElementById('invoiceDate').value = data.invoiceDate;
    if (data.currency && (data.currency === 'USD' || data.currency === 'RMB')) {
      document.getElementById('currency').value = data.currency;
      onCurrencyChange();
    }
    if (data.items && data.items.length) {
      items = data.items.map(it => ({
        name:      it.name || '',
        qty:       Number(it.qty) || 1,
        unitPrice: Number(it.unitPrice) || 0
      }));
      renderTable();
      quickUpdate();
      msg('scanMsg',`✅ Extracted ${items.length} items from invoice.`,'ok');
    } else {
      msg('scanMsg','No items found in the invoice.','error');
    }
  } catch(e) { msg('scanMsg','Error: '+e.message,'error'); }
}

// Init
addRow();
</script>
</body>
</html>"""


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=False)
