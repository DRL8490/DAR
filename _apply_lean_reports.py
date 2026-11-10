import os, re, glob, ast, subprocess

if not os.path.exists("mti_4panel_reports.py"):
    raise SystemExit("mti_4panel_reports.py not found in current folder.")

src = open("mti_4panel_reports.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")

lean_md_fn = """def build_structured_report_markdown(metrics, include_history=False, ledger_list=None, scale_p1=250, scale_p2=75):
    loc_id, mat_id = metrics.get("location_id", "CR-A1_M15"), metrics.get("mattress_id", "#A046")
    xing_id, usbl_s = metrics.get("crossing_id", "CR-A1_L1"), metrics.get("usbl_sensor", "Survey Pole")
    cl_off, cl_tol = float(metrics.get("cl_offset_m", 0.0)), float(metrics.get("cl_tol", 0.50))
    max_g, g_tol = float(metrics.get("max_gap_m", 0.0)), float(metrics.get("gap_tol", 0.50))
    is_first = bool(metrics.get("is_first_in_array", False))
    cur_uno = int(metrics.get("unit_no") or (1 if is_first else 2))
    c_enz = metrics.get("corners_enz") or [[0,0,0]]*4
    gaps = metrics.get("gaps") or {}
    cl_st = "PASS" if cl_off <= cl_tol else "EXCEEDS TOLERANCE"
    gap_st = "N/A (1st Unit)" if is_first else ("PASS" if max_g <= g_tol else "EXCEEDS TOLERANCE")

    env_parts = []
    if str(metrics.get("env_wind") or "").strip():
        env_parts.append(f"Wind {metrics['env_wind']}")
    if str(metrics.get("env_current") or "").strip():
        env_parts.append(f"Current {metrics['env_current']}")
    env_line = ", ".join(env_parts) if env_parts else "Not recorded"
    raw_rem = str(metrics.get("remarks") or "").strip()

    lines = [
        f"**Verdict:** {metrics.get('verdict', 'VERIFIED')}  --  **Crossing:** {xing_id}  --  **Placement:** {metrics.get('install_date','')}  --  **Surveyor:** {metrics.get('surveyor_name','Duty Surveyor')}",
        "",
        "## 1. GEODETIC & TOLERANCE SUMMARY",
        "| Parameter | Design | QA/QC USBL | As-Laid ROV | Delta / Result |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| Easting E (m, TWD97) | {metrics.get('design_e',0):.3f} | {metrics.get('qaqc_e',0):.3f} | {metrics.get('aslaid_e',0):.3f} | {metrics.get('aslaid_e',0)-metrics.get('design_e',0):+.3f} m |",
        f"| Northing N (m, TWD97) | {metrics.get('design_n',0):.3f} | {metrics.get('qaqc_n',0):.3f} | {metrics.get('aslaid_n',0):.3f} | {metrics.get('aslaid_n',0)-metrics.get('design_n',0):+.3f} m |",
        f"| Depth Z (m, TWVD2001) | Seabed + 0.30 m | - | {metrics.get('aslaid_z',-18.2):.2f} | WROV 4-Corner Mean |",
        f"| South Bearing (deg) | {metrics.get('design_brg',0):.2f} | {metrics.get('qaqc_brg',0):.2f} | {metrics.get('heading_deg',0):.2f} | {metrics.get('brg_diff_deg',0):+.2f} deg |",
        f"| Radial Offset dCL (m) | <= {cl_tol:.2f} m | - | {cl_off:.3f} m | {cl_st} (dAl {metrics.get('d_along_m',0):+.2f}, dCr {metrics.get('d_cross_m',0):+.2f}m) |",
        f"| Side-to-Side Gap (m) | <= {g_tol:.2f} m | - | {metrics.get('gap_labels','N/A')} | {gap_st} |",
        "",
        "## 2. AS-LAID 4-CORNER ROV COORDINATES",
        f"- C1 (NW): E {c_enz[0][0]:.3f}, N {c_enz[0][1]:.3f}, Z {c_enz[0][2]:.2f} m" + ("" if is_first else f"  [Gap NW: {gaps.get('nw') or '-'}]"),
        f"- C2 (NE): E {c_enz[1][0]:.3f}, N {c_enz[1][1]:.3f}, Z {c_enz[1][2]:.2f} m" + ("" if is_first else f"  [Gap NE: {gaps.get('ne') or '-'}]"),
        f"- C3 (SE): E {c_enz[2][0]:.3f}, N {c_enz[2][1]:.3f}, Z {c_enz[2][2]:.2f} m" + ("" if is_first else f"  [Gap SE: {gaps.get('se') or '-'}]"),
        f"- C4 (SW): E {c_enz[3][0]:.3f}, N {c_enz[3][1]:.3f}, Z {c_enz[3][2]:.2f} m" + ("" if is_first else f"  [Gap SW: {gaps.get('sw') or '-'}]"),
        "",
        "## 3. FIELD EXCEPTIONS, ENVIRONMENT & REMARKS",
        f"- Metocean: {env_line}",
        f"- Remarks: {raw_rem if raw_rem else 'None (within design specification).'}"
    ]
    hist_rows = [r for r in (ledger_list or []) if int(float(r.get("unit_no") or 0)) < cur_uno] if (include_history and not is_first) else []
    if hist_rows:
        lines.extend(["", "## 4. PRIOR PLACED UNITS IN CROSSING", "| Unit # | Date/Time | Box ID | Tag ID | As-Laid E | As-Laid N | dCL (m) | Gaps |", "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"])
        for r in hist_rows:
            lines.append(f"| {r.get('unit_no','')} | {r.get('install_date','')} | {r.get('design_box_id','')} | {r.get('physical_tag','')} | {float(r.get('aslaid_e') or 0):.3f} | {float(r.get('aslaid_n') or 0):.3f} | {float(r.get('cl_offset_m') or 0):.3f} | {r.get('gap_labels','')} |")
    return chr(10).join(lines)"""

src = re.sub(
    r"def build_structured_report_markdown\(.*?(?=\ndef render_a4_landscape_figures)",
    lambda _m: lean_md_fn.strip() + "\n",
    src,
    count=1,
    flags=re.S
)

headline_hook = """    # --- EXECUTIVE TAKEAWAY LINE (Audience-First Signal Before Tables) ---
    latest_status = day_logs[-1][4][:78] if day_logs else ("Installation active" if day_fixes else "No field events logged")
    pct_done = (len(cum_fixes) * 100.0) / 139.0
    exec_line = f"DAILY TAKEAWAY: +{len(day_fixes)} Laid Today ({len(cum_fixes)}/139 Cumul, {pct_done:.1f}%)  |  {len(day_logs)} Log Event(s)  |  Latest Status: {latest_status}"
    ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.8, facecolor="#f0f9ff", edgecolor="#0284c7", linewidth=0.6))
    ax.text(15, y + 1.1, exec_line[:135], fontsize=7.8, fontweight="bold", color="#0f172a", va="center")
    y -= 6.0

    # --- SECTION 1: DAILY & CUMULATIVE MTI PROGRESS MATRIX BY CROSSING ---"""

if "DAILY TAKEAWAY:" not in src:
    src = src.replace("    # --- SECTION 1: DAILY & CUMULATIVE MTI PROGRESS MATRIX BY CROSSING ---", headline_hook, 1)

ast.parse(src)
open("mti_4panel_reports.py", "w", encoding="utf-8").write(src)

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try: os.remove(p)
    except Exception: pass

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else ("python" if os.path.exists("sync.py") else "py")
subprocess.run([sync_py, "sync.py", "refactor(reports): apply audience-first signal-over-volume reporting principle to MTI PDFs"], check=False)
print("Lean audience-first reporting applied to mti_4panel_reports.py and synced!")