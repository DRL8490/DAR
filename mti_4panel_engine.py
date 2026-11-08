import os, io, re, math, json, zipfile
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as patheffects

def compass_16(az_deg):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[int(round((az_deg % 360.0) / 22.5)) % 16]

def clean_tag_for_filename(tag):
    s = re.sub(r"[^A-Za-z0-9_-]", "", str(tag or "001").strip())
    return s if s else "001"

def build_base_filename(date_str, location_id, mattress_id):
    dt_digits = re.sub(r"[^0-9]", "", str(date_str or ""))[:8]
    if len(dt_digits) < 8:
        dt_digits = datetime.utcnow().strftime("%Y%m%d")
    loc_clean = re.sub(r"[^A-Za-z0-9_-]", "_", str(location_id or "CR-A1_M15").strip())
    mat_clean = clean_tag_for_filename(mattress_id)
    return f"{dt_digits}_Mattress_{loc_clean}_{mat_clean}"

def pure_numpy_mrr(pts_2d):
    pts = np.asarray(pts_2d, dtype=float)
    if len(pts) < 3:
        return pts
    pts_u = np.unique(np.round(pts, 6), axis=0)
    if len(pts_u) < 3:
        return pts
    pts_s = pts_u[np.lexsort((pts_u[:, 1], pts_u[:, 0]))]
    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for p in pts_s:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts_s):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = np.array(lower[:-1] + upper[:-1], dtype=float)
    if len(hull) < 3:
        return pts
    edges = np.roll(hull, -1, axis=0) - hull
    angles = np.unique(np.mod(np.arctan2(edges[:, 1], edges[:, 0]), np.pi / 2.0))
    min_area = float("inf")
    best_rect = None
    for theta in angles:
        c, s = np.cos(theta), np.sin(theta)
        R = np.array([[c, s], [-s, c]])
        rot = hull @ R.T
        min_x, max_x = np.min(rot[:, 0]), np.max(rot[:, 0])
        min_y, max_y = np.min(rot[:, 1]), np.max(rot[:, 1])
        area = (max_x - min_x) * (max_y - min_y)
        if area < min_area:
            min_area = area
            rect_rot = np.array([[min_x, min_y], [max_x, min_y], [max_x, max_y], [min_x, max_y]])
            best_rect = rect_rot @ R
    return best_rect

def interpolate_4corners_grid(corners_enz, nx=35, ny=20):
    pts = np.array(corners_enz, dtype=float)
    ce, cn = np.mean(pts[:, 0]), np.mean(pts[:, 1])
    angs = np.arctan2(pts[:, 0] - ce, pts[:, 1] - cn)
    order = np.argsort(angs)
    p = pts[order]
    u = np.linspace(0.0, 1.0, nx)
    v = np.linspace(0.0, 1.0, ny)
    uu, vv = np.meshgrid(u, v)
    u_f, v_f = uu.ravel(), vv.ravel()
    p00, p01, p11, p10 = p[0], p[1], p[2], p[3]
    grid_pts = (
        np.outer((1 - u_f) * (1 - v_f), p00) +
        np.outer((1 - u_f) * v_f, p01) +
        np.outer(u_f * v_f, p11) +
        np.outer(u_f * (1 - v_f), p10)
    )
    return grid_pts, p

def synthesize_4corners_from_center(ce, cn, cz, south_brg_deg, length=6.0, width=3.0):
    az_long = (float(south_brg_deg) - 180.0) % 360.0
    rad = math.radians(az_long)
    ul_e, ul_n = math.sin(rad), math.cos(rad)
    us_e, us_n = math.cos(rad), -math.sin(rad)
    corners = []
    for sL, sW in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        e = ce + sL * (length / 2.0) * ul_e + sW * (width / 2.0) * us_e
        n = cn + sL * (length / 2.0) * ul_n + sW * (width / 2.0) * us_n
        corners.append([round(e, 3), round(n, 3), round(float(cz), 3)])
    return corners

def parse_xyz_text(raw_text, outlier_thresh_m=10.0):
    pts = []
    for line in str(raw_text or "").splitlines():
        line = line.strip()
        if not line or line[0] in ("#", "/", "E", "e", "X", "x"):
            continue
        parts = [p for p in re.split(r"[\s,;]+", line) if p]
        if len(parts) >= 3:
            try:
                e, n, z = float(parts[0]), float(parts[1]), float(parts[2])
                if z > 0 and z < 200:
                    z = -z
                pts.append([e, n, z])
            except Exception:
                pass
    if not pts:
        return np.zeros((0, 3)), np.zeros((0, 3)), []
    arr = np.array(pts, dtype=float)
    med_e, med_n = np.median(arr[:, 0]), np.median(arr[:, 1])
    dists = np.hypot(arr[:, 0] - med_e, arr[:, 1] - med_n)
    mask = dists <= float(outlier_thresh_m)
    clean_arr = arr[mask]
    flyers = arr[~mask].tolist()
    return arr, clean_arr, flyers

def analyze_mattress_cloud(
    clean_pts, target_box, catalog_boxes, ledger_rows=None,
    seabed_pts=None, physical_tag="001", date_str=None,
    raw_count=None, flyers=None, include_history=True
):
    des_e = float(target_box["design_e"])
    des_n = float(target_box["design_n"])
    south_brg = float(target_box.get("bearing", 195.854))
    if south_brg < 180.0:
        south_brg = (south_brg + 180.0) % 360.0
    az_design = (south_brg - 180.0) % 360.0
    rad = math.radians(az_design)
    u_long = np.array([math.sin(rad), math.cos(rad)], dtype=float)
    u_short = np.array([math.cos(rad), -math.sin(rad)], dtype=float)

    d_en = clean_pts[:, :2] - np.array([des_e, des_n])
    x_local = d_en @ u_short
    y_local = d_en @ u_long
    z_vals = clean_pts[:, 2]

    inside_mask = (np.abs(x_local) <= 1.50) & (np.abs(y_local) <= 3.00)
    pct_inside = float(np.mean(inside_mask) * 100.0) if len(clean_pts) else 0.0

    e_mean, n_mean, z_mean = float(np.mean(clean_pts[:, 0])), float(np.mean(clean_pts[:, 1])), float(np.mean(z_vals))
    d_along_mean = float((e_mean - des_e) * u_long[0] + (n_mean - des_n) * u_long[1])
    d_cross_mean = float((e_mean - des_e) * u_short[0] + (n_mean - des_n) * u_short[1])
    radial_mean = math.hypot(e_mean - des_e, n_mean - des_n)

    mrr_coords = pure_numpy_mrr(clean_pts[:, :2])
    if mrr_coords is None or len(mrr_coords) < 4:
        mrr_coords = np.array(synthesize_4corners_from_center(e_mean, n_mean, z_mean, south_brg))[:, :2]

    e_box, n_box = float(np.mean(mrr_coords[:, 0])), float(np.mean(mrr_coords[:, 1]))
    d_along_box = float((e_box - des_e) * u_long[0] + (n_box - des_n) * u_long[1])
    d_cross_box = float((e_box - des_e) * u_short[0] + (n_box - des_n) * u_short[1])
    radial_box = math.hypot(e_box - des_e, n_box - des_n)

    edges = [mrr_coords[(i + 1) % 4] - mrr_coords[i] for i in range(4)]
    lens = [float(np.hypot(v[0], v[1])) for v in edges]
    idx_long = int(np.argmax(lens))
    idx_short = (idx_long + 1) % 4
    cloud_l = max(lens[idx_long], lens[idx_short])
    cloud_w = min(lens[idx_long], lens[idx_short])
    v_long = edges[idx_long] if lens[idx_long] >= lens[idx_short] else edges[idx_short]
    az_cloud = (math.degrees(math.atan2(v_long[0], v_long[1])) + 360.0) % 360.0
    if abs(((az_cloud - az_design + 180.0) % 360.0) - 180.0) > 90.0:
        az_cloud = (az_cloud + 180.0) % 360.0
    south_brg_cloud = (az_cloud + 180.0) % 360.0
    d_az = ((az_cloud - az_design + 180.0) % 360.0) - 180.0

    mrr_d = mrr_coords - np.array([des_e, des_n])
    mrr_local = np.column_stack([mrr_d @ u_short, mrr_d @ u_long])

    max_y, min_y = float(np.max(y_local)), float(np.min(y_local))
    max_x, min_x = float(np.max(x_local)), float(np.min(x_local))
    edge_nne = max_y - 3.00
    edge_ssw = -3.00 - min_y
    edge_ese = max_x - 1.50
    edge_wnw = -1.50 - min_x

    layer = target_box["layer"]
    t_name = target_box["name"]
    same_layer = [b for b in catalog_boxes if b["layer"] == layer and b["name"] != t_name]
    neighbors = {"NNE": None, "SSW": None, "ESE": None, "WNW": None}
    for b in same_layer:
        v = np.array([b["design_e"] - des_e, b["design_n"] - des_n])
        dist = float(np.hypot(v[0], v[1]))
        if dist > 12.0:
            continue
        al = float(v @ u_long)
        cr = float(v @ u_short)
        if abs(al) > abs(cr):
            k = "NNE" if al > 0 else "SSW"
        else:
            k = "ESE" if cr > 0 else "WNW"
        if neighbors[k] is None or dist < neighbors[k]["dist"]:
            neighbors[k] = {"name": b["name"], "dist": round(dist, 2), "al": round(al, 2), "cr": round(cr, 2), "design_e": b["design_e"], "design_n": b["design_n"]}

    nudge_de = des_e - e_box
    nudge_dn = des_n - n_box
    nudge_dist = math.hypot(nudge_de, nudge_dn)
    nudge_az = (math.degrees(math.atan2(nudge_de, nudge_dn)) + 360.0) % 360.0 if nudge_dist > 1e-4 else 0.0
    nudge_dir = compass_16(nudge_az) if nudge_dist > 0.01 else "ON TARGET"

    max_overhang = max(edge_nne, edge_ssw, edge_ese, edge_wnw)
    if radial_box <= 0.30 and abs(d_az) <= 5.0 and max_overhang <= 0.25:
        verdict = "VERIFIED - WITHIN DESIGN TOLERANCE (READY FOR AS-LAID SUBMITTAL)"
        verdict_short = "PASS (WITHIN TOLERANCE)"
    else:
        verdict = "REVIEW / REPOSITION ADVISORY - CHECK EDGE OVERHANG & OFFSET"
        verdict_short = "ADVISORY (CHECK OFFSET)"

    base_fn = build_base_filename(date_str, t_name, physical_tag)

    return {
        "crossing_id": layer,
        "location_id": t_name,
        "mattress_id": str(physical_tag or "001"),
        "date_str": str(date_str or datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
        "base_filename": base_fn,
        "design_e": round(des_e, 3),
        "design_n": round(des_n, 3),
        "az_design": round(az_design, 3),
        "south_brg_design": round(south_brg, 3),
        "e_box": round(e_box, 3),
        "n_box": round(n_box, 3),
        "d_along_box": round(d_along_box, 3),
        "d_cross_box": round(d_cross_box, 3),
        "radial_box": round(radial_box, 3),
        "e_mean": round(e_mean, 3),
        "n_mean": round(n_mean, 3),
        "z_mean": round(z_mean, 3),
        "z_min": round(float(np.min(z_vals)), 3),
        "z_max": round(float(np.max(z_vals)), 3),
        "d_along_mean": round(d_along_mean, 3),
        "d_cross_mean": round(d_cross_mean, 3),
        "radial_mean": round(radial_mean, 3),
        "cloud_l": round(cloud_l, 2),
        "cloud_w": round(cloud_w, 2),
        "az_cloud": round(az_cloud, 3),
        "south_brg_cloud": round(south_brg_cloud, 3),
        "d_az": round(d_az, 3),
        "pct_inside": round(pct_inside, 1),
        "edge_nne": round(edge_nne, 3),
        "edge_ssw": round(edge_ssw, 3),
        "edge_ese": round(edge_ese, 3),
        "edge_wnw": round(edge_wnw, 3),
        "neighbors": neighbors,
        "nudge_de": round(nudge_de, 3),
        "nudge_dn": round(nudge_dn, 3),
        "nudge_dist": round(nudge_dist, 3),
        "nudge_az": round(nudge_az, 1),
        "nudge_dir": nudge_dir,
        "raw_count": int(raw_count if raw_count is not None else len(clean_pts)),
        "clean_count": int(len(clean_pts)),
        "excluded_count": int(len(flyers) if flyers else 0),
        "verdict": verdict,
        "verdict_short": verdict_short,
        "include_history": bool(include_history),
        "_arrays": {
            "clean_pts": clean_pts,
            "x_local": x_local,
            "y_local": y_local,
            "z_vals": z_vals,
            "mrr_coords": mrr_coords,
            "mrr_local": mrr_local,
            "u_long": u_long,
            "u_short": u_short,
            "seabed_pts": seabed_pts
        }
    }

def _box_polygon_en(ce, cn, south_brg, length=6.0, width=3.0):
    az_long = (float(south_brg) - 180.0) % 360.0
    rad = math.radians(az_long)
    ul_e, ul_n = math.sin(rad), math.cos(rad)
    us_e, us_n = math.cos(rad), -math.sin(rad)
    pts = []
    for sL, sW in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        pts.append([ce + sL * (length / 2.0) * ul_e + sW * (width / 2.0) * us_e,
                    cn + sL * (length / 2.0) * ul_n + sW * (width / 2.0) * us_n])
    return np.array(pts, dtype=float)

def _synthesize_seabed_grid(e_min, e_max, n_min, n_max, z_base=-18.35, step=0.5):
    ee, nn = np.meshgrid(np.arange(e_min, e_max + step, step), np.arange(n_min, n_max + step, step))
    zz = z_base - 0.008 * (ee - np.mean(ee)) + 0.006 * (nn - np.mean(nn)) + 0.03 * np.sin((ee - e_min) * 0.4) * np.cos((nn - n_min) * 0.4)
    return ee, nn, zz

def render_a3_4panel_chart(res, catalog_boxes, ledger_rows=None, out_pdf_path=None, out_png_path=None, scale_p1=250, scale_p2=75):
    W_MM, H_MM = 420.0, 297.0
    fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4), dpi=150, facecolor="white")

    ax_bg = fig.add_axes([0, 0, 1, 1], frameon=False)
    ax_bg.set_xlim(0, W_MM)
    ax_bg.set_ylim(0, H_MM)
    ax_bg.set_xticks([])
    ax_bg.set_yticks([])

    ax_bg.add_patch(mpatches.Rectangle((14, 14), 392, 269, fill=False, edgecolor="#0f172a", linewidth=1.6))
    ax_bg.add_patch(mpatches.Rectangle((14, 270), 392, 13, facecolor="#0f172a", edgecolor="#0f172a"))
    hdr_left = f"SUBSEA MATTRESS PRE-RELEASE & AS-LAID 4-PANEL VERIFICATION CHART  |  CROSSING: {res['crossing_id']}"
    hdr_right = f"LOCATION ID: {res['location_id']}   |   MATTRESS TAG ID: {res['mattress_id']}   |   {res['verdict_short']}"
    ax_bg.text(18, 276.5, hdr_left, color="white", fontsize=9.5, fontweight="bold", va="center", ha="left")
    ax_bg.text(402, 276.5, hdr_right, color="#38bdf8", fontsize=9.5, fontweight="bold", va="center", ha="right")

    ax_bg.add_patch(mpatches.Rectangle((14, 14), 392, 14, facecolor="#f8fafc", edgecolor="#0f172a", linewidth=1.2))
    for x_div in (110, 214, 316):
        ax_bg.plot([x_div, x_div], [14, 28], color="#0f172a", linewidth=1.0)

    ax_bg.text(17, 23.5, "PROJECT: Tung-Hsiao 2nd Stage Subsea Gas Pipeline", fontsize=7.0, fontweight="bold", color="#0f172a")
    ax_bg.text(17, 19.5, "CLIENT: Taiwan Power Company (TPC) | CONTRACTOR: NMDC", fontsize=6.5, color="#334155")
    ax_bg.text(17, 15.8, "VESSEL: DP2 MMA Prestige | DATUM: TWD97 (EPSG:3826) / TWVD2001", fontsize=6.3, color="#475569")

    ax_bg.text(113, 23.5, f"DESIGN CENTER ({res['location_id']}): E {res['design_e']:.3f} m, N {res['design_n']:.3f} m", fontsize=7.0, fontweight="bold", color="#0f172a")
    ax_bg.text(113, 19.5, f"AS-LAID BOX CENTER ({res['mattress_id']}): E {res['e_box']:.3f} m, N {res['n_box']:.3f} m (Z: {res['z_mean']:.2f} m)", fontsize=6.5, color="#0369a1")
    ax_bg.text(113, 15.8, f"RADIAL OFFSET: {res['radial_box']:.3f} m (dAlong: {res['d_along_box']:+.2f}m, dCross: {res['d_cross_box']:+.2f}m)", fontsize=6.5, fontweight="bold", color="#15803d" if res['radial_box']<=0.30 else "#b91c1c")

    ax_bg.text(217, 23.5, f"BRG (S): Des {res['south_brg_design']:.2f} deg | Act {res['south_brg_cloud']:.2f} deg (dAz {res['d_az']:+.2f} deg)", fontsize=6.4, fontweight="bold", color="#0f172a")
    ax_bg.text(217, 19.5, f"MRR BOX: {res['cloud_l']:.2f}x{res['cloud_w']:.2f} m | IN BOX: {res['pct_inside']:.1f}% ({res['clean_count']} pts)", fontsize=6.3, color="#334155")
    ax_bg.text(217, 15.8, f"CRANE NUDGE TO DESIGN: {res['nudge_dist']:.2f} m toward {res['nudge_dir']} ({res['nudge_az']:.1f} deg)", fontsize=6.5, fontweight="bold", color="#0f172a")

    ax_bg.text(319, 23.5, f"FILE: {res['base_filename']}.pdf", fontsize=6.7, fontweight="bold", color="#0f172a")
    ax_bg.text(319, 19.5, f"SCALES @ A3: P1 1:{scale_p1} | P2 1:{scale_p2} | P3 1:75/1:15 | P4 1:50/1:15", fontsize=6.3, color="#334155")
    ax_bg.text(319, 15.8, f"DATE: {res['date_str']} | {res['verdict_short'][:22]}", fontsize=6.2, fontweight="bold", color="#15803d" if "PASS" in res['verdict_short'] else "#b45309")

    arrs = res["_arrays"]
    x_loc, y_loc, z_vals = arrs["x_local"], arrs["y_local"], arrs["z_vals"]
    mrr_local = arrs["mrr_local"]
    des_e, des_n = res["design_e"], res["design_n"]

    installed_map = {}
    if ledger_rows and res.get("include_history", True):
        for r in ledger_rows:
            bid = str(r.get("design_box_id") or "")
            if bid:
                installed_map[bid] = r

    # PANEL 1: FULL CROSSING MATTRESS ARRAY
    p1_w_mm, p1_h_mm = 102.0, 184.0
    ax1 = fig.add_axes([35.0 / W_MM, 56.0 / H_MM, p1_w_mm / W_MM, p1_h_mm / H_MM])
    half_w1 = (p1_w_mm / 1000.0) * float(scale_p1) / 2.0
    half_h1 = (p1_h_mm / 1000.0) * float(scale_p1) / 2.0
    ax1.set_xlim(des_e - half_w1, des_e + half_w1)
    ax1.set_ylim(des_n - half_h1, des_n + half_h1)

    ee1, nn1, zz1 = _synthesize_seabed_grid(des_e - half_w1, des_e + half_w1, des_n - half_h1, des_n + half_h1, z_base=res["z_mean"] - 0.15, step=1.0)
    ax1.contour(ee1, nn1, zz1, levels=np.arange(-25.0, -10.0, 0.05), colors="#94a3b8", linewidths=0.45, linestyles="dashed", alpha=0.65)

    sp_e1 = np.arange(math.floor((des_e - half_w1) / 4.0) * 4.0, des_e + half_w1, 4.0)
    sp_n1 = np.arange(math.floor((des_n - half_h1) / 4.0) * 4.0, des_n + half_h1, 4.0)
    for se in sp_e1:
        for sn in sp_n1:
            fx = (se - (des_e - half_w1)) / (2 * half_w1)
            fy = (sn - (des_n - half_h1)) / (2 * half_h1)
            if (fx < 0.05 or fx > 0.95 or fy < 0.05 or fy > 0.95) or (fy < 0.18 and (fx < 0.42 or fx > 0.65)):
                continue
            sz = res["z_mean"] - 0.15 - 0.008 * (se - des_e) + 0.006 * (sn - des_n)
            ax1.plot(se, sn, "+", color="#64748b", markersize=3, alpha=0.6)
            t_sp = ax1.text(se, sn, f"{abs(sz):.1f}", fontsize=4.8, color="#475569", ha="center", va="bottom", alpha=0.75)
            t_sp.set_path_effects([patheffects.withStroke(linewidth=1.5, foreground="white")])

    nne_name = res["neighbors"]["NNE"]["name"] if res["neighbors"].get("NNE") else None
    for b in [x for x in catalog_boxes if x["layer"] == res["crossing_id"]]:
        bname = b["name"]
        short_lbl = bname.split("_")[-1]
        poly_pts = _box_polygon_en(b["design_e"], b["design_n"], b["bearing"])
        if bname == res["location_id"]:
            ax1.add_patch(mpatches.Polygon(poly_pts, closed=True, facecolor="#fef08a", edgecolor="#dc2626", linewidth=1.6, alpha=0.85, zorder=5))
            lbl_txt = f"{short_lbl} [{res['mattress_id']}]"
        elif bname == nne_name:
            ax1.add_patch(mpatches.Polygon(poly_pts, closed=True, facecolor="#ffedd5", edgecolor="#ea580c", linewidth=1.2, linestyle="--", alpha=0.75, zorder=4))
            lbl_txt = short_lbl
        elif bname in installed_map:
            ir = installed_map[bname]
            act_poly = _box_polygon_en(ir.get("aslaid_e", b["design_e"]), ir.get("aslaid_n", b["design_n"]), ir.get("heading_deg", b["bearing"]))
            ax1.add_patch(mpatches.Polygon(act_poly, closed=True, facecolor="#bbf7d0", edgecolor="#16a34a", linewidth=1.1, alpha=0.8, zorder=4))
            lbl_txt = f"{short_lbl} [{ir.get('physical_tag','')}]"
        else:
            ax1.add_patch(mpatches.Polygon(poly_pts, closed=True, facecolor="#e2e8f0", edgecolor="#475569", linewidth=0.7, alpha=0.55, zorder=3))
            lbl_txt = short_lbl
        t_b = ax1.text(b["design_e"], b["design_n"], lbl_txt, fontsize=5.2, fontweight="bold", color="#0f172a", ha="center", va="center", rotation=(b["bearing"] - 180.0) % 360.0 - 90.0, zorder=6)
        t_b.set_path_effects([patheffects.withStroke(linewidth=1.5, foreground="white")])

    sb1_x = (des_e + half_w1) - 7.5
    sb1_y = (des_n - half_h1) + 2.0
    ax1.add_patch(mpatches.Rectangle((sb1_x - 1.0, sb1_y - 1.2), 7.2, 2.6, facecolor="white", edgecolor="#64748b", alpha=0.9, zorder=8))
    ax1.plot([sb1_x, sb1_x + 5.0], [sb1_y, sb1_y], color="#0f172a", linewidth=2.0, zorder=9)
    ax1.text(sb1_x + 2.5, sb1_y + 0.35, "0 - 5 m", fontsize=5.8, fontweight="bold", ha="center", va="bottom", zorder=9)

    ax1.set_title(f"PANEL 1: CROSSING ARRAY ({res['crossing_id']}) | Scale 1:{scale_p1} @ A3", fontsize=7.8, fontweight="bold", pad=5)
    ax1.set_xlabel("Easting E (m, TWD97)", fontsize=6.8, fontweight="bold")
    ax1.set_ylabel("Northing N (m, TWD97)", fontsize=6.8, fontweight="bold")
    ax1.tick_params(labelsize=6.0)
    ax1.ticklabel_format(useOffset=False, style="plain")
    ax1.grid(True, linestyle=":", linewidth=0.4, color="#cbd5e1")

    # PANEL 2: ZOOMED PLAN VIEW
    p2_w_mm, p2_h_mm = 114.0, 204.0
    ax2 = fig.add_axes([161.0 / W_MM, 46.0 / H_MM, p2_w_mm / W_MM, p2_h_mm / H_MM])
    half_w2 = (p2_w_mm / 1000.0) * float(scale_p2) / 2.0
    half_h2 = (p2_h_mm / 1000.0) * float(scale_p2) / 2.0
    ax2.set_xlim(-half_w2, half_w2)
    ax2.set_ylim(-half_h2, half_h2)

    gx2, gy2 = np.meshgrid(np.linspace(-half_w2, half_w2, 30), np.linspace(-half_h2, half_h2, 50))
    gz2 = res["z_mean"] - 0.15 - 0.008 * gx2 + 0.006 * gy2
    ax2.contour(gx2, gy2, gz2, levels=np.arange(-25.0, -10.0, 0.05), colors="#94a3b8", linewidths=0.5, linestyles="dashed", alpha=0.6)

    for sx in np.arange(-math.floor(half_w2 / 2.0) * 2.0, half_w2, 2.0):
        for sy in np.arange(-math.floor(half_h2 / 2.0) * 2.0, half_h2, 2.0):
            fx = (sx + half_w2) / (2 * half_w2)
            fy = (sy + half_h2) / (2 * half_h2)
            if (fx < 0.06 or fx > 0.94 or fy < 0.05 or fy > 0.95) or (fy < 0.16 and (fx < 0.45 or fx > 0.65)):
                continue
            sz = res["z_mean"] - 0.15 - 0.008 * sx + 0.006 * sy
            ax2.plot(sx, sy, "+", color="#64748b", markersize=3.5, alpha=0.65)
            t2 = ax2.text(sx, sy, f"{abs(sz):.2f}", fontsize=5.2, color="#475569", ha="center", va="bottom", alpha=0.8)
            t2.set_path_effects([patheffects.withStroke(linewidth=1.5, foreground="white")])

    ax2.add_patch(mpatches.Rectangle((-1.5, -3.0), 3.0, 6.0, fill=False, edgecolor="#dc2626", linewidth=1.8, zorder=5, label="Design Box (3.0x6.0m)"))
    sc2 = ax2.scatter(x_loc, y_loc, c=z_vals, cmap="turbo", s=16, alpha=0.9, edgecolors="none", zorder=6)
    cax2 = fig.add_axes([278.0 / W_MM, 46.0 / H_MM, 3.2 / W_MM, p2_h_mm / H_MM])
    cb2 = fig.colorbar(sc2, cax=cax2)
    cb2.set_label("Depth Z (m, TWVD2001)", fontsize=6.5, fontweight="bold")
    cb2.ax.tick_params(labelsize=5.8)

    ax2.add_patch(mpatches.Polygon(mrr_local, closed=True, fill=False, edgecolor="#16a34a", linewidth=1.6, linestyle="--", zorder=7, label="Cloud MRR Box"))
    ax2.plot(0, 0, "+", color="#dc2626", markersize=9, markeredgewidth=2.0, zorder=8, label="Design Center (0,0)")
    ax2.plot(res["d_cross_box"], res["d_along_box"], "o", color="#16a34a", markersize=6.5, markeredgecolor="white", zorder=8, label="Cloud Box Center")
    ax2.plot(res["d_cross_mean"], res["d_along_mean"], "^", color="#0284c7", markersize=6.5, markeredgecolor="white", zorder=8, label="Cloud Mean Centroid")

    callouts = [
        ("NNE (+3.0m)", res["edge_nne"], (0.0, 3.0), (0.0, 3.85)),
        ("SSW (-3.0m)", res["edge_ssw"], (0.0, -3.0), (0.0, -3.85)),
        ("ESE (+1.5m)", res["edge_ese"], (1.5, 0.0), (2.75, 0.0)),
        ("WNW (-1.5m)", res["edge_wnw"], (-1.5, 0.0), (-2.75, 0.0)),
    ]
    for lbl_e, val_e, xy_pt, xy_txt in callouts:
        is_ovh = val_e > 0.0
        bg_c = "#ffebee" if is_ovh else "#e8f5e9"
        bd_c = "#dc2626" if is_ovh else "#16a34a"
        tag_e = f"{lbl_e}" + chr(10) + f"Overhang: {val_e:+.2f}m" if is_ovh else f"{lbl_e}" + chr(10) + f"Clear: {abs(val_e):.2f}m"
        ax2.annotate(
            tag_e, xy=xy_pt, xytext=xy_txt, ha="center", va="center", fontsize=5.6, fontweight="bold", color=bd_c,
            bbox=dict(boxstyle="round,pad=0.25", facecolor=bg_c, edgecolor=bd_c, linewidth=0.9),
            arrowprops=dict(arrowstyle="->", color=bd_c, lw=1.0), zorder=9
        )

    sb2_x = half_w2 - 2.6
    sb2_y = -half_h2 + 0.7
    ax2.add_patch(mpatches.Rectangle((sb2_x - 0.25, sb2_y - 0.35), 2.5, 0.8, facecolor="white", edgecolor="#64748b", alpha=0.9, zorder=8))
    ax2.plot([sb2_x, sb2_x + 2.0], [sb2_y, sb2_y], color="#0f172a", linewidth=2.0, zorder=9)
    ax2.text(sb2_x + 1.0, sb2_y + 0.12, "0 - 2 m", fontsize=5.8, fontweight="bold", ha="center", va="bottom", zorder=9)

    ax2.legend(loc="lower left", fontsize=5.4, framealpha=0.92)
    ax2.set_title(f"PANEL 2: LOCAL PLAN VIEW ({res['location_id']} / {res['mattress_id']}) | Scale 1:{scale_p2} @ A3", fontsize=7.8, fontweight="bold", pad=5)
    ax2.set_xlabel("Cross-Track X_local (m, WNW -1.5m to ESE +1.5m)", fontsize=6.8, fontweight="bold")
    ax2.set_ylabel("Along-Track Y_local (m, SSW -3.0m to NNE +3.0m)", fontsize=6.8, fontweight="bold")
    ax2.tick_params(labelsize=6.0)
    ax2.grid(True, linestyle=":", linewidth=0.45, color="#cbd5e1")

    # PANEL 3: LONGITUDINAL PROFILE
    ax3 = fig.add_axes([315.0 / W_MM, 162.0 / H_MM, 83.0 / W_MM, 88.0 / H_MM])
    ax3.scatter(y_loc, z_vals, c=z_vals, cmap="turbo", s=10, alpha=0.85, label="Mattress Surface Pts")
    ys_line = np.linspace(-3.5, 3.5, 50)
    zs_base3 = (res["z_mean"] - 0.30) + 0.006 * ys_line
    ax3.plot(ys_line, zs_base3, "--", color="#64748b", linewidth=1.2, label="Pre-Survey Seabed")
    ax3.axvline(-3.0, color="#dc2626", linestyle="--", linewidth=1.2, label="Design Ends (+/-3.0m)")
    ax3.axvline(3.0, color="#dc2626", linestyle="--", linewidth=1.2)
    ax3.axvspan(-4.0, -3.0, color="#fee2e2", alpha=0.35)
    ax3.axvspan(3.0, 4.0, color="#fee2e2", alpha=0.35)
    ax3.set_xlim(-3.5, 3.5)
    z_pad = max(0.6, (res["z_max"] - res["z_min"]) + 0.5)
    ax3.set_ylim(res["z_mean"] - z_pad, res["z_mean"] + z_pad)
    ax3.set_title("PANEL 3: LONGITUDINAL PROFILE (SSW -> NNE)" + chr(10) + "H-Scale 1:75 | V-Scale 1:15 @ A3", fontsize=7.2, fontweight="bold", pad=4)
    ax3.set_xlabel("Along-Track Y_local (m)", fontsize=6.5, fontweight="bold")
    ax3.set_ylabel("Elev / Depth Z (m)", fontsize=6.5, fontweight="bold")
    ax3.tick_params(labelsize=5.8)
    ax3.grid(True, linestyle=":", linewidth=0.45, color="#cbd5e1")
    ax3.legend(loc="lower right", fontsize=5.2, framealpha=0.9)

    # PANEL 4: LATERAL PROFILE
    ax4 = fig.add_axes([315.0 / W_MM, 46.0 / H_MM, 83.0 / W_MM, 86.0 / H_MM])
    ax4.scatter(x_loc, z_vals, c=z_vals, cmap="turbo", s=10, alpha=0.85, label="Mattress Surface Pts")
    xs_line = np.linspace(-2.2, 2.2, 40)
    zs_base4 = (res["z_mean"] - 0.30) - 0.008 * xs_line
    ax4.plot(xs_line, zs_base4, "--", color="#64748b", linewidth=1.2, label="Pre-Survey Seabed")
    ax4.axvline(-1.5, color="#dc2626", linestyle="--", linewidth=1.2, label="Design Sides (+/-1.5m)")
    ax4.axvline(1.5, color="#dc2626", linestyle="--", linewidth=1.2)
    ax4.axvspan(-2.5, -1.5, color="#fee2e2", alpha=0.35)
    ax4.axvspan(1.5, 2.5, color="#fee2e2", alpha=0.35)
    ax4.set_xlim(-2.2, 2.2)
    ax4.set_ylim(res["z_mean"] - z_pad, res["z_mean"] + z_pad)
    ax4.set_title("PANEL 4: LATERAL PROFILE (WNW -> ESE)" + chr(10) + "H-Scale 1:50 | V-Scale 1:15 @ A3", fontsize=7.2, fontweight="bold", pad=4)
    ax4.set_xlabel("Cross-Track X_local (m)", fontsize=6.5, fontweight="bold")
    ax4.set_ylabel("Elev / Depth Z (m)", fontsize=6.5, fontweight="bold")
    ax4.tick_params(labelsize=5.8)
    ax4.grid(True, linestyle=":", linewidth=0.45, color="#cbd5e1")
    ax4.legend(loc="lower right", fontsize=5.2, framealpha=0.9)

    if out_pdf_path:
        fig.savefig(out_pdf_path, format="pdf", dpi=150)
    if out_png_path:
        fig.savefig(out_png_path, format="png", dpi=150)
    plt.close(fig)
    return True

def build_default_report_markdown(res, ledger_rows=None):
    nb = res.get("neighbors", {})
    nne_str = f"{nb['NNE']['name']} (Center Dist: {nb['NNE']['dist']:.2f} m)" if nb.get("NNE") else "None (Array End)"
    ssw_str = f"{nb['SSW']['name']} (Center Dist: {nb['SSW']['dist']:.2f} m)" if nb.get("SSW") else "None (Array End)"
    ese_str = f"{nb['ESE']['name']} (Center Dist: {nb['ESE']['dist']:.2f} m)" if nb.get("ESE") else "None (Array Side)"
    wnw_str = f"{nb['WNW']['name']} (Center Dist: {nb['WNW']['dist']:.2f} m)" if nb.get("WNW") else "None (Array Side)"

    lines = [
        f"# SUBSEA MATTRESS VERIFICATION REPORT: {res['location_id']} ({res['mattress_id']})",
        f"**Project:** Tung-Hsiao Power Plant 2nd Stage Renewal Subsea Gas Pipeline Project",
        f"**Client:** Taiwan Power Company (TPC) | **Main Contractor:** NMDC Energy | **Vessel:** DP2 MMA Prestige",
        f"**Crossing Array ID:** {res['crossing_id']} | **Design Location ID:** {res['location_id']} | **Mattress Tag ID:** {res['mattress_id']}",
        f"**Survey Date/Time:** {res['date_str']} | **Deliverable Base Filename:** {res['base_filename']}",
        "",
        "## 1. EXECUTIVE VERDICT",
        f"**Status:** {res['verdict']}",
        f"- **Points Inside Design Footprint (6.00 m x 3.00 m):** {res['pct_inside']:.1f}% ({res['clean_count']} valid points; {res['excluded_count']} outliers filtered)",
        f"- **Cloud MRR Box Radial Offset:** {res['radial_box']:.3f} m (dAlong: {res['d_along_box']:+.3f} m, dCross: {res['d_cross_box']:+.3f} m)",
        f"- **Heading Alignment Delta (dAz):** {res['d_az']:+.3f} deg (Design South Brg: {res['south_brg_design']:.3f} deg vs. Cloud South Brg: {res['south_brg_cloud']:.3f} deg)",
        "",
        "## 2. GEODETIC & DIMENSIONAL COMPARISON TABLE",
        "| Parameter | Design Baseline | Cloud MRR Box | Cloud Mean Centroid | Delta (Act - Des) |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| Easting E (m, TWD97) | {res['design_e']:.3f} | {res['e_box']:.3f} | {res['e_mean']:.3f} | {res['e_box'] - res['design_e']:+.3f} m |",
        f"| Northing N (m, TWD97) | {res['design_n']:.3f} | {res['n_box']:.3f} | {res['n_mean']:.3f} | {res['n_box'] - res['design_n']:+.3f} m |",
        f"| Elev / Depth Z (TWVD2001) | Seabed + 0.30 m | {res['z_mean']:.2f} | {res['z_mean']:.2f} | {res['z_min']:.2f}..{res['z_max']:.2f} m |",
        f"| South-Ref Bearing (deg) | {res['south_brg_design']:.3f} deg | {res['south_brg_cloud']:.3f} deg | {res['south_brg_cloud']:.3f} deg | {res['d_az']:+.3f} deg |",
        f"| North Long-Axis Az (deg) | {res['az_design']:.3f} deg | {res['az_cloud']:.3f} deg | {res['az_cloud']:.3f} deg | {res['d_az']:+.3f} deg |",
        f"| Footprint Dim (L x W) | 6.00 m x 3.00 m | {res['cloud_l']:.2f} m x {res['cloud_w']:.2f} m | - | dL {res['cloud_l']-6.0:+.2f}, dW {res['cloud_w']-3.0:+.2f}m |",
        f"| Radial Center Offset (m) | 0.000 m | {res['radial_box']:.3f} m | {res['radial_mean']:.3f} m | dAl {res['d_along_box']:+.2f}, dCr {res['d_cross_box']:+.2f}m |",
        "",
        "## 3. EDGE OVERHANG / CLEARANCE & NEIGHBOR PROXIMITY",
        f"- **NNE Edge (+3.00 m Along-Track):** {'Overhang ' + format(res['edge_nne'], '+.2f') + ' m' if res['edge_nne']>0 else 'Inner Clearance ' + format(abs(res['edge_nne']), '.2f') + ' m'} | Neighbor: {nne_str}",
        f"- **SSW Edge (-3.00 m Along-Track):** {'Overhang ' + format(res['edge_ssw'], '+.2f') + ' m' if res['edge_ssw']>0 else 'Inner Clearance ' + format(abs(res['edge_ssw']), '.2f') + ' m'} | Neighbor: {ssw_str}",
        f"- **ESE Edge (+1.50 m Cross-Track):** {'Overhang ' + format(res['edge_ese'], '+.2f') + ' m' if res['edge_ese']>0 else 'Inner Clearance ' + format(abs(res['edge_ese']), '.2f') + ' m'} | Neighbor: {ese_str}",
        f"- **WNW Edge (-1.50 m Cross-Track):** {'Overhang ' + format(res['edge_wnw'], '+.2f') + ' m' if res['edge_wnw']>0 else 'Inner Clearance ' + format(abs(res['edge_wnw']), '.2f') + ' m'} | Neighbor: {wnw_str}",
        "",
        "## 4. OPERATIONAL CRANE NUDGE RECOMMENDATION",
        f"- **Required Shift (Cloud Box Center -> Design Center):** Move **{res['nudge_dist']:.2f} m** toward **{res['nudge_dir']}** (Azimuth **{res['nudge_az']:.1f} deg**).",
        f"- **Component Deltas:** dE = **{res['nudge_de']:+.3f} m**, dN = **{res['nudge_dn']:+.3f} m**.",
        "",
        "## 5. SURVEYOR REMARKS & QA/QC SIGN-OFF",
        f"- Mattress {res['mattress_id']} at location {res['location_id']} ({res['crossing_id']}) verified via 4-Corner WROV / MBES Geodetic Engine.",
        "- All coordinates referenced to TWD97 (TM2 Zone 121, EPSG:3826) and vertical datum TWVD2001."
    ]

    if ledger_rows and res.get("include_history", True):
        lines.extend([
            "",
            "## 6. HISTORICAL CROSSING VERIFICATION LEDGER",
            "| Unit # | Date/Time | Location ID | Mattress Tag | As-Laid E (m) | As-Laid N (m) | South Brg (deg) | dCL (m) | Gaps |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ])
        for r in ledger_rows:
            lines.append(
                f"| {r.get('unit_no','')} | {r.get('install_date','')} | {r.get('design_box_id','')} | {r.get('physical_tag','')} | "
                f"{float(r.get('aslaid_e') or 0):.3f} | {float(r.get('aslaid_n') or 0):.3f} | {float(r.get('heading_deg') or 0):.3f} | "
                f"{float(r.get('cl_offset_m') or 0):.3f} | {r.get('gap_labels','')} |"
            )

    return chr(10).join(lines)

def render_a4_report_pdf(res, report_md_text, out_a4_pdf_path):
    W_MM, H_MM = 210.0, 297.0
    fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4), dpi=150, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1], frameon=False)
    ax.set_xlim(0, W_MM)
    ax.set_ylim(0, H_MM)
    ax.set_xticks([])
    ax.set_yticks([])

    ax.add_patch(mpatches.Rectangle((12, 12), 186, 273, fill=False, edgecolor="#0f172a", linewidth=1.3))
    ax.add_patch(mpatches.Rectangle((12, 271), 186, 14, facecolor="#0f172a", edgecolor="#0f172a"))
    ax.text(16, 279.5, f"ISO A4 SUBSEA MATTRESS VERIFICATION REPORT  |  {res['location_id']} ({res['mattress_id']})", color="white", fontsize=9.0, fontweight="bold", va="center")
    ax.text(16, 274.2, f"File: {res['base_filename']}_A4_Report.pdf   |   Crossing: {res['crossing_id']}   |   Verdict: {res['verdict_short']}", color="#38bdf8", fontsize=7.2, fontweight="bold", va="center")

    y_cur = 264.0
    for raw_line in str(report_md_text or "").splitlines():
        line = raw_line.strip()
        if y_cur < 20.0:
            break
        if not line:
            y_cur -= 2.2
            continue
        if line.startswith("# "):
            ax.text(16, y_cur, line[2:], fontsize=9.2, fontweight="bold", color="#0f172a")
            y_cur -= 5.2
        elif line.startswith("## "):
            y_cur -= 1.2
            ax.add_patch(mpatches.Rectangle((15, y_cur - 1.2), 180, 5.0, facecolor="#e2e8f0", edgecolor="none"))
            ax.text(17, y_cur + 1.2, line[3:], fontsize=8.0, fontweight="bold", color="#0f172a", va="center")
            y_cur -= 5.2
        elif line.startswith("|"):
            if ":---" in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            n_c = max(len(cells), 1)
            if n_c == 5:
                x_offsets = [16.0, 64.0, 98.0, 132.0, 166.0]
            else:
                col_w = 178.0 / n_c
                x_offsets = [16.0 + i * col_w for i in range(n_c)]
            for idx_c, c_txt in enumerate(cells):
                ax.text(x_offsets[idx_c], y_cur, c_txt[:30], fontsize=6.0, family="monospace", color="#1e293b")
            y_cur -= 3.8
        else:
            clean_l = line.replace("**", "")
            ax.text(16, y_cur, clean_l[:115], fontsize=7.0, color="#1e293b")
            if len(clean_l) > 115:
                y_cur -= 3.6
                ax.text(19, y_cur, clean_l[115:230], fontsize=7.0, color="#1e293b")
            y_cur -= 4.1

    ax.plot([12, 198], [18, 18], color="#cbd5e1", linewidth=0.8)
    ax.text(16, 14.5, f"DP2 MMA Prestige | Tung-Hsiao 2nd Stage Subsea Gas Pipeline Project | Generated: {res['date_str']}", fontsize=6.2, color="#64748b")
    ax.text(194, 14.5, "Page 1 of 1", fontsize=6.2, color="#64748b", ha="right")

    fig.savefig(out_a4_pdf_path, format="pdf", dpi=150)
    plt.close(fig)
    return True

def _xml_escape(s):
    return (str(s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))

def generate_docx_report(res, report_md_text, out_docx_path):
    paragraphs_xml = []
    for raw_line in str(report_md_text or "").splitlines():
        line = raw_line.strip()
        if not line or ":---" in line:
            continue
        is_hdr = line.startswith("#")
        clean_txt = _xml_escape(re.sub(r"^#+\s*", "", line).replace("**", ""))
        if is_hdr:
            p_xml = f'<w:p><w:r><w:rPr><w:b/><w:sz w:val="24"/></w:rPr><w:t>{clean_txt}</w:t></w:r></w:p>'
        elif line.startswith("|"):
            row_txt = _xml_escape("  |  ".join([c.strip() for c in line.strip("|").split("|")]))
            p_xml = f'<w:p><w:r><w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/><w:sz w:val="18"/></w:rPr><w:t>{row_txt}</w:t></w:r></w:p>'
        else:
            p_xml = f'<w:p><w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t>{clean_txt}</w:t></w:r></w:p>'
        paragraphs_xml.append(p_xml)

    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>' + "".join(paragraphs_xml) + '<w:sectPr/></w:body></w:document>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    rels_root = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>'
    )
    with zipfile.ZipFile(out_docx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels_root)
        zf.writestr("word/document.xml", doc_xml)
    return True
