"""
Gunicorn entry point for Purchase Order tool.
File: /home/dckakadia/import-tools-portal/po_wrapper.py
"""
from po_flask import app  # noqa

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004)
