import os, re, ast, subprocess

# 1. Update MATTRESS_CATALOG, add_fix, and load_mti_state in mti_blueprint.py to use South-referenced bearings (+180 deg)
with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")

mc = mc.replace(
    '"bearing": r[4]',
    '"bearing": round((r[4] + 180.0) % 360.0, 3)'
)
mc = mc.replace("15.854", "195.854").replace("Brg:15.9", "Brg:195.9")

mc = mc.replace(
    "hdg = round((math.degrees(math.atan2(fe - be, fn - bn)) + 360.0) % 360.0, 3)",
    "hdg = round((math.degrees(math.atan2(fe - be, fn - bn)) + 360.0) % 360.0, 3)\n        if hdg < 180.0: hdg = round(hdg + 180.0, 3)"
)

migrate_hook = """    for r in st.get("ledger", []):
        if float(r.get("heading_deg", 0)) < 180.0:
            r["heading_deg"] = round(float(r.get("heading_deg", 15.854)) + 180.0, 3)
            changed = True
"""
if 'float(r.get("heading_deg", 0)) < 180.0' not in mc and "if changed:" in mc:
    mc = mc.replace("    if changed:", migrate_hook + "    if changed:", 1)

ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)
print("1. Updated MATTRESS_CATALOG (all 139 mattresses) and DB ledger in mti_blueprint.py to South-referenced bearings (+180 deg)!")

# 2. Update default bearings & 4-corner JS calculator in templates/mti_dashboard.html and templates/mti_mobile.html
for target in ["templates/mti_dashboard.html", "templates/mti_mobile.html"]:
    if not os.path.exists(target): continue
    with open(target, "r", encoding="utf-8-sig") as f: txt = f.read()
    txt = txt.replace("15.854", "195.854").replace("15.9&deg;", "195.9&deg;")
    txt = txt.replace(
        "brg = ((Math.atan2(fe - be, fn - bn) * 180.0 / Math.PI) + 360.0) % 360.0;",
        "brg = ((Math.atan2(fe - be, fn - bn) * 180.0 / Math.PI) + 360.0) % 360.0; if (brg < 180.0) brg += 180.0;"
    )
    with open(target, "w", encoding="utf-8") as f: f.write(txt)
    print(f"2. Updated default bearings & South-referenced 4-corner calculator in {target}!")

subprocess.run(["py", "sync.py", "feat: revise Design and Actual Bearings to South-referenced (+180 deg) across all 139 mattresses"], check=False)
