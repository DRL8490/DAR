import os, re, ast, subprocess

bp_path = "mti_blueprint.py"
if not os.path.exists(bp_path):
    raise SystemExit("mti_blueprint.py not found! Run inside your DAR project folder.")

bp = open(bp_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")

# === 1. REPLACE sync_to_dpr() WITH 1-LOG-PER-CONFIRMED-MATTRESS-FIX ENGINE ===
per_fix_dpr_block = """# --- MTI_ONE_LOG_PER_CONFIRMED_FIX_START ---
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

def _sync_fix_to_mti_input_logs(input_logs, entry):
    logs = list(input_logs or [])
    box_id = str(entry.get("design_box_id") or "").strip()
    box_up = box_id.upper()
    tag_id = str(entry.get("physical_tag") or "").strip()
    usbl_s = str(entry.get("usbl_sensor") or "Survey Pole").strip()
    status_ok = (str(entry.get("status") or "Completed").strip().lower() == "completed")

    match_idx = None
    for idx, lg in enumerate(logs):
        if str(lg.get("event_type") or "").strip().lower() != "mattress fix":
            continue
        ref_up = str(lg.get("ref_id") or "").upper()
        if box_up and re.search(rf"(?<![A-Za-z0-9_-]){re.escape(box_up)}(?![0-9])", ref_up):
            match_idx = idx
            break

    if not status_ok:
        if match_idx is not None:
            logs.pop(match_idx)
        return logs

    raw_surv = str(entry.get("surveyor_name") or entry.get("surveyor") or getattr(current_user, "name", "Duty Surveyor")).strip()
    full_surv = resolve_full_surveyor_name(raw_surv) if "resolve_full_surveyor_name" in globals() else raw_surv
    as_e = float(entry.get("aslaid_e") or 0.0)
    as_n = float(entry.get("aslaid_n") or 0.0)
    as_z = float(entry.get("aslaid_z") or 0.0)
    cl_off = float(entry.get("cl_offset_m") or 0.0)
    hdg = float(entry.get("heading_deg") or 0.0)
    gap_lbl = str(entry.get("gap_labels") or "N/A")

    new_lg = {
        "id": int(logs[match_idx].get("id", 0)) if match_idx is not None else (max([int(x.get("id", 0)) for x in logs] + [0]) + 1),
        "event_type": "Mattress fix",
        "timestamp": str(entry.get("install_date") or datetime.utcnow().strftime("%Y-%m-%d %H:%M")).strip(),
        "surveyor": full_surv,
        "ref_id": f"{box_id} ({tag_id}) [{usbl_s}]",
        "val1": f"Act E:{as_e:.3f}, N:{as_n:.3f}, Z:{as_z:.2f} (dCL:{cl_off:.2f}m)",
        "val2": f"Brg:{hdg:.1f} deg | {gap_lbl}",
        "usbl_sensor": usbl_s,
        "env_wind": str(entry.get("env_wind") or ""),
        "env_current": str(entry.get("env_current") or ""),
        "remarks": str(entry.get("remarks") or ""),
    }
    if match_idx is not None:
        logs[match_idx] = new_lg
    else:
        logs.append(new_lg)
    return logs

def _remove_fix_from_dpr_and_logs(box_id, unit_no=None, state=None):
    box_up = str(box_id or "").strip().upper()
    if isinstance(state, dict) and box_up:
        state["input_logs"] = [
            lg for lg in (state.get("input_logs") or [])
            if not (
                str(lg.get("event_type") or "").strip().lower() == "mattress fix"
                and re.search(rf"(?<![A-Za-z0-9_-]){re.escape(box_up)}(?![0-9])", str(lg.get("ref_id") or "").upper())
            )
        ]
    try:
        from app import SurveyTask, db
        q_rows = SurveyTask.query.filter(SurveyTask.sub_location == "338_Subsea_Crossings").all()
        removed = False
        for t in q_rows:
            rem_t = str(t.remarks or "")
            if "MMA Prestige Mattress Fix Confirmed" in rem_t:
                if (box_up and f": {box_up} (" in rem_t.upper()) or (unit_no and f"Unit #{unit_no}:" in rem_t):
                    db.session.delete(t)
                    removed = True
        if removed:
            db.session.commit()
    except Exception:
        pass

def _upsert_confirmed_fix_to_surveytask(entry, skip_if_manual_exists=False):
    if str(entry.get("status") or "Completed").strip().lower() != "completed":
        _remove_fix_from_dpr_and_logs(entry.get("design_box_id"), entry.get("unit_no"))
        return False

    from app import SurveyTask, db
    unit_no = int(float(entry.get("unit_no") or 1))
    box_id = str(entry.get("design_box_id") or f"CR-A1_M{unit_no}").strip()
    box_up = box_id.upper()
    tag_id = str(entry.get("physical_tag") or "").strip() or "N/A"
    usbl_s = str(entry.get("usbl_sensor") or "Survey Pole").strip()
    exec_dt, fix_dt = _parse_mti_fix_dt(entry.get("install_date"))

    raw_surv = str(entry.get("surveyor_name") or entry.get("surveyor") or getattr(current_user, "name", "Duty Surveyor")).strip()
    full_surv = resolve_full_surveyor_name(raw_surv) if "resolve_full_surveyor_name" in globals() else raw_surv
    if not full_surv or full_surv.lower() in ("duty surveyor", "surveyor"):
        full_surv = getattr(current_user, "name", "Daryll Enano")

    as_e = float(entry.get("aslaid_e") or 0.0)
    as_n = float(entry.get("aslaid_n") or 0.0)
    as_z = float(entry.get("aslaid_z") or 0.0)
    hdg = float(entry.get("heading_deg") or 0.0)
    cl_off = float(entry.get("cl_offset_m") or 0.0)
    gap_lbl = str(entry.get("gap_labels") or ("1st Unit (N/A)" if entry.get("is_first_in_array") else "N/A"))

    raw_rem = str(entry.get("remarks") or "").strip()
    clean_note = _strip_auto_rem_tags(raw_rem) if "_strip_auto_rem_tags" in globals() else raw_rem

    opening_str = f"MMA Prestige Mattress Fix Confirmed - Unit #{unit_no}: {box_id} ({tag_id})"
    closing_bits = [
        f"Act E:{as_e:.3f}, N:{as_n:.3f}, Z:{as_z:.2f}m",
        f"Brg:{hdg:.2f} deg",
        f"dCL:{cl_off:.2f}m",
        f"Gaps:{gap_lbl}",
        f"USBL:{usbl_s}",
        f"Verified by {full_surv}",
    ]
    if clean_note:
        closing_bits.append(f"Notes: {clean_note}")
    full_rem = f"{opening_str} | Closed: {' ; '.join(closing_bits)}"

    bundled_hdr = f"MMA Prestige Subsea Mattress Installation Witnessing ({exec_dt.strftime('%Y-%m-%d')})"
    for old_b in SurveyTask.query.filter(SurveyTask.execution_date == exec_dt, SurveyTask.remarks.ilike(f"%{bundled_hdr}%")).all():
        db.session.delete(old_b)

    all_sub = SurveyTask.query.filter(SurveyTask.sub_location == "338_Subsea_Crossings").all()
    existing_t = None
    for t in all_sub:
        rem_t = str(t.remarks or "")
        rem_up = rem_t.upper()
        if "MMA PRESTIGE MATTRESS FIX CONFIRMED" in rem_up:
            if f": {box_up} (" in rem_up or f"UNIT #{unit_no}:" in rem_up:
                existing_t = t
                break
        elif skip_if_manual_exists and t.execution_date == exec_dt:
            if box_up in rem_up and "MATTRESS INSTALLATION" in rem_up and "WROV ASSIST" not in rem_up and "WITNESSING (" not in rem_up:
                return False

    team_roster = "Daryll Enano, Mohamad Abror Hediarto, Roderick Gonzales Clavel"
    if existing_t:
        existing_t.surveyor_name = full_surv
        existing_t.assigned_to = team_roster
        existing_t.execution_date = exec_dt
        existing_t.start_time = fix_dt
        existing_t.end_time = fix_dt
        existing_t.remarks = full_rem
        existing_t.status = "Closed"
    else:
        db.session.add(SurveyTask(
            surveyor_name=full_surv,
            assigned_to=team_roster,
            requestor="Offshore - Walaa Ezzat Gomaa",
            command_verb="VERIFY",
            task_category="Bathymetric Survey",
            action_required="Check Survey",
            instrument="USBL",
            area="300_Marine",
            location="330_Offshore",
            sub_location="338_Subsea_Crossings",
            work_scope="338-00_OS_Subsea_Crossings",
            remarks=full_rem,
            status="Closed",
            is_urgent=False,
            priority=99,
            start_time=fix_dt,
            execution_date=exec_dt,
            end_time=fix_dt
        ))
    return True

@mti_bp.route('/sync_to_dpr', methods=['POST'])
@login_required
def sync_to_dpr():
    from app import db
    state = load_mti_state()
    ledger = list(state.get("ledger") or [])
    in_logs = list(state.get("input_logs") or [])
    sync_mode = str(request.form.get("sync_mode") or "date").strip().lower()
    sync_date_str = str(request.form.get("sync_date") or datetime.utcnow().strftime("%Y-%m-%d")).strip()

    def _row_ymd(r):
        d_obj, _ = _parse_mti_fix_dt(r.get("install_date"))
        return d_obj.strftime("%Y-%m-%d")

    if sync_mode == "all_fixes":
        target_fixes = [
            r for r in ledger
            if str(r.get("status") or "Completed").strip().lower() == "completed"
        ]
    else:
        target_fixes = [
            r for r in ledger
            if _row_ymd(r) == sync_date_str
            and str(r.get("status") or "Completed").strip().lower() == "completed"
        ]

    target_fixes.sort(key=lambda r: (_parse_mti_fix_dt(r.get("install_date"))[1], int(float(r.get("unit_no") or 0))))

    if not target_fixes:
        scope_lbl = "the MTI Ledger" if sync_mode == "all_fixes" else sync_date_str
        flash(f"No confirmed (Completed) Mattress Fixes found on {scope_lbl} to sync.", "error")
        return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

    synced_cnt = 0
    for r in target_fixes:
        r_enr = dict(r)
        if not r_enr.get("surveyor_name") and "_find_fix_surveyor_from_logs" in globals():
            r_enr["surveyor_name"] = _find_fix_surveyor_from_logs(r_enr.get("design_box_id"), in_logs, r_enr.get("physical_tag"))
        in_logs = _sync_fix_to_mti_input_logs(in_logs, r_enr)
        if _upsert_confirmed_fix_to_surveytask(r_enr, skip_if_manual_exists=(sync_mode == "all_fixes")):
            synced_cnt += 1

    state["input_logs"] = in_logs
    save_mti_state(state)
    db.session.commit()

    if sync_mode == "all_fixes":
        flash(f"Synced {synced_cnt} individual SurveyTask log(s) across all confirmed Mattress Fixes!", "success")
    else:
        flash(f"Synced {synced_cnt} individual SurveyTask log(s) for confirmed Mattress Fixes on {sync_date_str}!", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))
# --- MTI_ONE_LOG_PER_CONFIRMED_FIX_END ---"""

bp, n_sync = re.subn(
    r"(?:# --- MTI_ONE_LOG_PER_CONFIRMED_FIX_START ---.*?# --- MTI_ONE_LOG_PER_CONFIRMED_FIX_END ---\n?|@mti_bp\.route\('/sync_to_dpr',\s*methods=\['POST'\]\)\s*\n@login_required\s*\ndef sync_to_dpr\(\):.*?(?=\n@mti_bp\.route\('/export_excel'))",
    lambda _m: per_fix_dpr_block + "\n",
    bp, count=1, flags=re.S
)
if not n_sync:
    raise SystemExit("Could not locate sync_to_dpr() in mti_blueprint.py!")

# === 2. HOOK AUTOMATIC 1-LOG-PER-CONFIRMED-FIX INTO add_fix() AND delete_fix() ===
auto_add_hook = """    state["input_logs"] = _sync_fix_to_mti_input_logs(state.get("input_logs", []), entry)
    try:
        from app import db as _db_af
        if _upsert_confirmed_fix_to_surveytask(entry, skip_if_manual_exists=False):
            _db_af.session.commit()
    except Exception:
        pass"""

if "_sync_fix_to_mti_input_logs(state.get(" not in bp:
    bp, n_af = re.subn(
        r"    (?:input_logs = state\.get\(\"input_logs\", \[\]\)\s*\n\s*if not existing:.*?state\[\"input_logs\"\] = input_logs|if not existing:\s*\n\s*input_logs = state\.get\(\"input_logs\", \[\]\).*?state\[\"input_logs\"\] = input_logs)",
        lambda _m: auto_add_hook,
        bp, count=1, flags=re.S
    )

new_del_fix = """@mti_bp.route('/delete_fix/<int:fix_id>', methods=['POST'])
@login_required
def delete_fix(fix_id):
    state = load_mti_state()
    ledger = state.get("ledger", [])
    target = next((r for r in ledger if int(r.get("id", 0)) == fix_id), None)
    state["ledger"] = [r for r in ledger if int(r.get("id", 0)) != fix_id]
    if target:
        _remove_fix_from_dpr_and_logs(target.get("design_box_id"), target.get("unit_no"), state=state)
    save_mti_state(state)
    flash("Removed entry from MTI Ledger & DPR Register.", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))"""

bp = re.sub(
    r"@mti_bp\.route\('/delete_fix/<int:fix_id>',\s*methods=\['POST'\]\)\s*\n@login_required\s*\ndef delete_fix\(fix_id\):.*?(?=\n@mti_bp\.route\('/add_input_log')",
    lambda _m: new_del_fix + "\n",
    bp, count=1, flags=re.S
)

ast.parse(bp)
open(bp_path, "w", encoding="utf-8").write(bp)
print("  -> Updated mti_blueprint.py (1 SurveyTask + 1 Input Log per confirmed Mattress Fix, AST OK)")

# === 3. UPDATE 1-CLICK DPR BOARD SYNC CARD IN templates/mti_dashboard.html ===
for dash_path in ("templates/mti_dashboard.html", "mti_dashboard.html"):
    if os.path.exists(dash_path):
        d_html = open(dash_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
        new_sync_card = """<div class="text-muted small fw-bold text-uppercase">1-Click DPR Board Sync</div>
                <form action="/mti/sync_to_dpr" method="POST" class="mt-2 d-flex flex-wrap gap-1">
                    <input type="date" name="sync_date" value="{{ today_str }}" class="form-control form-control-sm" style="flex:1 1 118px;min-width:118px;" required>
                    <button type="submit" name="sync_mode" value="date" class="btn btn-sm btn-warning fw-bold text-nowrap" title="Create/update 1 SurveyTask log per confirmed Mattress Fix on selected date">Sync Date</button>
                    <button type="submit" name="sync_mode" value="all_fixes" class="btn btn-sm btn-outline-dark fw-bold text-nowrap" title="Convert &amp; sync 1 SurveyTask log for every confirmed Mattress Fix in Ledger">All Fixes</button>
                </form>
                <small class="text-muted d-block mt-1">Logs 1 SurveyTask entry per confirmed Mattress Fix</small>"""
        d_html_new, n_c = re.subn(
            r'<div class="text-muted small fw-bold text-uppercase">1-Click DPR Board Sync</div>.*?</small>',
            lambda _m: new_sync_card,
            d_html, count=1, flags=re.S
        )
        if n_c and d_html_new != d_html:
            open(dash_path, "w", encoding="utf-8").write(d_html_new)
            print(f"  -> Updated {dash_path} (Added Sync Date + All Fixes buttons)")

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti-dpr): log one individual SurveyTask entry per confirmed Mattress Fix"], check=False)
print("\nONE LOG PER CONFIRMED MATTRESS FIX COMPLETE & SYNCED!")