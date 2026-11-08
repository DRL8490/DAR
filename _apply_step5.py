import os, re, ast, subprocess

with open("_step5_script.html", "r", encoding="utf-8-sig") as f:
    s = f.read().lstrip("\ufeff").strip()

for t in ("templates/mti_dashboard.html", "mti_blueprint.py"):
    if not os.path.exists(t):
        continue
    with open(t, "r", encoding="utf-8-sig") as f:
        txt = f.read()
    if 'id="mti4PanelStudioUpgrade"' in txt:
        txt = re.sub(r'<script id="mti4PanelStudioUpgrade">.*?</script>', s, txt, flags=re.S)
    elif '</body>' in txt:
        txt = txt.replace('</body>', s + '\n</body>', 1)
    if t.endswith(".py"):
        ast.parse(txt)
    with open(t, "w", encoding="utf-8") as f:
        f.write(txt)
    print("Injected Step 5 Studio UI into:", t)

req_p = "requirements.txt"
req = open(req_p, "r", encoding="utf-8-sig").read() if os.path.exists(req_p) else ""
if "matplotlib" not in req.lower():
    with open(req_p, "w", encoding="utf-8") as f:
        f.write(req.rstrip() + "\nmatplotlib\n")

from app import app
rules = sorted([r.rule for r in app.url_map.iter_rules() if "mti" in r.rule])
print("STEP 5 COMPLETE! Total MTI Routes Registered:", len(rules))
subprocess.run(["python", "sync.py", "feat: complete 5-step modular 4-Panel Verification Studio integration"], check=False)
