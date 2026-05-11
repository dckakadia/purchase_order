"""
SQLite Database Schema & Initialization
Replaces JSON-based storage (po_data.json) with relational SQLite database
"""

import sqlite3
import os
from contextlib import contextmanager
from datetime import date

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "po", "database.db")


def get_db_path():
    """Get database path and ensure directory exists"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


def get_connection():
    """Get a connection to the SQLite database"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
    return conn


@contextmanager
def get_db():
    """Context manager for database connections.

    Auto-commits when the ``with`` block exits cleanly; rolls back (and
    re-raises) on any exception.  Explicit ``conn.commit()`` calls inside the
    block are still safe — SQLite treats them as no-ops if nothing is pending.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()   # commit on clean exit
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _safe_add_column(cursor, table, column, definition):
    """Add a column to an existing table only if it doesn't already exist.

    SQLite doesn't support ALTER TABLE ... ADD COLUMN IF NOT EXISTS, so we
    inspect pragma table_info instead.
    """
    cursor.execute(f"PRAGMA table_info(\"{table}\")")
    rows = cursor.fetchall()
    existing = {row[1] for row in rows}
    if column not in existing:
        cursor.execute(f"ALTER TABLE \"{table}\" ADD COLUMN {column} {definition}")


def init_db():
    """Initialize database schema - run once on startup"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
    
        # ── SUPPLIERS TABLE ──────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                company TEXT NOT NULL,
                address TEXT,
                country TEXT DEFAULT 'China',
                email TEXT,
                phone TEXT,
                wechat TEXT,
                bank_name TEXT,
                bank_account TEXT,
                swift_code TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, company)
            )
        """)
    
        # ── ITEMS TABLE ──────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                hs_code TEXT,
                unit TEXT DEFAULT 'PCS',
                currency TEXT DEFAULT 'CNY',
                default_price_usd REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
        # ── FORWARDERS TABLE ─────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forwarders (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                godowns TEXT,  -- JSON array kept for legacy reads; canonical data in forwarder_godowns
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
        # ── FORWARDER GODOWNS TABLE ──────────────────────────────────────────────
        # Stores full godown objects: label, contact_person, phone, email, address.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forwarder_godowns (
                id             TEXT PRIMARY KEY,
                forwarder_id   TEXT NOT NULL,
                name           TEXT NOT NULL DEFAULT '',
                contact_person TEXT NOT NULL DEFAULT '',
                phone          TEXT NOT NULL DEFAULT '',
                email          TEXT NOT NULL DEFAULT '',
                address        TEXT NOT NULL DEFAULT '',
                sort_order     INTEGER DEFAULT 0,
                FOREIGN KEY (forwarder_id) REFERENCES forwarders(id) ON DELETE CASCADE
            )
        """)
        # Migrate existing tables that may be missing the new columns
        for col, defn in [
            ("contact_person", "TEXT NOT NULL DEFAULT ''"),
            ("phone",          "TEXT NOT NULL DEFAULT ''"),
            ("email",          "TEXT NOT NULL DEFAULT ''"),
            ("address",        "TEXT NOT NULL DEFAULT ''"),
        ]:
            _safe_add_column(cursor, "forwarder_godowns", col, defn)
    
        # ── PURCHASE ORDERS TABLE ────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id TEXT PRIMARY KEY,
                po_number TEXT UNIQUE NOT NULL,
                po_date TEXT NOT NULL,
                supplier_id TEXT NOT NULL,
                supplier_snapshot TEXT,  -- JSON stored as TEXT for historical record
                payment_conditions TEXT,
                delivery_terms TEXT DEFAULT 'FOB',
                delivery_address TEXT,
                forwarder_id TEXT,
                forwarder_name TEXT,
                forwarder_contact TEXT,
                remarks TEXT,
                currency TEXT DEFAULT 'USD',
                status TEXT DEFAULT 'Draft',
                created_at TEXT NOT NULL,
                lead_time_days INTEGER DEFAULT 0,
                due_date TEXT,
                godown_id TEXT,
    
                -- Landing Cost fields
                lc_usd_rate REAL DEFAULT 84.0,
                lc_rmb_rate REAL DEFAULT 11.5,
                lc_bank REAL DEFAULT 0.0,
                lc_ship REAL DEFAULT 0.0,
                lc_duty REAL DEFAULT 0.0,
                lc_trans REAL DEFAULT 0.0,
                lc_gst_duty REAL DEFAULT 0.0,
                lc_doc_pct REAL DEFAULT 0.0,
                attach_count INTEGER DEFAULT 0,
    
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT DEFAULT NULL,  -- NULL = active; timestamp = soft-deleted
    
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT
            )
        """)
    
        # Migrate existing purchase_orders table if deleted_at column is missing
        _safe_add_column(cursor, "purchase_orders", "deleted_at", "TEXT DEFAULT NULL")
        _safe_add_column(cursor, "purchase_orders", "attach_count", "INTEGER DEFAULT 0")
        _safe_add_column(cursor, "purchase_orders", "godown_id", "TEXT")
    
        # ── PO ATTACHMENTS TABLE ─────────────────────────────────────────────────
        # Replaces per-PO _meta.json files so attachments travel with DB backups.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS po_attachments (
                id          TEXT PRIMARY KEY,
                po_id       TEXT NOT NULL,
                filename    TEXT NOT NULL,   -- UUID-based safe name on disk
                original    TEXT NOT NULL,   -- Original upload filename
                label       TEXT NOT NULL,
                mime        TEXT NOT NULL DEFAULT 'application/octet-stream',
                uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (po_id) REFERENCES purchase_orders(id) ON DELETE CASCADE
            )
        """)
    
        # Backfill attach_count for existing purchase orders
        cursor.execute("""
            UPDATE purchase_orders 
            SET attach_count = (
                SELECT count(*) 
                FROM po_attachments 
                WHERE po_attachments.po_id = purchase_orders.id
            )
        """)
    
        # ── PO STATUS LOG TABLE ──────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS po_status_log (
                id          TEXT PRIMARY KEY,
                po_id       TEXT NOT NULL,
                from_status TEXT,          -- NULL for the initial Draft entry
                to_status   TEXT NOT NULL,
                changed_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                note        TEXT,          -- Optional user comment, e.g. "Supplier confirmed ETD Jan 5"
                FOREIGN KEY (po_id) REFERENCES purchase_orders(id) ON DELETE CASCADE
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_po_status_log_po_id ON po_status_log(po_id)"
        )

        # Migration: create po_status_log on databases that pre-date the table
        # (CREATE TABLE IF NOT EXISTS above handles new DBs; this catches existing ones)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='po_status_log'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE po_status_log (
                    id          TEXT PRIMARY KEY,
                    po_id       TEXT NOT NULL,
                    from_status TEXT,
                    to_status   TEXT NOT NULL,
                    changed_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    note        TEXT,
                    FOREIGN KEY (po_id) REFERENCES purchase_orders(id) ON DELETE CASCADE
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_po_status_log_po_id ON po_status_log(po_id)"
            )

        # ── PO LINE ITEMS TABLE ──────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS po_items (
                id TEXT PRIMARY KEY,
                po_id TEXT NOT NULL,
                item_id TEXT,
                item_name TEXT NOT NULL,
                description TEXT,
                hs_code TEXT,
                qty REAL NOT NULL,
                unit TEXT DEFAULT 'PCS',
                unit_price REAL NOT NULL,
                line_sequence INTEGER,  -- For ordering
                FOREIGN KEY (po_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
            )
        """)
    
        # ── QUOTATIONS TABLE ─────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotations (
                id TEXT PRIMARY KEY,
                quotation_number TEXT UNIQUE,
                title TEXT NOT NULL DEFAULT '',
                currency TEXT DEFAULT 'CNY',
                status TEXT DEFAULT 'Open',
                awarded_to TEXT,
                customer_ref TEXT,
                notes TEXT,
                date TEXT,
                details TEXT,  -- Full JSON payload (legacy; canonical data in line-item tables)
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
        # ── QUOTATION LINE ITEMS TABLE ───────────────────────────────────────────
        # Normalised representation of line_items buried in quotations.details.
        # Populated (replaced) on every quotation save alongside the blob.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotation_line_items (
                id TEXT PRIMARY KEY,
                quotation_id TEXT NOT NULL,
                item_id TEXT,
                item_name TEXT NOT NULL,
                qty REAL NOT NULL DEFAULT 1,
                unit TEXT DEFAULT 'PCS',
                description TEXT DEFAULT '',
                selected_supplier_id TEXT,
                selected_supplier_name TEXT,
                line_sequence INTEGER DEFAULT 0,
                FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
            )
        """)
    
        # Migrate existing quotation_line_items table if description column is missing
        _safe_add_column(cursor, "quotation_line_items", "description", "TEXT DEFAULT ''")
    
        # ── QUOTATION SUPPLIER ROWS TABLE ────────────────────────────────────────
        # Per-line-item supplier prices; replaces the nested supplier_rows JSON.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotation_supplier_rows (
                id TEXT PRIMARY KEY,
                line_item_id TEXT NOT NULL,
                quotation_id TEXT NOT NULL,  -- denormalised for fast per-quotation deletes
                supplier_id TEXT,
                supplier_name TEXT,
                price REAL DEFAULT 0,
                FOREIGN KEY (line_item_id) REFERENCES quotation_line_items(id) ON DELETE CASCADE,
                FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
            )
        """)
    
        # ── QUOTATION REFERENCE TABLE ────────────────────────────────────────────
        # Tracks which suppliers / items appear in each quotation.
        # Populated (replaced) every time a quotation is saved, enabling O(1)
        # reference-checks in delete_supplier / delete_item without JSON scanning.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotation_refs (
                quotation_id   TEXT NOT NULL,
                ref_type       TEXT NOT NULL,   -- 'supplier' or 'item'
                ref_id         TEXT NOT NULL,
                PRIMARY KEY (quotation_id, ref_type, ref_id),
                FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
            )
        """)
    
    
    
        # ── PO PAYMENT PROOFS TABLE ──────────────────────────────────────────────
        # Replaces per-PO _payment_meta.json files.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS po_payments (
                po_id        TEXT PRIMARY KEY,
                filename     TEXT NOT NULL,
                original     TEXT NOT NULL,
                uploaded_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                confirmed    INTEGER NOT NULL DEFAULT 0,   -- 0 / 1 boolean
                confirmed_at TEXT,
                FOREIGN KEY (po_id) REFERENCES purchase_orders(id) ON DELETE CASCADE
            )
        """)
    
        # ── SETTINGS TABLE ──────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
    
        # ── TRIGGERS ────────────────────────────────────────────────────────────
        # Automatically keep updated_at current on every UPDATE so individual
        # routes don't need to remember to set it.  SQLite recursive triggers are
        # OFF by default so the inner UPDATE won't re-fire the trigger.
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_po_updated_at
            AFTER UPDATE ON purchase_orders
            FOR EACH ROW
            WHEN OLD.updated_at = NEW.updated_at  -- only fire if caller didn't set it
              OR NEW.updated_at IS NULL
            BEGIN
                UPDATE purchase_orders
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.id;
            END
        """)
    
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_quotation_updated_at
            AFTER UPDATE ON quotations
            FOR EACH ROW
            WHEN OLD.updated_at = NEW.updated_at
              OR NEW.updated_at IS NULL
            BEGIN
                UPDATE quotations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.id;
            END
        """)
    
        # ── INDEXES FOR PERFORMANCE ─────────────────────────────────────────────
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_po_supplier_id ON purchase_orders(supplier_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_po_status ON purchase_orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_po_date ON purchase_orders(po_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_po_deleted_at ON purchase_orders(deleted_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_po_items_po_id ON po_items(po_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_qrefs_ref_id ON quotation_refs(ref_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_qrefs_type_id ON quotation_refs(ref_type, ref_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_po_attach_po_id ON po_attachments(po_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_qli_quotation_id ON quotation_line_items(quotation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_qsr_line_item_id ON quotation_supplier_rows(line_item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_qsr_quotation_id ON quotation_supplier_rows(quotation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fwd_godowns_fid ON forwarder_godowns(forwarder_id)")
    
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_default_settings(conn):
    """Initialize default settings if not already present"""
    cursor = conn.cursor()

    defaults = {
        "company_name": "Your Company Name",
        "company_address": "",
        "company_phone": "",
        "company_email": "",
        "company_website": "",
        "company_gstin": "",
        "default_usd_rate": "84.0",
        "default_rmb_rate": "11.5",
        "po_prefix": "PO",
        "po_sequence": "0",
    }

    for key, value in defaults.items():
        cursor.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )

    conn.commit()


if __name__ == "__main__":
    print("Initializing database...")
    init_db()

    with get_db() as conn:
        init_default_settings(conn)

    print(f"✓ Database initialized at: {get_db_path()}")
