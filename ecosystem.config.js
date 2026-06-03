module.exports = {
  apps: [
    {
      name: "purchase_order",
      script: "venv/bin/gunicorn",
      args: "--bind 0.0.0.0:8090 --workers 2 --timeout 120 purchase_order_app:app",
      interpreter: "none",
      cwd: "./",
      error_file: "./logs/purchase_order_error.log",
      out_file: "./logs/purchase_order_out.log",
      merge_logs: true,
      time: true
    }
  ]
};
