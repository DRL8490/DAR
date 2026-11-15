import os, re, ast, subprocess

# === 1. UPDATE mti_blueprint.py (Sync Checkbox Support for Event Logs -> SurveyTask) ===
bp_path = "mti_blueprint.py"
if not os.path.exists(bp_path):
    raise SystemExit("mti_blueprint.py not found! Run inside your DAR project folder.")

bp = open(bp_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")

evt_kpi_helpers = """# --- MTI_EVT_KPI_CHECKBOX_START ---
def _map_event_to_kpi_meta(evt_type):
    et = str(evt_type or "").strip()
    et_low = et.lower()
    if "calib" in et_low or "setup" in et_low or "tbt" in et_low:
        return ("CONFIGURE", "Equipment Configuration", "Survey Software Configuration", "USBL", "MMA Prestige Setup")
    if "issue" in et_low:
        return ("CHECK", "Equipment Configuration", "System Check", "USBL", "MMA Prestige Issue")
    if et in ("Pole down", "Pole up", "ADCP input"):
        return ("CHECK", "Equipment Configuration", "System Check", "USBL", f"MMA Prestige {et}")
    return ("VERIFY", "Bathymetric Survey", "Check Survey", "USBL", f"MMA Prestige {et}")

def _remove_event_log_from_surveytask(log_id, surveytask_id=None):
    try:
        from app import SurveyTask, db
        removed = False
        if surveytask_id:
            t_id = SurveyTask.query.get(int(surveytask_id))
            if t_id:
                db.session.delete(t_id); removed = True
        marker = f"[MTI_EVT_ID:{log_id}]"
        for t in SurveyTask.query.filter(SurveyTask.sub_location == "338_Subsea_Crossings").all():
            if marker in str(t.remarks or ""):
                db.session.delete(t); removed = True
        if removed:
            db.session.commit()
    except Exception:
        pass

def _upsert_event_log_to_surveytask(entry):
    log_id = entry.get("id")
    if not entry.get("sync_to_kpi"):
        _remove_event_log_from_surveytask(log_id, entry.get("surveytask_id"))
        entry.pop("surveytask_id", None)
        return False

    from app import SurveyTask, db
    evt_t = str(entry.get("event_type") or "Calib, Setup & TBT").strip()
    if evt_t.lower() == "mattress fix":
        return False

    exec_dt, evt_dt = _parse_mti_fix_dt(entry.get("timestamp"))
    fake_fix = {"surveyor_name": entry.get("surveyor") or "", "install_date": entry.get("timestamp") or ""}
    if "_resolve_kpi_assigned_surveyor" in globals():
        kpi_user, full_surv = _resolve_kpi_assigned_surveyor(fake_fix, [])
    else:
        kpi_user = str(entry.get("surveyor") or getattr(current_user, "name", "Daryll Enano")).strip()
        full_surv = kpi_user

    cmd_v, t_cat, act_req, inst, pfx_lbl = _map_event_to_kpi_meta(evt_t)
    val1_clean = re.sub(r"\\s*\\[[^\\]]+\\]", "", str(entry.get("val1") or "").strip()).strip()
    ref_clean = str(entry.get("ref_id") or "").strip()
    act_headline = val1_clean or ref_clean or evt_t
    opening_str = f"{pfx_lbl}: {act_headline} ({ref_clean})" if (ref_clean and ref_clean.upper() not in act_headline.upper() and len(act_headline) < 75) else f"{pfx_lbl}: {act_headline}"

    val2_s = str(entry.get("val2") or "").strip()
    rem_s = str(entry.get("remarks") or "").strip()
    closing_bits = []
    if val2_s and val2_s.lower() not in rem_s.lower():
        closing_bits.append(val2_s)
    if rem_s and rem_s.lower() != act_headline.lower():
        closing_bits.append(rem_s)
    closing_bits.extend([f"Logged by {full_surv}", f"[MTI_EVT_ID:{log_id}]"])
    full_rem = f"{opening_str} | Closed: {' ; '.join(closing_bits)}"

    marker = f"[MTI_EVT_ID:{log_id}]"
    existing_t = None
    if entry.get("surveytask_id"):
        try: existing_t = SurveyTask.query.get(int(entry["surveytask_id"]))
        except Exception: existing_t = None
    if not existing_t:
        for t in SurveyTask.query.filter(SurveyTask.sub_location == "338_Subsea_Crossings").all():
            if marker in str(t.remarks or ""):
                existing_t = t; break

    if existing_t:
        existing_t.surveyor_name = kpi_user
        existing_t.assigned_to = kpi_user
        existing_t.command_verb = cmd_v
        existing_t.task_category = t_cat
        existing_t.action_required = act_req
        existing_t.instrument = inst
        existing_t.execution_date = exec_dt
        existing_t.start_time = evt_dt
        existing_t.end_time = evt_dt
        existing_t.remarks = full_rem
        existing_t.status = "Closed"
        db.session.flush()
        entry["surveytask_id"] = existing_t.id
    else:
        new_t = SurveyTask(
            surveyor_name=kpi_user, assigned_to=kpi_user, requestor="Offshore - Walaa Ezzat Gomaa",
            command_verb=cmd_v, task_category=t_cat, action_required=act_req, instrument=inst,
            area="300_Marine", location="330_Offshore", sub_location="338_Subsea_Crossings",
            work_scope="338-00_OS_Subsea_Crossings", remarks=full_rem, status="Closed",
            is_urgent=False, priority=99, start_time=evt_dt, execution_date=exec_dt, end_time=evt_dt
        )
        db.session.add(new_t)
        db.session.flush()
        entry["surveytask_id"] = new_t.id
    return True
# --- MTI_EVT_KPI_CHECKBOX_END ---"""

if "def _parse_mti_fix_dt(" not in bp:
    fallback_dt_fn = """def _parse_mti_fix_dt(dt_raw, fallback_ymd=None):
    s = re.sub(r"\\s+", " ", str(dt_raw or "").replace("T", " ").strip())
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d"):
        try:
            dt_obj = datetime.strptime(s[:len(fmt) + 2].strip(), fmt)
            return dt_obj.date(), dt_obj
        except Exception:
            pass
    m_iso = re.search(r"(\\d{4}-\\d{2}-\\d{2})", s)
    ymd = m_iso.group(1) if m_iso else (fallback_ymd or datetime.utcnow().strftime("%Y-%m-%d"))
    m_hm = re.search(r"(\\d{1,2}):(\\d{2})", s)
    hh, mm = (int(m_hm.group(1)), int(m_hm.group(2))) if m_hm else (0, 0)
    dt_obj = datetime.strptime(f"{ymd} {hh:02d}:{mm:02d}", "%Y-%m-%d %H:%M")
    return dt_obj.date(), dt_obj
"""
    evt_kpi_helpers = fallback_dt_fn + "\n" + evt_kpi_helpers

if "# --- MTI_EVT_KPI_CHECKBOX_START ---" in bp:
    bp = re.sub(r"# --- MTI_EVT_KPI_CHECKBOX_START ---.*?# --- MTI_EVT_KPI_CHECKBOX_END ---", lambda _m: evt_kpi_helpers, bp, count=1, flags=re.S)
else:
    bp = bp.replace("@mti_bp.route('/add_input_log', methods=['POST'])", evt_kpi_helpers + "\n\n@mti_bp.route('/add_input_log', methods=['POST'])", 1)

new_event_routes = """@mti_bp.route('/add_input_log', methods=['POST'])
@login_required
def add_input_log():
    state = load_mti_state()
    input_logs = state.get("input_logs", [])
    log_id = request.form.get("log_id", type=int)
    existing = next((x for x in input_logs if int(x.get("id", 0)) == log_id), None) if log_id else None

    evt_t = (request.form.get("event_type") or "Pole down").strip()
    usbl_s = (request.form.get("usbl_sensor") or "").strip() if evt_t in ("ROV & Vessel Ops", "Calib, Setup & TBT", "Survey Issue Reporting", "Survey Issue") else ""
    env_w = fmt_knots(request.form.get("env_wind") or "") if "fmt_knots" in globals() else (request.form.get("env_wind") or "").strip()
    env_c = fmt_knots(request.form.get("env_current") or "") if "fmt_knots" in globals() else (request.form.get("env_current") or "").strip()
    env_s = (request.form.get("env_swell") or "").strip()
    env_tag = " | ".join([f"{k}:{v}" for k, v in [("USBL", usbl_s), ("Wind", env_w), ("Curr", env_c)] if v])
    raw_rem = (request.form.get("remarks") or "").strip()
    clean_rem = re.sub(r"(?:\\s*\\[(?:USBL:[^\\]]*\\|?\\s*)?(?:Wind:[^\\]]*|Curr:[^\\]]*)\\])+\\s*$", "", raw_rem, flags=re.I).strip()
    if usbl_s and f"[USBL:{usbl_s}]" in clean_rem and env_tag:
        clean_rem = clean_rem.replace(f"[USBL:{usbl_s}]", "").strip()
    rem = f"{clean_rem} [{env_tag}]".strip() if (env_tag and env_tag not in clean_rem) else clean_rem

    sync_kpi_chk = str(request.form.get("sync_to_kpi") or "").strip().lower() in ("true", "1", "on", "yes")
    raw_surv = (request.form.get("surveyor") or getattr(current_user, "name", "Surveyor")).strip()
    surv_clean = resolve_full_surveyor_name(raw_surv) if "resolve_full_surveyor_name" in globals() else raw_surv

    entry = {
        "id": int(existing["id"]) if existing else (max([int(x.get("id", 0)) for x in input_logs] + [0]) + 1),
        "event_type": evt_t,
        "timestamp": (request.form.get("timestamp") or datetime.utcnow().strftime('%Y-%m-%d %H:%M')).strip(),
        "surveyor": surv_clean,
        "ref_id": (request.form.get("ref_id") or "").strip(),
        "val1": (request.form.get("val1") or "").strip(),
        "val2": (request.form.get("val2") or "").strip(),
        "usbl_sensor": usbl_s,
        "env_wind": env_w, "env_current": env_c, "env_swell": env_s,
        "remarks": rem,
        "sync_to_kpi": sync_kpi_chk,
    }
    if existing and existing.get("surveytask_id"):
        entry["surveytask_id"] = existing["surveytask_id"]

    kpi_synced = False
    try:
        from app import db as _db_ev
        kpi_synced = _upsert_event_log_to_surveytask(entry)
        if kpi_synced:
            _db_ev.session.commit()
    except Exception:
        kpi_synced = False

    if existing:
        input_logs[input_logs.index(existing)] = entry
    else:
        input_logs.append(entry)
    state["input_logs"] = input_logs
    save_mti_state(state)

    kpi_note = " & synced to KPI/DPR Register" if kpi_synced else ""
    flash(f"Saved '{entry['event_type']}' at {entry['timestamp']}{kpi_note}!", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/delete_input_log/<int:log_id>', methods=['POST'])
@login_required
def delete_input_log(log_id):
    state = load_mti_state()
    logs = state.get("input_logs", [])
    target = next((x for x in logs if int(x.get("id", 0)) == log_id), None)
    if target:
        _remove_event_log_from_surveytask(log_id, target.get("surveytask_id"))
    state["input_logs"] = [x for x in logs if int(x.get("id", 0)) != log_id]
    save_mti_state(state)
    flash("Removed event from Survey Input Log & KPI Register.", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))"""

bp, n_evr = re.subn(
    r"@mti_bp\.route\('/add_input_log',\s*methods=\['POST'\]\)\s*\n@login_required\s*\ndef add_input_log\(\):.*?(?=\n@mti_bp\.route\('/update_targets')",
    lambda _m: new_event_routes + "\n", bp, count=1, flags=re.S
)
if not n_evr:
    raise SystemExit("Could not locate add_input_log / delete_input_log in mti_blueprint.py!")

if "target_evts =" not in bp and "def sync_to_dpr():" in bp:
    old_sync_tail = """    if not target_fixes:
        flash(f"No confirmed (Completed) Mattress Fixes found on {'the MTI Ledger' if sync_mode == 'all_fixes' else sync_date_str} to sync.", "error")
        return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

    synced_cnt = 0"""
    new_sync_tail = """    target_evts = [
        lg for lg in in_logs
        if lg.get("sync_to_kpi") and str(lg.get("event_type") or "").strip().lower() != "mattress fix"
        and (sync_mode == "all_fixes" or _parse_mti_fix_dt(lg.get("timestamp"))[0].strftime("%Y-%m-%d") == sync_date_str)
    ]

    if not target_fixes and not target_evts:
        flash(f"No confirmed Mattress Fixes or KPI-checked events found on {'the MTI Ledger' if sync_mode == 'all_fixes' else sync_date_str} to sync.", "error")
        return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

    synced_cnt = 0
    for lg_e in target_evts:
        if _upsert_event_log_to_surveytask(lg_e):
            synced_cnt += 1"""
    bp = bp.replace(old_sync_tail, new_sync_tail, 1)

ast.parse(bp)
open(bp_path, "w", encoding="utf-8").write(bp)
print("  -> Updated mti_blueprint.py (Event KPI/DPR checkbox sync + auto edit/delete cleanup, AST OK)")

# === 2. UPDATE templates/mti_dashboard.html (Checkbox + KPI Badge + Default-On Rules) ===
for dash_path in ("templates/mti_dashboard.html", "mti_dashboard.html"):
    if os.path.exists(dash_path):
        dh = open(dash_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
        dh_orig = dh
        new_evt_hdr = """                            <div class="d-flex flex-wrap justify-content-between align-items-center mb-2 gap-2">
                                <h6 class="fw-bold text-primary mb-0" id="evtBoxTitle">Log Event: Pole down</h6>
                                <div class="d-flex align-items-center gap-3">
                                    <div class="form-check form-switch mb-0">
                                        <input class="form-check-input" type="checkbox" name="sync_to_kpi" id="chkEvtSyncKpi" value="true">
                                        <label class="form-check-label small fw-bold text-dark" for="chkEvtSyncKpi" title="Creates/updates an individual SurveyTask entry in the KPI &amp; DPR Master Register">Sync to KPI / DPR Master Reg.</label>
                                    </div>
                                    <button type="button" class="btn-close small" onclick="document.getElementById('dynamicEventBox').style.display='none';"></button>
                                </div>
                            </div>"""
        if 'id="chkEvtSyncKpi"' not in dh:
            dh = re.sub(
                r'<div class="d-flex[^>]*>\s*<h6 class="fw-bold text-primary mb-0" id="evtBoxTitle">Log Event: Pole down</h6>\s*<button type="button" class="btn-close small" onclick="document\.getElementById\(\'dynamicEventBox\'\)\.style\.display=\'none\';"></button>\s*</div>',
                lambda _m: new_evt_hdr, dh, count=1, flags=re.S
            )
        if "il.sync_to_kpi" not in dh:
            dh = dh.replace(
                '{% if il.ref_id %}\n                                            <span class="badge bg-secondary ms-1">{{ il.ref_id }}</span>\n                                        {% endif %}',
                '{% if il.ref_id %}\n                                            <span class="badge bg-secondary ms-1">{{ il.ref_id }}</span>\n                                        {% endif %}\n                                        {% if il.sync_to_kpi or is_fix %}\n                                            <span class="badge bg-warning text-dark ms-1" title="Synced to KPI &amp; DPR Master Register">KPI</span>\n                                        {% endif %}', 1
            )
        if 'data-kpi="{{' not in dh:
            dh = dh.replace('data-rem="{{ il.remarks }}"', 'data-rem="{{ il.remarks }}"\n                                                data-kpi="{{ \'true\' if il.sync_to_kpi else \'false\' }}"', 1)
        if "chkEvtSyncKpi" in dh and "const kpiChk = document.getElementById('chkEvtSyncKpi');" not in dh:
            dh = dh.replace(
                "document.getElementById('evtBoxTitle').innerText = 'Log Event: ' + evtType;",
                "document.getElementById('evtBoxTitle').innerText = 'Log Event: ' + evtType;\n        const kpiChk = document.getElementById('chkEvtSyncKpi');\n        if (kpiChk) kpiChk.checked = (evtType === 'Calib, Setup & TBT' || evtType === 'Survey Issue Reporting' || evtType === 'Survey Issue');", 1
            )
            dh = dh.replace(
                "document.getElementById('evtBoxTitle').innerText = 'Edit Event: ' + d.type;",
                "document.getElementById('evtBoxTitle').innerText = 'Edit Event: ' + d.type;\n        const kpiChkEd = document.getElementById('chkEvtSyncKpi');\n        if (kpiChkEd) kpiChkEd.checked = (d.kpi === 'true');", 1
            )
        if dh != dh_orig:
            open(dash_path, "w", encoding="utf-8").write(dh)
            print(f"  -> Updated {dash_path} (Added Sync to KPI / DPR checkbox, default-on rules & KPI badge)")

# === 3. UPDATE templates/mti_mobile.html (Mobile Event Sync Checkbox Parity) ===
for mob_path in ("templates/mti_mobile.html", "mti_mobile.html"):
    if os.path.exists(mob_path):
        mh = open(mob_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
        mh_orig = mh
        mob_kpi_row = '<div class="form-check form-switch mb-2 p-2 ps-5 rounded border border-warning" style="background:rgba(250,204,21,0.08);"><input class="form-check-input" type="checkbox" name="sync_to_kpi" id="mChkEvtSyncKpi" value="true"><label class="form-check-label small fw-bold text-warning" for="mChkEvtSyncKpi">Sync to KPI / DPR Master Reg.</label></div>'
        if 'id="mChkEvtSyncKpi"' not in mh:
            mh = mh.replace('<button type="submit" class="btn btn-info fw-bold w-100 py-2">Save Log</button>', mob_kpi_row + '\n      <button type="submit" class="btn btn-info fw-bold w-100 py-2">Save Log</button>', 1)
        if "mChkEvtSyncKpi" in mh and "getElementById('mChkEvtSyncKpi')" not in mh:
            mh = mh.replace(
                "document.getElementById('mEvtTitle').innerText = 'Log Event: ' + t;",
                "document.getElementById('mEvtTitle').innerText = 'Log Event: ' + t;\n  const mKpi = document.getElementById('mChkEvtSyncKpi'); if (mKpi) mKpi.checked = (t === 'Calib, Setup & TBT' || t === 'Survey Issue Reporting' || t === 'Survey Issue');", 1
            )
        if mh != mh_orig:
            open(mob_path, "w", encoding="utf-8").write(mh)
            print(f"  -> Updated {mob_path} (Added Mobile Sync to KPI / DPR checkbox)")

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti-kpi): add Sync to KPI/DPR checkbox for milestone shift events"], check=False)
print("\nSYNC TO KPI / DPR CHECKBOX COMPLETE & PUSHED TO RENDER!")