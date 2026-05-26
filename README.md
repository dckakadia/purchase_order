# Purchase Order — Greenwave Traders

A unified, single-page application dashboard for managing Purchase Orders, Supplier/Customer Ledgers, Forwarder logistics, and Quotation analytics. Built with Python (Flask) and a local SQLite database for speed and portability.

---

## Features

- **Unified Dashboard**: Access all features (POs, Ledgers, Analytics) from a single seamless interface.
- **Dynamic Role-Based Access Control (RBAC)**: Assign specific page-level permissions to users. An intuitive Admin UI allows managers to adjust access via a permission matrix.
- **SQLite Database**: Self-contained `database.db` ensures data portability and eliminates the need for separate database servers.
- **PM2 Process Management**: Managed via `ecosystem.config.js` for automatic restarts, log management, and robust deployment.

---

## Setup & Execution (Local Development)

### 1. Prerequisites
- Python 3.9+
- A Virtual Environment (`venv`)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/dckakadia/purchase_order.git
cd purchase_order

# Create and activate virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Install dependencies (assuming you have a requirements.txt)
pip install -r requirements.txt
```

### 3. Running the App
Start the development server:
```bash
python purchase_order_app.py
```
*The app will be available at `http://127.0.0.1:8090`.*

---

## Authentication & Default Credentials

The system utilizes an internal RBAC system. When the database is initialized for the first time, a default administrator account is generated.

**Default Login:**
- **Username**: `admin`
- **Password**: `admin`

> **Warning:** It is highly recommended to change the admin password via the Admin Panel immediately after your first login in a production environment.

---

## Deployment (Production with PM2)

For production deployment on Windows or Linux, PM2 (Node.js) is recommended to keep the application running continuously in the background.

```bash
# Install PM2 globally (requires Node.js)
npm install -g pm2

# Start the application using the ecosystem config
pm2 start ecosystem.config.js

# Save the PM2 state to resurrect on reboot
pm2 save
```

Logs can be monitored using:
```bash
pm2 logs purchase_order
```

---

## File Structure

```
purchase_order/
├── purchase_order_app.py       # Main Flask application and API routes
├── database.py                 # SQLite schema definitions and initializers
├── ecosystem.config.js         # PM2 configuration for background execution
├── purchase_order_wrapper.py   # WSGI/Gunicorn wrapper script for deployment
├── data/po/                    # Persistent database storage directory
│   ├── database.db             # The SQLite database (auto-generated)
│   └── attachments/            # Uploaded physical files and attachments
└── templates/                  # HTML Templates
    ├── purchase_order.html     # Main application dashboard
    ├── login.html              # Authentication page
    ├── admin_roles.html        # RBAC and User management panel
    ├── supplier_book.html      # Supplier Ledger interface
    ├── customer_book.html      # Customer Ledger interface
    └── forwarder_dashboard.html# Forwarder logistics interface
```
