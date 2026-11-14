import os, re, glob, ast, subprocess

# === 1. UPDATE mti_4panel_a3.py FOR OPTION A (CR-A3 & CR-B3 TWIN 1:250 STRIPS P1A + P1B) ===
a3_path = "mti_4panel_a3.py"
if not os.path.exists(a3_path):
    raise SystemExit("mti_4panel_a3.py not found! Run inside your DAR project folder.")

a3 = open(a3_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")

new_north_fn = """def draw_north_arrow(ax, x_lim, y_lim, north_angle_deg=0.0, sub_label="Grid N"):
    w = float(x_lim[1] - x_lim[0])
    h = float(y_lim[1] - y_lim[0])
    if w > 1.5 * h:
        r = 0.068 * h
        cx = float(x_lim[0]) + 0.032 * w
        cy = float(y_lim[1]) - 0.285 * h
        fs_n, fs_sub = 5.8, 4.2
    else:
        r = 0.046 * w
        cx = float(x_lim[0]) + 0.105 * w
        cy = float(y_lim[1]) - 0.082 * h
        fs_n, fs_sub = 6.8, 4.6

    bg_circle = mpatches.Circle((cx, cy), r * 1.38, facecolor="white", edgecolor="#475569", linewidth=0.8, alpha=0.92, zorder=10, clip_on=True)
    ax.add_patch(bg_circle)
    inner_ring = mpatches.Circle((cx, cy), r * 1.12, fill=False, edgecolor="#94a3b8", linewidth=0.45, linestyle=":", zorder=10, clip_on=True)
    ax.add_patch(inner_ring)

    rad = math.radians(float(north_angle_deg))
    ux, uy = math.sin(rad), math.cos(rad)
    px, py = math.cos(rad), -math.sin(rad)

    tip = (cx + ux * r, cy + uy * r)
    tail_c = (cx - ux * (r * 0.35), cy - uy * (r * 0.35))
    left_w = (cx - ux * (r * 0.65) - px * (r * 0.42), cy - uy * (r * 0.65) - py * (r * 0.42))
    right_w = (cx - ux * (r * 0.65) + px * (r * 0.42), cy - uy * (r * 0.65) + py * (r * 0.42))

    ax.add_patch(mpatches.Polygon([tip, left_w, tail_c], closed=True, facecolor="#0f172a", edgecolor="#0f172a", linewidth=0.7, zorder=11, clip_on=True))
    ax.add_patch(mpatches.Polygon([tip, right_w, tail_c], closed=True, facecolor="white", edgecolor="#0f172a", linewidth=0.7, zorder=11, clip_on=True))

    nx_lbl = cx + ux * (r * 1.72)
    ny_lbl = cy + uy * (r * 1.72)
    t_n = ax.text(nx_lbl, ny_lbl, "N", fontsize=fs_n, fontweight="bold", color="#0f172a", ha="center", va="center", zorder=12, clip_on=True)
    t_n.set_path_effects([patheffects.withStroke(linewidth=1.8, foreground="white")])

    if sub_label:
        t_sub = ax.text(cx, cy - r * 1.65, sub_label, fontsize=fs_sub, fontweight="bold", color="#334155", ha="center", va="top", zorder=12, clip_on=True)
        t_sub.set_path_effects([patheffects.withStroke(linewidth=1.5, foreground="white")])"""

a3, n_na = re.subn(
    r'def draw_north_arrow\(ax, x_lim, y_lim, north_angle_deg=0\.0, sub_label="Grid N"\):.*?(?=\n\ndef plot_cad_background)',
    lambda _m: new_north_fn,
    a3, count=1, flags=re.S
)
if not n_na:
    raise SystemExit("Could not locate draw_north_arrow() in mti_4panel_a3.py!")

dual_mode_panels = """    xing_up = str(metrics.get("crossing_id") or "").strip().upper()
    is_split_a3b3 = xing_up.startswith("CR-A3") or xing_up.startswith("CR-B3")

    def _m_idx(bid_str):
        m = re.search(r"_M(\\d+)$", str(bid_str or "").strip(), re.I)
        return int(m.group(1)) if m else 999

    if is_split_a3b3:
        sorted_bids = sorted(boxes_dict.keys(), key=_m_idx)
        seg_a_ids = [k for k in sorted_bids if _m_idx(k) <= 18] or sorted_bids[:18]
        seg_b_ids = [k for k in sorted_bids if _m_idx(k) > 18] or sorted_bids[18:]
        ref_b = boxes_dict[sorted_bids[0]]
        strip_az = float(ref_b["azimuth"])
        u_s, u_l = ref_b["u_short"], ref_b["u_long"]

        P1S_W, P1S_H = 238.0, 56.0
        hw_s = (P1S_W / 1000.0) * float(scale_p1) / 2.0
        hh_s = (P1S_H / 1000.0) * float(scale_p1) / 2.0
        metrics["split_p1_viewports"] = {}

        for p_tag, seg_ids, y_mm in [
            ("1A", seg_a_ids, 202.0),
            ("1B", seg_b_ids, 131.0),
        ]:
            if not seg_ids:
                continue
            ax_s = fig.add_axes([26.0 / W_MM, y_mm / H_MM, P1S_W / W_MM, P1S_H / H_MM])
            seg_c_world = np.vstack([boxes_dict[k]["corners"] for k in seg_ids])
            c_world_0 = np.mean(seg_c_world, axis=0)
            d0 = seg_c_world - c_world_0
            sx_mid = 0.5 * (float(np.min(d0 @ u_s)) + float(np.max(d0 @ u_s)))
            sy_mid = 0.5 * (float(np.min(d0 @ u_l)) + float(np.max(d0 @ u_l)))
            seg_ce = float(c_world_0[0] + sx_mid * u_s[0] + sy_mid * u_l[0])
            seg_cn = float(c_world_0[1] + sx_mid * u_s[1] + sy_mid * u_l[1])
            metrics["split_p1_viewports"][f"PANEL {p_tag}"] = {"ce": round(seg_ce, 3), "cn": round(seg_cn, 3), "az": round(strip_az, 3)}

            ax_s.set_xlim(-hw_s, hw_s); ax_s.set_ylim(-hh_s, hh_s)
            if len(seabed_full_xyz) > 0:
                sb_d_s = seabed_full_xyz[:, :2] - np.array([seg_ce, seg_cn])
                sb_strip = np.column_stack([sb_d_s @ u_s, sb_d_s @ u_l, seabed_full_xyz[:, 2]])
                plot_seabed_layer(ax_s, sb_strip, (-hw_s, hw_s), (-hh_s, hh_s), False, show_contours, contour_interval, show_soundings, spot_spacing, bathy_src)
            plot_cad_background(ax_s, cad_polys, is_local=True, des_e=seg_ce, des_n=seg_cn, u_short=u_s, u_long=u_l)

            for bid in sorted_bids:
                b = boxes_dict[bid]
                short_lbl = bid.split("_")[-1]
                if bid == loc_id:
                    if is_first:
                        w_pts = b["corners"]
                        fc_p, ec_p, lw_p, ls_p, ht_p, al_p, zo_p = "#fef08a", "#dc2626", 1.6, "-", None, 0.88, 5
                    else:
                        w_pts, _, _ = _box_corners_cw(metrics["aslaid_e"], metrics["aslaid_n"], (float(metrics["heading_deg"]) - 180.0) % 360.0)
                        fc_p, ec_p, lw_p, ls_p, ht_p, al_p, zo_p = (0.13, 0.77, 0.37, 0.30), "#15803d", 1.7, "-", "///", None, 5
                    lbl = f"{short_lbl} [{mat_id}]"
                elif bid in hist_map:
                    hr = hist_map[bid]
                    w_pts, _, _ = _box_corners_cw(hr.get("aslaid_e", b["design_e"]), hr.get("aslaid_n", b["design_n"]), (float(hr.get("heading_deg", b["bearing"])) - 180.0) % 360.0)
                    fc_p, ec_p, lw_p, ls_p, ht_p, al_p, zo_p = (0.80, 0.92, 1.0, 0.32), "#0369a1", 1.3, "--", None, None, 4
                    lbl = f"{short_lbl} [{hr.get('physical_tag','')}]"
                else:
                    w_pts = b["corners"]
                    is_in_seg = (bid in seg_ids)
                    fc_p, ec_p, lw_p, ls_p, ht_p, al_p, zo_p = ("#e2e8f0", "#475569", 0.75, "-", None, 0.60 if is_in_seg else 0.22, 3)
                    lbl = short_lbl

                rel_c = np.asarray(w_pts, dtype=float) - np.array([seg_ce, seg_cn])
                loc_pts = np.column_stack([rel_c @ u_s, rel_c @ u_l])
                kw_p = dict(closed=True, facecolor=fc_p, edgecolor=ec_p, linewidth=lw_p, linestyle=ls_p, zorder=zo_p, clip_on=True)
                if ht_p: kw_p["hatch"] = ht_p
                if al_p is not None: kw_p["alpha"] = al_p
                poly_p = mpatches.Polygon(loc_pts, **kw_p)
                ax_s.add_patch(poly_p); poly_p.set_clip_path(ax_s.patch)

                bx_l = float((b["design_e"] - seg_ce) * u_s[0] + (b["design_n"] - seg_cn) * u_s[1])
                by_l = float((b["design_e"] - seg_ce) * u_l[0] + (b["design_n"] - seg_cn) * u_l[1])
                if bid in seg_ids and (-hw_s + 1.0 <= bx_l <= hw_s - 1.0):
                    t_s = ax_s.text(bx_l, by_l, lbl, fontsize=4.8, fontweight="bold", color="#0f172a", ha="center", va="center", rotation=90.0, zorder=6, clip_on=True)
                    t_s.set_path_effects([patheffects.withStroke(linewidth=1.3, foreground="white")])
                    t_s.set_clip_path(ax_s.patch)

            draw_north_arrow(ax_s, (-hw_s, hw_s), (-hh_s, hh_s), north_angle_deg=-strip_az, sub_label="Grid N")
            sba_x, sba_y = hw_s - 6.2, -hh_s + 1.15
            ax_s.add_patch(mpatches.Rectangle((sba_x - 0.5, sba_y - 0.75), 6.0, 2.0, facecolor="white", edgecolor="#64748b", alpha=0.92, zorder=8, clip_on=True))
            ax_s.plot([sba_x, sba_x + 5.0], [sba_y, sba_y], color="#0f172a", linewidth=2.0, zorder=9, clip_on=True)
            ax_s.text(sba_x + 2.5, sba_y + 0.28, "0 - 5 m", fontsize=5.3, fontweight="bold", ha="center", zorder=9, clip_on=True)

            first_m, last_m = seg_ids[0].split("_")[-1], seg_ids[-1].split("_")[-1]
            half_lbl = "NW HALF" if p_tag == "1A" else "SE HALF"
            ax_s.set_title(f"PANEL {p_tag}: CROSSING ARRAY {half_lbl} ({metrics['crossing_id']}: {first_m} - {last_m}) | 1:{scale_p1} @ A3", fontsize=7.3, fontweight="bold", pad=3.5)
            ax_s.set_xlabel("Along-Crossing Array Offset (m, NW -> SE)", fontsize=6.1, fontweight="bold", labelpad=1.8)
            ax_s.set_ylabel("Local Y (m)", fontsize=6.1, fontweight="bold", labelpad=2.0)
            ax_s.tick_params(labelsize=5.4); ax_s.grid(True, linestyle=":", linewidth=0.4, color="#cbd5e1")

        p2_rect = [278.0 / W_MM, 41.0 / H_MM, 106.0 / W_MM, 217.0 / H_MM]
        p2_w_mm, p2_h_mm = 106.0, 217.0
        cax_rect = [386.8 / W_MM, 41.0 / H_MM, 3.2 / W_MM, 217.0 / H_MM]
        p3_rect = [46.0 / W_MM, 41.0 / H_MM, 58.1 / W_MM, 61.6 / H_MM]
        p4_rect = [162.0 / W_MM, 41.0 / H_MM, 58.1 / W_MM, 61.6 / H_MM]
    else:
        ax1 = fig.add_axes([33.0 / W_MM, 41.0 / H_MM, 128.0 / W_MM, 219.0 / H_MM])
        hw1, hh1 = (128.0 / 1000.0) * float(scale_p1) / 2.0, (219.0 / 1000.0) * float(scale_p1) / 2.0
        if metrics.get("group_center_e") is not None and metrics.get("group_center_n") is not None:
            p1_ce, p1_cn = float(metrics["group_center_e"]), float(metrics["group_center_n"])
        else:
            _all_c = np.vstack([b["corners"] for b in boxes_dict.values()])
            p1_ce = 0.5 * (float(np.min(_all_c[:, 0])) + float(np.max(_all_c[:, 0])))
            p1_cn = 0.5 * (float(np.min(_all_c[:, 1])) + float(np.max(_all_c[:, 1])))
        e_lim1, n_lim1 = (p1_ce - hw1, p1_ce + hw1), (p1_cn - hh1, p1_cn + hh1)
        ax1.set_xlim(*e_lim1); ax1.set_ylim(*n_lim1)
        plot_seabed_layer(ax1, seabed_full_xyz, e_lim1, n_lim1, False, show_contours, contour_interval, show_soundings, spot_spacing, bathy_src)
        plot_cad_background(ax1, cad_polys, is_local=False)

        w1_span, h1_span = max(e_lim1[1] - e_lim1[0], 1e-3), max(n_lim1[1] - n_lim1[0], 1e-3)
        for bid, b in boxes_dict.items():
            short_lbl = bid.split("_")[-1]
            if bid == loc_id:
                if is_first:
                    poly_p = mpatches.Polygon(b["corners"], closed=True, facecolor="#fef08a", edgecolor="#dc2626", linewidth=1.6, linestyle="-", alpha=0.88, zorder=5, clip_on=True)
                else:
                    cur_c, _, _ = _box_corners_cw(metrics["aslaid_e"], metrics["aslaid_n"], (float(metrics["heading_deg"]) - 180.0) % 360.0)
                    poly_p = mpatches.Polygon(cur_c, closed=True, facecolor=(0.13, 0.77, 0.37, 0.25), edgecolor="#15803d", linewidth=1.8, linestyle="-", hatch="///", zorder=5, clip_on=True)
                lbl = f"{short_lbl} [{mat_id}]"
            elif bid in hist_map:
                hr = hist_map[bid]
                hc, _, _ = _box_corners_cw(hr.get("aslaid_e", b["design_e"]), hr.get("aslaid_n", b["design_n"]), (float(hr.get("heading_deg", b["bearing"])) - 180.0) % 360.0)
                poly_p = mpatches.Polygon(hc, closed=True, facecolor=(0.80, 0.92, 1.0, 0.28), edgecolor="#0369a1", linewidth=1.4, linestyle="--", zorder=4, clip_on=True)
                lbl = f"{short_lbl} [{hr.get('physical_tag','')}]"
            else:
                poly_p = mpatches.Polygon(b["corners"], closed=True, facecolor="#e2e8f0", edgecolor="#475569", linewidth=0.7, alpha=0.55, zorder=3, clip_on=True)
                lbl = short_lbl
            ax1.add_patch(poly_p)
            poly_p.set_clip_path(ax1.patch)

            fx_b = (b["design_e"] - e_lim1[0]) / w1_span
            fy_b = (b["design_n"] - n_lim1[0]) / h1_span
            if 0.04 <= fx_b <= 0.96 and 0.04 <= fy_b <= 0.96:
                if not (fy_b > 0.84 and fx_b < 0.20) and not (fy_b < 0.12 and fx_b > 0.68):
                    t1 = ax1.text(b["design_e"], b["design_n"], lbl, fontsize=5.1, fontweight="bold", color="#0f172a", ha="center", va="center", rotation=b["azimuth"] - 90.0, zorder=6, clip_on=True)
                    t1.set_path_effects([patheffects.withStroke(linewidth=1.4, foreground="white")])
                    t1.set_clip_path(ax1.patch)

        draw_north_arrow(ax1, e_lim1, n_lim1, north_angle_deg=0.0, sub_label="Grid N")
        sb1_x, sb1_y = e_lim1[1] - 7.2, n_lim1[0] + 1.8
        ax1.add_patch(mpatches.Rectangle((sb1_x - 0.8, sb1_y - 1.0), 6.8, 2.3, facecolor="white", edgecolor="#64748b", alpha=0.9, zorder=8, clip_on=True))
        ax1.plot([sb1_x, sb1_x + 5.0], [sb1_y, sb1_y], color="#0f172a", linewidth=2.0, zorder=9, clip_on=True)
        ax1.text(sb1_x + 2.5, sb1_y + 0.3, "0 - 5 m", fontsize=5.6, fontweight="bold", ha="center", zorder=9, clip_on=True)
        ax1.set_title(f"PANEL 1: CROSSING ARRAY ({metrics['crossing_id']}) | 1:{scale_p1} @ A3", fontsize=7.6, fontweight="bold", pad=4)
        ax1.set_xlabel("Easting E (m, TWD97)", fontsize=6.6, fontweight="bold"); ax1.set_ylabel("Northing N (m, TWD97)", fontsize=6.6, fontweight="bold")
        ax1.tick_params(labelsize=5.8); ax1.ticklabel_format(useOffset=False, style="plain"); ax1.grid(True, linestyle=":", linewidth=0.4, color="#cbd5e1")

        p2_rect = [179.0 / W_MM, 41.0 / H_MM, 128.0 / W_MM, 219.0 / H_MM]
        p2_w_mm, p2_h_mm = 128.0, 219.0
        cax_rect = [309.8 / W_MM, 41.0 / H_MM, 3.2 / W_MM, 219.0 / H_MM]
        p3_rect = [341.9 / W_MM, 163.9 / H_MM, 58.1 / W_MM, 61.6 / H_MM]
        p4_rect = [341.9 / W_MM, 75.5 / H_MM, 58.1 / W_MM, 61.6 / H_MM]

    # PANEL 2: LOCAL PLAN VIEW (with Rotated Grid North Arrow)
    ax2 = fig.add_axes(p2_rect)
    hw2, hh2 = (p2_w_mm / 1000.0) * float(scale_p2) / 2.0, (p2_h_mm / 1000.0) * float(scale_p2) / 2.0"""

a3, n_dm = re.subn(
    r"    # PANEL 1: FULL CROSSING ARRAY.*?# PANEL 2: LOCAL PLAN VIEW[^\n]*\n\s*ax2 = fig\.add_axes\(\[[^\]]+\]\)\s*\n\s*hw2, hh2 = [^\n]+",
    lambda _m: dual_mode_panels,
    a3, count=1, flags=re.S
)
if not n_dm:
    a3, n_dm = re.subn(
        r"    xing_up = str\(metrics\.get\(\"crossing_id\"\) or \"\"\)\.strip\(\)\.upper\(\)\s*\n\s*is_split_a3b3 = .*?# PANEL 2: LOCAL PLAN VIEW[^\n]*\n\s*ax2 = fig\.add_axes\(p2_rect\)\s*\n\s*hw2, hh2 = [^\n]+",
        lambda _m: dual_mode_panels,
        a3, count=1, flags=re.S
    )
if not n_dm:
    raise SystemExit("Could not locate Panel 1/2 block in mti_4panel_a3.py!")

a3 = re.sub(r"cax2 = fig\.add_axes\((?:\[[^\]]+\]|cax_rect)\)", "cax2 = fig.add_axes(cax_rect)", a3, count=1)

p34_loop_block = """    for ax_p, coord_arr, lim_x, edge_v, is_long, ttl_top, x_lbl in [
        (fig.add_axes(p3_rect), y_local, (-3.486, 3.486), 3.0, True, "PANEL 3: LONGITUDINAL (SSW -> NNE)", "Along-Track Y_local (m)"),
        (fig.add_axes(p4_rect), x_local, (-3.486, 3.486), 1.5, False, "PANEL 4: LATERAL (WNW -> ESE)", "Cross-Track X_local (m)")
    ]:
        ax_p.scatter(coord_arr, z_vals, c=z_vals, cmap="turbo", vmin=vmin_c, vmax=vmax_c, s=9, alpha=0.85, label="Mattress Surface")
        xs_l = np.linspace(lim_x[0], lim_x[1], 40)
        if bathy_src == "SURVEY_BATHY" and len(sb_loc_arr) >= 1:
            q_prof = np.column_stack([np.zeros_like(xs_l), xs_l]) if is_long else np.column_stack([xs_l, np.zeros_like(xs_l)])
            z_prof = idw_interpolate(sb_loc_arr[:, :2], sb_loc_arr[:, 2], q_prof)
            ax_p.plot(xs_l, z_prof, "--", color="#0284c7", lw=1.25, label="Survey Seabed Profile")
            z_center = 0.5 * (float(np.mean(z_vals)) + float(np.mean(z_prof)))
            half_win = max(0.616, 0.5 * abs(float(np.max(z_prof) - np.min(z_vals))) + 0.32)
        else:
            z_center = z_mean
            half_win = 0.616
        v_sc_lbl = int(round((2.0 * half_win) / (61.6 / 1000.0)))
        ttl = ttl_top + chr(10) + f"H 1:120 | V 1:{v_sc_lbl} @ A3"
        if z_center <= 0:
            y_bottom, y_top = z_center - half_win, z_center + half_win
        else:
            y_bottom, y_top = z_center + half_win, z_center - half_win
        ax_p.axvline(-edge_v, color="#dc2626", ls="--", lw=1.1, label=f"Design (+/-{edge_v:.1f}m)"); ax_p.axvline(edge_v, color="#dc2626", ls="--", lw=1.1)
        ax_p.set_xlim(*lim_x); ax_p.set_ylim(y_bottom, y_top)
        ax_p.set_title(ttl, fontsize=6.5, fontweight="bold", pad=3); ax_p.set_xlabel(x_lbl, fontsize=5.9, fontweight="bold"); ax_p.set_ylabel("Depth Z (m, TWVD2001)", fontsize=5.9, fontweight="bold")
        ax_p.tick_params(labelsize=5.2); ax_p.grid(True, linestyle=":", lw=0.45, color="#cbd5e1"); ax_p.legend(loc="lower right", fontsize=4.6, framealpha=0.9)"""

a3, n_p34 = re.subn(
    r"    for ax_p, coord_arr, lim_x, edge_v, is_long, ttl(?:_top)?, x_lbl in \[.*?(?=\n\s*buf_png = io\.BytesIO\(\))",
    lambda _m: p34_loop_block,
    a3, count=1, flags=re.S
)
if not n_p34:
    raise SystemExit("Could not locate Panel 3/4 loop in mti_4panel_a3.py!")

ast.parse(a3)
open(a3_path, "w", encoding="utf-8").write(a3)
print("  -> Updated mti_4panel_a3.py (Option A Twin 1:250 Strips for CR-A3 & CR-B3, AST OK)")

# === 2. UPDATE mti_dxf_export.py SO PANEL 1A & PANEL 1B EXPORT AS LOCKED ROTATED TWD97 VIEWPORTS ===
dxf_path = "mti_dxf_export.py"
if os.path.exists(dxf_path):
    dxf_src = open(dxf_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    vp_split_code = """            is_twd97 = (50000.0 <= 0.5 * (x0 + x1) <= 500000.0 and 2000000.0 <= 0.5 * (y0 + y1) <= 3100000.0)
            is_p2_local = (native_4panel_metrics is not None and "PANEL 2" in ttl_up)
            split_vps = (native_4panel_metrics or {}).get("split_p1_viewports") or {}
            split_key = "PANEL 1A" if "PANEL 1A" in ttl_up else ("PANEL 1B" if "PANEL 1B" in ttl_up else "")"""

    if "split_p1_viewports" not in dxf_src:
        dxf_src = dxf_src.replace(
            '            is_twd97 = (50000.0 <= 0.5 * (x0 + x1) <= 500000.0 and 2000000.0 <= 0.5 * (y0 + y1) <= 3100000.0)\n            is_p2_local = (native_4panel_metrics is not None and "PANEL 2" in ttl_up)',
            vp_split_code,
            1
        )
        dxf_src = dxf_src.replace(
            "            elif is_p2_local:",
            """            elif split_key and split_key in split_vps:
                sv = split_vps[split_key]
                _add_locked_viewport(psp, doc, bb_mm, float(sv["ce"]), float(sv["cn"]), abs(y1 - y0), twist_deg=float(sv["az"]))
                _render_axes_chrome_and_texts_mm(psp, ax, px_to_mm, l_sheet, include_data_texts=False)
            elif is_p2_local:""",
            1
        )
    ast.parse(dxf_src)
    open(dxf_path, "w", encoding="utf-8").write(dxf_src)
    print("  -> Updated mti_dxf_export.py (Locked rotated TWD97 viewports for PANEL 1A & PANEL 1B, AST OK)")

# Purge cached workspace charts so CR-A3 / CR-B3 render Option A immediately
for f_stale in glob.glob(os.path.join("workspace", "*.pdf")) + glob.glob(os.path.join("workspace", "*.png")) + glob.glob(os.path.join("workspace", "*.dxf")) + glob.glob(os.path.join("workspace", "*_cache.json")):
    try: os.remove(f_stale)
    except Exception: pass

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti-a3): add Option A twin 1:250 fixed strip layout (P1A/P1B) for Crossings A3 and B3"], check=False)
print("\nOPTION A (CR-A3 & CR-B3) IMPLEMENTATION COMPLETE & PUSHED TO RENDER!")