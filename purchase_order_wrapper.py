"""
Gunicorn entry point for Purchase Order tool.
File: /home/dckakadia/purchase_order/purchase_order_wrapper.py
"""
from purchase_order_app import app  # noqa

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004)
