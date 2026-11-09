import os, re, ast, subprocess

# 1. Update mti_4panel_math.py so CR-A3_M18 and any crossing's 1st unit auto-resolves its layer and is_first status
if os.path.exists("mti_4panel_math.py"):
    m_txt = open("mti_4panel_math.py", "r", encoding="utf-8-sig").read()
    m_txt = m_txt.replace(
        'layer_boxes = [b for b in cats if str(b.get("layer", "")) == str(crossing_id)] or cats',
        't_hit = next((b for b in cats if str(b.get("name") or b.get("design_box_id")) == str(target_box_id)), None)\n    if t_hit and t_hit.get("layer"): crossing_id = str(t_hit["layer"])\n    layer_boxes = [b for b in cats if str(b.get("layer", "")) == str(crossing_id)] or cats'
    ).replace(
        'is_first = bool(fix_data.get("is_first_in_array")) or (unit_no == 1) or (str(loc_id).endswith("_M15") and str(mat_id).replace("#", "") == "A046")',
        'is_first = bool(fix_data.get("is_first_in_array")) or (unit_no == 1) or ("1st unit" in str(fix_data.get("gap_labels", "")).lower()) or (str(loc_id).endswith("_M15") and str(mat_id).replace("#", "") == "A046")'
    )
    ast.parse(m_txt)
    open("mti_4panel_math.py", "w", encoding="utf-8").write(m_txt)
    print("Updated mti_4panel_math.py for multi-crossing & 1st-unit detection.")

# 2. Cleanly update mti_blueprint.py (strip any old STEP 4 or stray <script id="mti4PanelStudioUpgrade"> blocks)
with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")
with open("_phase2_bathy_routes.py", "r", encoding="utf-8-sig") as f:
    p4 = f.read().lstrip("\ufeff")

mc = re.sub(r"# --- STEP 4:.*", "", mc, flags=re.S)
mc = re.sub(r'<script id="mti4PanelStudioUpgrade">.*?</script>', "", mc, flags=re.S)
mc = mc.rstrip() + "\n\n" + p4.strip() + "\n"
ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)
print("Successfully updated and AST-verified mti_blueprint.py")

# 3. Cleanly update templates/mti_dashboard.html:
#    - Remove "139 CAD Design Mattresses - Tolerances: Centerline Offset <= +/-0.50 m | Inter-Mattress Gap <= 0.20 m"
#    - Inject resilient 4-Panel Studio buttons (Top Bar + Ledger Rows + Mattress Fix Form)
with open("_phase2_bathy_dash.html", "r", encoding="utf-8-sig") as f:
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
    print("Removed top bar subtitle and injected 4-Panel buttons in:", t)

from app import app
rules = sorted([r.rule for r in app.url_map.iter_rules() if "mti" in r.rule])
print("REGISTERED MTI ROUTES (" + str(len(rules)) + "):", [r for r in rules if "seabed" in r or "studio" in r or "4panel" in r])
subprocess.run(["py", "sync.py", "fix(mti): remove top bar tolerance subtitle and restore 4-Panel Studio buttons on MTI dashboard"], check=False)
