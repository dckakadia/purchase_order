import re

def categorize_route(url, method):
    url = url.split("<")[0] # remove params
    url = url.rstrip("/")
    if url.startswith("/api/admin") or url in ["/api/settings", "/api/reset", "/api/import"]:
        return "admin_rbac"
    if url.startswith("/api/po") or url.startswith("/api/items") or url.startswith("/api/quotations") or url.startswith("/api/lc-report") or url.startswith("/api/scan-invoice"):
        return "po_" + ("delete" if method == "DELETE" else "edit")
    if url.startswith("/api/suppliers") or url.startswith("/api/ledger/supplier"):
        return "supplier_" + ("delete" if method == "DELETE" else "edit")
    if url.startswith("/api/customers") or url.startswith("/api/ledger/customer"):
        return "customer_" + ("delete" if method == "DELETE" else "edit")
    if url.startswith("/api/forwarders") or url.startswith("/api/shipments"):
        return "forwarder_" + ("delete" if method == "DELETE" else "edit")
    return None

with open("purchase_order_app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip_next_require = False
for i, line in enumerate(lines):
    if line.strip().startswith("@app.route"):
        new_lines.append(line)
        # Parse route and methods
        match = re.search(r'@app\.route\("([^"]+)"', line)
        if not match:
            match = re.search(r"@app\.route\('([^']+)'", line)
        
        methods_match = re.search(r'methods=\[([^\]]+)\]', line)
        methods = ["GET"] # default
        if methods_match:
            methods_str = methods_match.group(1).replace('"', '').replace("'", "").replace(" ", "")
            methods = methods_str.split(",")
        
        if match:
            url = match.group(1)
            # Find if this route needs protection
            # We only protect modifying routes here, GETs are read-only (mostly).
            needs_protection = False
            perm = None
            for m in methods:
                if m in ["POST", "PUT", "DELETE"]:
                    perm = categorize_route(url, m)
                    if perm:
                        needs_protection = True
                        break
            
            if needs_protection and perm:
                # Check if the next line is already a @require_permission
                if i + 1 < len(lines) and "@require_permission" in lines[i+1]:
                    pass # already there, we might need to update it? No, script is run once.
                else:
                    indent = line[:len(line) - len(line.lstrip())]
                    new_lines.append(f'{indent}@require_permission("{perm}")\n')
    else:
        new_lines.append(line)

with open("purchase_order_app.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Patching complete.")
