import os, re, ast, subprocess

bp_path = "mti_blueprint.py"
if not os.path.exists(bp_path):
    raise SystemExit("mti_blueprint.py not found! Run inside your DAR project folder.")

bp = open(bp_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")

per_fix_kpi_block = """# --- MTI_ONE_LOG_PER_CONFIRMED_FIX_START ---
def _parse_mti_fix_dt(dt_raw, fallback_ymd=None):
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

def _resolve_kpi_assigned_surveyor(entry, input_logs=None):
    box_up = str(entry.get("design_box_id") or "").strip().upper()
    tag_up = str(entry.get("physical_tag") or "").strip().upper().replace("#", "")
    dt_ymd = str(entry.get("install_date") or "").strip()[:10]
    cand = str(entry.get("input_by") or entry.get("surveyor_name") or entry.get("surveyor") or "").strip()
    if cand.lower() in ("duty surveyor", "surveyor", "unknown", "none"):
        cand = ""

    if not cand and input_logs:
        for lg in input_logs:
            if str(lg.get("event_type") or "").strip().lower() != "mattress fix":
                continue
            ref_up = str(lg.get("ref_id") or "").upper()
            if (box_up and re.search(rf"(?<![A-Za-z0-9_-]){re.escape(box_up)}(?![0-9])", ref_up)) or (tag_up and tag_up in ref_up):
                s_lg = str(lg.get("surveyor") or lg.get("surveyor_name") or "").strip()
                if s_lg and s_lg.lower() not in ("duty surveyor", "surveyor"):
                    cand = s_lg; break

    if not cand and input_logs:
        for lg in input_logs:
            blob_up = f"{lg.get('ref_id','')} {lg.get('val1','')} {lg.get('remarks','')}".upper()
            if str(lg.get("timestamp") or "").strip()[:10] == dt_ymd and ((box_up and box_up in blob_up) or (tag_up and len(tag_up) >= 3 and tag_up in blob_up)):
                s_lg = str(lg.get("surveyor") or lg.get("surveyor_name") or "").strip()
                if s_lg and s_lg.lower() not in ("duty surveyor", "surveyor"):
                    cand = s_lg; break

    cand = cand or str(getattr(current_user, "name", "Daryll Enano") or "Daryll Enano").strip()
    full_disp = resolve_full_surveyor_name(cand) if "resolve_full_surveyor_name" in globals() else cand

    try:
        from app import User
        users_db = User.query.all()
    except Exception:
        users_db = []

    c_low = cand.lower()
    exp_tokens = {w for w in re.split(r"[^a-z0-9]+", c_low) if w}
    for aset in ({"abror", "mohamad", "hediarto"}, {"roderick", "gonzales", "clavel"}, {"daryll", "esternon", "enano"}, {"danilo", "bartolome"}, {"mateo", "mollaneda"}, {"renante", "bacalan"}, {"min", "ying", "tsai"}):
        if exp_tokens & aset:
            exp_tokens |= aset

    for u in users_db:
        un = str(getattr(u, "name", "") or "").strip()
        if un and un.lower() in (c_low, full_disp.lower()):
            return un, full_disp

    best_un, best_sc = "", 0
    for u in users_db:
        un = str(getattr(u, "name", "") or "").strip()
        if not un:
            continue
        u_toks = {w for w in re.split(r"[^a-z0-9]+", f"{un} {getattr(u, 'username', '')} {getattr(u, 'email', '')}".lower()) if w}
        un_toks = {w for w in re.split(r"[^a-z0-9]+", un.lower()) if w}
        sc = len(exp_tokens & un_toks) * 10 + len(exp_tokens & u_toks)
        if sc > best_sc:
            best_sc, best_un = sc, un

    return (best_un if (best_un and best_sc >= 10) else full_disp), full_disp

def _sync_fix_to_mti_input_logs(input_logs, entry):
    logs = list(input_logs or [])
    box_id = str(entry.get("design_box_id") or "").strip()
    box_up, tag_id = box_id.upper(), str(entry.get("physical_tag") or "").strip()
    usbl_s = str(entry.get("usbl_sensor") or "Survey Pole").strip()
    match_idx = next((i for i, lg in enumerate(logs) if str(lg.get("event_type") or "").strip().lower() == "mattress fix" and box_up and re.search(rf"(?<![A-Za-z0-9_-]){re.escape(box_up)}(?![0-9])", str(lg.get("ref_id") or "").upper())), None)
    if str(entry.get("status") or "Completed").strip().lower() != "completed":
        if match_idx is not None: logs.pop(match_idx)
        return logs
    _, full_surv = _resolve_kpi_assigned_surveyor(entry, logs)
    new_lg = {
        "id": int(logs[match_idx].get("id", 0)) if match_idx is not None else (max([int(x.get("id", 0)) for x in logs] + [0]) + 1),
        "event_type": "Mattress fix", "timestamp": str(entry.get("install_date") or datetime.utcnow().strftime("%Y-%m-%d %H:%M")).strip(),
        "surveyor": full_surv, "ref_id": f"{box_id} ({tag_id}) [{usbl_s}]",
        "val1": f"Act E:{float(entry.get('aslaid_e') or 0):.3f}, N:{float(entry.get('aslaid_n') or 0):.3f}, Z:{float(entry.get('aslaid_z') or 0):.2f} (dCL:{float(entry.get('cl_offset_m') or 0):.2f}m)",
        "val2": f"Brg:{float(entry.get('heading_deg') or 0):.1f} deg | {entry.get('gap_labels') or 'N/A'}",
        "usbl_sensor": usbl_s, "env_wind": str(entry.get("env_wind") or ""), "env_current": str(entry.get("env_current") or ""), "remarks": str(entry.get("remarks") or ""),
    }
    if match_idx is not None: logs[match_idx] = new_lg
    else: logs.append(new_lg)
    return logs

def _remove_fix_from_dpr_and_logs(box_id, unit_no=None, state=None):
    box_up = str(box_id or "").strip().upper()
    if isinstance(state, dict) and box_up:
        state["input_logs"] = [lg for lg in (state.get("input_logs") or []) if not (str(lg.get("event_type") or "").strip().lower() == "mattress fix" and re.search(rf"(?<![A-Za-z0-9_-]){re.escape(box_up)}(?![0-9])", str(lg.get("ref_id") or "").upper()))]
    try:
        from app import SurveyTask, db
        removed = False
        for t in SurveyTask.query.filter(SurveyTask.sub_location == "338_Subsea_Crossings").all():
            rem_t = str(t.remarks or "")
            if "MMA Prestige Mattress Fix Confirmed" in rem_t and ((box_up and f": {box_up} (" in rem_t.upper()) or (unit_no and f"Unit #{unit_no}:" in rem_t)):
                db.session.delete(t); removed = True
        if removed: db.session.commit()
    except Exception:
        pass

def _upsert_confirmed_fix_to_surveytask(entry, skip_if_manual_exists=False, input_logs=None):
    if str(entry.get("status") or "Completed").strip().lower() != "completed":
        _remove_fix_from_dpr_and_logs(entry.get("design_box_id"), entry.get("unit_no"))
        return False
    from app import SurveyTask, db
    unit_no = int(float(entry.get("unit_no") or 1))
    box_id = str(entry.get("design_box_id") or f"CR-A1_M{unit_no}").strip()
    box_up, tag_id = box_id.upper(), (str(entry.get("physical_tag") or "").strip() or "N/A")
    usbl_s = str(entry.get("usbl_sensor") or "Survey Pole").strip()
    exec_dt, fix_dt = _parse_mti_fix_dt(entry.get("install_date"))
    kpi_assigned_user, full_surv = _resolve_kpi_assigned_surveyor(entry, input_logs)

    raw_rem = str(entry.get("remarks") or "").strip()
    clean_note = _strip_auto_rem_tags(raw_rem) if "_strip_auto_rem_tags" in globals() else raw_rem
    opening_str = f"MMA Prestige Mattress Fix Confirmed - Unit #{unit_no}: {box_id} ({tag_id})"
    closing_bits = [
        f"Act E:{float(entry.get('aslaid_e') or 0):.3f}, N:{float(entry.get('aslaid_n') or 0):.3f}, Z:{float(entry.get('aslaid_z') or 0):.2f}m",
        f"Brg:{float(entry.get('heading_deg') or 0):.2f} deg", f"dCL:{float(entry.get('cl_offset_m') or 0):.2f}m",
        f"Gaps:{entry.get('gap_labels') or ('1st Unit (N/A)' if entry.get('is_first_in_array') else 'N/A')}",
        f"USBL:{usbl_s}", f"Verified by {full_surv}",
    ]
    if clean_note: closing_bits.append(f"Notes: {clean_note}")
    full_rem = f"{opening_str} | Closed: {' ; '.join(closing_bits)}"

    bundled_hdr = f"MMA Prestige Subsea Mattress Installation Witnessing ({exec_dt.strftime('%Y-%m-%d')})"
    for old_b in SurveyTask.query.filter(SurveyTask.execution_date == exec_dt, SurveyTask.remarks.ilike(f"%{bundled_hdr}%")).all():
        db.session.delete(old_b)

    existing_t = None
    for t in SurveyTask.query.filter(SurveyTask.sub_location == "338_Subsea_Crossings").all():
        rem_up = str(t.remarks or "").upper()
        if "MMA PRESTIGE MATTRESS FIX CONFIRMED" in rem_up and (f": {box_up} (" in rem_up or f"UNIT #{unit_no}:" in rem_up):
            existing_t = t; break
        elif skip_if_manual_exists and t.execution_date == exec_dt and box_up in rem_up and "MATTRESS INSTALLATION" in rem_up and "WROV ASSIST" not in rem_up and "WITNESSING (" not in rem_up:
            return False

    if existing_t:
        existing_t.surveyor_name = kpi_assigned_user
        existing_t.assigned_to = kpi_assigned_user
        existing_t.execution_date = exec_dt
        existing_t.start_time = fix_dt
        existing_t.end_time = fix_dt
        existing_t.remarks = full_rem
        existing_t.status = "Closed"
    else:
        db.session.add(SurveyTask(
            surveyor_name=kpi_assigned_user, assigned_to=kpi_assigned_user,
            requestor="Offshore - Walaa Ezzat Gomaa", command_verb="VERIFY",
            task_category="Bathymetric Survey", action_required="Check Survey", instrument="USBL",
            area="300_Marine", location="330_Offshore", sub_location="338_Subsea_Crossings",
            work_scope="338-00_OS_Subsea_Crossings", remarks=full_rem, status="Closed",
            is_urgent=False, priority=99, start_time=fix_dt, execution_date=exec_dt, end_time=fix_dt
        ))
    return True

@mti_bp.route('/sync_to_dpr', methods=['POST'])
@login_required
def sync_to_dpr():
    from app import db
    state = load_mti_state()
    ledger, in_logs = list(state.get("ledger") or []), list(state.get("input_logs") or [])
    sync_mode = str(request.form.get("sync_mode") or "date").strip().lower()
    sync_date_str = str(request.form.get("sync_date") or datetime.utcnow().strftime("%Y-%m-%d")).strip()

    target_fixes = [
        r for r in ledger
        if str(r.get("status") or "Completed").strip().lower() == "completed"
        and (sync_mode == "all_fixes" or _parse_mti_fix_dt(r.get("install_date"))[0].strftime("%Y-%m-%d") == sync_date_str)
    ]
    target_fixes.sort(key=lambda r: (_parse_mti_fix_dt(r.get("install_date"))[1], int(float(r.get("unit_no") or 0))))

    if not target_fixes:
        flash(f"No confirmed (Completed) Mattress Fixes found on {'the MTI Ledger' if sync_mode == 'all_fixes' else sync_date_str} to sync.", "error")
        return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

    synced_cnt = 0
    for r in target_fixes:
        r_enr = dict(r)
        if "_find_fix_surveyor_from_logs" in globals():
            lg_s = _find_fix_surveyor_from_logs(r_enr.get("design_box_id"), in_logs, r_enr.get("physical_tag"))
            if lg_s and (not r_enr.get("surveyor_name") or str(r_enr.get("surveyor_name")).strip().lower() in ("duty surveyor", "surveyor")):
                r_enr["surveyor_name"] = lg_s
        in_logs = _sync_fix_to_mti_input_logs(in_logs, r_enr)
        if _upsert_confirmed_fix_to_surveytask(r_enr, skip_if_manual_exists=(sync_mode == "all_fixes"), input_logs=in_logs):
            synced_cnt += 1

    state["input_logs"] = in_logs
    save_mti_state(state)
    db.session.commit()
    flash(f"Synced {synced_cnt} SurveyTask log(s) assigned individually to each fix surveyor!", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))
# --- MTI_ONE_LOG_PER_CONFIRMED_FIX_END ---"""

bp, n_sync = re.subn(
    r"(?:# --- MTI_ONE_LOG_PER_CONFIRMED_FIX_START ---.*?# --- MTI_ONE_LOG_PER_CONFIRMED_FIX_END ---\n?|@mti_bp\.route\('/sync_to_dpr',\s*methods=\['POST'\]\)\s*\n@login_required\s*\ndef sync_to_dpr\(\):.*?(?=\n@mti_bp\.route\('/export_excel'))",
    lambda _m: per_fix_kpi_block + "\n",
    bp, count=1, flags=re.S
)
if not n_sync:
    raise SystemExit("Could not locate sync_to_dpr() block in mti_blueprint.py!")

bp = bp.replace(
    "_upsert_confirmed_fix_to_surveytask(entry, skip_if_manual_exists=False)",
    "_upsert_confirmed_fix_to_surveytask(entry, skip_if_manual_exists=False, input_logs=state.get('input_logs', []))"
)

ast.parse(bp)
open(bp_path, "w", encoding="utf-8").write(bp)
print("  -> Updated mti_blueprint.py (SurveyTask.assigned_to set to the individual Mattress Fix surveyor, AST OK)")

# Ensure mobile Mattress Fix form also exposes Surveyor Name field
for mob_path in ("templates/mti_mobile.html", "mti_mobile.html"):
    if os.path.exists(mob_path):
        m_html = open(mob_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
        if 'name="surveyor_name"' not in m_html:
            old_dt = '<div class="col-md-3 col-4">\n        <label class="form-label small fw-bold mb-1">Date/Time</label>\n        <input type="text" name="install_date" id="inpFixDateTime" value="{{ today_str|default(\'\') }} {{ now_dt_str.split(\'T\')[-1] if now_dt_str is defined else \'\' }}" class="form-control form-control-sm" required>\n      </div>'
            new_dt = '<div class="col-md-3 col-6">\n        <label class="form-label small fw-bold mb-1">Date/Time</label>\n        <input type="text" name="install_date" id="inpFixDateTime" value="{{ today_str|default(\'\') }} {{ now_dt_str.split(\'T\')[-1] if now_dt_str is defined else \'\' }}" class="form-control form-control-sm" required>\n      </div>\n      <div class="col-md-3 col-6">\n        <label class="form-label small fw-bold text-info mb-1">Surveyor Name</label>\n        <input type="text" name="surveyor_name" id="inpMobFixSurveyor" value="{{ current_user.name }}" class="form-control form-control-sm fw-bold" required>\n      </div>'
            if old_dt in m_html:
                m_html = m_html.replace('<div class="col-md-5">', '<div class="col-md-4 col-12">', 1).replace('<div class="col-md-2 col-4">\n        <label class="form-label small fw-bold mb-1">Unit #</label>', '<div class="col-md-1 col-4">\n        <label class="form-label small fw-bold mb-1">Unit #</label>', 1).replace('<div class="col-md-2 col-4">\n        <div class="form-check', '<div class="col-md-1 col-8">\n        <div class="form-check', 1).replace(old_dt, new_dt, 1)
                open(mob_path, "w", encoding="utf-8").write(m_html)
                print(f"  -> Updated {mob_path} (Added Surveyor Name field to Mobile Mattress Fix form)")

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti-kpi): set SurveyTask assigned_to to the individual surveyor who input each Mattress Fix"], check=False)
print("\nKPI/DPR ASSIGNED-TO SURVEYOR UPDATE COMPLETE & SYNCED!")