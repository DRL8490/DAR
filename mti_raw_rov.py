import os, re, json, math
from datetime import datetime
import numpy as np

QUADS_CW = ("NW", "NE", "SE", "SW")

DEFAULT_SEEDED_RAW_ROV_TEXT = """CRA1M15_NW\t194540.8\t2702617\t-54.615
CRA1M15_NE\t194543.7\t2702616\t-54.606
CRA1M15_SW\t194539.1\t2702611\t-54.643
CRA1M15_SE\t194542\t2702610\t-53.246

C1_NW_A1M16\t194543.8\t2702616\t-54.615
C2_SW_A1M16\t194542.1\t2702610\t-54.507
C3_SE_A1M16\t194545\t2702610\t-54.788
C4_NE_A1M16\t194546.6\t2702615\t-54.866

C1_NW_A3M18\t212336.4\t2711930\t-46.883
C2_SW_A3M18\t212332.3\t2711925\t-47.035
C3_SE_A3M18\t212334.4\t2711923\t-47.009
C4_NE_A3M18\t212338.6\t2711928\t-46.866"""

def normalize_box_id(token, known_boxes=None):
    s = str(token or "").upper().strip()
    for kb in (known_boxes or []):
        if kb.upper() == s:
            return kb
    m = re.search(r"(?:CR[-_]?)?([AB][123])(?:[-_]?L[12])?[-_]?M0*(\d+)(?=$|[^0-9])", s)
    if m:
        grp, num = m.group(1), int(m.group(2))
        c1, c2 = f"CR-{grp}_M{num}", f"CR-{grp}_M{num:02d}"
        for kb in (known_boxes or []):
            if kb.upper() in (c1.upper(), c2.upper()):
                return kb
        return c1
    return ""

def extract_quad(token):
    s = str(token or "").upper().strip()
    if s in QUADS_CW:
        return s
    m = re.search(r"(?:^|[-_0-9])(NW|NE|SE|SW)(?:$|[-_0-9])", s)
    return m.group(1) if m else ""

def _resolve_box_bearing(box_id, ledger=None, catalog=None):
    b_up = str(box_id or "").upper()
    for r in (ledger or []):
        if str(r.get("design_box_id") or "").upper() == b_up:
            for k in ("qaqc_brg", "heading_deg", "design_brg"):
                try:
                    v = float(r.get(k) or 0.0)
                    if abs(v) > 1e-6:
                        return v
                except Exception:
                    pass
    for c in (catalog or []):
        if str(c.get("name") or "").upper() == b_up:
            try:
                return float(c.get("bearing") or 195.854)
            except Exception:
                pass
    return 195.854

def assign_corners_cw(pts_list, south_brg_deg=195.854):
    if not pts_list:
        return [], {}
    b = float(south_brg_deg or 195.854) % 360.0
    s_brg = (b + 180.0) % 360.0 if b < 180.0 else b
    az_rad = math.radians((s_brg - 180.0) % 360.0)
    ul = np.array([math.sin(az_rad), math.cos(az_rad)], dtype=float)
    us = np.array([math.cos(az_rad), -math.sin(az_rad)], dtype=float)

    corners, used_idx = {}, set()
    for idx, p in enumerate(pts_list):
        q = str(p.get("quad") or "").upper()
        if q in QUADS_CW:
            corners[q] = dict(p)
            used_idx.add(idx)

    missing = [q for q in QUADS_CW if q not in corners]
    if missing and pts_list:
        xy = np.array([[float(p["e"]), float(p["n"])] for p in pts_list], dtype=float)
        rel = xy - np.mean(xy, axis=0)
        x_loc, y_loc = rel @ us, rel @ ul
        targets = {"NW": (-1.5, 3.0), "NE": (1.5, 3.0), "SE": (1.5, -3.0), "SW": (-1.5, -3.0)}
        for q in missing:
            tx, ty = targets[q]
            best_i, best_d = None, 1e18
            for idx in range(len(pts_list)):
                if idx in used_idx and len(pts_list) >= 4:
                    continue
                d = math.hypot(float(x_loc[idx]) - tx, float(y_loc[idx]) - ty)
                if d < best_d:
                    best_d, best_i = d, idx
            if best_i is not None:
                used_idx.add(best_i)
                if not pts_list[best_i].get("quad"):
                    pts_list[best_i]["quad"] = q
                cp = dict(pts_list[best_i])
                cp["quad"] = q
                corners[q] = cp
    return pts_list, corners

def format_points_as_text(pts_list):
    return "\n".join(
        f"{p.get('pt_id') or p.get('quad') or 'PT'}\t{float(p.get('e',0)):.3f}\t{float(p.get('n',0)):.3f}\t{float(p.get('z',0)):.3f}"
        for p in (pts_list or [])
    )

def parse_and_merge_raw_rov_text(
    raw_text, store_dict, target_box_id="", negate_z=False,
    append_mode=False, ledger=None, catalog=None
):
    known_boxes = [str(c.get("name") or "") for c in (catalog or []) if c.get("name")]
    for r in (ledger or []):
        b = str(r.get("design_box_id") or "").strip()
        if b and b not in known_boxes:
            known_boxes.append(b)

    t_clean = str(target_box_id or "").strip()
    forced_box = normalize_box_id(t_clean, known_boxes) if t_clean not in ("", "__AUTO__") else ""
    grouped, skipped = {}, 0

    for raw_ln in str(raw_text or "").splitlines():
        ln = raw_ln.strip()
        if not ln or ln.startswith("#"):
            continue
        toks = [t for t in re.split(r"[\t,;]+|\s+", ln) if t]
        if len(toks) < 2:
            continue
        nums, lbls = [], []
        for t in toks:
            try:
                nums.append(float(t))
            except Exception:
                lbls.append(t)
        pt_id = "_".join(lbls) if lbls else ""
        if not pt_id and len(nums) >= 4 and abs(nums[0]) < 1000 and abs(nums[1]) > 10000 and abs(nums[2]) > 100000:
            pt_id, nums = f"PT{int(nums[0])}", nums[1:]
        if len(nums) < 2 or (abs(nums[0]) < 1000 and abs(nums[1]) < 1000):
            skipped += 1
            continue
        e_v, n_v = float(nums[0]), float(nums[1])
        z_v = float(nums[2]) * (-1.0 if negate_z else 1.0) if len(nums) >= 3 else 0.0
        box_use = forced_box or normalize_box_id(pt_id, known_boxes)
        if not box_use:
            skipped += 1
            continue
        quad = extract_quad(pt_id)
        if not pt_id:
            pt_id = f"{box_use}_PT{len(grouped.get(box_use, [])) + 1}"
        grouped.setdefault(box_use, []).append({
            "pt_id": pt_id, "quad": quad, "e": round(e_v, 3), "n": round(n_v, 3), "z": round(z_v, 3)
        })

    updated_boxes = []
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    out_store = dict(store_dict or {})
    for b_id, new_pts in grouped.items():
        prev_pts = list(out_store.get(b_id, {}).get("points") or []) if append_mode else []
        final_pts, corners_map = assign_corners_cw(prev_pts + new_pts, _resolve_box_bearing(b_id, ledger, catalog))
        zs = [float(p["z"]) for p in final_pts if p.get("z") is not None]
        out_store[b_id] = {
            "box_id": b_id,
            "points": final_pts,
            "corners": corners_map,
            "count": len(final_pts),
            "z_min": round(min(zs), 3) if zs else 0.0,
            "z_max": round(max(zs), 3) if zs else 0.0,
            "raw_text": format_points_as_text(final_pts),
            "updated_at": now_str
        }
        updated_boxes.append(b_id)
    return out_store, updated_boxes, skipped

def load_raw_rov_store(st_data=None, workspace_dir="workspace", save_state_fn=None, ledger=None, catalog=None):
    os.makedirs(workspace_dir, exist_ok=True)
    json_p = os.path.join(workspace_dir, "raw_rov_points.json")
    store = {}
    if isinstance(st_data, dict):
        s1 = st_data.get("raw_rov_points")
        s2 = (st_data.get("survey_setup") or {}).get("raw_rov_points")
        store = dict(s1) if isinstance(s1, dict) and s1 else (dict(s2) if isinstance(s2, dict) and s2 else {})
    if not store and os.path.exists(json_p):
        try:
            loaded = json.load(open(json_p, "r", encoding="utf-8"))
            if isinstance(loaded, dict):
                store = loaded
        except Exception:
            pass
    seeded = isinstance(st_data, dict) and bool(st_data.get("raw_rov_seeded"))
    if not store and not seeded and not os.path.exists(json_p):
        store, _, _ = parse_and_merge_raw_rov_text(
            DEFAULT_SEEDED_RAW_ROV_TEXT, {}, "", False, False, ledger, catalog
        )
        save_raw_rov_store(store, st_data, save_state_fn, workspace_dir)
    return store

def save_raw_rov_store(store, st_data=None, save_state_fn=None, workspace_dir="workspace"):
    os.makedirs(workspace_dir, exist_ok=True)
    open(os.path.join(workspace_dir, "raw_rov_points.json"), "w", encoding="utf-8").write(json.dumps(store or {}, indent=2))
    if isinstance(st_data, dict):
        st_data["raw_rov_points"] = store or {}
        st_data["raw_rov_seeded"] = True
        st_data.setdefault("survey_setup", {})["raw_rov_points"] = store or {}
        if callable(save_state_fn):
            save_state_fn(st_data)

def get_raw_rov_corners_tuple(store, box_id):
    b_up = str(box_id or "").strip().upper()
    entry = next((v for k, v in (store or {}).items() if str(k).upper() == b_up), None)
    c_map = (entry or {}).get("corners") or {}
    if all(q in c_map for q in QUADS_CW):
        xy = np.array([[float(c_map[q]["e"]), float(c_map[q]["n"])] for q in QUADS_CW], dtype=float)
        ids = [str(c_map[q].get("pt_id") or f"{b_up}_{q}") for q in QUADS_CW]
        zs = [float(c_map[q].get("z") or 0.0) for q in QUADS_CW]
        return xy, ids, zs
    return None, None, None