import os
import ast
import subprocess

# 1. Register mti_bp inside app.py
if os.path.exists("app.py"):
    with open("app.py", "r", encoding="utf-8") as f:
        app_code = f.read()
    if "register_blueprint(mti_bp)" not in app_code:
        mti_hook = """
# --- MTI MATTRESS INSTALLATION MODULE BLUEPRINT ---
try:
    from mti_blueprint import mti_bp
    app.register_blueprint(mti_bp)
except Exception as _mti_err:
    print(f"MTI Blueprint Notice: {_mti_err}")
"""
        if "if __name__ ==" in app_code:
            idx = app_code.rfind("if __name__ ==")
            app_code = app_code[:idx] + mti_hook + "\n" + app_code[idx:]
        else:
            app_code += "\n" + mti_hook
        ast.parse(app_code)
        with open("app.py", "w", encoding="utf-8") as f:
            f.write(app_code)
        print("1. Registered mti_bp in app.py (/mti is now active).")

# 2. Add "🧱 MTI Mattress Tracker" button to Admin Toolkit bar in templates/admin_dashboard.html
adm_path = "templates/admin_dashboard.html" if os.path.exists("templates/admin_dashboard.html") else "admin_dashboard.html"
if os.path.exists(adm_path):
    with open(adm_path, "r", encoding="utf-8") as f:
        adm_html = f.read()
    if 'href="/mti"' not in adm_html and '<a href="/reports" class="cmd-btn">' in adm_html:
        adm_html = adm_html.replace(
            '<a href="/reports" class="cmd-btn">📊 Reports Generator</a>',
            '<a href="/reports" class="cmd-btn">📊 Reports Generator</a>\n        <a href="/mti" class="cmd-btn" style="border-color: #20c997; color: #20c997;">🧱 MTI Mattress Tracker</a>',
            1
        )
        with open(adm_path, "w", encoding="utf-8") as f:
            f.write(adm_html)
        print("2. Added MTI Mattress Tracker button to Admin Dashboard toolkit bar.")

# 3. Add "🧱 MTI Mattress Tracker" button to templates/reports.html header
rep_path = "templates/reports.html" if os.path.exists("templates/reports.html") else "reports.html"
if os.path.exists(rep_path):
    with open(rep_path, "r", encoding="utf-8") as f:
        rep_html = f.read()
    if 'href="/mti"' not in rep_html and '<div class="d-flex gap-2">' in rep_html:
        rep_html = rep_html.replace(
            '<div class="d-flex gap-2">',
            '<div class="d-flex gap-2">\n            <a href="/mti" class="btn btn-primary fw-bold">🧱 MTI Mattress Tracker</a>',
            1
        )
        with open(rep_path, "w", encoding="utf-8") as f:
            f.write(rep_html)
        print("3. Added MTI Mattress Tracker button to Reports page header.")

# 4. Commit and push to GitHub -> Render
email_res = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True)
author_email = email_res.stdout.strip() or "DRL8490@users.noreply.github.com"

subprocess.run(["git", "add", "-A"], check=False)
subprocess.run([
    "git", "commit",
    f"--author=DRL8490 <{author_email}>",
    "-m", "feat: install MTI Subsea Mattress Installation Tracker blueprint (/mti) and nav buttons"
], check=False)
print("4. Pushing MTI Module to GitHub...")
subprocess.run(["git", "push", "origin", "main"], check=False)
