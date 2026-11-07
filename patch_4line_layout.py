import os, re, subprocess

FORM_AND_JS = """<form action="/mti/add_fix" method="POST" id="mattressFixForm" class="rov-corners-box">
  <div class="d-flex justify-content-between align-items-center mb-2 border-bottom pb-1">
    <h6 class="fw-bold text-success mb-0"><i class="fas fa-crosshairs me-1"></i> Mattress Fix Input Box (Actual Mattress &amp; Bearing Calculated from ROV Corners)</h6>
    <span class="badge bg-secondary" id="calcSourceBadge">Enter 4 ROV Corners</span>
  </div>

  <!-- LINE 1 : SELECT MATTRESS -->
  <div class="p-2 mb-2 rounded bg-white border text-dark">
    <div class="small fw-bold text-uppercase text-secondary mb-1" style="font-size:10.5px;">Line 1 : Select Mattress</div>
    <div class="row g-2 align-items-end">
      <div class="col-md-5">
        <label class="form-label small fw-bold text-success mb-1">Select Design Mattress (1 of 139)</label>
        <select id="designCatalogSelect" class="form-select form-select-sm border-success fw-bold" onchange="onSelectDesignMattress()">
          <option value="">-- Choose Design Mattress (139) --</option>
        </select>
      </div>
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Unit #</label>
        <input type="number" name="unit_no" id="inpUnitNo" class="form-control form-control-sm fw-bold" value="{{ ledger|length + 1 }}" min="1" max="300" oninput="toggleGapInputs()" required>
      </div>
      <div class="col-md-2 col-4">
        <div class="form-check form-switch pb-1">
          <input class="form-check-input" type="checkbox" id="chkFirstMattress" name="is_first_in_array" value="true" onchange="toggleGapInputs()">
          <label class="form-check-label small fw-bold text-primary" for="chkFirstMattress">1st Mattress (No Gaps)</label>
        </div>
      </div>
      <div class="col-md-3 col-4">
        <label class="form-label small fw-bold mb-1">Date/Time</label>
        <input type="text" name="install_date" id="inpFixDateTime" value="{{ today_str|default('') }} {{ now_dt_str.split('T')[-1] if now_dt_str is defined else '' }}" class="form-control form-control-sm" required>
      </div>
    </div>
  </div>

  <!-- LINE 2 : MATTRESS INFO INCLUDING THEORETICAL DESIGN -->
  <div class="p-2 mb-2 rounded bg-white border text-dark">
    <div class="small fw-bold text-uppercase text-secondary mb-1" style="font-size:10.5px;">Line 2 : Mattress Info &amp; Theoretical Design</div>
    <div class="row g-2 align-items-end">
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Xing / Layer</label>
        <input type="text" name="crossing_id" id="inpCrossingId" class="form-control form-control-sm bg-light" value="CR-A1_L1" required>
      </div>
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Box ID</label>
        <input type="text" name="design_box_id" id="inpBoxId" class="form-control form-control-sm bg-light" value="CR-A1_M{{ ledger|length + 1 }}" required>
      </div>
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Mattress Tag ID *</label>
        <input type="text" name="physical_tag" id="inpTagId" class="form-control form-control-sm fw-bold border-dark" placeholder="e.g., #A046" required>
      </div>
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Design E (m)</label>
        <input type="number" step="0.001" name="design_e" id="inpDesE" class="form-control form-control-sm bg-light" value="194541.443" oninput="recalcAllMattress()" required>
      </div>
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Design N (m)</label>
        <input type="number" step="0.001" name="design_n" id="inpDesN" class="form-control form-control-sm bg-light" value="2702613.394" oninput="recalcAllMattress()" required>
      </div>
      <div class="col-md-2 col-4">
        <label class="form-label small fw-bold mb-1">Design Brg (&deg;)</label>
        <input type="number" step="0.001" name="design_brg" id="inpDesBrg" class="form-control form-control-sm bg-light" value="15.854" oninput="recalcAllMattress()">
      </div>
    </div>
  </div>

  <!-- LINE 3 : AS-LAID QA/QC INPUT = MATTRESS CENTER (E,N) AND BEARING -->
  <div class="p-2 mb-2 rounded bg-white border border-primary text-dark">
    <div class="d-flex justify-content-between align-items-center mb-1">
      <span class="small fw-bold text-uppercase text-primary" style="font-size:10.5px;">Line 3 : As-Laid QA/QC Input = Mattress Center (E, N) &amp; Bearing</span>
      <button type="button" class="btn btn-outline-primary btn-sm py-0 px-2 fw-bold" style="font-size:11px;" onclick="seedCornersFromQaqc()">Seed 4 ROV Corners from QA/QC</button>
    </div>
    <div class="row g-2 align-items-end">
      <div class="col-md-3 col-6">
        <label class="form-label small fw-bold text-primary mb-1">Active USBL Used *</label>
        <select name="usbl_sensor" id="inpUsblSensor" class="form-select form-select-sm border-primary fw-bold">
          <option value="Pole USBL">Pole USBL (Primary)</option>
          <option value="Vessel USBL">Vessel USBL</option>
          <option value="Vessel Nav + Pole Fix">Vessel Nav + Pole Final Fix</option>
        </select>
      </div>
      <div class="col-md-3 col-6">
        <label class="form-label small fw-bold text-primary mb-1">QA/QC Center E *</label>
        <input type="number" step="0.001" name="qaqc_e" id="inpQaqcE" class="form-control form-control-sm border-primary fw-bold" placeholder="194541.520" oninput="recalcAllMattress()" required>
      </div>
      <div class="col-md-3 col-6">
        <label class="form-label small fw-bold text-primary mb-1">QA/QC Center N *</label>
        <input type="number" step="0.001" name="qaqc_n" id="inpQaqcN" class="form-control form-control-sm border-primary fw-bold" placeholder="2702613.300" oninput="recalcAllMattress()" required>
      </div>
      <div class="col-md-3 col-6">
        <label class="form-label small fw-bold text-primary mb-1">QA/QC Bearing (&deg;) *</label>
        <input type="number" step="0.001" name="qaqc_brg" id="inpQaqcBrg" class="form-control form-control-sm border-primary fw-bold" value="15.854" oninput="recalcAllMattress()" required>
      </div>
    </div>
  </div>

  <!-- LINE 4 : AS-LAID ROV COORDINATES INPUT = E,N,Z OF 4-CORNERS OF MATTRESS -->
  <div class="p-2 mb-2 rounded bg-white border border-success text-dark">
    <div class="small fw-bold text-uppercase text-success mb-1" style="font-size:10.5px;">Line 4 : As-Laid ROV Coordinates Input = E, N, Z of 4-Corners of Mattress</div>
    <div class="row g-2">
      <div class="col-md-3 col-6">
        <label class="small fw-bold text-dark mb-1">Corner 1 (C1: E, N, Z)</label>
        <div class="input-group input-group-sm">
          <input type="number" step="0.001" name="c1_e" id="c1_e" class="form-control px-1 border-success" placeholder="E1" oninput="recalcAllMattress()">
          <input type="number" step="0.001" name="c1_n" id="c1_n" class="form-control px-1 border-success" placeholder="N1" oninput="recalcAllMattress()">
          <input type="number" step="0.01" name="c1_z" id="c1_z" class="form-control px-1 border-success" placeholder="Z1" oninput="recalcAllMattress()">
        </div>
      </div>
      <div class="col-md-3 col-6">
        <label class="small fw-bold text-dark mb-1">Corner 2 (C2: E, N, Z)</label>
        <div class="input-group input-group-sm">
          <input type="number" step="0.001" name="c2_e" id="c2_e" class="form-control px-1 border-success" placeholder="E2" oninput="recalcAllMattress()">
          <input type="number" step="0.001" name="c2_n" id="c2_n" class="form-control px-1 border-success" placeholder="N2" oninput="recalcAllMattress()">
          <input type="number" step="0.01" name="c2_z" id="c2_z" class="form-control px-1 border-success" placeholder="Z2" oninput="recalcAllMattress()">
        </div>
      </div>
      <div class="col-md-3 col-6">
        <label class="small fw-bold text-dark mb-1">Corner 3 (C3: E, N, Z)</label>
        <div class="input-group input-group-sm">
          <input type="number" step="0.001" name="c3_e" id="c3_e" class="form-control px-1 border-success" placeholder="E3" oninput="recalcAllMattress()">
          <input type="number" step="0.001" name="c3_n" id="c3_n" class="form-control px-1 border-success" placeholder="N3" oninput="recalcAllMattress()">
          <input type="number" step="0.01" name="c3_z" id="c3_z" class="form-control px-1 border-success" placeholder="Z3" oninput="recalcAllMattress()">
        </div>
      </div>
      <div class="col-md-3 col-6">
        <label class="small fw-bold text-dark mb-1">Corner 4 (C4: E, N, Z)</label>
        <div class="input-group input-group-sm">
          <input type="number" step="0.001" name="c4_e" id="c4_e" class="form-control px-1 border-success" placeholder="E4" oninput="recalcAllMattress()">
          <input type="number" step="0.001" name="c4_n" id="c4_n" class="form-control px-1 border-success" placeholder="N4" oninput="recalcAllMattress()">
          <input type="number" step="0.01" name="c4_z" id="c4_z" class="form-control px-1 border-success" placeholder="Z4" oninput="recalcAllMattress()">
        </div>
      </div>
    </div>
  </div>

  <!-- BOX 1 : NORTH UP IMAGE FOR GAP INPUT + AUTO-CALCULATED ACTUAL MATTRESS & BEARING -->
  <div class="row g-2 align-items-stretch">
    <div class="col-md-5" id="gap1Container">
      <div class="p-2 border border-secondary rounded bg-white text-center text-dark h-100">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="badge bg-dark text-info" style="font-size:9.5px;">BOX 1 : N &uarr; NORTH UP GAPS</span>
          <span class="badge bg-light text-dark border" id="lblSvgBrg" style="font-size:9.5px;">Brg: 15.9&deg;</span>
        </div>
        <div class="d-flex justify-content-between px-1 mb-1">
          <input type="number" step="0.01" name="gap_nw" id="gNW" class="form-control form-control-sm text-center fw-bold" style="width:82px;height:24px;font-size:11px;" placeholder="NW (m)" oninput="syncDirGaps()">
          <input type="number" step="0.01" name="gap_ne" id="gNE" class="form-control form-control-sm text-center fw-bold" style="width:82px;height:24px;font-size:11px;" placeholder="NE (m)" oninput="syncDirGaps()">
        </div>
        <div class="my-1">
          <svg width="110" height="68" viewBox="0 0 110 68" style="background:#e2e8f0;border-radius:6px;border:1px solid #cbd5e1;">
            <line x1="55" y1="0" x2="55" y2="68" stroke="#94a3b8" stroke-dasharray="2,2"/><line x1="0" y1="34" x2="110" y2="34" stroke="#94a3b8" stroke-dasharray="2,2"/>
            <g id="svgMattRot" transform="rotate(15.854 55 34)">
              <rect x="44" y="12" width="22" height="44" fill="#0284c7" fill-opacity="0.3" stroke="#0369a1" stroke-width="1.8"/>
              <line x1="55" y1="12" x2="55" y2="20" stroke="#dc2626" stroke-width="2"/>
              <circle cx="44" cy="12" r="2.3" fill="#0f172a"/><circle cx="66" cy="12" r="2.3" fill="#0f172a"/>
              <circle cx="44" cy="56" r="2.3" fill="#0f172a"/><circle cx="66" cy="56" r="2.3" fill="#0f172a"/>
            </g>
          </svg>
        </div>
        <div class="d-flex justify-content-between px-1 mt-1">
          <input type="number" step="0.01" name="gap_sw" id="gSW" class="form-control form-control-sm text-center fw-bold" style="width:82px;height:24px;font-size:11px;" placeholder="SW (m)" oninput="syncDirGaps()">
          <input type="number" step="0.01" name="gap_se" id="gSE" class="form-control form-control-sm text-center fw-bold" style="width:82px;height:24px;font-size:11px;" placeholder="SE (m)" oninput="syncDirGaps()">
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
              <input type="number" step="0.001" name="aslaid_e" id="inpAsE" class="form-control form-control-sm bg-light fw-bold" readonly required>
            </div>
            <div class="col-3">
              <label class="small fw-bold mb-1">Actual N</label>
              <input type="number" step="0.001" name="aslaid_n" id="inpAsN" class="form-control form-control-sm bg-light fw-bold" readonly required>
            </div>
            <div class="col-2">
              <label class="small fw-bold mb-1">Actual Z</label>
              <input type="number" step="0.01" name="aslaid_z" id="inpAsZ" class="form-control form-control-sm bg-light fw-bold" value="0.00" readonly>
            </div>
            <div class="col-2">
              <label class="small fw-bold mb-1">Actual Brg (&deg;)</label>
              <input type="number" step="0.001" name="heading_deg" id="inpHeadingDeg" class="form-control form-control-sm bg-light fw-bold" value="15.854" readonly required>
            </div>
            <div class="col-2">
              <label class="small fw-bold mb-1">CL Off (m)</label>
              <input type="number" step="0.01" name="cl_offset_m" id="inpClOff" class="form-control form-control-sm bg-light fw-bold" placeholder="Auto" readonly required>
            </div>
          </div>
          <div class="row g-2 mb-2">
            <div class="col-4"><input type="text" name="env_wind" class="form-control form-control-sm" placeholder="Wind (e.g. 16kt NE)"></div>
            <div class="col-4"><input type="text" name="env_current" class="form-control form-control-sm" placeholder="Curr (e.g. 0.35m/s)"></div>
            <div class="col-4"><input type="text" name="env_swell" class="form-control form-control-sm" placeholder="Swell Hs (e.g. 0.7m)"></div>
          </div>
        </div>
        <div class="row g-2 align-items-end">
          <div class="col-3">
            <label class="small fw-bold mb-1">Status</label>
            <select name="status" class="form-select form-select-sm fw-bold">
              <option value="Completed">Completed</option>
              <option value="In Progress">In Progress</option>
              <option value="Planned">Planned</option>
            </select>
          </div>
          <div class="col-6">
            <label class="small fw-bold mb-1">Remarks</label>
            <input type="text" name="remarks" class="form-control form-control-sm" placeholder="Notes..." required>
          </div>
          <div class="col-3">
            <button type="submit" class="btn btn-sm btn-success fw-bold w-100"><i class="fas fa-save"></i> Save Fix</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</form>
<script>
document.addEventListener('DOMContentLoaded', function(){
  const sel = document.getElementById('designCatalogSelect');
  const catList = (typeof DESIGN_CATALOG !== 'undefined') ? DESIGN_CATALOG : ((typeof CATALOG !== 'undefined') ? CATALOG : []);
  if (sel && sel.options.length <= 1 && catList.length) {
    window.catalogByName = window.catalogByName || {};
    catList.forEach(it => {
      window.catalogByName[it.name] = it;
      sel.appendChild(new Option(`${it.name} (${it.layer}) - E:${it.design_e.toFixed(2)}, N:${it.design_n.toFixed(2)}, Brg:${it.bearing.toFixed(1)}°`, it.name));
    });
  }
  const dtEl = document.getElementById('inpFixDateTime');
  if (dtEl && (!dtEl.value || dtEl.value.trim() === '')) {
    const d = new Date(), p = n => String(n).padStart(2,'0');
    dtEl.value = `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }
  if (typeof openMobFix === 'function') {
    window.openMobFix = function(){
      document.getElementById('mobEvtCard').style.display='none';
      const c = document.getElementById('mobFixCard'); c.style.display='block';
      if (dtEl && typeof nowStr === 'function') dtEl.value = nowStr();
      c.scrollIntoView({behavior:'smooth'});
    };
  }
});
function onSelectDesignMattress(){
  const sel = document.getElementById('designCatalogSelect');
  const mapObj = (typeof catalogByName !== 'undefined' && Object.keys(catalogByName).length) ? catalogByName : (typeof catMap !== 'undefined' ? catMap : {});
  const it = sel ? mapObj[sel.value] : null;
  if (!it) return;
  document.getElementById('inpCrossingId').value = it.layer;
  document.getElementById('inpBoxId').value = it.name;
  document.getElementById('inpDesE').value = it.design_e.toFixed(3);
  document.getElementById('inpDesN').value = it.design_n.toFixed(3);
  if (document.getElementById('inpDesBrg')) document.getElementById('inpDesBrg').value = it.bearing.toFixed(3);
  if (document.getElementById('inpQaqcBrg')) document.getElementById('inpQaqcBrg').value = it.bearing.toFixed(3);
  recalcAllMattress();
}
function seedCornersFromQaqc(){
  const ce = parseFloat(document.getElementById('inpQaqcE')?.value || document.getElementById('inpDesE')?.value) || 0;
  const cn = parseFloat(document.getElementById('inpQaqcN')?.value || document.getElementById('inpDesN')?.value) || 0;
  const brg = parseFloat(document.getElementById('inpQaqcBrg')?.value || document.getElementById('inpDesBrg')?.value) || 0;
  if (!ce || !cn) return;
  const rad = brg * Math.PI / 180.0, sb = Math.sin(rad), cb = Math.cos(rad);
  [[1,-1],[1,1],[-1,1],[-1,-1]].forEach((s, idx) => {
    const i = idx + 1;
    document.getElementById(`c${i}_e`).value = (ce + s[0]*3.0*sb + s[1]*1.5*cb).toFixed(3);
    document.getElementById(`c${i}_n`).value = (cn + s[0]*3.0*cb - s[1]*1.5*sb).toFixed(3);
    if (!document.getElementById(`c${i}_z`).value) document.getElementById(`c${i}_z`).value = '-18.20';
  });
  recalcAllMattress();
}
function recalcAllMattress(){
  const de = parseFloat(document.getElementById('inpDesE')?.value);
  const dn = parseFloat(document.getElementById('inpDesN')?.value);
  const pts = [1,2,3,4].map(i => [
    parseFloat(document.getElementById(`c${i}_e`)?.value),
    parseFloat(document.getElementById(`c${i}_n`)?.value),
    parseFloat(document.getElementById(`c${i}_z`)?.value || '0')
  ]);
  let ae, an, az = 0, brg;
  const badge = document.getElementById('calcSourceBadge');
  if (pts.every(p => !isNaN(p[0]) && !isNaN(p[1]))) {
    ae = (pts[0][0]+pts[1][0]+pts[2][0]+pts[3][0])/4.0;
    an = (pts[0][1]+pts[1][1]+pts[2][1]+pts[3][1])/4.0;
    az = (pts[0][2]+pts[1][2]+pts[2][2]+pts[3][2])/4.0;
    const fe = (pts[0][0]+pts[1][0])/2.0, fn = (pts[0][1]+pts[1][1])/2.0;
    const be = (pts[2][0]+pts[3][0])/2.0, bn = (pts[2][1]+pts[3][1])/2.0;
    brg = ((Math.atan2(fe - be, fn - bn) * 180.0 / Math.PI) + 360.0) % 360.0;
    if (badge) { badge.className = 'badge bg-success'; badge.innerText = 'Calculated from 4 ROV Corners'; }
  } else {
    ae = parseFloat(document.getElementById('inpQaqcE')?.value);
    an = parseFloat(document.getElementById('inpQaqcN')?.value);
    brg = parseFloat(document.getElementById('inpQaqcBrg')?.value || document.getElementById('inpDesBrg')?.value || '15.854');
    if (badge) { badge.className = 'badge bg-secondary'; badge.innerText = 'Enter 4 ROV Corners (Previewing QA/QC)'; }
  }
  if (!isNaN(ae)) document.getElementById('inpAsE').value = ae.toFixed(3);
  if (!isNaN(an)) document.getElementById('inpAsN').value = an.toFixed(3);
  document.getElementById('inpAsZ').value = az.toFixed(2);
  if (!isNaN(brg)) {
    document.getElementById('inpHeadingDeg').value = brg.toFixed(3);
    const g = document.getElementById('svgMattRot');
    if (g) g.setAttribute('transform', `rotate(${brg} 55 34)`);
    const lbl = document.getElementById('lblSvgBrg');
    if (lbl) lbl.innerHTML = `Brg: ${brg.toFixed(1)}&deg;`;
  }
  if (!isNaN(de) && !isNaN(dn) && !isNaN(ae) && !isNaN(an)) {
    document.getElementById('inpClOff').value = Math.hypot(ae - de, an - dn).toFixed(2);
  }
}
function syncDirGaps(){
  const vals = ['gNW','gNE','gSW','gSE'].map(id => parseFloat(document.getElementById(id)?.value)).filter(v => !isNaN(v));
  document.getElementById('inpGap1').value = (vals[0] ?? 0).toFixed(2);
  document.getElementById('inpGap2').value = (vals[1] ?? vals[0] ?? 0).toFixed(2);
  ['gNW','gNE','gSW','gSE'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.borderColor = el.value === '' ? '#ced4da' : (parseFloat(el.value) <= 0.20 ? '#16a34a' : '#dc2626');
  });
}
</script>"""

for target in ["templates/mti_dashboard.html", "templates/mti_mobile.html", "mti_blueprint.py"]:
    if not os.path.exists(target): continue
    with open(target, "r", encoding="utf-8-sig") as f: txt = f.read()
    pat = r'<form action="/mti/add_fix" method="POST".*?</form>'
    if re.search(pat, txt, flags=re.S):
        txt = re.sub(pat, FORM_AND_JS, txt, count=1, flags=re.S)
        with open(target, "w", encoding="utf-8") as f: f.write(txt)
        print(f"Updated 4-Line + Box 1 Mattress Fix layout in {target}!")

subprocess.run(["py", "sync.py", "feat: structure Mattress Fix into Line 1-4 and Box 1 with ROV 4-corner auto-calculation"], check=False)
