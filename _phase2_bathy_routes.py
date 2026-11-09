# --- STEP 4: FAST 4-PANEL STUDIO ROUTES & DEDICATED NEW WINDOW (/mti/studio) ---
import os, re, json, base64
import numpy as np
from flask import jsonify, send_file, render_template_string
from mti_4panel_math import run_rov_4panel_verification, parse_bathy_xyz_text
from mti_4panel_a3 import generate_a3_4panel_chart
from mti_4panel_reports import build_structured_report_markdown, generate_a4_report_pdf, generate_editable_docx

MTI_WS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
_as_bool = lambda v, d=True: d if v is None else str(v).strip().lower() in ("1", "true", "yes", "on")

def _resolve_fix_data(req, ledger):
    uno = str(req.get("unit_no") or req.get("fix_id") or "").strip()
    box_q = str(req.get("design_box_id") or req.get("location_id") or req.get("box_id") or "").strip()
    tag_q = str(req.get("physical_tag") or req.get("mattress_id") or "").strip()
    matched = None
    if box_q:
        matched = next((r for r in ledger if str(r.get("design_box_id", "")).upper() == box_q.upper()), None)
    if not matched and uno:
        matched = next((r for r in ledger if str(r.get("unit_no", "")) == uno or str(r.get("id", "")) == uno), None)
    if not matched and tag_q:
        matched = next((r for r in ledger if str(r.get("physical_tag", "")).replace("#", "").upper() == tag_q.replace("#", "").upper()), None)
    if not matched and ledger and not box_q:
        matched = ledger[0]
    fix_data = dict(matched) if matched else {}
    for k, v in req.items():
        if k in ("unit_no", "fix_id") and matched:
            continue
        if v is not None and str(v).strip() != "":
            fix_data[k] = v
    if box_q and "design_box_id" not in fix_data:
        fix_data["design_box_id"] = box_q
    return fix_data

@mti_bp.route('/verify_4panel', methods=['POST'])
@login_required
def verify_4panel():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    st = load_mti_state()
    ledger = st.get("ledger", [])
    cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    req = request.get_json(silent=True) or request.form.to_dict()
    fix_data = _resolve_fix_data(req, ledger)

    sc_p1, sc_p2 = int(float(req.get("scale_p1") or 250)), int(float(req.get("scale_p2") or 75))
    inc_hist = _as_bool(req.get("include_history"), True)
    sh_cont, sh_snd = _as_bool(req.get("show_contours"), True), _as_bool(req.get("show_soundings"), True)
    c_int, s_spc = float(req.get("contour_interval") or 0.05), float(req.get("spot_spacing") or 2.0)

    b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full = run_rov_4panel_verification(fix_data, cat_list, MTI_WS_DIR)
    png_b, _ = generate_a3_4panel_chart(b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full, MTI_WS_DIR, inc_hist, ledger, sc_p1, sc_p2, sh_cont, c_int, sh_snd, s_spc, save_pdf=False)
    rep_md = build_structured_report_markdown(metrics, inc_hist, ledger, sc_p1, sc_p2)

    cache_obj = {"fix_data": fix_data, "metrics": metrics, "report_md": rep_md, "scale_p1": sc_p1, "scale_p2": sc_p2, "include_history": inc_hist, "show_contours": sh_cont, "show_soundings": sh_snd, "contour_interval": c_int, "spot_spacing": s_spc}
    open(os.path.join(MTI_WS_DIR, "last_4panel_cache.json"), "w", encoding="utf-8").write(json.dumps(cache_obj, ensure_ascii=False))
    return jsonify({"status": "ok", "image_b64": base64.b64encode(png_b).decode("ascii"), "report_md": rep_md, "metrics": metrics})

def _load_4panel_cache():
    p = os.path.join(MTI_WS_DIR, "last_4panel_cache.json")
    if os.path.exists(p):
        try: return json.loads(open(p, "r", encoding="utf-8").read())
        except Exception: pass
    st = load_mti_state()
    return st.get("last_4panel") or {}

@mti_bp.route('/update_4panel_report', methods=['POST'])
@login_required
def update_4panel_report():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    last = _load_4panel_cache()
    req = request.get_json(silent=True) or request.form.to_dict()
    rep_md = str(req.get("report_md") or last.get("report_md") or "").strip()
    metrics = last.get("metrics") or {"location_id": "CR-A1_M15", "mattress_id": "#A046", "base_filename": "20261104_Mattress_CR-A1_M15_A046"}
    generate_a4_report_pdf(metrics, MTI_WS_DIR, rep_md)
    generate_editable_docx(metrics, rep_md, MTI_WS_DIR)
    last["report_md"] = rep_md
    open(os.path.join(MTI_WS_DIR, "last_4panel_cache.json"), "w", encoding="utf-8").write(json.dumps(last, ensure_ascii=False))
    return jsonify({"status": "ok", "base_filename": metrics.get("base_filename")})

@mti_bp.route('/upload_seabed', methods=['POST'])
@login_required
def upload_seabed():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req_json = request.get_json(silent=True) or {}
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(request.form.get("crossing_id") or req_json.get("crossing_id") or "CR-A1_L1").strip())
    raw_txt = ""
    f = request.files.get("seabed_file")
    if f and f.filename:
        raw_txt = f.read().decode("utf-8", errors="ignore")
    else:
        raw_txt = str(request.form.get("bathy_xyz_text") or req_json.get("bathy_xyz_text") or "")
    pts_arr = parse_bathy_xyz_text(raw_txt)
    if len(pts_arr) > 0:
        np.save(os.path.join(MTI_WS_DIR, f"{xing_id}_seabed.npy"), pts_arr)
        z_min, z_max = round(float(np.min(pts_arr[:, 2])), 2), round(float(np.max(pts_arr[:, 2])), 2)
        return jsonify({"status": "ok", "crossing_id": xing_id, "points": int(len(pts_arr)), "z_min": z_min, "z_max": z_max})
    return jsonify({"status": "error", "message": "No valid E N Z bathy points found."}), 400

@mti_bp.route('/clear_seabed', methods=['POST'])
@login_required
def clear_seabed():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req = request.get_json(silent=True) or request.form.to_dict()
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(req.get("crossing_id") or "CR-A1_L1").strip())
    p = os.path.join(MTI_WS_DIR, f"{xing_id}_seabed.npy")
    if os.path.exists(p):
        try: os.remove(p)
        except Exception: pass
    return jsonify({"status": "ok", "crossing_id": xing_id})

def _dl_4panel_file(kind, suffix, mime):
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    cache = _load_4panel_cache()
    metrics = cache.get("metrics") or {"location_id": "CR-A1_M15", "mattress_id": "#A046", "base_filename": "20261104_Mattress_CR-A1_M15_A046"}
    base = str(request.args.get("file") or metrics.get("base_filename") or "20261104_Mattress_CR-A1_M15_A046").strip()
    p = os.path.join(MTI_WS_DIR, base + suffix)
    rep_md = cache.get("report_md") or ""
    if kind == "a3_pdf" and not os.path.exists(p):
        st = load_mti_state()
        ledger = st.get("ledger", [])
        cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
        fd = cache.get("fix_data") or (ledger[0] if ledger else {})
        b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full = run_rov_4panel_verification(fd, cat_list, MTI_WS_DIR)
        generate_a3_4panel_chart(b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full, MTI_WS_DIR, cache.get("include_history", True), ledger, cache.get("scale_p1", 250), cache.get("scale_p2", 75), cache.get("show_contours", True), cache.get("contour_interval", 0.05), cache.get("show_soundings", True), cache.get("spot_spacing", 2.0), save_pdf=True)
    elif kind == "a4_pdf" and not os.path.exists(p):
        generate_a4_report_pdf(metrics, MTI_WS_DIR, rep_md or None)
    elif kind == "docx" and not os.path.exists(p):
        generate_editable_docx(metrics, rep_md or build_structured_report_markdown(metrics), MTI_WS_DIR)
    return send_file(p, as_attachment=True, download_name=base + suffix, mimetype=mime)

@mti_bp.route('/download_a3_pdf')
@login_required
def download_a3_pdf(): return _dl_4panel_file("a3_pdf", ".pdf", "application/pdf")

@mti_bp.route('/download_a3_png')
@login_required
def download_a3_png(): return _dl_4panel_file("a3_png", ".png", "image/png")

@mti_bp.route('/download_a4_pdf')
@login_required
def download_a4_pdf(): return _dl_4panel_file("a4_pdf", "_A4_Report.pdf", "application/pdf")

@mti_bp.route('/download_docx')
@login_required
def download_docx(): return _dl_4panel_file("docx", "_Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

STUDIO_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>4-Panel Subsea Mattress Verification Studio | DP2 MMA Prestige</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css" rel="stylesheet">
  <style>
    body { background:#0f172a; color:#f8fafc; font-family:system-ui,-apple-system,sans-serif; }
    .studio-card { background:#1e293b; border:1px solid #334155; border-radius:8px; }
    #fpVisBox { background:#ffffff; color:#0f172a; height:520px; overflow-y:auto; white-space:pre-wrap; font-size:12.5px; line-height:1.45; }
    #fpMdBox { background:#0f172a; color:#38bdf8; height:520px; font-size:12px; }
  </style>
</head>
<body>
<div class="container-fluid py-2 px-3">
  <div class="d-flex flex-wrap justify-content-between align-items-center py-2 px-3 mb-2 rounded" style="background:#020617;border:1px solid #1e293b;">
    <div class="d-flex flex-wrap align-items-center gap-2">
      <span class="fw-bold text-info fs-6"><i class="fas fa-drafting-compass me-2"></i>Subsea Mattress 4-Panel Verification &amp; Submittal Studio</span>
      <span id="fpActiveFilename" class="badge bg-primary font-monospace">Loading...</span>
      <span id="fpBathyBadge" class="badge bg-secondary font-monospace">BATHY: REF_DEPTH</span>
    </div>
    <div class="d-flex flex-wrap gap-1 align-items-center">
      <a id="dlA3Pdf" href="/mti/download_a3_pdf" class="btn btn-sm btn-danger fw-bold"><i class="fas fa-file-pdf me-1"></i>A3 Chart PDF</a>
      <a id="dlA3Png" href="/mti/download_a3_png" class="btn btn-sm btn-info text-dark fw-bold"><i class="fas fa-image me-1"></i>A3 PNG</a>
      <a id="dlA4Pdf" href="/mti/download_a4_pdf" class="btn btn-sm btn-warning text-dark fw-bold"><i class="fas fa-file-alt me-1"></i>A4 Report PDF</a>
      <a id="dlDocx" href="/mti/download_docx" class="btn btn-sm btn-primary fw-bold"><i class="fas fa-file-word me-1"></i>Editable Word (.docx)</a>
      <button type="button" class="btn btn-sm btn-outline-light ms-2" onclick="window.close()">Close Window</button>
    </div>
  </div>

  <div class="studio-card p-2 mb-2">
    <div class="row g-2 align-items-end">
      <div class="col-md-3 col-12">
        <label class="small fw-bold text-info">1-Click Installed Ledger Mattress Switcher</label>
        <select id="ledgerSelect" class="form-select form-select-sm fw-bold bg-dark text-warning border-info" onchange="window.selectLedgerUnit(this.value)">
          {% for r in ledger %}
          <option value="{{ r.design_box_id }}" {% if r.design_box_id == init_box %}selected{% endif %}>
            Unit #{{ r.unit_no }}: {{ r.design_box_id }} ({{ r.physical_tag }}) - {{ r.install_date }}
          </option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-2 col-6">
        <label class="small fw-bold text-light">Location Box ID</label>
        <input type="text" id="inpBoxId" class="form-control form-control-sm fw-bold" value="{{ init_box }}">
      </div>
      <div class="col-md-1 col-6">
        <label class="small fw-bold text-light">Mattress ID</label>
        <input type="text" id="inpTagId" class="form-control form-control-sm fw-bold" value="{{ init_tag }}">
      </div>
      <div class="col-md-1 col-6">
        <label class="small fw-bold text-light">P1 Scale</label>
        <select id="fpScP1" class="form-select form-select-sm"><option value="200">1:200</option><option value="250" selected>1:250</option><option value="300">1:300</option><option value="400">1:400</option></select>
      </div>
      <div class="col-md-1 col-6">
        <label class="small fw-bold text-light">P2 Scale</label>
        <select id="fpScP2" class="form-select form-select-sm"><option value="50">1:50</option><option value="75" selected>1:75</option><option value="100">1:100</option></select>
      </div>
      <div class="col-md-2 col-12 d-flex flex-column justify-content-center">
        <div class="form-check form-switch"><input class="form-check-input" type="checkbox" id="fpSnd" checked><label class="form-check-label small" for="fpSnd">Spot Soundings</label></div>
        <div class="form-check form-switch"><input class="form-check-input" type="checkbox" id="fpCnt" checked><label class="form-check-label small" for="fpCnt">Contours &amp; History</label></div>
      </div>
      <div class="col-md-2 col-12 d-flex gap-1">
        <button type="button" class="btn btn-sm btn-outline-info fw-bold w-50" onclick="window.toggleBathyDrawer()"><i class="fas fa-water me-1"></i>Bathy Input</button>
        <button type="button" id="btnRefresh4P" class="btn btn-sm btn-success fw-bold w-50" onclick="window.runStudioVerify()"><i class="fas fa-sync-alt me-1"></i>Render</button>
      </div>
    </div>

    <div id="bathyInputDrawer" class="mt-2 pt-2 border-top border-secondary" style="display:block;">
      <div class="row g-2 align-items-end">
        <div class="col-md-5 col-12">
          <label class="small fw-bold text-info"><i class="fas fa-water me-1"></i>Paste Pre-Survey Bathy Spot Soundings (E N Z or ID E N Z, one per line):</label>
          <textarea id="inpBathyXyz" class="form-control form-control-sm font-monospace bg-dark text-light border-secondary" rows="2" placeholder="194540.00 2702615.00 -18.42&#10;194542.00 2702613.00 -18.45&#10;194545.00 2702611.00 -18.48"></textarea>
        </div>
        <div class="col-md-3 col-12">
          <label class="small fw-bold text-info">Or Upload Bathy File (.xyz / .csv / .txt):</label>
          <input type="file" id="inpBathyFile" class="form-control form-control-sm bg-dark text-light border-secondary" accept=".xyz,.csv,.txt">
        </div>
        <div class="col-md-2 col-6">
          <label class="small fw-bold text-light">Fallback Ref Depth (m)</label>
          <input type="number" step="0.01" id="inpSeabedRefZ" class="form-control form-control-sm bg-dark text-warning border-secondary fw-bold" value="-18.45" title="Used when no .xyz soundings are uploaded">
        </div>
        <div class="col-md-2 col-6 d-flex gap-1">
          <button type="button" class="btn btn-sm btn-info text-dark fw-bold flex-grow-1" onclick="window.saveAndApplyBathy()"><i class="fas fa-check me-1"></i>Apply Bathy</button>
          <button type="button" class="btn btn-sm btn-outline-danger fw-bold" onclick="window.clearBathyData()" title="Clear uploaded bathy soundings"><i class="fas fa-trash"></i></button>
        </div>
      </div>
    </div>
  </div>

  <div class="row g-2">
    <div class="col-lg-7">
      <div class="studio-card p-2 text-center position-relative" style="min-height:560px;display:flex;align-items:center;justify-content:center;">
        <div id="fpSpinner" class="position-absolute top-50 start-50 translate-middle badge bg-dark border border-info p-3 fs-6" style="display:none;z-index:10;">
          <i class="fas fa-spinner fa-spin text-info me-2"></i>Rendering ISO A3 4-Panel Chart...
        </div>
        <img id="fpPreviewImg" src="" class="img-fluid rounded bg-white" style="max-height:550px;" alt="ISO A3 4-Panel Chart Preview">
      </div>
    </div>
    <div class="col-lg-5">
      <div class="studio-card p-2 d-flex flex-column h-100">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="small fw-bold text-info"><i class="fas fa-edit me-1"></i>Editable ISO A4 &amp; Word (.docx) Report Studio</span>
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-outline-info active" id="tabVis" onclick="window.toggleFpTab(false)">Visual Editor</button>
            <button type="button" class="btn btn-outline-info" id="tabMd" onclick="window.toggleFpTab(true)">Markdown Source</button>
          </div>
        </div>
        <div id="fpVisBox" contenteditable="true" class="form-control mb-2"></div>
        <textarea id="fpMdBox" class="form-control font-monospace mb-2" style="display:none;"></textarea>
        <div class="d-flex align-items-center gap-2">
          <button type="button" class="btn btn-sm btn-primary fw-bold flex-grow-1" onclick="window.apply4PanelReportEdits()"><i class="fas fa-save me-1"></i>Apply Edits to A4 PDF &amp; Word (.docx)</button>
          <span id="fpEditMsg" class="small fw-bold text-warning"></span>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
const LEDGER_DATA = {{ ledger_json | safe }};
const INIT_PARAMS = new URLSearchParams(window.location.search);

window.toggleBathyDrawer = function() {
  const d = document.getElementById('bathyInputDrawer');
  d.style.display = (d.style.display === 'none') ? 'block' : 'none';
};

window.selectLedgerUnit = function(boxId) {
  const row = LEDGER_DATA.find(r => r.design_box_id === boxId);
  if (row) {
    document.getElementById('inpBoxId').value = row.design_box_id || '';
    document.getElementById('inpTagId').value = row.physical_tag || '';
  }
  window.runStudioVerify({ design_box_id: boxId });
};

window.toggleFpTab = function(showMd) {
  const vis = document.getElementById('fpVisBox'), md = document.getElementById('fpMdBox');
  if (showMd) { md.value = vis.innerText; vis.style.display = 'none'; md.style.display = 'block'; }
  else { vis.innerText = md.value; md.style.display = 'none'; vis.style.display = 'block'; }
  document.getElementById('tabVis').classList.toggle('active', !showMd);
  document.getElementById('tabMd').classList.toggle('active', showMd);
};

window.saveAndApplyBathy = function() {
  const f = document.getElementById('inpBathyFile').files[0];
  const txt = document.getElementById('inpBathyXyz').value.trim();
  const boxVal = document.getElementById('inpBoxId').value.trim();
  const xingVal = boxVal.indexOf('CR-A3') === 0 ? 'CR-A3' : 'CR-A1_L1';
  if (f || txt) {
    const fd = new FormData();
    fd.append('crossing_id', xingVal);
    if (f) fd.append('seabed_file', f);
    if (txt) fd.append('bathy_xyz_text', txt);
    fetch('/mti/upload_seabed', { method: 'POST', body: fd })
      .then(r => r.json()).then(d => {
        if (d.status === 'ok') {
          window.runStudioVerify();
        } else {
          alert(d.message || 'Check E N Z format.');
        }
      });
  } else {
    window.runStudioVerify();
  }
};

window.clearBathyData = function() {
  document.getElementById('inpBathyXyz').value = '';
  document.getElementById('inpBathyFile').value = '';
  const boxVal = document.getElementById('inpBoxId').value.trim();
  const xingVal = boxVal.indexOf('CR-A3') === 0 ? 'CR-A3' : 'CR-A1_L1';
  fetch('/mti/clear_seabed', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({crossing_id: xingVal}) })
    .then(() => window.runStudioVerify());
};

window.runStudioVerify = function(extra) {
  const payload = Object.assign({}, Object.fromEntries(INIT_PARAMS.entries()), extra || {});
  payload.design_box_id = (extra && extra.design_box_id) || document.getElementById('inpBoxId').value.trim();
  payload.physical_tag = document.getElementById('inpTagId').value.trim();
  payload.scale_p1 = document.getElementById('fpScP1').value;
  payload.scale_p2 = document.getElementById('fpScP2').value;
  payload.show_soundings = document.getElementById('fpSnd').checked;
  payload.show_contours = document.getElementById('fpCnt').checked;
  payload.include_history = document.getElementById('fpCnt').checked;
  payload.seabed_ref_z = document.getElementById('inpSeabedRefZ').value;
  const inlineBathy = document.getElementById('inpBathyXyz').value.trim();
  if (inlineBathy) payload.bathy_xyz_text = inlineBathy;

  const btn = document.getElementById('btnRefresh4P'), sp = document.getElementById('fpSpinner');
  btn.disabled = true; sp.style.display = 'block';
  fetch('/mti/verify_4panel', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) })
    .then(r => r.json()).then(d => {
      btn.disabled = false; sp.style.display = 'none';
      if (d.status === 'ok') {
        document.getElementById('fpPreviewImg').src = 'data:image/png;base64,' + d.image_b64;
        document.getElementById('fpMdBox').value = d.report_md || '';
        document.getElementById('fpVisBox').innerText = d.report_md || '';
        if (d.metrics) {
          const fn = d.metrics.base_filename || 'Report';
          document.getElementById('fpActiveFilename').innerText = fn + '.pdf';
          document.getElementById('inpBoxId').value = d.metrics.location_id || '';
          document.getElementById('inpTagId').value = d.metrics.mattress_id || '';
          const bBadge = document.getElementById('fpBathyBadge');
          bBadge.innerText = 'BATHY: ' + (d.metrics.bathy_source || 'REF_DEPTH') + ' (' + (d.metrics.bathy_count || 0) + ' pts | ' + (d.metrics.bathy_z_min || 0) + 'm)';
          bBadge.className = 'badge font-monospace ' + (d.metrics.bathy_source === 'SURVEY_BATHY' ? 'bg-success' : 'bg-secondary');
          document.getElementById('dlA3Pdf').href = '/mti/download_a3_pdf?file=' + encodeURIComponent(fn);
          document.getElementById('dlA3Png').href = '/mti/download_a3_png?file=' + encodeURIComponent(fn);
          document.getElementById('dlA4Pdf').href = '/mti/download_a4_pdf?file=' + encodeURIComponent(fn);
          document.getElementById('dlDocx').href = '/mti/download_docx?file=' + encodeURIComponent(fn);
        }
      }
    }).catch(err => { btn.disabled = false; sp.style.display = 'none'; alert('Render error: ' + err); });
};

window.apply4PanelReportEdits = function() {
  const md = document.getElementById('fpMdBox'), vis = document.getElementById('fpVisBox');
  const txt = (md.style.display !== 'none') ? md.value : vis.innerText;
  md.value = txt;
  const msg = document.getElementById('fpEditMsg');
  msg.innerText = 'Saving...';
  fetch('/mti/update_4panel_report', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ report_md: txt }) })
    .then(r => r.json()).then(d => { msg.innerText = 'Saved A4 PDF & Word!'; setTimeout(() => { msg.innerText = ''; }, 2500); });
};

document.addEventListener('DOMContentLoaded', function() {
  if (INIT_PARAMS.get('seabed_ref_z')) document.getElementById('inpSeabedRefZ').value = INIT_PARAMS.get('seabed_ref_z');
  if (INIT_PARAMS.get('bathy_xyz_text')) document.getElementById('inpBathyXyz').value = INIT_PARAMS.get('bathy_xyz_text');
  window.runStudioVerify();
});
</script>
</body>
</html>"""

@mti_bp.route('/studio')
@login_required
def mti_4panel_studio_window():
    st = load_mti_state()
    ledger = st.get("ledger", [])
    req = request.args.to_dict()
    fd = _resolve_fix_data(req, ledger)
    init_box = fd.get("design_box_id") or "CR-A1_M15"
    init_tag = fd.get("physical_tag") or "#A046"
    return render_template_string(STUDIO_HTML_TEMPLATE, ledger=ledger, ledger_json=json.dumps(ledger), init_box=init_box, init_tag=init_tag)
