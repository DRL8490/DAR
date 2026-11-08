import os, sys, re, ast, subprocess

# 1. Fix missing `import os` at top of mti_blueprint.py
with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")

TOP_IMPORTS = "import os, sys, io, re, math, json, zlib, base64\nfrom datetime import datetime\n"
if not mc.startswith("import os, sys, io, re, math, json"):
    mc = TOP_IMPORTS + mc

ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)

# 2. Inject Step 3 4-Panel Studio UI into templates/mti_dashboard.html and mti_blueprint.py
with open("_step3_studio.html", "r", encoding="utf-8-sig") as f:
    studio_snippet = f.read().lstrip("\ufeff").strip()

for target in ["templates/mti_dashboard.html", "mti_blueprint.py"]:
    if not os.path.exists(target):
        continue
    with open(target, "r", encoding="utf-8-sig") as f:
        txt = f.read()

    if 'id="mti4PanelStudioUpgrade"' in txt:
        txt = re.sub(r'<!-- STEP 3: 4-PANEL SUBSEA MATTRESS VERIFICATION.*?<script id="mti4PanelStudioUpgrade">.*?</script>', studio_snippet, txt, flags=re.S)
        txt = re.sub(r'<script id="mti4PanelStudioUpgrade">.*?</script>', studio_snippet, txt, flags=re.S)
    elif '</body>' in txt:
        txt = txt.replace('</body>', studio_snippet + '\n</body>', 1)

    if target.endswith(".py"):
        ast.parse(txt)

    with open(target, "w", encoding="utf-8") as f:
        f.write(txt)
    print("Updated Step 3 4-Panel Studio UI in:", target)

# 3. Direct import check (unmasked) + verify all MTI routes are registered in app.py
import mti_blueprint
from app import app
rules = sorted([r.rule for r in app.url_map.iter_rules() if "mti" in r.rule])
print("REGISTERED MTI ROUTES (" + str(len(rules)) + "):")
for r in rules:
    print("  ", r)

assert "/mti/verify_4panel" in rules, "ERROR: /mti/verify_4panel did not register!"
print("ALL STEP 1, STEP 2, AND STEP 3 CHECKS PASSED!")

# 4. Sync & Push to GitHub / Render
subprocess.run(["py", "sync.py", "fix: add missing import os to mti_blueprint and complete 4-Panel Studio integration"], check=False)
