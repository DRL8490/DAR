import os, re, glob, ast, subprocess

rep_path = "mti_4panel_reports.py"
if not os.path.exists(rep_path):
    raise SystemExit("mti_4panel_reports.py not found! Run inside your DAR project folder.")

src = open(rep_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")

if "timedelta" not in src:
    src = src.replace("from datetime import datetime", "from datetime import datetime, timedelta", 1)

# === 1. ADD HISTORICAL TIMESTAMP PROGRESS CALCULATOR & STYLED 0001-2400 TABLE DRAWER ===
progress_helpers = """CONSOLIDATED_CROSSING_SCOPES = [
    ("C-A1", 27),
    ("C-B1", 27),
    ("C-A2", 7),
    ("C-B2", 7),
    ("C-A3", 36),
    ("C-B3", 35),
]

def _parse_fix_dt_tuple(dt_raw):
    s = str(dt_raw or "").strip()
    d_iso = norm_mti_date(s)
    if not d_iso:
        return ("", "00:00:00")
    m_t = re.search(r"(?:^|\\s|T)(\\d{1,2}):(\\d{2})(?::(\\d{2}))?", s)
    if m_t:
        hh, mm, ss = int(m_t.group(1)), int(m_t.group(2)), int(m_t.group(3) or 0)
        return (d_iso, f"{hh:02d}:{mm:02d}:{ss:02d}")
    return (d_iso, "23:59:59")

def _resolve_ledger_for_report(ledger_list=None):
    if ledger_list is not None:
        return list(ledger_list)
    try:
        import mti_blueprint as _mb
        return list((_mb.load_mti_state() or {}).get("ledger") or [])
    except Exception:
        return []

def compute_historical_progress_rows(ledger_list, cutoff_dt_str, current_metrics=None, full_day=False):
    rows_in = [dict(r) for r in _resolve_ledger_for_report(ledger_list)]
    ref_d, ref_t = _parse_fix_dt_tuple(cutoff_dt_str)
    if not ref_d:
        all_ds = [_parse_fix_dt_tuple(r.get("install_date"))[0] for r in rows_in]
        all_ds = [d for d in all_ds if d]
        ref_d = max(all_ds) if all_ds else datetime.utcnow().strftime("%Y-%m-%d")
    if full_day or not re.search(r"\\d{1,2}:\\d{2}", str(cutoff_dt_str or "")):
        ref_t = "23:59:59"

    try:
        prev_d = (datetime.strptime(ref_d, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception:
        prev_d = ""

    cur_uno = None
    if isinstance(current_metrics, dict) and current_metrics.get("location_id"):
        cur_box = str(current_metrics.get("location_id") or "").strip().upper()
        try:
            cur_uno = int(float(current_metrics.get("unit_no") or 0)) or None
        except Exception:
            cur_uno = None
        if cur_box and not any(str(r.get("design_box_id") or "").strip().upper() == cur_box for r in rows_in):
            rows_in.append({
                "unit_no": cur_uno or 9999,
                "crossing_id": current_metrics.get("crossing_id") or cur_box,
                "design_box_id": cur_box,
                "install_date": current_metrics.get("install_date") or f"{ref_d} {ref_t[:5]}",
                "status": current_metrics.get("status") or "Completed",
                "unit_type": "Concrete Mattress",
            })

    valid_up_to_cutoff = []
    for r in rows_in:
        if str(r.get("unit_type") or "Concrete Mattress").strip() == "Rock Bag":
            continue
        if str(r.get("status") or "Completed").strip().lower() == "planned":
            continue
        rd, rt = _parse_fix_dt_tuple(r.get("install_date"))
        if not rd:
            continue
        if (rd, rt) < (ref_d, ref_t):
            valid_up_to_cutoff.append((rd, r))
        elif (rd, rt) == (ref_d, ref_t):
            try:
                r_uno = int(float(r.get("unit_no") or 0))
            except Exception:
                r_uno = 0
            if cur_uno is None or r_uno <= cur_uno or not full_day:
                valid_up_to_cutoff.append((rd, r))

    out_rows = []
    tot_scope = tot_post = tot_today = tot_cum = tot_rem = 0
    for grp_id, scope_qty in CONSOLIDATED_CROSSING_SCOPES:
        grp_items = [(rd, r) for (rd, r) in valid_up_to_cutoff if normalize_crossing_group(r.get("crossing_id") or r.get("design_box_id")) == grp_id]
        cum_q = len(grp_items)
        today_q = sum(1 for (rd, _) in grp_items if rd == ref_d)
        post_q = sum(1 for (rd, _) in grp_items if prev_d and rd == prev_d)
        rem_q = max(0, scope_qty - cum_q)
        out_rows.append((grp_id, scope_qty, post_q, today_q, cum_q, rem_q))
        tot_scope += scope_qty
        tot_post += post_q
        tot_today += today_q
        tot_cum += cum_q
        tot_rem += rem_q

    totals = ("TOTAL", tot_scope, tot_post, tot_today, tot_cum, tot_rem)
    return out_rows, totals, ref_d

def draw_mattress_progress_box(ax, y_top, prog_rows, totals_row, title_str="INSTALLATION PROGRESS OF CONCRETE MATTRESS 0001-2400"):
    x0, w_tot = 13.0, 271.0
    col_edges = [13.0, 58.0, 105.0, 150.0, 193.0, 241.0, 284.0]
    h_title = 5.2
    h_hdr = 10.6
    h_row = 4.3

    ax.add_patch(mpatches.Rectangle((x0, y_top - h_title), w_tot, h_title, facecolor="#fef08a", edgecolor="#0f172a", linewidth=0.75))
    ax.text(x0 + w_tot / 2.0, y_top - h_title / 2.0, title_str, fontsize=8.4, fontweight="bold", color="#0f172a", ha="center", va="center")
    ax.plot([x0 + 68.0, x0 + w_tot - 68.0], [y_top - h_title + 0.85, y_top - h_title + 0.85], color="#0f172a", linewidth=0.65)
    y = y_top - h_title

    ax.add_patch(mpatches.Rectangle((x0, y - h_hdr), w_tot, h_hdr, facecolor="#bae6fd", edgecolor="#0f172a", linewidth=0.75))
    hdr_labels = [
        "LOCATION /\\nCROSSING ID",
        "TOTAL\\nQUANTITY TO\\nBE INSTALLED",
        "POST\\nINSTALLED\\nQUANTITY",
        "TODAY\\nINSTALLED",
        "TOTAL\\nCUMULATIVE\\nINSTALLED",
        "REMAINING",
    ]
    for ic, h_txt in enumerate(hdr_labels):
        cx = 0.5 * (col_edges[ic] + col_edges[ic + 1])
        ax.text(cx, y - h_hdr / 2.0, h_txt, fontsize=6.8, fontweight="bold", color="#0f172a", ha="center", va="center", linespacing=1.15)
    y -= h_hdr

    all_draw_rows = list(prog_rows) + [totals_row]
    for lbl, sc_q, post_q, tod_q, cum_q, rem_q in all_draw_rows:
        is_tot = (lbl == "TOTAL")
        fc_r = "#f8fafc" if is_tot else "#ffffff"
        ax.add_patch(mpatches.Rectangle((x0, y - h_row), w_tot, h_row, facecolor=fc_r, edgecolor="#0f172a", linewidth=0.65))
        row_col = "#0f172a" if is_tot else get_crossing_group_color(lbl, default="#0f172a")
        vals_r = [lbl, str(sc_q), str(post_q), str(tod_q), str(cum_q), str(rem_q)]
        for ic, v_txt in enumerate(vals_r):
            cx = 0.5 * (col_edges[ic] + col_edges[ic + 1])
            fw_cell = "bold" if (is_tot or ic == 0 or (ic in (2, 3, 4) and int(v_txt) > 0)) else "normal"
            c_cell = row_col if (is_tot or ic == 0 or int(v_txt) > 0) else "#475569"
            ax.text(cx, y - h_row / 2.0, v_txt, fontsize=7.6, fontweight=fw_cell, color=c_cell, ha="center", va="center")
        y -= h_row

    y_grid_top = y_top - h_title
    for xv in col_edges[1:-1]:
        ax.plot([xv, xv], [y, y_grid_top], color="#0f172a", linewidth=0.6)

    return y - 2.6
"""

if "def compute_historical_progress_rows(" not in src:
    src = src.replace(
        "CROSSING_SCOPES = [",
        progress_helpers + "\nCROSSING_SCOPES = [",
        1
    )

# === 2. APPEND PROGRESS TABLE SECTION IN build_structured_report_markdown() ===
old_md_ret = """    if hist_rows:
        lines.extend(["", "## 4. PRIOR PLACED UNITS IN CROSSING", "| Unit # | Date/Time | Box ID | Tag ID | As-Laid E | As-Laid N | dCL (m) | Gaps |", "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"])
        for r in hist_rows:
            lines.append(f"| {r.get('unit_no','')} | {r.get('install_date','')} | {r.get('design_box_id','')} | {r.get('physical_tag','')} | {float(r.get('aslaid_e') or 0):.3f} | {float(r.get('aslaid_n') or 0):.3f} | {float(r.get('cl_offset_m') or 0):.3f} | {r.get('gap_labels','')} |")
    return chr(10).join(lines)"""

new_md_ret = """    ledger_all = _resolve_ledger_for_report(ledger_list)
    hist_use = [r for r in ledger_all if int(float(r.get("unit_no") or 0)) < cur_uno] if (include_history and not is_first) else []
    sec_no = 4
    if hist_use:
        lines.extend(["", f"## {sec_no}. PRIOR PLACED UNITS IN CROSSING", "| Unit # | Date/Time | Box ID | Tag ID | As-Laid E | As-Laid N | dCL (m) | Gaps |", "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"])
        for r in hist_use:
            lines.append(f"| {r.get('unit_no','')} | {r.get('install_date','')} | {r.get('design_box_id','')} | {r.get('physical_tag','')} | {float(r.get('aslaid_e') or 0):.3f} | {float(r.get('aslaid_n') or 0):.3f} | {float(r.get('cl_offset_m') or 0):.3f} | {r.get('gap_labels','')} |")
        sec_no += 1

    prog_rows, prog_tot, _ = compute_historical_progress_rows(ledger_all, metrics.get("install_date"), current_metrics=metrics, full_day=False)
    lines.extend([
        "",
        f"## {sec_no}. INSTALLATION PROGRESS OF CONCRETE MATTRESS 0001-2400",
        "| LOCATION / CROSSING ID | TOTAL QUANTITY TO BE INSTALLED | POST INSTALLED QUANTITY | TODAY INSTALLED | TOTAL CUMULATIVE INSTALLED | REMAINING |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])
    for pr in list(prog_rows) + [prog_tot]:
        lines.append(f"| {pr[0]} | {pr[1]} | {pr[2]} | {pr[3]} | {pr[4]} | {pr[5]} |")
    return chr(10).join(lines)"""

if "INSTALLATION PROGRESS OF CONCRETE MATTRESS 0001-2400" not in src.split("def render_a4_landscape_figures")[0]:
    src = src.replace(old_md_ret, new_md_ret, 1)

# === 3. RENDER GRAPHICAL YELLOW/BLUE PROGRESS TABLE ON A4 VERIFICATION REPORT ===
src = src.replace(
    "def render_a4_landscape_figures(metrics, custom_report_md=None):",
    "def render_a4_landscape_figures(metrics, custom_report_md=None, ledger_list=None):",
    1
)
src = src.replace(
    "md_text = custom_report_md if custom_report_md else build_structured_report_markdown(metrics)",
    "md_text = custom_report_md if custom_report_md else build_structured_report_markdown(metrics, True, ledger_list)"
)

prog_intercept_loop = """    idx_ln = 0
    drawn_prog_box = False
    while idx_ln < len(filtered_lines):
        line = filtered_lines[idx_ln].strip()
        idx_ln += 1

        if line.startswith("## ") and "INSTALLATION PROGRESS OF CONCRETE MATTRESS" in line.upper():
            while idx_ln < len(filtered_lines) and (not filtered_lines[idx_ln].strip() or filtered_lines[idx_ln].strip().startswith("|")):
                idx_ln += 1
            prog_rows, prog_tot, _ = compute_historical_progress_rows(ledger_list, metrics.get("install_date"), current_metrics=metrics, full_day=False)
            y_cur -= 1.0
            if y_cur - 47.0 < 16.5:
                page_no += 1
                fig, ax = _new_a4_landscape_page(page_no)
                figs.append(fig)
                y_cur = 181.5
            y_cur = draw_mattress_progress_box(ax, y_cur + 2.0, prog_rows, prog_tot)
            drawn_prog_box = True
            continue"""

if "drawn_prog_box = False" not in src:
    src = src.replace(
        "    for raw_l in filtered_lines:\n        line = raw_l.strip()",
        prog_intercept_loop,
        1
    )
    src = src.replace(
        "    return figs\n\ndef generate_a4_report_pdf",
        """    if not drawn_prog_box:
        prog_rows, prog_tot, _ = compute_historical_progress_rows(ledger_list, metrics.get("install_date"), current_metrics=metrics, full_day=False)
        if y_cur - 47.0 < 16.5:
            page_no += 1
            fig, ax = _new_a4_landscape_page(page_no)
            figs.append(fig)
            y_cur = 181.5
        draw_mattress_progress_box(ax, y_cur + 1.0, prog_rows, prog_tot)

    return figs\n\ndef generate_a4_report_pdf""",
        1
    )

# === 4. RENDER IDENTICAL 0001-2400 PROGRESS TABLE IN A4 DPR PDF (SECTION 1) ===
new_dpr_sec1 = """    # --- SECTION 1: INSTALLATION PROGRESS OF CONCRETE MATTRESS 0001-2400 ---
    prog_rows_dpr, prog_tot_dpr, _ = compute_historical_progress_rows(ledger, f"{dt_iso} 23:59:59", current_metrics=None, full_day=True)
    y = draw_mattress_progress_box(ax, y + 2.2, prog_rows_dpr, prog_tot_dpr, title_str="INSTALLATION PROGRESS OF CONCRETE MATTRESS 0001-2400")
"""

src = re.sub(
    r"    # --- SECTION 1:.*?(?=\n    # --- SECTION 2: MATTRESSES PLACED ON TARGET DATE)",
    lambda _m: new_dpr_sec1,
    src, count=1, flags=re.S
)

ast.parse(src)
open(rep_path, "w", encoding="utf-8").write(src)
print("  -> Updated mti_4panel_reports.py (0001-2400 Progress Table + historical timestamp logic active on BOTH A4 reports, AST OK)")

for f_stale in glob.glob(os.path.join("workspace", "*.pdf")) + glob.glob(os.path.join("workspace", "*.docx")) + glob.glob(os.path.join("workspace", "*_cache.json")):
    try: os.remove(f_stale)
    except Exception: pass

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti-reports): add knots units, per-crossing group colors, and historical 0001-2400 progress table on A4 reports"], check=False)
print("\nPHASE 3 COMPLETE & SYNCED TO RENDER!")