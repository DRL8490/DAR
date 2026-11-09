import os, re, ast, subprocess

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")
with open("_phase2_bathy_routes.py", "r", encoding="utf-8-sig") as f:
    p4 = f.read().lstrip("\ufeff")

# Replace from # --- STEP 4: all the way to EOF so STUDIO_HTML_TEMPLATE is cleanly replaced
mc = re.sub(r"# --- STEP 4:.*", "", mc, flags=re.S).rstrip() + "\n\n" + p4.strip() + "\n"
ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)
print("Successfully updated and AST-verified mti_blueprint.py")

with open("_phase2_bathy_dash.html", "r", encoding="utf-8-sig") as f:
    s5 = f.read().lstrip("\ufeff").strip()

# Inject Step 5 dashboard script ONLY into templates/mti_dashboard.html
t = "templates/mti_dashboard.html"
if os.path.exists(t):
    txt = open(t, "r", encoding="utf-8-sig").read()
    if 'id="mti4PanelStudioUpgrade"' in txt:
        txt = re.sub(r'<script id="mti4PanelStudioUpgrade">.*?</script>', s5, txt, flags=re.S)
    elif '</body>' in txt:
        txt = txt.replace('</body>', s5 + '\n</body>', 1)
    open(t, "w", encoding="utf-8").write(txt)
    print("Updated Phase 2 Bathy Input UI in:", t)

from app import app
rules = sorted([r.rule for r in app.url_map.iter_rules() if "mti" in r.rule])
print("PHASE 2 BATHY UI & ROUTES REGISTERED (" + str(len(rules)) + "):", [r for r in rules if "seabed" in r or "studio" in r or "4panel" in r])
subprocess.run(["py", "sync.py", "feat(mti): add Pre-Survey Bathy Spot Soundings input drawer and fix spot soundings"], check=False)
