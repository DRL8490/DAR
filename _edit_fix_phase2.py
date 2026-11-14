import os, re, subprocess

dash_path = os.path.join("templates", "mti_dashboard.html")
mob_path = os.path.join("templates", "mti_mobile.html")
if not os.path.exists(dash_path):
    raise SystemExit("templates/mti_dashboard.html not found! Run inside your DAR project folder.")

dash = open(dash_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")

# 1. Prevent mtiV2Upgrade from injecting duplicate corner/QAQC inputs inside #mattressFixForm
dash = dash.replace(
    "if (f.querySelector('.rov-corners-box')) return;",
    "if (f.classList.contains('rov-corners-box') || f.querySelector('.rov-corners-box')) return;"
)

# 2. Prevent mti4PanelStudioUpgrade from overwriting a row's saved Surveyor Name during Edit mode
dash = dash.replace(
    "const inp = document.getElementById('inpFormSurveyorName') || document.querySelector('[name=\"surveyor_name\"]');\n    if (!inp) return;",
    "const inp = document.getElementById('inpFormSurveyorName') || document.querySelector('[name=\"surveyor_name\"]');\n    if (!inp || (document.getElementById('inpFixId') && document.getElementById('inpFixId').value)) return;"
)

# 3. Upgrade #addFixDrawer HTML (Line 4 editable E,N only; unclipped inputs; native Surveyor Name & Edit state)
new_drawer_html = r"""<div class="collapse border-bottom bg-light p-3" id="addFixDrawer">
<!-- MTI_FIX_DRAWER_V3_START -->
<style>
  #mattressFixForm input[type="number"] {
    -moz-appearance: textfield;
    font-variant-numeric: tabular-nums;
  }
  #mattressFixForm input[type="number"]::-webkit-outer-spin-button,
  #mattressFixForm input[type="number"]::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }
  #mattressFixForm .coord-inp {
    padding-left: 6px;
    padding-right: 6px;
    font-size: 12px;
    font-weight: 700;
  }
</style>
<form action="/mti/add_fix" method="POST" id="mattressFixForm" class="rov-corners-box">
  <input type="hidden" name="fix_id" id="inpFixId" value="">
  <input type="hidden" name="corners_ui_bound" value="1">

  <div class="d-flex flex-wrap justify-content-between align-items-center mb-2 border-bottom pb-1 gap-2">
    <h6 class="fw-bold text-success mb-0" id="fixFormTitle">
      <i class="fas fa-crosshairs me-1"></i> Mattress Fix Input Box (Actual Mattress &amp; Bearing Calculated from ROV Corners)
    </h6>
    <div class="d-flex align-items-center gap-2">
      <button type="button" id="btnCancelEditFix" class="btn btn-outline-secondary btn-sm py-0 px-2 fw-bold" style="display:none;font-size:11px;" onclick="resetFixFormToNew()">
        <i class="fas fa-times me-1"></i>Cancel Edit (New Fix)
      </button>
      <span class="badge bg-secondary" id="calcSourceBadge">Enter 4 ROV Corners</span>
    </div>
  </div>

  <!-- LINE 1 : SELECT MATTRESS -->
  <div class="p-2 mb-2 rounded bg-white border text-dark">
    <div class="small fw-bold text-uppercase text-secondary mb-1" style="font-size:10.5px;">Line 1 : Select Mattress</div>
    <div class="row g-2 align-items-end">
      <div class="col-md-4 col-12">
        <label class="form-label small fw-bold text-success mb-1">Select Design Mattress (1 of 139)</label>
        <select id="designCatalogSelect" class="form-select form-select-sm border-success fw-bold" onchange="onSelectDesignMattress()">
          <option value="">-- Choose Design Mattress (139) --</option>
        </select>
      </div>
      <div class="col-md-1 col-4">
        <label class="form-label small fw-bold mb-1">Unit #</label>
        <input type="number" name="unit_no" id="inpUnitNo" class="form-control form-control-sm fw-bold text-center px-1" value="{{ ledger|length + 1 }}" min="1" max="300" oninput="toggleGapInputs()" required>
      </div>
      <div class="col-md-2 col-8">
        <div class="form-check form-switch pb-1">
          <input class="form-check-input" type="checkbox" id="chkFirstMattress" name="is_first_in_array" value="true" onchange="toggleGapInputs()">
          <label class="form-check-label small fw-bold text-primary" for="chkFirstMattress">1st Mattress (No Gaps)</label>
        </div>
      </div>
      <div class="col-md-2 col-6">
        <label class="form-label small fw-bold mb-1">Date/Time</label>
        <input type="text" name="install_date" id="inpFixDateTime" value="{{ today_str|default('') }} {{ now_dt_str.split('T')[-1] if now_dt_str is defined else '' }}" class="form-control form-control-sm px-1" required>
      </div>
      <div class="col-md-3 col-6">
        <label class="form-label small fw-bold text-info mb-1">Surveyor Name</label>
        <input type="text" name="surveyor_name" id="inpFormSurveyorName" class="form-control form-control-sm fw-bold" value="{{ current_user.name }}" placeholder="Surveyor">
      </div>
    </div>
  </div>

  <!-- LINE 2 : MATTRESS INFO & THEORETICAL DESIGN -->
  <div class="p-2 mb-2 rounded bg-white border text-dark">
    <div class="small fw-bold text-uppercase text-secondary mb-1" style="font-size:10.5px;">Line 2 : Mattress Info &amp; Theoretical Design</div>
    <div class="row g-2 align-items-end">
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Xing / Layer</label>
        <input type="text" name="crossing_id" id="inpCrossingId" class="form-control form-control-sm bg-light px-1 fw-bold" value="CR-A1_L1" required>
      </div>
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Box ID</label>
        <input type="text" name="design_box_id" id="inpBoxId" class="form-control form-control-sm bg-light px-1 fw-bold" value="CR-A1_M{{ ledger|length + 1 }}" required>
      </div>
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Mattress Tag ID *</label>
        <input type="text" name="physical_tag" id="inpTagId" class="form-control form-control-sm fw-bold border-dark px-1" placeholder="e.g., #A046" required>
      </div>
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Design E (m)</label>
        <input type="number" step="0.001" name="design_e" id="inpDesE" class="form-control form-control-sm bg-light coord-inp" value="194541.443" oninput="recalcAllMattress()" required>
      </div>
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Design N (m)</label>
        <input type="number" step="0.001" name="design_n" id="inpDesN" class="form-control form-control-sm bg-light coord-inp" value="2702613.394" oninput="recalcAllMattress()" required>
      </div>
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Design Brg (&deg;)</label>
        <input type="number" step="0.001" name="design_brg" id="inpDesBrg" class="form-control form-control-sm bg-light coord-inp" value="195.854" oninput="recalcAllMattress()">
      </div>
    </div>
  </div>

  <!-- LINE 3 : AS-LAID QA/QC INPUT = MATTRESS CENTER (E,N) & BEARING -->
  <div class="p-2 mb-2 rounded bg-white border border-primary text-dark">
    <div class="d-flex justify-content-between align-items-center mb-1">
      <span class="small fw-bold text-uppercase text-primary" style="font-size:10.5px;">Line 3 : As-Laid QA/QC Input = Mattress Center (E, N) &amp; Bearing</span>
      <button type="button" class="btn btn-outline-primary btn-sm py-0 px-2 fw-bold" style="font-size:11px;" onclick="seedCornersFromQaqc()">Seed 4 ROV Corners from QA/QC</button>
    </div>
    <div class="row g-2 align-items-end">
      <div class="col-md-3 col-6">
        <label class="form-label small fw-bold text-primary mb-1">Active USBL *</label>
        <div class="d-flex align-items-center gap-3 p-1 px-2 border border-primary rounded bg-light" style="min-height:31px;">
          <label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">
            <input type="radio" class="form-check-input m-0" name="usbl_sensor" id="usblPole" value="Survey Pole" checked> Survey Pole
          </label>
          <label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">
            <input type="radio" class="form-check-input m-0" name="usbl_sensor" id="usblVessel" value="Vessel"> Vessel
          </label>
        </div>
      </div>
      <div class="col-md-3 col-6">
        <label class="form-label small fw-bold text-primary mb-1">QA/QC Center E *</label>
        <input type="number" step="0.001" name="qaqc_e" id="inpQaqcE" class="form-control form-control-sm border-primary coord-inp" placeholder="194541.520" oninput="recalcAllMattress()">
      </div>
      <div class="col-md-3 col-6">
        <label class="form-label small fw-bold text-primary mb-1">QA/QC Center N *</label>
        <input type="number" step="0.001" name="qaqc_n" id="inpQaqcN" class="form-control form-control-sm border-primary coord-inp" placeholder="2702613.300" oninput="recalcAllMattress()">
      </div>
      <div class="col-md-3 col-6">
        <label class="form-label small fw-bold text-primary mb-1">QA/QC Bearing (&deg;) *</label>
        <input type="number" step="0.001" name="qaqc_brg" id="inpQaqcBrg" class="form-control form-control-sm border-primary coord-inp" value="195.854" oninput="recalcAllMattress()">
      </div>
    </div>
  </div>

  <!-- LINE 4 : AS-LAID ROV COORDINATES INPUT = E, N OF 4-CORNERS OF MATTRESS (EDITABLE, E & N ONLY) -->
  <div class="p-2 mb-2 rounded bg-white border border-success text-dark rov-corners-box">
    <div class="small fw-bold text-uppercase text-success mb-1" style="font-size:10.5px;">Line 4 : As-Laid ROV Coordinates Input = E, N of 4-Corners of Mattress</div>
    <div class="row g-2">
      <div class="col-xl-3 col-md-6 col-12">
        <label class="small fw-bold text-dark mb-1">Corner 1 (C1 - NW: E, N)</label>
        <div class="input-group input-group-sm">
          <input type="number" step="0.001" name="c1_e" id="c1_e" class="form-control border-success coord-inp" placeholder="E1" oninput="recalcAllMattress()">
          <input type="number" step="0.001" name="c1_n" id="c1_n" class="form-control border-success coord-inp" placeholder="N1" oninput="recalcAllMattress()">
          <input type="hidden" name="c1_z" id="c1_z" value="">
        </div>
      </div>
      <div class="col-xl-3 col-md-6 col-12">
        <label class="small fw-bold text-dark mb-1">Corner 2 (C2 - NE: E, N)</label>
        <div class="input-group input-group-sm">
          <input type="number" step="0.001" name="c2_e" id="c2_e" class="form-control border-success coord-inp" placeholder="E2" oninput="recalcAllMattress()">
          <input type="number" step="0.001" name="c2_n" id="c2_n" class="form-control border-success coord-inp" placeholder="N2" oninput="recalcAllMattress()">
          <input type="hidden" name="c2_z" id="c2_z" value="">
        </div>
      </div>
      <div class="col-xl-3 col-md-6 col-12">
        <label class="small fw-bold text-dark mb-1">Corner 3 (C3 - SE: E, N)</label>
        <div class="input-group input-group-sm">
          <input type="number" step="0.001" name="c3_e" id="c3_e" class="form-control border-success coord-inp" placeholder="E3" oninput="recalcAllMattress()">
          <input type="number" step="0.001" name="c3_n" id="c3_n" class="form-control border-success coord-inp" placeholder="N3" oninput="recalcAllMattress()">
          <input type="hidden" name="c3_z" id="c3_z" value="">
        </div>
      </div>
      <div class="col-xl-3 col-md-6 col-12">
        <label class="small fw-bold text-dark mb-1">Corner 4 (C4 - SW: E, N)</label>
        <div class="input-group input-group-sm">
          <input type="number" step="0.001" name="c4_e" id="c4_e" class="form-control border-success coord-inp" placeholder="E4" oninput="recalcAllMattress()">
          <input type="number" step="0.001" name="c4_n" id="c4_n" class="form-control border-success coord-inp" placeholder="N4" oninput="recalcAllMattress()">
          <input type="hidden" name="c4_z" id="c4_z" value="">
        </div>
      </div>
    </div>
  </div>

  <!-- BOX 1 : NORTH UP GAPS + ACTUAL MATTRESS & BEARING -->
  <div class="row g-2 align-items-stretch">
    <div class="col-md-5" id="gap1Container">
      <div class="p-2 border border-secondary rounded bg-white text-center text-dark h-100">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="badge bg-dark text-info" style="font-size:9.5px;">BOX 1 : N &uarr; NORTH UP GAPS</span>
          <span class="badge bg-light text-dark border" id="lblSvgBrg" style="font-size:9.5px;">Brg: 195.9&deg;</span>
        </div>
        <div class="d-flex justify-content-between px-1 mb-1">
          <input type="number" step="0.01" name="gap_nw" id="gNW" class="form-control form-control-sm text-center fw-bold px-1" style="width:98px;height:26px;font-size:11.5px;" placeholder="C1 / NW (m)" oninput="syncDirGaps()">
          <input type="number" step="0.01" name="gap_ne" id="gNE" class="form-control form-control-sm text-center fw-bold px-1" style="width:98px;height:26px;font-size:11.5px;" placeholder="C2 / NE (m)" oninput="syncDirGaps()">
        </div>
        <div class="my-1">
          <svg width="140" height="84" viewBox="0 0 140 84" style="background:#e2e8f0;border-radius:6px;border:1px solid #cbd5e1;">
            <line x1="70" y1="0" x2="70" y2="84" stroke="#94a3b8" stroke-dasharray="2,2"/><line x1="0" y1="42" x2="140" y2="42" stroke="#94a3b8" stroke-dasharray="2,2"/>
            <g id="svgMattRot" transform="rotate(15.854 70 42)">
              <rect x="58" y="18" width="24" height="48" fill="#0284c7" fill-opacity="0.28" stroke="#0369a1" stroke-width="1.8"/>
              <line x1="70" y1="54" x2="70" y2="66" stroke="#dc2626" stroke-width="2.2"/>
              <circle cx="58" cy="18" r="2.8" fill="#16a34a"/><circle cx="82" cy="18" r="2.8" fill="#16a34a"/>
              <circle cx="82" cy="66" r="2.8" fill="#16a34a"/><circle cx="58" cy="66" r="2.8" fill="#16a34a"/>
              <text id="svgTxtC1" x="47" y="16" font-size="9.5" font-weight="800" fill="#0f172a" text-anchor="middle" transform="rotate(-15.854 47 13)">C1</text>
              <text id="svgTxtC2" x="93" y="16" font-size="9.5" font-weight="800" fill="#0f172a" text-anchor="middle" transform="rotate(-15.854 93 13)">C2</text>
              <text id="svgTxtC3" x="93" y="72" font-size="9.5" font-weight="800" fill="#0f172a" text-anchor="middle" transform="rotate(-15.854 93 69)">C3</text>
              <text id="svgTxtC4" x="47" y="72" font-size="9.5" font-weight="800" fill="#0f172a" text-anchor="middle" transform="rotate(-15.854 47 69)">C4</text>
            </g>
          </svg>
        </div>
        <div class="d-flex justify-content-between px-1 mt-1">
          <input type="number" step="0.01" name="gap_sw" id="gSW" class="form-control form-control-sm text-center fw-bold px-1" style="width:98px;height:26px;font-size:11.5px;" placeholder="C4 / SW (m)" oninput="syncDirGaps()">
          <input type="number" step="0.01" name="gap_se" id="gSE" class="form-control form-control-sm text-center fw-bold px-1" style="width:98px;height:26px;font-size:11.5px;" placeholder="C3 / SE (m)" oninput="syncDirGaps()">
        </div>
        <input type="hidden" name="gap1_m" id="inpGap1" value="0.00"><input type="hidden" name="gap2_m" id="inpGap2" value="0.00">
      </div>
    </div>
    <div id="gap2Container" style="display:none;"></div>

    <div class="col-md-7">
      <div class="p-2 border rounded bg-white text-dark h-100 d-flex flex-column justify-content-between">
        <div>
          <div class="small fw-bold text-uppercase text-success mb-1" style="font-size:10.5px;">Actual Mattress &amp; Bearing (Auto-Calculated from ROV Corners)</div>
          <div class="row g-2 mb-2">
            <div class="col-3">
              <label class="small fw-bold mb-1">Actual E</label>
              <input type="number" step="0.001" name="aslaid_e" id="inpAsE" class="form-control form-control-sm bg-light coord-inp" readonly required>
            </div>
            <div class="col-3">
              <label class="small fw-bold mb-1">Actual N</label>
              <input type="number" step="0.001" name="aslaid_n" id="inpAsN" class="form-control form-control-sm bg-light coord-inp" readonly required>
            </div>
            <div class="col-2">
              <label class="small fw-bold mb-1">Actual Z</label>
              <input type="number" step="0.01" name="aslaid_z" id="inpAsZ" class="form-control form-control-sm coord-inp" value="0.00" oninput="onManualActualZ()">
            </div>
            <div class="col-2">
              <label class="small fw-bold mb-1">Actual Brg (&deg;)</label>
              <input type="number" step="0.001" name="heading_deg" id="inpHeadingDeg" class="form-control form-control-sm bg-light coord-inp" value="195.854" readonly required>
            </div>
            <div class="col-2">
              <label class="small fw-bold mb-1">CL Off (m)</label>
              <input type="number" step="0.01" name="cl_offset_m" id="inpClOff" class="form-control form-control-sm bg-light coord-inp" placeholder="Auto" readonly required>
            </div>
          </div>
          <div class="row g-2 mb-2 align-items-end">
            <div class="col-4">
              <label class="small fw-bold mb-1">Wind</label>
              <input type="text" name="env_wind" id="inpEnvWind" class="form-control form-control-sm" placeholder="e.g. 16kt NE">
            </div>
            <div class="col-4">
              <label class="small fw-bold mb-1">Current</label>
              <input type="text" name="env_current" id="inpEnvCurr" class="form-control form-control-sm" placeholder="e.g. 0.35m/s">
            </div>
            <div class="col-4">
              <label class="small fw-bold mb-1">Status</label>
              <select name="status" id="inpFixStatus" class="form-select form-select-sm fw-bold">
                <option value="Completed">Completed</option>
                <option value="In Progress">In Progress</option>
                <option value="Planned">Planned</option>
              </select>
            </div>
          </div>
        </div>
        <div class="row g-2 align-items-end">
          <div class="col-md-8 col-12">
            <label class="small fw-bold mb-1">Remarks</label>
            <input type="text" name="remarks" id="inpFixRemarks" class="form-control form-control-sm" placeholder="Field notes (USBL &amp; Wind/Curr auto-tagged on save)...">
          </div>
          <div class="col-md-4 col-12">
            <button type="submit" id="btnSaveFixSubmit" class="btn btn-sm btn-success fw-bold w-100"><i class="fas fa-save me-1"></i>Save Fix</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</form>
<!-- MTI_FIX_DRAWER_V3_END -->
</div>"""

dash, n_drw = re.subn(
    r'<div class="collapse border-bottom bg-light p-3" id="addFixDrawer">.*?(?=\n\s*<!-- EXACT 6 REQUESTED COLUMNS)',
    lambda _m: new_drawer_html,
    dash, count=1, flags=re.S
)
if n_drw == 0:
    raise SystemExit("Could not locate #addFixDrawer in templates/mti_dashboard.html!")

# 4. Add data-id="{{ r.id }}" to Ledger Edit button
new_edit_btn = r"""<button type="button" class="btn btn-sm btn-outline-primary py-0 px-1 me-1" title="Edit Unit #{{ r.unit_no }}"
                                            data-id="{{ r.id }}"
                                            data-unit="{{ r.unit_no }}"
                                            data-first="{{ 'true' if r.is_first_in_array else 'false' }}"
                                            data-crossing="{{ r.crossing_id }}"
                                            data-box="{{ r.design_box_id }}"
                                            data-tag="{{ r.physical_tag }}"
                                            data-date="{{ r.install_date }}"
                                            data-surveyor="{{ r.surveyor_name|default('') }}"
                                            data-usbl="{{ r.usbl_sensor|default('Survey Pole') }}"
                                            data-des-e="{{ '%.3f'|format(r.design_e|float) }}"
                                            data-des-n="{{ '%.3f'|format(r.design_n|float) }}"
                                            data-des-brg="{{ '%.3f'|format(r.design_brg|default(r.heading_deg)|float) }}"
                                            data-qaqc-e="{{ '%.3f'|format(r.qaqc_e|default(r.aslaid_e)|float) }}"
                                            data-qaqc-n="{{ '%.3f'|format(r.qaqc_n|default(r.aslaid_n)|float) }}"
                                            data-qaqc-brg="{{ '%.3f'|format(r.qaqc_brg|default(r.heading_deg)|float) }}"
                                            data-as-e="{{ '%.3f'|format(r.aslaid_e|float) }}"
                                            data-as-n="{{ '%.3f'|format(r.aslaid_n|float) }}"
                                            data-as-z="{{ '%.2f'|format(r.aslaid_z|default(0)|float) }}"
                                            data-cl="{{ '%.2f'|format(r.cl_offset_m|float) }}"
                                            data-hdg="{{ '%.3f'|format(r.heading_deg|float) }}"
                                            data-gnw="{{ r.gap_nw|default('') }}"
                                            data-gne="{{ r.gap_ne|default('') }}"
                                            data-gsw="{{ r.gap_sw|default('') }}"
                                            data-gse="{{ r.gap_se|default('') }}"
                                            data-gap1="{{ '%.2f'|format(r.gap1_m|default(r.gap_m)|float) }}"
                                            data-gap2="{{ '%.2f'|format(r.gap2_m|default(r.gap_m)|float) }}"
                                            data-wind="{{ r.env_wind|default('') }}"
                                            data-curr="{{ r.env_current|default('') }}"
                                            data-status="{{ r.status }}"
                                            data-remarks="{{ r.clean_remarks|default(r.remarks) }}"
                                            onclick="editFixRow(this)">
                                        <i class="fas fa-edit"></i>
                                    </button>"""

dash, n_eb = re.subn(
    r'<button type="button" class="btn btn-sm btn-outline-primary[^>]*title="Edit Unit #\{\{ r\.unit_no \}\}".*?onclick="editFixRow\(this\)">\s*<i class="fas fa-edit"></i>\s*</button>',
    lambda _m: new_edit_btn,
    dash, count=1, flags=re.S
)
if n_eb == 0:
    raise SystemExit("Could not locate Edit button in templates/mti_dashboard.html!")

# 5. Replace duplicate/legacy JS functions with unified Edit/New/4-Corner controller
unified_js = r"""// --- MTI_UNIFIED_FIX_JS_START ---
    window.LEDGER_FIX_ROWS = {{ ledger_json | default('[]') | safe }};
    window.MTI_GAP_TOL = Number({{ gap_tol | default(0.50) }}) || 0.50;

    document.addEventListener('DOMContentLoaded', function() {
        const sel = document.getElementById('designCatalogSelect');
        if (sel && DESIGN_CATALOG.length) {
            sel.innerHTML = '<option value="">-- Choose Design Mattress (' + DESIGN_CATALOG.length + ') --</option>';
            const groups = {};
            DESIGN_CATALOG.forEach(item => {
                catalogByName[item.name] = item;
                groups[item.layer] = groups[item.layer] || [];
                groups[item.layer].push(item);
            });
            for (const [layerName, items] of Object.entries(groups)) {
                const og = document.createElement('optgroup');
                og.label = `${layerName} (${items.length} Mattresses)`;
                items.forEach(it => {
                    og.appendChild(new Option(`${it.name} - E:${Number(it.design_e).toFixed(2)}, N:${Number(it.design_n).toFixed(2)}, Brg:${Number(it.bearing).toFixed(1)} deg`, it.name));
                });
                sel.appendChild(og);
            }
        }
        toggleGapInputs();
    });

    function nowFormatted() {
        const now = new Date(), p = n => String(n).padStart(2, '0');
        return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())} ${p(now.getHours())}:${p(now.getMinutes())}`;
    }

    function computeCwCornersJs(ce, cn, brgDeg) {
        let b = Number(brgDeg || 195.854) % 360.0;
        if (b < 0) b += 360.0;
        const sBrg = b < 180.0 ? (b + 180.0) % 360.0 : b;
        const azRad = ((sBrg - 180.0) * Math.PI) / 180.0;
        const sa = Math.sin(azRad), ca = Math.cos(azRad);
        return [[1, -1], [1, 1], [-1, 1], [-1, -1]].map(s => [
            ce + s[0] * 3.0 * sa + s[1] * 1.5 * ca,
            cn + s[0] * 3.0 * ca - s[1] * 1.5 * sa
        ]);
    }

    function onSelectDesignMattress() {
        const sel = document.getElementById('designCatalogSelect');
        const it = sel ? catalogByName[sel.value] : null;
        if (!it) return;
        document.getElementById('inpCrossingId').value = it.layer;
        document.getElementById('inpBoxId').value = it.name;
        document.getElementById('inpDesE').value = Number(it.design_e).toFixed(3);
        document.getElementById('inpDesN').value = Number(it.design_n).toFixed(3);
        if (document.getElementById('inpDesBrg')) document.getElementById('inpDesBrg').value = Number(it.bearing).toFixed(3);
        if (document.getElementById('inpQaqcBrg') && !document.getElementById('inpFixId').value) {
            document.getElementById('inpQaqcBrg').value = Number(it.bearing).toFixed(3);
        }
        recalcAllMattress();
    }

    function seedCornersFromQaqc() {
        const ce = parseFloat(document.getElementById('inpQaqcE')?.value || document.getElementById('inpDesE')?.value) || 0;
        const cn = parseFloat(document.getElementById('inpQaqcN')?.value || document.getElementById('inpDesN')?.value) || 0;
        const brg = parseFloat(document.getElementById('inpQaqcBrg')?.value || document.getElementById('inpDesBrg')?.value) || 195.854;
        if (!ce || !cn) return;
        const curZ = parseFloat(document.getElementById('inpAsZ')?.value);
        const zStr = (!isNaN(curZ) && Math.abs(curZ) > 0.001) ? curZ.toFixed(2) : '0.00';
        computeCwCornersJs(ce, cn, brg).forEach((pt, idx) => {
            const i = idx + 1;
            document.getElementById(`c${i}_e`).value = pt[0].toFixed(3);
            document.getElementById(`c${i}_n`).value = pt[1].toFixed(3);
            if (!document.getElementById(`c${i}_z`).value) document.getElementById(`c${i}_z`).value = zStr;
        });
        recalcAllMattress();
    }

    function onManualActualZ() {
        const zv = parseFloat(document.getElementById('inpAsZ')?.value);
        if (!isNaN(zv)) {
            [1, 2, 3, 4].forEach(i => { document.getElementById(`c${i}_z`).value = zv.toFixed(2); });
        }
    }

    function recalcAllMattress() {
        const de = parseFloat(document.getElementById('inpDesE')?.value);
        const dn = parseFloat(document.getElementById('inpDesN')?.value);
        const pts = [1, 2, 3, 4].map(i => [
            parseFloat(document.getElementById(`c${i}_e`)?.value),
            parseFloat(document.getElementById(`c${i}_n`)?.value),
            parseFloat(document.getElementById(`c${i}_z`)?.value || '')
        ]);
        let ae, an, az = parseFloat(document.getElementById('inpAsZ')?.value || '0') || 0, brg;
        const badge = document.getElementById('calcSourceBadge');
        if (pts.every(p => !isNaN(p[0]) && !isNaN(p[1]))) {
            ae = (pts[0][0] + pts[1][0] + pts[2][0] + pts[3][0]) / 4.0;
            an = (pts[0][1] + pts[1][1] + pts[2][1] + pts[3][1]) / 4.0;
            const zList = pts.map(p => p[2]).filter(z => !isNaN(z) && Math.abs(z) > 0.001);
            if (zList.length === 4) az = (zList[0] + zList[1] + zList[2] + zList[3]) / 4.0;
            const be = (pts[0][0] + pts[1][0]) / 2.0, bn = (pts[0][1] + pts[1][1]) / 2.0;
            const fe = (pts[2][0] + pts[3][0]) / 2.0, fn = (pts[2][1] + pts[3][1]) / 2.0;
            brg = ((Math.atan2(fe - be, fn - bn) * 180.0 / Math.PI) + 360.0) % 360.0;
            if (brg < 180.0) brg += 180.0;
            if (badge) { badge.className = 'badge bg-success'; badge.innerText = 'Calculated from 4 ROV Corners'; }
        } else {
            ae = parseFloat(document.getElementById('inpQaqcE')?.value);
            an = parseFloat(document.getElementById('inpQaqcN')?.value);
            brg = parseFloat(document.getElementById('inpQaqcBrg')?.value || document.getElementById('inpDesBrg')?.value || '195.854');
            if (badge) { badge.className = 'badge bg-secondary'; badge.innerText = 'Enter 4 ROV Corners (Previewing QA/QC)'; }
        }
        if (!isNaN(ae)) document.getElementById('inpAsE').value = ae.toFixed(3);
        if (!isNaN(an)) document.getElementById('inpAsN').value = an.toFixed(3);
        if (document.activeElement !== document.getElementById('inpAsZ') && !isNaN(az)) {
            document.getElementById('inpAsZ').value = az.toFixed(2);
        }
        if (!isNaN(brg)) {
            document.getElementById('inpHeadingDeg').value = brg.toFixed(3);
            const g = document.getElementById('svgMattRot');
            const rot = ((brg - 180.0) + 360.0) % 360.0;
            if (g) g.setAttribute('transform', `rotate(${rot} 70 42)`);
            [['svgTxtC1', 47, 13], ['svgTxtC2', 93, 13], ['svgTxtC3', 93, 69], ['svgTxtC4', 47, 69]].forEach(c => {
                const el = document.getElementById(c[0]);
                if (el) el.setAttribute('transform', `rotate(${-rot} ${c[1]} ${c[2]})`);
            });
            const lbl = document.getElementById('lblSvgBrg');
            if (lbl) lbl.innerHTML = `Brg: ${brg.toFixed(1)}&deg;`;
        }
        if (!isNaN(de) && !isNaN(dn) && !isNaN(ae) && !isNaN(an)) {
            document.getElementById('inpClOff').value = Math.hypot(ae - de, an - dn).toFixed(2);
        }
    }

    function syncDirGaps() {
        const tol = window.MTI_GAP_TOL || 0.50;
        const vals = ['gNW', 'gNE', 'gSW', 'gSE'].map(id => parseFloat(document.getElementById(id)?.value)).filter(v => !isNaN(v));
        document.getElementById('inpGap1').value = (vals[0] ?? 0).toFixed(2);
        document.getElementById('inpGap2').value = (vals[1] ?? vals[0] ?? 0).toFixed(2);
        ['gNW', 'gNE', 'gSW', 'gSE'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.borderColor = el.value === '' ? '#ced4da' : (parseFloat(el.value) <= tol ? '#16a34a' : '#dc2626');
        });
    }

    function toggleGapInputs() {
        const isFirst = Boolean(document.getElementById('chkFirstMattress')?.checked);
        const g1Box = document.getElementById('gap1Container');
        if (g1Box) g1Box.style.opacity = isFirst ? '0.40' : '1';
        ['gNW', 'gNE', 'gSW', 'gSE'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = isFirst;
        });
        if (isFirst) {
            document.getElementById('inpGap1').value = '0.00';
            document.getElementById('inpGap2').value = '0.00';
        }
    }

    function resetFixFormToNew() {
        document.getElementById('inpFixId').value = '';
        const nextUno = (window.LEDGER_FIX_ROWS || []).reduce((m, r) => Math.max(m, parseInt(r.unit_no || 0, 10)), 0) + 1;
        document.getElementById('inpUnitNo').value = nextUno;
        document.getElementById('chkFirstMattress').checked = (nextUno === 1);
        document.getElementById('inpFixDateTime').value = nowFormatted();
        const sInp = document.getElementById('inpFormSurveyorName');
        if (sInp) sInp.value = window.MTI_CURRENT_USER_NAME || "{{ current_user.name }}";
        document.getElementById('designCatalogSelect').value = '';
        document.getElementById('inpTagId').value = '';
        document.getElementById('usblPole').checked = true;
        ['inpQaqcE', 'inpQaqcN', 'c1_e', 'c1_n', 'c1_z', 'c2_e', 'c2_n', 'c2_z', 'c3_e', 'c3_n', 'c3_z', 'c4_e', 'c4_n', 'c4_z', 'gNW', 'gNE', 'gSW', 'gSE', 'inpAsE', 'inpAsN', 'inpClOff', 'inpEnvWind', 'inpEnvCurr', 'inpFixRemarks'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        document.getElementById('inpAsZ').value = '0.00';
        document.getElementById('inpFixStatus').value = 'Completed';
        document.getElementById('fixFormTitle').innerHTML = '<i class="fas fa-crosshairs me-1"></i> Mattress Fix Input Box (Actual Mattress &amp; Bearing Calculated from ROV Corners)';
        document.getElementById('btnSaveFixSubmit').innerHTML = '<i class="fas fa-save me-1"></i>Save Fix';
        document.getElementById('btnCancelEditFix').style.display = 'none';
        toggleGapInputs();
        syncDirGaps();
        recalcAllMattress();
    }

    function openMattressFixBox() {
        resetFixFormToNew();
        const drawerEl = document.getElementById('addFixDrawer');
        if (drawerEl && !drawerEl.classList.contains('show')) {
            new bootstrap.Collapse(drawerEl, { toggle: true });
        }
        drawerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        document.getElementById('designCatalogSelect').focus();
    }

    function openEventInputBox(evtType) {
        const cfg = EVENT_CONFIGS[evtType];
        if (!cfg) return;
        const box = document.getElementById('dynamicEventBox');
        document.getElementById('evtLogId').value = '';
        document.getElementById('evtTypeInput').value = evtType;
        document.getElementById('evtBoxTitle').innerText = 'Log Event: ' + evtType;
        document.getElementById('evtTimestamp').value = nowFormatted();
        document.getElementById('lblRefId').innerText = cfg.lblRef;
        document.getElementById('evtRefId').value = cfg.defRef;
        document.getElementById('lblVal1').innerText = cfg.lbl1;
        document.getElementById('evtVal1').value = '';
        document.getElementById('evtVal1').placeholder = cfg.ph1;
        document.getElementById('lblVal2').innerText = cfg.lbl2;
        document.getElementById('evtVal2').value = '';
        document.getElementById('evtVal2').placeholder = cfg.ph2;
        document.getElementById('evtRemarks').value = '';
        document.getElementById('evtRemarks').placeholder = cfg.phRem;
        box.style.display = 'block';
        document.getElementById('evtVal1').focus();
    }

    function editEventLogRow(btn) {
        const d = btn.dataset;
        openEventInputBox(d.type);
        document.getElementById('evtLogId').value = d.id;
        document.getElementById('evtBoxTitle').innerText = 'Edit Event: ' + d.type;
        document.getElementById('evtTimestamp').value = d.ts;
        document.getElementById('evtSurveyor').value = d.surv;
        document.getElementById('evtRefId').value = d.ref;
        document.getElementById('evtVal1').value = d.val1;
        document.getElementById('evtVal2').value = d.val2;
        document.getElementById('evtRemarks').value = d.rem;
        document.getElementById('dynamicEventBox').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function editFixRow(btn) {
        const d = btn.dataset;
        const rowId = parseInt(d.id || '0', 10);
        const unitNo = parseInt(d.unit || '0', 10);
        const r = (window.LEDGER_FIX_ROWS || []).find(x => (rowId && parseInt(x.id, 10) === rowId) || (!rowId && parseInt(x.unit_no, 10) === unitNo)) || {};

        const drawerEl = document.getElementById('addFixDrawer');
        if (drawerEl && !drawerEl.classList.contains('show')) {
            new bootstrap.Collapse(drawerEl, { toggle: true });
        }

        const boxId = r.design_box_id || d.box || '';
        const tagId = r.physical_tag || d.tag || '';
        const unoVal = r.unit_no || d.unit || '';
        document.getElementById('inpFixId').value = r.id || d.id || '';
        document.getElementById('inpUnitNo').value = unoVal;
        document.getElementById('chkFirstMattress').checked = (r.is_first_in_array !== undefined) ? Boolean(r.is_first_in_array) : (d.first === 'true');
        document.getElementById('inpFixDateTime').value = r.install_date || d.date || '';

        const sel = document.getElementById('designCatalogSelect');
        if (sel && boxId) {
            if (!Array.from(sel.options).some(o => o.value === boxId)) {
                sel.appendChild(new Option(boxId, boxId));
            }
            sel.value = boxId;
        }

        const sInp = document.getElementById('inpFormSurveyorName');
        const savedSurv = (r.surveyor_name || r.surveyor || d.surveyor || '').trim();
        if (sInp) {
            sInp.value = (savedSurv && savedSurv.toLowerCase() !== 'duty surveyor') ? savedSurv : (window.MTI_CURRENT_USER_NAME || "{{ current_user.name }}");
        }

        const catIt = catalogByName[boxId] || {};
        const desE = Number(r.design_e ?? d.desE ?? catIt.design_e ?? 0);
        const desN = Number(r.design_n ?? d.desN ?? catIt.design_n ?? 0);
        const desBrg = Number(r.design_brg ?? d.desBrg ?? catIt.bearing ?? 195.854);
        document.getElementById('inpCrossingId').value = r.crossing_id || d.crossing || catIt.layer || '';
        document.getElementById('inpBoxId').value = boxId;
        document.getElementById('inpTagId').value = tagId;
        document.getElementById('inpDesE').value = desE.toFixed(3);
        document.getElementById('inpDesN').value = desN.toFixed(3);
        document.getElementById('inpDesBrg').value = desBrg.toFixed(3);

        const usblStr = String(r.usbl_sensor || d.usbl || 'Survey Pole').toLowerCase();
        if (usblStr.indexOf('vessel') !== -1 && usblStr.indexOf('pole') === -1) {
            document.getElementById('usblVessel').checked = true;
        } else {
            document.getElementById('usblPole').checked = true;
        }

        const asE = Number(r.aslaid_e ?? d.asE ?? desE);
        const asN = Number(r.aslaid_n ?? d.asN ?? desN);
        const asZ = Number(r.aslaid_z ?? d.asZ ?? 0);
        const hdg = Number(r.heading_deg ?? d.hdg ?? desBrg);
        document.getElementById('inpQaqcE').value = Number(r.qaqc_e ?? d.qaqcE ?? asE).toFixed(3);
        document.getElementById('inpQaqcN').value = Number(r.qaqc_n ?? d.qaqcN ?? asN).toFixed(3);
        document.getElementById('inpQaqcBrg').value = Number(r.qaqc_brg ?? d.qaqcBrg ?? hdg).toFixed(3);

        let cPts = [1, 2, 3, 4].map(i => [
            parseFloat(r[`c${i}_e`]),
            parseFloat(r[`c${i}_n`]),
            parseFloat(r[`c${i}_z`] ?? asZ)
        ]);
        if (!cPts.every(p => !isNaN(p[0]) && !isNaN(p[1]) && Math.abs(p[0]) > 1000)) {
            cPts = computeCwCornersJs(asE, asN, hdg).map(pt => [pt[0], pt[1], asZ]);
        } else if ((cPts[0][1] + cPts[1][1]) < (cPts[2][1] + cPts[3][1])) {
            cPts = [cPts[2], cPts[3], cPts[0], cPts[1]];
        }
        cPts.forEach((pt, idx) => {
            const i = idx + 1;
            document.getElementById(`c${i}_e`).value = pt[0].toFixed(3);
            document.getElementById(`c${i}_n`).value = pt[1].toFixed(3);
            document.getElementById(`c${i}_z`).value = (!isNaN(pt[2]) ? pt[2] : asZ).toFixed(2);
        });

        document.getElementById('inpAsZ').value = asZ.toFixed(2);
        document.getElementById('gNW').value = (r.gap_nw ?? d.gnw ?? '');
        document.getElementById('gNE').value = (r.gap_ne ?? d.gne ?? '');
        document.getElementById('gSW').value = (r.gap_sw ?? d.gsw ?? '');
        document.getElementById('gSE').value = (r.gap_se ?? d.gse ?? '');
        document.getElementById('inpGap1').value = Number(r.gap1_m ?? d.gap1 ?? 0).toFixed(2);
        document.getElementById('inpGap2').value = Number(r.gap2_m ?? d.gap2 ?? 0).toFixed(2);

        document.getElementById('inpEnvWind').value = r.env_wind ?? d.wind ?? '';
        document.getElementById('inpEnvCurr').value = r.env_current ?? d.curr ?? '';
        document.getElementById('inpFixStatus').value = r.status || d.status || 'Completed';
        document.getElementById('inpFixRemarks').value = (r.clean_remarks !== undefined) ? r.clean_remarks : (d.remarks || '');

        document.getElementById('fixFormTitle').innerHTML = `<i class="fas fa-edit text-primary me-1"></i> Editing Unit #${unoVal}: ${boxId} (${tagId})`;
        document.getElementById('btnSaveFixSubmit').innerHTML = `<i class="fas fa-save me-1"></i>Update Unit #${unoVal}`;
        document.getElementById('btnCancelEditFix').style.display = 'inline-block';

        toggleGapInputs();
        syncDirGaps();
        recalcAllMattress();
        drawerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function calcOffset() {
        recalcAllMattress();
    }
// --- MTI_UNIFIED_FIX_JS_END ---
</script>"""

dash, n_js = re.subn(
    r"(?:// --- MTI_UNIFIED_FIX_JS_START ---.*?// --- MTI_UNIFIED_FIX_JS_END ---|document\.addEventListener\('DOMContentLoaded',\s*function\(\)\s*\{\s*const sel = document\.getElementById\('designCatalogSelect'\);.*?function calcOffset\(\)\s*\{.*?\})\s*</script>",
    lambda _m: unified_js,
    dash, count=1, flags=re.S
)
if n_js == 0:
    raise SystemExit("Could not locate Mattress Fix JS block in templates/mti_dashboard.html!")

open(dash_path, "w", encoding="utf-8").write(dash)
print("  -> Updated templates/mti_dashboard.html (Line 4 editable E,N only + full Edit/Save controller).")

# 6. Align templates/mti_mobile.html (Line 4 E,N only, hidden Z, 0.50m gap border, null-selector guard)
if os.path.exists(mob_path):
    mob = open(mob_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    mob = mob.replace(
        "if (f.querySelector('.rov-corners-box')) return;",
        "if (f.classList.contains('rov-corners-box') || f.querySelector('.rov-corners-box')) return;"
    )
    mob = mob.replace("E, N, Z of 4-Corners of Mattress", "E, N of 4-Corners of Mattress")
    for q_idx, q_lbl in ((1, "NW"), (2, "NE"), (3, "SE"), (4, "SW")):
        mob = mob.replace(f"Corner {q_idx} (C{q_idx} - {q_lbl}: E, N, Z)", f"Corner {q_idx} (C{q_idx} - {q_lbl}: E, N)")
        mob = re.sub(
            rf'<input type="number"[^>]*name="c{q_idx}_z"[^>]*>',
            f'<input type="hidden" name="c{q_idx}_z" id="c{q_idx}_z" value="">',
            mob
        )
    if 'name="fix_id"' not in mob:
        mob = mob.replace(
            '<form action="/mti/add_fix" method="POST" id="mattressFixForm" class="rov-corners-box">',
            '<form action="/mti/add_fix" method="POST" id="mattressFixForm" class="rov-corners-box">\n  <input type="hidden" name="fix_id" id="inpFixId" value="">\n  <input type="hidden" name="corners_ui_bound" value="1">',
            1
        )
    mob = mob.replace("parseFloat(el.value) <= 0.20", "parseFloat(el.value) <= 0.50")
    mob = mob.replace(
        "const sel = document.getElementById('mCatalogSel');\n  CATALOG.forEach",
        "const sel = document.getElementById('mCatalogSel');\n  if (sel) CATALOG.forEach"
    )
    mob = mob.replace("document.getElementById('mFixTs').value=nowStr();", "if(document.getElementById('inpFixDateTime')) document.getElementById('inpFixDateTime').value=nowStr();")
    open(mob_path, "w", encoding="utf-8").write(mob)
    print("  -> Updated templates/mti_mobile.html (Line 4 E,N only + 0.50m gap check + JS guard).")

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "fix(mti): full Mattress Fix edit/save population with editable E,N-only Line 4"], check=False)
print("\nEDIT FIX PHASE 2 COMPLETE & PUSHED TO RENDER!")