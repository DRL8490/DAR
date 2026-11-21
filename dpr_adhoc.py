import os, io, re, gc, json, math, uuid, time, base64, textwrap, traceback, contextlib
from datetime import datetime, date, timedelta
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

TASK_COLUMNS = (
    "id", "surveyor_name", "assigned_to", "requestor", "command_verb", "task_category",
    "instrument", "action_required", "area", "location", "sub_location", "work_scope",
    "remarks", "deliverable_link", "reference_links", "status", "is_urgent", "priority",
    "start_time", "execution_date", "end_time", "effective_date"
)

STARTER_DPR_ADHOC_SCRIPT = """# Starter Ad-Hoc DPR Report (Landscape A4: Scope Progress & Surveyor Workload)
fig = plt.figure(figsize=(11.69, 8.27), dpi=150, facecolor="white")
gs = fig.add_gridspec(1, 2, left=0.08, right=0.96, top=0.84, bottom=0.14, wspace=0.28)
fig.suptitle(f"THPP DPR AD-HOC KPI SUMMARY  |  {TODAY_ISO}  |  {SURVEYOR_NAME}", fontsize=12, fontweight="bold", y=0.94)
ax1, ax2 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
if not df_tasks.empty:
    piv = df_tasks.pivot_table(index="work_scope", columns="status", values="id", aggfunc="count", fill_value=0)
    piv["Total"] = piv.sum(axis=1)
    piv = piv.sort_values("Total", ascending=True).tail(10)
    c_vals = piv["Closed"].to_numpy() if "Closed" in piv.columns else np.zeros(len(piv))
    o_vals = piv["Open"].to_numpy() if "Open" in piv.columns else np.zeros(len(piv))
    ax1.barh(piv.index.astype(str), c_vals, color="#198754", label="Closed")
    ax1.barh(piv.index.astype(str), o_vals, left=c_vals, color="#fd7e14", label="Open")
    ax1.legend(loc="lower right", fontsize=8.5)
    surv = df_tasks["surveyor_name"].replace("", "Unassigned").value_counts().head(10).iloc[::-1]
    ax2.barh(surv.index.astype(str), surv.values, color="#0d6efd")
    OUTPUT_DF = piv.reset_index().sort_values("Total", ascending=False)
    OUTPUT_SUMMARY = f"Tasks: {len(df_tasks)} | Closed: {int((df_tasks['status']=='Closed').sum())} | Open: {int((df_tasks['status']=='Open').sum())}"
else:
    for ax, msg in ((ax1, "No tasks match filter"), (ax2, "No surveyor records")):
        ax.text(0.5, 0.5, msg, ha="center", va="center")
    OUTPUT_DF = pd.DataFrame(columns=["work_scope", "Closed", "Open", "Total"])
    OUTPUT_SUMMARY = "No SurveyTask records matched the selected filter."
ax1.set_title("Top Work Scopes (Closed vs Open)", fontweight="bold", fontsize=10)
ax2.set_title("Top Surveyors by Logged Tasks", fontweight="bold", fontsize=10)
for ax in (ax1, ax2):
    ax.set_xlabel("Task Count", fontweight="bold")
    ax.grid(True, axis="x", linestyle=":", alpha=0.6)
OUTPUT_FILENAME = f"{TODAY_YYYYMMDD}_DPR_AdHoc_KPI_Summary.pdf"
OUTPUT_FIGS.append(fig)
"""

def _task_to_dict(t):
    ex_d = t.execution_date.strftime("%Y-%m-%d") if getattr(t, "execution_date", None) else ""
    st_d = t.start_time.strftime("%Y-%m-%d") if getattr(t, "start_time", None) else ""
    return {
        "id": t.id, "surveyor_name": t.surveyor_name or "", "assigned_to": t.assigned_to or "",
        "requestor": t.requestor or "", "command_verb": t.command_verb or "",
        "task_category": t.task_category or "", "instrument": t.instrument or "",
        "action_required": t.action_required or "", "area": t.area or "",
        "location": t.location or "", "sub_location": t.sub_location or "",
        "work_scope": t.work_scope or "", "remarks": t.remarks or "",
        "deliverable_link": t.deliverable_link or "", "reference_links": t.reference_links or "",
        "status": t.status or "Open", "is_urgent": bool(t.is_urgent), "priority": t.priority or 99,
        "start_time": t.start_time.strftime("%Y-%m-%d %H:%M:%S") if t.start_time else "",
        "execution_date": ex_d, "end_time": t.end_time.strftime("%Y-%m-%d %H:%M:%S") if t.end_time else "",
        "effective_date": ex_d or st_d,
    }

def query_dpr_dataset(SurveyTask, start_date="", end_date="", work_scope="", status_filter=""):
    all_rows = [_task_to_dict(t) for t in SurveyTask.query.order_by(SurveyTask.id.desc()).all()]
    s_dt, e_dt = str(start_date or "").strip(), str(end_date or "").strip()
    ws_q, st_q = str(work_scope or "").strip().lower(), str(status_filter or "").strip().lower()
    filt = [
        r for r in all_rows
        if (not s_dt or (r["effective_date"] and r["effective_date"] >= s_dt))
        and (not e_dt or (r["effective_date"] and r["effective_date"] <= e_dt))
        and (not ws_q or ws_q in r["work_scope"].lower())
        and (not st_q or r["status"].lower() == st_q)
    ]
    return all_rows, filt, pd.DataFrame(all_rows, columns=TASK_COLUMNS), pd.DataFrame(filt, columns=TASK_COLUMNS)

def _top_vc(df, col, limit=12):
    if df.empty or col not in df.columns:
        return {}
    s = df[col].fillna("").astype(str).str.strip()
    return {k: int(v) for k, v in s[s != ""].value_counts().head(limit).items()}

def build_dpr_gemini_prompt(
    SurveyTask, User=None, UserActivityLog=None, user_request="",
    start_date="", end_date="", work_scope="", status_filter="", surveyor_name="Duty Surveyor"
):
    _, _, df_all, df_filt = query_dpr_dataset(SurveyTask, start_date, end_date, work_scope, status_filter)
    t_cols = [f"{c.name}:{c.type}" for c in SurveyTask.__table__.columns] + ["effective_date:YYYY-MM-DD"]
    a_cols = [f"{c.name}:{c.type}" for c in UserActivityLog.__table__.columns] if UserActivityLog else []
    u_names = [u.name for u in User.query.filter_by(is_active=True).all()] if User else []
    dates_s = df_filt["effective_date"].replace("", np.nan).dropna()
    date_span = f"{dates_s.min()} to {dates_s.max()}" if not dates_s.empty else "None"
    today_iso, today_ymd = datetime.utcnow().strftime("%Y-%m-%d"), datetime.utcnow().strftime("%Y%m%d")
    req_txt = str(user_request or "").strip() or "Create an executive KPI chart and summary table for the filtered DPR tasks."
    return "\n".join([
        "=== THPP SURVEY DPR & KPI AD-HOC PYTHON REPORT STUDIO CONTEXT ===",
        "Write raw executable Python code for the THPP DPR Ad-Hoc Studio (`/reports`). Return ONLY raw Python code (no pip installs, no Flask imports).",
        "1. BASELINE: Tung-Hsiao 2nd Stage Subsea Gas Pipeline (NMDC 20012). Fit charts on Landscape A4 (11.69x8.27 in) or A3 (16.54x11.69 in), dpi=150.",
        f"2. LIVE GLOBALS: SURVEYOR_NAME='{surveyor_name}' | TODAY_ISO='{today_iso}' | TODAY_YYYYMMDD='{today_ymd}'",
        f"   - FILTER_INFO: {{'start_date': '{start_date}', 'end_date': '{end_date}', 'work_scope': '{work_scope}', 'status': '{status_filter}'}}",
        f"   - df_tasks (DataFrame) & tasks (list[dict]): {len(df_filt)} filtered rows (of {len(df_all)} total in df_all_tasks) | Span: {date_span}",
        f"   - SurveyTask Columns: {t_cols}",
        f"   - Active status: {_top_vc(df_filt, 'status', 6)} | DB work_scope: {_top_vc(df_all, 'work_scope', 16)}",
        f"   - Active area: {_top_vc(df_filt, 'area', 12)} | instrument: {_top_vc(df_filt, 'instrument', 10)}",
        f"   - Active surveyor_name: {_top_vc(df_filt, 'surveyor_name', 12)} | Active users: {u_names}",
        f"   - df_activity (DataFrame): Recent UserActivityLog rows ({a_cols})",
        "   - Pre-loaded modules: pd, np, plt, matplotlib, PdfPages, Document (python-docx), openpyxl, datetime, date, timedelta, math, re, json, io, textwrap",
        "3. MULTI-FORMAT OUTPUT CONTRACT (AT END OF SCRIPT):",
        "   - Charts/PDF: Append figures to `OUTPUT_FIGS` (`OUTPUT_FIGS.append(fig)`). Never call `plt.show()` or `sys.exit()`.",
        "   - Excel (.xlsx): Set `OUTPUT_DF = df` (1 sheet) OR `OUTPUT_SHEETS = {'Summary': df1, 'Raw': df2}` OR `OUTPUT_XLSX_BYTES`.",
        "   - Word (.docx): Optional `OUTPUT_DOCX = doc` (`Document()`) or `OUTPUT_DOCX_BYTES` (if omitted, Studio auto-builds .docx from summary, table & figures).",
        '   - Metadata: Set `OUTPUT_SUMMARY = "..."` (1-2 line KPI headline) and `OUTPUT_FILENAME = f"{TODAY_YYYYMMDD}_DPR_<ShortName>.pdf"`.',
        "4. USER CUSTOM REPORT / CHART REQUEST:",
        req_txt,
    ])

# === PHASE 2: MULTI-FORMAT RUNNER & POSTGRESQL PRESETS ===
import openpyxl
from docx import Document
from docx.shared import Inches

_EXPORT_CACHE = {}
_MIMES = {"pdf": "application/pdf", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}

def get_dpr_export_file(token, fmt="pdf"):
    rec, ext = _EXPORT_CACHE.get(str(token or "")), str(fmt or "pdf").lower().lstrip(".")
    if not rec or ext not in _MIMES: return None, None, None
    if not rec.get(ext) and ext == "xlsx":
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            for k, d in rec["sheets"].items():
                sh = re.sub(r"[\[\]:*?/\\]", "_", str(k or "Sheet1"))[:31] or "Sheet1"
                (d if isinstance(d, pd.DataFrame) else pd.DataFrame(d)).to_excel(w, sheet_name=sh, index=False)
        rec["xlsx"] = buf.getvalue()
    elif not rec.get(ext) and ext == "docx":
        doc, df = Document(), rec["df"]
        doc.add_heading(rec["stem"], level=1)
        doc.add_paragraph(rec["summary"] or "")
        for p in rec["pngs"]: doc.add_picture(io.BytesIO(p), width=Inches(6.2))
        if isinstance(df, pd.DataFrame) and not df.empty:
            sub = df.head(40).fillna("").astype(str)
            rows_all = [list(sub.columns)] + sub.values.tolist()
            tbl = doc.add_table(rows=len(rows_all), cols=len(sub.columns))
            with contextlib.suppress(Exception): tbl.style = "Table Grid"
            for i, r in enumerate(rows_all):
                for j, v in enumerate(r): tbl.rows[i].cells[j].text = str(v)
        bd = io.BytesIO(); doc.save(bd); rec["docx"] = bd.getvalue()
    return rec.get(ext), f"{rec['stem']}.{ext}", _MIMES[ext]

def run_dpr_adhoc_script(script_code, SurveyTask, User=None, UserActivityLog=None, start_date="", end_date="", work_scope="", status_filter="", surveyor_name="Duty Surveyor", custom_filename=""):
    clean = re.sub(r"\n```\s*$", "", re.sub(r"^```(?:python|py)?\s*\n", "", str(script_code or "").strip(), flags=re.I)).strip()
    if not clean: return {"status": "error", "message": "Script is empty.", "logs": ""}
    plt.close("all")
    all_r, filt_r, df_all, df_filt = query_dpr_dataset(SurveyTask, start_date, end_date, work_scope, status_filter)
    act_q = UserActivityLog.query.order_by(UserActivityLog.id.desc()).limit(500).all() if UserActivityLog else []
    df_act = pd.DataFrame([{c.name: str(getattr(a, c.name) or "") for c in a.__table__.columns} for a in act_q])
    t_iso, t_ymd, out_buf = datetime.utcnow().strftime("%Y-%m-%d"), datetime.utcnow().strftime("%Y%m%d"), io.StringIO()
    ns = {k: globals()[k] for k in ("os", "io", "re", "gc", "json", "math", "textwrap", "datetime", "date", "timedelta", "np", "pd", "plt", "matplotlib", "PdfPages", "Document", "openpyxl")}
    ns.update({"__builtins__": __builtins__, "SURVEYOR_NAME": surveyor_name, "TODAY_ISO": t_iso, "TODAY_YYYYMMDD": t_ymd,
        "FILTER_INFO": {"start_date": start_date, "end_date": end_date, "work_scope": work_scope, "status": status_filter},
        "tasks": filt_r, "all_tasks": all_r, "df_tasks": df_filt.copy(), "df_all_tasks": df_all.copy(), "df_activity": df_act,
        "OUTPUT_FIGS": [], "OUTPUT_DF": None, "OUTPUT_SHEETS": None, "OUTPUT_SUMMARY": "", "OUTPUT_PDF_BYTES": None,
        "OUTPUT_XLSX_BYTES": None, "OUTPUT_DOCX": None, "OUTPUT_DOCX_BYTES": None, "OUTPUT_FILENAME": custom_filename or f"{t_ymd}_DPR_AdHoc.pdf"})
    try:
        with contextlib.redirect_stdout(out_buf): exec(compile(clean, "<dpr_adhoc>", "exec"), ns, ns)
    except Exception:
        tb = traceback.format_exc(); plt.close("all"); gc.collect()
        return {"status": "error", "message": "Script execution failed.", "logs": (out_buf.getvalue() + "\n" + tb).strip()}
    raw_fn = os.path.basename(str(custom_filename or ns.get("OUTPUT_FILENAME") or "DPR_AdHoc"))
    stem = re.sub(r"\.(pdf|xlsx|docx)$", "", re.sub(r"[^A-Za-z0-9_ .()-]", "_", raw_fn), flags=re.I)
    stem = stem if re.match(r"^\d{8}_", stem) else f"{t_ymd}_{stem}"
    surv = re.sub(r"[^A-Za-z0-9 ._-]", "", str(surveyor_name or "")).strip()
    stem = f"{stem}_({surv})" if surv and surv.lower() not in ("duty surveyor", "surveyor") and f"({surv})" not in stem else stem
    sheets = ns["OUTPUT_SHEETS"] if isinstance(ns.get("OUTPUT_SHEETS"), dict) and ns["OUTPUT_SHEETS"] else None
    out_df = ns["OUTPUT_DF"] if isinstance(ns.get("OUTPUT_DF"), pd.DataFrame) else (pd.DataFrame(next(iter(sheets.values()))) if sheets else df_filt)
    sheets = sheets or {"Report": out_df}
    figs = list(ns.get("OUTPUT_FIGS") or []) or [plt.figure(n) for n in plt.get_fignums()]
    summary = str(ns.get("OUTPUT_SUMMARY") or f"Rows: {len(out_df)} | Date: {t_iso}").strip()
    if not figs and not ns.get("OUTPUT_PDF_BYTES"):
        fa, ax = plt.subplots(figsize=(11.69, 8.27), dpi=150); ax.axis("off"); ax.set_title(f"{stem}\n{summary}", fontsize=10, fontweight="bold")
        if not out_df.empty:
            st = out_df.head(20).fillna("").astype(str)
            tb_m = ax.table(cellText=st.values, colLabels=st.columns, loc="center", cellLoc="left"); tb_m.auto_set_font_size(False); tb_m.set_fontsize(7.5)
        figs = [fa]
    pngs = [b.getvalue() for f in figs for b in (io.BytesIO(),) if f.savefig(b, format="png", dpi=130, bbox_inches="tight") is None]
    bp = io.BytesIO()
    if figs and not ns.get("OUTPUT_PDF_BYTES"):
        with PdfPages(bp) as pp:
            for f in figs: pp.savefig(f, dpi=150, bbox_inches="tight")
    pdf_b, docx_b = ns.get("OUTPUT_PDF_BYTES") or bp.getvalue(), ns.get("OUTPUT_DOCX_BYTES")
    plt.close("all"); gc.collect()
    if not docx_b and ns.get("OUTPUT_DOCX") is not None:
        bd = io.BytesIO(); ns["OUTPUT_DOCX"].save(bd); docx_b = bd.getvalue()
    now, tok = time.time(), uuid.uuid4().hex[:12]
    for k in [k for k, v in list(_EXPORT_CACHE.items()) if now - v["ts"] > 3600] + list(_EXPORT_CACHE.keys())[:-14]: _EXPORT_CACHE.pop(k, None)
    _EXPORT_CACHE[tok] = {"ts": now, "stem": stem, "pdf": pdf_b, "xlsx": ns.get("OUTPUT_XLSX_BYTES"), "docx": docx_b, "pngs": pngs, "sheets": sheets, "df": out_df, "summary": summary}
    tbl_h = out_df.head(20).fillna("").to_html(index=False, classes="table table-sm table-bordered table-striped mb-0 small") if not out_df.empty else ""
    return {"status": "ok", "token": tok, "filename_stem": stem, "page_count": max(1, len(pngs)), "row_count": int(len(out_df)), "summary": summary,
            "image_b64": base64.b64encode(pngs[0]).decode("ascii") if pngs else "", "table_html": tbl_h, "logs": out_buf.getvalue().strip() or f"Rendered {max(1, len(pngs))} page(s) -> {stem}"}

def manage_dpr_presets(db, AppConfig, action="list", item=None):
    cfg, blob = AppConfig.query.first() or AppConfig(schema_data="{}"), {}
    if not cfg.id: db.session.add(cfg)
    with contextlib.suppress(Exception): blob = json.loads(cfg.schema_data or "{}")
    if not isinstance(blob, dict): blob = {}
    presets = list(blob.get("dpr_adhoc_presets") or [])
    if action == "save" and isinstance(item, dict):
        pid = uuid.uuid4().hex[:8] if item.get("id") in (None, "", "starter_kpi") else str(item["id"])
        entry = {"id": pid, "name": str(item.get("name") or "Custom Preset").strip()[:80], "prompt": str(item.get("prompt") or ""),
                 "script": str(item.get("script") or ""), "author": str(item.get("author") or ""), "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M")}
        presets = [p for p in presets if p.get("id") != pid] + [entry]
        blob["dpr_adhoc_presets"] = presets; cfg.schema_data = json.dumps(blob); db.session.commit()
    elif action == "delete" and item:
        presets = [p for p in presets if p.get("id") != str(item)]
        blob["dpr_adhoc_presets"] = presets; cfg.schema_data = json.dumps(blob); db.session.commit()
    starter = {"id": "starter_kpi", "name": "Starter: Scope & Surveyor KPI Summary", "prompt": "Executive KPI summary by work_scope and surveyor.", "script": STARTER_DPR_ADHOC_SCRIPT, "builtin": True}
    return [starter] + presets

# === PHASE 3: FLASK BLUEPRINT FACTORY ===
from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user

def create_dpr_adhoc_blueprint(db, SurveyTask, User=None, UserActivityLog=None, AppConfig=None):
    bp = Blueprint("dpr_adhoc", __name__)
    _surv = lambda: getattr(current_user, "name", None) or getattr(current_user, "email", None) or "Duty Surveyor"

    @bp.route("/api/dpr_adhoc/meta", methods=["GET"])
    @login_required
    def api_meta():
        _, _, df_all, _ = query_dpr_dataset(SurveyTask)
        scopes = sorted([s for s in df_all["work_scope"].dropna().unique().tolist() if str(s).strip()]) if not df_all.empty else []
        presets = manage_dpr_presets(db, AppConfig, "list") if AppConfig else []
        return jsonify({"status": "ok", "scopes": scopes, "presets": presets, "starter_script": STARTER_DPR_ADHOC_SCRIPT})

    @bp.route("/api/dpr_adhoc/context", methods=["POST"])
    @login_required
    def api_context():
        d = request.get_json(silent=True) or {}
        prompt = build_dpr_gemini_prompt(
            SurveyTask, User=User, UserActivityLog=UserActivityLog, user_request=d.get("user_request", ""),
            start_date=d.get("start_date", ""), end_date=d.get("end_date", ""),
            work_scope=d.get("work_scope", ""), status_filter=d.get("status_filter", ""), surveyor_name=_surv()
        )
        return jsonify({"status": "ok", "prompt": prompt})

    @bp.route("/api/dpr_adhoc/run", methods=["POST"])
    @login_required
    def api_run():
        d = request.get_json(silent=True) or {}
        res = run_dpr_adhoc_script(
            d.get("script_code", ""), SurveyTask, User=User, UserActivityLog=UserActivityLog,
            start_date=d.get("start_date", ""), end_date=d.get("end_date", ""),
            work_scope=d.get("work_scope", ""), status_filter=d.get("status_filter", ""),
            surveyor_name=_surv(), custom_filename=d.get("custom_filename", "")
        )
        return jsonify(res), (200 if res.get("status") == "ok" else 400)

    @bp.route("/api/dpr_adhoc/download/<token>", methods=["GET"])
    @login_required
    def api_download(token):
        fmt = request.args.get("fmt", "pdf")
        data, fname, mime = get_dpr_export_file(token, fmt)
        if not data:
            return jsonify({"status": "error", "message": "Export token expired or invalid. Re-run script."}), 404
        return send_file(io.BytesIO(data), mimetype=mime, as_attachment=True, download_name=fname)

    @bp.route("/api/dpr_adhoc/presets", methods=["GET", "POST"])
    @login_required
    def api_presets():
        if not AppConfig:
            return jsonify({"status": "error", "message": "AppConfig unavailable"}), 500
        if request.method == "GET":
            return jsonify({"status": "ok", "presets": manage_dpr_presets(db, AppConfig, "list")})
        d = request.get_json(silent=True) or {}
        act = d.get("action", "list")
        payload = {**d, "author": _surv()} if act == "save" else d.get("id")
        return jsonify({"status": "ok", "presets": manage_dpr_presets(db, AppConfig, act, payload)})

    return bp
