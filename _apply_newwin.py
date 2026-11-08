import os, re, ast, subprocess

with open("mti_4panel_math.py", "r", encoding="utf-8-sig") as f:
    m_txt = f.read()
m_txt = m_txt.replace(
    "ee, nn = np.meshgrid(np.arange(e_min, e_max + 1.0, 1.0), np.arange(n_min, n_max + 1.0, 1.0))",
    "ee, nn = np.meshgrid(np.arange(e_min, e_max + 2.5, 2.5), np.arange(n_min, n_max + 2.5, 2.5))"
)
ast.parse(m_txt)
with open("mti_4panel_math.py", "w", encoding="utf-8") as f:
    f.write(m_txt)

with open("_fast_a3.py", "r", encoding="utf-8-sig") as f:
    a3_txt = f.read().lstrip("\ufeff")
ast.parse(a3_txt)
with open("mti_4panel_a3.py", "w", encoding="utf-8") as f:
    f.write(a3_txt)

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")
with open("_step4_studio_win.py", "r", encoding="utf-8-sig") as f:
    p4 = f.read().lstrip("\ufeff")

mc = re.sub(r"# --- STEP 4:.*?(?=<script|\Z)", "", mc, flags=re.S).rstrip() + "\n\n" + p4.strip() + "\n"
ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)

with open("_step5_newwin.html", "r", encoding="utf-8-sig") as f:
    s5 = f.read().lstrip("\ufeff").strip()

for t in ("templates/mti_dashboard.html", "mti_blueprint.py"):
    if not os.path.exists(t):
        continue
    txt = open(t, "r", encoding="utf-8-sig").read()
    if 'id="mti4PanelStudioUpgrade"' in txt:
        txt = re.sub(r'<script id="mti4PanelStudioUpgrade">.*?</script>', s5, txt, flags=re.S)
    elif '</body>' in txt:
        txt = txt.replace('</body>', s5 + '\n</body>', 1)
    if t.endswith(".py"):
        ast.parse(txt)
    open(t, "w", encoding="utf-8").write(txt)
    print("Updated New-Window 4-Panel Studio in:", t)

from app import app
rules = sorted([r.rule for r in app.url_map.iter_rules() if "mti" in r.rule])
print("REGISTERED MTI ROUTES (" + str(len(rules)) + "):", [r for r in rules if "studio" in r or "4panel" in r])
subprocess.run(["python", "sync.py", "perf(mti): open 4-Panel Studio in dedicated new window (/mti/studio) and speed up IDW 10x"], check=False)
