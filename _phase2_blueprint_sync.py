import os, re, glob, ast, subprocess
from mti_4panel_math import resolve_full_surveyor_name

# === 1. UPDATE mti_adhoc.py (Full Surveyor Name + _(SurveyorName) on Ad-Hoc PDF & DXF) ===
adhoc_path = "mti_adhoc.py"
if os.path.exists(adhoc_path):
    a_src = open(adhoc_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    if "resolve_full_surveyor_name" not in a_src:
        a_src = a_src.replace(
            "from mti_4panel_math import (",
            "from mti_4panel_math import (\n    resolve_full_surveyor_name,",
            1
        )
    a_src = a_src.replace(
        'safe_fn = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(raw_fn))',
        'safe_fn = re.sub(r"[^A-Za-z0-9_ .()-]", "_", os.path.basename(raw_fn))'
    )
    tag_inject = """    if not re.match(r"^\\d{8}_", safe_fn):
        safe_fn = f"{today_ymd}_{safe_fn}"
    full_surv = resolve_full_surveyor_name(surveyor_name)
    clean_surv = re.sub(r"[^A-Za-z0-9 ._-]", "", str(full_surv or "")).strip()
    if clean_surv and clean_surv.lower() not in ("duty surveyor", "surveyor") and f"({clean_surv})" not in safe_fn:
        stem_fn = safe_fn[:-4] if safe_fn.lower().endswith(".pdf") else safe_fn
        safe_fn = f"{stem_fn}_({clean_surv}).pdf" """
    if "clean_surv =" not in a_src:
        a_src = re.sub(
            r'    if not re\.match\(r"\^\\d\{8\}_", safe_fn\):\n        safe_fn = f"\{today_ymd\}_\{safe_fn\}"',
            lambda _m: tag_inject.rstrip(),
            a_src, count=1
        )
    ast.parse(a_src)
    open(adhoc_path, "w", encoding="utf-8").write(a_src)
    print("  -> Updated mti_adhoc.py (AST OK)")

# === 2. UPDATE mti_blueprint.py (Full Surveyor Name + Safe PDF/DXF Download Resolution) ===
bp_path = "mti_blueprint.py"
bp = open(bp_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")

if "resolve_full_surveyor_name" not in bp:
    bp = bp.replace(
        "from mti_4panel_math import (",
        "from mti_4panel_math import (\n    resolve_full_surveyor_name,",
        1
    )

# Expand surveyor_name to full name in _enrich_fix_row, add_fix, and _resolve_fix_data
bp = bp.replace(
    'd["surveyor_name"] = surv',
    'd["surveyor_name"] = resolve_full_surveyor_name(surv) if "resolve_full_surveyor_name" in globals() else surv'
)
bp = bp.replace(
    'surv_name = (request.form.get("surveyor_name") or ex.get("surveyor_name") or ex.get("surveyor") or cur_usr).strip()',
    'surv_name = resolve_full_surveyor_name((request.form.get("surveyor_name") or ex.get("surveyor_name") or ex.get("surveyor") or cur_usr).strip())'
)
if 'fix_data["surveyor_name"] = resolve_full_surveyor_name(' not in bp:
    bp = bp.replace(
        "    return fix_data\n",
        '    fix_data["surveyor_name"] = resolve_full_surveyor_name(fix_data.get("surveyor_name"))\n    return fix_data\n',
        1
    )

# Allow parentheses & spaces in adhoc PDF/DXF download filenames
bp = bp.replace('r"[^A-Za-z0-9_.-]"', 'r"[^A-Za-z0-9_ .()-]"')

# Keep _dl_4panel_file synced when regenerated metrics include _(SurveyorFullName)
old_dl_ret = "    return send_file(p, as_attachment=True, download_name=base + suffix, mimetype=mime)"
new_dl_ret = """    if not os.path.exists(p) and metrics.get("base_filename"):
        base = str(metrics["base_filename"]).strip()
        p = os.path.join(MTI_WS_DIR, base + suffix)
    return send_file(p, as_attachment=True, download_name=base + suffix, mimetype=mime)"""
if 'if not os.path.exists(p) and metrics.get("base_filename"):' not in bp:
    bp = bp.replace(old_dl_ret, new_dl_ret, 1)

# Upgrade existing DB ledger rows to full surveyor names once on load
upgrade_hook = """        if not st.get("full_surveyor_upgrade_v1"):
            in_logs = st.get("input_logs") or []
            for r in (st.get("ledger") or []):
                raw_s = r.get("surveyor_name") or r.get("surveyor") or ""
                if not raw_s or str(raw_s).strip().lower() in ("duty surveyor", "surveyor"):
                    if "_find_fix_surveyor_from_logs" in globals():
                        raw_s = _find_fix_surveyor_from_logs(r.get("design_box_id"), in_logs, r.get("physical_tag"))
                full_s = resolve_full_surveyor_name(raw_s)
                if full_s and full_s.lower() not in ("duty surveyor", "surveyor"):
                    r["surveyor_name"] = full_s
                    r["surveyor"] = full_s
            st["full_surveyor_upgrade_v1"] = True
            dirty = True"""

if 'st.get("full_surveyor_upgrade_v1")' not in bp:
    if "if dirty and not _final_gaptol_saving:" in bp:
        bp = bp.replace(
            "        if dirty and not _final_gaptol_saving:",
            upgrade_hook + "\n        if dirty and not _final_gaptol_saving:",
            1
        )
    elif 'if not st.get("dpr_20261107_clean_v7"):' in bp:
        fallback_hook = upgrade_hook.replace("        ", "    ").replace("    dirty = True", "    save_mti_state(st)")
        bp = bp.replace('    if not st.get("dpr_20261107_clean_v7"):', fallback_hook + '\n    if not st.get("dpr_20261107_clean_v7"):', 1)

ast.parse(bp)
open(bp_path, "w", encoding="utf-8").write(bp)
print("  -> Updated mti_blueprint.py (AST OK)")

# Purge stale workspace cache so _(SurveyorFullName) PDF & DXF files regenerate cleanly
for f_stale in glob.glob(os.path.join("workspace", "*.pdf")) + glob.glob(os.path.join("workspace", "*.dxf")) + glob.glob(os.path.join("workspace", "*_cache.json")):
    try: os.remove(f_stale)
    except Exception: pass

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti): group-centered P1 for A1/A2/B1/B2, full surveyor names, and (SurveyorName) PDF/DXF exports"], check=False)
print("\nPHASE 2 COMPLETE & PUSHED TO RENDER!")