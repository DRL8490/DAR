# --- STEP 4: CLEAN 4-PANEL STUDIO (/mti/studio) & TABLE-BASED SURVEY SETUP (/mti/setup) ---
import os, re, gc, glob, json, base64
import numpy as np
from flask import jsonify, send_file, render_template_string
from mti_4panel_math import (
    AREA_LOCATIONS, run_rov_4panel_verification, parse_bathy_xyz_text,
    parse_design_catalog_text, parse_dxf_background,
    load_custom_catalog, build_crossing_boxes_from_catalog
)
from mti_4panel_a3 import generate_a3_4panel_chart
from mti_4panel_reports import build_structured_report_markdown, generate_a4_report_pdf, generate_editable_docx

MTI_WS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
_as_bool = lambda v, d=True: d if v is None else str(v).strip().lower() in ("1", "true", "yes", "on")

def _load_setup_meta():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    p = os.path.join(MTI_WS_DIR, "setup_meta.json")
    meta = {"cad": {}, "bathy": {}}
    if os.path.exists(p):
        try:
            meta = json.loads(open(p, "r", encoding="utf-8").read())
        except Exception:
            pass
    try:
        st = load_mti_state()
        db_setup = st.get("survey_setup") or {}
        for k in ("cad", "bathy"):
            for loc, info in (db_setup.get(k) or {}).items():
                if loc not in meta.get(k, {}):
                    meta.setdefault(k, {})[loc] = info
                if k == "bathy" and info.get("pts_compact"):
                    npy_p = os.path.join(MTI_WS_DIR, f"{loc}_seabed.npy")
                    if not os.path.exists(npy_p):
                        np.save(npy_p, np.array(info["pts_compact"], dtype=float))
                elif k == "cad" and info.get("polylines"):
                    cad_p = os.path.join(MTI_WS_DIR, f"{loc}_cad_bg.json")
                    if not os.path.exists(cad_p):
                        open(cad_p, "w", encoding="utf-8").write(json.dumps(info["polylines"]))
    except Exception:
        pass
    return meta

def _save_setup_meta(meta):
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    open(os.path.join(MTI_WS_DIR, "setup_meta.json"), "w", encoding="utf-8").write(json.dumps(meta))
    try:
        st = load_mti_state()
        st["survey_setup"] = meta
        save_mti_state(st)
    except Exception:
        pass

def _purge_cached_pdfs():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    for p in glob.glob(os.path.join(MTI_WS_DIR, "*.pdf")):
        try:
            os.remove(p)
        except Exception:
            pass

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
    _load_setup_meta()
    st = load_mti_state()
    ledger = st.get("ledger", [])
    cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    req = request.get_json(silent=True) or request.form.to_dict()
    fix_data = _resolve_fix_data(req, ledger)

    sc_p1, sc_p2 = int(float(req.get("scale_p1") or 250)), int(float(req.get("scale_p2") or 75))
    inc_hist = _as_bool(req.get("include_history"), True)
    sh_cont, sh_snd = _as_bool(req.get("show_contours"), True), _as_bool(req.get("show_soundings"), True)
    c_int, s_spc = float(req.get("contour_interval") or 0.05), float(req.get("spot_spacing") or 2.0)

    _purge_cached_pdfs()

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
    fname = str(request.form.get("filename") or req_json.get("filename") or "").strip()
    pts_json = req_json.get("points_array")
    if pts_json and isinstance(pts_json, list) and len(pts_json) > 0:
        pts_arr = np.array(pts_json, dtype=float)[:, :3]
        pts_arr[:, 2] = np.where((pts_arr[:, 2] > 0) & (pts_arr[:, 2] < 500), -pts_arr[:, 2], pts_arr[:, 2])
    else:
        raw_txt = ""
        f = request.files.get("seabed_file")
        if f and f.filename:
            fname = f.filename
            raw_txt = f.read().decode("utf-8", errors="ignore")
        else:
            raw_txt = str(request.form.get("bathy_xyz_text") or req_json.get("bathy_xyz_text") or "")
        pts_arr = parse_bathy_xyz_text(raw_txt)
    if len(pts_arr) > 0:
        if len(pts_arr) > 2500:
            pts_arr = pts_arr[::max(1, len(pts_arr) // 2500)]
        np.save(os.path.join(MTI_WS_DIR, f"{xing_id}_seabed.npy"), pts_arr)
        if xing_id == "CR-A1_L1":
            np.save(os.path.join(MTI_WS_DIR, "CR-A1_L2_seabed.npy"), pts_arr)
        z_min, z_max = round(float(np.min(pts_arr[:, 2])), 2), round(float(np.max(pts_arr[:, 2])), 2)
        meta = _load_setup_meta()
        meta.setdefault("bathy", {})[xing_id] = {
            "filename": fname or f"{xing_id}_bathy.xyz",
            "points": int(len(pts_arr)),
            "z_min": z_min,
            "z_max": z_max,
            "pts_compact": np.round(pts_arr[::max(1, len(pts_arr) // 800)], 2).tolist()
        }
        _save_setup_meta(meta)
        _purge_cached_pdfs()
        return jsonify({"status": "ok", "crossing_id": xing_id, "filename": fname or f"{xing_id}_bathy.xyz", "points": int(len(pts_arr)), "z_min": z_min, "z_max": z_max})
    return jsonify({"status": "error", "message": "No valid E N Z bathy points found in file."}), 400

@mti_bp.route('/clear_seabed', methods=['POST'])
@login_required
def clear_seabed():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req = request.get_json(silent=True) or request.form.to_dict()
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(req.get("crossing_id") or "ALL").strip())
    meta = _load_setup_meta()
    for fn in os.listdir(MTI_WS_DIR):
        if fn.endswith("_seabed.npy") and (xing_id in ("ALL", "GLOBAL") or fn == f"{xing_id}_seabed.npy"):
            try: os.remove(os.path.join(MTI_WS_DIR, fn))
            except Exception: pass
    if xing_id in ("ALL", "GLOBAL"):
        meta["bathy"] = {}
    else:
        meta.get("bathy", {}).pop(xing_id, None)
    _save_setup_meta(meta)
    _purge_cached_pdfs()
    return jsonify({"status": "ok", "crossing_id": xing_id})

@mti_bp.route('/save_cad_bg', methods=['POST'])
@login_required
def save_cad_bg():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req_json = request.get_json(silent=True) or {}
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(request.form.get("crossing_id") or req_json.get("crossing_id") or "CR-A1_L1").strip())
    fname = str(request.form.get("filename") or req_json.get("filename") or "").strip()
    polylines = req_json.get("polylines_array")
    if not polylines or not isinstance(polylines, list):
        raw_txt = ""
        f = request.files.get("cad_file")
        if f and f.filename:
            fname = f.filename
            raw_txt = f.read().decode("utf-8", errors="ignore")
        else:
            raw_txt = str(request.form.get("cad_text") or req_json.get("cad_text") or "")
        polylines = parse_dxf_background(raw_txt)
        if not polylines and raw_txt.strip():
            cur_poly = []
            for ln in raw_txt.splitlines():
                nums = [float(m) for m in re.findall(r"[+-]?\d+(?:\.\d+)?", ln)]
                if len(nums) >= 2 and abs(nums[0]) > 50000 and abs(nums[1]) > 50000:
                    e, n = (nums[1], nums[0]) if (nums[1] < nums[0] and nums[0] > 1000000) else (nums[0], nums[1])
                    cur_poly.append([round(e, 3), round(n, 3)])
                elif len(cur_poly) >= 2:
                    polylines.append(cur_poly); cur_poly = []
            if len(cur_poly) >= 2:
                polylines.append(cur_poly)
    if polylines:
        open(os.path.join(MTI_WS_DIR, f"{xing_id}_cad_bg.json"), "w", encoding="utf-8").write(json.dumps(polylines))
        n_verts = sum(len(p) for p in polylines)
        meta = _load_setup_meta()
        meta.setdefault("cad", {})[xing_id] = {
            "filename": fname or f"{xing_id}.dxf",
            "polylines": polylines[:250],
            "poly_count": len(polylines),
            "vertices": n_verts
        }
        _save_setup_meta(meta)
        _purge_cached_pdfs()
        return jsonify({"status": "ok", "crossing_id": xing_id, "filename": fname or f"{xing_id}.dxf", "polylines": len(polylines), "vertices": n_verts})
    return jsonify({"status": "error", "message": "No valid DXF LWPOLYLINE/POLYLINE/LINE entities found."}), 400

@mti_bp.route('/clear_cad_bg', methods=['POST'])
@login_required
def clear_cad_bg():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req = request.get_json(silent=True) or request.form.to_dict()
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(req.get("crossing_id") or "CR-A1_L1").strip())
    p = os.path.join(MTI_WS_DIR, f"{xing_id}_cad_bg.json")
    if os.path.exists(p):
        try: os.remove(p)
        except Exception: pass
    meta = _load_setup_meta()
    meta.get("cad", {}).pop(xing_id, None)
    _save_setup_meta(meta)
    _purge_cached_pdfs()
    return jsonify({"status": "ok", "crossing_id": xing_id})

@mti_bp.route('/save_design_catalog', methods=['POST'])
@login_required
def save_design_catalog():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req = request.get_json(silent=True) or request.form.to_dict()
    xing_def = str(req.get("crossing_id") or "CR-A1_L1").strip()
    new_entries = []
    if req.get("box_id") and req.get("design_e") and req.get("design_n"):
        try:
            new_entries.append({
                "layer": xing_def,
                "name": str(req.get("box_id")).strip(),
                "design_e": round(float(req.get("design_e")), 3),
                "design_n": round(float(req.get("design_n")), 3),
                "bearing": round(float(req.get("bearing") or 195.854) % 360.0, 3)
            })
        except Exception:
            pass
    raw_txt = str(req.get("catalog_text") or "")
    f = request.files.get("catalog_file")
    if f and f.filename:
        raw_txt += "\n" + f.read().decode("utf-8", errors="ignore")
    if raw_txt.strip():
        new_entries.extend(parse_design_catalog_text(raw_txt, xing_def))
    if not new_entries:
        return jsonify({"status": "error", "message": "Provide a single Design Box or paste Crossing, Box_ID, E, N, Bearing lines."}), 400
    existing = {str(b.get("name")): b for b in load_custom_catalog(MTI_WS_DIR) if b.get("name")}
    for e in new_entries:
        existing[e["name"]] = e
    saved_list = list(existing.values())
    open(os.path.join(MTI_WS_DIR, "custom_design_catalog.json"), "w", encoding="utf-8").write(json.dumps(saved_list, indent=2))
    _purge_cached_pdfs()
    return jsonify({"status": "ok", "added": len(new_entries), "total_custom": len(saved_list)})

@mti_bp.route('/clear_design_catalog', methods=['POST'])
@login_required
def clear_design_catalog():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    p = os.path.join(MTI_WS_DIR, "custom_design_catalog.json")
    if os.path.exists(p):
        try: os.remove(p)
        except Exception: pass
    _purge_cached_pdfs()
    return jsonify({"status": "ok"})

@mti_bp.route('/setup_status')
@login_required
def mti_setup_status():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    meta = _load_setup_meta()
    cad_meta = meta.get("cad") or {}
    bathy_meta = meta.get("bathy") or {}

    locations_table = []
    for loc in AREA_LOCATIONS:
        c_info = cad_meta.get(loc) or {}
        cad_p = os.path.join(MTI_WS_DIR, f"{loc}_cad_bg.json")
        cad_loaded = os.path.exists(cad_p)
        cad_polys = c_info.get("poly_count", 0)
        if cad_loaded and not cad_polys:
            try:
                d = json.loads(open(cad_p, "r", encoding="utf-8").read())
                cad_polys = len(d.get("polylines", []) if isinstance(d, dict) else d)
            except Exception:
                pass
        b_info = bathy_meta.get(loc) or {}
        npy_p = os.path.join(MTI_WS_DIR, f"{loc}_seabed.npy")
        bathy_loaded = os.path.exists(npy_p)
        b_pts = b_info.get("points", 0)
        z_min, z_max = b_info.get("z_min", 0.0), b_info.get("z_max", 0.0)
        if bathy_loaded and not b_pts:
            try:
                arr = np.load(npy_p)
                b_pts = int(len(arr))
                if b_pts > 0:
                    z_min, z_max = round(float(np.min(arr[:, 2])), 2), round(float(np.max(arr[:, 2])), 2)
            except Exception:
                pass
        locations_table.append({
            "location": loc,
            "cad_loaded": bool(cad_loaded and cad_polys > 0),
            "cad_filename": c_info.get("filename") or (f"{loc}.dxf" if cad_loaded else "No CAD File"),
            "cad_polylines": int(cad_polys),
            "bathy_loaded": bool(bathy_loaded and b_pts > 0),
            "bathy_filename": b_info.get("filename") or (f"{loc}_bathy.xyz" if bathy_loaded else "No Bathy File"),
            "bathy_points": int(b_pts),
            "z_min": z_min,
            "z_max": z_max
        })

    base_cats = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    custom_cats = load_custom_catalog(MTI_WS_DIR)
    merged = {str(b.get("name") or b.get("design_box_id")): dict(b, source="CAD Default") for b in base_cats}
    for cb in custom_cats:
        merged[str(cb.get("name"))] = dict(cb, source="Custom Override")
    return jsonify({
        "status": "ok",
        "locations": locations_table,
        "custom_design_count": len(custom_cats),
        "catalog": list(merged.values())
    })

def _dl_4panel_file(kind, suffix, mime):
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    _load_setup_meta()
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

STUDIO_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>4-Panel Subsea Mattress Verification Studio | DP2 MMA Prestige</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css" rel="stylesheet">
  <style>
    body { background:#0f172a; color:#f8fafc; font-family:system-ui,-apple-system,sans-serif; }
    .studio-card { background:#1e293b; border:1px solid #334155; border-radius:8px; }
    #fpVisBox { background:#ffffff; color:#0f172a; height:555px; overflow-y:auto; white-space:pre-wrap; font-size:12.5px; line-height:1.45; }
    #fpMdBox { background:#0f172a; color:#38bdf8; height:555px; font-size:12px; }
  </style>
</head>
<body>
<div class="container-fluid py-2 px-3">
  <div class="d-flex flex-wrap justify-content-between align-items-center py-2 px-3 mb-2 rounded" style="background:#020617;border:1px solid #1e293b;">
    <div class="d-flex flex-wrap align-items-center gap-2">
      <span class="fw-bold text-info fs-6"><i class="fas fa-drafting-compass me-2"></i>Subsea Mattress 4-Panel Verification &amp; Submittal Studio</span>
      <span id="fpActiveFilename" class="badge bg-primary font-monospace">Loading...</span>
      <span id="fpBathyBadge" class="badge bg-secondary font-monospace">BATHY: CHECKING...</span>
    </div>
    <div class="d-flex flex-wrap gap-1 align-items-center">
      <a href="/mti/setup" target="_blank" class="btn btn-sm btn-outline-info fw-bold me-1"><i class="fas fa-sliders-h me-1"></i>Survey Setup (CAD / Design / Bathy)</a>
      <a id="dlA3Pdf" href="/mti/download_a3_pdf" class="btn btn-sm btn-danger fw-bold"><i class="fas fa-file-pdf me-1"></i>A3 Chart PDF</a>
      <a id="dlA3Png" href="/mti/download_a3_png" class="btn btn-sm btn-info text-dark fw-bold"><i class="fas fa-image me-1"></i>A3 PNG</a>
      <a id="dlA4Pdf" href="/mti/download_a4_pdf" class="btn btn-sm btn-warning text-dark fw-bold"><i class="fas fa-file-alt me-1"></i>A4 Report PDF</a>
      <a id="dlDocx" href="/mti/download_docx" class="btn btn-sm btn-primary fw-bold"><i class="fas fa-file-word me-1"></i>Editable Word (.docx)</a>
      <button type="button" class="btn btn-sm btn-outline-light ms-1" onclick="window.close()">Close</button>
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
      <div class="col-md-2 col-12">
        <button type="button" id="btnRefresh4P" class="btn btn-sm btn-success fw-bold w-100" onclick="window.runStudioVerify()"><i class="fas fa-sync-alt me-1"></i>Render 4-Panel</button>
      </div>
    </div>
  </div>

  <div class="row g-2">
    <div class="col-lg-7">
      <div class="studio-card p-2 text-center position-relative" style="min-height:600px;display:flex;align-items:center;justify-content:center;">
        <div id="fpSpinner" class="position-absolute top-50 start-50 translate-middle badge bg-dark border border-info p-3 fs-6" style="display:none;z-index:10;">
          <i class="fas fa-spinner fa-spin text-info me-2"></i>Rendering ISO A3 4-Panel Chart...
        </div>
        <img id="fpPreviewImg" src="" class="img-fluid rounded bg-white" style="max-height:590px;" alt="ISO A3 4-Panel Chart Preview">
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

window.runStudioVerify = function(extra) {
  const payload = Object.assign({}, Object.fromEntries(INIT_PARAMS.entries()), extra || {});
  payload.design_box_id = (extra && extra.design_box_id) || document.getElementById('inpBoxId').value.trim();
  payload.physical_tag = document.getElementById('inpTagId').value.trim();
  payload.scale_p1 = document.getElementById('fpScP1').value;
  payload.scale_p2 = document.getElementById('fpScP2').value;
  payload.show_soundings = document.getElementById('fpSnd').checked;
  payload.show_contours = document.getElementById('fpCnt').checked;
  payload.include_history = document.getElementById('fpCnt').checked;

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
          if (d.metrics.bathy_source === 'SURVEY_BATHY') {
            bBadge.innerText = 'BATHY: ' + d.metrics.bathy_count + ' PTS (' + d.metrics.bathy_z_min + 'm to ' + d.metrics.bathy_z_max + 'm)';
            bBadge.className = 'badge font-monospace bg-success';
          } else {
            bBadge.innerText = 'NO BATHY UPLOADED FOR ' + (d.metrics.crossing_id || 'AREA');
            bBadge.className = 'badge font-monospace bg-warning text-dark';
          }
          const ts = Date.now();
          document.getElementById('dlA3Pdf').href = '/mti/download_a3_pdf?file=' + encodeURIComponent(fn) + '&t=' + ts;
          document.getElementById('dlA3Png').href = '/mti/download_a3_png?file=' + encodeURIComponent(fn) + '&t=' + ts;
          document.getElementById('dlA4Pdf').href = '/mti/download_a4_pdf?file=' + encodeURIComponent(fn) + '&t=' + ts;
          document.getElementById('dlDocx').href = '/mti/download_docx?file=' + encodeURIComponent(fn) + '&t=' + ts;
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
  window.runStudioVerify();
});
</script>
</body>
</html>"""

SETUP_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>MTI Survey Setup: Area CAD &amp; Bathy Tables + Design Sheet</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css" rel="stylesheet">
  <style>
    body { background:#0f172a; color:#f8fafc; font-family:system-ui,-apple-system,sans-serif; }
    .setup-card { background:#1e293b; border:1px solid #334155; border-radius:8px; height:100%; }
    .loc-table th, .loc-table td { vertical-align:middle; padding:6px 8px; font-size:12px; }
  </style>
</head>
<body>
<div class="container-fluid py-3 px-3">
  <div class="d-flex flex-wrap justify-content-between align-items-center py-2 px-3 mb-2 rounded" style="background:#020617;border:1px solid #1e293b;">
    <div>
      <span class="fw-bold text-info fs-5"><i class="fas fa-sliders-h me-2"></i>MTI Survey Baseline Setup Manager</span>
      <span class="badge bg-secondary ms-2">1. Area / CAD Files Table  |  2. Design Center &amp; Bearing Sheet  |  3. Area / Bathy Files Table</span>
    </div>
    <div class="d-flex gap-2">
      <a href="/mti/studio" target="_blank" class="btn btn-sm btn-info text-dark fw-bold"><i class="fas fa-drafting-compass me-1"></i>Open 4-Panel Studio</a>
      <a href="/mti" class="btn btn-sm btn-outline-light fw-bold"><i class="fas fa-arrow-left me-1"></i>Back to MTI Dashboard</a>
    </div>
  </div>

  <!-- Live Action Banner -->
  <div id="globalToastBanner" class="alert alert-info py-2 px-3 mb-3 fw-bold small" style="display:none;"></div>

  <!-- Hidden Reusable File Inputs for Per-Row Table Uploads -->
  <input type="file" id="hiddenCadFilePicker" accept=".dxf,.txt,.csv" style="display:none;" onchange="window.handleRowCadUpload(this)">
  <input type="file" id="hiddenBathyFilePicker" accept=".xyz,.csv,.txt" style="display:none;" onchange="window.handleRowBathyUpload(this)">

  <div class="row g-3">
    <!-- CARD 1: CAD BACKGROUND TABLE BY LOCATION -->
    <div class="col-lg-4">
      <div class="setup-card p-3 d-flex flex-column">
        <div class="d-flex justify-content-between align-items-center border-bottom border-secondary pb-2 mb-2">
          <h6 class="fw-bold text-info mb-0"><i class="fas fa-layer-group me-2"></i>1. CAD Background Table (Area vs. CAD File)</h6>
          <span id="cadStatusBadge" class="badge bg-secondary">0 / 8 Loaded</span>
        </div>
        <p class="small text-secondary mb-2">Assign an ASCII <code>.dxf</code> file to each crossing location. Click <strong>Upload</strong> on any row to attach or replace that location's CAD background.</p>

        <div class="table-responsive rounded border border-secondary flex-grow-1" style="background:#0f172a;">
          <table class="table table-dark table-striped table-hover loc-table mb-0">
            <thead>
              <tr class="text-info">
                <th style="width:28%;">Area / Location</th>
                <th style="width:47%;">CAD File (.dxf)</th>
                <th style="width:25%;" class="text-end">Action</th>
              </tr>
            </thead>
            <tbody id="cadTableBody">
              <tr><td colspan="3" class="text-center text-secondary py-3">Loading locations...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- CARD 2: CENTER POINT & BEARING DESIGN INPUT (KEPT INTACT) -->
    <div class="col-lg-4">
      <div class="setup-card p-3 d-flex flex-column">
        <div class="d-flex justify-content-between align-items-center border-bottom border-secondary pb-2 mb-2">
          <h6 class="fw-bold text-warning mb-0"><i class="fas fa-crosshairs me-2"></i>2. Center Point &amp; Bearing Design Sheet</h6>
          <span id="desStatusBadge" class="badge bg-primary">139 Boxes</span>
        </div>
        <p class="small text-secondary mb-2">Add or override Mattress Design Box Center Coordinates (<code>E, N</code> in TWD97) and Design South Bearing (<code>deg</code>). Click any row below to edit.</p>

        <div class="row g-1 mb-2">
          <div class="col-4">
            <label class="small fw-bold text-light">Crossing ID</label>
            <input type="text" id="desXingId" class="form-control form-control-sm bg-dark text-light border-secondary fw-bold" value="CR-A1_L1">
          </div>
          <div class="col-4">
            <label class="small fw-bold text-light">Box Location ID</label>
            <input type="text" id="desBoxId" class="form-control form-control-sm bg-dark text-warning border-secondary fw-bold" placeholder="CR-A1_M15">
          </div>
          <div class="col-4">
            <label class="small fw-bold text-light">South Brg (deg)</label>
            <input type="number" step="0.001" id="desBrg" class="form-control form-control-sm bg-dark text-light border-secondary" placeholder="195.854">
          </div>
          <div class="col-6">
            <label class="small fw-bold text-light">Design Easting E (m)</label>
            <input type="number" step="0.001" id="desEast" class="form-control form-control-sm bg-dark text-light border-secondary" placeholder="194541.443">
          </div>
          <div class="col-6">
            <label class="small fw-bold text-light">Design Northing N (m)</label>
            <input type="number" step="0.001" id="desNorth" class="form-control form-control-sm bg-dark text-light border-secondary" placeholder="2702613.394">
          </div>
        </div>

        <div class="mb-2">
          <label class="small fw-bold text-light">Or Bulk Paste / Upload CSV (<code>Crossing_ID, Box_ID, Design_E, Design_N, Bearing</code>):</label>
          <textarea id="desBulkText" class="form-control form-control-sm font-monospace bg-dark text-warning border-secondary mb-1" rows="2" placeholder="CR-A1_L1, CR-A1_M15, 194541.443, 2702613.394, 195.861"></textarea>
          <input type="file" id="desFileInput" class="form-control form-control-sm bg-dark text-light border-secondary" accept=".csv,.txt">
        </div>

        <div class="d-flex gap-2 mb-2">
          <button type="button" id="btnSaveDes" class="btn btn-sm btn-warning text-dark fw-bold flex-grow-1" onclick="window.saveDesignCatalog()"><i class="fas fa-save me-1"></i>Save Design Box(es)</button>
          <button type="button" class="btn btn-sm btn-outline-danger fw-bold" onclick="window.clearDesignCatalog()" title="Reset custom overrides"><i class="fas fa-undo me-1"></i>Reset</button>
        </div>

        <div class="table-responsive rounded border border-secondary flex-grow-1" style="max-height:220px;overflow-y:auto;background:#0f172a;">
          <table class="table table-sm table-dark table-striped mb-0" style="font-size:11px;">
            <thead class="sticky-top bg-dark"><tr><th>Crossing</th><th>Box ID</th><th>Design E</th><th>Design N</th><th>Brg</th></tr></thead>
            <tbody id="desCatalogTbody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- CARD 3: PRE-SURVEY BATHY TABLE BY LOCATION -->
    <div class="col-lg-4">
      <div class="setup-card p-3 d-flex flex-column">
        <div class="d-flex justify-content-between align-items-center border-bottom border-secondary pb-2 mb-2">
          <h6 class="fw-bold text-success mb-0"><i class="fas fa-water me-2"></i>3. Bathy Soundings Table (Area vs. Bathy File)</h6>
          <span id="bathyStatusBadge" class="badge bg-secondary">0 / 8 Loaded</span>
        </div>
        <p class="small text-secondary mb-2">Assign a pre-survey <code>.xyz</code> / <code>.csv</code> bathy file to each location. Click <strong>Upload</strong> on any row to crop &amp; save real seabed soundings for that crossing.</p>

        <div class="table-responsive rounded border border-secondary flex-grow-1" style="background:#0f172a;">
          <table class="table table-dark table-striped table-hover loc-table mb-0">
            <thead>
              <tr class="text-success">
                <th style="width:28%;">Area / Location</th>
                <th style="width:47%;">Bathy File (.xyz / .csv)</th>
                <th style="width:25%;" class="text-end">Action</th>
              </tr>
            </thead>
            <tbody id="bathyTableBody">
              <tr><td colspan="3" class="text-center text-secondary py-3">Loading locations...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
window._catalogCache = [];
window._activeUploadLoc = 'CR-A1_L1';

window.showSetupBanner = function(msg, cls) {
  const el = document.getElementById('globalToastBanner');
  el.className = 'alert py-2 px-3 mb-3 fw-bold small ' + (cls || 'alert-info');
  el.innerHTML = msg;
  el.style.display = 'block';
};

window.getCrossingBounds = function(xingId) {
  const basePrefix = xingId.split('_')[0];
  let boxes = (window._catalogCache || []).filter(b => b.layer === xingId);
  if (!boxes.length) {
    boxes = (window._catalogCache || []).filter(b => String(b.layer || '').indexOf(basePrefix) === 0);
  }
  if (!boxes.length) return null;
  const es = boxes.map(b => Number(b.design_e));
  const ns = boxes.map(b => Number(b.design_n));
  return {
    eMin: Math.min.apply(null, es) - 90.0,
    eMax: Math.max.apply(null, es) + 90.0,
    nMin: Math.min.apply(null, ns) - 90.0,
    nMax: Math.max.apply(null, ns) + 90.0
  };
};

window.refreshSetupStatus = function() {
  fetch('/mti/setup_status').then(r => r.json()).then(d => {
    if (d.status !== 'ok') return;
    window._catalogCache = d.catalog || [];
    const locs = d.locations || [];

    // 1. Populate CAD Table (Column 1: Area/Location | Column 2: CAD File | Column 3: Upload/Clear)
    let cadLoadedCnt = 0;
    const cadTbody = document.getElementById('cadTableBody');
    cadTbody.innerHTML = locs.map(row => {
      if (row.cad_loaded) cadLoadedCnt += 1;
      const fileCell = row.cad_loaded
        ? ('<div class="fw-bold text-info text-truncate" style="max-width:190px;" title="' + row.cad_filename + '"><i class="fas fa-check-circle me-1"></i>' + row.cad_filename + '</div>' +
           '<small class="text-light">' + row.cad_polylines + ' polyline(s) active</small>')
        : '<span class="text-secondary"><i class="fas fa-minus-circle me-1"></i>No CAD file</span>';
      return (
        '<tr id="cadRow_' + row.location + '">' +
        '<td class="fw-bold text-warning font-monospace">' + row.location + '</td>' +
        '<td id="cadCell_' + row.location + '">' + fileCell + '</td>' +
        '<td class="text-end text-nowrap">' +
          '<button type="button" class="btn btn-xs btn-sm btn-info text-dark fw-bold py-0 px-2 me-1" onclick="window.triggerRowCadPicker(\'' + row.location + '\')"><i class="fas fa-upload me-1"></i>Upload</button>' +
          (row.cad_loaded ? ('<button type="button" class="btn btn-xs btn-sm btn-outline-danger py-0 px-2" onclick="window.clearCadBg(\'' + row.location + '\')" title="Remove CAD file"><i class="fas fa-trash"></i></button>') : '') +
        '</td></tr>'
      );
    }).join('');
    document.getElementById('cadStatusBadge').innerText = cadLoadedCnt + ' / ' + locs.length + ' Loaded';
    document.getElementById('cadStatusBadge').className = 'badge ' + (cadLoadedCnt > 0 ? 'bg-info text-dark' : 'bg-secondary');

    // 2. Populate Design Catalog Table
    const cat = d.catalog || [];
    document.getElementById('desStatusBadge').innerText = cat.length + ' Boxes (' + (d.custom_design_count || 0) + ' Custom)';
    const desTbody = document.getElementById('desCatalogTbody');
    desTbody.innerHTML = cat.map((b, idx) => (
      '<tr style="cursor:pointer;" onclick="window.fillDesignRowByIdx(' + idx + ')">' +
      '<td>' + b.layer + '</td><td class="fw-bold text-warning">' + b.name + '</td>' +
      '<td>' + Number(b.design_e).toFixed(3) + '</td><td>' + Number(b.design_n).toFixed(3) + '</td><td>' + Number(b.bearing).toFixed(2) + '&deg;</td></tr>'
    )).join('');

    // 3. Populate Bathy Table (Column 1: Area/Location | Column 2: Bathy File | Column 3: Upload/Clear)
    let bathyLoadedCnt = 0;
    const bathyTbody = document.getElementById('bathyTableBody');
    bathyTbody.innerHTML = locs.map(row => {
      if (row.bathy_loaded) bathyLoadedCnt += 1;
      const fileCell = row.bathy_loaded
        ? ('<div class="fw-bold text-success text-truncate" style="max-width:190px;" title="' + row.bathy_filename + '"><i class="fas fa-check-circle me-1"></i>' + row.bathy_filename + '</div>' +
           '<small class="text-light">' + row.bathy_points.toLocaleString() + ' pts | Z: ' + row.z_min + 'm to ' + row.z_max + 'm</small>')
        : '<span class="text-secondary"><i class="fas fa-minus-circle me-1"></i>No Bathy file</span>';
      return (
        '<tr id="bathyRow_' + row.location + '">' +
        '<td class="fw-bold text-warning font-monospace">' + row.location + '</td>' +
        '<td id="bathyCell_' + row.location + '">' + fileCell + '</td>' +
        '<td class="text-end text-nowrap">' +
          '<button type="button" class="btn btn-xs btn-sm btn-success fw-bold py-0 px-2 me-1" onclick="window.triggerRowBathyPicker(\'' + row.location + '\')"><i class="fas fa-upload me-1"></i>Upload</button>' +
          (row.bathy_loaded ? ('<button type="button" class="btn btn-xs btn-sm btn-outline-danger py-0 px-2" onclick="window.clearBathySetup(\'' + row.location + '\')" title="Remove Bathy file"><i class="fas fa-trash"></i></button>') : '') +
        '</td></tr>'
      );
    }).join('');
    document.getElementById('bathyStatusBadge').innerText = bathyLoadedCnt + ' / ' + locs.length + ' Loaded';
    document.getElementById('bathyStatusBadge').className = 'badge ' + (bathyLoadedCnt > 0 ? 'bg-success' : 'bg-secondary');
  });
};

window.fillDesignRowByIdx = function(idx) {
  const b = (window._catalogCache || [])[idx];
  if (!b) return;
  document.getElementById('desXingId').value = b.layer || '';
  document.getElementById('desBoxId').value = b.name || '';
  document.getElementById('desEast').value = b.design_e || '';
  document.getElementById('desNorth').value = b.design_n || '';
  document.getElementById('desBrg').value = b.bearing || '';
  window.showSetupBanner('Loaded <strong>' + b.name + '</strong> (' + b.layer + ') into Design Editor.', 'alert-warning');
};

window.triggerRowCadPicker = function(loc) {
  window._activeUploadLoc = loc;
  const picker = document.getElementById('hiddenCadFilePicker');
  picker.value = '';
  picker.click();
};

window.handleRowCadUpload = function(inputEl) {
  const f = inputEl.files && inputEl.files[0];
  if (!f) return;
  const loc = window._activeUploadLoc || 'CR-A1_L1';
  const cell = document.getElementById('cadCell_' + loc);
  if (cell) cell.innerHTML = '<span class="text-info"><i class="fas fa-spinner fa-spin me-1"></i>Uploading &amp; parsing ' + f.name + '...</span>';

  const fd = new FormData();
  fd.append('crossing_id', loc);
  fd.append('filename', f.name);
  fd.append('cad_file', f);

  fetch('/mti/save_cad_bg', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(d => {
      if (d.status === 'ok') {
        window.showSetupBanner('&#10004; Saved CAD file <strong>' + d.filename + '</strong> (' + d.polylines + ' polylines) for <strong>' + d.crossing_id + '</strong>!', 'alert-success');
      } else {
        window.showSetupBanner('CAD Upload Error (' + loc + '): ' + (d.message || 'Invalid DXF'), 'alert-danger');
      }
      window.refreshSetupStatus();
    })
    .catch(err => {
      window.showSetupBanner('CAD Upload Network Error: ' + err, 'alert-danger');
      window.refreshSetupStatus();
    });
};

window.clearCadBg = function(loc) {
  fetch('/mti/clear_cad_bg', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({crossing_id: loc}) })
    .then(() => {
      window.showSetupBanner('Cleared CAD file for <strong>' + loc + '</strong>.', 'alert-secondary');
      window.refreshSetupStatus();
    });
};

window.triggerRowBathyPicker = function(loc) {
  window._activeUploadLoc = loc;
  const picker = document.getElementById('hiddenBathyFilePicker');
  picker.value = '';
  picker.click();
};

window.parseXyzTextClientSide = function(rawText, xingId) {
  const bnd = window.getCrossingBounds(xingId);
  const allPts = [];
  const inBoxPts = [];
  const lines = rawText.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const s = lines[i].trim();
    if (!s) continue;
    const c0 = s.charCodeAt(0);
    if (c0 === 35 || c0 === 47 || c0 === 69 || c0 === 101 || c0 === 88 || c0 === 120) continue;
    const ps = s.replace(/[,;]/g, ' ').trim().split(/\s+/);
    if (ps.length < 3) continue;
    const v0 = parseFloat(ps[0]), v1 = parseFloat(ps[1]), v2 = parseFloat(ps[2]);
    if (isNaN(v0) || isNaN(v1) || isNaN(v2)) continue;
    let e = v0, n = v1, z = v2;
    if (ps.length >= 4 && Math.abs(v0) < 50000 && Math.abs(v1) > 100000 && Math.abs(v2) > 100000) {
      e = v1; n = v2; z = parseFloat(ps[3]);
    }
    if (Math.abs(e) < 50000 || Math.abs(n) < 50000 || isNaN(z)) continue;
    if (n < e && e > 1000000) { const t = e; e = n; n = t; }
    if (z > 0 && z < 500) z = -Math.abs(z);
    const pt = [Math.round(e * 1000) / 1000, Math.round(n * 1000) / 1000, Math.round(z * 1000) / 1000];
    allPts.push(pt);
    if (bnd && e >= bnd.eMin && e <= bnd.eMax && n >= bnd.nMin && n <= bnd.nMax) {
      inBoxPts.push(pt);
    }
  }
  const chosen = (inBoxPts.length >= 4) ? inBoxPts : allPts;
  const maxKeep = 2500;
  if (chosen.length > maxKeep) {
    const step = Math.ceil(chosen.length / maxKeep);
    const thinned = [];
    for (let j = 0; j < chosen.length; j += step) thinned.push(chosen[j]);
    return { points: thinned, totalRead: allPts.length, croppedCount: inBoxPts.length };
  }
  return { points: chosen, totalRead: allPts.length, croppedCount: inBoxPts.length };
};

window.handleRowBathyUpload = function(inputEl) {
  const f = inputEl.files && inputEl.files[0];
  if (!f) return;
  const loc = window._activeUploadLoc || 'CR-A1_L1';
  const cell = document.getElementById('bathyCell_' + loc);
  if (cell) cell.innerHTML = '<span class="text-warning"><i class="fas fa-spinner fa-spin me-1"></i>Reading &amp; cropping ' + f.name + '...</span>';

  const reader = new FileReader();
  reader.onload = function(evt) {
    const parsed = window.parseXyzTextClientSide(evt.target.result || '', loc);
    if (!parsed.points.length) {
      window.showSetupBanner('Bathy Error: No valid E N Z coordinates found in ' + f.name, 'alert-danger');
      window.refreshSetupStatus();
      return;
    }
    if (cell) cell.innerHTML = '<span class="text-info"><i class="fas fa-spinner fa-spin me-1"></i>Saving ' + parsed.points.length.toLocaleString() + ' pts...</span>';
    fetch('/mti/upload_seabed', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        crossing_id: loc,
        filename: f.name,
        points_array: parsed.points
      })
    }).then(r => r.json()).then(d => {
      if (d.status === 'ok') {
        window.showSetupBanner('&#10004; Saved Bathy file <strong>' + d.filename + '</strong> for <strong>' + d.crossing_id + '</strong> (' + d.points.toLocaleString() + ' pts | Z: ' + d.z_min + 'm to ' + d.z_max + 'm)!', 'alert-success');
      } else {
        window.showSetupBanner('Bathy Upload Error: ' + (d.message || 'Error'), 'alert-danger');
      }
      window.refreshSetupStatus();
    }).catch(err => {
      window.showSetupBanner('Bathy Upload Error: ' + err, 'alert-danger');
      window.refreshSetupStatus();
    });
  };
  reader.readAsText(f);
};

window.clearBathySetup = function(loc) {
  fetch('/mti/clear_seabed', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({crossing_id: loc}) })
    .then(() => {
      window.showSetupBanner('Cleared Bathy file for <strong>' + loc + '</strong>.', 'alert-secondary');
      window.refreshSetupStatus();
    });
};

window.saveDesignCatalog = function() {
  const btn = document.getElementById('btnSaveDes');
  btn.disabled = true;
  const fd = new FormData();
  fd.append('crossing_id', document.getElementById('desXingId').value);
  fd.append('box_id', document.getElementById('desBoxId').value);
  fd.append('design_e', document.getElementById('desEast').value);
  fd.append('design_n', document.getElementById('desNorth').value);
  fd.append('bearing', document.getElementById('desBrg').value);
  fd.append('catalog_text', document.getElementById('desBulkText').value);
  const f = document.getElementById('desFileInput').files[0];
  if (f) fd.append('catalog_file', f);
  fetch('/mti/save_design_catalog', { method: 'POST', body: fd }).then(r => r.json()).then(d => {
    btn.disabled = false;
    if (d.status === 'ok') {
      document.getElementById('desBulkText').value = '';
      window.showSetupBanner('&#10004; Saved ' + d.added + ' design box entry/entries!', 'alert-success');
      window.refreshSetupStatus();
    } else window.showSetupBanner(d.message || 'Error saving design catalog.', 'alert-danger');
  }).catch(() => { btn.disabled = false; });
};

window.clearDesignCatalog = function() {
  if (!confirm('Reset all custom design box overrides back to default CAD catalog?')) return;
  fetch('/mti/clear_design_catalog', { method: 'POST' }).then(() => {
    window.showSetupBanner('Reset design catalog to 139 CAD defaults.', 'alert-secondary');
    window.refreshSetupStatus();
  });
};

document.addEventListener('DOMContentLoaded', window.refreshSetupStatus);
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

@mti_bp.route('/setup')
@login_required
def mti_survey_setup_window():
    return render_template_string(SETUP_HTML_TEMPLATE)
