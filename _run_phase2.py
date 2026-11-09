import os, ast, subprocess
from app import app
import mti_4panel_math as m
import mti_4panel_a3 as a3
import mti_4panel_reports as rep
from mti_blueprint import load_mti_state, save_mti_state, MATTRESS_CATALOG

with app.app_context():
    st = load_mti_state()
    ledger = st.get("ledger", [])
    for r in ledger:
        if str(r.get("design_box_id")) == "CR-A1_M16" or str(r.get("physical_tag")) == "#A007":
            if not r.get("gap_nw") and not r.get("gap_sw"):
                r["gap_nw"] = "0.02"
                r["gap_sw"] = "0.10"
            r["gap_labels"] = "NW:0.02m | SW:0.10m"
            if abs(float(r.get("aslaid_z") or 0.0)) < 1.0:
                r["aslaid_z"] = -18.35
                for ci in (1, 2, 3, 4):
                    r[f"c{ci}_z"] = -18.35
    save_mti_state(st)

    cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    for uno_target, def_box, def_tag, def_dt, is_1st in [
        (1, "CR-A1_M15", "#A046", "2026-11-04 14:34", True),
        (2, "CR-A1_M16", "#A007", "2026-11-05 04:20", False),
    ]:
        row = next((r for r in ledger if str(r.get("design_box_id")) == def_box), {"unit_no": uno_target, "design_box_id": def_box, "physical_tag": def_tag, "install_date": def_dt, "is_first_in_array": is_1st, "gap_nw": "" if is_1st else "0.02", "gap_sw": "" if is_1st else "0.10"})
        b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full = m.run_rov_4panel_verification(row, cat_list, "workspace")
        a3.generate_a3_4panel_chart(b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full, "workspace", include_history=True, ledger_list=ledger, save_pdf=True)
        md_txt = rep.build_structured_report_markdown(metrics, include_history=True, ledger_list=ledger)
        rep.generate_a4_report_pdf(metrics, "workspace", md_txt)
        rep.generate_editable_docx(metrics, md_txt, "workspace")
        print(f"PHASE 2 REGENERATED UNIT #{uno_target}: workspace\\{metrics['base_filename']}.pdf | Verdict: {metrics['verdict']}")

subprocess.run(["py", "sync.py", "feat(mti): Phase 2 succeeding-unit 4-panel chart (P1 dashed history & green hatch current, P2 surveyor corner gaps <=0.50m, no nudge)"], check=False)
