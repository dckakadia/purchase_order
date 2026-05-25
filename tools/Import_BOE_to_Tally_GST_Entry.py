from flask import Flask, render_template_string, request, jsonify
import json
import base64
import os
import re
import google.generativeai as genai

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PI → BOE Calculator</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Courier New', monospace;
  background: #fff;
  color: #000;
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}
.header {
  text-align: center;
  margin-bottom: 30px;
  border-bottom: 2px solid #000;
  padding-bottom: 20px;
}
h1 { font-size: 28px; margin-bottom: 5px; }
.subtitle { font-size: 14px; }

.grid-2 { 
  display: grid; 
  grid-template-columns: 1fr 1fr; 
  gap: 20px; 
  margin-bottom: 20px;
}

.card {
  border: 2px solid #000;
  padding: 20px;
  background: #fff;
}
.card-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 15px;
  text-transform: uppercase;
  border-bottom: 1px solid #000;
  padding-bottom: 10px;
}

.input-red { color: #FF0000; }
.output-green { color: #008000; }
.formula-black { color: #000; }

.form-group {
  margin-bottom: 15px;
}
label {
  display: block;
  font-size: 12px;
  font-weight: bold;
  margin-bottom: 5px;
  text-transform: uppercase;
}
input {
  width: 100%;
  background: #fff;
  border: 2px solid #000;
  padding: 10px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}
input:focus {
  outline: none;
  border-color: #666;
}
input.red { color: #FF0000; font-weight: bold; }
input.green { color: #008000; font-weight: bold; }

table {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
  border: 2px solid #000;
}
th, td {
  border: 1px solid #000;
  padding: 10px;
  text-align: left;
  font-size: 13px;
}
th {
  background: #000;
  color: #fff;
  font-weight: bold;
  text-transform: uppercase;
}
tr:nth-child(even) {
  background: #f5f5f5;
}
.total-row {
  font-weight: bold;
  background: #e0e0e0 !important;
}

button {
  background: #fff;
  border: 2px solid #000;
  padding: 12px 20px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  cursor: pointer;
  margin: 5px;
}
button:hover {
  background: #000;
  color: #fff;
}
button:active {
  transform: scale(0.98);
}
.btn-primary { font-weight: bold; }
.btn-danger { color: #FF0000; border-color: #FF0000; }
.btn-danger:hover { background: #FF0000; color: #fff; }
.btn-success { color: #008000; border-color: #008000; }
.btn-success:hover { background: #008000; color: #fff; }

/* Print Styles */
@media print {
  body {
    padding: 10px;
    max-width: 100%;
    font-size: 10px;
  }
  .header {
    margin-bottom: 15px;
    padding-bottom: 10px;
  }
  h1 { font-size: 18px; }
  .subtitle { font-size: 10px; }
  
  /* Hide elements not needed in print */
  .no-print,
  button,
  .saved-calcs {
    display: none !important;
  }
  
  /* Adjust cards for print */
  .card {
    border: 1px solid #000;
    padding: 10px;
    margin-bottom: 10px;
    page-break-inside: avoid;
  }
  .card-title {
    font-size: 12px;
    margin-bottom: 8px;
    padding-bottom: 5px;
  }
  
  /* Compact grids */
  .grid-2 {
    gap: 10px;
    margin-bottom: 10px;
  }
  
  /* Compact tables */
  table {
    font-size: 9px;
    margin: 10px 0;
    border: 1px solid #000;
  }
  th, td {
    padding: 4px;
    border: 1px solid #000;
  }
  th {
    font-size: 8px;
  }
  
  /* Compact stats */
  .stat-grid {
    gap: 8px;
    margin-top: 10px;
  }
  .stat-box {
    padding: 8px;
    border: 1px solid #000;
  }
  .stat-label {
    font-size: 8px;
    margin-bottom: 3px;
  }
  .stat-value {
    font-size: 14px;
  }
  
  /* Result card */
  .result-card {
    padding: 10px;
    border: 1px solid #000;
    margin-top: 10px;
    background: #fff !important;
  }
  
  /* Form elements in print */
  .form-group {
    margin-bottom: 8px;
  }
  label {
    font-size: 9px;
    margin-bottom: 3px;
  }
  input {
    border: none;
    border-bottom: 1px solid #000;
    padding: 2px 4px;
    font-size: 10px;
  }
  
  /* Ensure single page */
  @page {
    size: A4 portrait;
    margin: 10mm;
  }
  
  /* Prevent page breaks inside important elements */
  .card, .result-card, table, .stat-grid {
    page-break-inside: avoid;
  }
  
  /* Show print-only values, hide inputs */
  input {
    display: none !important;
  }
  .print-only {
    display: inline !important;
  }
}

.result-card {
  background: #f9f9f9;
  border: 2px solid #000;
  padding: 20px;
  margin-top: 20px;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
  margin-top: 15px;
}
.stat-box {
  border: 1px solid #000;
  padding: 15px;
  text-align: center;
}
.stat-label {
  font-size: 10px;
  text-transform: uppercase;
  margin-bottom: 5px;
}
.stat-value {
  font-size: 24px;
  font-weight: bold;
}
.hidden { display: none; }

.saved-calcs {
  margin-top: 30px;
  border: 2px solid #000;
  padding: 20px;
}
.calc-card {
  border: 1px solid #000;
  padding: 15px;
  margin-bottom: 10px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
}
.calc-card:hover {
  background: #f0f0f0;
}
.calc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.calc-name {
  font-weight: bold;
  font-size: 16px;
}
.calc-date {
  font-size: 12px;
  color: #666;
}
.calc-summary {
  font-size: 12px;
  color: #333;
}
</style>
</head>
<body>

<div class="header">
  <h1>PI → BOE → TALLY CALCULATOR</h1>
  <div class="subtitle">Proforma Invoice to Bill of Entry Calculator</div>
</div>

<!-- ===== GEMINI AI INVOICE SCANNER ===== -->
<div class="card no-print" style="margin-bottom:20px; border-color:#6200ea;">
  <div class="card-title" style="color:#6200ea; border-color:#6200ea;">🤖 AI Invoice Scanner (Powered by Gemini)</div>

  <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin-bottom:15px;">
    <div class="form-group">
      <label style="color:#6200ea;">Gemini API Key</label>
      <input type="password" id="gemini_api_key" placeholder="AIza..." style="border-color:#6200ea;"
             value="" oninput="saveApiKey(this.value)">
      <div style="font-size:11px; color:#666; margin-top:4px;">Get free key at <a href="https://aistudio.google.com/apikey" target="_blank">aistudio.google.com</a></div>
    </div>
    <div class="form-group">
      <label style="color:#6200ea;">Gemini Model</label>
      <select id="gemini_model" style="width:100%; border:2px solid #6200ea; padding:10px; font-family:'Courier New',monospace; font-size:13px; background:#fff;" onchange="saveModel(this.value)">
        <option value="gemini-2.5-flash">gemini-2.5-flash ✅ (recommended)</option>
        <option value="gemini-2.0-flash-lite">gemini-2.0-flash-lite</option>
        <option value="gemini-2.0-flash">gemini-2.0-flash</option>
        <option value="gemini-1.5-flash-8b">gemini-1.5-flash-8b</option>
        <option value="gemini-1.5-pro">gemini-1.5-pro</option>
      </select>
    </div>
    <div class="form-group">
      <label style="color:#6200ea;">Upload Invoice (PDF / JPG / PNG)</label>
      <input type="file" id="invoice_file" accept=".pdf,.jpg,.jpeg,.png"
             style="border-color:#6200ea; padding:8px; cursor:pointer;">
    </div>
  </div>

  <div id="drop-zone"
       style="border:3px dashed #6200ea; padding:25px; text-align:center; cursor:pointer; margin-bottom:15px; background:#faf5ff;"
       ondragover="event.preventDefault()" ondrop="handleDrop(event)" onclick="document.getElementById('invoice_file').click()">
    <div style="font-size:36px;">📄</div>
    <div style="font-size:14px; color:#6200ea; font-weight:bold; margin-top:8px;">Drag & Drop Invoice Here</div>
    <div style="font-size:12px; color:#888; margin-top:4px;">or click to browse • PDF, JPG, PNG supported</div>
  </div>

  <div id="scan-preview" style="display:none; margin-bottom:15px; text-align:center;">
    <img id="preview-img" style="max-height:200px; border:2px solid #6200ea; display:none;">
    <div id="preview-pdf" style="font-size:13px; color:#6200ea; padding:15px; border:2px solid #6200ea; background:#faf5ff; display:none;">
      📄 PDF selected — ready to scan
    </div>
  </div>

  <div style="text-align:center;">
    <button onclick="scanInvoice()" class="btn-primary"
            style="border-color:#6200ea; color:#6200ea; font-size:16px; padding:14px 35px;">
      🔍 SCAN &amp; AUTO-FILL INVOICE
    </button>
  </div>

  <div id="scan-status" style="margin-top:15px; font-size:13px; display:none;"></div>
</div>
<!-- ===== END AI SCANNER ===== -->

<div class="grid-2">
  <div class="card">
    <div class="card-title input-red">⚙ Configuration (User Input)</div>
    
    <div class="form-group">
      <label>Exchange Rate Date</label>
      <input type="date" id="er_date" class="red">
      <span class="print-only" id="er_date_print"></span>
    </div>
    
    <div class="form-group">
      <label>Exchange Rate (USD to INR)</label>
      <input type="number" step="0.01" id="er_rate" class="red" placeholder="87.2">
      <span class="print-only" id="er_rate_print"></span>
    </div>
  </div>

  <div class="card">
    <div class="card-title input-red">📄 BOE Details (From BOE Document)</div>

    <div class="no-print" style="background:#fff8e1; border:2px dashed #f9a825; padding:12px; margin-bottom:15px; border-radius:2px;">
      <div style="font-size:12px; font-weight:bold; color:#f9a825; margin-bottom:8px;">🤖 SCAN BOE DOCUMENT</div>
      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
        <input type="file" id="boe_file" accept=".pdf,.jpg,.jpeg,.png"
               style="flex:1; border:1px solid #f9a825; padding:6px; font-size:12px; min-width:0;"
               onchange="showMiniPreview('boe_file','boe_preview')">
        <button onclick="scanBOE()" style="border-color:#f9a825; color:#f9a825; padding:8px 15px; white-space:nowrap; font-size:13px;">
          🔍 SCAN BOE
        </button>
      </div>
      <div id="boe_preview" style="font-size:11px; color:#888; margin-top:5px;"></div>
      <div id="boe_scan_status" style="display:none; margin-top:8px; font-size:12px; padding:8px;"></div>
    </div>
    
    <div class="form-group">
      <label>BOE Number</label>
      <input type="text" id="boe_number" class="red" placeholder="Enter BOE Number">
      <span class="print-only" id="boe_number_print"></span>
    </div>
    
    <div class="form-group">
      <label>BOE Date</label>
      <input type="date" id="boe_date" class="red">
      <span class="print-only" id="boe_date_print"></span>
    </div>
    
    <div class="form-group">
      <label>PORT Code</label>
      <input type="text" id="port_code" class="red" placeholder="Enter PORT Code">
      <span class="print-only" id="port_code_print"></span>
    </div>
    
    <div class="form-group">
      <label>BOE Taxable Amount (₹)</label>
      <input type="number" step="0.01" id="boe_taxable" class="red" placeholder="1012377.78">
      <span class="print-only" id="boe_taxable_print"></span>
    </div>
    
    <div class="form-group">
      <label>BOE GST Amount (₹)</label>
      <input type="number" step="0.01" id="boe_gst" class="red" placeholder="182228">
      <span class="print-only" id="boe_gst_print"></span>
    </div>
  </div>
</div>

<div class="card">
  <div class="card-title input-red">💳 ICEGATE CHALLAN DETAILS</div>

  <div class="no-print" style="background:#e8f5e9; border:2px dashed #2e7d32; padding:12px; margin-bottom:15px; border-radius:2px;">
    <div style="font-size:12px; font-weight:bold; color:#2e7d32; margin-bottom:8px;">🤖 SCAN ICEGATE CHALLAN</div>
    <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
      <input type="file" id="challan_file" accept=".pdf,.jpg,.jpeg,.png"
             style="flex:1; border:1px solid #2e7d32; padding:6px; font-size:12px; min-width:0;"
             onchange="showMiniPreview('challan_file','challan_preview')">
      <button onclick="scanChallan()" style="border-color:#2e7d32; color:#2e7d32; padding:8px 15px; white-space:nowrap; font-size:13px;">
        🔍 SCAN CHALLAN
      </button>
    </div>
    <div id="challan_preview" style="font-size:11px; color:#888; margin-top:5px;"></div>
    <div id="challan_scan_status" style="display:none; margin-top:8px; font-size:12px; padding:8px;"></div>
  </div>
  
  <table style="border: 1px solid #000; font-size: 16px; margin-top: 10px;">
    <tbody>
      <tr>
        <td style="width: 40%; font-weight: bold; border: 1px solid #000; padding: 12px;">Challan Date:</td>
        <td style="width: 60%; border: 1px solid #000; padding: 12px;">
          <input type="date" id="challan_date" class="red" style="border: none; width: 100%; padding: 5px;">
          <span class="print-only" id="challan_date_print"></span>
        </td>
      </tr>
      <tr>
        <td style="font-weight: bold; border: 1px solid #000; padding: 12px;">Challan Amount:</td>
        <td style="border: 1px solid #000; padding: 12px;">
          <input type="number" step="0.01" id="challan_amount" class="red" placeholder="₹ 0.00" oninput="calculateChallanDetails()" style="border: none; width: 100%; padding: 5px;">
          <span class="print-only" id="challan_amount_print"></span>
        </td>
      </tr>
      <tr>
        <td style="font-weight: bold; border: 1px solid #000; padding: 12px;">IGST Amount:</td>
        <td style="border: 1px solid #000; padding: 12px; background: #f0f0f0;">
          <input type="number" step="0.01" id="challan_igst" class="green" readonly placeholder="= BOE GST Amount" style="border: none; width: 100%; padding: 5px; background: transparent;">
          <span class="print-only" id="challan_igst_print"></span>
        </td>
      </tr>
      <tr>
        <td style="font-weight: bold; border: 1px solid #000; padding: 12px;">Custom Duty:</td>
        <td style="border: 1px solid #000; padding: 12px; background: #f0f0f0;">
          <input type="number" step="0.01" id="challan_custom_duty" class="green" readonly placeholder="= Challan Amount - BOE GST Amount" style="border: none; width: 100%; padding: 5px; background: transparent;">
          <span class="print-only" id="challan_custom_duty_print"></span>
        </td>
      </tr>
    </tbody>
  </table>
  
  <div style="margin-top: 10px; font-size: 11px; color: #666; font-style: italic;">
    <strong>Note:</strong> IGST Amount = BOE GST Amount | Custom Duty = Challan Amount - BOE GST Amount
  </div>
</div>

<div class="card">
  <div class="card-title input-red">📋 Proforma Invoice Items</div>
  
  <table>
    <thead>
      <tr>
        <th style="width: 5%">#</th>
        <th style="width: 30%">Item Name</th>
        <th style="width: 10%">Quantity</th>
        <th style="width: 12%">Unit Price (USD)</th>
        <th style="width: 13%" class="formula-black">Total (USD)</th>
        <th style="width: 13%" class="formula-black">Total (INR)</th>
        <th class="no-print" style="width: 17%">Actions</th>
      </tr>
    </thead>
    <tbody id="items-body"></tbody>
  </table>
  
  <div class="no-print">
    <button onclick="addItem()" class="btn-primary">+ ADD ITEM</button>
    <button onclick="clearAllItems()" class="btn-danger">CLEAR ALL ITEMS</button>
  </div>
</div>

<div class="no-print" style="text-align: center; margin: 30px 0;">
  <button onclick="calculate()" class="btn-success" style="font-size: 18px; padding: 15px 40px;">🧮 CALCULATE</button>
  <button onclick="resetAll()" class="btn-danger" style="font-size: 18px; padding: 15px 40px;">🔄 RESET ALL</button>
</div>

<div id="results" class="hidden">
  <div class="result-card">
    <div class="card-title output-green">📊 CALCULATION SUMMARY</div>
    
    <div class="stat-grid">
      <div class="stat-box">
        <div class="stat-label">Total PI (USD)</div>
        <div class="stat-value input-red" id="total-usd">$0.00</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Total PI (INR)</div>
        <div class="stat-value input-red" id="total-inr">₹0.00</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">BOE Loading %</div>
        <div class="stat-value output-green" id="boe-pct">0.0000%</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Taxable Amount</div>
        <div class="stat-value" id="taxable-amt">₹0.00</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">GST Amount</div>
        <div class="stat-value" id="gst-amt">₹0.00</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Total Payable</div>
        <div class="stat-value output-green" id="total-payable">₹0.00</div>
      </div>
    </div>
  </div>

  <div class="card" style="margin-top: 20px;">
    <div class="card-title output-green">📈 ITEM-WISE BREAKDOWN</div>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Item</th>
          <th>Qty</th>
          <th>Price (USD)</th>
          <th>Total (USD)</th>
          <th>Total (INR)</th>
          <th class="output-green">After BOE Loading (INR)</th>
          <th>BOE %</th>
        </tr>
      </thead>
      <tbody id="results-body"></tbody>
    </table>
  </div>
  
  <div class="no-print" style="text-align: center; margin: 20px 0;">
    <button onclick="window.print()" class="btn-primary" style="font-size: 16px;">🖨️ PRINT CALCULATION</button>
    <button onclick="saveCalculation()" class="btn-success" style="font-size: 16px;">💾 SAVE CALCULATION</button>
  </div>
</div>

<div class="card" style="margin-top: 20px;">
  <div class="card-title">📝 TALLY ENTRY STEPS</div>
  
  <div style="font-size: 13px; line-height: 1.8;">
    <div style="margin-bottom: 20px;">
      <div style="font-weight: bold; font-size: 14px; margin-bottom: 10px; text-decoration: underline;">Step 1: Purchase Voucher</div>
      <ul style="margin-left: 20px;">
        <li><strong>Select Sundry Creditor</strong></li>
        <li><strong>Select Item</strong> → <strong>Qty</strong> → <strong>Blank</strong> → <strong>Put Value as per CI</strong></li>
        <li><strong>Select Purchase Ledger</strong></li>
        <li><strong>GST Taxable Value Details</strong> → <strong>Override Taxable Value</strong> → <strong>YES</strong></li>
        <li><strong>Taxable Value</strong> → <strong>BOE Value</strong></li>
        <li><strong>Put BOE and Eway Detail on Sub Tab</strong></li>
      </ul>
    </div>
    
    <div style="margin-bottom: 20px;">
      <div style="font-weight: bold; font-size: 14px; margin-bottom: 10px; text-decoration: underline;">Step 2: Journal Voucher</div>
      <ul style="margin-left: 20px;">
        <li><strong>Alt + J</strong></li>
        <li><strong>GST</strong> → <strong>Increase in Tax Liability</strong> → <strong>Import of Services</strong></li>
        <li><strong>BY:</strong></li>
        <li style="margin-left: 20px;"><strong>Tax on Custom Duty (Assets)</strong> → <strong>Put BOE GST Amt</strong></li>
        <li><strong>TO: Input IGST @ 18%</strong></li>
        <li>Rate: <strong>18%</strong></li>
        <li><strong>Taxable Amount</strong></li>
      </ul>
    </div>
    
    <div style="margin-bottom: 20px;">
      <div style="font-weight: bold; font-size: 14px; margin-bottom: 10px; text-decoration: underline;">Step 3: Bank Voucher</div>
      <ul style="margin-left: 20px;">
        <li><strong>Convert Into Journal</strong></li>
        <li><strong>BY: Input IGST @ 18%</strong></li>
        <li><strong>BY: Custom Duty (Purchase Head)</strong></li>
        <li><strong>Select Stock Item Which we want to adjust Custom Duty</strong></li>
        <li><strong>TO: ICICI Bank A/c</strong></li>
      </ul>
    </div>
    
    <div style="margin-bottom: 20px;">
      <div style="font-weight: bold; font-size: 14px; margin-bottom: 10px; text-decoration: underline;">Step 4: Journal Voucher</div>
      <ul style="margin-left: 20px;">
        <li><strong>Alt + J</strong></li>
        <li><strong>GST</strong> → <strong>Increase in Input Tax Credit</strong> → <strong>Import of Goods</strong></li>
        <li><strong>BY: Input IGST @ 18%</strong></li>
        <li>Rate: <strong>18%</strong></li>
        <li><strong>Taxable Amount</strong></li>
        <li><strong>TO: Tax on Custom Duty (Assets)</strong></li>
      </ul>
    </div>
  </div>
</div>

<div class="saved-calcs no-print">
  <div class="card-title">💾 SAVED CALCULATIONS</div>
  <div id="saved-list"></div>
</div>

<script>
let items = [];
let itemCounter = 0;
let currentResults = null;

function addItem(name = '', qty = '', price = '') {
  itemCounter++;
  const id = itemCounter;
  items.push({ id, name, qty, price });
  
  const tbody = document.getElementById('items-body');
  const row = document.createElement('tr');
  row.id = 'item-' + id;
  row.innerHTML = `
    <td>${id}</td>
    <td>
      <input type="text" class="red" value="${name}" onchange="updateItem(${id}, 'name', this.value)" placeholder="Item name">
      <span class="print-only"></span>
    </td>
    <td>
      <input type="number" class="red" value="${qty}" onchange="updateItem(${id}, 'qty', this.value)" placeholder="0">
      <span class="print-only"></span>
    </td>
    <td>
      <input type="number" step="0.01" class="red" value="${price}" onchange="updateItem(${id}, 'price', this.value)" placeholder="0.00">
      <span class="print-only"></span>
    </td>
    <td class="formula-black" id="total-usd-${id}">$0.00</td>
    <td class="formula-black" id="total-inr-${id}">₹0.00</td>
    <td class="no-print"><button onclick="removeItem(${id})" class="btn-danger">Remove</button></td>
  `;
  tbody.appendChild(row);
  updateItemCalc(id);
}

function updateItem(id, field, value) {
  const item = items.find(i => i.id === id);
  if (item) {
    item[field] = value;
    updateItemCalc(id);
  }
}

function updateItemCalc(id) {
  const item = items.find(i => i.id === id);
  if (!item) return;
  
  const qty = parseFloat(item.qty) || 0;
  const price = parseFloat(item.price) || 0;
  const rate = parseFloat(document.getElementById('er_rate').value) || 0;
  
  const totalUSD = qty * price;
  const totalINR = totalUSD * rate;
  
  document.getElementById('total-usd-' + id).textContent = '$' + totalUSD.toFixed(2);
  document.getElementById('total-inr-' + id).textContent = '₹' + totalINR.toFixed(2);
}

function calculateChallanDetails() {
  const boeGST = parseFloat(document.getElementById('boe_gst').value) || 0;
  const challanAmount = parseFloat(document.getElementById('challan_amount').value) || 0;
  
  // IGST Amount = BOE GST Amount
  document.getElementById('challan_igst').value = boeGST.toFixed(2);
  
  // Custom Duty = Challan Amount - BOE GST Amount
  const customDuty = challanAmount - boeGST;
  document.getElementById('challan_custom_duty').value = customDuty.toFixed(2);
}

function beforePrint() {
  // Update print-only spans with current values
  document.getElementById('er_date_print').textContent = document.getElementById('er_date').value || '—';
  document.getElementById('er_rate_print').textContent = document.getElementById('er_rate').value || '—';
  document.getElementById('boe_number_print').textContent = document.getElementById('boe_number').value || '—';
  document.getElementById('boe_date_print').textContent = document.getElementById('boe_date').value || '—';
  document.getElementById('port_code_print').textContent = document.getElementById('port_code').value || '—';
  document.getElementById('boe_taxable_print').textContent = document.getElementById('boe_taxable').value || '—';
  document.getElementById('boe_gst_print').textContent = document.getElementById('boe_gst').value || '—';
  document.getElementById('challan_date_print').textContent = document.getElementById('challan_date').value || '—';
  document.getElementById('challan_amount_print').textContent = document.getElementById('challan_amount').value || '—';
  document.getElementById('challan_igst_print').textContent = document.getElementById('challan_igst').value || '—';
  document.getElementById('challan_custom_duty_print').textContent = document.getElementById('challan_custom_duty').value || '—';
  
  // Update item print values
  items.forEach(item => {
    const row = document.getElementById('item-' + item.id);
    if (row) {
      const printSpans = row.querySelectorAll('.print-only');
      if (printSpans[0]) printSpans[0].textContent = item.name || '—';
      if (printSpans[1]) printSpans[1].textContent = item.qty || '—';
      if (printSpans[2]) printSpans[2].textContent = item.price || '—';
    }
  });
}

// Register print event
window.addEventListener('beforeprint', beforePrint);

function removeItem(id) {
  items = items.filter(i => i.id !== id);
  document.getElementById('item-' + id).remove();
}

function clearAllItems() {
  if (confirm('Clear all items?')) {
    items = [];
    itemCounter = 0;
    document.getElementById('items-body').innerHTML = '';
  }
}

function resetAll() {
  if (confirm('Reset everything? This will clear all inputs.')) {
    items = [];
    itemCounter = 0;
    document.getElementById('items-body').innerHTML = '';
    document.getElementById('er_date').value = '';
    document.getElementById('er_rate').value = '';
    document.getElementById('boe_number').value = '';
    document.getElementById('boe_date').value = '';
    document.getElementById('port_code').value = '';
    document.getElementById('boe_taxable').value = '';
    document.getElementById('boe_gst').value = '';
    document.getElementById('challan_date').value = '';
    document.getElementById('challan_amount').value = '';
    document.getElementById('challan_igst').value = '';
    document.getElementById('challan_custom_duty').value = '';
    document.getElementById('results').classList.add('hidden');
  }
}

function calculate() {
  const rate = parseFloat(document.getElementById('er_rate').value) || 0;
  const boeTaxable = parseFloat(document.getElementById('boe_taxable').value) || 0;
  const boeGST = parseFloat(document.getElementById('boe_gst').value) || 0;
  
  if (items.length === 0) {
    alert('Please add at least one item!');
    return;
  }
  
  if (rate === 0) {
    alert('Please enter exchange rate!');
    return;
  }
  
  let totalUSD = 0;
  let totalINR = 0;
  const results = [];
  
  items.forEach(item => {
    const qty = parseFloat(item.qty) || 0;
    const price = parseFloat(item.price) || 0;
    const itemTotalUSD = qty * price;
    const itemTotalINR = itemTotalUSD * rate;
    
    totalUSD += itemTotalUSD;
    totalINR += itemTotalINR;
    
    results.push({
      id: item.id,
      name: item.name || 'Unnamed Item',
      qty,
      price,
      totalUSD: itemTotalUSD,
      totalINR: itemTotalINR
    });
  });
  
  const boeLoadingPct = totalINR > 0 ? ((boeTaxable - totalINR) / totalINR * 100) : 0;
  const totalPayable = boeTaxable + boeGST;
  const gstPct = boeTaxable > 0 ? (boeGST / boeTaxable * 100) : 0;
  
  currentResults = {
    totalUSD,
    totalINR,
    boeLoadingPct,
    boeTaxable,
    boeGST,
    totalPayable,
    gstPct,
    results
  };
  
  // Update summary
  document.getElementById('total-usd').textContent = '$' + totalUSD.toFixed(2);
  document.getElementById('total-inr').textContent = '₹' + totalINR.toFixed(2);
  document.getElementById('boe-pct').textContent = boeLoadingPct.toFixed(4) + '%';
  document.getElementById('taxable-amt').textContent = '₹' + boeTaxable.toFixed(2);
  document.getElementById('gst-amt').textContent = '₹' + boeGST.toFixed(2);
  document.getElementById('total-payable').textContent = '₹' + totalPayable.toFixed(2);
  
  // Update results table
  const tbody = document.getElementById('results-body');
  tbody.innerHTML = '';
  
  results.forEach((item, idx) => {
    const afterBOE = item.totalINR * (1 + boeLoadingPct / 100);
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${idx + 1}</td>
      <td>${item.name}</td>
      <td>${item.qty}</td>
      <td>$${item.price.toFixed(2)}</td>
      <td>$${item.totalUSD.toFixed(2)}</td>
      <td>₹${item.totalINR.toFixed(2)}</td>
      <td class="output-green">₹${afterBOE.toFixed(2)}</td>
      <td>${boeLoadingPct.toFixed(4)}%</td>
    `;
    tbody.appendChild(row);
  });
  
  // Add total row
  const totalAfterBOE = totalINR * (1 + boeLoadingPct / 100);
  const totalRow = document.createElement('tr');
  totalRow.className = 'total-row';
  totalRow.innerHTML = `
    <td colspan="4" style="text-align: right;">TOTALS</td>
    <td>$${totalUSD.toFixed(2)}</td>
    <td>₹${totalINR.toFixed(2)}</td>
    <td class="output-green">₹${totalAfterBOE.toFixed(2)}</td>
    <td>${boeLoadingPct.toFixed(4)}%</td>
  `;
  tbody.appendChild(totalRow);
  
  // Show results
  document.getElementById('results').classList.remove('hidden');
  document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}

function saveCalculation() {
  if (!currentResults) {
    alert('Please calculate first before saving!');
    return;
  }
  
  const name = prompt('Enter a name for this calculation:', 'Calculation ' + new Date().toLocaleDateString());
  if (!name) return;
  
  const savedCalcs = JSON.parse(localStorage.getItem('savedCalculations') || '[]');
  
  const calc = {
    id: Date.now(),
    name,
    date: new Date().toISOString(),
    erDate: document.getElementById('er_date').value,
    erRate: parseFloat(document.getElementById('er_rate').value),
    boeNumber: document.getElementById('boe_number').value,
    boeDate: document.getElementById('boe_date').value,
    portCode: document.getElementById('port_code').value,
    boeTaxable: parseFloat(document.getElementById('boe_taxable').value),
    boeGST: parseFloat(document.getElementById('boe_gst').value),
    challanDate: document.getElementById('challan_date').value,
    challanAmount: parseFloat(document.getElementById('challan_amount').value),
    challanIGST: parseFloat(document.getElementById('challan_igst').value),
    challanCustomDuty: parseFloat(document.getElementById('challan_custom_duty').value),
    items: items.map(i => ({...i})),
    results: currentResults
  };
  
  savedCalcs.push(calc);
  localStorage.setItem('savedCalculations', JSON.stringify(savedCalcs));
  
  loadSavedCalculations();
  alert('Calculation saved successfully!');
}

function loadSavedCalculations() {
  const savedCalcs = JSON.parse(localStorage.getItem('savedCalculations') || '[]');
  const container = document.getElementById('saved-list');
  
  if (savedCalcs.length === 0) {
    container.innerHTML = '<p style="color: #666; font-size: 14px;">No saved calculations yet. Click "SAVE CALCULATION" to save your work.</p>';
    return;
  }
  
  container.innerHTML = '';
  savedCalcs.reverse().forEach(calc => {
    const card = document.createElement('div');
    card.className = 'calc-card';
    card.onclick = () => loadCalculation(calc);
    
    const date = new Date(calc.date);
    card.innerHTML = `
      <div class="calc-header">
        <div class="calc-name">${calc.name}</div>
        <div class="calc-date">${date.toLocaleDateString()} ${date.toLocaleTimeString()}</div>
      </div>
      <div class="calc-summary">
        ${calc.items.length} items • Total: ₹${calc.results.totalPayable.toFixed(2)} • BOE: ${calc.results.boeLoadingPct.toFixed(2)}%
      </div>
      <button onclick="event.stopPropagation(); deleteCalculation(${calc.id})" class="btn-danger" style="margin-top: 10px; padding: 5px 10px; font-size: 12px;">Delete</button>
    `;
    container.appendChild(card);
  });
}

function loadCalculation(calc) {
  if (!confirm('Load this calculation? Current data will be replaced.')) return;
  
  document.getElementById('er_date').value = calc.erDate;
  document.getElementById('er_rate').value = calc.erRate;
  document.getElementById('boe_number').value = calc.boeNumber || '';
  document.getElementById('boe_date').value = calc.boeDate || '';
  document.getElementById('port_code').value = calc.portCode || '';
  document.getElementById('boe_taxable').value = calc.boeTaxable;
  document.getElementById('boe_gst').value = calc.boeGST;
  document.getElementById('challan_date').value = calc.challanDate || '';
  document.getElementById('challan_amount').value = calc.challanAmount || '';
  document.getElementById('challan_igst').value = calc.challanIGST || '';
  document.getElementById('challan_custom_duty').value = calc.challanCustomDuty || '';
  
  items = [];
  itemCounter = 0;
  document.getElementById('items-body').innerHTML = '';
  
  calc.items.forEach(item => {
    addItem(item.name, item.qty, item.price);
  });
  
  calculate();
}

function deleteCalculation(id) {
  if (!confirm('Delete this calculation?')) return;
  
  let savedCalcs = JSON.parse(localStorage.getItem('savedCalculations') || '[]');
  savedCalcs = savedCalcs.filter(c => c.id !== id);
  localStorage.setItem('savedCalculations', JSON.stringify(savedCalcs));
  
  loadSavedCalculations();
}

// ===== GEMINI AI SCANNER =====

function saveApiKey(val) {
  localStorage.setItem('gemini_api_key', val);
}

function saveModel(val) {
  localStorage.setItem('gemini_model', val);
}

function handleDrop(e) {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  if (file) {
    const dt = new DataTransfer();
    dt.items.add(file);
    document.getElementById('invoice_file').files = dt.files;
    showPreview(file);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // Restore saved API key
  const savedKey = localStorage.getItem('gemini_api_key') || '';
  document.getElementById('gemini_api_key').value = savedKey;
  const savedModel = localStorage.getItem('gemini_model') || 'gemini-2.5-flash';
  document.getElementById('gemini_model').value = savedModel;

  document.getElementById('invoice_file').addEventListener('change', function() {
    if (this.files[0]) showPreview(this.files[0]);
  });
});

function showPreview(file) {
  const previewDiv = document.getElementById('scan-preview');
  const previewImg = document.getElementById('preview-img');
  const previewPdf = document.getElementById('preview-pdf');
  previewDiv.style.display = 'block';

  if (file.type === 'application/pdf') {
    previewImg.style.display = 'none';
    previewPdf.style.display = 'block';
    previewPdf.textContent = '📄 ' + file.name + ' — ready to scan';
  } else {
    previewPdf.style.display = 'none';
    previewImg.style.display = 'block';
    previewImg.src = URL.createObjectURL(file);
  }
}

async function scanInvoice() {
  const apiKey = document.getElementById('gemini_api_key').value.trim();
  const fileInput = document.getElementById('invoice_file');
  const statusDiv = document.getElementById('scan-status');

  if (!apiKey) {
    showScanStatus('error', '❌ Please enter your Gemini API key first.');
    return;
  }
  if (!fileInput.files[0]) {
    showScanStatus('error', '❌ Please select an invoice file first.');
    return;
  }

  showScanStatus('loading', '🔄 Uploading and scanning invoice with Gemini AI... please wait...');

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('api_key', apiKey);
  formData.append('model', document.getElementById('gemini_model').value);

  try {
    const resp = await fetch('/scan-invoice', { method: 'POST', body: formData });
    const data = await resp.json();

    if (!resp.ok || data.error) {
      showScanStatus('error', '❌ Error: ' + (data.error || 'Unknown error'));
      return;
    }

    // Auto-fill form fields
    if (data.exchange_rate) document.getElementById('er_rate').value = data.exchange_rate;
    if (data.exchange_rate_date) document.getElementById('er_date').value = data.exchange_rate_date;
    if (data.boe_number) document.getElementById('boe_number').value = data.boe_number;
    if (data.boe_date) document.getElementById('boe_date').value = data.boe_date;
    if (data.port_code) document.getElementById('port_code').value = data.port_code;
    if (data.boe_taxable_amount) document.getElementById('boe_taxable').value = data.boe_taxable_amount;
    if (data.boe_gst_amount) document.getElementById('boe_gst').value = data.boe_gst_amount;

    // Auto-fill items
    if (data.items && data.items.length > 0) {
      items = [];
      itemCounter = 0;
      document.getElementById('items-body').innerHTML = '';
      data.items.forEach(item => {
        addItem(item.name || '', item.qty || '', item.unit_price_usd || '');
      });
    }

    // Trigger challan calculation
    calculateChallanDetails();

    const itemCount = data.items ? data.items.length : 0;
    const rawText = data.raw_text ? `<details style="margin-top:10px;"><summary style="cursor:pointer; font-size:11px;">📋 Raw AI Response</summary><pre style="font-size:10px; white-space:pre-wrap; margin-top:5px;">${data.raw_text}</pre></details>` : '';
    showScanStatus('success',
      `✅ Successfully extracted <strong>${itemCount} items</strong> from invoice! Form has been auto-filled. Review and click CALCULATE.${rawText}`
    );

  } catch (err) {
    showScanStatus('error', '❌ Network error: ' + err.message);
  }
}

function showScanStatus(type, html) {
  const div = document.getElementById('scan-status');
  div.style.display = 'block';
  const colors = { loading:'#6200ea', success:'#008000', error:'#cc0000' };
  const bgs    = { loading:'#f3e8ff', success:'#f0fff0', error:'#fff0f0' };
  div.style.color = colors[type];
  div.style.background = bgs[type];
  div.style.border = '2px solid ' + colors[type];
  div.style.padding = '15px';
  div.innerHTML = html;
}

function showMiniStatus(statusId, type, html) {
  const div = document.getElementById(statusId);
  div.style.display = 'block';
  const colors = { loading:'#666', success:'#2e7d32', error:'#cc0000' };
  const bgs    = { loading:'#f5f5f5', success:'#f0fff0', error:'#fff0f0' };
  div.style.color = colors[type];
  div.style.background = bgs[type];
  div.style.border = '1px solid ' + colors[type];
  div.style.padding = '8px';
  div.innerHTML = html;
}

function showMiniPreview(fileInputId, previewId) {
  const file = document.getElementById(fileInputId).files[0];
  if (file) {
    document.getElementById(previewId).textContent = '📎 ' + file.name + ' (' + (file.size/1024).toFixed(1) + ' KB)';
  }
}

async function scanBOE() {
  const apiKey = document.getElementById('gemini_api_key').value.trim();
  const fileInput = document.getElementById('boe_file');
  if (!apiKey) { showMiniStatus('boe_scan_status','error','❌ Enter Gemini API key in the scanner section above.'); return; }
  if (!fileInput.files[0]) { showMiniStatus('boe_scan_status','error','❌ Please select a BOE document file.'); return; }

  showMiniStatus('boe_scan_status','loading','🔄 Scanning BOE document with Gemini AI...');

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('api_key', apiKey);
  formData.append('model', document.getElementById('gemini_model').value);

  try {
    const resp = await fetch('/scan-boe', { method: 'POST', body: formData });
    const data = await resp.json();
    if (!resp.ok || data.error) { showMiniStatus('boe_scan_status','error','❌ ' + (data.error || 'Unknown error')); return; }

    if (data.boe_number)        document.getElementById('boe_number').value   = data.boe_number;
    if (data.boe_date)          document.getElementById('boe_date').value      = data.boe_date;
    if (data.port_code)         document.getElementById('port_code').value     = data.port_code;
    if (data.boe_taxable_amount && data.boe_taxable_amount > 0)
                                document.getElementById('boe_taxable').value   = data.boe_taxable_amount;
    if (data.boe_gst_amount && data.boe_gst_amount > 0)
                                document.getElementById('boe_gst').value       = data.boe_gst_amount;
    if (data.exchange_rate)     document.getElementById('er_rate').value       = data.exchange_rate;
    if (data.exchange_rate_date) document.getElementById('er_date').value      = data.exchange_rate_date;

    calculateChallanDetails();
    const formula = data._formula ? `<div style="margin-top:6px; font-size:11px; color:#555;">📐 Taxable = ${data._formula}</div>` : '';
    showMiniStatus('boe_scan_status','success','✅ BOE data extracted and filled! Review the values above.' + formula);
  } catch(err) {
    showMiniStatus('boe_scan_status','error','❌ Network error: ' + err.message);
  }
}

async function scanChallan() {
  const apiKey = document.getElementById('gemini_api_key').value.trim();
  const fileInput = document.getElementById('challan_file');
  if (!apiKey) { showMiniStatus('challan_scan_status','error','❌ Enter Gemini API key in the scanner section above.'); return; }
  if (!fileInput.files[0]) { showMiniStatus('challan_scan_status','error','❌ Please select a Challan file.'); return; }

  showMiniStatus('challan_scan_status','loading','🔄 Scanning ICEGATE Challan with Gemini AI...');

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('api_key', apiKey);
  formData.append('model', document.getElementById('gemini_model').value);

  try {
    const resp = await fetch('/scan-challan', { method: 'POST', body: formData });
    const data = await resp.json();
    if (!resp.ok || data.error) { showMiniStatus('challan_scan_status','error','❌ ' + (data.error || 'Unknown error')); return; }

    if (data.challan_date)   document.getElementById('challan_date').value   = data.challan_date;
    if (data.challan_amount && data.challan_amount > 0)
                             document.getElementById('challan_amount').value  = data.challan_amount;

    // Always recalculate IGST and custom duty after filling
    calculateChallanDetails();
    showMiniStatus('challan_scan_status','success','✅ Challan data extracted and filled! IGST & Custom Duty auto-calculated.');
  } catch(err) {
    showMiniStatus('challan_scan_status','error','❌ Network error: ' + err.message);
  }
}
// ===== END GEMINI AI SCANNER =====

// Initialize
window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('er_rate').value = '87.2';
  document.getElementById('er_date').value = '2025-07-29';
  document.getElementById('boe_taxable').value = '1012377.78';
  document.getElementById('boe_gst').value = '182228';
  
  addItem('3 hp pump', 40, 121.64);
  addItem('1.5 hp pump', 102, 54.27);
  
  // Update live calculations
  document.getElementById('er_rate').addEventListener('input', () => {
    items.forEach(item => updateItemCalc(item.id));
  });
  
  // Auto-calculate challan details when BOE GST changes
  document.getElementById('boe_gst').addEventListener('input', calculateChallanDetails);
  
  loadSavedCalculations();
});
</script>

</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/scan-invoice', methods=['POST'])
def scan_invoice():
    """Receive an invoice file, send to Gemini API, return structured JSON."""
    try:
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            return jsonify({'error': 'Gemini API key is required'}), 400

        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file uploaded'}), 400

        filename = file.filename.lower()
        file_bytes = file.read()
        mime_type = file.mimetype or 'application/octet-stream'

        # Determine mime type from extension if needed
        if filename.endswith('.pdf'):
            mime_type = 'application/pdf'
        elif filename.endswith(('.jpg', '.jpeg')):
            mime_type = 'image/jpeg'
        elif filename.endswith('.png'):
            mime_type = 'image/png'

        # Configure Gemini
        selected_model = request.form.get('model', 'gemini-2.5-flash').strip()
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(selected_model)

        prompt = """You are an expert invoice data extractor for Indian import/customs calculations.

Carefully analyze this Proforma Invoice (PI) document and extract ALL data.

Return ONLY a valid JSON object with this exact structure (no markdown, no extra text):
{
  "items": [
    {
      "name": "exact product/item description",
      "qty": 10,
      "unit_price_usd": 121.64
    }
  ],
  "exchange_rate": 87.20,
  "exchange_rate_date": "2025-07-29",
  "boe_number": "",
  "boe_date": "",
  "port_code": "",
  "boe_taxable_amount": 0,
  "boe_gst_amount": 0
}

Rules:
- Extract EVERY line item from the invoice table (name, quantity, unit price in USD)
- qty must be a number (not string)
- unit_price_usd must be a number in USD only
- exchange_rate: fill only if explicitly stated in the document, else null
- exchange_rate_date: YYYY-MM-DD format if found, else null
- boe_number, boe_date, port_code: fill only if found in document, else empty string
- boe_taxable_amount, boe_gst_amount: fill only if found, else 0
- All numeric fields must be numbers (not strings)
- DO NOT invent data — only extract what is visible"""

        # Build the content parts
        image_part = {
            'inline_data': {
                'mime_type': mime_type,
                'data': base64.b64encode(file_bytes).decode('utf-8')
            }
        }

        response = model.generate_content([prompt, image_part])
        raw_text = response.text.strip()

        # Parse JSON — strip markdown fences if present
        clean = re.sub(r'^```(?:json)?\s*', '', raw_text, flags=re.MULTILINE)
        clean = re.sub(r'\s*```$', '', clean, flags=re.MULTILINE).strip()

        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            # Try to find JSON block inside the text
            match = re.search(r'\{[\s\S]+\}', clean)
            if match:
                data = json.loads(match.group())
            else:
                return jsonify({'error': 'Gemini returned non-JSON response', 'raw_text': raw_text}), 500

        data['raw_text'] = raw_text
        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/scan-boe', methods=['POST'])
def scan_boe():
    """Scan a BOE (Bill of Entry) document and extract key fields."""
    try:
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            return jsonify({'error': 'Gemini API key is required'}), 400
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file uploaded'}), 400

        filename = file.filename.lower()
        file_bytes = file.read()
        mime_type = 'application/pdf' if filename.endswith('.pdf') else \
                    'image/jpeg' if filename.endswith(('.jpg','.jpeg')) else 'image/png'

        selected_model = request.form.get('model', 'gemini-2.5-flash').strip()
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(selected_model)

        prompt = """You are an expert at reading Indian Customs Bill of Entry (BOE) documents.

Extract the following fields and return ONLY a valid JSON object (no markdown, no extra text):

{
  "boe_number": "BE No from top header (numeric, e.g. 5224087)",
  "boe_date": "BE Date from top header in YYYY-MM-DD format",
  "port_code": "Port Code from top header (e.g. INNSA1, INSUR4, INMAA1)",
  "tot_ass_val": 0.00,
  "bcd_amount": 0.00,
  "sws_amount": 0.00,
  "boe_gst_amount": 0.00,
  "exchange_rate": null,
  "exchange_rate_date": null
}

CRITICAL EXTRACTION RULES:

1. boe_number: The "BE No" in the top header box (short number like 5224087, NOT the long BE reference)

2. boe_date: The "BE Date" in the top header box, convert DD/MM/YYYY → YYYY-MM-DD

3. port_code: The "Port Code" from top header (e.g. INNSA1)

4. From section "C. DUTY SUMMARY" extract these 3 separate values:
   - tot_ass_val = "18.TOT.ASS VAL" column value (Total Assessable Value in INR)
   - bcd_amount  = "1.BCD" column value (Basic Customs Duty total in INR)
   - sws_amount  = "3.SWS" column value (Social Welfare Surcharge total in INR)

5. boe_gst_amount = "7.IGST" column value from C. DUTY SUMMARY (total IGST in INR)

6. exchange_rate: Look in "H. PROCESSING DETAILS" for text like "1 USD=88.7INR" — extract just the number 88.7

7. exchange_rate_date: Date of "Assessment" event in H. PROCESSING DETAILS, YYYY-MM-DD format

IMPORTANT: Do NOT compute boe_taxable_amount yourself — return the 3 components separately (tot_ass_val, bcd_amount, sws_amount) and the backend will add them correctly.

All amounts must be plain numbers (not strings). Use 0 if not found. Use "" for missing text fields. DO NOT invent data."""

        image_part = {'inline_data': {'mime_type': mime_type, 'data': base64.b64encode(file_bytes).decode('utf-8')}}
        response = model.generate_content([prompt, image_part])
        raw_text = response.text.strip()

        clean = re.sub(r'^```(?:json)?\s*', '', raw_text, flags=re.MULTILINE)
        clean = re.sub(r'\s*```$', '', clean, flags=re.MULTILINE).strip()
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]+\}', clean)
            if match:
                data = json.loads(match.group())
            else:
                return jsonify({'error': 'Gemini returned non-JSON response', 'raw_text': raw_text}), 500

        # ✅ Correct formula: IGST Taxable = TOT.ASS.VAL + BCD + SWS
        tot_ass_val = float(data.get('tot_ass_val') or 0)
        bcd_amount  = float(data.get('bcd_amount')  or 0)
        sws_amount  = float(data.get('sws_amount')  or 0)
        data['boe_taxable_amount'] = round(tot_ass_val + bcd_amount + sws_amount, 2)
        data['_formula'] = f"{tot_ass_val} (ASS VAL) + {bcd_amount} (BCD) + {sws_amount} (SWS) = {data['boe_taxable_amount']}"

        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/scan-challan', methods=['POST'])
def scan_challan():
    """Scan an ICEGATE Challan document and extract payment fields."""
    try:
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            return jsonify({'error': 'Gemini API key is required'}), 400
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file uploaded'}), 400

        filename = file.filename.lower()
        file_bytes = file.read()
        mime_type = 'application/pdf' if filename.endswith('.pdf') else \
                    'image/jpeg' if filename.endswith(('.jpg','.jpeg')) else 'image/png'

        selected_model = request.form.get('model', 'gemini-2.5-flash').strip()
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(selected_model)

        prompt = """You are an expert at reading Indian ICEGATE Customs Challan payment receipts.

Extract the following fields from this challan document and return ONLY a valid JSON object (no markdown, no extra text):

{
  "challan_date": "YYYY-MM-DD format",
  "challan_amount": 0.00
}

Field extraction rules:
- challan_date: the payment/challan date, convert to YYYY-MM-DD format
- challan_amount: the TOTAL amount paid on this challan in INR (₹) — this is the grand total paid, NOT IGST alone
- All amounts must be numbers (not strings), use 0 if not found
- Return empty string "" for date if not found
- The challan total includes both Custom Duty + IGST components — extract the total
- DO NOT invent data"""

        image_part = {'inline_data': {'mime_type': mime_type, 'data': base64.b64encode(file_bytes).decode('utf-8')}}
        response = model.generate_content([prompt, image_part])
        raw_text = response.text.strip()

        clean = re.sub(r'^```(?:json)?\s*', '', raw_text, flags=re.MULTILINE)
        clean = re.sub(r'\s*```$', '', clean, flags=re.MULTILINE).strip()
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]+\}', clean)
            if match:
                data = json.loads(match.group())
            else:
                return jsonify({'error': 'Gemini returned non-JSON response', 'raw_text': raw_text}), 500

        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 PI → BOE → TALLY CALCULATOR - Starting Application")
    print("="*70)
    print("\n📍 Server Status:")
    print("   • Application is running successfully")
    print("   • Access URL: http://localhost:5000")
    print("   • Host: 0.0.0.0 (accessible from network)")
    print("   • Port: 5000")
    print("\n💡 Application Features:")
    print("   • 🤖 AI Invoice Scanner (Gemini) — upload PDF/JPG/PNG to auto-fill")
    print("   • Real-time USD to INR currency conversion")
    print("   • Automatic BOE (Bill of Entry) loading percentage calculation")
    print("   • GST (Goods and Services Tax) computation")
    print("   • Color-coded interface:")
    print("     - RED: User input fields")
    print("     - GREEN: Calculated output values")
    print("   • Save calculations for future reference")
    print("   • Load and compare different PI (Proforma Invoice) and BOE data")
    print("   • Print-friendly calculation reports")
    print("\n🎯 Getting Started:")
    print("   1. Ensure this script is running: python pi_boe_calculator.py")
    print("   2. Open your web browser and navigate to: http://localhost:5000")
    print("   3. Enter exchange rate and BOE details in the input fields")
    print("   4. Add invoice items with quantities and unit prices")
    print("   5. Click the 'CALCULATE' button to see results")
    print("   6. Optionally save your calculation for later comparison")
    print("\n🔧 Additional Commands (Windows PowerShell):")
    print("   Enable Windows Defender real-time protection:")
    print("   • Set-MpPreference -DisableRealtimeMonitoring $false")
    print("   • Set-MpPreference -DisableBehaviorMonitoring $false")
    print("   • Set-MpPreference -DisableBlockAtFirstSeen $false")
    print("   • Set-MpPreference -DisableIOAVProtection $false")
    print("   • Set-MpPreference -DisableScriptScanning $false")
    print("\n💾 Data Storage:")
    print("   • Calculations are saved in browser local storage")
    print("   • Data persists across browser sessions")
    print("   • Clear browser data to reset saved calculations")
    print("\n⚠️  Important Notes:")
    print("   • Make sure port 5000 is not being used by another application")
    print("   • Use Ctrl+C to stop the server when finished")
    print("   • Debug mode is enabled for development purposes")
    print("\n" + "="*70)
    print("✅ Server is ready! Waiting for connections...")
    print("="*70 + "\n")
    app.run(debug=True, port=5000, host='0.0.0.0')
