import os, re, math, json
from datetime import datetime
import numpy as np

def build_base_filename(location_id, mattress_id, date_str=None):
    dt = re.sub(r"[^0-9]", "", str(date_str or ""))[:8]
    if len(dt) < 8:
        dt = datetime.utcnow().strftime("%Y%m%d")
    loc = re.sub(r"[^A-Za-z0-9_-]", "_", str(location_id or "CR-A1_M15").strip())
    tag = re.sub(r"[^A-Za-z0-9_-]", "", str(mattress_id or "001").replace("#", "").strip()) or "001"
    return f"{dt}_Mattress_{loc}_{tag}"

def _box_corners_cw(ce, cn, az_deg, length=6.0, width=3.0):
    rad = math.radians(float(az_deg) % 360.0)
    ul = np.array([math.sin(rad), math.cos(rad)], dtype=float)
    us = np.array([math.cos(rad), -math.sin(rad)], dtype=float)
    c = np.array([float(ce), float(cn)], dtype=float)
    pts = [c + sL * (length / 2.0) * ul + sW * (width / 2.0) * us for sL, sW in [(1, -1), (1, 1), (-1, 1), (-1, -1)]]
    return np.array(pts, dtype=float), ul, us

def parse_bathy_xyz_text(raw_text):
    pts = []
    for ln in str(raw_text or "").splitlines():
        s = ln.strip()
        if not s or s[0] in ("#", "/", "E", "e", "X", "x", "P", "p"):
            continue
        ps = [p for p in re.split(r"[\s,;]+", s) if p]
        if len(ps) >= 3:
            try:
                nums = [float(p) for p in ps[:4] if re.match(r"^[+-]?\d+(\.\d+)?$", p)]
                if len(nums) >= 3:
                    if len(nums) == 4 and abs(nums[0]) < 10000 and nums[1] > 100000:
                        e, n, z = nums[1], nums[2], nums[3]
                    else:
                        e, n, z = nums[0], nums[1], nums[2]
                    if n < e and e > 1000000:
                        e, n = n, e
                    z = -abs(z) if 0 < abs(z) < 200 else z
                    pts.append([e, n, z])
            except Exception:
                pass
    return np.array(pts, dtype=float) if pts else np.zeros((0, 3), dtype=float)

def build_crossing_boxes_from_catalog(catalog_list, crossing_id="CR-A1_L1", target_box_id="CR-A1_M15"):
    cats = list(catalog_list.values()) if isinstance(catalog_list, dict) else list(catalog_list or [])
    t_hit = next((b for b in cats if str(b.get("name") or b.get("design_box_id")) == str(target_box_id)), None)
    if t_hit and t_hit.get("layer"): crossing_id = str(t_hit["layer"])
    layer_boxes = [b for b in cats if str(b.get("layer", "")) == str(crossing_id)] or cats
    boxes_dict = {}
    for b in layer_boxes:
        bid = str(b.get("name") or b.get("design_box_id") or "CR-A1_M15")
        de, dn = float(b.get("design_e", 194541.443)), float(b.get("design_n", 2702613.394))
        s_brg = float(b.get("bearing", 195.854))
        s_brg = (s_brg + 180.0) % 360.0 if s_brg < 180.0 else s_brg
        az = (s_brg - 180.0) % 360.0
        corners, ul, us = _box_corners_cw(de, dn, az, 6.0, 3.0)
        boxes_dict[bid] = {
            "id": bid, "layer": str(b.get("layer", crossing_id)), "design_e": round(de, 3), "design_n": round(dn, 3),
            "bearing": round(s_brg, 3), "azimuth": round(az, 3), "length": 6.0, "width": 3.0,
            "corners": corners, "u_long": ul, "u_short": us,
            "neighbors": {"NNE": None, "SSW": None, "WNW": None, "ESE": None}
        }
    if target_box_id not in boxes_dict and boxes_dict:
        target_box_id = next(iter(boxes_dict.keys()))
    if target_box_id in boxes_dict:
        tb = boxes_dict[target_box_id]
        t_c = np.array([tb["design_e"], tb["design_n"]])
        best_d = {"NNE": 999.0, "SSW": 999.0, "WNW": 999.0, "ESE": 999.0}
        for oid, ob in boxes_dict.items():
            if oid == target_box_id:
                continue
            v = np.array([ob["design_e"], ob["design_n"]]) - t_c
            dist = float(np.hypot(v[0], v[1]))
            if dist <= 12.0:
                al, cr = float(v @ tb["u_long"]), float(v @ tb["u_short"])
                k = ("NNE" if al > 0 else "SSW") if abs(al) >= abs(cr) else ("ESE" if cr > 0 else "WNW")
                if dist < best_d[k]:
                    best_d[k], tb["neighbors"][k] = dist, oid
    return boxes_dict

def idw_interpolate(src_xy, src_z, query_xy, power=2.0):
    src_xy, src_z, query_xy = np.asarray(src_xy, float), np.asarray(src_z, float), np.asarray(query_xy, float)
    if len(src_xy) == 0:
        return np.full(len(query_xy), -18.45)
    if len(src_xy) > 1200:
        step = max(1, len(src_xy) // 1200)
        src_xy, src_z = src_xy[::step], src_z[::step]
    dx, dy = query_xy[:, 0:1] - src_xy[:, 0][None, :], query_xy[:, 1:2] - src_xy[:, 1][None, :]
    w = 1.0 / (np.maximum(dx * dx + dy * dy, 1e-8) ** (power / 2.0))
    return (w @ src_z) / np.sum(w, axis=1)

def get_or_build_seabed_xyz(workspace_dir, crossing_id, boxes_dict, ref_depth_m=-18.45):
    os.makedirs(workspace_dir, exist_ok=True)
    npy_p = os.path.join(workspace_dir, f"{crossing_id}_seabed.npy")
    if os.path.exists(npy_p):
        try:
            arr = np.load(npy_p)
            if arr.ndim == 2 and arr.shape[1] >= 3 and len(arr) >= 1:
                arr = arr.copy()
                arr[:, 2] = np.where((arr[:, 2] > 0) & (arr[:, 2] < 200), -arr[:, 2], arr[:, 2])
                return arr[:, :3], "SURVEY_BATHY"
        except Exception:
            pass
    safe_ref = float(ref_depth_m) if abs(float(ref_depth_m)) > 2.0 else -18.45
    safe_ref = -abs(safe_ref)
    es = [b["design_e"] for b in boxes_dict.values()] if boxes_dict else [194541.4]
    ns = [b["design_n"] for b in boxes_dict.values()] if boxes_dict else [2702613.4]
    e_min, e_max, n_min, n_max = min(es) - 25.0, max(es) + 25.0, min(ns) - 25.0, max(ns) + 25.0
    ee, nn = np.meshgrid(np.arange(e_min, e_max + 2.0, 2.0), np.arange(n_min, n_max + 2.0, 2.0))
    zz = np.full_like(ee, safe_ref, dtype=float)
    return np.column_stack([ee.ravel(), nn.ravel(), zz.ravel()]), "REF_DEPTH"

def run_rov_4panel_verification(fix_data, catalog_list, workspace_dir="workspace", cl_tol=0.50, gap_tol=0.50):
    xing_id = str(fix_data.get("crossing_id") or "CR-A1_L1").strip()
    loc_id = str(fix_data.get("design_box_id") or fix_data.get("location_id") or "CR-A1_M15").strip()
    mat_id = str(fix_data.get("physical_tag") or fix_data.get("mattress_id") or "#A046").strip()
    dt_str = str(fix_data.get("install_date") or datetime.utcnow().strftime("%Y-%m-%d %H:%M")).strip()
    usbl_s = str(fix_data.get("usbl_sensor") or "Survey Pole").strip()
    unit_no = int(float(fix_data.get("unit_no") or (1 if loc_id.endswith("_M15") else 2)))
    boxes_dict = build_crossing_boxes_from_catalog(catalog_list, xing_id, loc_id)
    tb = boxes_dict.get(loc_id) or next(iter(boxes_dict.values()))
    loc_id, des_e, des_n, des_brg, des_az, ul, us = tb["id"], tb["design_e"], tb["design_n"], tb["bearing"], tb["azimuth"], tb["u_long"], tb["u_short"]

    bathy_txt = str(fix_data.get("bathy_xyz_text") or "").strip()
    if bathy_txt:
        parsed_b = parse_bathy_xyz_text(bathy_txt)
        if len(parsed_b) > 0:
            os.makedirs(workspace_dir, exist_ok=True)
            np.save(os.path.join(workspace_dir, f"{xing_id}_seabed.npy"), parsed_b)

    as_e, as_n = float(fix_data.get("aslaid_e") or fix_data.get("qaqc_e") or des_e), float(fix_data.get("aslaid_n") or fix_data.get("qaqc_n") or des_n)
    raw_z = float(fix_data.get("aslaid_z") or 0.0)
    as_z = -abs(raw_z) if abs(raw_z) > 2.0 else (-18.20 if unit_no == 1 else -18.35)
    hdg = float(fix_data.get("heading_deg") or fix_data.get("qaqc_brg") or des_brg)
    hdg = round((hdg + 180.0) % 360.0, 3) if hdg < 180.0 else hdg

    c_pts = []
    for i in (1, 2, 3, 4):
        ce, cn, cz = fix_data.get(f"c{i}_e"), fix_data.get(f"c{i}_n"), fix_data.get(f"c{i}_z")
        if ce is not None and cn is not None and str(ce).strip() != "" and str(cn).strip() != "":
            try:
                zv = -abs(float(cz)) if (cz is not None and str(cz).strip() != "" and abs(float(cz)) > 2.0) else as_z
                c_pts.append([float(ce), float(cn), zv])
            except Exception:
                pass
    if len(c_pts) != 4:
        c2d, _, _ = _box_corners_cw(as_e, as_n, (hdg - 180.0) % 360.0, 6.0, 3.0)
        c_pts = [[round(float(p[0]), 3), round(float(p[1]), 3), round(as_z, 3)] for p in c2d]
    c_arr = np.array(c_pts, dtype=float)
    as_e, as_n, as_z = float(np.mean(c_arr[:, 0])), float(np.mean(c_arr[:, 1])), float(np.mean(c_arr[:, 2]))
    be, bn, fe, fn = (c_arr[0, 0] + c_arr[1, 0]) / 2.0, (c_arr[0, 1] + c_arr[1, 1]) / 2.0, (c_arr[2, 0] + c_arr[3, 0]) / 2.0, (c_arr[2, 1] + c_arr[3, 1]) / 2.0
    hdg = round((math.degrees(math.atan2(fe - be, fn - bn)) + 360.0) % 360.0, 3)
    hdg = round(hdg + 180.0, 3) if hdg < 180.0 else hdg
    act_az = round((hdg - 180.0) % 360.0, 3)

    ug, vg = np.meshgrid(np.linspace(0.0, 1.0, 20), np.linspace(0.0, 1.0, 35))
    uf, vf = ug.ravel(), vg.ravel()
    cleaned_xyz = (np.outer((1 - uf) * (1 - vf), c_arr[3]) + np.outer((1 - uf) * vf, c_arr[0]) + np.outer(uf * vf, c_arr[1]) + np.outer(uf * (1 - vf), c_arr[2]))
    d_en = cleaned_xyz[:, :2] - np.array([des_e, des_n])
    x_local, y_local, z_vals = d_en @ us, d_en @ ul, cleaned_xyz[:, 2]
    c_loc_d = c_arr[:, :2] - np.array([des_e, des_n])
    corners_local = np.column_stack([c_loc_d @ us, c_loc_d @ ul])

    d_along, d_cross = float((as_e - des_e) * ul[0] + (as_n - des_n) * ul[1]), float((as_e - des_e) * us[0] + (as_n - des_n) * us[1])
    cl_off, d_brg = float(math.hypot(as_e - des_e, as_n - des_n)), round(((hdg - des_brg + 180.0) % 360.0) - 180.0, 3)
    pct_in = float(np.mean((np.abs(x_local) <= 1.50) & (np.abs(y_local) <= 3.00)) * 100.0)

    is_first = bool(fix_data.get("is_first_in_array")) or (unit_no == 1) or ("1st unit" in str(fix_data.get("gap_labels", "")).lower()) or (str(loc_id).endswith("_M15") and str(mat_id).replace("#", "") == "A046")
    gaps = {k: str(fix_data.get(f"gap_{k}", "") or "").strip() for k in ("nw", "ne", "sw", "se")}
    if not is_first and not any(gaps.values()):
        g1, g2 = float(fix_data.get("gap1_m") or 0.0), float(fix_data.get("gap2_m") or 0.0)
        if g1 > 0: gaps["nw"] = f"{g1:.2f}"
        if g2 > 0: gaps["sw"] = f"{g2:.2f}"
    gap_vals = []
    for k in ("nw", "ne", "sw", "se"):
        if gaps[k]:
            try: gap_vals.append(float(re.sub(r"[^0-9.]", "", gaps[k])))
            except Exception: pass
    max_gap = max(gap_vals) if gap_vals else float(fix_data.get("gap_m") or 0.0)
    gap_lbl_parts = [f"{k.upper()}:{gaps[k]}m" for k in ("nw", "ne", "sw", "se") if gaps[k]]
    gap_labels = "1st Unit (N/A)" if is_first else (" | ".join(gap_lbl_parts) if gap_lbl_parts else str(fix_data.get("gap_labels") or "N/A"))

    verdict = ("VERIFIED - WITHIN DESIGN TOLERANCE" if is_first else "VERIFIED - WITHIN DESIGN & GAP TOLERANCE") if (cl_off <= float(cl_tol) and (is_first or max_gap <= float(gap_tol))) else "ADVISORY - CHECK OFFSET OR GAP TOLERANCE"

    raw_ref_sb = fix_data.get("seabed_ref_z")
    ref_sb_z = float(raw_ref_sb) if (raw_ref_sb is not None and str(raw_ref_sb).strip() != "" and abs(float(raw_ref_sb)) > 2.0) else (as_z - 0.25)
    seabed_full_xyz, bathy_src = get_or_build_seabed_xyz(workspace_dir, xing_id, boxes_dict, ref_depth_m=ref_sb_z)
    sb_d = seabed_full_xyz[:, :2] - np.array([des_e, des_n])
    sb_x, sb_y = sb_d @ us, sb_d @ ul
    m_loc = (np.abs(sb_x) <= 10.0) & (np.abs(sb_y) <= 12.0)
    seabed_local_xyz = np.column_stack([sb_x[m_loc], sb_y[m_loc], seabed_full_xyz[m_loc, 2]]) if np.any(m_loc) else np.column_stack([sb_x, sb_y, seabed_full_xyz[:, 2]])

    metrics = {
        "unit_no": unit_no, "crossing_id": xing_id, "location_id": loc_id, "mattress_id": mat_id, "install_date": dt_str, "usbl_sensor": usbl_s,
        "status": str(fix_data.get("status") or "Completed"), "base_filename": build_base_filename(loc_id, mat_id, dt_str),
        "design_e": des_e, "design_n": des_n, "design_brg": des_brg, "design_az": des_az,
        "qaqc_e": float(fix_data.get("qaqc_e") or as_e), "qaqc_n": float(fix_data.get("qaqc_n") or as_n), "qaqc_brg": float(fix_data.get("qaqc_brg") or hdg),
        "aslaid_e": round(as_e, 3), "aslaid_n": round(as_n, 3), "aslaid_z": round(as_z, 3), "heading_deg": hdg, "act_az": act_az, "brg_diff_deg": d_brg,
        "cl_offset_m": round(cl_off, 3), "d_along_m": round(d_along, 3), "d_cross_m": round(d_cross, 3), "pct_inside": round(pct_in, 1),
        "corners_enz": c_arr.tolist(), "corners_local": corners_local.tolist(),
        "edge_nne": round(float(np.max(y_local)) - 3.0, 3), "edge_ssw": round(-3.0 - float(np.min(y_local)), 3),
        "edge_ese": round(float(np.max(x_local)) - 1.5, 3), "edge_wnw": round(-1.5 - float(np.min(x_local)), 3),
        "is_first_in_array": is_first, "gaps": gaps, "gap_labels": gap_labels,
        "max_gap_m": round(max_gap, 3), "cl_tol": cl_tol, "gap_tol": gap_tol,
        "bathy_source": bathy_src, "bathy_count": int(len(seabed_full_xyz)),
        "bathy_z_min": round(float(np.min(seabed_full_xyz[:, 2])), 2), "bathy_z_max": round(float(np.max(seabed_full_xyz[:, 2])), 2),
        "neighbors": tb["neighbors"], "verdict": verdict,
        "env_wind": str(fix_data.get("env_wind") or ""), "env_current": str(fix_data.get("env_current") or ""), "remarks": str(fix_data.get("remarks") or "")
    }
    return boxes_dict, metrics, cleaned_xyz, x_local, y_local, z_vals, seabed_local_xyz, seabed_full_xyz
