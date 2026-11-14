import os, io, re, gc, json, zipfile, textwrap
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from mti_4panel_math import fmt_knots, format_remarks_knots

try:
    from mti_4panel_math import resolve_full_surveyor_name
except Exception:
    resolve_full_surveyor_name = lambda s: str(s or "").strip()

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

CONSOLIDATED_CROSSING_SCOPES = [
    ("C-A1", 27),
    ("C-B1", 27),
    ("C-A2", 7),
    ("C-B2", 7),
    ("C-A3", 36),
    ("C-B3", 35),
]

CROSSING_SCOPES = [
    ("CR-A1_L1", 25), ("CR-A1_L2", 2), ("CR-A2", 7), ("CR-A3", 36),
    ("CR-B1_L1", 25), ("CR-B1_L2", 2), ("CR-B2", 7), ("CR-B3", 35),
]

def normalize_crossing_group(val):
    s = str(val or "").strip().upper()
    if not s:
        return ""
    m = re.search(
        r"(?<![#A-Z0-9])(?:CR[-_\s]?([AB][123])|C[-_\s]?([AB][123])|CROSSING\s+([AB][123])|([AB][123])[-_]?(?:L[12]\b|M\d+))(?:\b|[_-]|M\d|$)",
        s,
    )
    if m:
        code = m.group(1) or m.group(2) or m.group(3) or m.group(4)
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

def _strip_redundant_verdict_prefix(line):
    s = str(line or "")
    s2 = re.sub(r"^\s*(?:\*\*)?Verdict\s*:(?:\*\*)?\s*.*?\s*--\s*", "", s, flags=re.I)
    if re.match(r"^\s*(?:\*\*)?Verdict\s*:(?:\*\*)?\s*", s2, flags=re.I) and "--" not in s2:
        return ""
    return s2

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
    months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    m4 = re.search(r"([A-Za-z]{3})[a-z]*[\s,-]+(\d{1,2})[\s,-]+(\d{4})", s)
    if m4 and m4.group(1).lower() in months:
        return f"{int(m4.group(3)):04d}-{months[m4.group(1).lower()]:02d}-{int(m4.group(2)):02d}"
    m5 = re.search(r"(\d{1,2})[\s,-]+([A-Za-z]{3})[a-z]*[\s,-]+(\d{4})", s)
    if m5 and m5.group(2).lower() in months:
        return f"{int(m5.group(3)):04d}-{months[m5.group(2).lower()]:02d}-{int(m5.group(1)):02d}"
    return ""

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

def _format_unit_gaps_clean(val_or_row):
    if isinstance(val_or_row, dict):
        r = val_or_row
        if r.get("is_first_in_array"):
            return "1st Unit (N/A)"
        raw = str(r.get("gap_labels") or "").strip()
        if not raw:
            q_parts = []
            for q in ("nw", "ne", "sw", "se"):
                qv = str(r.get(f"gap_{q}") or "").strip()
                if qv:
                    sfx = "" if qv.lower().endswith("m") else "m"
                    q_parts.append(f"{q.upper()}:{qv}{sfx}")
            if q_parts:
                raw = ", ".join(q_parts)
            else:
                g1, g2 = float(r.get("gap1_m") or 0.0), float(r.get("gap2_m") or 0.0)
                raw = f"G1:{g1:.2f}m, G2:{g2:.2f}m" if (g1 > 0 or g2 > 0) else "N/A"
    else:
        raw = str(val_or_row or "").strip()
    if not raw:
        return "N/A"
    return ", ".join(p.strip() for p in raw.split("|") if p.strip()) or "N/A"

def _format_aligned_md_table(headers, rows, right_cols=()):
    all_r = [list(map(str, headers))] + [[str(c) for c in r] for r in rows]
    n_c = len(headers)
    widths = [max(len(r[i]) if i < len(r) else 0 for r in all_r) for i in range(n_c)]
    widths = [max(w, 4) for w in widths]

    def _fmt_row(cells):
        parts = []
        for i in range(n_c):
            val = cells[i] if i < len(cells) else ""
            parts.append(val.rjust(widths[i]) if i in right_cols else val.ljust(widths[i]))
        return "| " + " | ".join(parts) + " |"

    sep = "| " + " | ".join(
        (":" + "-" * (widths[i] - 1)) if i not in right_cols else ("-" * (widths[i] - 1) + ":")
        for i in range(n_c)
    ) + " |"
    out = [_fmt_row(all_r[0]), sep]
    for r in all_r[1:]:
        out.append(_fmt_row(r))
    return out

def _split_md_pipe_row(line):
    s = str(line or "").strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]

def _detect_md_table_kind(header_cells):
    c0 = str(header_cells[0] if header_cells else "").strip().lower()
    if "parameter" in c0:
        return "geodetic"
    if "unit" in c0:
        has_xing = len(header_cells) > 2 and "crossing" in str(header_cells[2]).strip().lower()
        return "placed_units_9" if has_xing else "placed_units_8"
    if "location" in c0 or "crossing id" in c0:
        return "progress"
    return "generic"

def _normalize_md_table_cells(raw_cells, kind, expected_cols=None):
    cells = [str(c).strip() for c in (raw_cells or [])]
    if kind == "placed_units_9":
        if len(cells) > 9:
            merged_gaps = ", ".join(x for x in cells[8:] if x) or "N/A"
            cells = cells[:8] + [merged_gaps]
        elif len(cells) < 9:
            cells = cells + [""] * (9 - len(cells))
        if not cells[8]:
            cells[8] = "N/A"
        return cells[:9]
    if kind == "placed_units_8":
        if len(cells) > 8:
            merged_gaps = ", ".join(x for x in cells[7:] if x) or "N/A"
            cells = cells[:7] + [merged_gaps]
        elif len(cells) < 8:
            cells = cells + [""] * (8 - len(cells))
        if not cells[7]:
            cells[7] = "N/A"
        return cells[:8]
    if kind == "geodetic":
        if len(cells) > 5:
            mid_rov = ", ".join(x for x in cells[3:-1] if x) or "-"
            cells = cells[:3] + [mid_rov, cells[-1]]
        elif len(cells) < 5:
            cells = cells + [""] * (5 - len(cells))
        return cells[:5]
    if kind == "progress":
        if len(cells) < 6:
            cells = cells + ["0"] * (6 - len(cells))
        return cells[:6]
    n_exp = expected_cols or len(cells) or 1
    if len(cells) > n_exp:
        cells = cells[: n_exp - 1] + [", ".join(x for x in cells[n_exp - 1 :] if x)]
    elif len(cells) < n_exp:
        cells = cells + [""] * (n_exp - len(cells))
    return cells

def _resolve_ledger_for_report(ledger_list=None):
    if ledger_list is not None:
        return list(ledger_list)
    try:
        from flask import has_app_context
        if has_app_context():
            import mti_blueprint as _mb
            return list((_mb.load_mti_state() or {}).get("ledger") or [])
    except Exception:
        pass
    try:
        sf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mti_state.json")
        if os.path.exists(sf):
            with open(sf, "r", encoding="utf-8") as f:
                st = json.load(f)
            if isinstance(st, dict) and isinstance(st.get("ledger"), list):
                return list(st["ledger"])
    except Exception:
        pass
    try:
        import mti_blueprint as _mb
        return list(getattr(_mb, "PRELOADED_MTI_LEDGER", []) or [])
    except Exception:
        return []

def _collect_placed_mattresses_up_to_cutoff(ledger_list, cutoff_dt_str, current_metrics=None, full_day=False):
    rows_in = [dict(r) for r in _resolve_ledger_for_report(ledger_list)]
    eff_cutoff = str(cutoff_dt_str or "").strip()
    if not eff_cutoff and isinstance(current_metrics, dict):
        eff_cutoff = str(current_metrics.get("install_date") or "").strip()

    ref_d, ref_t = _parse_fix_dt_tuple(eff_cutoff)
    if not ref_d:
        all_ds = [_parse_fix_dt_tuple(r.get("install_date"))[0] for r in rows_in]
        all_ds = [d for d in all_ds if d]
        ref_d = max(all_ds) if all_ds else datetime.utcnow().strftime("%Y-%m-%d")
    if full_day or not re.search(r"\d{1,2}:\d{2}", eff_cutoff):
        ref_t = "23:59:59"

    cur_uno = None
    cur_box = ""
    if isinstance(current_metrics, dict) and current_metrics.get("location_id"):
        cur_box = str(current_metrics.get("location_id") or "").strip().upper()
        try:
            cur_uno = int(float(current_metrics.get("unit_no") or 0)) or None
        except Exception:
            cur_uno = None
        matched_cur = False
        for r in rows_in:
            if cur_box and str(r.get("design_box_id") or "").strip().upper() == cur_box:
                if current_metrics.get("install_date"):
                    r["install_date"] = current_metrics["install_date"]
                if current_metrics.get("crossing_id"):
                    r["crossing_id"] = current_metrics["crossing_id"]
                if current_metrics.get("mattress_id"):
                    r["physical_tag"] = current_metrics["mattress_id"]
                if current_metrics.get("aslaid_e") is not None:
                    r["aslaid_e"] = current_metrics["aslaid_e"]
                if current_metrics.get("aslaid_n") is not None:
                    r["aslaid_n"] = current_metrics["aslaid_n"]
                if current_metrics.get("cl_offset_m") is not None:
                    r["cl_offset_m"] = current_metrics["cl_offset_m"]
                if current_metrics.get("gap_labels"):
                    r["gap_labels"] = current_metrics["gap_labels"]
                if "is_first_in_array" in current_metrics:
                    r["is_first_in_array"] = bool(current_metrics["is_first_in_array"])
                if current_metrics.get("status"):
                    r["status"] = current_metrics["status"]
                matched_cur = True
                break
        if cur_box and not matched_cur:
            rows_in.append({
                "unit_no": cur_uno or (max([int(float(x.get("unit_no") or 0)) for x in rows_in] + [0]) + 1),
                "crossing_id": current_metrics.get("crossing_id") or cur_box,
                "design_box_id": cur_box,
                "physical_tag": current_metrics.get("mattress_id") or "-",
                "install_date": current_metrics.get("install_date") or f"{ref_d} {ref_t[:5]}",
                "aslaid_e": current_metrics.get("aslaid_e") or 0.0,
                "aslaid_n": current_metrics.get("aslaid_n") or 0.0,
                "cl_offset_m": current_metrics.get("cl_offset_m") or 0.0,
                "gap_labels": current_metrics.get("gap_labels") or "",
                "is_first_in_array": bool(current_metrics.get("is_first_in_array", False)),
                "status": current_metrics.get("status") or "Completed",
                "unit_type": "Concrete Mattress",
            })

    valid_up_to_cutoff = []
    for r in rows_in:
        if str(r.get("unit_type") or "Concrete Mattress").strip() == "Rock Bag":
            continue
        if str(r.get("status") or "Completed").strip().lower() in ("planned", "cancelled", "rejected"):
            continue
        try:
            r_uno = int(float(r.get("unit_no") or 0))
        except Exception:
            r_uno = 0
        rd, rt = _parse_fix_dt_tuple(r.get("install_date"))
        if not rd:
            if full_day or cur_uno is None or r_uno <= cur_uno:
                rd, rt = ref_d, "00:00:00"
            else:
                continue
        r_box = str(r.get("design_box_id") or "").strip().upper()
        if (rd, rt) < (ref_d, ref_t):
            valid_up_to_cutoff.append((rd, r))
        elif (rd, rt) == (ref_d, ref_t):
            if full_day or cur_uno is None or r_uno <= cur_uno or (cur_box and r_box == cur_box):
                valid_up_to_cutoff.append((rd, r))

    valid_up_to_cutoff.sort(key=lambda pair: (int(float(pair[1].get("unit_no") or 9999)), pair[0], str(pair[1].get("install_date") or "")))
    return valid_up_to_cutoff, ref_d

def compute_historical_progress_rows(ledger_list, cutoff_dt_str, current_metrics=None, full_day=False):
    valid_up_to_cutoff, ref_d = _collect_placed_mattresses_up_to_cutoff(
        ledger_list, cutoff_dt_str, current_metrics=current_metrics, full_day=full_day
    )
    out_rows = []
    tot_scope = tot_post = tot_today = tot_cum = tot_rem = 0
    for grp_id, scope_qty in CONSOLIDATED_CROSSING_SCOPES:
        grp_items = [
            (rd, r) for (rd, r) in valid_up_to_cutoff
            if normalize_crossing_group(r.get("crossing_id") or r.get("design_box_id")) == grp_id
        ]
        cum_q = len(grp_items)
        today_q = sum(1 for (rd, _) in grp_items if rd == ref_d)
        post_q = sum(1 for (rd, _) in grp_items if rd < ref_d)
        rem_q = max(0, scope_qty - cum_q)
        out_rows.append((grp_id, scope_qty, post_q, today_q, cum_q, rem_q))
        tot_scope += scope_qty
        tot_post += post_q
        tot_today += today_q
        tot_cum += cum_q
        tot_rem += rem_q

    totals = ("TOTAL", tot_scope, tot_post, tot_today, tot_cum, tot_rem)
    return out_rows, totals, ref_d

def draw_mattress_progress_box(
    ax, y_top, prog_rows, totals_row,
    title_str="INSTALLATION PROGRESS OF CONCRETE MATTRESS 0001-2400",
    active_group="",
):
    x0, w_tot = 13.0, 271.0
    col_edges = [13.0, 58.0, 105.0, 150.0, 193.0, 241.0, 284.0]
    h_title, h_hdr, h_row = 5.2, 10.6, 4.3

    ax.add_patch(mpatches.Rectangle((x0, y_top - h_title), w_tot, h_title, facecolor="#fef08a", edgecolor="#0f172a", linewidth=0.75))
    ax.text(x0 + w_tot / 2.0, y_top - h_title / 2.0, title_str, fontsize=8.4, fontweight="bold", color="#0f172a", ha="center", va="center")
    ul_half = min(w_tot * 0.46, max(58.0, len(title_str) * 1.12))
    cx_title = x0 + w_tot / 2.0
    ax.plot([cx_title - ul_half, cx_title + ul_half], [y_top - h_title + 0.85, y_top - h_title + 0.85], color="#0f172a", linewidth=0.65)
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

    for lbl, sc_q, post_q, tod_q, cum_q, rem_q in list(prog_rows) + [totals_row]:
        is_tot = (lbl == "TOTAL")
        is_act_grp = (not is_tot and active_group and lbl == active_group)
        fc_r = "#e0f2fe" if is_tot else ("#f0f9ff" if is_act_grp else "#ffffff")
        ax.add_patch(mpatches.Rectangle((x0, y - h_row), w_tot, h_row, facecolor=fc_r, edgecolor="#0f172a", linewidth=0.65))
        row_col = "#0f172a" if is_tot else get_crossing_group_color(lbl, default="#0f172a")
        vals_r = [lbl, str(sc_q), str(post_q), str(tod_q), str(cum_q), str(rem_q)]
        for ic, v_txt in enumerate(vals_r):
            cx = 0.5 * (col_edges[ic] + col_edges[ic + 1])
            is_nonzero = (ic > 0 and int(v_txt) > 0)
            fw_cell = "bold" if (is_tot or ic == 0 or is_act_grp or (ic in (2, 3, 4) and is_nonzero)) else "normal"
            al_cell = 1.0 if (is_tot or ic in (0, 1, 5) or is_nonzero) else 0.72
            ax.text(cx, y - h_row / 2.0, v_txt, fontsize=7.6, fontweight=fw_cell, color=row_col, alpha=al_cell, ha="center", va="center")
        y -= h_row

    y_grid_top = y_top - h_title
    for xv in col_edges[1:-1]:
        ax.plot([xv, xv], [y, y_grid_top], color="#0f172a", linewidth=0.6)
    return y - 2.6

def extract_all_mti_logs(st_data):
    if not isinstance(st_data, dict):
        return []
    priority_keys = (
        "input_logs", "logs", "survey_logs", "onboard_logs",
        "events", "event_log", "event_logs", "daily_logs", "ops_logs", "activity_logs",
    )
    collected, seen_sigs = [], set()

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
    dt_found, tm_found = "", ""
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

    area_raw = str(
        lg.get("crossing_id") or lg.get("crossing") or lg.get("ref_id") or lg.get("area") or
        lg.get("location") or lg.get("asset") or lg.get("vessel") or lg.get("target") or "MMA Prestige"
    ).strip()
    area_s = re.sub(r"\s*\[(?:USBL:)?(?:Survey Pole(?:\s+USBL)?|Vessel(?:\s+USBL)?)[^\]]*\]", "", area_raw, flags=re.I).strip() or "MMA Prestige"

    primary_parts = []
    for pk in ("event", "activity", "title", "description", "summary", "message", "log_text", "val1"):
        pv = str(lg.get(pk) or "").strip()
        if pv and pv not in primary_parts:
            primary_parts.append(pv)

    v2 = str(lg.get("val2") or "").strip()
    rem_cand = str(lg.get("remarks") or lg.get("details") or lg.get("notes") or "").strip()
    if v2:
        win_txt = v2.split("Window:", 1)[1].strip() if v2.lower().startswith("window:") else v2
        if win_txt and win_txt not in rem_cand and all(v2 not in p for p in primary_parts):
            primary_parts.append(v2)

    for sk in ("details", "notes", "note", "remarks", "comment", "sub_text", "operational_notes"):
        sv = str(lg.get(sk) or "").strip()
        if not sv:
            continue
        primary_parts = [p for p in primary_parts if p not in sv]
        if all(sv not in p for p in primary_parts):
            primary_parts.append(sv)

    if not primary_parts:
        skip_meta = {
            "id", "date", "log_date", "event_date", "dpr_date", "time", "log_time", "event_time",
            "timestamp", "datetime", "dt", "created_at", "logged_at", "category", "log_type",
            "event_type", "type", "activity_type", "phase", "crossing_id", "crossing", "ref_id",
            "area", "location", "asset", "vessel", "target", "val1", "val2", "wind", "env_wind",
            "wind_kt", "wind_speed", "current", "curr", "env_current", "current_ms", "curr_kt",
            "env_swell", "usbl", "usbl_sensor", "surveyor", "surveyor_name", "logged_by",
            "user_name", "username", "user", "author",
        }
        for fk, fv in lg.items():
            if str(fk).lower() not in skip_meta and isinstance(fv, str) and fv.strip():
                primary_parts.append(fv.strip())
    raw_combined = " | ".join(primary_parts) if primary_parts else "-"

    w_val = str(lg.get("wind") or lg.get("env_wind") or lg.get("wind_kt") or lg.get("wind_speed") or "").strip()
    c_val = str(lg.get("current") or lg.get("curr") or lg.get("env_current") or lg.get("current_ms") or lg.get("curr_kt") or "").strip()
    m_env = re.search(r"\[([^\]]*(?:Wind|Curr|USBL)[^\]]*)\]", raw_combined, re.I)
    env_tag = m_env.group(1) if m_env else ""
    clean_desc = re.sub(r"\s*\[[^\]]*(?:Wind|Curr|USBL)[^\]]*\]", "", raw_combined).strip(" |")
    clean_desc = re.sub(r"^(?:\[(?:Survey Pole(?:\s+USBL)?|Vessel(?:\s+USBL)?)\]\s*)+", "", clean_desc, flags=re.I).strip()
    clean_desc = format_remarks_knots(clean_desc) if clean_desc else "-"

    if env_tag:
        raw_et = re.sub(r"USBL:[^|]+\|?\s*", "", env_tag, flags=re.I).strip(" |")
        et_parts = []
        for ep in [x.strip() for x in raw_et.split("|") if x.strip()]:
            mp = re.match(r"^(Wind(?:\s+Speed)?|W|Curr(?:ent)?|C)\s*:\s*(.*)$", ep, re.I)
            if mp:
                kl = "W" if mp.group(1).lower().startswith("w") else "C"
                vf = fmt_knots(mp.group(2))
                if vf:
                    et_parts.append(f"{kl}:{vf}")
            elif not ep.lower().startswith("usbl"):
                et_parts.append(ep)
        env_short = " | ".join(et_parts) if et_parts else "-"
    elif w_val or c_val:
        wf, cf = fmt_knots(w_val), fmt_knots(c_val)
        env_short = " | ".join([x for x in (f"W:{wf}" if wf else "", f"C:{cf}" if cf else "") if x]) or "-"
    else:
        env_short = "-"

    surv_raw = str(
        lg.get("surveyor_name") or lg.get("surveyor") or lg.get("logged_by") or
        lg.get("user_name") or lg.get("username") or lg.get("user") or lg.get("author") or default_surveyor
    ).strip()
    surv_l = resolve_full_surveyor_name(surv_raw) or surv_raw
    return dt_found, (tm_found or "00:00"), cat_s, area_s, clean_desc, env_short, surv_l

def build_structured_report_markdown(metrics, include_history=True, ledger_list=None, scale_p1=250, scale_p2=75):
    resolved_ledger = _resolve_ledger_for_report(ledger_list)
    loc_id = metrics.get("location_id", "CR-A1_M15")
    xing_id = metrics.get("crossing_id", "CR-A1_L1")
    act_grp = normalize_crossing_group(xing_id) or normalize_crossing_group(loc_id)
    cl_off, cl_tol = float(metrics.get("cl_offset_m", 0.0)), float(metrics.get("cl_tol", 0.50))
    max_g, g_tol = float(metrics.get("max_gap_m", 0.0)), float(metrics.get("gap_tol", 0.50))
    is_first = bool(metrics.get("is_first_in_array", False))
    c_enz = metrics.get("corners_enz") or [[0, 0, 0]] * 4
    gaps = metrics.get("gaps") or {}
    cl_st = "PASS" if cl_off <= cl_tol else "EXCEEDS TOLERANCE"
    gap_st = "N/A (1st Unit)" if is_first else ("PASS" if max_g <= g_tol else "EXCEEDS TOLERANCE")

    env_parts = []
    w_rep, c_rep = fmt_knots(metrics.get("env_wind")), fmt_knots(metrics.get("env_current"))
    if w_rep:
        env_parts.append(f"Wind Speed {w_rep}")
    if c_rep:
        env_parts.append(f"Current {c_rep}")
    env_line = ", ".join(env_parts) if env_parts else "Not recorded"
    raw_rem = format_remarks_knots(str(metrics.get("remarks") or "").strip())

    xing_disp = f"{xing_id} ({act_grp})" if (act_grp and act_grp != xing_id) else xing_id
    clean_cur_gaps = "1st Unit (N/A)" if is_first else _format_unit_gaps_clean(metrics.get("gap_labels", "N/A"))

    geo_headers = ["Parameter", "Design", "QA/QC USBL", "As-Laid ROV", "Delta / Result"]
    geo_rows = [
        ["Easting E (m, TWD97)", f"{metrics.get('design_e',0):.3f}", f"{metrics.get('qaqc_e',0):.3f}", f"{metrics.get('aslaid_e',0):.3f}", f"{metrics.get('aslaid_e',0)-metrics.get('design_e',0):+.3f} m"],
        ["Northing N (m, TWD97)", f"{metrics.get('design_n',0):.3f}", f"{metrics.get('qaqc_n',0):.3f}", f"{metrics.get('aslaid_n',0):.3f}", f"{metrics.get('aslaid_n',0)-metrics.get('design_n',0):+.3f} m"],
        ["Depth Z (m, TWVD2001)", "Seabed + 0.30 m", "-", f"{metrics.get('aslaid_z',-18.2):.2f}", "WROV 4-Corner Mean"],
        ["South Bearing (deg)", f"{metrics.get('design_brg',0):.2f}", f"{metrics.get('qaqc_brg',0):.2f}", f"{metrics.get('heading_deg',0):.2f}", f"{metrics.get('brg_diff_deg',0):+.2f} deg"],
        ["Radial Offset dCL (m)", f"<= {cl_tol:.2f} m", "-", f"{cl_off:.3f} m", f"{cl_st} (dAl {metrics.get('d_along_m',0):+.2f}, dCr {metrics.get('d_cross_m',0):+.2f}m)"],
        ["Side-to-Side Gap (m)", f"<= {g_tol:.2f} m", "-", clean_cur_gaps, gap_st],
    ]

    lines = [
        f"**Crossing:** {xing_disp}  --  **Placement:** {metrics.get('install_date','')}  --  **Surveyor:** {metrics.get('surveyor_name','Duty Surveyor')}",
        "",
        "## 1. GEODETIC & TOLERANCE SUMMARY",
        *_format_aligned_md_table(geo_headers, geo_rows),
        "",
        "## 2. AS-LAID 4-CORNER ROV COORDINATES",
        f"- C1 (NW): E {c_enz[0][0]:.3f}, N {c_enz[0][1]:.3f}, Z {c_enz[0][2]:.2f} m" + ("" if is_first else f"  [Gap NW: {gaps.get('nw') or '-'}]"),
        f"- C2 (NE): E {c_enz[1][0]:.3f}, N {c_enz[1][1]:.3f}, Z {c_enz[1][2]:.2f} m" + ("" if is_first else f"  [Gap NE: {gaps.get('ne') or '-'}]"),
        f"- C3 (SE): E {c_enz[2][0]:.3f}, N {c_enz[2][1]:.3f}, Z {c_enz[2][2]:.2f} m" + ("" if is_first else f"  [Gap SE: {gaps.get('se') or '-'}]"),
        f"- C4 (SW): E {c_enz[3][0]:.3f}, N {c_enz[3][1]:.3f}, Z {c_enz[3][2]:.2f} m" + ("" if is_first else f"  [Gap SW: {gaps.get('sw') or '-'}]"),
        "",
        "## 3. FIELD EXCEPTIONS, ENVIRONMENT & REMARKS",
        f"- Metocean: {env_line}",
        f"- Remarks: {raw_rem if raw_rem else 'None (within design specification).'}",
    ]

    placed_pairs, _ = _collect_placed_mattresses_up_to_cutoff(
        resolved_ledger, metrics.get("install_date"), current_metrics=metrics, full_day=False
    )
    placed_rows = [r for (_, r) in placed_pairs]

    prog_sec_no = 4
    if placed_rows:
        prog_sec_no = 5
        placed_headers = ["Unit #", "Date/Time", "Crossing", "Box ID", "Tag ID", "As-Laid E", "As-Laid N", "dCL (m)", "Gaps"]
        placed_data = []
        for r in placed_rows:
            dt_clean = re.sub(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})", r"\1 \2", str(r.get("install_date") or "").strip())
            r_xing = str(r.get("crossing_id") or "").strip() or normalize_crossing_group(r.get("design_box_id")) or "-"
            placed_data.append([
                str(r.get("unit_no", "")).strip(),
                dt_clean,
                r_xing,
                str(r.get("design_box_id") or "").strip(),
                str(r.get("physical_tag") or "-").strip() or "-",
                f"{float(r.get('aslaid_e') or 0):.3f}",
                f"{float(r.get('aslaid_n') or 0):.3f}",
                f"{float(r.get('cl_offset_m') or 0):.3f}",
                _format_unit_gaps_clean(r),
            ])
        lines.extend([
            "",
            "## 4. PLACED CONCRETE MATTRESSES",
            *_format_aligned_md_table(placed_headers, placed_data, right_cols=(5, 6, 7)),
        ])

    prog_rows, prog_tot, _ = compute_historical_progress_rows(
        resolved_ledger, metrics.get("install_date"), current_metrics=metrics, full_day=False
    )
    prog_headers = [
        "LOCATION / CROSSING ID",
        "TOTAL QUANTITY TO BE INSTALLED",
        "POST INSTALLED QUANTITY",
        "TODAY INSTALLED",
        "TOTAL CUMULATIVE INSTALLED",
        "REMAINING",
    ]
    prog_data = [[grp_lbl, sc_q, post_q, tod_q, cum_q, rem_q] for (grp_lbl, sc_q, post_q, tod_q, cum_q, rem_q) in list(prog_rows) + [prog_tot]]
    lines.extend([
        "",
        f"## {prog_sec_no}. INSTALLATION PROGRESS OF CONCRETE MATTRESS 0001-2400",
        *_format_aligned_md_table(prog_headers, prog_data, right_cols=(1, 2, 3, 4, 5)),
    ])
    return chr(10).join(lines)

def render_a4_landscape_figures(metrics, custom_report_md=None, ledger_list=None):
    resolved_ledger = _resolve_ledger_for_report(ledger_list)
    md_text = custom_report_md if custom_report_md else build_structured_report_markdown(metrics, True, resolved_ledger)
    filtered_lines = [
        ln for ln in str(md_text).splitlines()
        if "chart scales @ a3" not in ln.strip().lower() and "chart scales:" not in ln.strip().lower()
    ]

    W_MM, H_MM = 297.0, 210.0
    loc_id, mat_id = metrics.get("location_id", "CR-A1_M15"), metrics.get("mattress_id", "#A046")
    loc_up = str(loc_id or "").strip().upper()
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

    def _draw_boxed_md_table(tbl_kind, hdr_cells, data_rows):
        nonlocal page_no, fig, ax, y_cur
        n_c = len(hdr_cells)
        is_placed_tbl = tbl_kind in ("placed_units_9", "placed_units_8")
        if tbl_kind == "geodetic":
            edges = [13.0, 69.0, 115.0, 157.0, 216.0, 284.0]
            aligns = ["left", "center", "center", "center", "left"]
            max_lens = [34, 24, 20, 34, 38]
            bold_cols = (0,)
        elif tbl_kind == "placed_units_9":
            edges = [13.0, 26.0, 60.0, 84.0, 112.0, 132.0, 161.0, 192.0, 213.0, 284.0]
            aligns = ["center", "center", "center", "center", "center", "right", "right", "center", "left"]
            max_lens = [7, 19, 13, 15, 11, 14, 14, 10, 44]
            bold_cols = (0, 2, 3, 4)
        elif tbl_kind == "placed_units_8":
            edges = [13.0, 27.0, 65.0, 95.0, 117.0, 148.0, 180.0, 203.0, 284.0]
            aligns = ["center", "center", "center", "center", "right", "right", "center", "left"]
            max_lens = [8, 20, 16, 12, 14, 14, 10, 48]
            bold_cols = (0, 2, 3)
        else:
            edges = [13.0 + i * (271.0 / n_c) for i in range(n_c + 1)]
            aligns = ["left"] * n_c
            max_lens = [max(10, int(160 / n_c))] * n_c
            bold_cols = (0,)

        h_hdr_r, h_dat_r = 4.3, 3.9

        def _render_row_cells(cells_r, y_top_r, h_r, is_header=False, r_idx=0):
            is_cur_unit = (not is_header and is_placed_tbl and loc_up and any(c.strip().upper() == loc_up for c in cells_r))
            if is_header:
                fc = "#bae6fd" if is_placed_tbl else "#e2e8f0"
                ec = "#0f172a" if is_placed_tbl else "#94a3b8"
            else:
                fc = "#f0f9ff" if is_cur_unit else ("#f8fafc" if r_idx % 2 == 0 else "#ffffff")
                ec = "#64748b" if is_placed_tbl else "#cbd5e1"
            ax.add_patch(mpatches.Rectangle((13.0, y_top_r - h_r), 271.0, h_r, facecolor=fc, edgecolor=ec, linewidth=0.55))
            for xv in edges[1:-1]:
                ax.plot([xv, xv], [y_top_r - h_r, y_top_r], color=ec, linewidth=0.45)

            row_x_col = "" if is_header else get_crossing_group_color(" ".join(cells_r), default="")

            yc = y_top_r - h_r / 2.0
            for ic in range(min(n_c, len(cells_r))):
                txt_c = cells_r[ic][: max_lens[ic]]
                al = aligns[ic] if not is_header else ("center" if aligns[ic] in ("center", "right") else "left")
                if al == "center":
                    xp, ha_u = 0.5 * (edges[ic] + edges[ic + 1]), "center"
                elif al == "right":
                    xp, ha_u = edges[ic + 1] - 2.2, "right"
                else:
                    xp, ha_u = edges[ic] + 1.8, "left"

                if is_header:
                    c_use, fw_use = "#0f172a", "bold"
                elif tbl_kind == "geodetic":
                    if ic == 0:
                        c_use, fw_use = "#0f172a", "bold"
                    elif ic == 3:
                        c_use, fw_use = act_col, "bold"
                    elif ic == 4:
                        u_t = txt_c.upper()
                        c_use = "#15803d" if "PASS" in u_t else ("#b91c1c" if "EXCEEDS" in u_t else "#1e293b")
                        fw_use = "bold" if ("PASS" in u_t or "EXCEEDS" in u_t) else "normal"
                    else:
                        c_use, fw_use = "#1e293b", "normal"
                elif row_x_col:
                    c_use = row_x_col
                    fw_use = "bold" if (is_cur_unit or ic in bold_cols) else "normal"
                else:
                    c_use = "#1e293b"
                    fw_use = "bold" if (is_cur_unit or ic in bold_cols) else "normal"

                fs_u = 7.3 if tbl_kind == "placed_units_9" else 7.5
                ax.text(xp, yc, txt_c, fontsize=fs_u, fontweight=fw_use, family="monospace", color=c_use, ha=ha_u, va="center")

        if y_cur - (h_hdr_r + h_dat_r) < 17.0:
            page_no += 1
            fig, ax = _new_a4_landscape_page(page_no)
            figs.append(fig)
            y_cur = 181.5

        _render_row_cells(hdr_cells, y_cur + 1.4, h_hdr_r, is_header=True)
        y_cur -= h_hdr_r
        for r_i, d_row in enumerate(data_rows):
            if y_cur + 1.4 - h_dat_r < 16.8:
                page_no += 1
                fig, ax = _new_a4_landscape_page(page_no)
                figs.append(fig)
                y_cur = 181.5
                _render_row_cells(hdr_cells, y_cur + 1.4, h_hdr_r, is_header=True)
                y_cur -= h_hdr_r
            _render_row_cells(d_row, y_cur + 1.4, h_dat_r, is_header=False, r_idx=r_i)
            y_cur -= h_dat_r
        y_cur -= 1.0

    sec_counter = 0
    idx_ln = 0
    while idx_ln < len(filtered_lines):
        raw_ln = filtered_lines[idx_ln].strip()
        idx_ln += 1

        if raw_ln.startswith("## ") and "INSTALLATION PROGRESS OF CONCRETE MATTRESS" in raw_ln.upper():
            while idx_ln < len(filtered_lines) and (not filtered_lines[idx_ln].strip() or filtered_lines[idx_ln].strip().startswith("|")):
                idx_ln += 1
            continue

        line = _strip_redundant_verdict_prefix(raw_ln) if not raw_ln.startswith("|") else raw_ln
        if raw_ln and not line:
            continue

        if y_cur < 19.5:
            page_no += 1
            fig, ax = _new_a4_landscape_page(page_no)
            figs.append(fig)
            y_cur = 180.5

        if not line:
            y_cur -= 1.3
            continue
        if line.startswith("# "):
            ax.text(14, y_cur, line[2:], fontsize=10.6, fontweight="bold", color=act_col)
            y_cur -= 4.8
        elif line.startswith("## "):
            sec_counter += 1
            raw_sec_title = re.sub(r"^\d+\.\s*", "", line[3:].strip())
            if "PRIOR PLACED UNITS" in raw_sec_title.upper():
                raw_sec_title = "PLACED CONCRETE MATTRESSES"
            sec_lbl = f"{sec_counter}. {raw_sec_title}"
            y_cur -= 0.6
            ax.add_patch(mpatches.Rectangle((13, y_cur - 1.3), 271, 4.9, facecolor="#e2e8f0", edgecolor="none"))
            ax.text(15, y_cur + 1.1, sec_lbl, fontsize=9.3, fontweight="bold", color="#0f172a", va="center")
            y_cur -= 4.7
        elif line.startswith("|"):
            tbl_raw_lines = [line]
            while idx_ln < len(filtered_lines) and filtered_lines[idx_ln].strip().startswith("|"):
                tbl_raw_lines.append(filtered_lines[idx_ln].strip())
                idx_ln += 1
            parsed_pipe = [_split_md_pipe_row(tl) for tl in tbl_raw_lines if ":---" not in tl and "---:" not in tl]
            if not parsed_pipe:
                continue
            t_kind = _detect_md_table_kind(parsed_pipe[0])
            if t_kind == "progress":
                continue
            if t_kind in ("placed_units_8", "placed_units_9") and custom_report_md and t_kind == "placed_units_8":
                # Upgrade legacy 8-col cached table to all placed mattresses across all crossings
                placed_pairs_u, _ = _collect_placed_mattresses_up_to_cutoff(
                    resolved_ledger, metrics.get("install_date"), current_metrics=metrics, full_day=False
                )
                h_norm = ["Unit #", "Date/Time", "Crossing", "Box ID", "Tag ID", "As-Laid E", "As-Laid N", "dCL (m)", "Gaps"]
                d_norm = []
                for _, r_u in placed_pairs_u:
                    dt_c = re.sub(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})", r"\1 \2", str(r_u.get("install_date") or "").strip())
                    rx_c = str(r_u.get("crossing_id") or "").strip() or normalize_crossing_group(r_u.get("design_box_id")) or "-"
                    d_norm.append([
                        str(r_u.get("unit_no", "")).strip(), dt_c, rx_c,
                        str(r_u.get("design_box_id") or "").strip(),
                        str(r_u.get("physical_tag") or "-").strip() or "-",
                        f"{float(r_u.get('aslaid_e') or 0):.3f}",
                        f"{float(r_u.get('aslaid_n') or 0):.3f}",
                        f"{float(r_u.get('cl_offset_m') or 0):.3f}",
                        _format_unit_gaps_clean(r_u),
                    ])
                _draw_boxed_md_table("placed_units_9", h_norm, d_norm)
                continue
            h_norm = _normalize_md_table_cells(parsed_pipe[0], t_kind)
            d_norm = [_normalize_md_table_cells(pr, t_kind, len(h_norm)) for pr in parsed_pipe[1:]]
            _draw_boxed_md_table(t_kind, h_norm, d_norm)
        else:
            cl = line.replace("**", "").strip()
            is_meta_ln = cl.startswith("Crossing:")
            is_corner_ln = bool(re.match(r"^-\s*C[1-4]\s*\(", cl))
            ln_x_col = act_col if (is_meta_ln or is_corner_ln) else get_crossing_group_color(cl, default="#1e293b")
            fw_ln = "bold" if is_meta_ln else "normal"
            ax.text(14, y_cur, cl[:145], fontsize=8.6, fontweight=fw_ln, color=ln_x_col)
            if len(cl) > 145:
                y_cur -= 3.8
                ax.text(18, y_cur, cl[145:290], fontsize=8.6, fontweight=fw_ln, color=ln_x_col)
            y_cur -= 3.9

    prog_rows, prog_tot, _ = compute_historical_progress_rows(
        resolved_ledger, metrics.get("install_date"), current_metrics=metrics, full_day=False
    )
    if y_cur - 45.9 < 16.5:
        page_no += 1
        fig, ax = _new_a4_landscape_page(page_no)
        figs.append(fig)
        y_cur = 182.0
    draw_mattress_progress_box(ax, y_cur + 0.6, prog_rows, prog_tot, active_group=act_grp)

    return figs

def generate_a4_report_pdf(metrics, workspace_dir="workspace", custom_report_md=None, ledger_list=None):
    os.makedirs(workspace_dir, exist_ok=True)
    figs = render_a4_landscape_figures(metrics, custom_report_md, ledger_list)
    buf = io.BytesIO()
    with PdfPages(buf) as pdf_pages:
        for f in figs:
            pdf_pages.savefig(f, dpi=150)
            f.clf(); plt.close(f)
    plt.close("all"); gc.collect()
    pdf_bytes = buf.getvalue()
    for fn in ("latest_A4_Verification_Report.pdf", f"{metrics.get('base_filename','Report')}_A4_Report.pdf"):
        open(os.path.join(workspace_dir, fn), "wb").write(pdf_bytes)
    return pdf_bytes

def generate_mti_dpr_pdf(st_data, target_date_str=None, surveyor_name="Duty Surveyor", workspace_dir="workspace"):
    os.makedirs(workspace_dir, exist_ok=True)
    surv_disp = resolve_full_surveyor_name(surveyor_name) or surveyor_name
    ledger = list((st_data or {}).get("ledger") or [])
    raw_logs = extract_all_mti_logs(st_data)
    parsed_logs = [parse_log_entry_fields(lg, surv_disp) for lg in raw_logs]

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

    day_fixes = [
        r for r in ledger
        if norm_mti_date(r.get("install_date")) == dt_iso
        and str(r.get("status") or "Completed").strip().lower() not in ("planned", "cancelled", "rejected")
    ]
    day_fixes.sort(key=lambda r: _extract_time(r.get("install_date")))

    day_logs = [item for item in parsed_logs if item[0] == dt_iso]
    day_logs.sort(key=lambda item: item[1])

    prog_rows_dpr, prog_tot_dpr, _ = compute_historical_progress_rows(
        ledger, f"{dt_iso} 23:59:59", current_metrics=None, full_day=True
    )
    _, tot_scope, tot_post, tot_today, tot_cum, tot_rem = prog_tot_dpr

    day_grps = []
    for r in day_fixes:
        g = normalize_crossing_group(r.get("crossing_id") or r.get("design_box_id"))
        if g and g not in day_grps:
            day_grps.append(g)
    if not day_grps:
        for (_, _, _, area_s, clean_desc, _, _) in day_logs:
            g = normalize_crossing_group(area_s) or normalize_crossing_group(clean_desc)
            if g and g not in day_grps:
                day_grps.append(g)
    primary_dpr_grp = day_grps[0] if len(day_grps) == 1 else ""
    dpr_hdr_col = get_crossing_group_color(day_grps[0], default="#38bdf8", dark_bg=True) if day_grps else "#38bdf8"

    W_MM, H_MM = 297.0, 210.0

    def _new_dpr_page(page_num):
        fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4), dpi=150, facecolor="white")
        ax = fig.add_axes([0, 0, 1, 1], frameon=False)
        ax.set_xlim(0, W_MM); ax.set_ylim(0, H_MM); ax.set_xticks([]); ax.set_yticks([])
        ax.add_patch(mpatches.Rectangle((10, 10), 277, 190, fill=False, edgecolor="#0f172a", linewidth=1.4))
        ax.add_patch(mpatches.Rectangle((10, 185.5), 277, 14.5, facecolor="#0f172a", edgecolor="#0f172a"))
        ax.text(14, 194.8, "SUBSEA MATTRESS & ROCK BAG INSTALLATION (MTI) - DAILY PROGRESS REPORT (DPR)", color="white", fontsize=9.8, fontweight="bold", va="center")
        if day_grps:
            ax.text(283, 194.8, f"CROSSING: {' / '.join(day_grps)}", color=dpr_hdr_col, fontsize=8.8, fontweight="bold", va="center", ha="right")
        ax.text(14, 188.8, f"Reporting Period: {dt_iso} (00:00 to 23:59 hrs)  |  Vessel: DP2 MMA Prestige  |  Client: TPC  |  Contractor: NMDC", color=dpr_hdr_col, fontsize=8.2, fontweight="bold", va="center")
        ax.plot([10, 287], [15.5, 15.5], color="#cbd5e1", linewidth=0.8)
        ax.text(14, 12.0, f"Tung-Hsiao 2nd Stage Subsea Gas Pipeline Project  |  Duty Surveyor: {surv_disp}", fontsize=7.8, color="#475569", fontweight="bold")
        ax.text(283, 12.0, f"MTI DPR ({dt_iso} | 00:00-23:59) | Page {page_num}", fontsize=7.8, color="#475569", ha="right")
        return fig, ax

    figs = []
    p_no = 1
    fig, ax = _new_dpr_page(p_no)
    figs.append(fig)
    y = 180.0

    latest_status = day_logs[-1][4][:74] if day_logs else ("Installation active" if day_fixes else "No field events logged")
    pct_done = (tot_cum * 100.0) / float(tot_scope or 139)
    exec_line = (
        f"DAILY TAKEAWAY: +{tot_today} Laid Today (Post: {tot_post} | Cumul: {tot_cum}/{tot_scope}, {pct_done:.1f}% | Rem: {tot_rem})"
        f"  |  {len(day_logs)} Log Event(s)  |  Latest: {latest_status}"
    )
    ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.8, facecolor="#f0f9ff", edgecolor="#0284c7", linewidth=0.6))
    ax.text(15, y + 1.1, exec_line[:142], fontsize=7.6, fontweight="bold", color="#0f172a", va="center")
    y -= 6.0

    y = draw_mattress_progress_box(
        ax, y + 2.2, prog_rows_dpr, prog_tot_dpr,
        title_str="INSTALLATION PROGRESS OF CONCRETE MATTRESS 0001-2400",
        active_group=primary_dpr_grp,
    )

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
            (212.0, 284.0, "Corner Gaps / Verdict"),
        ]
        ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.4, facecolor="#e2e8f0", edgecolor="#94a3b8", linewidth=0.5))
        for x0, x1, h_lbl in f_cols:
            ax.text(x0 + 1.5, y + 0.9, h_lbl, fontsize=7.4, fontweight="bold", color="#0f172a", va="center")
        y -= 4.4
        for idx_f, r in enumerate(day_fixes):
            if y < 19.5:
                p_no += 1; fig, ax = _new_dpr_page(p_no); figs.append(fig); y = 180.0
                ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.4, facecolor="#e2e8f0", edgecolor="#94a3b8", linewidth=0.5))
                for x0, x1, h_lbl in f_cols:
                    ax.text(x0 + 1.5, y + 0.9, h_lbl, fontsize=7.4, fontweight="bold", color="#0f172a", va="center")
                y -= 4.4
            bg_c = "#f8fafc" if idx_f % 2 == 0 else "#ffffff"
            ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.2, facecolor=bg_c, edgecolor="#cbd5e1", linewidth=0.4))
            t_hm = _extract_time(r.get("install_date"))
            vals_f = [
                f"#{r.get('unit_no','')}", t_hm, str(r.get("crossing_id") or "")[:10],
                str(r.get("design_box_id") or "")[:12], str(r.get("physical_tag") or "")[:8],
                f"{float(r.get('aslaid_e') or 0):.3f}", f"{float(r.get('aslaid_n') or 0):.3f}",
                f"{float(r.get('heading_deg') or 0):.1f} deg", f"{float(r.get('cl_offset_m') or 0):.2f} m",
                f"{_format_unit_gaps_clean(r)} | {r.get('status','Completed')}"[:42],
            ]
            fx_col = get_crossing_group_color(r.get("crossing_id") or r.get("design_box_id"), default="#1e293b")
            for idx_fc, ((x0, x1, _), v_str) in enumerate(zip(f_cols, vals_f)):
                ax.text(x0 + 1.5, y + 0.8, v_str, fontsize=7.4, fontweight="bold" if idx_fc in (0, 2, 3) else "normal", color=fx_col, family="monospace", va="center")
            y -= 4.2
        y -= 2.5

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
            (13.0, 27.0, "Time"), (27.0, 59.0, "Category"), (59.0, 95.0, "Asset / Crossing"),
            (95.0, 205.0, "Operational Event & Remarks"), (205.0, 250.0, "Wind / Curr (knots)"), (250.0, 284.0, "Surveyor"),
        ]
        ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.4, facecolor="#e2e8f0", edgecolor="#94a3b8", linewidth=0.5))
        for x0, x1, h_lbl in l_cols:
            ax.text(x0 + 1.5, y + 0.9, h_lbl, fontsize=7.4, fontweight="bold", color="#0f172a", va="center")
        y -= 4.4

        for idx_l, (_, t_hm, cat_s, area_s, clean_desc, env_short, surv_l) in enumerate(day_logs):
            area_lines = textwrap.wrap(area_s, width=18) or ["-"]
            wrapped_lines = textwrap.wrap(clean_desc, width=60) or ["-"]
            env_lines = [x.strip() for x in env_short.split("|")] if len(env_short) > 25 and "|" in env_short else [env_short[:28]]
            surv_lines = textwrap.wrap(surv_l, width=18) or ["-"]
            n_row_ln = max(len(area_lines), len(wrapped_lines), len(env_lines), len(surv_lines))
            row_h = max(4.2, n_row_ln * 3.5 + 0.8)

            if y - row_h + 3.0 < 17.0:
                p_no += 1; fig, ax = _new_dpr_page(p_no); figs.append(fig); y = 180.0
                ax.add_patch(mpatches.Rectangle((13, y - 1.2), 271, 4.4, facecolor="#e2e8f0", edgecolor="#94a3b8", linewidth=0.5))
                for x0, x1, h_lbl in l_cols:
                    ax.text(x0 + 1.5, y + 0.9, h_lbl, fontsize=7.4, fontweight="bold", color="#0f172a", va="center")
                y -= 4.4

            bg_c = "#f8fafc" if idx_l % 2 == 0 else "#ffffff"
            ax.add_patch(mpatches.Rectangle((13, y - row_h + 3.0), 271, row_h, facecolor=bg_c, edgecolor="#cbd5e1", linewidth=0.4))

            ax.text(14.5, y + 0.7, t_hm, fontsize=7.4, fontweight="bold", color="#0369a1", family="monospace", va="center")
            ax.text(28.5, y + 0.7, cat_s[:17], fontsize=7.3, fontweight="bold", color="#0f172a", va="center")
            lg_x_col = get_crossing_group_color(area_s, default="") or get_crossing_group_color(clean_desc, default="")
            for a_idx, a_ln in enumerate(area_lines):
                ax.text(60.5, y + 0.7 - a_idx * 3.5, a_ln, fontsize=7.2, fontweight="bold" if lg_x_col else "normal", color=lg_x_col or "#334155", family="monospace", va="center")
            for w_idx, w_ln in enumerate(wrapped_lines):
                ax.text(96.5, y + 0.7 - w_idx * 3.5, w_ln, fontsize=7.4, color=lg_x_col or "#1e293b", va="center")
            for e_idx, e_ln in enumerate(env_lines):
                ax.text(206.5, y + 0.7 - e_idx * 3.5, e_ln, fontsize=6.7, color="#0369a1", family="monospace", va="center")
            for s_idx, s_ln in enumerate(surv_lines):
                ax.text(251.5, y + 0.7 - s_idx * 3.5, s_ln, fontsize=7.1, color="#475569", va="center")
            y -= row_h

    buf = io.BytesIO()
    with PdfPages(buf) as pdf_pages:
        for f in figs:
            pdf_pages.savefig(f, dpi=150)
            f.clf(); plt.close(f)
    plt.close("all"); gc.collect()
    pdf_bytes = buf.getvalue()
    yyyymmdd = dt_iso.replace("-", "")
    fn_out = f"{yyyymmdd}_MTI_Daily_Progress_Report.pdf"
    open(os.path.join(workspace_dir, fn_out), "wb").write(pdf_bytes)
    return pdf_bytes, fn_out, dt_iso

def _xml_esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

def _build_docx_table_xml(col_widths_dxa, rows_spec, aligns=None):
    tot_w = sum(col_widths_dxa)
    grid_xml = "".join(f'<w:gridCol w:w="{w}"/>' for w in col_widths_dxa)
    bdr = '<w:tblBorders><w:top w:val="single" w:sz="6" w:space="0" w:color="334155"/><w:left w:val="single" w:sz="6" w:space="0" w:color="334155"/><w:bottom w:val="single" w:sz="6" w:space="0" w:color="334155"/><w:right w:val="single" w:sz="6" w:space="0" w:color="334155"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="94A3B8"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="94A3B8"/></w:tblBorders>'
    tr_xml_list = []
    for cells, fill_hex, text_hex, is_bold, span_all, is_underline in rows_spec:
        if span_all:
            txt = _xml_esc(cells[0] if cells else "")
            b_t = "<w:b/>" if is_bold else ""
            u_t = '<w:u w:val="single"/>' if is_underline else ""
            tc_xml = (
                f'<w:tc><w:tcPr><w:tcW w:w="{tot_w}" w:type="dxa"/><w:gridSpan w:val="{len(col_widths_dxa)}"/>'
                f'<w:shd w:val="clear" w:color="auto" w:fill="{fill_hex}"/><w:vAlign w:val="center"/></w:tcPr>'
                f'<w:p><w:pPr><w:spacing w:before="30" w:after="30"/><w:jc w:val="center"/></w:pPr>'
                f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>{b_t}<w:color w:val="{text_hex}"/><w:sz w:val="19"/>{u_t}</w:rPr>'
                f'<w:t xml:space="preserve">{txt}</w:t></w:r></w:p></w:tc>'
            )
            tr_xml_list.append(f"<w:tr>{tc_xml}</w:tr>")
            continue

        tcs = []
        for ic, w_col in enumerate(col_widths_dxa):
            c_txt = _xml_esc(cells[ic] if ic < len(cells) else "")
            jc = "center" if is_bold else ((aligns[ic] if (aligns and ic < len(aligns)) else "left"))
            b_t = "<w:b/>" if (is_bold or ic == 0) else ""
            tcs.append(
                f'<w:tc><w:tcPr><w:tcW w:w="{w_col}" w:type="dxa"/>'
                f'<w:shd w:val="clear" w:color="auto" w:fill="{fill_hex}"/><w:vAlign w:val="center"/></w:tcPr>'
                f'<w:p><w:pPr><w:spacing w:before="24" w:after="24"/><w:jc w:val="{jc}"/></w:pPr>'
                f'<w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>{b_t}<w:color w:val="{text_hex}"/><w:sz w:val="17"/></w:rPr>'
                f'<w:t xml:space="preserve">{c_txt}</w:t></w:r></w:p></w:tc>'
            )
        tr_xml_list.append("<w:tr>" + "".join(tcs) + "</w:tr>")

    return (
        f'<w:tbl><w:tblPr><w:tblW w:w="{tot_w}" w:type="dxa"/>{bdr}<w:tblLayout w:type="fixed"/>'
        f'<w:tblCellMar><w:top w:w="30" w:type="dxa"/><w:left w:w="70" w:type="dxa"/><w:bottom w:w="30" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        f'<w:tblGrid>{grid_xml}</w:tblGrid>' + "".join(tr_xml_list) + "</w:tbl>"
    )

def generate_editable_docx(metrics, report_md, workspace_dir="workspace", ledger_list=None):
    os.makedirs(workspace_dir, exist_ok=True)
    resolved_ledger = _resolve_ledger_for_report(ledger_list)
    loc_up = str(metrics.get("location_id") or "").strip().upper()
    act_grp = normalize_crossing_group(metrics.get("crossing_id") or metrics.get("location_id"))
    act_hex = get_crossing_group_color(act_grp, default="#1e293b").lstrip("#").upper()
    elem_list = []

    pending_tbl_kind = None
    pending_tbl_rows = []

    def _flush_pending_table():
        nonlocal pending_tbl_kind, pending_tbl_rows
        if not pending_tbl_rows:
            pending_tbl_kind = None
            return
        if pending_tbl_kind == "progress":
            pending_tbl_kind = None
            pending_tbl_rows = []
            return
        n_cols = len(pending_tbl_rows[0][0])
        if pending_tbl_kind == "geodetic":
            widths = [3200, 2600, 2400, 3400, 3800]
            aligns = ["left", "center", "center", "center", "left"]
        elif pending_tbl_kind == "placed_units_9":
            widths = [850, 2100, 1450, 1650, 1150, 1750, 1800, 1100, 3550]
            aligns = ["center", "center", "center", "center", "center", "right", "right", "center", "left"]
        elif pending_tbl_kind == "placed_units_8":
            widths = [950, 2250, 1750, 1250, 1800, 1850, 1150, 4400]
            aligns = ["center", "center", "center", "center", "right", "right", "center", "left"]
        else:
            widths = [int(15400 / max(n_cols, 1))] * max(n_cols, 1)
            aligns = ["left"] * max(n_cols, 1)
        elem_list.append(_build_docx_table_xml(widths, pending_tbl_rows, aligns))
        pending_tbl_kind = None
        pending_tbl_rows = []

    md_lines = str(report_md or "").splitlines()
    idx_l = 0
    sec_no = 0
    while idx_l < len(md_lines):
        raw_ln = md_lines[idx_l].strip()
        idx_l += 1
        if not raw_ln or "chart scales @ a3" in raw_ln.lower() or "chart scales:" in raw_ln.lower():
            _flush_pending_table()
            continue
        if raw_ln.startswith("## ") and "INSTALLATION PROGRESS OF CONCRETE MATTRESS" in raw_ln.upper():
            _flush_pending_table()
            while idx_l < len(md_lines) and (not md_lines[idx_l].strip() or md_lines[idx_l].strip().startswith("|")):
                idx_l += 1
            continue
        line = _strip_redundant_verdict_prefix(raw_ln) if not raw_ln.startswith("|") else raw_ln
        if not line:
            continue
        if line.startswith("|"):
            if ":---" in line or "---:" in line:
                continue
            raw_cells = _split_md_pipe_row(line)
            if pending_tbl_kind is None:
                pending_tbl_kind = _detect_md_table_kind(raw_cells)
                h_cells = _normalize_md_table_cells(raw_cells, pending_tbl_kind)
                hdr_fill = "BAE6FD" if pending_tbl_kind in ("placed_units_9", "placed_units_8") else "E2E8F0"
                pending_tbl_rows.append((h_cells, hdr_fill, "0F172A", True, False, False))
            else:
                d_cells = _normalize_md_table_cells(raw_cells, pending_tbl_kind, len(pending_tbl_rows[0][0]))
                r_hex = get_crossing_group_color(" ".join(d_cells), default="#1E293B").lstrip("#").upper()
                is_cur_u = loc_up and any(c.strip().upper() == loc_up for c in d_cells)
                fill_r = "F0F9FF" if is_cur_u else ("F8FAFC" if len(pending_tbl_rows) % 2 == 1 else "FFFFFF")
                pending_tbl_rows.append((d_cells, fill_r, r_hex, bool(is_cur_u), False, False))
            continue

        _flush_pending_table()
        raw_plain = re.sub(r"^#+\s*", "", line).replace("**", "")
        if line.startswith("## "):
            sec_no += 1
            clean_t = re.sub(r"^\d+\.\s*", "", raw_plain.strip())
            if "PRIOR PLACED UNITS" in clean_t.upper():
                clean_t = "PLACED CONCRETE MATTRESSES"
            raw_plain = f"{sec_no}. {clean_t}"
        txt = _xml_esc(raw_plain)
        if line.startswith("#"):
            elem_list.append(
                f'<w:p><w:pPr><w:spacing w:before="100" w:after="40"/></w:pPr>'
                f'<w:r><w:rPr><w:b/><w:color w:val="0F172A"/><w:sz w:val="22"/></w:rPr><w:t>{txt}</w:t></w:r></w:p>'
            )
        else:
            is_meta = raw_plain.strip().startswith("Crossing:")
            is_act = is_meta or bool(re.match(r"^-\s*C[1-4]\s*\(", raw_plain))
            l_hex = act_hex if is_act else get_crossing_group_color(line, default="#1E293B").lstrip("#").upper()
            b_tag = "<w:b/>" if is_meta else ""
            elem_list.append(
                f'<w:p><w:pPr><w:spacing w:before="20" w:after="20"/></w:pPr>'
                f'<w:r><w:rPr>{b_tag}<w:color w:val="{l_hex}"/><w:sz w:val="19"/></w:rPr><w:t>{txt}</w:t></w:r></w:p>'
            )
    _flush_pending_table()

    prog_rows, prog_tot, _ = compute_historical_progress_rows(
        resolved_ledger, metrics.get("install_date"), current_metrics=metrics, full_day=False
    )
    elem_list.append('<w:p><w:pPr><w:spacing w:before="80" w:after="20"/></w:pPr></w:p>')
    prog_spec = [
        (["INSTALLATION PROGRESS OF CONCRETE MATTRESS 0001-2400"], "FEF08A", "0F172A", True, True, True),
        (["LOCATION / CROSSING ID", "TOTAL QTY TO BE INSTALLED", "POST INSTALLED QTY", "TODAY INSTALLED", "TOTAL CUMULATIVE INSTALLED", "REMAINING"], "BAE6FD", "0F172A", True, False, False),
    ]
    for lbl, sc_q, post_q, tod_q, cum_q, rem_q in list(prog_rows) + [prog_tot]:
        is_tot = (lbl == "TOTAL")
        fill_p = "E0F2FE" if is_tot else ("F0F9FF" if (act_grp and lbl == act_grp) else "FFFFFF")
        col_p = "0F172A" if is_tot else get_crossing_group_color(lbl, default="#0F172A").lstrip("#").upper()
        prog_spec.append(([lbl, str(sc_q), str(post_q), str(tod_q), str(cum_q), str(rem_q)], fill_p, col_p, is_tot, False, False))
    elem_list.append(_build_docx_table_xml([2500, 2700, 2500, 2400, 2900, 2400], prog_spec, ["center"] * 6))

    sect_pr = '<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/><w:pgMar w:top="567" w:right="680" w:bottom="567" w:left="680" w:header="360" w:footer="360" w:gutter="0"/></w:sectPr>'
    doc_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + "".join(elem_list) + sect_pr + "</w:body></w:document>"
    ct_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("word/document.xml", doc_xml)
    docx_bytes = buf.getvalue()
    for fn in ("latest_Verification_Report.docx", f"{metrics.get('base_filename','Report')}_Report.docx"):
        open(os.path.join(workspace_dir, fn), "wb").write(docx_bytes)
    return docx_bytes