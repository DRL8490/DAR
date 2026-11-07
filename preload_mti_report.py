import os, re, ast, json, subprocess

PRELOAD_DATA_DEFS = """
# --- PRELOADED BASELINE MTI REPORT (30 OCT - 07 NOV 2026) ---
PRELOADED_MTI_LEDGER = [
    {
        "id": 1, "unit_no": 1, "is_first_in_array": True, "unit_type": "Concrete Mattress",
        "crossing_id": "CR-A1_L1", "design_box_id": "CR-A1_M15", "physical_tag": "#A046",
        "install_date": "2026-11-05 03:20", "usbl_sensor": "Survey Pole",
        "design_e": 194541.443, "design_n": 2702613.394, "design_brg": 195.861,
        "qaqc_e": 194541.206, "qaqc_n": 2702613.513, "qaqc_brg": 196.889,
        "aslaid_e": 194541.206, "aslaid_n": 2702613.513, "aslaid_z": -18.20,
        "cl_offset_m": 0.265, "heading_deg": 196.889, "brg_diff_deg": -1.028,
        "c1_e": 194540.642, "c1_n": 2702616.819, "c1_z": -18.20,
        "c2_e": 194543.513, "c2_n": 2702615.948, "c2_z": -18.20,
        "c3_e": 194541.770, "c3_n": 2702610.207, "c3_z": -18.20,
        "c4_e": 194538.899, "c4_n": 2702611.078, "c4_z": -18.20,
        "gap_nw": "", "gap_ne": "", "gap_sw": "", "gap_se": "",
        "gap_labels": "1st Unit (N/A)", "gap1_m": 0.0, "gap2_m": 0.0, "gap_m": 0.0,
        "env_wind": "14kt NE", "env_current": "0.35m/s",
        "status": "Completed",
        "remarks": "[Survey Pole] 1st mattress installed at CR-A1_M15 (#A046); 4 hooks released cleanly; dCL=0.265m, dBrg=-1.028 deg [Wind:14kt NE | Curr:0.35m/s]"
    },
    {
        "id": 2, "unit_no": 2, "is_first_in_array": False, "unit_type": "Concrete Mattress",
        "crossing_id": "CR-A1_L1", "design_box_id": "CR-A1_M16", "physical_tag": "#A007",
        "install_date": "2026-11-05 11:36", "usbl_sensor": "Vessel",
        "design_e": 194544.329, "design_n": 2702612.575, "design_brg": 195.852,
        "qaqc_e": 194544.356, "qaqc_n": 2702612.753, "qaqc_brg": 198.397,
        "aslaid_e": 194544.356, "aslaid_n": 2702612.753, "aslaid_z": -18.35,
        "cl_offset_m": 0.180, "heading_deg": 198.397, "brg_diff_deg": -2.545,
        "c1_e": 194543.879, "c1_n": 2702616.073, "c1_z": -18.35,
        "c2_e": 194546.726, "c2_n": 2702615.126, "c2_z": -18.35,
        "c3_e": 194544.833, "c3_n": 2702609.433, "c3_z": -18.35,
        "c4_e": 194541.986, "c4_n": 2702610.380, "c4_z": -18.35,
        "gap_nw": "0.08", "gap_ne": "", "gap_sw": "0.10", "gap_se": "",
        "gap_labels": "NW:0.08m | SW:0.10m", "gap1_m": 0.08, "gap2_m": 0.10, "gap_m": 0.10,
        "env_wind": "16kt NE", "env_current": "0.40m/s",
        "status": "Completed",
        "remarks": "[Vessel] Installed CR-A1_M16 (#A007); navigated via Vessel USBL during Pole beacon dropout, verified with Pole USBL; dCL=0.180m, dBrg=-2.545 deg [Wind:16kt NE | Curr:0.40m/s]"
    }
]

PRELOADED_MTI_LOGS = [
    {
        "id": 1, "event_type": "Calib, Setup & TBT", "timestamp": "2026-11-04 07:38",
        "surveyor": "Abror / Roderick", "ref_id": "MMA Prestige / Mess Room",
        "val1": "Daily TBT & Crane Helmsman PC Setup", "val2": "USBL Tripod Verification Completed",
        "usbl_sensor": "Survey Pole", "env_wind": "", "env_current": "",
        "remarks": "Conducted TBT for mattress installation, verified USBL on seabed tripod, and established Wi-Fi Helmsman display in crane cabin [USBL:Survey Pole]"
    },
    {
        "id": 2, "event_type": "Pole down", "timestamp": "2026-11-04 16:40",
        "surveyor": "Abror", "ref_id": "CR-A1_L1",
        "val1": "Ranger 2 HPT & RDI ADCP Online", "val2": "",
        "usbl_sensor": "", "env_wind": "14kt NE", "env_current": "0.35m/s",
        "remarks": "Over-the-side survey pole deployed & locked in working position prior to subsea mattress operations [Wind:14kt NE | Curr:0.35m/s]"
    },
    {
        "id": 3, "event_type": "ROV & Vessel Ops", "timestamp": "2026-11-04 20:54",
        "surveyor": "Abror", "ref_id": "MMA Prestige / WROV",
        "val1": "WROV Launched for Seabed Inspection at CR-A1", "val2": "Heading 38.9 deg / DP AutoPos",
        "usbl_sensor": "Survey Pole", "env_wind": "14kt NE", "env_current": "0.35m/s",
        "remarks": "WROV deployed for pre-lay inspection and transponder verification [USBL:Survey Pole | Wind:14kt NE | Curr:0.35m/s]"
    },
    {
        "id": 4, "event_type": "Mattress fix", "timestamp": "2026-11-05 03:20",
        "surveyor": "Roderick", "ref_id": "CR-A1_M15 (#A046) [Survey Pole]",
        "val1": "Act E:194541.21, N:2702613.51, Z:-18.20 (dCL:0.26m)", "val2": "Brg:196.9 deg | 1st Unit (N/A)",
        "usbl_sensor": "Survey Pole", "env_wind": "14kt NE", "env_current": "0.35m/s",
        "remarks": "[Survey Pole] 1st mattress CR-A1_M15 (#A046) deployed and 4 ROV corners logged; frame recovered to deck at 03:45 [Wind:14kt NE | Curr:0.35m/s]"
    },
    {
        "id": 5, "event_type": "Survey Issue Reporting", "timestamp": "2026-11-05 08:25",
        "surveyor": "Abror", "ref_id": "Survey Pole -> Switched to Vessel USBL",
        "val1": "Pole USBL Beacon Dropout During Lowering of #A007", "val2": "Switched to Vessel USBL for Positioning (25m impact)",
        "usbl_sensor": "Vessel", "env_wind": "", "env_current": "",
        "remarks": "Survey Pole USBL stopped tracking beacons at 08:25; switched to Vessel USBL for navigation until Pole USBL restored for final fix [USBL:Vessel]"
    },
    {
        "id": 6, "event_type": "Mattress fix", "timestamp": "2026-11-05 11:36",
        "surveyor": "Abror", "ref_id": "CR-A1_M16 (#A007) [Vessel]",
        "val1": "Act E:194544.36, N:2702612.75, Z:-18.35 (dCL:0.18m)", "val2": "Brg:198.4 deg | NW:0.08m | SW:0.10m",
        "usbl_sensor": "Vessel", "env_wind": "16kt NE", "env_current": "0.40m/s",
        "remarks": "[Vessel] 2nd mattress CR-A1_M16 (#A007) installed and 4 ROV corners verified; frame recovered to deck at 12:18 [Wind:16kt NE | Curr:0.40m/s]"
    },
    {
        "id": 7, "event_type": "Mattress on water", "timestamp": "2026-11-05 13:18",
        "surveyor": "Roderick", "ref_id": "CR-A1_M17 (#A023)",
        "val1": "Attempted Mattress Placement (#A023)", "val2": "Concrete Debris on Seabed & Tagline Entanglement",
        "usbl_sensor": "", "env_wind": "", "env_current": "",
        "remarks": "Mattress #A023 lowered for CR-A1_M17; obstructed by concrete debris on seabed (14:00) and tagline entanglement; recovered to deck at 18:18 for inspection"
    },
    {
        "id": 8, "event_type": "Pole up", "timestamp": "2026-11-06 00:01",
        "surveyor": "Roderick", "ref_id": "CR-A1_L1",
        "val1": "Recovered & Secured on Deck Cradle", "val2": "Weather Standby & ROV Maintenance",
        "usbl_sensor": "", "env_wind": "24kt NE", "env_current": "0.55m/s",
        "remarks": "Survey pole recovered and secured due to weather standby and WROV maintenance [Wind:24kt NE | Curr:0.55m/s]"
    }
]
"""

NEW_LOAD_STATE = """def load_mti_state():
    st = None
    try:
        from app import AppConfig
        row = AppConfig.query.filter_by(key="mti_state_v1").first()
        if row and row.value:
            st = json.loads(row.value)
    except Exception:
        pass
    if not st and os.path.exists(MTI_STATE_FILE):
        try:
            with open(MTI_STATE_FILE, "r", encoding="utf-8") as f:
                st = json.load(f)
        except Exception:
            st = None
    if not isinstance(st, dict):
        st = {}
    changed = False
    if not st.get("ledger"):
        st["ledger"] = [dict(x) for x in PRELOADED_MTI_LEDGER]
        st["baseline_ledger_merged_v2"] = True
        changed = True
    elif not st.get("baseline_ledger_merged_v2"):
        existing_boxes = {r.get("design_box_id") for r in st.get("ledger", [])}
        for p in PRELOADED_MTI_LEDGER:
            if p["design_box_id"] not in existing_boxes:
                st["ledger"].append(dict(p))
        st["baseline_ledger_merged_v2"] = True
        changed = True
    if not st.get("input_logs"):
        st["input_logs"] = [dict(x) for x in PRELOADED_MTI_LOGS]
        st["baseline_logs_merged_v2"] = True
        changed = True
    elif not st.get("baseline_logs_merged_v2"):
        existing_keys = {(x.get("timestamp"), x.get("event_type")) for x in st["input_logs"]}
        next_id = max([int(x.get("id") or 0) for x in st["input_logs"]] + [0]) + 1
        for p in PRELOADED_MTI_LOGS:
            if (p["timestamp"], p["event_type"]) not in existing_keys:
                item = dict(p)
                item["id"] = next_id
                next_id += 1
                st["input_logs"].append(item)
        st["baseline_logs_merged_v2"] = True
        changed = True
    for r in st.get("ledger", []):
        if float(r.get("heading_deg") or 0) < 180.0:
            r["heading_deg"] = round(float(r.get("heading_deg") or 15.854) + 180.0, 3)
            changed = True
    if changed:
        save_mti_state(st)
    return st"""

NEW_SAVE_STATE = """def save_mti_state(state):
    raw = json.dumps(state, ensure_ascii=False)
    try:
        from app import db, AppConfig
        row = AppConfig.query.filter_by(key="mti_state_v1").first()
        if not row:
            row = AppConfig(key="mti_state_v1", value=raw)
            db.session.add(row)
        else:
            row.value = raw
        db.session.commit()
    except Exception:
        pass
    try:
        dname = os.path.dirname(MTI_STATE_FILE)
        if dname:
            os.makedirs(dname, exist_ok=True)
        with open(MTI_STATE_FILE, "w", encoding="utf-8") as f:
            f.write(raw)
    except Exception:
        pass"""

IMPORT_ROUTE_CODE = """
@mti_bp.route('/import_excel', methods=['POST'])
@login_required
def import_excel():
    import pandas as pd
    f = request.files.get('excel_file')
    if not f or not f.filename:
        flash("Please select an Excel (.xlsx) file to upload.", "warning")
        return redirect(request.referrer or '/mti')
    try:
        xls = pd.ExcelFile(f)
        state = load_mti_state()
        ledger = state.get("ledger", [])
        logs = state.get("input_logs", [])
        imported_f, imported_l = 0, 0
        for s in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=s).dropna(how='all')
            if df.empty:
                continue
            cols = [str(c).lower() for c in df.columns]
            if '1_mattress' in s.lower() or any('aslaid' in c or 'as-laid' in c or 'design_box' in c for c in cols):
                for _, row in df.iterrows():
                    rdict = {str(k).strip(): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                    uno = int(rdict.get('unit_no') or rdict.get('Unit #') or (len(ledger) + 1))
                    box = str(rdict.get('design_box_id') or rdict.get('Design Box ID') or rdict.get('ID') or f'CR-A1_M{uno}')
                    tag = str(rdict.get('physical_tag') or rdict.get('Mattress No (Tag)') or rdict.get('Mattress No') or '')
                    de = float(rdict.get('design_e') or rdict.get('Design Easting (m)') or 194541.443)
                    dn = float(rdict.get('design_n') or rdict.get('Design Northing (m)') or 2702613.394)
                    ae = float(rdict.get('aslaid_e') or rdict.get('As-Laid Easting (m)') or de)
                    an = float(rdict.get('aslaid_n') or rdict.get('As-Laid Northing (m)') or dn)
                    hdg = float(rdict.get('heading_deg') or rdict.get('As-Laid Bearing (Deg)') or 195.854)
                    if hdg < 180.0:
                        hdg = round(hdg + 180.0, 3)
                    cl = round(math.hypot(ae - de, an - dn), 2)
                    corners = compute_4_corners(ae, an, hdg, 6.0, 3.0)
                    entry = {
                        "id": max([int(x.get("id") or 0) for x in ledger] + [0]) + 1,
                        "unit_no": uno, "is_first_in_array": (uno == 1), "unit_type": "Concrete Mattress",
                        "crossing_id": str(rdict.get('crossing_id') or rdict.get('Crossing / Layer') or 'CR-A1_L1'),
                        "design_box_id": box, "physical_tag": tag,
                        "install_date": str(rdict.get('install_date') or rdict.get('Date/Time') or '2026-11-05 03:20'),
                        "usbl_sensor": str(rdict.get('usbl_sensor') or rdict.get('Active USBL') or 'Survey Pole'),
                        "design_e": round(de, 3), "design_n": round(dn, 3),
                        "qaqc_e": round(ae, 3), "qaqc_n": round(an, 3), "qaqc_brg": round(hdg, 3),
                        "aslaid_e": round(ae, 3), "aslaid_n": round(an, 3), "aslaid_z": float(rdict.get('aslaid_z') or -18.20),
                        "cl_offset_m": cl, "heading_deg": round(hdg, 3),
                        "gap_labels": str(rdict.get('gap_labels') or rdict.get('Corner Gaps') or '0.00m'),
                        "gap1_m": float(rdict.get('gap1_m') or 0.0), "gap2_m": float(rdict.get('gap2_m') or 0.0), "gap_m": float(rdict.get('gap_m') or 0.0),
                        "status": str(rdict.get('status') or rdict.get('Status') or 'Completed'),
                        "remarks": str(rdict.get('remarks') or rdict.get('Remarks') or ''),
                        **corners
                    }
                    existing = next((x for x in ledger if str(x.get("design_box_id")) == box), None)
                    if existing:
                        ledger.remove(existing)
                    ledger.append(entry)
                    imported_f += 1
            elif '2_survey' in s.lower() or any('event' in c or 'surveyor' in c for c in cols):
                for _, row in df.iterrows():
                    rdict = {str(k).strip(): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                    logs.append({
                        "id": max([int(x.get("id") or 0) for x in logs] + [0]) + 1,
                        "event_type": str(rdict.get('event_type') or rdict.get('Event Type') or 'Pole down'),
                        "timestamp": str(rdict.get('timestamp') or rdict.get('Date/Time') or '2026-11-05 00:00'),
                        "surveyor": str(rdict.get('surveyor') or rdict.get('Surveyor') or 'Surveyor'),
                        "ref_id": str(rdict.get('ref_id') or rdict.get('Location / Ref ID') or ''),
                        "val1": str(rdict.get('val1') or rdict.get('Primary Parameter / Status') or ''),
                        "val2": str(rdict.get('val2') or rdict.get('Secondary Parameter / Details') or ''),
                        "usbl_sensor": str(rdict.get('usbl_sensor') or rdict.get('Active USBL') or ''),
                        "env_wind": str(rdict.get('env_wind') or rdict.get('Wind') or ''),
                        "env_current": str(rdict.get('env_current') or rdict.get('Current') or ''),
                        "remarks": str(rdict.get('remarks') or rdict.get('Remarks / Action Taken') or rdict.get('Remarks') or '')
                    })
                    imported_l += 1
        state["ledger"] = ledger
        state["input_logs"] = logs
        save_mti_state(state)
        if imported_f == 0 and imported_l == 0:
            flash("The uploaded Excel file had 0 data rows (press Ctrl+S in Excel before uploading). Preloaded baseline report is active.", "warning")
        else:
            flash(f"Imported {imported_f} Mattress Fix(es) and {imported_l} Survey Log(s) from {f.filename}!", "success")
    except Exception as e:
        flash(f"Excel import error: {e}", "danger")
    return redirect(request.referrer or '/mti')
"""

def replace_func_via_ast(source_code, func_name, new_func_code):
    tree = ast.parse(source_code)
    lines = source_code.splitlines(keepends=True)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            start_line = node.decorator_list[0].lineno if node.decorator_list else node.lineno
            end_line = node.end_lineno
            new_lines = lines[:start_line - 1] + [new_func_code.rstrip() + "\n\n"] + lines[end_line:]
            return "".join(new_lines), (start_line, end_line)
    return source_code, None

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")

if "PRELOADED_MTI_LEDGER =" not in mc:
    mc = mc.replace("def load_mti_state():", PRELOAD_DATA_DEFS.strip() + "\n\ndef load_mti_state():", 1)

mc, s1 = replace_func_via_ast(mc, "load_mti_state", NEW_LOAD_STATE)
mc, s2 = replace_func_via_ast(mc, "save_mti_state", NEW_SAVE_STATE)

if "def import_excel():" not in mc:
    mc = mc.rstrip() + "\n\n" + IMPORT_ROUTE_CODE.strip() + "\n"

ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)
print(f"1. Preloaded baseline MTI report & upgraded PostgreSQL persistence in mti_blueprint.py ({s1}, {s2})!")

IMPORT_BTN_JS = """<script id="mtiExcelImportBtn">
document.addEventListener('DOMContentLoaded', function(){
  const expLink = document.querySelector('a[href*="export"]');
  if (expLink && !document.getElementById('mtiImportForm')) {
    const f = document.createElement('form');
    f.id = 'mtiImportForm'; f.action = '/mti/import_excel'; f.method = 'POST'; f.enctype = 'multipart/form-data';
    f.className = 'd-inline-block ms-1';
    f.innerHTML = '<input type="file" name="excel_file" id="mtiExcelFileInput" accept=".xlsx,.xls" style="display:none;" onchange="this.form.submit()">' +
      '<button type="button" class="btn btn-sm btn-outline-light fw-bold" onclick="document.getElementById(\\'mtiExcelFileInput\\').click()"><i class="fas fa-file-upload text-warning me-1"></i>Import Excel</button>';
    expLink.parentNode.insertBefore(f, expLink.nextSibling);
  }
});
</script>"""

for target in ["templates/mti_dashboard.html", "mti_blueprint.py"]:
    if not os.path.exists(target): continue
    with open(target, "r", encoding="utf-8-sig") as f: txt = f.read()
    if 'id="mtiExcelImportBtn"' not in txt and '</body>' in txt:
        txt = txt.replace('</body>', IMPORT_BTN_JS + '\n</body>', 1)
        if target.endswith(".py"): ast.parse(txt)
        with open(target, "w", encoding="utf-8") as f: f.write(txt)
        print(f"2. Added Import Excel (.xlsx) button to {target}!")

subprocess.run(["py", "sync.py", "feat: preload Nov 04-06 MTI Ledger and Survey Input Logs into PostgreSQL and add Excel import"], check=False)
