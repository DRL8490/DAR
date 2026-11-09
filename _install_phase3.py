import os, re, ast, subprocess

with open("_phase3_dash.html", "r", encoding="utf-8-sig") as f:
    s5 = f.read().lstrip("\ufeff").strip()

t = "templates/mti_dashboard.html"
if os.path.exists(t):
    raw_html = open(t, "r", encoding="utf-8-sig").read()
    raw_html = re.sub(r'<!-- STEP 3: 4-PANEL SUBSEA MATTRESS VERIFICATION.*?</script>', '', raw_html, flags=re.S)
    raw_html = re.sub(r'<script id="mti4PanelStudioUpgrade">.*?</script>', '', raw_html, flags=re.S)

    cleaned_lines = []
    for ln in raw_html.splitlines():
        if "CAD Design Mattresses" in ln or ("Centerline Offset" in ln and "Inter-Mattress Gap" in ln):
            continue
        cleaned_lines.append(ln)
    txt = "\n".join(cleaned_lines)
    txt = txt.replace("0.20m Gap Checks", "0.50m Gap Checks")

    if "</body>" in txt:
        txt = txt.replace("</body>", s5 + "\n</body>", 1)
    elif "{% endblock %}" in txt:
        idx = txt.rfind("{% endblock %}")
        txt = txt[:idx] + s5 + "\n" + txt[idx:]
    else:
        txt = txt.rstrip() + "\n" + s5 + "\n"

    open(t, "w", encoding="utf-8").write(txt)
    print("PHASE 3 OK! Updated:", t)

ast.parse(open("mti_blueprint.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff"))
from app import app
rules = sorted([r.rule for r in app.url_map.iter_rules() if "mti" in r.rule])
print("TOTAL REGISTERED MTI ROUTES (" + str(len(rules)) + "):", rules)

subprocess.run(["py", "sync.py", "feat(mti): add /mti/setup route for CAD/Design/Bathy input, clean /mti/studio UI, and restore 4-Panel buttons"], check=False)
