import os, re, glob, ast, subprocess

print("=== [1/3] Updating templates/mti_dashboard.html (MTI Top Bar Overhaul) ===")
with open("_phase2_topbar_js.html", "r", encoding="utf-8-sig") as f:
    s5 = f.read().lstrip("\ufeff").strip()

t_dash = "templates/mti_dashboard.html"
if os.path.exists(t_dash):
    raw_t = open(t_dash, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    raw_t = re.sub(r'<script id="mti4PanelStudioUpgrade">.*?</script>', '', raw_t, flags=re.S)
    if "</body>" in raw_t:
        raw_t = raw_t.replace("</body>", s5 + "\n</body>", 1)
    elif "{% endblock %}" in raw_t:
        idx = raw_t.rfind("{% endblock %}")
        raw_t = raw_t[:idx] + s5 + "\n" + raw_t[idx:]
    else:
        raw_t = raw_t.rstrip() + "\n" + s5 + "\n"
    open(t_dash, "w", encoding="utf-8").write(raw_t)
    print("  -> templates/mti_dashboard.html updated with new MTI top bar buttons.")

print("=== [2/3] Cleaning 'ISO A4' Label in mti_blueprint.py Studio & Verifying AST ===")
if os.path.exists("mti_blueprint.py"):
    b_txt = open("mti_blueprint.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    b_txt = b_txt.replace("Editable ISO A4 &amp; Word (.docx) Report Studio", "Editable Verification Report &amp; Word (.docx) Studio")
    b_txt = b_txt.replace("Rendering ISO A3 4-Panel Chart...", "Rendering 4-Panel Verification Chart...")
    ast.parse(b_txt)
    open("mti_blueprint.py", "w", encoding="utf-8").write(b_txt)
    print("  -> mti_blueprint.py updated & AST-verified.")

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try: os.remove(p)
    except Exception: pass

print("=== [3/3] Pushing Phase 2 MTI Top Bar Overhaul & PDF DPR to GitHub/Render ===")
sync_py = "python" if os.path.exists(".venv/Scripts/python.exe") else "py"
subprocess.run([sync_py, "sync.py", "feat(mti): remove ISO A4 text, add Create PDF MTI DPR (00:00-23:59), and streamline MTI top bar"], check=False)
