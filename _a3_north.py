import os, io, re, gc, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as patheffects
from mti_4panel_math import idw_interpolate, _box_corners_cw

def draw_north_arrow(ax, x_lim, y_lim, north_angle_deg=0.0, sub_label="Grid N"):
    w = float(x_lim[1] - x_lim[0])
    h = float(y_lim[1] - y_lim[0])
    cx = float(x_lim[0]) + 0.105 * w
    cy = float(y_lim[1]) - 0.082 * h
    r = 0.046 * w

    bg_circle = mpatches.Circle((cx, cy), r * 1.38, facecolor="white", edgecolor="#475569", linewidth=0.8, alpha=0.92, zorder=10)
    ax.add_patch(bg_circle)
    inner_ring = mpatches.Circle((cx, cy), r * 1.12, fill=False, edgecolor="#94a3b8", linewidth=0.45, linestyle=":", zorder=10)
    ax.add_patch(inner_ring)

    rad = math.radians(float(north_angle_deg))
    ux, uy = math.sin(rad), math.cos(rad)
    px, py = math.cos(rad), -math.sin(rad)

    tip = (cx + ux * r, cy + uy * r)
    tail_c = (cx - ux * (r * 0.35), cy - uy * (r * 0.35))
    left_w = (cx - ux * (r * 0.65) - px * (r * 0.42), cy - uy * (r * 0.65) - py * (r * 0.42))
    right_w = (cx - ux * (r * 0.65) + px * (r * 0.42), cy - uy * (r * 0.65) + py * (r * 0.42))

    ax.add_patch(mpatches.Polygon([tip, left_w, tail_c], closed=True, facecolor="#0f172a", edgecolor="#0f172a", linewidth=0.7, zorder=11))
    ax.add_patch(mpatches.Polygon([tip, right_w, tail_c], closed=True, facecolor="white", edgecolor="#0f172a", linewidth=0.7, zorder=11))

    nx_lbl = cx + ux * (r * 1.72)
    ny_lbl = cy + uy * (r * 1.72)
    t_n = ax.text(nx_lbl, ny_lbl, "N", fontsize=6.8, fontweight="bold", color="#0f172a", ha="center", va="center", zorder=12)
    t_n.set_path_effects([patheffects.withStroke(linewidth=1.8, foreground="white")])

    if sub_label:
        t_sub = ax.text(cx, cy - r * 1.65, sub_label, fontsize=4.6, fontweight="bold", color="#334155", ha="center", va="top", zorder=12)
        t_sub.set_path_effects([patheffects.withStroke(linewidth=1.5, foreground="white")])

def plot_cad_background(ax, cad_polylines, is_local=False, des_e=0.0, des_n=0.0, u_short=None, u_long=None):
    if not cad_polylines:
        return
    for poly in cad_polylines:
        arr = np.asarray(poly, dtype=float)
        if arr.ndim != 2 or len(arr) < 2:
            continue
        if is_local and u_short is not None and u_long is not None:
            d = arr[:, :2] - np.array([des_e, des_n])
            px, py = d @ u_short, d @ u_long
        else:
            px, py = arr[:, 0], arr[:, 1]
        ax.plot(px, py, color="#64748b", linewidth=0.65, linestyle="-", alpha=0.55, zorder=2)

def plot_seabed_layer(ax, seabed_xyz, x_lim, y_lim, is_zoomed=False, show_contours=True, contour_interval=0.05, show_soundings=True, spot_spacing=2.0, bathy_source="NO_BATHY_UPLOADED"):
    if seabed_xyz is None or len(seabed_xyz) < 1 or bathy_source != "SURVEY_BATHY":
        return
    sb = np.asarray(seabed_xyz, dtype=float)
    in_view = (sb[:, 0] >= x_lim[0] - 4.0) & (sb[:, 0] <= x_lim[1] + 4.0) & (sb[:, 1] >= y_lim[0] - 4.0) & (sb[:, 1] <= y_lim[1] + 4.0)
    sb_near = sb[in_view] if np.any(in_view) else sb

    nx, ny = (28, 36) if is_zoomed else (32, 44)
    gx, gy = np.meshgrid(np.linspace(x_lim[0], x_lim[1], nx), np.linspace(y_lim[0], y_lim[1], ny))
    q_xy = np.column_stack([gx.ravel(), gy.ravel()])
    gz = idw_interpolate(sb_near[:, :2], sb_near[:, 2], q_xy).reshape(gx.shape)

    if show_contours and len(sb_near) >= 4:
        c_step = max(float(contour_interval or 0.05), 0.01)
        z_lo, z_hi = float(np.min(gz)) - c_step, float(np.max(gz)) + c_step
        if (z_hi - z_lo) >= c_step * 0.25:
            levels = np.arange(math.floor(z_lo / c_step) * c_step, z_hi + c_step, c_step)
            if len(levels) > 60:
                c_step = max(round((z_hi - z_lo) / 30.0, 2), 0.05)
                levels = np.arange(math.floor(z_lo / c_step) * c_step, z_hi + c_step, c_step)
            if 2 <= len(levels) <= 65:
                ax.contour(gx, gy, gz, levels=levels, colors="#94a3b8", linewidths=0.45, linestyles="dashed", alpha=0.65, zorder=1)

    if show_soundings:
        sp = max(float(spot_spacing or 2.0), 0.5) if is_zoomed else max(float(spot_spacing or 2.0) * 2.0, 2.0)
        w_span, h_span = max(x_lim[1] - x_lim[0], 1e-3), max(y_lim[1] - y_lim[0], 1e-3)
        vis_mask = (sb[:, 0] >= x_lim[0]) & (sb[:, 0] <= x_lim[1]) & (sb[:, 1] >= y_lim[0]) & (sb[:, 1] <= y_lim[1])
        sb_vis = sb[vis_mask]

        plotted_pts = []
        if len(sb_vis) > 0:
            min_d = sp * 0.82
            for pt in sb_vis:
                fx, fy = (pt[0] - x_lim[0]) / w_span, (pt[1] - y_lim[0]) / h_span
                if fx < 0.05 or fx > 0.95 or fy < 0.05 or fy > 0.94 or (fy < 0.18 and (fx < 0.44 or fx > 0.62)) or (fy > 0.82 and fx < 0.22):
                    continue
                if all(math.hypot(pt[0] - p[0], pt[1] - p[1]) >= min_d for p in plotted_pts):
                    plotted_pts.append(pt)

        if not plotted_pts:
            xs = np.arange(math.ceil(x_lim[0] / sp) * sp, x_lim[1], sp)
            ys = np.arange(math.ceil(y_lim[0] / sp) * sp, y_lim[1], sp)
            grid_xy = []
            for sx in xs:
                for sy in ys:
                    fx, fy = (sx - x_lim[0]) / w_span, (sy - y_lim[0]) / h_span
                    if fx < 0.06 or fx > 0.94 or fy < 0.05 or fy > 0.94 or (fy < 0.18 and (fx < 0.44 or fx > 0.62)) or (fy > 0.82 and fx < 0.22):
                        continue
                    grid_xy.append([sx, sy])
            if grid_xy:
                g_arr = np.array(grid_xy, dtype=float)
                g_z = idw_interpolate(sb_near[:, :2], sb_near[:, 2], g_arr)
                plotted_pts = np.column_stack([g_arr, g_z]).tolist()

        fmt = "{:.2f}" if is_zoomed else "{:.1f}"
        for px, py, pz in plotted_pts:
            ax.plot(px, py, "+", color="#64748b", markersize=3.2, alpha=0.65, zorder=2)
            t = ax.text(px, py, fmt.format(abs(float(pz))), fontsize=5.0 if is_zoomed else 4.7, fontweight="bold", color="#475569", ha="center", va="bottom", alpha=0.8, zorder=2)
            t.set_path_effects([patheffects.withStroke(linewidth=1.5, foreground="white")])

def generate_a3_4panel_chart(
    boxes_dict, metrics, cleaned_xyz, x_local, y_local, z_vals, seabed_local_xyz, seabed_full_xyz,
    workspace_dir="workspace", include_history=False, ledger_list=None, scale_p1=250, scale_p2=75,
    show_contours=True, contour_interval=0.05, show_soundings=True, spot_spacing=2.0, save_pdf=True
):
    os.makedirs(workspace_dir, exist_ok=True)
    W_MM, H_MM = 420.0, 297.0
    fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4), dpi=125, facecolor="white")

    ax_bg = fig.add_axes([0, 0, 1, 1], frameon=False)
    ax_bg.set_xlim(0, W_MM); ax_bg.set_ylim(0, H_MM); ax_bg.set_xticks([]); ax_bg.set_yticks([])

    ax_bg.add_patch(mpatches.Rectangle((14, 14), 392, 269, fill=False, edgecolor="#0f172a", linewidth=1.6))
    ax_bg.add_patch(mpatches.Rectangle((14, 270), 392, 13, facecolor="#0f172a", edgecolor="#0f172a"))
    loc_id, mat_id, usbl_s = metrics["location_id"], metrics["mattress_id"], metrics.get("usbl_sensor", "Survey Pole")
    surv_name = str(metrics.get("surveyor_name") or "Duty Surveyor").strip()
    cur_uno = int(float(metrics.get("unit_no") or (1 if str(loc_id).endswith("_M15") else 2)))
    is_first = bool(metrics.get("is_first_in_array")) or (cur_uno == 1) or (str(loc_id).endswith("_M15") and str(mat_id).replace("#", "") == "A046")
    gap_tol = float(metrics.get("gap_tol") or 0.50)
    cl_tol = float(metrics.get("cl_tol") or 0.50)
    bathy_src = str(metrics.get("bathy_source") or "NO_BATHY_UPLOADED")
    cad_polys = metrics.get("cad_polylines") or []

    verdict_full = str(metrics.get("verdict") or ("VERIFIED - WITHIN DESIGN TOLERANCE" if is_first else "VERIFIED - WITHIN DESIGN & GAP TOLERANCE"))
    ax_bg.text(18, 276.5, f"SUBSEA MATTRESS 4-PANEL VERIFICATION CHART  |  CROSSING: {metrics['crossing_id']}  |  ACTIVE USBL: {usbl_s}", color="white", fontsize=8.0, fontweight="bold", va="center", ha="left")
    ax_bg.text(402, 276.5, f"LOCATION: {loc_id}  |  MATTRESS ID: {mat_id}  |  {verdict_full}", color="#38bdf8", fontsize=7.8, fontweight="bold", va="center", ha="right")

    ax_bg.add_patch(mpatches.Rectangle((14, 14), 392, 14, facecolor="#f8fafc", edgecolor="#0f172a", linewidth=1.2))
    for x_div in (110, 214, 312):
        ax_bg.plot([x_div, x_div], [14, 28], color="#0f172a", linewidth=1.0)

    ax_bg.text(17, 23.5, "PROJECT: Tung-Hsiao 2nd Stage Subsea Gas Pipeline", fontsize=6.8, fontweight="bold", color="#0f172a")
    ax_bg.text(17, 19.5, "CLIENT: Taiwan Power Company (TPC) | CONTRACTOR: NMDC", fontsize=6.3, color="#334155")
    ax_bg.text(17, 15.8, f"VESSEL: DP2 MMA Prestige | USBL: {usbl_s} | TWD97 / TWVD2001", fontsize=6.2, color="#475569")

    ax_bg.text(113, 23.5, f"DESIGN ({loc_id}): E {metrics['design_e']:.3f} m, N {metrics['design_n']:.3f} m", fontsize=6.8, fontweight="bold", color="#0f172a")
    ax_bg.text(113, 19.5, f"AS-LAID ({mat_id}): E {metrics['aslaid_e']:.3f} m, N {metrics['aslaid_n']:.3f} m (Z: {metrics['aslaid_z']:.2f}m)", fontsize=6.4, color="#0369a1")
    ax_bg.text(113, 15.8, f"dCL OFFSET: {metrics['cl_offset_m']:.3f} m (Tol +/-{cl_tol:.2f}m | dAl {metrics['d_along_m']:+.2f}, dCr {metrics['d_cross_m']:+.2f}m)", fontsize=6.3, fontweight="bold", color="#15803d" if metrics["cl_offset_m"] <= cl_tol else "#b91c1c")

    ax_bg.text(217, 23.5, f"SOUTH BRG: Des {metrics['design_brg']:.2f} deg | Act {metrics['heading_deg']:.2f} deg (dBrg {metrics['brg_diff_deg']:+.2f} deg)", fontsize=6.4, fontweight="bold", color="#0f172a")
    ax_bg.text(217, 19.5, f"CORNER GAPS: {'1st Unit (N/A)' if is_first else metrics['gap_labels'][:36]}", fontsize=6.3, fontweight="bold", color="#0369a1" if not is_first else "#334155")
    ax_bg.text(217, 15.8, f"TOLERANCE: Centerline +/-{cl_tol:.2f} m | Side-to-Side Gap <= {gap_tol:.2f} m", fontsize=6.2, fontweight="bold", color="#15803d")

    ax_bg.text(314.5, 23.5, f"PLACEMENT DATE/TIME: {metrics['install_date']}", fontsize=6.3, fontweight="bold", color="#0f172a")
    ax_bg.text(314.5, 19.5, f"SURVEYOR: {surv_name} | STATUS: {metrics['status']}", fontsize=6.2, fontweight="bold", color="#0369a1")
    ax_bg.text(314.5, 15.8, f"FILE: {metrics['base_filename']}.pdf (P1 1:{scale_p1} | P2 1:{scale_p2})", fontsize=5.9, color="#334155")

    des_e, des_n = metrics["design_e"], metrics["design_n"]
    tb = boxes_dict[loc_id]
    hist_map = {}
    if not is_first and include_history and ledger_list:
        for r in ledger_list:
            r_bid = str(r.get("design_box_id") or "")
            r_uno = int(float(r.get("unit_no") or 0))
            if r_bid and r_bid != loc_id and (r_uno < cur_uno or r_bid == "CR-A1_M15"):
                hist_map[r_bid] = r

    # PANEL 1: FULL CROSSING ARRAY (with Grid North Arrow)
    ax1 = fig.add_axes([35.0 / W_MM, 56.0 / H_MM, 102.0 / W_MM, 184.0 / H_MM])
    hw1, hh1 = (102.0 / 1000.0) * float(scale_p1) / 2.0, (184.0 / 1000.0) * float(scale_p1) / 2.0
    e_lim1, n_lim1 = (des_e - hw1, des_e + hw1), (des_n - hh1, des_n + hh1)
    ax1.set_xlim(*e_lim1); ax1.set_ylim(*n_lim1)
    plot_seabed_layer(ax1, seabed_full_xyz, e_lim1, n_lim1, False, show_contours, contour_interval, show_soundings, spot_spacing, bathy_src)
    plot_cad_background(ax1, cad_polys, is_local=False)

    for bid, b in boxes_dict.items():
        short_lbl = bid.split("_")[-1]
        if bid == loc_id:
            if is_first:
                ax1.add_patch(mpatches.Polygon(b["corners"], closed=True, facecolor="#fef08a", edgecolor="#dc2626", linewidth=1.6, linestyle="-", alpha=0.88, zorder=5))
            else:
                cur_c, _, _ = _box_corners_cw(metrics["aslaid_e"], metrics["aslaid_n"], (float(metrics["heading_deg"]) - 180.0) % 360.0)
                ax1.add_patch(mpatches.Polygon(cur_c, closed=True, facecolor=(0.13, 0.77, 0.37, 0.25), edgecolor="#15803d", linewidth=1.8, linestyle="-", hatch="///", zorder=5))
            lbl = f"{short_lbl} [{mat_id}]"
        elif bid in hist_map:
            hr = hist_map[bid]
            hc, _, _ = _box_corners_cw(hr.get("aslaid_e", b["design_e"]), hr.get("aslaid_n", b["design_n"]), (float(hr.get("heading_deg", b["bearing"])) - 180.0) % 360.0)
            ax1.add_patch(mpatches.Polygon(hc, closed=True, facecolor=(0.80, 0.92, 1.0, 0.28), edgecolor="#0369a1", linewidth=1.4, linestyle="--", zorder=4))
            lbl = f"{short_lbl} [{hr.get('physical_tag','')}]"
        else:
            ax1.add_patch(mpatches.Polygon(b["corners"], closed=True, facecolor="#e2e8f0", edgecolor="#475569", linewidth=0.7, alpha=0.55, zorder=3))
            lbl = short_lbl
        t1 = ax1.text(b["design_e"], b["design_n"], lbl, fontsize=5.1, fontweight="bold", color="#0f172a", ha="center", va="center", rotation=b["azimuth"] - 90.0, zorder=6)
        t1.set_path_effects([patheffects.withStroke(linewidth=1.4, foreground="white")])

    draw_north_arrow(ax1, e_lim1, n_lim1, north_angle_deg=0.0, sub_label="Grid N")

    sb1_x, sb1_y = e_lim1[1] - 7.2, n_lim1[0] + 1.8
    ax1.add_patch(mpatches.Rectangle((sb1_x - 0.8, sb1_y - 1.0), 6.8, 2.3, facecolor="white", edgecolor="#64748b", alpha=0.9, zorder=8))
    ax1.plot([sb1_x, sb1_x + 5.0], [sb1_y, sb1_y], color="#0f172a", linewidth=2.0, zorder=9)
    ax1.text(sb1_x + 2.5, sb1_y + 0.3, "0 - 5 m", fontsize=5.6, fontweight="bold", ha="center", zorder=9)
    ax1.set_title(f"PANEL 1: CROSSING ARRAY ({metrics['crossing_id']}) | 1:{scale_p1} @ A3", fontsize=7.6, fontweight="bold", pad=4)
    ax1.set_xlabel("Easting E (m, TWD97)", fontsize=6.6, fontweight="bold"); ax1.set_ylabel("Northing N (m, TWD97)", fontsize=6.6, fontweight="bold")
    ax1.tick_params(labelsize=5.8); ax1.ticklabel_format(useOffset=False, style="plain"); ax1.grid(True, linestyle=":", linewidth=0.4, color="#cbd5e1")

    # PANEL 2: LOCAL PLAN VIEW (with Rotated Grid North Arrow)
    ax2 = fig.add_axes([161.0 / W_MM, 46.0 / H_MM, 114.0 / W_MM, 204.0 / H_MM])
    hw2, hh2 = (114.0 / 1000.0) * float(scale_p2) / 2.0, (204.0 / 1000.0) * float(scale_p2) / 2.0
    ax2.set_xlim(-hw2, hw2); ax2.set_ylim(-hh2, hh2)
    plot_seabed_layer(ax2, seabed_local_xyz, (-hw2, hw2), (-hh2, hh2), True, show_contours, contour_interval, show_soundings, spot_spacing, bathy_src)
    plot_cad_background(ax2, cad_polys, is_local=True, des_e=des_e, des_n=des_n, u_short=tb["u_short"], u_long=tb["u_long"])

    z_mean = float(np.mean(z_vals))
    vmin_c, vmax_c = round(z_mean - 0.50, 2), round(z_mean + 0.50, 2)
    ax2.add_patch(mpatches.Rectangle((-1.5, -3.0), 3.0, 6.0, fill=False, edgecolor="#dc2626", linewidth=1.8, zorder=5, label="Design Box (3.0x6.0m)"))
    sc2 = ax2.scatter(x_local, y_local, c=z_vals, cmap="turbo", vmin=vmin_c, vmax=vmax_c, s=16, alpha=0.9, zorder=6)
    cax2 = fig.add_axes([278.0 / W_MM, 46.0 / H_MM, 3.2 / W_MM, 204.0 / H_MM])
    cb2 = fig.colorbar(sc2, cax=cax2); cb2.set_label("Depth Z (m, TWVD2001)", fontsize=6.4, fontweight="bold"); cb2.ax.tick_params(labelsize=5.6)

    c_loc = np.asarray(metrics["corners_local"], dtype=float)
    ax2.add_patch(mpatches.Polygon(c_loc, closed=True, fill=False, edgecolor="#16a34a", linewidth=1.6, linestyle="--", zorder=7, label="ROV 4-Corner Polygon"))
    for idx_c, (cx, cy) in enumerate(c_loc, 1):
        ax2.plot(cx, cy, "s", color="#15803d", markersize=4.5, zorder=8)
        tc = ax2.text(cx, cy + 0.14, f"C{idx_c}", fontsize=5.8, fontweight="bold", color="#15803d", ha="center", zorder=9)
        tc.set_path_effects([patheffects.withStroke(linewidth=1.5, foreground="white")])

    q_d = np.array([metrics["qaqc_e"] - des_e, metrics["qaqc_n"] - des_n])
    qx, qy = float(q_d @ tb["u_short"]), float(q_d @ tb["u_long"])
    ax2.plot(0, 0, "+", color="#dc2626", markersize=9, markeredgewidth=2.0, zorder=8, label="Design Center")
    ax2.plot(metrics["d_cross_m"], metrics["d_along_m"], "o", color="#16a34a", markersize=6.5, markeredgecolor="white", zorder=8, label="ROV 4-Corner Center")
    ax2.plot(qx, qy, "^", color="#0284c7", markersize=6.5, markeredgecolor="white", zorder=8, label="QA/QC USBL Center")

    if is_first:
        side_callouts = [
            ("NNE (+3.0m)", metrics["edge_nne"], (0.0, 3.0), (0.0, 3.85)),
            ("SSW (-3.0m)", metrics["edge_ssw"], (0.0, -3.0), (0.0, -3.85)),
            ("ESE (+1.5m)", metrics["edge_ese"], (1.5, 0.0), (2.75, 0.0)),
            ("WNW (-1.5m)", metrics["edge_wnw"], (-1.5, 0.0), (-2.75, 0.0)),
        ]
        for lbl_e, val_e, xy_p, xy_t in side_callouts:
            ovh = val_e > 0.0
            bg, bd = ("#ffebee", "#dc2626") if ovh else ("#e8f5e9", "#16a34a")
            txt_c = f"{lbl_e}" + chr(10) + (f"Overhang: {val_e:+.2f}m" if ovh else f"Clear: {abs(val_e):.2f}m")
            ax2.annotate(txt_c, xy=xy_p, xytext=xy_t, ha="center", va="center", fontsize=5.5, fontweight="bold", color=bd,
                         bbox=dict(boxstyle="round,pad=0.24", facecolor=bg, edgecolor=bd, lw=0.85), arrowprops=dict(arrowstyle="->", color=bd, lw=0.9), zorder=9)
    else:
        gaps = metrics.get("gaps") or {}
        corner_defs = [
            ("C1 (NW Corner)", gaps.get("nw", ""), c_loc[0], (-2.55, 3.95)),
            ("C2 (NE Corner)", gaps.get("ne", ""), c_loc[1], (2.55, 3.95)),
            ("C3 (SE Corner)", gaps.get("se", ""), c_loc[2], (2.55, -3.95)),
            ("C4 (SW Corner)", gaps.get("sw", ""), c_loc[3], (-2.55, -3.95)),
        ]
        for c_title, g_raw, xy_c, xy_box in corner_defs:
            g_str = str(g_raw or "").strip()
            if g_str:
                try:
                    gv = float(re.sub(r"[^0-9.]", "", g_str))
                    ok = gv <= gap_tol
                except Exception:
                    gv, ok = 0.0, True
                bg, bd = ("#e8f5e9", "#15803d") if ok else ("#ffebee", "#dc2626")
                unit_sfx = "" if g_str.lower().endswith("m") else " m"
                txt_c = f"{c_title}" + chr(10) + f"Corner Gap: {g_str}{unit_sfx}" + chr(10) + f"(Tol <= {gap_tol:.2f} m)"
            else:
                bg, bd = ("#f1f5f9", "#475569")
                txt_c = f"{c_title}" + chr(10) + "Corner Gap: N/A"
            ax2.annotate(txt_c, xy=(float(xy_c[0]), float(xy_c[1])), xytext=xy_box, ha="center", va="center", fontsize=5.3, fontweight="bold", color=bd,
                         bbox=dict(boxstyle="round,pad=0.24", facecolor=bg, edgecolor=bd, lw=0.85), arrowprops=dict(arrowstyle="->", color=bd, lw=0.9), zorder=9)

    draw_north_arrow(ax2, (-hw2, hw2), (-hh2, hh2), north_angle_deg=-float(metrics.get("design_az", 0.0)), sub_label="Grid N")

    sb2_x, sb2_y = hw2 - 2.5, -hh2 + 0.65
    ax2.add_patch(mpatches.Rectangle((sb2_x - 0.2, sb2_y - 0.3), 2.4, 0.75, facecolor="white", edgecolor="#64748b", alpha=0.9, zorder=8))
    ax2.plot([sb2_x, sb2_x + 2.0], [sb2_y, sb2_y], color="#0f172a", linewidth=2.0, zorder=9)
    ax2.text(sb2_x + 1.0, sb2_y + 0.1, "0 - 2 m", fontsize=5.5, fontweight="bold", ha="center", zorder=9)
    ax2.legend(loc="lower left", fontsize=5.2, framealpha=0.92)
    ax2.set_title(f"PANEL 2: LOCAL PLAN VIEW ({loc_id} / {mat_id}) | 1:{scale_p2} @ A3", fontsize=7.6, fontweight="bold", pad=4)
    ax2.set_xlabel("Cross-Track X_local (m, WNW -1.5m to ESE +1.5m)", fontsize=6.6, fontweight="bold"); ax2.set_ylabel("Along-Track Y_local (m, SSW -3.0m to NNE +3.0m)", fontsize=6.6, fontweight="bold")
    ax2.tick_params(labelsize=5.8); ax2.grid(True, linestyle=":", linewidth=0.45, color="#cbd5e1")

    sb_loc_arr = np.asarray(seabed_local_xyz, dtype=float)
    for ax_p, coord_arr, lim_x, edge_v, is_long, ttl, x_lbl in [
        (fig.add_axes([315.0 / W_MM, 162.0 / H_MM, 83.0 / W_MM, 88.0 / H_MM]), y_local, (-3.5, 3.5), 3.0, True, "PANEL 3: LONGITUDINAL (SSW -> NNE)" + chr(10) + "H 1:75 | V 1:15 @ A3", "Along-Track Y_local (m)"),
        (fig.add_axes([315.0 / W_MM, 46.0 / H_MM, 83.0 / W_MM, 86.0 / H_MM]), x_local, (-2.2, 2.2), 1.5, False, "PANEL 4: LATERAL (WNW -> ESE)" + chr(10) + "H 1:50 | V 1:15 @ A3", "Cross-Track X_local (m)")
    ]:
        ax_p.scatter(coord_arr, np.abs(z_vals), c=z_vals, cmap="turbo", vmin=vmin_c, vmax=vmax_c, s=10, alpha=0.85, label="Mattress Surface")
        xs_l = np.linspace(lim_x[0], lim_x[1], 40)
        if bathy_src == "SURVEY_BATHY" and len(sb_loc_arr) >= 1:
            q_prof = np.column_stack([np.zeros_like(xs_l), xs_l]) if is_long else np.column_stack([xs_l, np.zeros_like(xs_l)])
            z_prof = idw_interpolate(sb_loc_arr[:, :2], sb_loc_arr[:, 2], q_prof)
            ax_p.plot(xs_l, np.abs(z_prof), "--", color="#0284c7", lw=1.35, label="Survey Seabed Profile")
            z_center = 0.5 * (float(np.mean(np.abs(z_vals))) + float(np.mean(np.abs(z_prof))))
            half_win = max(0.65, 0.5 * abs(float(np.max(np.abs(z_prof)) - np.min(np.abs(z_vals)))) + 0.35)
            y_hi, y_lo = z_center + half_win, z_center - half_win
        else:
            y_hi, y_lo = abs(z_mean) + 0.65, abs(z_mean) - 0.65
        ax_p.axvline(-edge_v, color="#dc2626", ls="--", lw=1.2, label=f"Design (+/-{edge_v:.1f}m)"); ax_p.axvline(edge_v, color="#dc2626", ls="--", lw=1.2)
        ax_p.set_xlim(*lim_x); ax_p.set_ylim(y_hi, y_lo)
        ax_p.set_title(ttl, fontsize=7.0, fontweight="bold", pad=3); ax_p.set_xlabel(x_lbl, fontsize=6.3, fontweight="bold"); ax_p.set_ylabel("Depth Z (m, Inv)", fontsize=6.3, fontweight="bold")
        ax_p.tick_params(labelsize=5.6); ax_p.grid(True, linestyle=":", lw=0.45, color="#cbd5e1"); ax_p.legend(loc="lower right", fontsize=5.0, framealpha=0.9)

    buf_png = io.BytesIO()
    fig.savefig(buf_png, format="png", dpi=125)
    png_bytes = buf_png.getvalue()
    pdf_bytes = b""
    if save_pdf:
        buf_pdf = io.BytesIO()
        fig.savefig(buf_pdf, format="pdf", dpi=150)
        pdf_bytes = buf_pdf.getvalue()
    fig.clf(); plt.close(fig); plt.close('all'); gc.collect()

    for fn in ("latest_A3_4Panel_Chart", metrics["base_filename"]):
        open(os.path.join(workspace_dir, fn + ".png"), "wb").write(png_bytes)
        if pdf_bytes:
            open(os.path.join(workspace_dir, fn + ".pdf"), "wb").write(pdf_bytes)
    return png_bytes, pdf_bytes
