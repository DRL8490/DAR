import os, re, glob, ast, subprocess

TARGET_FILES = [
    "mti_blueprint.py",
    "mti_4panel_math.py",
    "mti_4panel_a3.py",
    "mti_4panel_reports.py",
    "mti_adhoc.py",
    "app.py",
]
for tf in sorted(glob.glob(os.path.join("templates", "*.html"))):
    if "mti" in os.path.basename(tf).lower() and tf not in TARGET_FILES:
        TARGET_FILES.append(tf)

def patch_gap_tol_content(src):
    out = src

    # 1. Dict keys, subscript assignments, .get/.setdefault, Jinja |default()
    out = re.sub(
        r"""((?:["'](?:side_)?gap_tol(?:erance)?(?:_m)?["']\s*(?::|\]\s*=)\s*)|(?:(?:get|setdefault)\(\s*["'](?:side_)?gap_tol(?:erance)?(?:_m)?["']\s*,\s*)|(?:\b(?:side_)?gap_tol(?:erance)?(?:_m)?\s*\|\s*default\(\s*))0\.20?(?!\d)""",
        r"\g<1>0.50",
        out,
        flags=re.I
    )

    # 2. Variable / constant assignments (e.g. GAP_TOLERANCE_M = 0.20, gap_tol = ... or 0.20)
    out = re.sub(
        r"""(\b(?:default_)?(?:side_)?(?:gap_tol(?:erance)?(?:_m)?|tol_gap(?:_m)?)\b\s*=\s*[^\n#]*?(?:\bor\s+|=)\s*)0\.20?(?!\d)""",
        r"\g<1>0.50",
        out,
        flags=re.I
    )
    out = re.sub(
        r"""(\b(?:default_)?(?:side_)?(?:gap_tol(?:erance)?(?:_m)?|tol_gap(?:_m)?)\b\s*=\s*)0\.20?(?!\d)""",
        r"\g<1>0.50",
        out,
        flags=re.I
    )

    # 3. Function signature defaults (e.g. gap_tol=0.20, tol_gap=0.2)
    out = re.sub(
        r"""(\b(?:gap_tol(?:erance)?(?:_m)?|tol_gap(?:_m)?)\s*=\s*)0\.20?(?=\s*[,)])""",
        r"\g<1>0.50",
        out,
        flags=re.I
    )

    # 4. Direct comparisons of gap fields/variables against 0.2 or 0.20
    out = re.sub(
        r"""(\b(?:gap|gap_m|gap1_m|gap2_m|max_gap|max_gap_m|max_g|gap_nw|gap_ne|gap_se|gap_sw|side_gap|inter_gap|gap_val|gap_limit)\b[^\n#:]{0,45}?(?:<=|>=|<|>)\s*)0\.20?(?!\d)""",
        r"\g<1>0.50",
        out,
        flags=re.I
    )

    # 5. UI / Badge / Card / Tooltip text labels mentioning 0.20m or 0.2m with Gap
    out = re.sub(
        "((?:\u2264|&le;|&#8804;|<=|<)\\s*)0\\.20?(\\s*m\\b[^<\\n]{0,30}?\\bGap\\b)",
        r"\g<1>0.50\g<2>",
        out,
        flags=re.I
    )
    out = re.sub(
        "(\\b(?:Side[- ]to[- ]Side\\s+Gap|Side\\s+Gap|Inter[- ]Mattress\\s+Gap|Corner\\s+Gaps?|Gap\\s+Tol(?:erance)?|Gap\\s+Checks?)\\b[^\\n<]{0,35}?(?:\u2264|&le;|&#8804;|<=|<|:|=)\\s*)0\\.20?(?=\\s*m\\b)",
        r"\g<1>0.50",
        out,
        flags=re.I
    )

    # 6. HTML form inputs/placeholders for gap tolerance
    out = re.sub(
        r"""(name=["']gap_tolerance_m["'][^>]*?value=["'])0\.20?(?=["'])""",
        r"\g<1>0.50",
        out,
        flags=re.I
    )
    out = re.sub(
        "(gap[^\\n>]{0,60}?(?:<=|&le;|\u2264|<|Tol[:\\s]*)\\s*)0\\.20?(?=\\s*m\\b)",
        r"\g<1>0.50",
        out,
        flags=re.I
    )

    return out

print("=== [1/4] Updating Side Gap Tolerance (0.20m -> 0.50m) Across Code & Templates ===")
for fp in TARGET_FILES:
    if not os.path.exists(fp):
        continue
    raw = open(fp, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    updated = patch_gap_tol_content(raw)
    if updated != raw:
        if fp.endswith(".py"):
            ast.parse(updated)
        open(fp, "w", encoding="utf-8").write(updated)
        diff_cnt = sum(1 for a, b in zip(raw.splitlines(), updated.splitlines()) if a != b)
        print(f"  -> Updated {fp} ({diff_cnt} line(s) updated to 0.50m)")
    else:
        print(f"  -> Checked {fp} (already 0.50m)")

print("=== [2/4] Injecting Automatic DB State Migration (0.20m -> 0.50m) in mti_blueprint.py ===")
bp_path = "mti_blueprint.py"
if os.path.exists(bp_path):
    bp_txt = open(bp_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    bp_txt = re.sub(
        r"\n?# --- MTI_GAP_TOL_050_MIGRATION_START ---.*?# --- MTI_GAP_TOL_050_MIGRATION_END ---\n?",
        "\n",
        bp_txt,
        flags=re.S
    )

    migration_block = """
# --- MTI_GAP_TOL_050_MIGRATION_START ---
_orig_load_mti_state_gaptol050 = load_mti_state
_in_gaptol050_save_guard = False

def load_mti_state(*args, **kwargs):
    global _in_gaptol050_save_guard
    st = _orig_load_mti_state_gaptol050(*args, **kwargs)
    if isinstance(st, dict) and not st.get("gap_tol_050_migrated"):
        st["gap_tolerance_m"] = 0.50
        if isinstance(st.get("survey_setup"), dict) and "gap_tolerance_m" in st["survey_setup"]:
            st["survey_setup"]["gap_tolerance_m"] = 0.50
        st["gap_tol_050_migrated"] = True
        if not _in_gaptol050_save_guard and "save_mti_state" in globals():
            try:
                _in_gaptol050_save_guard = True
                save_mti_state(st)
            except Exception:
                pass
            finally:
                _in_gaptol050_save_guard = False
    return st
# --- MTI_GAP_TOL_050_MIGRATION_END ---
"""

    m_route = re.search(r"^@mti_bp\.route", bp_txt, flags=re.M)
    if m_route:
        idx = m_route.start()
        bp_txt = bp_txt[:idx] + migration_block.lstrip() + "\n" + bp_txt[idx:]
    else:
        bp_txt = bp_txt.rstrip() + "\n\n" + migration_block.strip() + "\n"

    ast.parse(bp_txt)
    open(bp_path, "w", encoding="utf-8").write(bp_txt)
    print("  -> Added automatic DB state migration hook in mti_blueprint.py (AST OK).")

print("=== [3/4] Migrating Local MTI State & Verifying Active Gap Tolerance ===")
try:
    from app import app
    import mti_blueprint as mb
    with app.app_context():
        st_now = mb.load_mti_state()
        st_now["gap_tolerance_m"] = 0.50
        st_now["gap_tol_050_migrated"] = True
        mb.save_mti_state(st_now)
        print(f"  -> Local DB state updated: cl_tolerance_m={st_now.get('cl_tolerance_m')}, gap_tolerance_m={st_now.get('gap_tolerance_m')}")
except Exception as exc:
    print("  -> Local DB note (will auto-migrate on app startup):", exc)

print("=== [4/4] Syncing Side Gap Tolerance (0.50m) Update to GitHub & Render ===")
sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti): update side-to-side gap tolerance from 0.20m to 0.50m across code, UI, and live state"], check=False)
else:
    print("  -> Updated locally (sync.py not found).")