import os, io, re, zipfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def build_structured_report_markdown(metrics, include_history=False, ledger_list=None, scale_p1=250, scale_p2=75):
    loc_id, mat_id = metrics.get("location_id", "CR-A1_M15"), metrics.get("mattress_id", "#A046")
    xing_id, usbl_s = metrics.get("crossing_id", "CR-A1_L1"), metrics.get("usbl_sensor", "Survey Pole")
    cl_off, cl_tol = float(metrics.get("cl_offset_m", 0.0)), float(metrics.get("cl_tol", 0.50))
    max_g, g_tol = float(metrics.get("max_gap_m", 0.0)), float(metrics.get("gap_tol", 0.20))
    is_first = bool(metrics.get("is_first_in_array", False))
    c_enz = metrics.get("corners_enz") or [[0,0,0]]*4
    nb, gaps = metrics.get("neighbors") or {}, metrics.get("gaps") or {}
    cl_st = "PASS" if cl_off <= cl_tol else "EXCEEDS"
    gap_st = "N/A (1st Unit)" if is_first else ("PASS" if max_g <= g_tol else "EXCEEDS")

    lines = [
        f"# SUBSEA MATTRESS VERIFICATION REPORT: {loc_id} ({mat_id})",
        f"**Project:** Tung-Hsiao Power Plant 2nd Stage Renewal Subsea Gas Pipeline Project",
        f"**Client:** Taiwan Power Company (TPC) | **Contractor:** NMDC Energy | **Vessel:** DP2 MMA Prestige",
        f"**Crossing Array:** {xing_id} | **Location ID:** {loc_id} | **Mattress ID:** {mat_id} | **Active USBL:** {usbl_s}",
        f"**Survey Date/Time:** {metrics.get('install_date','')} | **Deliverable Base:** {metrics.get('base_filename','')}",
        f"**Chart Scales @ A3:** Panel 1 (1:{scale_p1}) | Panel 2 (1:{scale_p2}) | Panel 3 (1:75/1:15) | Panel 4 (1:50/1:15)",
        "",
        "## EXECUTIVE VERDICT",
        f"- **Overall Status:** {metrics.get('verdict', 'VERIFIED')}",
        f"- **Identification & Sensor:** Mattress **{mat_id}** at **{loc_id}** ({xing_id}) tracked via **{usbl_s}**.",
        f"- **Centerline Offset (dCL):** **{cl_off:.3f} m** vs. Tolerance **+/-{cl_tol:.2f} m** ({cl_st}) [dAlong: {metrics.get('d_along_m',0):+.3f} m, dCross: {metrics.get('d_cross_m',0):+.3f} m].",
        f"- **Heading Alignment:** Design South Brg **{metrics.get('design_brg',195.854):.3f} deg** vs. As-Laid **{metrics.get('heading_deg',195.854):.3f} deg** (dBrg: **{metrics.get('brg_diff_deg',0):+.3f} deg**).",
        f"- **ROV Corner Gaps:** **{metrics.get('gap_labels','N/A')}** | Max Gap **{max_g:.2f} m** vs. Tolerance **<={g_tol:.2f} m** ({gap_st}).",
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
        f"| ROV Corner Gaps (m) | Tol <={g_tol:.2f} m | - | {metrics.get('gap_labels','N/A')} | {gap_st} |",
        "",
        "## 2. KEY SURVEY FINDINGS (4-CORNER ROV COORDINATES & ENVIRONMENT)",
        f"- **C1 (NW):** E {c_enz[0][0]:.3f} m, N {c_enz[0][1]:.3f} m, Z {c_enz[0][2]:.2f} m | ROV Gap NW: {gaps.get('nw') or 'N/A'}",
        f"- **C2 (NE):** E {c_enz[1][0]:.3f} m, N {c_enz[1][1]:.3f} m, Z {c_enz[1][2]:.2f} m | ROV Gap NE: {gaps.get('ne') or 'N/A'}",
        f"- **C3 (SE):** E {c_enz[2][0]:.3f} m, N {c_enz[2][1]:.3f} m, Z {c_enz[2][2]:.2f} m | ROV Gap SE: {gaps.get('se') or 'N/A'}",
        f"- **C4 (SW):** E {c_enz[3][0]:.3f} m, N {c_enz[3][1]:.3f} m, Z {c_enz[3][2]:.2f} m | ROV Gap SW: {gaps.get('sw') or 'N/A'}",
        f"- **Edge Clearances:** NNE {metrics.get('edge_nne',0):+.2f}m (Nbr: {nb.get('NNE') or 'None'}), SSW {metrics.get('edge_ssw',0):+.2f}m (Nbr: {nb.get('SSW') or 'None'}), ESE {metrics.get('edge_ese',0):+.2f}m (Nbr: {nb.get('ESE') or 'None'}), WNW {metrics.get('edge_wnw',0):+.2f}m (Nbr: {nb.get('WNW') or 'None'}).",
        f"- **Environment:** Wind: {metrics.get('env_wind') or 'Recorded in Log'} | Current: {metrics.get('env_current') or 'Recorded in Log'}.",
        "",
        "## 3. OPERATIONAL CRANE / ROV NUDGE RECOMMENDATION",
        f"- **Required Vector to Design Center:** Shift **{metrics.get('nudge_dist_m',0):.2f} m** toward **{metrics.get('nudge_dir','N')}** (Azimuth **{metrics.get('nudge_az_deg',0):.1f} deg**).",
        f"- **Cartesian Adjustments:** dE = **{metrics.get('nudge_de',0):+.3f} m**, dN = **{metrics.get('nudge_dn',0):+.3f} m**.",
        "",
        "## 4. SURVEYOR REMARKS",
        f"- {metrics.get('remarks') or 'Mattress installation verified via WROV 4-corner fix and USBL telemetry.'}"
    ]
    if include_history and ledger_list:
        lines.extend(["", "## 5. HISTORICAL CROSSING LEDGER", "| Unit # | Date/Time | Location ID | Tag ID | As-Laid E | As-Laid N | Brg (deg) | dCL (m) | Gaps |", "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"])
        for r in ledger_list:
            lines.append(f"| {r.get('unit_no','')} | {r.get('install_date','')} | {r.get('design_box_id','')} | {r.get('physical_tag','')} | {float(r.get('aslaid_e') or 0):.3f} | {float(r.get('aslaid_n') or 0):.3f} | {float(r.get('heading_deg') or 0):.2f} | {float(r.get('cl_offset_m') or 0):.3f} | {r.get('gap_labels','')} |")
    return chr(10).join(lines)

def generate_a4_report_pdf(metrics, workspace_dir="workspace", custom_report_md=None):
    os.makedirs(workspace_dir, exist_ok=True)
    md_text = custom_report_md if custom_report_md else build_structured_report_markdown(metrics)
    W_MM, H_MM = 210.0, 297.0
    fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4), dpi=150, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1], frameon=False)
    ax.set_xlim(0, W_MM); ax.set_ylim(0, H_MM); ax.set_xticks([]); ax.set_yticks([])

    ax.add_patch(mpatches.Rectangle((14, 14), 182, 269, fill=False, edgecolor="#0f172a", linewidth=1.3))
    ax.add_patch(mpatches.Rectangle((14, 269), 182, 14, facecolor="#0f172a", edgecolor="#0f172a"))
    loc_id, mat_id = metrics.get("location_id", "CR-A1_M15"), metrics.get("mattress_id", "#A046")
    ax.text(18, 277.5, f"ISO A4 SUBSEA MATTRESS VERIFICATION REPORT  |  {loc_id} ({mat_id})", color="white", fontsize=8.8, fontweight="bold", va="center")
    ax.text(18, 272.2, f"File: {metrics.get('base_filename','')}_A4_Report.pdf  |  Active USBL: {metrics.get('usbl_sensor','Survey Pole')}  |  {metrics.get('verdict','')[:36]}", color="#38bdf8", fontsize=6.8, fontweight="bold", va="center")

    y_cur = 262.5
    for raw_l in str(md_text).splitlines():
        line = raw_l.strip()
        if y_cur < 21.0: break
        if not line: y_cur -= 2.0; continue
        if line.startswith("# "):
            ax.text(18, y_cur, line[2:], fontsize=8.8, fontweight="bold", color="#0f172a"); y_cur -= 4.8
        elif line.startswith("## "):
            y_cur -= 1.0
            ax.add_patch(mpatches.Rectangle((17, y_cur - 1.1), 176, 4.6, facecolor="#e2e8f0", edgecolor="none"))
            ax.text(19, y_cur + 1.1, line[3:], fontsize=7.6, fontweight="bold", color="#0f172a", va="center"); y_cur -= 4.8
        elif line.startswith("|"):
            if ":---" in line: continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            n_c = max(len(cells), 1)
            xs = [18.0, 62.0, 96.0, 130.0, 164.0] if n_c == 5 else [18.0 + i * (174.0 / n_c) for i in range(n_c)]
            for ic, c_txt in enumerate(cells):
                ax.text(xs[ic], y_cur, c_txt[:28], fontsize=5.8, family="monospace", color="#1e293b")
            y_cur -= 3.5
        else:
            cl = line.replace("**", "")
            ax.text(18, y_cur, cl[:110], fontsize=6.8, color="#1e293b")
            if len(cl) > 110:
                y_cur -= 3.4; ax.text(21, y_cur, cl[110:220], fontsize=6.8, color="#1e293b")
            y_cur -= 3.8

    ax.plot([14, 196], [19, 19], color="#cbd5e1", linewidth=0.8)
    ax.text(18, 15.5, f"DP2 MMA Prestige | Tung-Hsiao 2nd Stage Subsea Gas Pipeline Project | Date: {metrics.get('install_date','')}", fontsize=6.0, color="#64748b")
    ax.text(192, 15.5, "ISO A4 Portrait | Page 1 of 1", fontsize=6.0, color="#64748b", ha="right")

    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", dpi=150); plt.close(fig)
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
        if not line or ":---" in line: continue
        txt = _xml_esc(re.sub(r"^#+\s*", "", line).replace("**", ""))
        if line.startswith("#"):
            p_list.append(f'<w:p><w:r><w:rPr><w:b/><w:sz w:val="24"/></w:rPr><w:t>{txt}</w:t></w:r></w:p>')
        elif line.startswith("|"):
            row_t = _xml_esc("  |  ".join([c.strip() for c in line.strip("|").split("|")]))
            p_list.append(f'<w:p><w:r><w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/><w:sz w:val="18"/></w:rPr><w:t>{row_t}</w:t></w:r></w:p>')
        else:
            p_list.append(f'<w:p><w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t>{txt}</w:t></w:r></w:p>')

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
