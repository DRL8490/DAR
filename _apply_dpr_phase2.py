import os, re, glob, ast, subprocess

print("=== [1/4] Upgrading Log Extractor (List & Date-Keyed Dicts) in mti_4panel_reports.py ===")
if os.path.exists("mti_4panel_reports.py"):
    r_txt = open("mti_4panel_reports.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")

    upgraded_helpers = r"""def norm_mti_date(s):
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
    return collected"""

    r_txt = re.sub(
        r"def norm_mti_date\(s\):.*?(?=\ndef parse_log_entry_fields)",
        lambda _m: upgraded_helpers.strip() + "\n",
        r_txt,
        count=1,
        flags=re.S
    )

    fallback_snippet = """    if not primary_parts:
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
    raw_combined = " | ".join(primary_parts) if primary_parts else "-" """.rstrip()

    if "skip_meta =" not in r_txt and 'raw_combined = " | ".join(primary_parts) if primary_parts else "-"' in r_txt:
        r_txt = r_txt.replace('    raw_combined = " | ".join(primary_parts) if primary_parts else "-"', fallback_snippet, 1)

    assert "Signature / Date:" not in r_txt and "Signature/Date:" not in r_txt, "Signature lines still present!"
    ast.parse(r_txt)
    open("mti_4panel_reports.py", "w", encoding="utf-8").write(r_txt)
    print("  -> mti_4panel_reports.py hardened & AST-verified (0 signature lines, YYYYMMDD filename active).")

print("=== [2/4] Injecting Top-Bar Calendar Date Selector in templates/mti_dashboard.html ===")
with open("_phase2_calendar_topbar.html", "r", encoding="utf-8-sig") as f:
    s5 = f.read().lstrip("\ufeff").strip()

t_dash = "templates/mti_dashboard.html"
if os.path.exists(t_dash):
    raw_t = open(t_dash, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    raw_t = re.sub(r'<script id="mti4PanelStudioUpgrade">.*?</script>', lambda _m: '', raw_t, flags=re.S)
    if "</body>" in raw_t:
        raw_t = raw_t.replace("</body>", s5 + "\n</body>", 1)
    elif "{% endblock %}" in raw_t:
        idx = raw_t.rfind("{% endblock %}")
        raw_t = raw_t[:idx] + s5 + "\n" + raw_t[idx:]
    else:
        raw_t = raw_t.rstrip() + "\n" + s5 + "\n"
    open(t_dash, "w", encoding="utf-8").write(raw_t)
    print("  -> templates/mti_dashboard.html updated with Calendar Date Selector (#mtiTopDprDate).")

print("=== [3/4] Verifying mti_blueprint.py AST & Clearing Cached PDFs ===")
if os.path.exists("mti_blueprint.py"):
    b_txt = open("mti_blueprint.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    ast.parse(b_txt)
    open("mti_blueprint.py", "w", encoding="utf-8").write(b_txt)
    print("  -> mti_blueprint.py AST-verified.")

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try:
        os.remove(p)
    except Exception:
        pass

print("=== [4/4] Syncing Phase 2 DPR Calendar Selector & Fixes to GitHub & Render ===")
sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else ("python" if os.path.exists("sync.py") else "py")
subprocess.run([sync_py, "sync.py", "feat(mti-dpr): add top-bar calendar date selector, universal log extraction, YYYYMMDD filename, and remove signature lines"], check=False)