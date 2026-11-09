import os, glob, ast, subprocess

with open("_upgraded_reports_dpr.py", "r", encoding="utf-8-sig") as f:
    r_txt = f.read().lstrip("\ufeff")
ast.parse(r_txt)
with open("mti_4panel_reports.py", "w", encoding="utf-8") as f:
    f.write(r_txt)
print("  -> Upgraded mti_4panel_reports.py AST-verified.")

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try: os.remove(p)
    except Exception: pass

sync_py = "python" if os.path.exists(".venv/Scripts/python.exe") else "py"
subprocess.run([sync_py, "sync.py", "feat(mti-dpr): upgrade 00:00-23:59 MTI DPR PDF with crossing matrix, bordered tables, metocean column, and sign-off block"], check=False)
