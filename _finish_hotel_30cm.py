import os, glob, ast, subprocess

print("=== [1/3] Stripping UTF-8 BOM (U+FEFF) & Verifying mti_4panel_math.py / mti_4panel_a3.py ===")
for fn in ("mti_4panel_math.py", "mti_4panel_a3.py"):
    if os.path.exists(fn):
        txt = open(fn, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
        if fn == "mti_4panel_math.py":
            txt = txt.replace("else 0.15)", "else 0.30)").replace("mat_thick = 0.15", "mat_thick = 0.30")
        ast.parse(txt)
        open(fn, "w", encoding="utf-8").write(txt)
        print(f"  -> Cleaned BOM & AST-verified: {fn}")

print("=== [2/3] Adding 0.30 m Thickness Input to /mti/studio in mti_blueprint.py ===")
if os.path.exists("mti_blueprint.py"):
    b_txt = open("mti_blueprint.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    old_ctrl = '<div class="col-md-1 col-6">\n        <label class="small fw-bold text-light">Mattress ID</label>\n        <input type="text" id="inpTagId" class="form-control form-control-sm fw-bold" value="{{ init_tag }}">\n      </div>'
    new_ctrl = (
        '<div class="col-md-1 col-6">\n        <label class="small fw-bold text-light">Mattress ID</label>\n        <input type="text" id="inpTagId" class="form-control form-control-sm fw-bold" value="{{ init_tag }}">\n      </div>\n'
        '      <div class="col-md-1 col-6">\n        <label class="small fw-bold text-warning" title="Concrete Mattress Thickness (30 cm = 0.30 m)">Thick (m)</label>\n        <input type="number" step="0.01" id="inpMatThick" class="form-control form-control-sm fw-bold bg-dark text-warning border-warning" value="0.30">\n      </div>'
    )
    if 'id="inpMatThick"' not in b_txt and old_ctrl in b_txt:
        b_txt = b_txt.replace(old_ctrl, new_ctrl, 1)
        b_txt = b_txt.replace('<div class="col-md-3 col-12">\n        <label class="small fw-bold text-info">1-Click Installed Ledger Mattress Switcher</label>', '<div class="col-md-2 col-12">\n        <label class="small fw-bold text-info">Ledger Switcher</label>', 1)
        b_txt = b_txt.replace("payload.physical_tag = document.getElementById('inpTagId').value.trim();", "payload.physical_tag = document.getElementById('inpTagId').value.trim();\n  if (document.getElementById('inpMatThick')) payload.mat_thickness_m = document.getElementById('inpMatThick').value;")
    elif 'id="inpMatThick"' in b_txt:
        b_txt = b_txt.replace('value="0.15"', 'value="0.30"')
    ast.parse(b_txt)
    open("mti_blueprint.py", "w", encoding="utf-8").write(b_txt)
    print("  -> Cleaned BOM & AST-verified: mti_blueprint.py (Thick = 0.30 m)")

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try: os.remove(p)
    except Exception: pass

print("=== [3/3] Pushing 0.30 m (30 cm) Mattress Thickness Update to GitHub & Render ===")
sync_py = "python" if os.path.exists(".venv/Scripts/python.exe") else "py"
subprocess.run([sync_py, "sync.py", "fix(mti): set concrete mattress thickness to 0.30m (30cm) and center Panels 3 & 4 Z-axes"], check=False)
