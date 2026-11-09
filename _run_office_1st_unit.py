import os, ast, subprocess
from app import app
import mti_4panel_math as m
import mti_4panel_a3 as a3
import mti_4panel_reports as rep
from mti_blueprint import load_mti_state, MATTRESS_CATALOG

if os.path.exists("mti_4panel_reports.py"):
    r_txt = open("mti_4panel_reports.py", "r", encoding="utf-8-sig").read()
    r_txt = r_txt.replace("if include_history and ledger_list:", "if include_history and ledger_list and not is_first:")
    ast.parse(r_txt)
    open("mti_4panel_reports.py", "w", encoding="utf-8").write(r_txt)

with app.app_context():
    st = load_mti_state()
    ledger = st.get("ledger", [])
    cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    unit1 = next((r for r in ledger if str(r.get("design_box_id")) == "CR-A1_M15"), ledger[0] if ledger else {"design_box_id": "CR-A1_M15", "physical_tag": "#A046", "install_date": "2026-11-04 14:34", "is_first_in_array": True})
    b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full = m.run_rov_4panel_verification(unit1, cat_list, "workspace")
    a3.generate_a3_4panel_chart(b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full, "workspace", include_history=True, ledger_list=ledger, save_pdf=True)
    md_txt = rep.build_structured_report_markdown(metrics, False, ledger)
    rep.generate_a4_report_pdf(metrics, "workspace", md_txt)
    rep.generate_editable_docx(metrics, md_txt, "workspace")
    print("=== [2/3] Regenerated 1st Unit Report:", metrics["base_filename"] + ".pdf ===")

print("=== [3/3] Pushing Updated 1st-Unit 4-Panel Code to GitHub & Render ===")
subprocess.run(["py", "sync.py", "fix(mti): refine 1st-unit 4-panel chart (no P1 history or M8 highlight, P2 overhang-only, full top bar text)"], check=False)
