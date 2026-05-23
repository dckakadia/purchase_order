#!/usr/bin/env python3
"""
China → India Import Cost Calculator
Python/Tkinter port of the React app — Gemini AI invoice parser included.
"""

import base64
import json
import os
import tempfile
import threading
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import date
from tkinter import messagebox, ttk

# ─── Config ────────────────────────────────────────────────────────────────
API_KEY_FILE = os.path.expanduser("~/.import_calc_gemini_key")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent?key={key}"
)

# ─── Colors (mirrors JS C object) ──────────────────────────────────────────
BG       = "#f5f0e8"
SURFACE  = "#fffef9"
CARD     = "#ffffff"
BORDER   = "#e2d9c8"
ACCENT   = "#c8602a"
GOLD     = "#b8860b"
GREEN    = "#2e7d32"
RED      = "#c62828"
BLUE     = "#1565c0"
MUTED    = "#7a6e60"
TEXT     = "#2d2520"
THEAD    = "#f0ebe0"
STRIPE   = "#faf7f2"

FONT_MONO = ("Courier", 10)
FONT_BOLD = ("Courier", 10, "bold")
FONT_H    = ("Georgia", 12, "bold")
FONT_SML  = ("Courier", 8)

# ─── Gemini API call (runs in background thread) ───────────────────────────

def parse_invoice_with_gemini(filepath: str, api_key: str, on_progress, on_done, on_error):
    """Read file → base64 → Gemini API → parsed JSON.  Runs in a thread."""
    def _run():
        try:
            on_progress("Reading file…")
            ext = os.path.splitext(filepath)[1].lower()
            mime_map = {".pdf": "application/pdf", ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg", ".png": "image/png"}
            mime = mime_map.get(ext, "application/octet-stream")

            with open(filepath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()

            on_progress("Sending to Gemini AI…")
            prompt = (
                'Extract all line items from this commercial invoice. '
                'Return ONLY valid JSON, no markdown, no explanation:\n'
                '{"invoiceRef": "invoice number or empty string", '
                '"items": [{"name": "item description", "qty": number, "unitPrice": number}]}\n'
                'Rules:\n'
                '- unitPrice = per unit USD price\n'
                '- If only total price given, divide by qty to get unitPrice\n'
                '- qty = numeric value only (no units)\n'
                '- If currency is not USD, still extract the numeric values as-is'
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
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())

            raw = data["candidates"][0]["content"]["parts"][0]["text"]
            # strip markdown fences
            raw = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)
            on_done(parsed)

        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                msg = json.loads(body)["error"]["message"]
            except Exception:
                msg = body[:200]
            on_error(f"API error {e.code}: {msg}")
        except Exception as exc:
            on_error(str(exc))

    threading.Thread(target=_run, daemon=True).start()


# ─── Helpers ───────────────────────────────────────────────────────────────

def fmt_inr(n: float) -> str:
    return "₹" + f"{int(round(n)):,}"

def fmt_usd(n: float) -> str:
    return f"${n:.2f}"

def safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ─── Main Application ───────────────────────────────────────────────────────

class ImportCalcApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("China → India Import Cost Calculator")
        self.configure(bg=BG)
        self.minsize(1100, 700)

        # ── State ──
        self.api_key       = tk.StringVar(value=self._load_key())
        self.invoice_ref   = tk.StringVar()
        self.usd_rate      = tk.DoubleVar(value=84.0)
        self.bank_charges  = tk.DoubleVar(value=0.0)
        self.shipping      = tk.DoubleVar(value=0.0)
        self.custom_duty   = tk.DoubleVar(value=0.0)
        self.local_trans   = tk.DoubleVar(value=0.0)

        # items: list of dicts {name, qty, unitPrice}
        self.items: list[dict] = []
        self._file_path = ""

        # Register trace for live recalc
        for var in (self.usd_rate, self.bank_charges, self.shipping,
                    self.custom_duty, self.local_trans):
            var.trace_add("write", lambda *_: self._recalc())

        self._build_ui()

    # ── Persistence ───────────────────────────────────────────────────────

    def _load_key(self) -> str:
        if os.path.exists(API_KEY_FILE):
            with open(API_KEY_FILE) as f:
                return f.read().strip()
        return ""

    def _save_key(self):
        key = self.api_key.get().strip()
        if key:
            with open(API_KEY_FILE, "w") as f:
                f.write(key)
            self._key_status.config(text="✓ Key saved", fg=GREEN)
        else:
            messagebox.showwarning("Empty", "Please enter an API key first.")

    def _clear_key(self):
        if os.path.exists(API_KEY_FILE):
            os.remove(API_KEY_FILE)
        self.api_key.set("")
        self._key_status.config(text="", fg=MUTED)

    # ── UI Build ──────────────────────────────────────────────────────────

    def _build_ui(self):
        # Scrollable canvas root
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._main = tk.Frame(canvas, bg=BG)
        self._win_id = canvas.create_window((0, 0), window=self._main, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(self._win_id, width=e.width)
        def _on_frame(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", _on_resize)
        self._main.bind("<Configure>", _on_frame)

        # Mouse wheel scroll
        def _scroll(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _scroll)

        self._build_header()
        self._build_api_key_section()

        row1 = tk.Frame(self._main, bg=BG)
        row1.pack(fill="x", padx=16, pady=(0, 12))
        self._build_invoice_section(row1)
        self._build_rate_section(row1)
        self._build_addl_section(row1)

        self._build_items_table()
        self._build_landed_section()

    def _build_header(self):
        hdr = tk.Frame(self._main, bg=TEXT)
        hdr.pack(fill="x")
        tk.Label(hdr, text="IMPORT COST CALCULATOR", bg=TEXT, fg=ACCENT,
                 font=FONT_SML).pack(anchor="w", padx=24, pady=(12, 0))
        top = tk.Frame(hdr, bg=TEXT)
        top.pack(fill="x", padx=24, pady=(0, 12))
        tk.Label(top, text="China → India Landed Cost", bg=TEXT, fg="white",
                 font=("Georgia", 16, "bold")).pack(side="left")
        tk.Button(top, text="🖨  Print Report", bg=ACCENT, fg="white",
                  font=FONT_MONO, relief="flat", bd=0, padx=14, pady=6,
                  command=self._print_report).pack(side="right")

    def _build_api_key_section(self):
        box = tk.LabelFrame(self._main, text=" 🔑  Gemini API Key ", bg=SURFACE,
                            fg=TEXT, font=FONT_BOLD, bd=1, relief="groove")
        box.pack(fill="x", padx=16, pady=(12, 0))
        inner = tk.Frame(box, bg=SURFACE)
        inner.pack(fill="x", padx=12, pady=10)

        tk.Label(inner, text="API Key:", bg=SURFACE, fg=MUTED, font=FONT_SML).pack(side="left")
        entry = tk.Entry(inner, textvariable=self.api_key, show="*",
                         width=55, font=FONT_MONO, bg=CARD, relief="solid", bd=1)
        entry.pack(side="left", padx=(6, 6))

        def toggle_show():
            entry.config(show="" if entry.cget("show") == "*" else "*")
        tk.Button(inner, text="👁", bg=THEAD, fg=MUTED, relief="flat",
                  command=toggle_show).pack(side="left", padx=2)
        tk.Button(inner, text="Save", bg=ACCENT, fg="white", font=FONT_BOLD,
                  relief="flat", padx=10, command=self._save_key).pack(side="left", padx=4)
        tk.Button(inner, text="Clear", bg=THEAD, fg=MUTED, font=FONT_SML,
                  relief="flat", padx=8, command=self._clear_key).pack(side="left")
        self._key_status = tk.Label(inner, text="" if not self._load_key() else "✓ Key saved",
                                    bg=SURFACE, fg=GREEN, font=FONT_SML)
        self._key_status.pack(side="left", padx=8)
        tk.Label(inner, text="Free key → aistudio.google.com/apikey",
                 bg=SURFACE, fg=MUTED, font=FONT_SML).pack(side="right")

    def _section_frame(self, parent, title, icon):
        outer = tk.LabelFrame(parent, text=f" {icon}  {title} ",
                               bg=CARD, fg=TEXT, font=FONT_BOLD, bd=1, relief="groove")
        inner = tk.Frame(outer, bg=CARD)
        inner.pack(fill="both", expand=True, padx=10, pady=8)
        return outer, inner

    def _build_invoice_section(self, parent):
        frm, inner = self._section_frame(parent, "Commercial Invoice", "🧾")
        frm.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=4)

        # Upload button
        self._upload_btn = tk.Button(inner, text="📄  Upload Invoice (PDF / JPG / PNG)",
                                     bg=STRIPE, fg=TEXT, font=FONT_MONO, relief="solid",
                                     bd=1, padx=10, pady=12, width=34,
                                     command=self._pick_file)
        self._upload_btn.pack(fill="x", pady=(0, 6))

        self._progress_lbl = tk.Label(inner, text="", bg=CARD, fg=ACCENT, font=FONT_SML)
        self._progress_lbl.pack()

        tk.Label(inner, text="Invoice Reference:", bg=CARD, fg=MUTED,
                 font=FONT_SML).pack(anchor="w", pady=(8, 2))
        tk.Entry(inner, textvariable=self.invoice_ref, font=FONT_MONO,
                 bg=SURFACE, relief="solid", bd=1).pack(fill="x")

    def _build_rate_section(self, parent):
        frm, inner = self._section_frame(parent, "USD → INR Rate", "💱")
        frm.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=4)

        tk.Label(inner, text="Exchange Rate (1 USD = ₹):", bg=CARD, fg=MUTED,
                 font=FONT_SML).pack(anchor="w", pady=(0, 4))
        rate_row = tk.Frame(inner, bg=CARD)
        rate_row.pack(fill="x")
        tk.Label(rate_row, text="₹", bg=THEAD, fg=MUTED, relief="solid",
                 bd=1, padx=6, font=FONT_MONO).pack(side="left")
        tk.Entry(rate_row, textvariable=self.usd_rate, width=10, font=FONT_MONO,
                 bg=SURFACE, relief="solid", bd=1).pack(side="left")
        tk.Label(rate_row, text="/ USD", bg=THEAD, fg=MUTED, relief="solid",
                 bd=1, padx=6, font=FONT_SML).pack(side="left")

        # Summary box
        summ = tk.Frame(inner, bg=STRIPE, bd=1, relief="solid")
        summ.pack(fill="x", pady=(14, 0))
        tk.Label(summ, text="INVOICE VALUE IN INR", bg=STRIPE, fg=MUTED,
                 font=FONT_SML).pack(anchor="w", padx=10, pady=(6, 0))
        self._inr_total_lbl = tk.Label(summ, text="₹0", bg=STRIPE, fg=ACCENT,
                                        font=("Courier", 18, "bold"))
        self._inr_total_lbl.pack(anchor="w", padx=10)
        self._inr_sub_lbl = tk.Label(summ, text="$0.00 × ₹84", bg=STRIPE, fg=MUTED, font=FONT_SML)
        self._inr_sub_lbl.pack(anchor="w", padx=10, pady=(0, 6))

    def _build_addl_section(self, parent):
        frm, inner = self._section_frame(parent, "Additional Costs (INR)", "➕")
        frm.pack(side="left", fill="both", expand=True, pady=4)

        grid = tk.Frame(inner, bg=CARD)
        grid.pack(fill="x")
        fields = [
            ("🏦 Bank Charges", self.bank_charges, 0, 0),
            ("🚢 Shipping Cost", self.shipping, 0, 1),
            ("🛃 Custom Duty",  self.custom_duty, 1, 0),
            ("🚛 Local Transport", self.local_trans, 1, 1),
        ]
        for label, var, row, col in fields:
            cell = tk.Frame(grid, bg=CARD)
            cell.grid(row=row, column=col, padx=6, pady=6, sticky="ew")
            tk.Label(cell, text=label, bg=CARD, fg=MUTED, font=FONT_SML).pack(anchor="w")
            row_f = tk.Frame(cell, bg=CARD)
            row_f.pack(fill="x")
            tk.Label(row_f, text="₹", bg=THEAD, fg=MUTED, relief="solid",
                     bd=1, padx=5, font=FONT_MONO).pack(side="left")
            tk.Entry(row_f, textvariable=var, width=12, font=FONT_MONO,
                     bg=SURFACE, relief="solid", bd=1).pack(side="left")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        addl = tk.Frame(inner, bg="#fff8f0", bd=1, relief="solid")
        addl.pack(fill="x", pady=(10, 0))
        tk.Label(addl, text="TOTAL ADDITIONAL", bg="#fff8f0", fg=MUTED,
                 font=FONT_SML).pack(side="left", padx=10, pady=6)
        self._addl_lbl = tk.Label(addl, text="₹0", bg="#fff8f0", fg=ACCENT,
                                   font=("Courier", 14, "bold"))
        self._addl_lbl.pack(side="right", padx=10)

    def _build_items_table(self):
        frm, inner = self._section_frame(self._main, "Invoice Items (in USD)", "📦")
        frm.pack(fill="x", padx=16, pady=(0, 12))

        cols = ("#", "Item / Description", "Qty", "Unit Price (USD)", "Total (USD)", "Total (INR)")
        self._items_tv = ttk.Treeview(inner, columns=cols, show="headings", height=6)
        widths = [35, 300, 70, 130, 110, 120]
        for c, w in zip(cols, widths):
            self._items_tv.heading(c, text=c)
            self._items_tv.column(c, width=w, anchor="center" if c != "Item / Description" else "w")
        self._items_tv.pack(fill="x", side="left", expand=True)
        ttk.Scrollbar(inner, orient="vertical",
                      command=self._items_tv.yview).pack(side="right", fill="y")
        self._items_tv.configure(yscrollcommand=lambda *a: None)
        self._items_tv.bind("<Double-1>", self._edit_item_dialog)

        btn_row = tk.Frame(frm, bg=CARD)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Button(btn_row, text="+ Add Item", bg=STRIPE, fg=ACCENT, font=FONT_MONO,
                  relief="solid", bd=1, padx=12, command=self._add_item_dialog).pack(side="left", padx=4)
        tk.Button(btn_row, text="✕ Remove Selected", bg=STRIPE, fg=RED, font=FONT_MONO,
                  relief="solid", bd=1, padx=12, command=self._remove_item).pack(side="left")

    def _build_landed_section(self):
        frm, inner = self._section_frame(self._main, "Item-Wise Landed Cost at Factory — India", "🏭")
        frm.pack(fill="x", padx=16, pady=(0, 16))

        cols = ("#", "Item", "Qty", "Invoice Value (INR)", "Share %",
                "Bank (INR)", "Shipping (INR)", "Duty (INR)", "Transport (INR)",
                "Total Addl. (INR)", "TOTAL LANDED (INR)", "PER UNIT (INR)")
        self._landed_tv = ttk.Treeview(inner, columns=cols, show="headings", height=8)
        widths = [35, 220, 55, 140, 65, 90, 100, 80, 105, 120, 140, 120]
        for c, w in zip(cols, widths):
            self._landed_tv.heading(c, text=c)
            self._landed_tv.column(c, width=w, anchor="center" if c != "Item" else "w",
                                   minwidth=w)
        sb_h = ttk.Scrollbar(inner, orient="horizontal", command=self._landed_tv.xview)
        self._landed_tv.configure(xscrollcommand=sb_h.set)
        self._landed_tv.pack(fill="x", expand=True)
        sb_h.pack(fill="x")

        # Summary row labels
        summ = tk.Frame(frm, bg=CARD)
        summ.pack(fill="x", padx=10, pady=(8, 4))
        self._grand_lbl = tk.Label(summ, text="Grand Total: ₹0", bg=CARD, fg=ACCENT,
                                    font=("Courier", 14, "bold"))
        self._grand_lbl.pack(side="right", padx=12)

        style = ttk.Style()
        style.configure("Treeview", rowheight=26, font=FONT_MONO, background=CARD,
                         fieldbackground=CARD, foreground=TEXT)
        style.configure("Treeview.Heading", font=FONT_BOLD, background=THEAD, foreground=TEXT)
        style.map("Treeview", background=[("selected", "#fdeede")])

    # ── File Handling ─────────────────────────────────────────────────────

    def _pick_file(self):
        if not self.api_key.get().strip():
            messagebox.showwarning("API Key Missing", "Please enter and save your Gemini API key first.")
            return
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select Commercial Invoice",
            filetypes=[("Supported files", "*.pdf *.jpg *.jpeg *.png"),
                       ("All files", "*.*")]
        )
        if not path:
            return
        self._file_path = path
        fname = os.path.basename(path)
        self._upload_btn.config(text=f"⚙  Processing: {fname}", state="disabled", fg=ACCENT)
        self._progress_lbl.config(text="")

        parse_invoice_with_gemini(
            filepath=path,
            api_key=self.api_key.get().strip(),
            on_progress=lambda msg: self.after(0, lambda: self._progress_lbl.config(text=msg)),
            on_done=self._on_parse_done,
            on_error=self._on_parse_error,
        )

    def _on_parse_done(self, parsed: dict):
        self.after(0, lambda: self._apply_parsed(parsed))

    def _on_parse_error(self, msg: str):
        self.after(0, lambda: self._show_parse_error(msg))

    def _apply_parsed(self, parsed: dict):
        if parsed.get("invoiceRef"):
            self.invoice_ref.set(parsed["invoiceRef"])
        raw_items = parsed.get("items", [])
        if raw_items:
            self.items = [
                {"name": it.get("name", ""), "qty": safe_float(it.get("qty", 1), 1),
                 "unitPrice": safe_float(it.get("unitPrice", 0))}
                for it in raw_items
            ]
        else:
            messagebox.showinfo("No Items", "No items extracted. Please add them manually.")
            self.items = [{"name": "", "qty": 1, "unitPrice": 0.0}]
        self._upload_btn.config(
            text=f"✓  {os.path.basename(self._file_path)}  (click to reload)",
            state="normal", fg=GREEN
        )
        self._progress_lbl.config(text="")
        self._recalc()

    def _show_parse_error(self, msg: str):
        self._upload_btn.config(text="📄  Upload Invoice (PDF / JPG / PNG)",
                                state="normal", fg=TEXT)
        self._progress_lbl.config(text="")
        messagebox.showerror("Gemini API Error", msg)

    # ── Item CRUD Dialogs ─────────────────────────────────────────────────

    def _item_dialog(self, title, name="", qty=1.0, price=0.0):
        dlg = tk.Toplevel(self, bg=CARD)
        dlg.title(title)
        dlg.resizable(False, False)
        dlg.grab_set()

        v_name  = tk.StringVar(value=name)
        v_qty   = tk.DoubleVar(value=qty)
        v_price = tk.DoubleVar(value=price)

        def field(lbl, var, row):
            tk.Label(dlg, text=lbl, bg=CARD, fg=MUTED, font=FONT_SML).grid(
                row=row, column=0, sticky="w", padx=14, pady=6)
            e = tk.Entry(dlg, textvariable=var, font=FONT_MONO, bg=SURFACE,
                         relief="solid", bd=1, width=28)
            e.grid(row=row, column=1, padx=14, pady=6)
            return e

        e_name = field("Item / Description:", v_name, 0)
        field("Quantity:", v_qty, 1)
        field("Unit Price (USD):", v_price, 2)
        e_name.focus()

        result = {}
        def ok():
            result["name"]      = v_name.get()
            result["qty"]       = safe_float(v_qty.get(), 1)
            result["unitPrice"] = safe_float(v_price.get(), 0)
            dlg.destroy()
        def cancel():
            dlg.destroy()

        btn_row = tk.Frame(dlg, bg=CARD)
        btn_row.grid(row=3, column=0, columnspan=2, pady=10)
        tk.Button(btn_row, text="OK", bg=ACCENT, fg="white", font=FONT_BOLD,
                  relief="flat", padx=16, command=ok).pack(side="left", padx=6)
        tk.Button(btn_row, text="Cancel", bg=THEAD, fg=MUTED, font=FONT_MONO,
                  relief="flat", padx=10, command=cancel).pack(side="left")
        dlg.wait_window()
        return result if result else None

    def _add_item_dialog(self):
        res = self._item_dialog("Add Item")
        if res:
            self.items.append(res)
            self._recalc()

    def _edit_item_dialog(self, _event=None):
        sel = self._items_tv.selection()
        if not sel:
            return
        idx = int(self._items_tv.item(sel[0])["values"][0]) - 1
        it = self.items[idx]
        res = self._item_dialog("Edit Item", it["name"], it["qty"], it["unitPrice"])
        if res:
            self.items[idx] = res
            self._recalc()

    def _remove_item(self):
        sel = self._items_tv.selection()
        if not sel:
            return
        idx = int(self._items_tv.item(sel[0])["values"][0]) - 1
        self.items.pop(idx)
        self._recalc()

    # ── Calculation & Refresh ─────────────────────────────────────────────

    def _recalc(self):
        rate     = safe_float(self.usd_rate.get(), 84)
        bank     = safe_float(self.bank_charges.get())
        ship     = safe_float(self.shipping.get())
        duty     = safe_float(self.custom_duty.get())
        trans    = safe_float(self.local_trans.get())
        total_addl = bank + ship + duty + trans

        inv_usd = sum(it["qty"] * it["unitPrice"] for it in self.items)
        inv_inr = inv_usd * rate
        grand   = inv_inr + total_addl

        # Header labels
        self._inr_total_lbl.config(text=fmt_inr(inv_inr))
        self._inr_sub_lbl.config(text=f"{fmt_usd(inv_usd)} × ₹{rate:.0f}")
        self._addl_lbl.config(text=fmt_inr(total_addl))
        self._grand_lbl.config(text=f"Grand Total: {fmt_inr(grand)}")

        # Items table
        for row in self._items_tv.get_children():
            self._items_tv.delete(row)
        for i, it in enumerate(self.items):
            total_usd = it["qty"] * it["unitPrice"]
            total_inr = total_usd * rate
            self._items_tv.insert("", "end", values=(
                i + 1,
                it["name"] or f"Item {i+1}",
                it["qty"],
                fmt_usd(it["unitPrice"]),
                fmt_usd(total_usd),
                fmt_inr(total_inr),
            ))

        # Landed table
        for row in self._landed_tv.get_children():
            self._landed_tv.delete(row)

        calc = []
        for it in self.items:
            item_inr   = it["qty"] * it["unitPrice"] * rate
            share      = (item_inr / inv_inr) if inv_inr > 0 else 0
            addl_share = total_addl * share
            total_item = item_inr + addl_share
            per_unit   = (total_item / it["qty"]) if it["qty"] > 0 else 0
            calc.append({**it, "item_inr": item_inr, "share": share,
                         "addl_share": addl_share, "total_item": total_item,
                         "per_unit": per_unit,
                         "bank_s": bank * share, "ship_s": ship * share,
                         "duty_s": duty * share, "trans_s": trans * share})

        for i, c in enumerate(calc):
            tag = "stripe" if i % 2 else ""
            self._landed_tv.insert("", "end", values=(
                i + 1,
                c["name"] or f"Item {i+1}",
                c["qty"],
                fmt_inr(c["item_inr"]),
                f"{c['share']*100:.1f}%",
                fmt_inr(c["bank_s"]),
                fmt_inr(c["ship_s"]),
                fmt_inr(c["duty_s"]),
                fmt_inr(c["trans_s"]),
                fmt_inr(c["addl_share"]),
                fmt_inr(c["total_item"]),
                fmt_inr(c["per_unit"]),
            ), tags=(tag,))

        self._landed_tv.tag_configure("stripe", background=STRIPE)

        # Grand total row
        self._landed_tv.insert("", "end", values=(
            "", "GRAND TOTAL", "",
            fmt_inr(inv_inr), "100%",
            fmt_inr(bank), fmt_inr(ship), fmt_inr(duty), fmt_inr(trans),
            fmt_inr(total_addl), fmt_inr(grand), "—",
        ), tags=("total",))
        self._landed_tv.tag_configure("total", background=TEXT, foreground="white")

    # ── Print Report (HTML → browser → Ctrl+P) ───────────────────────────

    def _print_report(self):
        if not self.items:
            messagebox.showinfo("No Data", "Add invoice items before printing.")
            return

        rate       = safe_float(self.usd_rate.get(), 84)
        bank       = safe_float(self.bank_charges.get())
        ship       = safe_float(self.shipping.get())
        duty       = safe_float(self.custom_duty.get())
        trans      = safe_float(self.local_trans.get())
        total_addl = bank + ship + duty + trans
        inv_usd    = sum(it["qty"] * it["unitPrice"] for it in self.items)
        inv_inr    = inv_usd * rate
        grand      = inv_inr + total_addl

        # Build per-item calculations
        calc = []
        for it in self.items:
            item_inr   = it["qty"] * it["unitPrice"] * rate
            share      = (item_inr / inv_inr) if inv_inr > 0 else 0
            addl_share = total_addl * share
            total_item = item_inr + addl_share
            per_unit   = (total_item / it["qty"]) if it["qty"] > 0 else 0
            calc.append({**it, "item_inr": item_inr, "share": share,
                         "addl_share": addl_share, "total_item": total_item,
                         "per_unit": per_unit,
                         "bank_s": bank * share, "ship_s": ship * share,
                         "duty_s": duty * share, "trans_s": trans * share})

        # Build summary boxes HTML
        summary_boxes = "".join(f"""
            <div class="summary-box">
                <div class="summary-label">{lbl}</div>
                <div class="summary-value" style="color:{col}">{val}</div>
                <div class="summary-sub">{sub} <span class="badge" style="background:{col}22;color:{col}">{pct}%</span></div>
            </div>""" for lbl, val, sub, col, pct in [
            ("Invoice Value",   fmt_inr(inv_inr),   fmt_usd(inv_usd),    "#b8860b", f"{inv_inr/grand*100:.1f}" if grand else "0"),
            ("Bank + Shipping", fmt_inr(bank+ship),  "Bank & Shipping",   "#1565c0", f"{(bank+ship)/grand*100:.1f}" if grand else "0"),
            ("Duty + Transport",fmt_inr(duty+trans), "Custom & Local",    "#7b1fa2", f"{(duty+trans)/grand*100:.1f}" if grand else "0"),
            ("Total Landed",    fmt_inr(grand),      "Factory Delivered", "#c8602a", "100.0"),
        ])

        # Build item rows HTML
        item_rows = ""
        for i, c in enumerate(calc):
            bg = "#ffffff" if i % 2 == 0 else "#faf7f2"
            item_rows += f"""
            <tr style="background:{bg}">
                <td style="text-align:center;color:#7a6e60">{i+1}</td>
                <td style="font-weight:600">{c['name'] or f'Item {i+1}'}</td>
                <td style="text-align:center">{c['qty']}</td>
                <td style="text-align:center;color:#1565c0">{fmt_usd(c['unitPrice'])}</td>
                <td style="text-align:center;color:#b8860b">{fmt_inr(c['item_inr'])}</td>
                <td style="text-align:center"><span class="badge" style="background:#c8602a22;color:#c8602a">{c['share']*100:.1f}%</span></td>
                <td style="text-align:center;color:#1565c0">{fmt_inr(c['bank_s'])}</td>
                <td style="text-align:center;color:#1565c0">{fmt_inr(c['ship_s'])}</td>
                <td style="text-align:center;color:#1565c0">{fmt_inr(c['duty_s'])}</td>
                <td style="text-align:center;color:#1565c0">{fmt_inr(c['trans_s'])}</td>
                <td style="text-align:center;font-weight:700;border-right:2px solid #c8602a">{fmt_inr(c['addl_share'])}</td>
                <td style="text-align:center;background:#fff3e0"><strong style="color:#c8602a;font-size:13px">{fmt_inr(c['total_item'])}</strong></td>
                <td style="text-align:center;background:#fff8f0"><strong style="color:#c8602a;font-size:14px">{fmt_inr(c['per_unit'])}</strong><br><span style="color:#7a6e60;font-size:9px">per unit</span></td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Landed Cost Report — {self.invoice_ref.get() or date.today().isoformat()}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Fraunces:wght@400;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'DM Mono', Courier, monospace; font-size: 11px; color: #2d2520; background: #fff; padding: 24px; }}
  h1 {{ font-family: 'Fraunces', Georgia, serif; font-size: 20px; font-weight: 800; color: #2d2520; letter-spacing: -0.5px; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start;
             border-bottom: 2.5px solid #2d2520; padding-bottom: 10px; margin-bottom: 14px; }}
  .header-right {{ text-align: right; color: #7a6e60; font-size: 10px; line-height: 1.7; }}
  .header-right strong {{ color: #2d2520; font-size: 12px; }}

  .cost-grid {{ display: grid; grid-template-columns: repeat(6,1fr); gap: 8px; margin-bottom: 14px; }}
  .cost-box {{ border: 1px solid #e2d9c8; border-radius: 5px; padding: 7px 9px; background: #faf7f2; }}
  .cost-box .lbl {{ font-size: 8px; color: #7a6e60; margin-bottom: 3px; }}
  .cost-box .val {{ font-size: 12px; font-weight: 700; }}

  .summary-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin: 16px 0; }}
  .summary-box {{ border: 1px solid #e2d9c8; border-radius: 7px; padding: 10px 12px; }}
  .summary-label {{ font-size: 9px; color: #7a6e60; letter-spacing: 0.8px; margin-bottom: 4px; text-transform:uppercase; }}
  .summary-value {{ font-size: 16px; font-weight: 700; margin-bottom: 3px; }}
  .summary-sub {{ font-size: 9px; color: #7a6e60; display: flex; justify-content: space-between; align-items: center; }}
  .badge {{ padding: 1px 7px; border-radius: 20px; font-size: 9px; font-weight: 600; }}

  table {{ width: 100%; border-collapse: collapse; font-size: 10px; }}
  th {{ background: #2d2520; color: #ccc; padding: 7px 6px; font-size: 9px; font-weight: 600;
        letter-spacing: 0.5px; white-space: nowrap; }}
  th.highlight {{ color: #e8845a; font-weight: 800; }}
  td {{ padding: 5px 6px; border-bottom: 1px solid #e2d9c8; }}
  tfoot td {{ background: #2d2520 !important; color: #fff; font-weight: 700; padding: 8px 6px; }}
  tfoot .grand {{ background: #c8602a !important; text-align: center; }}
  tfoot .grand .g-val {{ font-size: 14px; font-weight: 800; color: #fff; }}
  tfoot .grand .g-sub {{ font-size: 8px; color: #ffd54f; margin-top: 2px; }}

  .footer {{ margin-top: 10px; border-top: 1px solid #e2d9c8; padding-top: 6px;
             display: flex; justify-content: space-between; font-size: 8.5px; color: #7a6e60; }}
  .no-print {{ margin-bottom: 16px; text-align: center; }}
  .print-btn {{ background: #c8602a; color: #fff; border: none; border-radius: 7px;
                padding: 10px 28px; font-size: 14px; cursor: pointer; font-family: inherit; font-weight: 600; }}
  .print-btn:hover {{ background: #a0491e; }}
  @media print {{
    .no-print {{ display: none !important; }}
    @page {{ margin: 1cm; size: A4 landscape; }}
  }}
</style>
</head>
<body>

<div class="no-print">
  <button class="print-btn" onclick="window.print()">🖨 &nbsp;Print / Save as PDF</button>
</div>

<div class="header">
  <div>
    <div style="font-size:10px;color:#c8602a;letter-spacing:2px;margin-bottom:4px">IMPORT COST CALCULATOR</div>
    <h1>China → India Landed Cost Report</h1>
    <div style="font-size:9px;color:#7a6e60;margin-top:3px">Item-Wise Breakdown with Proportional Cost Allocation</div>
  </div>
  <div class="header-right">
    {'<strong>Invoice Ref: ' + self.invoice_ref.get() + '</strong><br>' if self.invoice_ref.get() else ''}
    Date: {date.today().strftime("%d-%m-%Y")}<br>
    Rate: 1 USD = ₹{rate:.2f}
  </div>
</div>

<div class="cost-grid">
  {''.join(f'<div class="cost-box"><div class="lbl">{l}</div><div class="val">{v}</div></div>' for l,v in [
    ("Invoice Value (USD)", fmt_usd(inv_usd)),
    ("Invoice Value (INR)", fmt_inr(inv_inr)),
    ("Bank Charges",        fmt_inr(bank)),
    ("Shipping Cost",       fmt_inr(ship)),
    ("Custom Duty",         fmt_inr(duty)),
    ("Local Transport",     fmt_inr(trans)),
  ])}
</div>

<table>
  <thead>
    <tr>
      <th>#</th><th style="text-align:left">Item / Description</th><th>Qty</th>
      <th>Unit Price</th><th>Invoice Value (INR)</th><th>Share</th>
      <th>Bank Charges</th><th>Shipping</th><th>Custom Duty</th><th>Local Trans.</th>
      <th style="border-right:2px solid #c8602a">Total Addl.</th>
      <th class="highlight">TOTAL LANDED (INR)</th>
      <th class="highlight">PER UNIT (INR)</th>
    </tr>
  </thead>
  <tbody>{item_rows}</tbody>
  <tfoot>
    <tr>
      <td colspan="4" style="color:#fff;font-weight:700">GRAND TOTAL</td>
      <td style="text-align:center;color:#ffd54f;font-weight:700">{fmt_inr(inv_inr)}</td>
      <td style="text-align:center;color:#aaa">100%</td>
      <td style="text-align:center;color:#90caf9">{fmt_inr(bank)}</td>
      <td style="text-align:center;color:#90caf9">{fmt_inr(ship)}</td>
      <td style="text-align:center;color:#90caf9">{fmt_inr(duty)}</td>
      <td style="text-align:center;color:#90caf9">{fmt_inr(trans)}</td>
      <td style="text-align:center;color:#fff;font-weight:700;border-right:2px solid #c8602a">{fmt_inr(total_addl)}</td>
      <td colspan="2" class="grand">
        <div class="g-val">{fmt_inr(grand)}</div>
        <div class="g-sub">TOTAL LANDED COST</div>
      </td>
    </tr>
  </tfoot>
</table>

<div class="summary-grid">{summary_boxes}</div>

<div class="footer">
  <span>Additional costs allocated proportionally by invoice value share.</span>
  <strong style="color:#2d2520">Total Landed: {fmt_inr(grand)} &nbsp;|&nbsp; Invoice: {fmt_usd(inv_usd)} @ ₹{rate:.2f}</strong>
</div>

</body></html>"""

        # Write to temp file and open in browser
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False,
            encoding="utf-8", prefix="landed_cost_"
        )
        tmp.write(html)
        tmp.close()
        webbrowser.open(f"file://{tmp.name}")


# ─── Entry Point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = ImportCalcApp()
    app.mainloop()
