import os, re, glob, ast, subprocess

# 1. Clear any old cached PDFs in workspace/ so fresh bathy soundings always render on PDF
os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try: os.remove(p)
    except Exception: pass

# 2. Update mti_blueprint.py with the new Location-by-Location CAD & Bathy Tables on /mti/setup
with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")
with open("_phase2_overhaul_routes.py", "r", encoding="utf-8-sig") as f:
    p4 = f.read().lstrip("\ufeff")

mc = re.sub(r"# --- STEP 4:.*", "", mc, flags=re.S)
mc = re.sub(r'<script id="mti4PanelStudioUpgrade">.*?</script>', "", mc, flags=re.S)
mc = mc.rstrip() + "\n\n" + p4.strip() + "\n"

ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)

from app import app
rules = sorted([r.rule for r in app.url_map.iter_rules() if "mti" in r.rule])
print("PHASE 2 OVERHAUL COMPLETE! Registered MTI Routes (" + str(len(rules)) + "):")
for r in rules:
    if any(k in r for k in ("setup", "studio", "cad", "design", "seabed", "4panel")):
        print("  ->", r)

subprocess.run(["py", "sync.py", "feat(mti-setup): overhaul CAD and Bathy setup into Location-vs-File tables and purge fallback PDF cache"], check=False)
