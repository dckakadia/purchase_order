import os
import re

def patch_template(filepath, edit_perm, delete_perm):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Inject the style overrides just before </head>
    injection = f"""
    {{% if '{edit_perm}' not in user_permissions %}}
    <style> .req-edit {{ display: none !important; pointer-events: none !important; }} </style>
    {{% endif %}}
    {{% if '{delete_perm}' not in user_permissions %}}
    <style> .req-delete {{ display: none !important; pointer-events: none !important; }} </style>
    {{% endif %}}
    </head>
"""
    if "</head>" in content and "req-edit" not in content:
        content = content.replace("</head>", injection, 1)

    # Now add req-edit and req-delete to specific elements
    # Helper to add class
    def add_class(match, cls):
        tag = match.group(0)
        if 'class="' in tag:
            return tag.replace('class="', f'class="{cls} ')
        else:
            # insert class before closing >
            return tag.replace('>', f' class="{cls}">')

    # Add req-edit to things that look like Add/Edit/Save buttons
    # We use regex to find buttons or anchors with specific text
    
    # 1. New / Add buttons
    content = re.sub(r'<button[^>]*>\s*\+\s*New[^<]*</button>', lambda m: add_class(m, "req-edit"), content, flags=re.IGNORECASE)
    content = re.sub(r'<button[^>]*>\s*\+\s*Add[^<]*</button>', lambda m: add_class(m, "req-edit"), content, flags=re.IGNORECASE)
    
    # 2. Save buttons
    content = re.sub(r'<button[^>]*>.*?Save.*?</button>', lambda m: add_class(m, "req-edit"), content, flags=re.IGNORECASE)
    
    # 3. Edit buttons (excluding textareas/inputs with edit)
    content = re.sub(r'<button[^>]*>.*?Edit.*?</button>', lambda m: add_class(m, "req-edit"), content, flags=re.IGNORECASE)
    
    # 4. Delete buttons (Delete text or trash emojis)
    content = re.sub(r'<button[^>]*>.*?Delete.*?</button>', lambda m: add_class(m, "req-delete"), content, flags=re.IGNORECASE)
    content = re.sub(r'<button[^>]*>.*?🗑️.*?</button>', lambda m: add_class(m, "req-delete"), content, flags=re.IGNORECASE)

    # Action headers / columns might be trickier, but hiding the buttons themselves will prevent clicks.
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

base_dir = "templates"
patch_template(os.path.join(base_dir, "purchase_order.html"), "po_edit", "po_delete")
patch_template(os.path.join(base_dir, "supplier_book.html"), "supplier_edit", "supplier_delete")
patch_template(os.path.join(base_dir, "customer_book.html"), "customer_edit", "customer_delete")
patch_template(os.path.join(base_dir, "forwarder_dashboard.html"), "forwarder_edit", "forwarder_delete")

print("Templates patched.")
