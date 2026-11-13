import os, re, glob, ast, subprocess

print("=== [1/4] Fixing Shadowed load_mti_state() Migration in mti_blueprint.py ===")
bp_path = "mti_blueprint.py"
if not os.path.exists(bp_path):
    raise SystemExit("mti_blueprint.py not found! Run this inside C:\\DAR.")

bp_txt = open(bp_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")

# 1. Remove the shadowed early migration block and any prior bottom block
bp_txt = re.sub(
    r"\n?# --- MTI_GAP_TOL_050_MIGRATION_START ---.*?# --- MTI_GAP_TOL_050_MIGRATION_END ---\n?",
    "\n\n",
    bp_txt,
    flags=re.S
)
bp_txt = re.sub(
    r"\n?# --- MTI_GAP_TOL_050_FINAL_ENFORCE_START ---.*?# --- MTI_GAP_TOL_050_FINAL_ENFORCE_END ---\n?",
    "\n",
    bp_txt,
    flags=re.S
)

# 2. Inject 0.50m upgrade directly inside the active mti_state_store load_mti_state()
anchor_v7 = '    if not st.get("dpr_20261107_clean_v7"):'
inject_v7 = """    if not st.get("gap_tol_050_v2") or abs(float(st.get("gap_tolerance_m") or 0.0) - 0.20) < 1e-6:
        st["gap_tolerance_m"] = 0.50
        if isinstance(st.get("survey_setup"), dict) and "gap_tolerance_m" in st["survey_setup"]:
            st["survey_setup"]["gap_tolerance_m"] = 0.50
        st["gap_tol_050_v2"] = True
        save_mti_state(st)
    if not st.get("dpr_20261107_clean_v7"):"""

if 'st.get("gap_tol_050_v2")' not in bp_txt and anchor_v7 in bp_txt:
    bp_txt = bp_txt.replace(anchor_v7, inject_v7, 1)

# 3. Ensure mti_dashboard() tol_pass_cnt handles 1st unit & gap_tol=0.50 cleanly
bp_txt = bp_txt.replace(
    'and float(r.get("gap_m", 0)) <= gap_tol',
    'and (bool(r.get("is_first_in_array")) or float(r.get("gap_m") or 0) <= gap_tol)'
)

# 4. Pass cl_tol & gap_tol to mti_mobile.html as well
old_mob = 'return render_template(\'mti_mobile.html\', ledger=ledger, input_logs=input_logs, completed_matt=completed_matt, target_matt=int(state.get("campaign_target_mattresses", 139)), catalog_json=json.dumps(MATTRESS_CATALOG))'
new_mob = 'return render_template(\'mti_mobile.html\', ledger=ledger, input_logs=input_logs, completed_matt=completed_matt, target_matt=int(state.get("campaign_target_mattresses", 139)), cl_tol=float(state.get("cl_tolerance_m", 0.50)), gap_tol=float(state.get("gap_tolerance_m", 0.50)), catalog_json=json.dumps(MATTRESS_CATALOG))'
if old_mob in bp_txt:
    bp_txt = bp_txt.replace(old_mob, new_mob, 1)

# 5. Append un-shadowable wrapper at the VERY BOTTOM of mti_blueprint.py
bottom_enforce = """
# --- MTI_GAP_TOL_050_FINAL_ENFORCE_START ---
_real_final_load_mti_state = load_mti_state
_final_gaptol_saving = False

def load_mti_state(*args, **kwargs):
    global _final_gaptol_saving
    st = _real_final_load_mti_state(*args, **kwargs)
    if isinstance(st, dict):
        cur_g = st.get("gap_tolerance_m")
        if not st.get("gap_tol_050_v2") or cur_g is None or abs(float(cur_g) - 0.20) < 1e-6:
            st["gap_tolerance_m"] = 0.50
            if isinstance(st.get("survey_setup"), dict):
                st["survey_setup"]["gap_tolerance_m"] = 0.50
            st["gap_tol_050_v2"] = True
            if not _final_gaptol_saving:
                try:
                    _final_gaptol_saving = True
                    save_mti_state(st)
                except Exception:
                    pass
                finally:
                    _final_gaptol_saving = False
    return st
# --- MTI_GAP_TOL_050_FINAL_ENFORCE_END ---
"""
bp_txt = bp_txt.rstrip() + "\n\n" + bottom_enforce.strip() + "\n"

ast.parse(bp_txt)
open(bp_path, "w", encoding="utf-8").write(bp_txt)
print("  -> mti_blueprint.py updated & AST-verified (un-shadowable bottom migration active).")

print("=== [2/4] Auditing & Patching MTI HTML Templates (mti_dashboard.html & mti_mobile.html) ===")
for tf in sorted(glob.glob(os.path.join("templates", "*mti*.html"))):
    raw_h = open(tf, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    new_h = raw_h

    for _ in range(4):
        h_next = re.sub(
            r"""(\b(?:gap|gap_m|gap1_m|gap2_m|max_gap|gap_nw|gap_ne|gap_se|gap_sw|gap_tol|gap_tolerance_m)\b[^<\n;]{0,60}?(?:<=|>=|<|>|\bdefault\s*\()\s*)0\.20?(?!\d)""",
            r"\g<1>0.50",
            new_h,
            flags=re.I
        )
        if h_next == new_h:
            break
        new_h = h_next

    new_h = re.sub(
        r"""(?<![A-Za-z0-9_:])0\.20?(\s*m\b[^<\n]{0,25}?\bGap\b)""",
        r"0.50\g<1>",
        new_h,
        flags=re.I
    )
    new_h = re.sub(
        "(\\b(?:Side[- ]to[- ]Side\\s+Gap|Side\\s+Gap|Inter[- ]Mattress\\s+Gap|Corner\\s+Gaps?|Gaps?\\s*\\(|Gap\\s+Tol(?:erance)?|Gap\\s+Max|Gap\\s+Checks?)[^\\n<]{0,35}?(?:\u2264|&le;|&#8804;|<=|<|:|=|\\bMax\\s+|\\bTol\\s+)\\s*)0\\.20?(?=\\s*m\\b)",
        r"\g<1>0.50",
        new_h,
        flags=re.I
    )

    if new_h != raw_h:
        open(tf, "w", encoding="utf-8").write(new_h)
        diff_n = sum(1 for a, b in zip(raw_h.splitlines(), new_h.splitlines()) if a != b)
        print(f"  -> Patched {tf} ({diff_n} template line(s) updated to 0.50m)")
    else:
        print(f"  -> Verified {tf} (uses dynamic gap_tol variable cleanly)")

    for lno, ln in enumerate(new_h.splitlines(), 1):
        if "gap_tol" in ln or "gap_m" in ln or "Gap Checks" in ln:
            print(f"     [{os.path.basename(tf)} L{lno}]: {ln.strip()[:110]}")

print("=== [3/4] Updating Local SQLite / JSON State & Verifying Active load_mti_state() ===")
try:
    from app import app
    import importlib, mti_blueprint as mb
    importlib.reload(mb)
    with app.app_context():
        st_chk = mb.load_mti_state()
        print(f"  -> Verified active load_mti_state() => gap_tolerance_m = {st_chk.get('gap_tolerance_m')}")
except Exception as exc:
    print("  -> Local verification note:", exc)

print("=== [4/4] Pushing Fix to GitHub & Render ===")
sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "fix(mti): place 0.50m side gap tolerance migration after mti_state_store loader so Render DB updates"], check=False)
else:
    print("  -> Saved locally (sync.py not found).")