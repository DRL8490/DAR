import os, re, glob, ast, subprocess

print("=== [1/4] Updating mti_4panel_math.py (Surveyor Name & Placement Date/Time + 0.30m Thickness) ===")
if os.path.exists("mti_4panel_math.py"):
    m_txt = open("mti_4panel_math.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    m_txt = m_txt.replace("else 0.15)", "else 0.30)").replace("mat_thick = 0.15", "mat_thick = 0.30")
    if "surveyor_name" not in m_txt:
        m_txt = m_txt.replace(
            'usbl_s = str(fix_data.get("usbl_sensor") or "Survey Pole").strip()',
            'usbl_s = str(fix_data.get("usbl_sensor") or "Survey Pole").strip()\n    surv_name = str(fix_data.get("surveyor_name") or fix_data.get("surveyor") or fix_data.get("logged_by") or "Duty Surveyor").strip()'
        )
        m_txt = m_txt.replace(
            '"usbl_sensor": usbl_s,',
            '"usbl_sensor": usbl_s, "surveyor_name": surv_name,'
        )
    ast.parse(m_txt)
    open("mti_4panel_math.py", "w", encoding="utf-8").write(m_txt)
    print("  -> mti_4panel_math.py updated & AST-verified.")

print("=== [2/4] Updating mti_4panel_a3.py (North Arrows on P1 & P2 + Placement Date/Time & Surveyor Name) ===")
with open("_a3_north.py", "r", encoding="utf-8-sig") as f:
    a3_txt = f.read().lstrip("\ufeff")
ast.parse(a3_txt)
with open("mti_4panel_a3.py", "w", encoding="utf-8") as f:
    f.write(a3_txt)
print("  -> mti_4panel_a3.py updated & AST-verified.")

print("=== [3/4] Updating mti_4panel_reports.py (Placement Date/Time & Surveyor Name in A4 PDF & Word .docx) ===")
if os.path.exists("mti_4panel_reports.py"):
    r_txt = open("mti_4panel_reports.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    r_txt = r_txt.replace(
        'f"**Survey Date/Time:** {metrics.get(\'install_date\',\'\')} | **Deliverable Base:** {metrics.get(\'base_filename\',\'\')}",',
        'f"**Placement Date & Time:** {metrics.get(\'install_date\',\'\')} | **Surveyor Name:** {metrics.get(\'surveyor_name\',\'Duty Surveyor\')} | **Deliverable:** {metrics.get(\'base_filename\',\'\')}",'
    )
    r_txt = r_txt.replace(
        'f"DP2 MMA Prestige | Tung-Hsiao 2nd Stage Subsea Gas Pipeline Project | Date: {metrics.get(\'install_date\',\'\')}"',
        'f"DP2 MMA Prestige | Placement Date/Time: {metrics.get(\'install_date\',\'\')} | Surveyor: {metrics.get(\'surveyor_name\',\'Duty Surveyor\')}"'
    )
    ast.parse(r_txt)
    open("mti_4panel_reports.py", "w", encoding="utf-8").write(r_txt)
    print("  -> mti_4panel_reports.py updated & AST-verified.")

print("=== [4/4] Updating /mti/studio in mti_blueprint.py (Placement Date/Time & Surveyor Name Inputs) ===")
if os.path.exists("mti_blueprint.py"):
    b_txt = open("mti_blueprint.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")

    old_verify_block = "b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full = run_rov_4panel_verification(fix_data, cat_list, MTI_WS_DIR)"
    new_verify_block = (
        "if req.get('surveyor_name') or req.get('install_date'):\n"
        "        for r in ledger:\n"
        "            if str(r.get('design_box_id','')).upper() == str(fix_data.get('design_box_id','')).upper():\n"
        "                if req.get('surveyor_name'): r['surveyor_name'] = str(req['surveyor_name']).strip()\n"
        "                if req.get('install_date'): r['install_date'] = str(req['install_date']).strip()\n"
        "        try: save_mti_state(st)\n"
        "        except Exception: pass\n"
        "    b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full = run_rov_4panel_verification(fix_data, cat_list, MTI_WS_DIR)"
    )
    if "if req.get('surveyor_name')" not in b_txt and old_verify_block in b_txt:
        b_txt = b_txt.replace(old_verify_block, new_verify_block, 1)

    b_txt = b_txt.replace(
        'init_tag = fd.get("physical_tag") or "#A046"\n    return render_template_string(STUDIO_HTML_TEMPLATE, ledger=ledger, ledger_json=json.dumps(ledger), init_box=init_box, init_tag=init_tag)',
        'init_tag = fd.get("physical_tag") or "#A046"\n    init_date = fd.get("install_date") or "2026-11-04 14:34"\n    init_surveyor = fd.get("surveyor_name") or fd.get("surveyor") or "Duty Surveyor"\n    return render_template_string(STUDIO_HTML_TEMPLATE, ledger=ledger, ledger_json=json.dumps(ledger), init_box=init_box, init_tag=init_tag, init_date=init_date, init_surveyor=init_surveyor)'
    )

    new_studio_bar = """<div class="studio-card p-2 mb-2">
    <div class="row g-2 align-items-end">
      <div class="col-md-2 col-12">
        <label class="small fw-bold text-info">Ledger Switcher</label>
        <select id="ledgerSelect" class="form-select form-select-sm fw-bold bg-dark text-warning border-info" onchange="window.selectLedgerUnit(this.value)">
          {% for r in ledger %}
          <option value="{{ r.design_box_id }}" {% if r.design_box_id == init_box %}selected{% endif %}>
            #{{ r.unit_no }}: {{ r.design_box_id }} ({{ r.physical_tag }})
          </option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-1 col-6">
        <label class="small fw-bold text-light">Location ID</label>
        <input type="text" id="inpBoxId" class="form-control form-control-sm fw-bold" value="{{ init_box }}">
      </div>
      <div class="col-md-1 col-6">
        <label class="small fw-bold text-light">Mattress ID</label>
        <input type="text" id="inpTagId" class="form-control form-control-sm fw-bold" value="{{ init_tag }}">
      </div>
      <div class="col-md-2 col-6">
        <label class="small fw-bold text-info">Placement Date &amp; Time</label>
        <input type="text" id="inpInstallDate" class="form-control form-control-sm fw-bold bg-dark text-light border-info" value="{{ init_date }}" placeholder="YYYY-MM-DD HH:MM">
      </div>
      <div class="col-md-2 col-6">
        <label class="small fw-bold text-info">Surveyor Name</label>
        <input type="text" id="inpSurveyor" class="form-control form-control-sm fw-bold bg-dark text-warning border-info" value="{{ init_surveyor }}" placeholder="e.g. Abror / Roderick">
      </div>
      <div class="col-md-1 col-4">
        <label class="small fw-bold text-warning" title="Mattress Thickness (m)">Thick(m)</label>
        <input type="number" step="0.01" id="inpMatThick" class="form-control form-control-sm fw-bold bg-dark text-warning border-secondary" value="0.30">
      </div>
      <div class="col-md-1 col-4">
        <label class="small fw-bold text-light">P1 / P2</label>
        <div class="d-flex gap-1">
          <select id="fpScP1" class="form-select form-select-sm px-1" title="Panel 1 Scale"><option value="200">200</option><option value="250" selected>250</option><option value="300">300</option><option value="400">400</option></select>
          <select id="fpScP2" class="form-select form-select-sm px-1" title="Panel 2 Scale"><option value="50">50</option><option value="75" selected>75</option><option value="100">100</option></select>
        </div>
      </div>
      <div class="col-md-1 col-4 d-flex flex-column justify-content-center">
        <div class="form-check form-switch mb-0"><input class="form-check-input" type="checkbox" id="fpSnd" checked><label class="form-check-label small" for="fpSnd">Snd</label></div>
        <div class="form-check form-switch mb-0"><input class="form-check-input" type="checkbox" id="fpCnt" checked><label class="form-check-label small" for="fpCnt">Cnt/Hist</label></div>
      </div>
      <div class="col-md-1 col-12">
        <button type="button" id="btnRefresh4P" class="btn btn-sm btn-success fw-bold w-100" onclick="window.runStudioVerify()"><i class="fas fa-sync-alt"></i> Render</button>
      </div>
    </div>
  </div>"""

    if 'id="inpSurveyor"' not in b_txt:
        b_txt = re.sub(
            r'<div class="studio-card p-2 mb-2">\s*<div class="row g-2 align-items-end">.*?</div>\s*</div>\s*(?=\n\s*<div class="row g-2">)',
            new_studio_bar,
            b_txt,
            count=1,
            flags=re.S
        )
        b_txt = b_txt.replace(
            "document.getElementById('inpTagId').value = row.physical_tag || '';",
            "document.getElementById('inpTagId').value = row.physical_tag || '';\n    if (document.getElementById('inpInstallDate')) document.getElementById('inpInstallDate').value = row.install_date || '';\n    if (document.getElementById('inpSurveyor')) document.getElementById('inpSurveyor').value = row.surveyor_name || row.surveyor || 'Duty Surveyor';"
        )
        b_txt = b_txt.replace(
            "payload.physical_tag = document.getElementById('inpTagId').value.trim();",
            "payload.physical_tag = document.getElementById('inpTagId').value.trim();\n  if (document.getElementById('inpInstallDate')) payload.install_date = document.getElementById('inpInstallDate').value.trim();\n  if (document.getElementById('inpSurveyor')) payload.surveyor_name = document.getElementById('inpSurveyor').value.trim();\n  if (document.getElementById('inpMatThick')) payload.mat_thickness_m = document.getElementById('inpMatThick').value;"
        )
        b_txt = b_txt.replace(
            "document.getElementById('inpTagId').value = d.metrics.mattress_id || '';",
            "document.getElementById('inpTagId').value = d.metrics.mattress_id || '';\n          if (document.getElementById('inpInstallDate') && d.metrics.install_date) document.getElementById('inpInstallDate').value = d.metrics.install_date;\n          if (document.getElementById('inpSurveyor') && d.metrics.surveyor_name) document.getElementById('inpSurveyor').value = d.metrics.surveyor_name;"
        )

    ast.parse(b_txt)
    open("mti_blueprint.py", "w", encoding="utf-8").write(b_txt)
    print("  -> mti_blueprint.py updated & AST-verified.")

t_dash = "templates/mti_dashboard.html"
if os.path.exists(t_dash):
    d_txt = open(t_dash, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    if "inpFormSurveyorName" not in d_txt and "if (fixForm && !document.getElementById('btnPreview4Panel'))" in d_txt:
        d_txt = d_txt.replace(
            "if (fixForm && !document.getElementById('btnPreview4Panel')) {",
            """if (fixForm && !fixForm.querySelector('[name="surveyor_name"]')) {
      const dtInp = fixForm.querySelector('[name="install_date"], [name*="date"]');
      if (dtInp && dtInp.parentNode) {
        const sDiv = document.createElement('div');
        sDiv.className = dtInp.parentNode.className || 'col-md-4 col-6';
        sDiv.innerHTML = '<label class="form-label small fw-bold text-info">Surveyor Name</label><input type="text" name="surveyor_name" id="inpFormSurveyorName" class="form-control form-control-sm fw-bold" placeholder="e.g. Abror / Roderick" value="Duty Surveyor">';
        dtInp.parentNode.parentNode.insertBefore(sDiv, dtInp.parentNode.nextSibling);
      }
    }
    if (fixForm && !document.getElementById('btnPreview4Panel')) {"""
        )
        open(t_dash, "w", encoding="utf-8").write(d_txt)
        print("  -> Added Surveyor Name input field to Mattress Fix Form in templates/mti_dashboard.html")

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try: os.remove(p)
    except Exception: pass

sync_py = "python" if os.path.exists(".venv/Scripts/python.exe") else "py"
subprocess.run([sync_py, "sync.py", "feat(mti): add North arrows on P1 & P2 and add Placement Date/Time & Surveyor Name"], check=False)
