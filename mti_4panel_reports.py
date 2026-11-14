import os, io, re, gc, zipfile, textwrap
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from mti_4panel_math import fmt_knots, format_remarks_knots

CROSSING_GROUP_COLORS = {
    "C-A1": "#1d4ed8",  # Navy Blue
    "C-B1": "#0f766e",  # Deep Teal
    "C-A2": "#6d28d9",  # Royal Purple
    "C-B2": "#b45309",  # Rust / Amber-Brown
    "C-A3": "#15803d",  # Forest Green
    "C-B3": "#be123c",  # Crimson Red
}

CROSSING_GROUP_DARK_BG_COLORS = {
    "C-A1": "#60a5fa",
    "C-B1": "#2dd4bf",
    "C-A2": "#c084fc",
    "C-B2": "#fbbf24",
    "C-A3": "#4ade80",
    "C-B3": "#fb7185",
}

def normalize_crossing_group(val):
    s = str(val or "").strip().upper()
    if not s:
        return ""
    m = re.search(r"(?<![#A-Z0-9])(?:CR[-_\s]?([AB][123])|C[-_]([AB][123])|([AB][123])[-_](?:L[12]|M\d+))(?:\b|[_-]|M\d)", s)
    if m:
        code = m.group(1) or m.group(2) or m.group(3)
        return f"C-{code}"
    if s in ("A1", "A2", "A3", "B1", "B2", "B3"):
        return f"C-{s}"
    return ""

def get_crossing_group_color(val, default="#1e293b", dark_bg=False):
    grp = normalize_crossing_group(val)
    if not grp:
        return default
    pal = CROSSING_GROUP_DARK_BG_COLORS if dark_bg else CROSSING_GROUP_COLORS
    return pal.get(grp, default)

CONSOLIDATED_CROSSING_SCOPES = [
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
    m_t = re.search(r"(?:^|\s|T)(\d{1,2}):(\d{2})(?::(\d{2}))?", s)
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
    if full_day or not re.search(r"\d{1,2}:\d{2}", str(cutoff_dt_str or "")):
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
        "LOCATION /\nCROSSING ID",
        "TOTAL\nQUANTITY TO\nBE INSTALLED",
        "POST\nINSTALLED\nQUANTITY",
        "TODAY\nINSTALLED",
        "TOTAL\nCUMULATIVE\nINSTALLED",
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

CROSSING_SCOPES = [
    ("CR-A1_L1", 25), ("CR-A1_L2", 2), ("CR-A2", 7), ("CR-A3", 36),
    ("CR-B1_L1", 25), ("CR-B1_L2", 2), ("CR-B2", 7), ("CR-B3", 35)
]

def norm_mti_date(s):
    s = str(s or "").strip()
    m1 = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m1:
        return f"{int(m1.group(1)):04d}-{int(m1.group(2)):02d}-{int(m1.group(3)):02d}"
    m2 = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if m2:
        a, b, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        return f"{y:04d}-{b:02d}-{a:02d}" if a > 12 else f"{y:04d}-{a:02d}-{b:02d}"
    m3 = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
    if m3:
        return f"{m3.group(1)}-{m3.group(2)}-{m3.group(3)}"
    months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    m4 = re.search(r"([A-Za-z]{3})[a-z]*[\s,-]+(\d{1,2})[\s,-]+(\d{4})", s)
    if m4 and m4.group(1).lower() in months:
        return f"{int(m4.group(3)):04d}-{months[m4.group(1).lower()]:02d}-{int(m4.group(2)):02d}"
    m5 = re.search(r"(\d{1,2})[\s,-]+([A-Za-z]{3})[a-z]*[\s,-]+(\d{4})", s)
    if m5 and m5.group(2).lower() in months:
        return f"{int(m5.group(3)):04d}-{months[m5.group(2).lower()]:02d}-{int(m5.group(1)):02d}"
    return ""

def extract_all_mti_logs(st_data):
    # Extracts onboard survey logs across list-of-dicts OR date-keyed dict-of-lists in MTI state.
    if not isinstance(st_data, dict):
        return []
    priority_keys = (
        "input_logs", "logs", "survey_logs", "onboard_logs",
        "events", "event_log", "event_logs", "daily_logs", "ops_logs", "activity_logs"
    )
    collected = []
    seen_sigs = set()

    def _add_item(item, parent_dt=""):
        if not isinstance(item, dict):
            return
        d_copy = dict(item)
        if parent_dt and not any(d_copy.get(k) for k in ("log_date", "event_date", "date", "dpr_date")):
            d_copy["log_date"] = parent_dt
        sig = repr(sorted((str(ik), str(iv)) for ik, iv in d_copy.items()))
        if sig not in seen_sigs:
            seen_sigs.add(sig)
            collected.append(d_copy)

    for k in priority_keys:
        val = st_data.get(k)
        if isinstance(val, list):
            for item in val:
                _add_item(item)
        elif isinstance(val, dict):
            for sub_k, sub_v in val.items():
                p_dt = norm_mti_date(sub_k)
                if isinstance(sub_v, list):
                    for item in sub_v:
                        _add_item(item, p_dt)
                elif isinstance(sub_v, dict):
                    _add_item(sub_v, p_dt)

    if not collected:
        skip_keys = {"ledger", "catalog", "custom_catalog", "users", "user_access", "survey_setup"}
        for k, val in st_data.items():
            if k in skip_keys:
                continue
            if isinstance(val, list) and val and isinstance(val[0], dict) and "design_e" not in val[0] and "aslaid_e" not in val[0]:
                for item in val:
                    _add_item(item)
            elif isinstance(val, dict):
                for sub_k, sub_v in val.items():
                    p_dt = norm_mti_date(sub_k)
                    if p_dt and isinstance(sub_v, list):
                        for item in sub_v:
                            _add_item(item, p_dt)
    return collected

def parse_log_entry_fields(lg, default_surveyor="Duty Surveyor"):
    """Normalizes any MTI log dict into (date_iso, time_hm, category, area, clean_desc, env_short, surveyor)."""
    dt_found = ""
    tm_found = ""
    date_keys = ("log_date", "event_date", "date", "dpr_date", "timestamp", "datetime", "dt", "created_at", "logged_at", "install_date", "time")
    time_keys = ("log_time", "event_time", "time", "start_time", "hm", "hrs", "timestamp", "datetime", "dt", "created_at", "logged_at")

    for dk in date_keys:
        if lg.get(dk):
            d = norm_mti_date(lg.get(dk))
            if d:
                dt_found = d
                break
    for tk in time_keys:
        val = str(lg.get(tk) or "").strip()
        m_t = re.search(r"(?:^|\s|T)(\d{1,2}:\d{2})(?::\d{2})?", val)
        if m_t:
            hh, mm = [int(x) for x in m_t.group(1).split(":")]
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                tm_found = f"{hh:02d}:{mm:02d}"
                break

    if not dt_found:
        for v in lg.values():
            if isinstance(v, str):
                d = norm_mti_date(v)
                if d:
                    dt_found = d
                    break
    if not tm_found:
        for v in lg.values():
            if isinstance(v, str):
                m_t = re.search(r"(?:^|\s|T)(\d{1,2}:\d{2})", v)
                if m_t:
                    hh, mm = [int(x) for x in m_t.group(1).split(":")]
                    if 0 <= hh <= 23 and 0 <= mm <= 59:
                        tm_found = f"{hh:02d}:{mm:02d}"
                        break

    cat_s = str(
        lg.get("category") or lg.get("log_type") or lg.get("event_type") or
        lg.get("type") or lg.get("activity_type") or lg.get("phase") or "Ops"
    ).strip()

    area_s = str(
        lg.get("crossing_id") or lg.get("crossing") or lg.get("area") or
        lg.get("location") or lg.get("asset") or lg.get("vessel") or lg.get("target") or "MMA Prestige"
    ).strip()

    primary_parts = []
    for pk in ("event", "activity", "title", "description", "summary", "message", "log_text"):
        pv = str(lg.get(pk) or "").strip()
        if pv and pv not in primary_parts:
            primary_parts.append(pv)
    for sk in ("details", "notes", "note", "remarks", "comment", "sub_text", "operational_notes"):
        sv = str(lg.get(sk) or "").strip()
        if sv and all(sv not in p for p in primary_parts):
            primary_parts.append(sv)
    if not primary_parts:
        skip_meta = {
            "id", "date", "log_date", "event_date", "dpr_date", "time", "log_time", "event_time",
            "timestamp", "datetime", "dt", "created_at", "logged_at", "category", "log_type",
            "event_type", "type", "activity_type", "phase", "crossing_id", "crossing", "area",
            "location", "asset", "vessel", "target", "wind", "env_wind", "wind_kt", "wind_speed",
            "current", "curr", "env_current", "current_ms", "curr_kt", "usbl", "usbl_sensor",
            "surveyor", "surveyor_name", "logged_by", "user_name", "username", "user", "author"
        }
        for fk, fv in lg.items():
            if str(fk).lower() not in skip_meta and isinstance(fv, str) and fv.strip():
                primary_parts.append(fv.strip())
    raw_combined = " | ".join(primary_parts) if primary_parts else "-"

    w_val = str(lg.get("wind") or lg.get("env_wind") or lg.get("wind_kt") or lg.get("wind_speed") or "").strip()
    c_val = str(lg.get("current") or lg.get("curr") or lg.get("env_current") or lg.get("current_ms") or lg.get("curr_kt") or "").strip()
    m_env = re.search(r"\[([^\]]*(?:Wind|Curr|USBL)[^\]]*)\]", raw_combined, re.I)
    env_tag = m_env.group(1) if m_env else ""
    clean_desc = re.sub(r"\s*\[[^\]]*(?:Wind|Curr|USBL)[^\]]*\]", "", raw_combined).strip(" |") or "-"

    if env_tag:
        raw_et = re.sub(r"USBL:[^|]+\|\s*", "", env_tag, flags=re.I).strip()
        et_parts = []
        for ep in [x.strip() for x in raw_et.split("|") if x.strip()]:
            mp = re.match(r"^(Wind(?:\s+Speed)?|W|Curr(?:ent)?|C)\s*:\s*(.*)$", ep, re.I)
            if mp:
                kl = "W" if mp.group(1).lower().startswith("w") else "C"
                vf = fmt_knots(mp.group(2))
                if vf:
                    et_parts.append(f"{kl}:{vf}")
            else:
                et_parts.append(ep)
        env_short = " | ".join(et_parts) if et_parts else "-"
    elif w_val or c_val:
        wf, cf = fmt_knots(w_val), fmt_knots(c_val)
        w_str = f"W:{wf}" if wf else ""
        c_str = f"C:{cf}" if cf else ""
        env_short = " | ".join([x for x in (w_str, c_str) if x]) or "-"
    else:
        env_short = "-"

    surv_l = str(
        lg.get("surveyor_name") or lg.get("surveyor") or lg.get("logged_by") or
        lg.get("user_name") or lg.get("username") or lg.get("user") or lg.get("author") or default_surveyor
    ).strip()

    return dt_found, (tm_found or "00:00"), cat_s, area_s, clean_desc, env_short, surv_l

def build_structured_report_markdown(metrics, include_history=False, ledger_list=None, scale_p1=250, scale_p2=75):
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
    w_rep = fmt_knots(metrics.get("env_wind"))
    c_rep = fmt_knots(metrics.get("env_current"))
    if w_rep:
        env_parts.append(f"Wind Speed {w_rep}")
    if c_rep:
        env_parts.append(f"Current {c_rep}")
    env_line = ", ".join(env_parts) if env_parts else "Not recorded"
    raw_rem = format_remarks_knots(str(metrics.get("remarks") or "").strip())

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
    return chr(10).join(lines)

def render_a4_landscape_figures(metrics, custom_report_md=None, ledger_list=None):
    md_text = custom_report_md if custom_report_md else build_structured_report_markdown(metrics, True, ledger_list)
    filtered_lines = [
        ln for ln in str(md_text).splitlines()
        if "chart scales @ a3" not in ln.strip().lower() and "chart scales:" not in ln.strip().lower()
    ]

    W_MM, H_MM = 297.0, 210.0
    loc_id, mat_id = metrics.get("location_id", "CR-A1_M15"), metrics.get("mattress_id", "#A046")
    xing_id = metrics.get("crossing_id") or loc_id
    act_grp = normalize_crossing_group(xing_id) or normalize_crossing_group(loc_id)
    act_col = get_crossing_group_color(act_grp, default="#1e293b", dark_bg=False)
    act_hdr_col = get_crossing_group_color(act_grp, default="#38bdf8", dark_bg=True)
    surv_name = metrics.get("surveyor_name", "Duty Surveyor")

    def _new_a4_landscape_page(page_num):
        fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4), dpi=150, facecolor="white")
        ax = fig.add_axes([0, 0, 1, 1], frameon=False)
        ax.set_xlim(0, W_MM); ax.set_ylim(0, H_MM); ax.set_xticks([]); ax.set_yticks([])
        ax.add_patch(mpatches.Rectangle((10, 10), 277, 190, fill=False, edgecolor="#0f172a", linewidth=1.4))
        ax.add_patch(mpatches.Rectangle((10, 186.5), 277, 13.5, facecolor="#0f172a", edgecolor="#0f172a"))
        ax.text(14, 195.2, f"SUBSEA MATTRESS VERIFICATION REPORT  |  {loc_id} ({mat_id})", color="white", fontsize=10.8, fontweight="bold", va="center")
        if act_grp:
            ax.text(283, 195.2, f"CROSSING GROUP: {act_grp}", color=act_hdr_col, fontsize=9.2, fontweight="bold", va="center", ha="right")
        ax.text(14, 189.6, f"File: {metrics.get('base_filename','')}.pdf  |  Active USBL: {metrics.get('usbl_sensor','Survey Pole')}  |  {metrics.get('verdict','')}", color=act_hdr_col, fontsize=8.2, fontweight="bold", va="center")
        ax.plot([10, 287], [16.0, 16.0], color="#cbd5e1", linewidth=0.8)
        ax.text(14, 12.2, f"DP2 MMA Prestige | Placement Date/Time: {metrics.get('install_date','')} | Surveyor: {surv_name}", fontsize=8.0, color="#475569", fontweight="bold")
        ax.text(283, 12.2, f"Verification Report | Page {page_num}", fontsize=8.0, color="#475569", ha="right")
        return fig, ax

    figs = []
    page_no = 1
    fig, ax = _new_a4_landscape_page(page_no)
    figs.append(fig)
    y_cur = 180.5

    idx_ln = 0
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
            continue
        if y_cur < 19.5:
            page_no += 1
            fig, ax = _new_a4_landscape_page(page_no)
            figs.append(fig)
            y_cur = 180.5
        if not line:
            y_cur -= 1.6
            continue
        if line.startswith("# "):
            ax.text(14, y_cur, line[2:], fontsize=10.8, fontweight="bold", color=act_col)
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
            if n_c == 5:
                xs = [14.0, 74.0, 128.0, 182.0, 236.0]
            elif n_c == 8:
                xs = [14.0, 28.0, 66.0, 96.0, 118.0, 149.0, 181.0, 204.0]
            else:
                xs = [14.0 + i * (268.0 / n_c) for i in range(n_c)]
            is_hdr = ("Parameter" in cells[0] or "Unit #" in cells[0] or "LOCATION" in cells[0].upper())
            row_x_col = "" if is_hdr else get_crossing_group_color(line, default="")
            for ic, c_txt in enumerate(cells):
                if is_hdr:
                    c_use, fw_use = "#0f172a", "bold"
                elif row_x_col:
                    c_use = row_x_col
                    fw_use = "bold" if ic in (0, 2) else "normal"
                elif n_c == 5 and ic == 3:
                    c_use, fw_use = act_col, "bold"
                elif n_c == 5 and ic == 4:
                    u_txt = c_txt.upper()
                    c_use = "#15803d" if "PASS" in u_txt else ("#b91c1c" if "EXCEEDS" in u_txt else "#1e293b")
                    fw_use = "bold" if ("PASS" in u_txt or "EXCEEDS" in u_txt) else "normal"
                else:
                    c_use, fw_use = "#1e293b", "normal"
                max_ch = 44 if (n_c == 8 and ic == 7) else 36
                ax.text(xs[ic], y_cur, c_txt[:max_ch], fontsize=7.8, fontweight=fw_use, family="monospace", color=c_use)
            y_cur -= 4.0
        else:
            cl = line.replace("**", "")
            is_verdict_ln = cl.startswith("Verdict:")
            is_corner_ln = bool(re.match(r"^-\s*C[1-4]\s*\(", cl))
            ln_x_col = act_col if (is_verdict_ln or is_corner_ln) else get_crossing_group_color(cl, default="#1e293b")
            fw_ln = "bold" if is_verdict_ln else "normal"
            ax.text(14, y_cur, cl[:145], fontsize=8.8, fontweight=fw_ln, color=ln_x_col)
            if len(cl) > 145:
                y_cur -= 4.0
                ax.text(18, y_cur, cl[145:290], fontsize=8.8, fontweight=fw_ln, color=ln_x_col)
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
    """
    Generates a Landscape Daily Progress Report (DPR) PDF for MTI Operations covering 00:00 to 23:59 hrs
    of target_date_str, with YYYYMMDD filename, universal log extraction, and signature lines removed.
    """
    os.makedirs(workspace_dir, exist_ok=True)
    ledger = list((st_data or {}).get("ledger") or [])
    raw_logs = extract_all_mti_logs(st_data)
    parsed_logs = [parse_log_entry_fields(lg, surveyor_name) for lg in raw_logs]

    def _extract_time(s):
        m = re.search(r"(\d{2}:\d{2})", str(s or ""))
        return m.group(1) if m else "00:00"

    dt_iso = norm_mti_date(target_date_str)
    if not dt_iso:
        all_dates = [d for (d, _, _, _, _, _, _) in parsed_logs if d]
        for r in ledger:
            d = norm_mti_date(r.get("install_date"))
            if d:
                all_dates.append(d)
        dt_iso = max(all_dates) if all_dates else datetime.utcnow().strftime("%Y-%m-%d")

    prior_fixes = [r for r in ledger if (norm_mti_date(r.get("install_date")) or "9999") < dt_iso]
    day_fixes = [r for r in ledger if norm_mti_date(r.get("install_date")) == dt_iso]
    day_fixes.sort(key=lambda r: _extract_time(r.get("install_date")))
    cum_fixes = [r for r in ledger if (norm_mti_date(r.get("install_date")) or "0000") <= dt_iso]

    day_logs = [item for item in parsed_logs if item[0] == dt_iso]
    day_logs.sort(key=lambda item: item[1])

    W_MM, H_MM = 297.0, 210.0

    def _new_dpr_page(page_num):
        fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4), dpi=150, facecolor="white")
        ax = fig.add_axes([0, 0, 1, 1], frameon=False)
        ax.set_xlim(0, W_MM); ax.set_ylim(0, H_MM); ax.set_xticks([]); ax.set_yticks([])
        ax.add_patch(mpatches.Rectangle((10, 10), 277, 190, fill=False, edgecolor="#0f172a", linewidth=1.4))
        ax.add_patch(mpatches.Rectangle((10, 185.5), 277, 14.5, facecolor="#0f172a", edgecolor="#0f172a"))
        ax.text(14, 194.8, "SUBSEA MATTRESS & ROCK BAG INSTALLATION (MTI) - DAILY PROGRESS REPORT (DPR)", color="white", fontsize=10.2, fontweight="bold", va="center")
        ax.text(14, 188.8, f"Reporting Period: {dt_iso} (00:00 to 23:59 hrs)  |  Vessel: DP2 MMA Prestige  |  Client: TPC  |  Contractor: NMDC", color="#38bdf8", fontsize=8.2, fontweight="bold", va="center")
        ax.plot([10, 287], [15.5, 15.5], color="#cbd5e1", linewidth=0.8)
        ax.text(14, 12.0, f"Tung-Hsiao 2nd Stage Subsea Gas Pipeline Project  |  Duty Surveyor: {surveyor_name}", fontsize=7.8, color="#475569", fontweight="bold")
        ax.text(283, 12.0, f"MTI DPR ({dt_iso} | 00:00-23:59) | Page {page_num}", fontsize=7.8, color="#475569", ha="right")
        return fig, ax

    figs = []
    p_no = 1
    fig, ax = _new_dpr_page(p_no)
    figs.append(fig)
    y = 180.0

    # --- EXECUTIVE TAKEAWAY LINE (Audience-First Signal Before Tables) ---
    latest_status = day_logs[-1][4][:78] if day_logs else ("Installation active" if day_fixes else "No field events logged")
    pct_done = (len(cum_fixes) * 100.0) / 139.0
    exec_line = f"DAILY TAKEAWAY: +{len(day_fixes)} Laid Today ({len(cum_fixes)}/139 Cumul, {pct_done:.1f}%)  |  {len(day_logs)} Log Event(s)  |  Latest Status: {latest_status}"
    ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.8, facecolor="#f0f9ff", edgecolor="#0284c7", linewidth=0.6))
    ax.text(15, y + 1.1, exec_line[:135], fontsize=7.8, fontweight="bold", color="#0f172a", va="center")
    y -= 6.0

    # --- SECTION 1: INSTALLATION PROGRESS OF CONCRETE MATTRESS 0001-2400 ---
    prog_rows_dpr, prog_tot_dpr, _ = compute_historical_progress_rows(ledger, f"{dt_iso} 23:59:59", current_metrics=None, full_day=True)
    y = draw_mattress_progress_box(ax, y + 2.2, prog_rows_dpr, prog_tot_dpr, title_str="INSTALLATION PROGRESS OF CONCRETE MATTRESS 0001-2400")

    # --- SECTION 2: MATTRESSES PLACED ON TARGET DATE (00:00 - 23:59) ---
    ax.add_patch(mpatches.Rectangle((13, y - 1.4), 271, 5.0, facecolor="#0f172a", edgecolor="none"))
    ax.text(15, y + 1.1, f"2. MATTRESSES PLACED ON {dt_iso} (00:00 TO 23:59 HRS)", fontsize=8.8, fontweight="bold", color="white", va="center")
    y -= 5.6

    if not day_fixes:
        ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.6, facecolor="#f8fafc", edgecolor="#cbd5e1", linewidth=0.5))
        ax.text(15, y + 1.0, f"No mattress installations recorded between 00:00 and 23:59 hrs on {dt_iso}.", fontsize=8.0, color="#64748b", va="center")
        y -= 6.5
    else:
        f_cols = [
            (13.0, 25.0, "Unit #"), (25.0, 40.0, "Time"), (40.0, 62.0, "Crossing"),
            (62.0, 88.0, "Box ID"), (88.0, 108.0, "Tag ID"), (108.0, 138.0, "As-Laid E"),
            (138.0, 170.0, "As-Laid N"), (170.0, 190.0, "Brg"), (190.0, 212.0, "dCL (m)"),
            (212.0, 284.0, "Corner Gaps / Verdict")
        ]
        ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.4, facecolor="#e2e8f0", edgecolor="#94a3b8", linewidth=0.5))
        for x0, x1, h_lbl in f_cols:
            ax.text(x0 + 1.5, y + 0.9, h_lbl, fontsize=7.4, fontweight="bold", color="#0f172a", va="center")
        y -= 4.4
        for idx_f, r in enumerate(day_fixes):
            if y < 19.5:
                p_no += 1; fig, ax = _new_dpr_page(p_no); figs.append(fig); y = 180.0
            bg_c = "#f8fafc" if idx_f % 2 == 0 else "#ffffff"
            ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.2, facecolor=bg_c, edgecolor="#cbd5e1", linewidth=0.4))
            t_hm = _extract_time(r.get("install_date"))
            vals_f = [
                f"#{r.get('unit_no','')}", t_hm, str(r.get("crossing_id") or "")[:10],
                str(r.get("design_box_id") or "")[:12], str(r.get("physical_tag") or "")[:8],
                f"{float(r.get('aslaid_e') or 0):.3f}", f"{float(r.get('aslaid_n') or 0):.3f}",
                f"{float(r.get('heading_deg') or 0):.1f} deg", f"{float(r.get('cl_offset_m') or 0):.2f} m",
                f"{r.get('gap_labels','1st Unit')} | {r.get('status','Completed')}"[:40]
            ]
            fx_col = get_crossing_group_color(r.get("crossing_id") or r.get("design_box_id"), default="#1e293b")
            for idx_fc, ((x0, x1, _), v_str) in enumerate(zip(f_cols, vals_f)):
                ax.text(x0 + 1.5, y + 0.8, v_str, fontsize=7.4, fontweight="bold" if idx_fc in (2, 3) else "normal", color=fx_col, family="monospace", va="center")
            y -= 4.2
        y -= 2.5

    # --- SECTION 3: CHRONOLOGICAL ONBOARD SURVEY EVENT LOG (00:00 - 23:59) ---
    if y < 28.0:
        p_no += 1; fig, ax = _new_dpr_page(p_no); figs.append(fig); y = 180.0
    ax.add_patch(mpatches.Rectangle((13, y - 1.4), 271, 5.0, facecolor="#0f172a", edgecolor="none"))
    ax.text(15, y + 1.1, f"3. CHRONOLOGICAL ONBOARD SURVEY EVENT LOG ({dt_iso} | 00:00 TO 23:59 HRS)", fontsize=8.8, fontweight="bold", color="white", va="center")
    y -= 5.6

    if not day_logs:
        ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.6, facecolor="#f8fafc", edgecolor="#cbd5e1", linewidth=0.5))
        ax.text(15, y + 1.0, f"No survey events logged between 00:00 and 23:59 hrs on {dt_iso}.", fontsize=8.0, color="#64748b", va="center")
        y -= 6.0
    else:
        l_cols = [
            (13.0, 27.0, "Time"), (27.0, 62.0, "Category"), (62.0, 92.0, "Asset / Area"),
            (92.0, 204.0, "Operational Event & Remarks"), (204.0, 252.0, "Wind / Curr (knots)"), (252.0, 284.0, "Surveyor")
        ]
        ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.4, facecolor="#e2e8f0", edgecolor="#94a3b8", linewidth=0.5))
        for x0, x1, h_lbl in l_cols:
            ax.text(x0 + 1.5, y + 0.9, h_lbl, fontsize=7.4, fontweight="bold", color="#0f172a", va="center")
        y -= 4.4

        for idx_l, (_, t_hm, cat_s, area_s, clean_desc, env_short, surv_l) in enumerate(day_logs):
            wrapped_lines = textwrap.wrap(clean_desc, width=62) or ["-"]
            env_lines = [x.strip() for x in env_short.split("|")] if len(env_short) > 26 and "|" in env_short else [env_short[:30]]
            n_row_ln = max(len(wrapped_lines), len(env_lines))
            row_h = max(4.2, n_row_ln * 3.6 + 0.8)

            if y - row_h + 3.0 < 17.0:
                p_no += 1; fig, ax = _new_dpr_page(p_no); figs.append(fig); y = 180.0
                ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.4, facecolor="#e2e8f0", edgecolor="#94a3b8", linewidth=0.5))
                for x0, x1, h_lbl in l_cols:
                    ax.text(x0 + 1.5, y + 0.9, h_lbl, fontsize=7.4, fontweight="bold", color="#0f172a", va="center")
                y -= 4.4

            bg_c = "#f8fafc" if idx_l % 2 == 0 else "#ffffff"
            ax.add_patch(mpatches.Rectangle((13, y - row_h + 3.0), 271, row_h, facecolor=bg_c, edgecolor="#cbd5e1", linewidth=0.4))

            ax.text(14.5, y + 0.7, t_hm, fontsize=7.5, fontweight="bold", color="#0369a1", family="monospace", va="center")
            ax.text(28.5, y + 0.7, cat_s[:18], fontsize=7.4, fontweight="bold", color="#0f172a", va="center")
            lg_x_col = get_crossing_group_color(area_s, default="") or get_crossing_group_color(clean_desc, default="")
            ax.text(63.5, y + 0.7, area_s[:15], fontsize=7.4, fontweight="bold" if lg_x_col else "normal", color=lg_x_col or "#334155", family="monospace", va="center")
            for w_idx, w_ln in enumerate(wrapped_lines):
                ax.text(93.5, y + 0.7 - w_idx * 3.5, w_ln, fontsize=7.5, color=lg_x_col or "#1e293b", va="center")
            for e_idx, e_ln in enumerate(env_lines):
                ax.text(205.5, y + 0.7 - e_idx * 3.5, e_ln, fontsize=6.7, color="#0369a1", family="monospace", va="center")
            ax.text(253.5, y + 0.7, surv_l[:16], fontsize=7.3, color="#475569", va="center")
            y -= row_h

    buf = io.BytesIO()
    with PdfPages(buf) as pdf_pages:
        for f in figs:
            pdf_pages.savefig(f, dpi=150)
            f.clf(); plt.close(f)
    plt.close('all'); gc.collect()
    pdf_bytes = buf.getvalue()
    yyyymmdd = dt_iso.replace("-", "")
    fn_out = f"{yyyymmdd}_MTI_Daily_Progress_Report.pdf"
    open(os.path.join(workspace_dir, fn_out), "wb").write(pdf_bytes)
    return pdf_bytes, fn_out, dt_iso

def _xml_esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

def generate_editable_docx(metrics, report_md, workspace_dir="workspace"):
    os.makedirs(workspace_dir, exist_ok=True)
    act_hex = get_crossing_group_color(metrics.get("crossing_id") or metrics.get("location_id"), default="#1e293b").lstrip("#").upper()
    p_list = []
    for raw_l in str(report_md or "").splitlines():
        line = raw_l.strip()
        if not line or ":---" in line or "chart scales @ a3" in line.lower():
            continue
        txt = _xml_esc(re.sub(r"^#+\s*", "", line).replace("**", ""))
        if line.startswith("#"):
            p_list.append(f'<w:p><w:r><w:rPr><w:b/><w:color w:val="0F172A"/><w:sz w:val="28"/></w:rPr><w:t>{txt}</w:t></w:r></w:p>')
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            is_hdr = ("Parameter" in cells[0] or "Unit #" in cells[0] or "LOCATION" in cells[0].upper())
            r_hex = "0F172A" if is_hdr else get_crossing_group_color(line, default="#1E293B").lstrip("#").upper()
            b_tag = "<w:b/>" if is_hdr else ""
            row_t = _xml_esc("  |  ".join(cells))
            p_list.append(f'<w:p><w:r><w:rPr>{b_tag}<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/><w:color w:val="{r_hex}"/><w:sz w:val="21"/></w:rPr><w:t>{row_t}</w:t></w:r></w:p>')
        else:
            is_act = txt.startswith("Verdict:") or bool(re.match(r"^-\s*C[1-4]\s*\(", txt))
            l_hex = act_hex if is_act else get_crossing_group_color(line, default="#1E293B").lstrip("#").upper()
            b_tag = "<w:b/>" if txt.startswith("Verdict:") else ""
            p_list.append(f'<w:p><w:r><w:rPr>{b_tag}<w:color w:val="{l_hex}"/><w:sz w:val="23"/></w:rPr><w:t>{txt}</w:t></w:r></w:p>')

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
