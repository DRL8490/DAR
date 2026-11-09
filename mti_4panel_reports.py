import os, io, re, gc, zipfile
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages

def build_structured_report_markdown(metrics, include_history=False, ledger_list=None, scale_p1=250, scale_p2=75):
    loc_id, mat_id = metrics.get("location_id", "CR-A1_M15"), metrics.get("mattress_id", "#A046")
    xing_id, usbl_s = metrics.get("crossing_id", "CR-A1_L1"), metrics.get("usbl_sensor", "Survey Pole")
    cl_off, cl_tol = float(metrics.get("cl_offset_m", 0.0)), float(metrics.get("cl_tol", 0.50))
    max_g, g_tol = float(metrics.get("max_gap_m", 0.0)), float(metrics.get("gap_tol", 0.50))
    is_first = bool(metrics.get("is_first_in_array", False))
    cur_uno = int(metrics.get("unit_no") or (1 if is_first else 2))
    c_enz = metrics.get("corners_enz") or [[0,0,0]]*4
    gaps = metrics.get("gaps") or {}
    cl_st = "PASS" if cl_off <= cl_tol else "EXCEEDS"
    gap_st = "N/A (1st Unit)" if is_first else ("PASS" if max_g <= g_tol else "EXCEEDS")

    lines = [
        f"# SUBSEA MATTRESS VERIFICATION REPORT: {loc_id} ({mat_id})",
        f"**Project:** Tung-Hsiao Power Plant 2nd Stage Renewal Subsea Gas Pipeline Project",
        f"**Client:** Taiwan Power Company (TPC) | **Contractor:** NMDC Energy | **Vessel:** DP2 MMA Prestige",
        f"**Crossing Array:** {xing_id} | **Location ID:** {loc_id} | **Mattress ID:** {mat_id} | **Active USBL:** {usbl_s}",
        f"**Placement Date & Time:** {metrics.get('install_date','')} | **Surveyor Name:** {metrics.get('surveyor_name','Duty Surveyor')} | **Deliverable:** {metrics.get('base_filename','')}",
        "",
        "## EXECUTIVE VERDICT",
        f"- **Overall Status:** {metrics.get('verdict', 'VERIFIED')}",
        f"- **Identification & Sensor:** Mattress **{mat_id}** at **{loc_id}** ({xing_id}) tracked via **{usbl_s}**.",
        f"- **Centerline Offset (dCL):** **{cl_off:.3f} m** vs. Tolerance **+/-{cl_tol:.2f} m** ({cl_st}) [dAlong: {metrics.get('d_along_m',0):+.3f} m, dCross: {metrics.get('d_cross_m',0):+.3f} m].",
        f"- **Heading Alignment:** Design South Brg **{metrics.get('design_brg',195.854):.3f} deg** vs. As-Laid **{metrics.get('heading_deg',195.854):.3f} deg** (dBrg: **{metrics.get('brg_diff_deg',0):+.3f} deg**).",
        f"- **Surveyor Corner Gaps:** **{metrics.get('gap_labels','N/A')}** | Max Gap **{max_g:.2f} m** vs. Side-to-Side Gap Tolerance **<={g_tol:.2f} m** ({gap_st}).",
        "",
        "## 1. GEODETIC, 4-CORNER ROV & GAP COMPARISON TABLE",
        "| Parameter | Design Baseline | QA/QC USBL Fix | As-Laid 4-Corner ROV | Delta / Status |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| Easting E (m, TWD97) | {metrics.get('design_e',0):.3f} | {metrics.get('qaqc_e',0):.3f} | {metrics.get('aslaid_e',0):.3f} | {metrics.get('aslaid_e',0)-metrics.get('design_e',0):+.3f} m |",
        f"| Northing N (m, TWD97) | {metrics.get('design_n',0):.3f} | {metrics.get('qaqc_n',0):.3f} | {metrics.get('aslaid_n',0):.3f} | {metrics.get('aslaid_n',0)-metrics.get('design_n',0):+.3f} m |",
        f"| Depth Z (m, TWVD2001) | Seabed + 0.30 m | - | {metrics.get('aslaid_z',-18.2):.2f} | Verified WROV |",
        f"| South Bearing (deg) | {metrics.get('design_brg',0):.3f} deg | {metrics.get('qaqc_brg',0):.3f} deg | {metrics.get('heading_deg',0):.3f} deg | {metrics.get('brg_diff_deg',0):+.3f} deg |",
        f"| North Azimuth (deg) | {metrics.get('design_az',0):.3f} deg | - | {metrics.get('act_az',0):.3f} deg | {metrics.get('brg_diff_deg',0):+.3f} deg |",
        f"| Radial Offset dCL (m) | 0.000 m (Tol +/-{cl_tol:.2f}m) | - | {cl_off:.3f} m | {cl_st} ({metrics.get('pct_inside',0):.1f}% in box) |",
        f"| Side-to-Side Gap (m) | Tol <={g_tol:.2f} m | - | {metrics.get('gap_labels','N/A')} | {gap_st} |",
        "",
        "## 2. KEY SURVEY FINDINGS (4-CORNER ROV COORDINATES & CORNER GAPS)",
        f"- **C1 (NW Corner):** E {c_enz[0][0]:.3f} m, N {c_enz[0][1]:.3f} m, Z {c_enz[0][2]:.2f} m" + ("" if is_first else f" | Surveyor Corner Gap NW: {gaps.get('nw') or 'N/A'}"),
        f"- **C2 (NE Corner):** E {c_enz[1][0]:.3f} m, N {c_enz[1][1]:.3f} m, Z {c_enz[1][2]:.2f} m" + ("" if is_first else f" | Surveyor Corner Gap NE: {gaps.get('ne') or 'N/A'}"),
        f"- **C3 (SE Corner):** E {c_enz[2][0]:.3f} m, N {c_enz[2][1]:.3f} m, Z {c_enz[2][2]:.2f} m" + ("" if is_first else f" | Surveyor Corner Gap SE: {gaps.get('se') or 'N/A'}"),
        f"- **C4 (SW Corner):** E {c_enz[3][0]:.3f} m, N {c_enz[3][1]:.3f} m, Z {c_enz[3][2]:.2f} m" + ("" if is_first else f" | Surveyor Corner Gap SW: {gaps.get('sw') or 'N/A'}"),
    ]
    if is_first:
        lines.append(f"- **1st-Unit Edge Overhang/Clearance:** NNE {metrics.get('edge_nne',0):+.2f}m, SSW {metrics.get('edge_ssw',0):+.2f}m, ESE {metrics.get('edge_ese',0):+.2f}m, WNW {metrics.get('edge_wnw',0):+.2f}m.")
    else:
        lines.append(f"- **Surveyor Recorded Corner Gaps (Tol <={g_tol:.2f}m Side-to-Side Gap):** {metrics.get('gap_labels','N/A')}.")
    lines.extend([
        f"- **Environment:** Wind: {metrics.get('env_wind') or 'Recorded in Log'} | Current: {metrics.get('env_current') or 'Recorded in Log'}.",
        "",
        "## 3. SURVEYOR REMARKS",
        f"- {metrics.get('remarks') or 'Mattress installation verified via WROV 4-corner fix and USBL telemetry.'}"
    ])
    hist_rows = [r for r in (ledger_list or []) if int(float(r.get("unit_no") or 0)) < cur_uno] if (include_history and not is_first) else []
    if hist_rows:
        lines.extend(["", "## 4. HISTORICAL PLACED UNITS LEDGER", "| Unit # | Date/Time | Location ID | Tag ID | As-Laid E | As-Laid N | Brg (deg) | dCL (m) | Corner Gaps |", "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"])
        for r in hist_rows:
            lines.append(f"| {r.get('unit_no','')} | {r.get('install_date','')} | {r.get('design_box_id','')} | {r.get('physical_tag','')} | {float(r.get('aslaid_e') or 0):.3f} | {float(r.get('aslaid_n') or 0):.3f} | {float(r.get('heading_deg') or 0):.2f} | {float(r.get('cl_offset_m') or 0):.3f} | {r.get('gap_labels','')} |")
    return chr(10).join(lines)

def render_a4_landscape_figures(metrics, custom_report_md=None):
    """Renders Landscape (297 x 210 mm) report page(s) with +2 pt larger fonts, no redundant Chart Scales line, and no 'ISO A4' text."""
    md_text = custom_report_md if custom_report_md else build_structured_report_markdown(metrics)
    filtered_lines = [
        ln for ln in str(md_text).splitlines()
        if "chart scales @ a3" not in ln.strip().lower() and "chart scales:" not in ln.strip().lower()
    ]

    W_MM, H_MM = 297.0, 210.0
    loc_id, mat_id = metrics.get("location_id", "CR-A1_M15"), metrics.get("mattress_id", "#A046")
    surv_name = metrics.get("surveyor_name", "Duty Surveyor")

    def _new_a4_landscape_page(page_num):
        fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4), dpi=150, facecolor="white")
        ax = fig.add_axes([0, 0, 1, 1], frameon=False)
        ax.set_xlim(0, W_MM); ax.set_ylim(0, H_MM); ax.set_xticks([]); ax.set_yticks([])
        ax.add_patch(mpatches.Rectangle((10, 10), 277, 190, fill=False, edgecolor="#0f172a", linewidth=1.4))
        ax.add_patch(mpatches.Rectangle((10, 186.5), 277, 13.5, facecolor="#0f172a", edgecolor="#0f172a"))
        ax.text(14, 195.2, f"SUBSEA MATTRESS VERIFICATION REPORT  |  {loc_id} ({mat_id})", color="white", fontsize=10.8, fontweight="bold", va="center")
        ax.text(14, 189.6, f"File: {metrics.get('base_filename','')}.pdf  |  Active USBL: {metrics.get('usbl_sensor','Survey Pole')}  |  {metrics.get('verdict','')}", color="#38bdf8", fontsize=8.6, fontweight="bold", va="center")
        ax.plot([10, 287], [16.0, 16.0], color="#cbd5e1", linewidth=0.8)
        ax.text(14, 12.2, f"DP2 MMA Prestige | Placement Date/Time: {metrics.get('install_date','')} | Surveyor: {surv_name}", fontsize=8.0, color="#475569", fontweight="bold")
        ax.text(283, 12.2, f"Verification Report | Page {page_num}", fontsize=8.0, color="#475569", ha="right")
        return fig, ax

    figs = []
    page_no = 1
    fig, ax = _new_a4_landscape_page(page_no)
    figs.append(fig)
    y_cur = 180.5

    for raw_l in filtered_lines:
        line = raw_l.strip()
        if y_cur < 19.5:
            page_no += 1
            fig, ax = _new_a4_landscape_page(page_no)
            figs.append(fig)
            y_cur = 180.5
        if not line:
            y_cur -= 1.6
            continue
        if line.startswith("# "):
            ax.text(14, y_cur, line[2:], fontsize=10.8, fontweight="bold", color="#0f172a")
            y_cur -= 5.0
        elif line.startswith("## "):
            y_cur -= 0.8
            ax.add_patch(mpatches.Rectangle((13, y_cur - 1.3), 271, 5.2, facecolor="#e2e8f0", edgecolor="none"))
            ax.text(15, y_cur + 1.2, line[3:], fontsize=9.6, fontweight="bold", color="#0f172a", va="center")
            y_cur -= 5.1
        elif line.startswith("|"):
            if ":---" in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            n_c = max(len(cells), 1)
            xs = [14.0, 74.0, 128.0, 182.0, 236.0] if n_c == 5 else [14.0 + i * (268.0 / n_c) for i in range(n_c)]
            is_hdr = ("Parameter" in cells[0] or "Unit #" in cells[0])
            for ic, c_txt in enumerate(cells):
                ax.text(xs[ic], y_cur, c_txt[:36], fontsize=7.8, fontweight="bold" if is_hdr else "normal", family="monospace", color="#0f172a" if is_hdr else "#1e293b")
            y_cur -= 4.0
        else:
            cl = line.replace("**", "")
            ax.text(14, y_cur, cl[:145], fontsize=8.8, color="#1e293b")
            if len(cl) > 145:
                y_cur -= 4.0
                ax.text(18, y_cur, cl[145:290], fontsize=8.8, color="#1e293b")
            y_cur -= 4.2

    return figs

def generate_a4_report_pdf(metrics, workspace_dir="workspace", custom_report_md=None):
    os.makedirs(workspace_dir, exist_ok=True)
    figs = render_a4_landscape_figures(metrics, custom_report_md)
    buf = io.BytesIO()
    with PdfPages(buf) as pdf_pages:
        for f in figs:
            pdf_pages.savefig(f, dpi=150)
            f.clf(); plt.close(f)
    plt.close('all'); gc.collect()
    pdf_bytes = buf.getvalue()
    for fn in ("latest_A4_Verification_Report.pdf", f"{metrics.get('base_filename','Report')}_A4_Report.pdf"):
        open(os.path.join(workspace_dir, fn), "wb").write(pdf_bytes)
    return pdf_bytes

def generate_mti_dpr_pdf(st_data, target_date_str=None, surveyor_name="Duty Surveyor", workspace_dir="workspace"):
    """Generates a Daily Progress Report (DPR) PDF for MTI Operations covering 00:00 to 23:59 of target_date_str."""
    os.makedirs(workspace_dir, exist_ok=True)
    ledger = list((st_data or {}).get("ledger") or [])
    raw_logs = []
    for k in ("logs", "events", "event_log", "survey_logs"):
        if isinstance((st_data or {}).get(k), list) and len(st_data[k]) > 0:
            raw_logs = list(st_data[k])
            break

    def _norm_date(s):
        s = str(s or "").strip()
        m1 = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", s)
        if m1:
            return f"{m1.group(1)}-{m1.group(2)}-{m1.group(3)}"
        m2 = re.search(r"(\d{2})[-/](\d{2})[-/](\d{4})", s)
        if m2:
            return f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}"
        return ""

    def _extract_time(s):
        m = re.search(r"(\d{2}:\d{2})", str(s or ""))
        return m.group(1) if m else "00:00"

    dt_iso = _norm_date(target_date_str)
    if not dt_iso:
        all_dates = []
        for lg in raw_logs:
            d = _norm_date(lg.get("timestamp") or lg.get("date") or lg.get("time") or lg.get("dt"))
            if d: all_dates.append(d)
        for r in ledger:
            d = _norm_date(r.get("install_date"))
            if d: all_dates.append(d)
        dt_iso = max(all_dates) if all_dates else datetime.utcnow().strftime("%Y-%m-%d")

    day_fixes = [r for r in ledger if _norm_date(r.get("install_date")) == dt_iso]
    day_fixes.sort(key=lambda r: _extract_time(r.get("install_date")))

    day_logs = []
    for lg in raw_logs:
        ts_raw = lg.get("timestamp") or lg.get("date") or lg.get("time") or lg.get("dt") or ""
        if _norm_date(ts_raw) == dt_iso:
            day_logs.append(lg)
    day_logs.sort(key=lambda lg: _extract_time(lg.get("timestamp") or lg.get("date") or lg.get("time") or ""))

    W_MM, H_MM = 297.0, 210.0

    def _new_dpr_page(page_num):
        fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4), dpi=150, facecolor="white")
        ax = fig.add_axes([0, 0, 1, 1], frameon=False)
        ax.set_xlim(0, W_MM); ax.set_ylim(0, H_MM); ax.set_xticks([]); ax.set_yticks([])
        ax.add_patch(mpatches.Rectangle((10, 10), 277, 190, fill=False, edgecolor="#0f172a", linewidth=1.4))
        ax.add_patch(mpatches.Rectangle((10, 185.5), 277, 14.5, facecolor="#0f172a", edgecolor="#0f172a"))
        ax.text(14, 194.8, "SUBSEA MATTRESS & ROCK BAG INSTALLATION (MTI) - DAILY PROGRESS REPORT (DPR)", color="white", fontsize=10.5, fontweight="bold", va="center")
        ax.text(14, 188.8, f"Reporting Period: {dt_iso} (00:00 to 23:59 hrs)  |  Vessel: DP2 MMA Prestige  |  Client: TPC  |  Contractor: NMDC", color="#38bdf8", fontsize=8.4, fontweight="bold", va="center")
        ax.plot([10, 287], [16.0, 16.0], color="#cbd5e1", linewidth=0.8)
        ax.text(14, 12.2, f"Tung-Hsiao 2nd Stage Subsea Gas Pipeline Project  |  Duty Surveyor: {surveyor_name}", fontsize=8.0, color="#475569", fontweight="bold")
        ax.text(283, 12.2, f"MTI DPR ({dt_iso} 00:00-23:59) | Page {page_num}", fontsize=8.0, color="#475569", ha="right")
        return fig, ax

    figs = []
    p_no = 1
    fig, ax = _new_dpr_page(p_no)
    figs.append(fig)
    y = 179.5

    ax.add_patch(mpatches.Rectangle((13, y - 1.5), 271, 5.2, facecolor="#e2e8f0", edgecolor="none"))
    ax.text(15, y + 1.0, f"1. DAILY MTI OPERATIONS SUMMARY ({dt_iso} | 00:00 TO 23:59 HRS)", fontsize=9.4, fontweight="bold", color="#0f172a", va="center")
    y -= 5.8
    total_scope = int((st_data or {}).get("target_mattresses") or 139)
    ax.text(15, y, f"Mattresses Laid on {dt_iso} (00:00-23:59): {len(day_fixes)} unit(s)   |   Cumulative Mattresses Laid: {len(ledger)} / {total_scope} ({len(ledger)*100.0/max(total_scope,1):.1f}%)   |   Events Logged Today: {len(day_logs)}", fontsize=8.8, fontweight="bold", color="#0369a1")
    y -= 5.5

    ax.add_patch(mpatches.Rectangle((13, y - 1.5), 271, 5.2, facecolor="#e2e8f0", edgecolor="none"))
    ax.text(15, y + 1.0, f"2. MATTRESSES PLACED ON {dt_iso} (00:00 TO 23:59 HRS)", fontsize=9.4, fontweight="bold", color="#0f172a", va="center")
    y -= 5.4

    if not day_fixes:
        ax.text(15, y, f"No mattress fixes recorded between 00:00 and 23:59 on {dt_iso}.", fontsize=8.5, color="#64748b")
        y -= 5.0
    else:
        cols_f = [(15, "Unit #"), (30, "Time"), (50, "Crossing"), (75, "Location ID"), (102, "Tag ID"), (122, "As-Laid E"), (152, "As-Laid N"), (182, "Brg"), (200, "dCL (m)"), (222, "Gaps / Status")]
        for cx, c_lbl in cols_f:
            ax.text(cx, y, c_lbl, fontsize=8.0, fontweight="bold", color="#0f172a", family="monospace")
        y -= 4.0
        for r in day_fixes:
            if y < 22.0:
                p_no += 1; fig, ax = _new_dpr_page(p_no); figs.append(fig); y = 179.5
            t_hm = _extract_time(r.get("install_date"))
            row_vals = [
                (15, f"#{r.get('unit_no','')}"),
                (30, t_hm),
                (50, str(r.get("crossing_id") or "")[:10]),
                (75, str(r.get("design_box_id") or "")[:12]),
                (102, str(r.get("physical_tag") or "")[:8]),
                (122, f"{float(r.get('aslaid_e') or 0):.3f}"),
                (152, f"{float(r.get('aslaid_n') or 0):.3f}"),
                (182, f"{float(r.get('heading_deg') or 0):.1f}"),
                (200, f"{float(r.get('cl_offset_m') or 0):.2f}m"),
                (222, f"{r.get('gap_labels','')} ({r.get('status','Completed')})"[:32])
            ]
            for cx, val_s in row_vals:
                ax.text(cx, y, val_s, fontsize=7.8, color="#1e293b", family="monospace")
            y -= 4.0
        y -= 2.0

    if y < 35.0:
        p_no += 1; fig, ax = _new_dpr_page(p_no); figs.append(fig); y = 179.5
    ax.add_patch(mpatches.Rectangle((13, y - 1.5), 271, 5.2, facecolor="#e2e8f0", edgecolor="none"))
    ax.text(15, y + 1.0, f"3. CHRONOLOGICAL ONBOARD SURVEY LOGS ({dt_iso} | 00:00 TO 23:59 HRS)", fontsize=9.4, fontweight="bold", color="#0f172a", va="center")
    y -= 5.4

    if not day_logs:
        ax.text(15, y, f"No survey events logged between 00:00 and 23:59 on {dt_iso}.", fontsize=8.5, color="#64748b")
    else:
        cols_l = [(15, "Time"), (32, "Category"), (68, "Asset / Area"), (102, "Event Description & Operational Details"), (250, "Surveyor")]
        for cx, c_lbl in cols_l:
            ax.text(cx, y, c_lbl, fontsize=8.0, fontweight="bold", color="#0f172a", family="monospace")
        y -= 4.0
        for lg in day_logs:
            if y < 21.0:
                p_no += 1; fig, ax = _new_dpr_page(p_no); figs.append(fig); y = 179.5
            ts_s = str(lg.get("timestamp") or lg.get("date") or lg.get("time") or "")
            t_hm = _extract_time(ts_s)
            cat_s = str(lg.get("category") or lg.get("type") or lg.get("event_type") or "Ops")[:16]
            area_s = str(lg.get("crossing_id") or lg.get("location") or lg.get("asset") or lg.get("vessel") or "MMA Prestige")[:15]
            desc_s = str(lg.get("description") or lg.get("title") or lg.get("remarks") or lg.get("message") or "").strip()
            sub_s = str(lg.get("details") or lg.get("sub_text") or lg.get("env") or "").strip()
            full_desc = f"{desc_s} | {sub_s}" if (sub_s and sub_s not in desc_s) else desc_s
            surv_l = str(lg.get("surveyor") or lg.get("surveyor_name") or lg.get("user") or surveyor_name)[:16]

            ax.text(15, y, t_hm, fontsize=7.8, fontweight="bold", color="#0369a1", family="monospace")
            ax.text(32, y, cat_s, fontsize=7.8, fontweight="bold", color="#0f172a", family="monospace")
            ax.text(68, y, area_s, fontsize=7.8, color="#334155", family="monospace")
            ax.text(102, y, full_desc[:78], fontsize=7.8, color="#1e293b")
            ax.text(250, y, surv_l, fontsize=7.6, color="#475569", family="monospace")
            if len(full_desc) > 78:
                y -= 3.6
                ax.text(104, y, full_desc[78:156], fontsize=7.6, color="#475569")
            y -= 4.1

    buf = io.BytesIO()
    with PdfPages(buf) as pdf_pages:
        for f in figs:
            pdf_pages.savefig(f, dpi=150)
            f.clf(); plt.close(f)
    plt.close('all'); gc.collect()
    pdf_bytes = buf.getvalue()
    fn_out = f"{dt_iso.replace('-','')}_MTI_Daily_Progress_Report.pdf"
    open(os.path.join(workspace_dir, fn_out), "wb").write(pdf_bytes)
    open(os.path.join(workspace_dir, "latest_MTI_DPR.pdf"), "wb").write(pdf_bytes)
    return pdf_bytes, fn_out, dt_iso

def _xml_esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

def generate_editable_docx(metrics, report_md, workspace_dir="workspace"):
    os.makedirs(workspace_dir, exist_ok=True)
    p_list = []
    for raw_l in str(report_md or "").splitlines():
        line = raw_l.strip()
        if not line or ":---" in line or "chart scales @ a3" in line.lower():
            continue
        txt = _xml_esc(re.sub(r"^#+\s*", "", line).replace("**", ""))
        if line.startswith("#"):
            p_list.append(f'<w:p><w:r><w:rPr><w:b/><w:sz w:val="28"/></w:rPr><w:t>{txt}</w:t></w:r></w:p>')
        elif line.startswith("|"):
            row_t = _xml_esc("  |  ".join([c.strip() for c in line.strip("|").split("|")]))
            p_list.append(f'<w:p><w:r><w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/><w:sz w:val="22"/></w:rPr><w:t>{row_t}</w:t></w:r></w:p>')
        else:
            p_list.append(f'<w:p><w:r><w:rPr><w:sz w:val="24"/></w:rPr><w:t>{txt}</w:t></w:r></w:p>')

    doc_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + "".join(p_list) + '<w:sectPr/></w:body></w:document>'
    ct_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct_xml); zf.writestr("_rels/.rels", rels_xml); zf.writestr("word/document.xml", doc_xml)
    docx_bytes = buf.getvalue()
    for fn in ("latest_Verification_Report.docx", f"{metrics.get('base_filename','Report')}_Report.docx"):
        open(os.path.join(workspace_dir, fn), "wb").write(docx_bytes)
    return docx_bytes
