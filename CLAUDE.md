# Purchase Order — CLAUDE.md

## Project Overview
Full-stack ERP for Greenwave Traders. Manages purchase orders, shipments, invoicing, and logistics tracking. Single-file Flask app with SQLite.

## Stack
- **Backend:** Python / Flask (`purchase_order_app.py`) — single large file
- **DB:** SQLite via `get_db()` context manager
- **Frontend:** Jinja2 templates in `templates/`, vanilla JS (no bundler)
- **Process manager:** PM2 on Ubuntu prod server (116.74.77.22)
- **User:** `dckakadia`, app name: `purchase_order`

## Running Locally
```bash
python purchase_order_app.py
```

## Deployment
```bash
git push origin main
# Then SSH to server:
# git pull origin main && pm2 restart purchase_order
```
Validate syntax before pushing: `python -c "import purchase_order_app; print('OK')"`

## Key Architecture — Shipment Part-Load System

### Tables
- `shipments` — one row per physical shipment
- `shipment_po_link` — many-to-many: `(shipment_id, po_id, qty_shipped, part_no, items_json)`
- `po_items` — full item list for a PO (source of truth for PO quantities)

### `items_json` (critical field)
`shipment_po_link.items_json` stores a JSON array of items selected for **this specific part-load**:
```json
[{"item_name": "2.0mm Rose Gold", "qty": 3000, "unit": "KG"}, ...]
```
- When a PO ships in parts, only the selected items appear in `items_json`
- Items NOT included in a part are not in that part's `items_json`
- Legacy links (created before per-item selection existed) have `items_json = NULL` → fall back to all `po_items`

### Pattern: always read `items_json`, not `po_items`, for per-shipment item display
Any endpoint or query that renders "what items are in this shipment" MUST:
1. Read `items_json` from `shipment_po_link`
2. If populated → show only those items
3. If NULL/empty → fall back to all `po_items` (legacy compat)

The two endpoints that do this correctly after the 2026-06-26 fix:
- `GET /api/shipments/active-items` → Arrival Planner
- `GET /api/shipments/<sid>/items` → table row expand

### Ship Remaining calculation
`GET /api/po/<pid>/shipment-summary` aggregates shipped quantities **per item** by iterating `items_json` across all parts. The frontend `shipRemaining()` calls this and pre-fills only items with `remaining > 0`.

## Frontend Structure (forwarder_dashboard.html)
- **Active Shipments tab** — sortable table, row expand via `toggleItems()`
- **Arrival Planner tab** — card view, data from `/api/shipments/active-items`
- **Drawer** — side panel with part-load breakdown, `openDrawer(id)` reads from `shipments[]` state
- **New Shipment modal** — `openNewShipmentModal(prefillPoId, prefillItems)` — used by Ship Remaining
- `shipments[]` global state is refreshed via `refresh()` → `fetchShipments()`

## Payment Proof System (multi-slot)

### Tables
- `po_payments` — legacy single-slot table (kept for backward compat, data migrated out)
- `po_payment_proofs` — current table: `(id, po_id, slot_num, slot_label, filename, original, uploaded_at, confirmed, confirmed_at)` with `UNIQUE(po_id, slot_num)`

### Slots
- Slot 1 = **30% Advance** → file saved as `Payment_PO-XXXX_01.pdf`
- Slot 2 = **70% Balance** → file saved as `Payment_PO-XXXX_02.pdf`

### Endpoints
- `GET /api/po/<pid>/payments` → array of both slots' status
- `POST /api/po/<pid>/payments/<slot>` → upload PDF (1 or 2)
- `POST /api/po/<pid>/payments/<slot>/confirm` → lock permanently
- `GET /api/po/<pid>/payments/<slot>/download` → download
- Old `/api/po/<pid>/payment` endpoints → alias to slot 1 (legacy compat)

### Migration
- On startup `database.py` runs `INSERT OR IGNORE` from `po_payments` → `po_payment_proofs` slot 1
- `_migrate_payment_json()` handles legacy `_payment_meta.json` file → slot 1
- `_migrate_legacy_po_payments()` handles old `po_payments` DB rows → slot 1
- Both migrations use `INSERT OR IGNORE` so they are safe to re-run

### Frontend (purchase_order.html)
- Two-slot side-by-side card UI inside the Documents & Attachments modal
- State: `_paymentPendingFiles = {1: null, 2: null}`
- Key functions: `payFileSelected(slot, files)`, `doConfirmPayment(slot)`, `cancelPayment(slot)`, `showPaymentConfirmed(slot, pid, meta)`, `loadPaymentProofStatus(pid)`
- Element IDs follow pattern: `paySlot{N}Upload`, `payDrop{N}`, `payFile{N}`, `payPending{N}`, `payFinal{N}`, `payConfirmed{N}`, `payCName{N}`, `payCMeta{N}`, `payCDl{N}`

## Permissions
Checked via `user_permissions` in Jinja context. Key permissions: `forwarder_edit`, `forwarder_delete`, `forwarder_dashboard`, `po_dashboard`, `admin_rbac`.
