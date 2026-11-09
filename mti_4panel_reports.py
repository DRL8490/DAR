import os, io, re, gc, zipfile
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
    """Renders ISO A4 Landscape (297 x 210 mm) report page(s) with +2 pt larger fonts and no redundant Chart Scales line."""
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
        ax.text(14, 195.2, f"ISO A4 SUBSEA MATTRESS VERIFICATION REPORT  |  {loc_id} ({mat_id})", color="white", fontsize=10.8, fontweight="bold", va="center")
        ax.text(14, 189.6, f"File: {metrics.get('base_filename','')}.pdf  |  Active USBL: {metrics.get('usbl_sensor','Survey Pole')}  |  {metrics.get('verdict','')}", color="#38bdf8", fontsize=8.6, fontweight="bold", va="center")
        ax.plot([10, 287], [16.0, 16.0], color="#cbd5e1", linewidth=0.8)
        ax.text(14, 12.2, f"DP2 MMA Prestige | Placement Date/Time: {metrics.get('install_date','')} | Surveyor: {surv_name}", fontsize=8.0, color="#475569", fontweight="bold")
        ax.text(283, 12.2, f"ISO A4 Landscape | Report Page {page_num}", fontsize=8.0, color="#475569", ha="right")
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
