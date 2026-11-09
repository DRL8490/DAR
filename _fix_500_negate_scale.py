import os, re, glob, json, ast, subprocess
import numpy as np

print("=== [1/4] Fixing /mti/studio 500 Error & Adding Negate-Z (Z*-1) Checkbox in mti_blueprint.py ===")
if os.path.exists("mti_blueprint.py"):
    b_txt = open("mti_blueprint.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")

    # 1. Fix _resolve_fix_data indentation bug where req_surv was indented inside `if box_q:` causing UnboundLocalError 500
    clean_resolve = """def _resolve_fix_data(req, ledger):
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
    req_surv = str(req.get("surveyor_name") or "").strip()
    saved_surv = str(fix_data.get("surveyor_name") or fix_data.get("surveyor") or "").strip()
    cur_u = _get_current_user_display_name()
    if req_surv and req_surv.lower() != "duty surveyor":
        fix_data["surveyor_name"] = req_surv
    elif saved_surv and saved_surv.lower() != "duty surveyor":
        fix_data["surveyor_name"] = saved_surv
    else:
        fix_data["surveyor_name"] = cur_u
    return fix_data
"""
    b_txt = re.sub(
        r"def _resolve_fix_data\(req,\s*ledger\):.*?(?=\n@mti_bp\.route)",
        clean_resolve.strip() + "\n",
        b_txt,
        count=1,
        flags=re.S
    )

    # 2. Update /mti/upload_seabed to multiply Z by -1 ONLY when negate_z checkbox is checked
    old_upload_block = re.search(r"@mti_bp\.route\('/upload_seabed'.*?(?=\n@mti_bp\.route)", b_txt, flags=re.S)
    new_upload_route = """@mti_bp.route('/upload_seabed', methods=['POST'])
@login_required
def upload_seabed():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req_json = request.get_json(silent=True) or {}
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(request.form.get("crossing_id") or req_json.get("crossing_id") or "CR-A1_L1").strip())
    fname = str(request.form.get("filename") or req_json.get("filename") or "").strip()
    neg_flag = _as_bool(req_json.get("negate_z") if "negate_z" in req_json else request.form.get("negate_z"), False)
    pts_json = req_json.get("points_array")
    if pts_json and isinstance(pts_json, list) and len(pts_json) > 0:
        pts_arr = np.array(pts_json, dtype=float)[:, :3]
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
        if neg_flag:
            pts_arr[:, 2] = pts_arr[:, 2] * -1.0
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
            "negate_z": bool(neg_flag),
            "pts_compact": np.round(pts_arr[::max(1, len(pts_arr) // 800)], 2).tolist()
        }
        _save_setup_meta(meta)
        _purge_cached_pdfs()
        return jsonify({"status": "ok", "crossing_id": xing_id, "filename": fname or f"{xing_id}_bathy.xyz", "points": int(len(pts_arr)), "z_min": z_min, "z_max": z_max, "negate_z": bool(neg_flag)})
    return jsonify({"status": "error", "message": "No valid E N Z bathy points found in file."}), 400
"""
    if old_upload_block:
        b_txt = b_txt[:old_upload_block.start()] + new_upload_route.strip() + "\n" + b_txt[old_upload_block.end():]

    # 3. Add /mti/negate_bathy_z route to multiply loaded file Z by -1 when checkbox is toggled
    negate_route = """
@mti_bp.route('/negate_bathy_z', methods=['POST'])
@login_required
def negate_bathy_z():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req = request.get_json(silent=True) or request.form.to_dict()
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(req.get("crossing_id") or "CR-A1_L1").strip())
    neg_flag = _as_bool(req.get("negate_z"), False)
    meta = _load_setup_meta()
    b_info = meta.setdefault("bathy", {}).get(xing_id) or {}
    npy_p = os.path.join(MTI_WS_DIR, f"{xing_id}_seabed.npy")
    if not os.path.exists(npy_p):
        return jsonify({"status": "error", "message": f"No bathy file loaded for {xing_id}."}), 400
    arr = np.load(npy_p).astype(float)
    arr[:, 2] = arr[:, 2] * -1.0
    np.save(npy_p, arr)
    if xing_id == "CR-A1_L1" and os.path.exists(os.path.join(MTI_WS_DIR, "CR-A1_L2_seabed.npy")):
        np.save(os.path.join(MTI_WS_DIR, "CR-A1_L2_seabed.npy"), arr)
    z_min, z_max = round(float(np.min(arr[:, 2])), 2), round(float(np.max(arr[:, 2])), 2)
    b_info["z_min"] = z_min
    b_info["z_max"] = z_max
    b_info["negate_z"] = bool(neg_flag)
    b_info["pts_compact"] = np.round(arr[::max(1, len(arr) // 800)], 2).tolist()
    meta["bathy"][xing_id] = b_info
    _save_setup_meta(meta)
    _purge_cached_pdfs()
    return jsonify({"status": "ok", "crossing_id": xing_id, "negate_z": bool(neg_flag), "z_min": z_min, "z_max": z_max, "points": int(len(arr))})
"""
    if "def negate_bathy_z():" not in b_txt:
        b_txt = b_txt.replace("@mti_bp.route('/clear_seabed'", negate_route.lstrip() + "\n@mti_bp.route('/clear_seabed'", 1)

    if '"negate_z": bool(b_info.get("negate_z", False)),' not in b_txt:
        b_txt = b_txt.replace(
            '"bathy_points": int(b_pts),',
            '"bathy_points": int(b_pts),\n            "negate_z": bool(b_info.get("negate_z", False)),'
        )

    # 4. Update SETUP_HTML_TEMPLATE in mti_blueprint.py:
    b_txt = b_txt.replace("if (z > 0 && z < 500) z = -Math.abs(z);", "// Preserve raw Z sign from file; server applies negate_z if checked")

    old_bathy_row_js = """      return (
        '<tr id="bathyRow_' + row.location + '">' +
        '<td class="fw-bold text-warning font-monospace">' + row.location + '</td>' +
        '<td id="bathyCell_' + row.location + '">' + fileCell + '</td>' +
        '<td class="text-end text-nowrap">' +
          '<button type="button" class="btn btn-xs btn-sm btn-success fw-bold py-0 px-2 me-1" onclick="window.triggerRowBathyPicker(\\'' + row.location + '\\')"><i class="fas fa-upload me-1"></i>Upload</button>' +
          (row.bathy_loaded ? ('<button type="button" class="btn btn-xs btn-sm btn-outline-danger py-0 px-2" onclick="window.clearBathySetup(\\'' + row.location + '\\')" title="Remove Bathy file"><i class="fas fa-trash"></i></button>') : '') +
        '</td></tr>'
      );"""
    new_bathy_row_js = """      const negChecked = row.negate_z ? 'checked' : '';
      const negBoxHtml = '<div class="form-check d-inline-block me-2 align-middle" title="If checked, Z value of the loaded file is multiplied by -1">' +
        '<input class="form-check-input border-warning" type="checkbox" id="negZ_' + row.location + '" ' + negChecked + ' onchange="window.toggleRowNegateZ(\\'' + row.location + '\\', this.checked)">' +
        '<label class="form-check-label small text-warning fw-bold" for="negZ_' + row.location + '">Negate Z (&times;-1)</label></div>';
      return (
        '<tr id="bathyRow_' + row.location + '">' +
        '<td class="fw-bold text-warning font-monospace">' + row.location + '</td>' +
        '<td id="bathyCell_' + row.location + '">' + fileCell + '</td>' +
        '<td class="text-end text-nowrap">' +
          negBoxHtml +
          '<button type="button" class="btn btn-xs btn-sm btn-success fw-bold py-0 px-2 me-1" onclick="window.triggerRowBathyPicker(\\'' + row.location + '\\')"><i class="fas fa-upload me-1"></i>Upload</button>' +
          (row.bathy_loaded ? ('<button type="button" class="btn btn-xs btn-sm btn-outline-danger py-0 px-2" onclick="window.clearBathySetup(\\'' + row.location + '\\')" title="Remove Bathy file"><i class="fas fa-trash"></i></button>') : '') +
        '</td></tr>'
      );"""
    if "window.toggleRowNegateZ" not in b_txt and old_bathy_row_js in b_txt:
        b_txt = b_txt.replace(old_bathy_row_js, new_bathy_row_js, 1)

    neg_js_fn = """window.toggleRowNegateZ = function(loc, isChecked) {
  const cell = document.getElementById('bathyCell_' + loc);
  if (!cell || cell.innerText.indexOf('No Bathy file') !== -1) return;
  fetch('/mti/negate_bathy_z', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ crossing_id: loc, negate_z: isChecked })
  }).then(r => r.json()).then(d => {
    if (d.status === 'ok') {
      window.showSetupBanner('&#10004; Negate Z (' + (isChecked ? 'ON' : 'OFF') + '): Multiplied Z by -1 for <strong>' + loc + '</strong> (New Z: ' + d.z_min + 'm to ' + d.z_max + 'm)', 'alert-info');
      window.refreshSetupStatus();
    }
  });
};
"""
    if "window.toggleRowNegateZ =" not in b_txt:
        b_txt = b_txt.replace("window.triggerRowBathyPicker =", neg_js_fn + "\nwindow.triggerRowBathyPicker =", 1)

    b_txt = b_txt.replace(
        "crossing_id: loc,\n        filename: f.name,\n        points_array: parsed.points",
        "crossing_id: loc,\n        filename: f.name,\n        negate_z: !!(document.getElementById('negZ_' + loc) && document.getElementById('negZ_' + loc).checked),\n        points_array: parsed.points"
    )

    ast.parse(b_txt)
    open("mti_blueprint.py", "w", encoding="utf-8").write(b_txt)
    print("  -> mti_blueprint.py updated & AST-verified.")

print("=== [2/4] Updating mti_4panel_math.py (Respect Signed Z from Loaded File) ===")
if os.path.exists("mti_4panel_math.py"):
    m_txt = open("mti_4panel_math.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    m_txt = m_txt.replace("z = -abs(z) if 0 < abs(z) < 500 else z", "z = float(z)")
    m_txt = m_txt.replace("arr[:, 2] = np.where((arr[:, 2] > 0) & (arr[:, 2] < 500), -arr[:, 2], arr[:, 2])", "# Respect exact Z sign stored in .npy file")
    if "thick_signed" not in m_txt:
        m_txt = m_txt.replace(
            "mat_thick = 0.30",
            "mat_thick = 0.30\n    thick_signed = mat_thick if seabed_at_center <= 0 else -mat_thick"
        ).replace(
            "else 0.30)",
            "else 0.30)\n        thick_signed = mat_thick if seabed_at_center <= 0 else -mat_thick"
        ).replace(
            "+ mat_thick",
            "+ thick_signed"
        )
    ast.parse(m_txt)
    open("mti_4panel_math.py", "w", encoding="utf-8").write(m_txt)
    print("  -> mti_4panel_math.py updated & AST-verified.")

print("=== [3/4] Updating mti_4panel_a3.py & mti_4panel_reports.py (P3 & P4 Same H 1:75 | V 1:15 Scale & Signed Z) ===")
if os.path.exists("mti_4panel_a3.py"):
    a3_txt = open("mti_4panel_a3.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    a3_txt = a3_txt.replace("fmt.format(abs(float(pz)))", "fmt.format(float(pz))")
    old_p3_p4_loop = re.search(r"sb_loc_arr = np\.asarray\(seabed_local_xyz, dtype=float\).*?(?=\n    buf_png = io\.BytesIO\(\))", a3_txt, flags=re.S)
    new_p3_p4_loop = """sb_loc_arr = np.asarray(seabed_local_xyz, dtype=float)
    for ax_p, coord_arr, lim_x, edge_v, is_long, ttl, x_lbl in [
        (fig.add_axes([315.0 / W_MM, 162.0 / H_MM, 83.0 / W_MM, 88.0 / H_MM]), y_local, (-3.5, 3.5), 3.0, True, "PANEL 3: LONGITUDINAL (SSW -> NNE)" + chr(10) + "H 1:75 | V 1:15 @ A3", "Along-Track Y_local (m)"),
        (fig.add_axes([315.0 / W_MM, 46.0 / H_MM, 83.0 / W_MM, 88.0 / H_MM]), x_local, (-3.5, 3.5), 1.5, False, "PANEL 4: LATERAL (WNW -> ESE)" + chr(10) + "H 1:75 | V 1:15 @ A3", "Cross-Track X_local (m)")
    ]:
        ax_p.scatter(coord_arr, z_vals, c=z_vals, cmap="turbo", vmin=vmin_c, vmax=vmax_c, s=10, alpha=0.85, label="Mattress Surface")
        xs_l = np.linspace(lim_x[0], lim_x[1], 40)
        if bathy_src == "SURVEY_BATHY" and len(sb_loc_arr) >= 1:
            q_prof = np.column_stack([np.zeros_like(xs_l), xs_l]) if is_long else np.column_stack([xs_l, np.zeros_like(xs_l)])
            z_prof = idw_interpolate(sb_loc_arr[:, :2], sb_loc_arr[:, 2], q_prof)
            ax_p.plot(xs_l, z_prof, "--", color="#0284c7", lw=1.35, label="Survey Seabed Profile")
            z_center = 0.5 * (float(np.mean(z_vals)) + float(np.mean(z_prof)))
            half_win = max(0.66, 0.5 * abs(float(np.max(z_prof) - np.min(z_vals))) + 0.35)
        else:
            z_center = z_mean
            half_win = 0.66
        if z_center <= 0:
            y_bottom, y_top = z_center - half_win, z_center + half_win
        else:
            y_bottom, y_top = z_center + half_win, z_center - half_win
        ax_p.axvline(-edge_v, color="#dc2626", ls="--", lw=1.2, label=f"Design (+/-{edge_v:.1f}m)"); ax_p.axvline(edge_v, color="#dc2626", ls="--", lw=1.2)
        ax_p.set_xlim(*lim_x); ax_p.set_ylim(y_bottom, y_top)
        ax_p.set_title(ttl, fontsize=7.0, fontweight="bold", pad=3); ax_p.set_xlabel(x_lbl, fontsize=6.3, fontweight="bold"); ax_p.set_ylabel("Depth Z (m, TWVD2001)", fontsize=6.3, fontweight="bold")
        ax_p.tick_params(labelsize=5.6); ax_p.grid(True, linestyle=":", lw=0.45, color="#cbd5e1"); ax_p.legend(loc="lower right", fontsize=5.0, framealpha=0.9)"""
    if old_p3_p4_loop:
        a3_txt = a3_txt[:old_p3_p4_loop.start()] + new_p3_p4_loop + "\n" + a3_txt[old_p3_p4_loop.end():]
    a3_txt = a3_txt.replace("P3 1:75/1:15 | P4 1:50/1:15", "P3 & P4 1:75/1:15")
    ast.parse(a3_txt)
    open("mti_4panel_a3.py", "w", encoding="utf-8").write(a3_txt)
    print("  -> mti_4panel_a3.py updated (P3 & P4 both H 1:75 | V 1:15 @ A3) & AST-verified.")

if os.path.exists("mti_4panel_reports.py"):
    r_txt = open("mti_4panel_reports.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    r_txt = r_txt.replace("Panel 3 (1:75/1:15) | Panel 4 (1:50/1:15)", "Panel 3 (1:75/1:15) | Panel 4 (1:75/1:15)")
    ast.parse(r_txt)
    open("mti_4panel_reports.py", "w", encoding="utf-8").write(r_txt)
    print("  -> mti_4panel_reports.py updated & AST-verified.")

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try: os.remove(p)
    except Exception: pass

print("=== [4/4] Syncing to GitHub & Render ===")
sync_py = "python" if os.path.exists(".venv/Scripts/python.exe") else "py"
subprocess.run([sync_py, "sync.py", "fix(mti): fix /mti/studio 500 error, add Negate Z (Z*-1) checkbox per bathy file, and set P3 & P4 to H 1:75 | V 1:15"], check=False)
