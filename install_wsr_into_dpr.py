"""
1-Click VS Code Auto-Installer: Wires WSR V13 Automation Module into your DPR Online App (thpp-survey-app)
Run in VS Code Terminal:
    python install_wsr_into_dpr.py
"""
import os
import re
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def step_1_install_packages():
    print("[1/4] Checking Python packages (docxtpl, python-docx, pypdf, docx2pdf)...")
    pkgs = ["docxtpl", "python-docx", "pypdf"]
    if os.name == "nt":
        pkgs.append("docx2pdf")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet"] + pkgs, check=False)
        print("  -> Packages verified.")
    except Exception as e:
        print(f"  -> Warning installing packages: {e}")

    req_path = os.path.join(BASE_DIR, "requirements.txt")
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            req_txt = f.read()
        added = []
        for p in ["docxtpl", "python-docx", "pypdf"]:
            if p.lower() not in req_txt.lower():
                req_txt = req_txt.rstrip() + f"\n{p}\n"
                added.append(p)
        if added:
            with open(req_path, "w", encoding="utf-8") as f:
                f.write(req_txt)
            print(f"  -> Added {', '.join(added)} to requirements.txt")

def step_2_patch_app_py():
    app_py_path = os.path.join(BASE_DIR, "app.py")
    if not os.path.exists(app_py_path):
        print("[2/4] app.py not found in current folder. (You can still run `python wsr_blueprint.py` standalone!)")
        return

    with open(app_py_path, "r", encoding="utf-8") as f:
        code = f.read()

    if "wsr_bp" in code or "wsr_blueprint" in code:
        print("[2/4] app.py already has wsr_bp registered! Skipping.")
        return

    snippet = "\n# --- WSR V13 AUTOMATION MODULE BLUEPRINT ---\nfrom wsr_blueprint import wsr_bp\napp.register_blueprint(wsr_bp)\n"

    if 'if __name__ ==' in code:
        idx = code.find('if __name__ ==')
        new_code = code[:idx] + snippet + "\n" + code[idx:]
    else:
        new_code = code + "\n" + snippet

    with open(app_py_path, "w", encoding="utf-8") as f:
        f.write(new_code)
    print("[2/4] Successfully registered `wsr_bp` inside app.py! (/wsr is now active)")

def step_3_patch_templates():
    print("[3/4] Adding 'WSR V13 Studio' launch button to DPR templates...")
    templates_dir = os.path.join(BASE_DIR, "templates")
    if not os.path.exists(templates_dir):
        print("  -> No `templates/` folder found; skipping template button injection.")
        return

    wsr_card_html = """
<!-- WSR V13 AUTOMATION STUDIO MODULE CARD -->
<div style="background: linear-gradient(90deg, #0f2c59 0%, #0c4a6e 100%); color: #ffffff; border-radius: 12px; padding: 18px 22px; margin: 16px 0; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; box-shadow: 0 4px 12px rgba(15,44,89,0.18);">
  <div>
    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #7dd3fc; font-weight: 700;">NMDC Project 20012 • 2-Week AI Context + Page-1 Admin Tables</div>
    <div style="font-size: 18px; font-weight: 800; margin-top: 2px;">Weekly Survey Report (WSR V13) Automation Studio</div>
    <div style="font-size: 12px; color: #e2e8f0; margin-top: 2px;">Pull 7-day closed SurveyTasks directly from the DPR database, edit Page-1 Personnel/Leave/Training tables, and generate pagination-locked Word &amp; PDF reports.</div>
  </div>
  <a href="/wsr" style="background-color: #10b981; color: #ffffff; font-weight: 700; padding: 10px 18px; border-radius: 8px; text-decoration: none; font-size: 13px; white-space: nowrap; box-shadow: 0 2px 6px rgba(0,0,0,0.2);">
    🚀 Open WSR V13 Studio →
  </a>
</div>
"""

    for tpl_name in ["reports.html", "admin_dashboard.html", "user_dashboard.html"]:
        tpl_path = os.path.join(templates_dir, tpl_name)
        if not os.path.exists(tpl_path):
            continue
        with open(tpl_path, "r", encoding="utf-8") as f:
            t_html = f.read()
        if "/wsr" in t_html or "WSR V13 AUTOMATION STUDIO" in t_html:
            print(f"  -> {tpl_name} already has a /wsr link.")
            continue
        # Inject right after <body...> or first <div class="container"...>
        m_body = re.search(r"<body[^>]*>", t_html, re.IGNORECASE)
        if m_body:
            insert_pos = m_body.end()
            t_html = t_html[:insert_pos] + "\n" + wsr_card_html + "\n" + t_html[insert_pos:]
            with open(tpl_path, "w", encoding="utf-8") as f:
                f.write(t_html)
            print(f"  -> Added WSR V13 Studio banner to templates/{tpl_name}")

def step_4_summary():
    print("==========================================================================")
    print(" ✅ WSR V13 MODULE INSTALLED INTO DPR ONLINE APP!")
    print(" 1. Start your DPR app in VS Code terminal:  python app.py")
    print(" 2. Open http://127.0.0.1:5000/wsr (or click 'Open WSR V13 Studio' in /reports)")
    print("==========================================================================")

if __name__ == "__main__":
    step_1_install_packages()
    step_2_patch_app_py()
    step_3_patch_templates()
    step_4_summary()
