import os, re, ast, subprocess

NEW_ADD_FIX = """@mti_bp.route('/add_fix', methods=['POST'])
@login_required
def add_fix():
    state = load_mti_state()
    ledger = state.get("ledger", [])
    unit_no = request.form.get("unit_no", type=int) or (len(ledger) + 1)
    is_first = (request.form.get("is_first_in_array") == "true") or (unit_no == 1)
    des_e = request.form.get("design_e", type=float) or 0.0
    des_n = request.form.get("design_n", type=float) or 0.0
    qaqc_e = request.form.get("qaqc_e", type=float) or 0.0
    qaqc_n = request.form.get("qaqc_n", type=float) or 0.0
    qaqc_brg = request.form.get("qaqc_brg", type=float) or 0.0
    usbl_sensor = (request.form.get("usbl_sensor") or "Pole USBL").strip()

    pts = []
    for i in (1, 2, 3, 4):
        ce = request.form.get(f"c{i}_e", type=float)
        cn = request.form.get(f"c{i}_n", type=float)
        cz = request.form.get(f"c{i}_z", type=float)
        if ce and cn:
            pts.append((ce, cn, cz or 0.0))

    if len(pts) == 4:
        as_e = round(sum(p[0] for p in pts) / 4.0, 3)
        as_n = round(sum(p[1] for p in pts) / 4.0, 3)
        as_z = round(sum(p[2] for p in pts) / 4.0, 3)
        fe, fn = (pts[0][0] + pts[1][0]) / 2.0, (pts[0][1] + pts[1][1]) / 2.0
        be, bn = (pts[2][0] + pts[3][0]) / 2.0, (pts[2][1] + pts[3][1]) / 2.0
        hdg = round((math.degrees(math.atan2(fe - be, fn - bn)) + 360.0) % 360.0, 3)
        corners = {f"c{i+1}_e": round(pts[i][0], 3) for i in range(4)}
        corners.update({f"c{i+1}_n": round(pts[i][1], 3) for i in range(4)})
        corners.update({f"c{i+1}_z": round(pts[i][2], 3) for i in range(4)})
    else:
        as_e = request.form.get("aslaid_e", type=float) or qaqc_e
        as_n = request.form.get("aslaid_n", type=float) or qaqc_n
        as_z = request.form.get("aslaid_z", type=float) or 0.0
        hdg = round(request.form.get("heading_deg", type=float) or qaqc_brg, 3)
        corners = compute_4_corners(as_e, as_n, hdg, 6.0, 3.0)

    cl_off = round(math.hypot(as_e - des_e, as_n - des_n), 2) if (as_e and des_e) else (request.form.get("cl_offset_m", type=float) or 0.0)

    gnw, gne, gsw, gse = [request.form.get(k, "").strip() for k in ("gap_nw", "gap_ne", "gap_sw", "gap_se")]
    g_parts, g_vals = [], []
    if not is_first:
        for lbl, val in [("NW", gnw), ("NE", gne), ("SW", gsw), ("SE", gse)]:
            if val != "":
                try:
                    fv = round(float(val), 2)
                    g_parts.append(f"{lbl}:{fv:.2f}m")
                    g_vals.append(fv)
                except Exception:
                    pass
    if is_first:
        gap_labels, gap1, gap2, max_gap = "1st Unit (N/A)", 0.0, 0.0, 0.0
    elif g_vals:
        gap_labels = " | ".join(g_parts)
        gap1, gap2, max_gap = g_vals[0], (g_vals[1] if len(g_vals) > 1 else g_vals[0]), max(g_vals)
    else:
        gap1 = round(request.form.get("gap1_m", type=float) or 0.0, 2)
        gap2 = round(request.form.get("gap2_m", type=float) or 0.0, 2)
        max_gap = round(max(gap1, gap2), 2)
        gap_labels = f"G1:{gap1:.2f}m | G2:{gap2:.2f}m"

    env_w = (request.form.get("env_wind") or "").strip()
    env_c = (request.form.get("env_current") or "").strip()
    env_s = (request.form.get("env_swell") or "").strip()
    env_tag = " | ".join([f"{k}:{v}" for k, v in [("Wind", env_w), ("Curr", env_c), ("Swell", env_s)] if v])

    dt_str = (request.form.get("install_date") or datetime.utcnow().strftime('%Y-%m-%d %H:%M')).strip()
    xing_id = (request.form.get("crossing_id") or "CR-A1_L1").strip()
    box_id = (request.form.get("design_box_id") or f"CR-A1_M{unit_no}").strip()
    tag_id = (request.form.get("physical_tag") or "").strip()
    rem_str = (request.form.get("remarks") or "").strip()
    if usbl_sensor and f"[{usbl_sensor}]" not in rem_str:
        rem_str = f"[{usbl_sensor}] {rem_str}".strip()
    if env_tag and env_tag not in rem_str:
        rem_str = f"{rem_str} [{env_tag}]".strip()

    existing = next((r for r in ledger if int(r.get("unit_no", 0)) == unit_no), None)
    entry = {
        "id": existing["id"] if existing else (max([int(r.get("id", 0)) for r in ledger] + [0]) + 1),
        "unit_no": unit_no, "is_first_in_array": is_first, "unit_type": "Concrete Mattress",
        "crossing_id": xing_id, "design_box_id": box_id, "physical_tag": tag_id,
        "install_date": dt_str, "usbl_sensor": usbl_sensor,
        "design_e": round(des_e, 3), "design_n": round(des_n, 3),
        "qaqc_e": round(qaqc_e or as_e, 3), "qaqc_n": round(qaqc_n or as_n, 3), "qaqc_brg": round(qaqc_brg or hdg, 3),
        "aslaid_e": round(as_e, 3), "aslaid_n": round(as_n, 3), "aslaid_z": round(as_z, 3),
        "cl_offset_m": round(cl_off, 2), "heading_deg": hdg,
        "gap_nw": gnw, "gap_ne": gne, "gap_sw": gsw, "gap_se": gse,
        "gap_labels": gap_labels, "gap1_m": gap1, "gap2_m": gap2, "gap_m": max_gap,
        "env_wind": env_w, "env_current": env_c, "env_swell": env_s,
        "status": request.form.get("status", "Completed"), "remarks": rem_str,
        **corners
    }
    if existing:
        ledger.remove(existing)
    ledger.append(entry)
    state["ledger"] = ledger

    input_logs = state.get("input_logs", [])
    if not existing:
        input_logs.append({
            "id": max([int(x.get("id", 0)) for x in input_logs] + [0]) + 1,
            "event_type": "Mattress fix", "timestamp": dt_str,
            "surveyor": getattr(current_user, "name", "Surveyor"),
            "ref_id": f"{box_id} ({tag_id}) [{usbl_sensor}]",
            "val1": f"Act E:{as_e:.2f}, N:{as_n:.2f}, Z:{as_z:.2f} (dCL:{cl_off:.2f}m)",
            "val2": f"Brg:{hdg:.1f} deg | {gap_labels}",
            "remarks": rem_str
        })
        state["input_logs"] = input_logs

    save_mti_state(state)
    flash(f"Saved Unit #{unit_no} ({box_id} / {tag_id}) via {usbl_sensor}!", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

"""

NEW_ADD_INPUT_LOG = """@mti_bp.route('/add_input_log', methods=['POST'])
@login_required
def add_input_log():
    state = load_mti_state()
    input_logs = state.get("input_logs", [])
    log_id = request.form.get("log_id", type=int)
    existing = next((x for x in input_logs if int(x.get("id", 0)) == log_id), None) if log_id else None

    env_w = (request.form.get("env_wind") or "").strip()
    env_c = (request.form.get("env_current") or "").strip()
    env_s = (request.form.get("env_swell") or "").strip()
    env_tag = " | ".join([f"{k}:{v}" for k, v in [("Wind", env_w), ("Curr", env_c), ("Swell", env_s)] if v])
    rem = (request.form.get("remarks") or "").strip()
    if env_tag and env_tag not in rem:
        rem = f"{rem} [{env_tag}]".strip()

    entry = {
        "id": existing["id"] if existing else (max([int(x.get("id", 0)) for x in input_logs] + [0]) + 1),
        "event_type": (request.form.get("event_type") or "Pole down").strip(),
        "timestamp": (request.form.get("timestamp") or datetime.utcnow().strftime('%Y-%m-%d %H:%M')).strip(),
        "surveyor": (request.form.get("surveyor") or getattr(current_user, "name", "Surveyor")).strip(),
        "ref_id": (request.form.get("ref_id") or "").strip(),
        "val1": (request.form.get("val1") or "").strip(),
        "val2": (request.form.get("val2") or "").strip(),
        "env_wind": env_w, "env_current": env_c, "env_swell": env_s,
        "remarks": rem
    }
    if existing:
        input_logs.remove(existing)
    input_logs.append(entry)
    state["input_logs"] = input_logs
    save_mti_state(state)
    flash(f"Logged '{entry['event_type']}' at {entry['timestamp']}!", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

"""

UI_V2_SCRIPT = """<script id="mtiV2Upgrade">
(function(){
  const ENV_EVENTS = new Set(['Pole down', 'Pole up', 'ROV & Vessel Ops']);
  const V2_CONFIGS = {
    "Pole down": {lblRef:"Location / Crossing ID",defRef:"CR-A1_L1",lbl1:"Pole Lock & Pin Status *",ph1:"Down & Locked in Working Position",lbl2:"USBL & ADCP Telemetry Check",ph2:"Ranger 2 HPT & RDI ADCP Online",phRem:"Over-the-side pole deployed prior to subsea operations...",r:"Location / Crossing ID",dr:"CR-A1_L1",l1:"Pole Lock & Pin Status *",p1:"Down & Locked in Working Position",l2:"USBL & ADCP Telemetry Check",p2:"Ranger 2 HPT & RDI ADCP Online",pr:"Over-the-side pole deployed prior to subsea operations..."},
    "Pole up": {lblRef:"Location / Crossing ID",defRef:"CR-A1_L1",lbl1:"Pole Stowed Status *",ph1:"Recovered & Secured on Deck Cradle",lbl2:"Reason for Recovery",ph2:"Transit / Weather / Maintenance",phRem:"USBL/ADCP pole raised and locked above waterline...",r:"Location / Crossing ID",dr:"CR-A1_L1",l1:"Pole Stowed Status *",p1:"Recovered & Secured on Deck Cradle",l2:"Reason for Recovery",p2:"Transit / Weather / Maintenance",pr:"USBL/ADCP pole raised and locked above waterline..."},
    "Mattress on water": {lblRef:"Xing / Box / Tag ID *",defRef:"CR-A1_M4",lbl1:"Deployment Stage & Tag # *",ph1:"Overboard / Seabed Align / Tagline / Recover to Deck (#A023)",lbl2:"Water Depth / Beacon Status",ph2:"Transponder Ch 1 & 2 Tracking OK",phRem:"Mattress lowered through splash zone; WROV monitoring alignment...",r:"Xing / Box / Tag ID *",dr:"CR-A1_M4",l1:"Deployment Stage & Tag # *",p1:"Overboard / Seabed Align / Tagline / Recover to Deck (#A023)",l2:"Water Depth / Beacon Status",p2:"Transponder Ch 1 & 2 Tracking OK",pr:"Mattress lowered through splash zone; WROV monitoring alignment..."},
    "Frame above water": {lblRef:"Xing / Box / Tag ID *",defRef:"CR-A1_M4",lbl1:"Acoustic Release Status *",ph1:"4-Hook Release Confirmed by WROV",lbl2:"Frame Deck Status",ph2:"Frame Above Water & Landed on Deck",phRem:"Deployment frame recovered cleanly; preparing next mattress...",r:"Xing / Box / Tag ID *",dr:"CR-A1_M4",l1:"Acoustic Release Status *",p1:"4-Hook Release Confirmed by WROV",l2:"Frame Deck Status",p2:"Frame Above Water & Landed on Deck",pr:"Deployment frame recovered cleanly; preparing next mattress..."},
    "ROV & Vessel Ops": {lblRef:"Vessel / ROV / Crossing ID *",defRef:"MMA Prestige / WROV",lbl1:"Operation Type (ROV Launch / On Deck / Maint / DP / Echo 4) *",ph1:"e.g., ROV Off Deck / Echo 4 Arrival / 100m DP Move",lbl2:"Position / Heading / Dive Status",ph2:"e.g., Lat/Long, Heading 38.9 deg, or ROV Dive #",phRem:"ROV deployment/maintenance or vessel DP/Echo 4 movement...",r:"Vessel / ROV / Crossing ID *",dr:"MMA Prestige / WROV",l1:"Operation Type (ROV Launch / On Deck / Maint / DP / Echo 4) *",p1:"e.g., ROV Off Deck / Echo 4 Arrival / 100m DP Move",l2:"Position / Heading / Dive Status",p2:"e.g., Lat/Long, Heading 38.9 deg, or ROV Dive #",pr:"ROV deployment/maintenance or vessel DP/Echo 4 movement..."},
    "Calib, Setup & TBT": {lblRef:"System / Location *",defRef:"USBL / Helmsman PC / Mess Room",lbl1:"Activity (USBL/Tripod Calib / Helmsman PC / TBT / Standby) *",ph1:"e.g., USBL Tripod Check / Crane Helmsman Wi-Fi / Daily TBT",lbl2:"Result / Standby Status",ph2:"e.g., Report Submitted / Weather Standby Active",phRem:"Calibration, crane-cabin Helmsman display setup, TBT, or standby...",r:"System / Location *",dr:"USBL / Helmsman PC / Mess Room",l1:"Activity (USBL/Tripod Calib / Helmsman PC / TBT / Standby) *",p1:"e.g., USBL Tripod Check / Crane Helmsman Wi-Fi / Daily TBT",l2:"Result / Standby Status",p2:"e.g., Report Submitted / Weather Standby Active",pr:"Calibration, crane-cabin Helmsman display setup, TBT, or standby..."},
    "Survey Issue Reporting": {lblRef:"System & Active USBL Handoff *",defRef:"Pole USBL -> Switched to Vessel USBL",lbl1:"Issue / Beacon Dropout / Entanglement *",ph1:"e.g., Pole USBL beacon dropout / ROV umbilical / Fallen tripod",lbl2:"USBL Switch / Downtime Impact",ph2:"e.g., Switched to Vessel USBL for positioning (25m downtime)",phRem:"Root cause, USBL sensor switch, and corrective action taken...",r:"System & Active USBL Handoff *",dr:"Pole USBL -> Switched to Vessel USBL",l1:"Issue / Beacon Dropout / Entanglement *",p1:"e.g., Pole USBL beacon dropout / ROV umbilical / Fallen tripod",l2:"USBL Switch / Downtime Impact",p2:"e.g., Switched to Vessel USBL for positioning (25m downtime)",pr:"Root cause, USBL sensor switch, and corrective action taken..."}
  };

  document.addEventListener('DOMContentLoaded', function(){
    if (typeof EVENT_CONFIGS !== 'undefined') Object.assign(EVENT_CONFIGS, V2_CONFIGS);

    document.querySelectorAll('button').forEach(function(btn){
      const txt = btn.innerText.trim();
      if (txt.indexOf('ADCP input') !== -1) {
        btn.innerHTML = btn.classList.contains('tap-btn') ? '<i class="fas fa-ship text-info fs-5"></i>ROV & Vessel Ops' : '<i class="fas fa-ship text-info"></i> ROV & Vessel Ops';
        btn.setAttribute('onclick', btn.classList.contains('tap-btn') ? "openMobEvt('ROV & Vessel Ops')" : "openEventInputBox('ROV & Vessel Ops')");
      } else if (txt.indexOf('Wind Input') !== -1) {
        btn.innerHTML = btn.classList.contains('tap-btn') ? '<i class="fas fa-tools text-warning fs-5"></i>Calib, Setup & TBT' : '<i class="fas fa-tools text-warning"></i> Calib, Setup & TBT';
        btn.setAttribute('onclick', btn.classList.contains('tap-btn') ? "openMobEvt('Calib, Setup & TBT')" : "openEventInputBox('Calib, Setup & TBT')");
      }
    });

    ['eventInputForm', 'mobEvtCard'].forEach(function(id){
      const c = document.getElementById(id);
      const form = c ? (c.tagName === 'FORM' ? c : c.querySelector('form')) : null;
      if (form && !form.querySelector('.env-strip-evt')) {
        const div = document.createElement('div');
        div.className = 'row g-2 mb-2 p-2 rounded border border-info env-strip-evt';
        div.style.background = 'rgba(14,165,233,0.08)';
        div.innerHTML = '<div class="col-12 small fw-bold text-info mb-0"><i class="fas fa-wind me-1"></i>Environmental Inputs (Wind, Current & Swell)</div>' +
          '<div class="col-4"><input type="text" name="env_wind" class="form-control form-control-sm" placeholder="Wind (e.g. 18kt NE)"></div>' +
          '<div class="col-4"><input type="text" name="env_current" class="form-control form-control-sm" placeholder="Curr (e.g. 0.4m/s)"></div>' +
          '<div class="col-4"><input type="text" name="env_swell" class="form-control form-control-sm" placeholder="Swell Hs (e.g. 0.8m)"></div>';
        const remRow = form.querySelector('[name="remarks"]').closest('.row, .mb-3');
        if (remRow) remRow.parentNode.insertBefore(div, remRow);
      }
    });

    const toggleEvtEnv = function(evtType){
      document.querySelectorAll('.env-strip-evt').forEach(el => {
        el.style.display = ENV_EVENTS.has(evtType) ? 'flex' : 'none';
      });
    };
    const origDeskEvt = window.openEventInputBox;
    if (origDeskEvt) window.openEventInputBox = function(t){ origDeskEvt(t); toggleEvtEnv(t); };
    const origMobEvt = window.openMobEvt;
    if (origMobEvt) window.openMobEvt = function(t){ origMobEvt(t); toggleEvtEnv(t); };

    document.querySelectorAll('form[action="/mti/add_fix"]').forEach(function(f){
      if (f.querySelector('.rov-corners-box')) return;
      const box = document.createElement('div');
      box.className = 'p-2 my-2 rounded border border-primary rov-corners-box';
      box.style.background = 'rgba(2,132,199,0.06)';
      box.innerHTML = `
        <div class="row g-2 mb-2 align-items-end">
          <div class="col-md-3 col-6"><label class="small fw-bold text-primary">Active USBL Used *</label>
            <select name="usbl_sensor" class="form-select form-select-sm border-primary fw-bold">
              <option value="Pole USBL">Pole USBL (Primary)</option>
              <option value="Vessel USBL">Vessel USBL</option>
              <option value="Vessel Nav + Pole Fix">Vessel Nav + Pole Final Fix</option>
            </select>
          </div>
          <div class="col-md-3 col-6"><label class="small fw-bold">1. QA/QC Center E</label><input type="number" step="0.001" name="qaqc_e" class="form-control form-control-sm qaqc-e" placeholder="Pre-Rel E"></div>
          <div class="col-md-3 col-6"><label class="small fw-bold">1. QA/QC Center N</label><input type="number" step="0.001" name="qaqc_n" class="form-control form-control-sm qaqc-n" placeholder="Pre-Rel N"></div>
          <div class="col-md-3 col-6"><label class="small fw-bold">1. QA/QC Brg (&deg;)</label>
            <div class="input-group input-group-sm">
              <input type="number" step="0.001" name="qaqc_brg" class="form-control form-control-sm qaqc-brg" value="15.854">
              <button type="button" class="btn btn-outline-primary fw-bold" title="Seed 4 ROV Corners from QA/QC" onclick="window.seedRovCorners(this.closest('form'))">Seed 4C</button>
            </div>
          </div>
        </div>
        <div class="small fw-bold text-success mb-1"><i class="fas fa-vector-square me-1"></i>2. ROV 4-Corners Input (E, N, Z) &rarr; Auto-Calculates Actual Mattress Center &amp; Bearing</div>
        <div class="row g-1 mb-2">
          <div class="col-md-3 col-6"><div class="input-group input-group-sm"><span class="input-group-text fw-bold px-1">C1</span><input type="number" step="0.001" name="c1_e" class="form-control px-1 rc" placeholder="E1"><input type="number" step="0.001" name="c1_n" class="form-control px-1 rc" placeholder="N1"><input type="number" step="0.01" name="c1_z" class="form-control px-1 rc" placeholder="Z1"></div></div>
          <div class="col-md-3 col-6"><div class="input-group input-group-sm"><span class="input-group-text fw-bold px-1">C2</span><input type="number" step="0.001" name="c2_e" class="form-control px-1 rc" placeholder="E2"><input type="number" step="0.001" name="c2_n" class="form-control px-1 rc" placeholder="N2"><input type="number" step="0.01" name="c2_z" class="form-control px-1 rc" placeholder="Z2"></div></div>
          <div class="col-md-3 col-6"><div class="input-group input-group-sm"><span class="input-group-text fw-bold px-1">C3</span><input type="number" step="0.001" name="c3_e" class="form-control px-1 rc" placeholder="E3"><input type="number" step="0.001" name="c3_n" class="form-control px-1 rc" placeholder="N3"><input type="number" step="0.01" name="c3_z" class="form-control px-1 rc" placeholder="Z3"></div></div>
          <div class="col-md-3 col-6"><div class="input-group input-group-sm"><span class="input-group-text fw-bold px-1">C4</span><input type="number" step="0.001" name="c4_e" class="form-control px-1 rc" placeholder="E4"><input type="number" step="0.001" name="c4_n" class="form-control px-1 rc" placeholder="N4"><input type="number" step="0.01" name="c4_z" class="form-control px-1 rc" placeholder="Z4"></div></div>
        </div>
        <div class="row g-2">
          <div class="col-4"><input type="text" name="env_wind" class="form-control form-control-sm" placeholder="Wind (e.g. 16kt NE)"></div>
          <div class="col-4"><input type="text" name="env_current" class="form-control form-control-sm" placeholder="Current (e.g. 0.35m/s)"></div>
          <div class="col-4"><input type="text" name="env_swell" class="form-control form-control-sm" placeholder="Swell Hs (e.g. 0.7m)"></div>
        </div>
        <input type="hidden" name="aslaid_z" class="aslaid-z" value="0.00">`;
      const submitBtn = f.querySelector('button[type="submit"]');
      const targetRow = submitBtn ? submitBtn.closest('.row, button') : f.lastElementChild;
      f.insertBefore(box, targetRow);

      [['gNW','mgNW','gap_nw'],['gNE','mgNE','gap_ne'],['gSW','mgSW','gap_sw'],['gSE','mgSE','gap_se']].forEach(pair => {
        const el = f.querySelector('#'+pair[0]) || f.querySelector('#'+pair[1]);
        if (el) el.setAttribute('name', pair[2]);
      });
      f.querySelectorAll('.rc').forEach(inp => inp.addEventListener('input', () => window.calcFromRovCorners(f)));
    });
  });

  window.seedRovCorners = function(f){
    const ce = parseFloat(f.querySelector('.qaqc-e')?.value || f.querySelector('[name="design_e"]')?.value) || 0;
    const cn = parseFloat(f.querySelector('.qaqc-n')?.value || f.querySelector('[name="design_n"]')?.value) || 0;
    const brg = parseFloat(f.querySelector('.qaqc-brg')?.value || f.querySelector('[name="heading_deg"]')?.value) || 0;
    if (!ce || !cn) return;
    const rad = brg * Math.PI / 180.0, sb = Math.sin(rad), cb = Math.cos(rad);
    [[1,-1],[1,1],[-1,1],[-1,-1]].forEach((s, idx) => {
      const i = idx + 1;
      f.querySelector(`[name="c${i}_e"]`).value = (ce + s[0]*3.0*sb + s[1]*1.5*cb).toFixed(3);
      f.querySelector(`[name="c${i}_n"]`).value = (cn + s[0]*3.0*cb - s[1]*1.5*sb).toFixed(3);
      if (!f.querySelector(`[name="c${i}_z"]`).value) f.querySelector(`[name="c${i}_z"]`).value = '-18.20';
    });
    window.calcFromRovCorners(f);
  };

  window.calcFromRovCorners = function(f){
    const pts = [1,2,3,4].map(i => [
      parseFloat(f.querySelector(`[name="c${i}_e"]`)?.value),
      parseFloat(f.querySelector(`[name="c${i}_n"]`)?.value),
      parseFloat(f.querySelector(`[name="c${i}_z"]`)?.value || '0')
    ]);
    if (pts.every(p => !isNaN(p[0]) && !isNaN(p[1]))) {
      const ae = (pts[0][0]+pts[1][0]+pts[2][0]+pts[3][0])/4.0;
      const an = (pts[0][1]+pts[1][1]+pts[2][1]+pts[3][1])/4.0;
      const az = (pts[0][2]+pts[1][2]+pts[2][2]+pts[3][2])/4.0;
      const fe = (pts[0][0]+pts[1][0])/2.0, fn = (pts[0][1]+pts[1][1])/2.0;
      const be = (pts[2][0]+pts[3][0])/2.0, bn = (pts[2][1]+pts[3][1])/2.0;
      const brg = ((Math.atan2(fe - be, fn - bn) * 180.0 / Math.PI) + 360.0) % 360.0;
      const inpE = f.querySelector('[name="aslaid_e"]'), inpN = f.querySelector('[name="aslaid_n"]'), inpH = f.querySelector('[name="heading_deg"]');
      if (inpE) { inpE.value = ae.toFixed(3); inpE.dispatchEvent(new Event('input', {bubbles:true})); }
      if (inpN) { inpN.value = an.toFixed(3); inpN.dispatchEvent(new Event('input', {bubbles:true})); }
      if (inpH) { inpH.value = brg.toFixed(3); inpH.dispatchEvent(new Event('input', {bubbles:true})); }
      const inpZ = f.querySelector('.aslaid-z');
      if (inpZ) inpZ.value = az.toFixed(2);
    }
  };
})();
</script>
</body>"""

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")

mc = re.sub(r"@mti_bp\.route\('/add_fix'.*?(?=@mti_bp\.route\('/delete_fix)", NEW_ADD_FIX, mc, count=1, flags=re.S)
mc = re.sub(r"@mti_bp\.route\('/add_input_log'.*?(?=@mti_bp\.route\('/delete_input_log)", NEW_ADD_INPUT_LOG, mc, count=1, flags=re.S)
ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)
print("1. Upgraded mti_blueprint.py with 2-Dataset Mattress Fix, USBL sensor, & Env inputs.")

for target in ["templates/mti_dashboard.html", "templates/mti_mobile.html", "mti_blueprint.py"]:
    if not os.path.exists(target): continue
    with open(target, "r", encoding="utf-8-sig") as f: txt = f.read()
    txt = txt.replace(
        'G1: {{ "%.2f"|format(r.gap1_m|default(r.gap_m)|float) }}m | G2: {{ "%.2f"|format(r.gap2_m|default(r.gap_m)|float) }}m',
        '{{ r.gap_labels if r.gap_labels else ("G1: " ~ ("%.2f"|format(r.gap1_m|default(r.gap_m)|float)) ~ "m | G2: " ~ ("%.2f"|format(r.gap2_m|default(r.gap_m)|float)) ~ "m") }}'
    )
    if 'id="mtiV2Upgrade"' not in txt and '</body>' in txt:
        txt = txt.replace('</body>', UI_V2_SCRIPT, 1)
    with open(target, "w", encoding="utf-8") as f: f.write(txt)
    print(f"2. Injected finalized 8-button grid, ROV 4-Corner calculator & Env strip into {target}!")

subprocess.run(["py", "sync.py", "feat: upgrade MTI with 8-button grid, 2-dataset ROV 4-corner calculator, USBL selector, and Wind/Current/Swell inputs"], check=False)
