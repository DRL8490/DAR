import os as _os; _os.environ.setdefault("EZDXF_DISABLE_C_EXT", "1")
import os, io, re, math
import numpy as np
import ezdxf
from ezdxf.enums import TextEntityAlignment
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.collections import Collection, PathCollection

def _rgb_tuple(mpl_color, fallback=(15, 23, 42)):
    try:
        if mpl_color is None or str(mpl_color).lower() == "none":
            return None
        r, g, b = mcolors.to_rgb(mpl_color)
        return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))
    except Exception:
        return fallback

def _ensure_styles_and_linetypes(doc):
    for name, ttf in (("MTI_SANS", "arial.ttf"), ("MTI_MONO", "consola.ttf")):
        if name not in doc.styles:
            try:
                doc.styles.add(name, font=ttf)
            except Exception:
                pass
    if "MTI_DASHED" not in doc.linetypes:
        try:
            doc.linetypes.add("MTI_DASHED", pattern=[3.0, 1.8, -1.2], description="Dashed __ _")
        except Exception:
            pass
    if "MTI_DOTTED" not in doc.linetypes:
        try:
            doc.linetypes.add("MTI_DOTTED", pattern=[1.2, 0.4, -0.8], description="Dotted . . .")
        except Exception:
            pass

def _ensure_layer(doc, name, rgb=(226, 232, 240), linetype="CONTINUOUS"):
    clean = re.sub(r"[^A-Za-z0-9_-]", "_", str(name or "0"))[:58] or "0"
    if clean not in doc.layers:
        lt = linetype if linetype in doc.linetypes else "CONTINUOUS"
        lyr = doc.layers.add(clean, dxfattribs={"linetype": lt})
        lyr.dxf.true_color = ezdxf.rgb2int(rgb)
    return clean

def _mpl_ls_to_dxf(ls):
    s = str(ls or "-").strip()
    if s in ("--", "dashed"):
        return "MTI_DASHED"
    if s in (":", "dotted", "-.", "dashdot"):
        return "MTI_DOTTED"
    return "CONTINUOUS"

def _add_solid_poly(space, pts_2d, rgb, layer_name):
    if rgb is None or len(pts_2d) < 3:
        return
    try:
        h = space.add_hatch(dxfattribs={"layer": layer_name})
        h.set_solid_fill(rgb=rgb)
        h.paths.add_polyline_path([(float(p[0]), float(p[1])) for p in pts_2d], is_closed=True)
    except Exception:
        pass

def _add_clean_text(space, text_str, x, y, cap_h, rgb=(15, 23, 42), ha="left", va="center", rot_deg=0.0, mono=False, layer="0"):
    raw = str(text_str or "").replace("\r", "")
    if not raw.strip():
        return
    lines = [ln for ln in raw.split("\n")]
    style_name = "MTI_MONO" if (mono and "MTI_MONO" in space.doc.styles) else ("MTI_SANS" if "MTI_SANS" in space.doc.styles else "Standard")
    h_map = {
        ("left", "top"): TextEntityAlignment.TOP_LEFT,
        ("center", "top"): TextEntityAlignment.TOP_CENTER,
        ("right", "top"): TextEntityAlignment.TOP_RIGHT,
        ("left", "center"): TextEntityAlignment.MIDDLE_LEFT,
        ("center", "center"): TextEntityAlignment.MIDDLE_CENTER,
        ("right", "center"): TextEntityAlignment.MIDDLE_RIGHT,
        ("left", "bottom"): TextEntityAlignment.BOTTOM_LEFT,
        ("center", "bottom"): TextEntityAlignment.BOTTOM_CENTER,
        ("right", "bottom"): TextEntityAlignment.BOTTOM_RIGHT,
        ("left", "baseline"): TextEntityAlignment.LEFT,
        ("center", "baseline"): TextEntityAlignment.CENTER,
        ("right", "baseline"): TextEntityAlignment.RIGHT,
    }
    ha_k = ha if ha in ("left", "center", "right") else "left"
    va_k = va if va in ("top", "center", "bottom", "baseline") else "center"
    align_enum = h_map.get((ha_k, va_k), TextEntityAlignment.MIDDLE_LEFT)

    line_step = cap_h * 1.48
    n_ln = len(lines)
    start_offset = 0.5 * (n_ln - 1) * line_step if va_k == "center" else (0.0 if va_k == "top" else (n_ln - 1) * line_step)
    rad = math.radians(float(rot_deg))
    nx_dir, ny_dir = math.sin(rad), -math.cos(rad)

    for idx, ln in enumerate(lines):
        if not ln.strip():
            continue
        dy_local = start_offset - idx * line_step
        px = float(x) - dy_local * nx_dir
        py = float(y) - dy_local * (-ny_dir) if abs(rot_deg) > 1e-3 else float(y) + dy_local
        t_ent = space.add_text(
            ln,
            dxfattribs={
                "layer": layer,
                "style": style_name,
                "height": max(0.35, float(cap_h)),
                "rotation": float(rot_deg),
                "width": 0.88,
                "true_color": ezdxf.rgb2int(rgb or (15, 23, 42)),
            }
        )
        t_ent.set_placement((px, py), align=align_enum)

def populate_4panel_modelspace(
    doc, boxes_dict, metrics, cleaned_xyz, seabed_full_xyz, cad_polys=None,
    ledger_list=None, raw_rov_store=None, show_contours=True, contour_interval=0.05,
    show_soundings=True, spot_spacing=2.0
):
    """Writes all real-world TWD97 / TWVD2001 (E, N, Z) survey & design entities to Model Space."""
    msp = doc.modelspace()
    l_cad = _ensure_layer(doc, "01_CAD_BACKGROUND", (148, 163, 184))
    l_cnt = _ensure_layer(doc, "02_BATHY_CONTOURS", (56, 189, 248))
    l_snd = _ensure_layer(doc, "03_BATHY_SOUNDINGS", (125, 211, 252))
    l_des = _ensure_layer(doc, "04_DESIGN_BOXES", (250, 204, 21), "MTI_DASHED")
    l_lbl = _ensure_layer(doc, "04_DESIGN_LABELS", (250, 204, 21))
    l_hst = _ensure_layer(doc, "05_HIST_MATTRESSES", (168, 85, 247))
    l_qaq = _ensure_layer(doc, "06_QAQC_FOOTPRINT", (2, 132, 199), "MTI_DASHED")
    l_asl = _ensure_layer(doc, "07_ASLAID_MATTRESS", (34, 197, 94))
    l_srf = _ensure_layer(doc, "07_ASLAID_SURFACE_3D", (74, 222, 128))
    l_raw = _ensure_layer(doc, "08_RAW_ROV_POINTS", (249, 115, 22))

    # 1. CAD Background Polylines (TWD97 E, N)
    for poly in (cad_polys or []):
        arr = np.asarray(poly, dtype=float)
        if arr.ndim == 2 and len(arr) >= 2:
            msp.add_lwpolyline([(float(p[0]), float(p[1])) for p in arr[:, :2]], dxfattribs={"layer": l_cad})

    # 2. Seabed Bathy Contours & 2m Spot Soundings in TWD97 (E, N, Z)
    sb = np.asarray(seabed_full_xyz if seabed_full_xyz is not None else [], dtype=float)
    if sb.ndim == 2 and len(sb) >= 4:
        if show_contours:
            try:
                import matplotlib.pyplot as _plt
                fig_tmp, ax_tmp = _plt.subplots()
                z_min, z_max = float(np.min(sb[:, 2])), float(np.max(sb[:, 2]))
                step = max(0.02, float(contour_interval or 0.05))
                if z_max - z_min >= step * 0.5:
                    lvls = np.arange(math.floor(z_min / step) * step, math.ceil(z_max / step) * step + step * 0.5, step)
                    if 1 <= len(lvls) <= 80:
                        cs = ax_tmp.tricontour(sb[:, 0], sb[:, 1], sb[:, 2], levels=lvls)
                        for lvl_val, seg_list in zip(cs.levels, cs.allsegs):
                            for seg in seg_list:
                                if len(seg) >= 2:
                                    msp.add_lwpolyline(
                                        [(float(p[0]), float(p[1])) for p in seg],
                                        dxfattribs={"layer": l_cnt, "elevation": float(lvl_val)}
                                    )
                _plt.close(fig_tmp)
            except Exception:
                pass

        if show_soundings:
            sp = max(0.5, float(spot_spacing or 2.0))
            seen_cells = set()
            for row_pt in sb:
                ce, cn, cz = float(row_pt[0]), float(row_pt[1]), float(row_pt[2])
                cell = (int(round(ce / sp)), int(round(cn / sp)))
                if cell not in seen_cells:
                    seen_cells.add(cell)
                    msp.add_point((ce, cn, cz), dxfattribs={"layer": l_snd})
                    _add_clean_text(msp, f"{cz:.2f}", ce, cn, 0.28, rgb=(56, 189, 248), ha="center", va="center", mono=True, layer=l_snd)

    # 3. Crossing Design Mattress Boxes & Labels in TWD97
    loc_active = str(metrics.get("location_id") or "").upper()
    for b_id, b_info in (boxes_dict or {}).items():
        c_arr = np.asarray(b_info.get("corners"), dtype=float)
        if c_arr.shape == (4, 2):
            is_act_slot = (str(b_id).upper() == loc_active)
            msp.add_lwpolyline(
                [(float(p[0]), float(p[1])) for p in c_arr],
                close=True,
                dxfattribs={
                    "layer": l_des,
                    "linetype": "CONTINUOUS" if is_act_slot else "MTI_DASHED",
                    "true_color": ezdxf.rgb2int((239, 68, 68) if is_act_slot else (250, 204, 21)),
                }
            )
            be, bn = float(b_info.get("design_e", np.mean(c_arr[:, 0]))), float(b_info.get("design_n", np.mean(c_arr[:, 1])))
            az = float(b_info.get("azimuth", 0.0))
            txt_rot = (90.0 - az) % 360.0
            if 90.0 < txt_rot < 270.0:
                txt_rot = (txt_rot + 180.0) % 360.0
            short_lbl = str(b_id).split("_")[-1] if "_" in str(b_id) else str(b_id)
            _add_clean_text(msp, short_lbl, be, bn, 0.42, rgb=(250, 204, 21), ha="center", va="center", rot_deg=txt_rot, mono=True, layer=l_lbl)

    # 4. Historical Placed Mattresses in TWD97
    from mti_4panel_math import _box_corners_cw
    cur_uno = int(float(metrics.get("unit_no") or 1))
    cur_xing = str(metrics.get("crossing_id") or "").upper()
    for r in (ledger_list or []):
        r_uno = int(float(r.get("unit_no") or 9999))
        r_xing = str(r.get("crossing_id") or "").upper()
        if r_uno < cur_uno and (not cur_xing or r_xing == cur_xing):
            he, hn = float(r.get("aslaid_e") or 0.0), float(r.get("aslaid_n") or 0.0)
            hz = float(r.get("aslaid_z") or 0.0)
            h_brg = float(r.get("heading_deg") or 195.854)
            h_az = ((h_brg + 180.0) % 360.0 - 180.0) % 360.0 if h_brg >= 180.0 else h_brg
            if abs(he) > 1000.0 and abs(hn) > 1000.0:
                hc, _, _ = _box_corners_cw(he, hn, h_az, 6.0, 3.0)
                msp.add_lwpolyline([(float(p[0]), float(p[1])) for p in hc], close=True, dxfattribs={"layer": l_hst, "elevation": hz})
                _add_clean_text(msp, str(r.get("physical_tag") or f"#{r_uno}"), he, hn, 0.40, rgb=(192, 132, 252), ha="center", va="center", mono=True, layer=l_hst)

    # 5. QA/QC Calculated Footprint in TWD97
    qe, qn = float(metrics.get("qaqc_e") or 0.0), float(metrics.get("qaqc_n") or 0.0)
    q_brg = float(metrics.get("qaqc_brg") or metrics.get("design_brg") or 195.854)
    s_qbrg = (q_brg + 180.0) % 360.0 if q_brg < 180.0 else q_brg
    q_az = (s_qbrg - 180.0) % 360.0
    if abs(qe) > 1000.0 and abs(qn) > 1000.0:
        qc, _, _ = _box_corners_cw(qe, qn, q_az, 6.0, 3.0)
        msp.add_lwpolyline([(float(p[0]), float(p[1])) for p in qc], close=True, dxfattribs={"layer": l_qaq, "linetype": "MTI_DASHED"})
        msp.add_circle((qe, qn), radius=0.15, dxfattribs={"layer": l_qaq})

    # 6. Active As-Laid 4-Corner ROV Footprint & 3D Mattress Surface Points in TWD97
    c_enz = metrics.get("corners_enz") or []
    act_z = float(metrics.get("aslaid_z") or 0.0)
    if len(c_enz) == 4:
        msp.add_lwpolyline(
            [(float(c[0]), float(c[1])) for c in c_enz],
            close=True,
            dxfattribs={"layer": l_asl, "elevation": act_z, "const_width": 0.04}
        )
        for idx_c, ( cname, c_pt ) in enumerate(zip(("C1_NW", "C2_NE", "C3_SE", "C4_SW"), c_enz)):
            ce, cn, cz = float(c_pt[0]), float(c_pt[1]), float(c_pt[2])
            msp.add_circle((ce, cn, cz), radius=0.12, dxfattribs={"layer": l_asl})
            _add_clean_text(msp, f"{cname} ({cz:.2f}m)", ce + 0.18, cn + 0.18, 0.25, rgb=(34, 197, 94), ha="left", va="bottom", mono=True, layer=l_asl)

    ae, an = float(metrics.get("aslaid_e") or 0.0), float(metrics.get("aslaid_n") or 0.0)
    if abs(ae) > 1000.0 and abs(an) > 1000.0:
        msp.add_circle((ae, an, act_z), radius=0.16, dxfattribs={"layer": l_asl})
        _add_clean_text(msp, f"{metrics.get('location_id','')} ({metrics.get('mattress_id','')})", ae, an, 0.35, rgb=(34, 197, 94), ha="center", va="center", mono=True, layer=l_asl)

    cl_arr = np.asarray(cleaned_xyz if cleaned_xyz is not None else [], dtype=float)
    if cl_arr.ndim == 2 and len(cl_arr) > 0:
        step_pt = max(1, len(cl_arr) // 400)
        for pt in cl_arr[::step_pt]:
            msp.add_point((float(pt[0]), float(pt[1]), float(pt[2])), dxfattribs={"layer": l_srf})

    # 7. Actual Unadjusted Raw ROV Points (from Setup Panel 4 if available)
    if isinstance(raw_rov_store, dict):
        for b_key, r_entry in raw_rov_store.items():
            for p in (r_entry.get("points") or []):
                re_v, rn_v, rz_v = float(p.get("e", 0)), float(p.get("n", 0)), float(p.get("z", 0))
                if abs(re_v) > 1000.0 and abs(rn_v) > 1000.0:
                    msp.add_circle((re_v, rn_v, rz_v), radius=0.14, dxfattribs={"layer": l_raw})
                    _add_clean_text(msp, f"{p.get('pt_id','RAW')} ({rz_v:.2f}m)", re_v + 0.18, rn_v - 0.18, 0.24, rgb=(249, 115, 22), ha="left", va="top", mono=True, layer=l_raw)

def _extract_axes_data_to_modelspace(doc, ax, layer_prefix):
    """Extracts geodetic TWD97 lines, polygons, markers, contours, and data-coord callouts from a Matplotlib Axes into Model Space."""
    msp = doc.modelspace()
    created_layers = set()
    l_poly = _ensure_layer(doc, f"{layer_prefix}_POLYGONS", (34, 197, 94))
    l_line = _ensure_layer(doc, f"{layer_prefix}_LINES", (56, 189, 248))
    l_pts = _ensure_layer(doc, f"{layer_prefix}_POINTS", (250, 204, 21))
    l_txt = _ensure_layer(doc, f"{layer_prefix}_LABELS", (248, 250, 252))
    created_layers.update([l_poly, l_line, l_pts, l_txt])

    x0, x1 = sorted(ax.get_xlim())
    y0, y1 = sorted(ax.get_ylim())
    pad_x, pad_y = (x1 - x0) * 0.25, (y1 - y0) * 0.25

    def _in_twd_bounds(px, py):
        return (x0 - pad_x <= px <= x1 + pad_x) and (y0 - pad_y <= py <= y1 + pad_y)

    # Patches (Polygons, Rectangles, Circles in data coordinates)
    for p in ax.patches:
        if not p.get_visible():
            continue
        ec_rgb = _rgb_tuple(p.get_edgecolor(), (56, 189, 248))
        ls_dxf = _mpl_ls_to_dxf(p.get_linestyle())
        if isinstance(p, mpatches.Circle):
            cx, cy = p.center
            if _in_twd_bounds(cx, cy):
                msp.add_circle((float(cx), float(cy)), radius=float(p.radius), dxfattribs={"layer": l_poly, "true_color": ezdxf.rgb2int(ec_rgb or (56, 189, 248))})
        else:
            verts = p.get_path().transformed(p.get_patch_transform()).vertices
            # Convert display px back to data E, N via ax.transData.inverted()
            data_v = ax.transData.inverted().transform(verts)
            if len(data_v) >= 2 and _in_twd_bounds(float(data_v[0, 0]), float(data_v[0, 1])):
                msp.add_lwpolyline(
                    [(float(v[0]), float(v[1])) for v in data_v],
                    close=True,
                    dxfattribs={"layer": l_poly, "linetype": ls_dxf, "true_color": ezdxf.rgb2int(ec_rgb or (34, 197, 94))}
                )

    # Lines & Markers
    for ln in ax.lines:
        if not ln.get_visible():
            continue
        xd, yd = np.asarray(ln.get_xdata(), dtype=float), np.asarray(ln.get_ydata(), dtype=float)
        if len(xd) == 0:
            continue
        c_rgb = _rgb_tuple(ln.get_color(), (56, 189, 248)) or (56, 189, 248)
        ls_s = str(ln.get_linestyle() or "-")
        mk_s = str(ln.get_marker() or "None")
        pts = [(float(ex), float(ny)) for ex, ny in zip(xd, yd) if _in_twd_bounds(float(ex), float(ny))]
        if len(pts) >= 2 and ls_s not in ("None", "none", ""):
            msp.add_lwpolyline(pts, dxfattribs={"layer": l_line, "linetype": _mpl_ls_to_dxf(ls_s), "true_color": ezdxf.rgb2int(c_rgb)})
        if mk_s not in ("None", "none", "") and pts:
            for px, py in pts:
                msp.add_circle((px, py), radius=0.13, dxfattribs={"layer": l_pts, "true_color": ezdxf.rgb2int(c_rgb)})

    # Collections (Contours, LineCollections, Scatter)
    for col in ax.collections:
        if not col.get_visible():
            continue
        ec_list = col.get_edgecolors()
        fc_list = col.get_facecolors()
        base_col = ec_list[0] if len(ec_list) > 0 else (fc_list[0] if len(fc_list) > 0 else (56, 189, 248))
        c_rgb = _rgb_tuple(base_col, (56, 189, 248)) or (56, 189, 248)
        if isinstance(col, PathCollection):
            offs = col.get_offsets()
            for pt in np.asarray(offs, dtype=float):
                if len(pt) >= 2 and _in_twd_bounds(float(pt[0]), float(pt[1])):
                    msp.add_point((float(pt[0]), float(pt[1]), 0.0), dxfattribs={"layer": l_pts, "true_color": ezdxf.rgb2int(c_rgb)})
        else:
            for pth in col.get_paths():
                disp_pts = col.get_transform().transform(pth.vertices)
                d_pts = ax.transData.inverted().transform(disp_pts)
                if len(d_pts) >= 2 and _in_twd_bounds(float(d_pts[0, 0]), float(d_pts[0, 1])):
                    msp.add_lwpolyline([(float(v[0]), float(v[1])) for v in d_pts], dxfattribs={"layer": l_line, "true_color": ezdxf.rgb2int(c_rgb)})

    # Data-coordinate Texts & Annotations
    for tx in ax.texts:
        if not tx.get_visible() or not str(tx.get_text() or "").strip():
            continue
        disp_xy = tx.get_transform().transform(tx.get_position())
        dx, dy = ax.transData.inverted().transform(disp_xy)
        if _in_twd_bounds(float(dx), float(dy)):
            c_rgb = _rgb_tuple(tx.get_color(), (248, 250, 252)) or (248, 250, 252)
            c_rgb = (248, 250, 252) if sum(c_rgb) < 160 else c_rgb
            # Scale text cap-height to true world meters matching the axes scale
            ax_bb = ax.get_position()
            fig_h_mm = ax.figure.get_size_inches()[1] * 25.4
            m_per_mm = (y1 - y0) / max(1.0, ax_bb.height * fig_h_mm)
            cap_m = float(tx.get_fontsize()) * 0.254 * m_per_mm
            _add_clean_text(
                msp, tx.get_text(), float(dx), float(dy), cap_m, rgb=c_rgb,
                ha=tx.get_ha(), va=tx.get_va(), rot_deg=float(tx.get_rotation() or 0.0),
                mono=("monospace" in str(tx.get_fontfamily()).lower()), layer=l_txt
            )
    return created_layers

def _render_axes_to_paperspace_mm(psp, doc, ax, dpi, layer_name):
    """Renders non-geodetic Matplotlib Axes (banners, tables, profiles, colorbars) into exact Paper Space mm."""
    px_to_mm = 25.4 / float(dpi)

    def _disp_to_mm(pts_disp):
        arr = np.asarray(pts_disp, dtype=float)
        return arr * px_to_mm

    # 1. Axes Background & Spines if framed
    if ax.get_frame_on():
        bbox = ax.get_window_extent()
        x0_m, y0_m = bbox.x0 * px_to_mm, bbox.y0 * px_to_mm
        x1_m, y1_m = bbox.x1 * px_to_mm, bbox.y1 * px_to_mm
        fc = _rgb_tuple(ax.get_facecolor(), None)
        if fc and fc != (255, 255, 255):
            _add_solid_poly(psp, [(x0_m, y0_m), (x1_m, y0_m), (x1_m, y1_m), (x0_m, y1_m)], fc, layer_name)
        psp.add_lwpolyline([(x0_m, y0_m), (x1_m, y0_m), (x1_m, y1_m), (x0_m, y1_m)], close=True, dxfattribs={"layer": layer_name, "true_color": ezdxf.rgb2int((15, 23, 42))})

    # 2. Patches (Banners, Table Cells, KPI Cards, Bars, Legend Boxes)
    for p in ax.patches:
        if not p.get_visible():
            continue
        verts_mm = _disp_to_mm(p.get_path().transformed(p.get_patch_transform()).vertices)
        if len(verts_mm) < 3:
            continue
        fc_rgb = _rgb_tuple(p.get_facecolor(), None) if p.get_fill() else None
        ec_rgb = _rgb_tuple(p.get_edgecolor(), None)
        if fc_rgb and p.get_alpha() != 0:
            _add_solid_poly(psp, verts_mm, fc_rgb, layer_name)
        if ec_rgb and float(p.get_linewidth() or 0.0) > 0.05:
            psp.add_lwpolyline(
                [(float(v[0]), float(v[1])) for v in verts_mm],
                close=True,
                dxfattribs={"layer": layer_name, "linetype": _mpl_ls_to_dxf(p.get_linestyle()), "true_color": ezdxf.rgb2int(ec_rgb)}
            )

    # 3. Collections (Profile Scatter Points, Colorbar QuadMesh)
    for col in ax.collections:
        if not col.get_visible():
            continue
        fc_arr = col.get_facecolors()
        ec_arr = col.get_edgecolors()
        if isinstance(col, PathCollection):
            offs = np.asarray(col.get_offsets(), dtype=float)
            if len(offs) > 0:
                disp_offs = col.get_offset_transform().transform(offs) * px_to_mm
                for idx_pt, (mx, my) in enumerate(disp_offs):
                    c_use = fc_arr[min(idx_pt, len(fc_arr) - 1)] if len(fc_arr) > 0 else (ec_arr[0] if len(ec_arr) > 0 else (2, 132, 199))
                    rgb_p = _rgb_tuple(c_use, (2, 132, 199)) or (2, 132, 199)
                    psp.add_circle((float(mx), float(my)), radius=0.42, dxfattribs={"layer": layer_name, "true_color": ezdxf.rgb2int(rgb_p)})
        else:
            paths = col.get_paths()
            step_c = max(1, len(paths) // 64)
            for idx_p in range(0, len(paths), step_c):
                v_mm = _disp_to_mm(col.get_transform().transform(paths[idx_p].vertices))
                if len(v_mm) >= 3 and len(fc_arr) > 0:
                    c_rgb = _rgb_tuple(fc_arr[min(idx_p, len(fc_arr) - 1)], None)
                    _add_solid_poly(psp, v_mm, c_rgb, layer_name)
                elif len(v_mm) >= 2 and len(ec_arr) > 0:
                    c_rgb = _rgb_tuple(ec_arr[min(idx_p, len(ec_arr) - 1)], (56, 189, 248)) or (56, 189, 248)
                    psp.add_lwpolyline([(float(v[0]), float(v[1])) for v in v_mm], dxfattribs={"layer": layer_name, "true_color": ezdxf.rgb2int(c_rgb)})

    # 4. Lines (Table Grid Rules, Seabed Profiles, Tolerance Lines)
    for ln in ax.lines:
        if not ln.get_visible():
            continue
        xy_data = np.column_stack([np.asarray(ln.get_xdata(), dtype=float), np.asarray(ln.get_ydata(), dtype=float)])
        if len(xy_data) >= 2 and str(ln.get_linestyle() or "-") not in ("None", "none", ""):
            xy_mm = _disp_to_mm(ln.get_transform().transform(xy_data))
            c_rgb = _rgb_tuple(ln.get_color(), (15, 23, 42)) or (15, 23, 42)
            psp.add_lwpolyline(
                [(float(v[0]), float(v[1])) for v in xy_mm],
                dxfattribs={"layer": layer_name, "linetype": _mpl_ls_to_dxf(ln.get_linestyle()), "true_color": ezdxf.rgb2int(c_rgb)}
            )

    # 5. Texts, Axis Titles, Labels, Tick Labels & Legends
    _render_axes_chrome_and_texts_mm(psp, ax, px_to_mm, layer_name, include_data_texts=True)

def _render_axes_chrome_and_texts_mm(psp, ax, px_to_mm, layer_name, include_data_texts=False):
    bbox = ax.get_window_extent()
    x0_m, y0_m, x1_m, y1_m = bbox.x0 * px_to_mm, bbox.y0 * px_to_mm, bbox.x1 * px_to_mm, bbox.y1 * px_to_mm

    if ax.get_frame_on():
        psp.add_lwpolyline([(x0_m, y0_m), (x1_m, y0_m), (x1_m, y1_m), (x0_m, y1_m)], close=True, dxfattribs={"layer": layer_name, "true_color": ezdxf.rgb2int((15, 23, 42))})

    # Titles & X/Y Labels
    for t_obj in (ax.title, ax.xaxis.label, ax.yaxis.label):
        if t_obj and t_obj.get_visible() and str(t_obj.get_text() or "").strip():
            px, py = t_obj.get_transform().transform(t_obj.get_position())
            _add_clean_text(
                psp, t_obj.get_text(), px * px_to_mm, py * px_to_mm,
                float(t_obj.get_fontsize()) * 0.254,
                rgb=_rgb_tuple(t_obj.get_color(), (15, 23, 42)),
                ha=t_obj.get_ha(), va=t_obj.get_va(), rot_deg=float(t_obj.get_rotation() or 0.0), layer=layer_name
            )

    # X & Y Tick Marks + Tick Labels
    if ax.xaxis.get_visible():
        for tick in ax.xaxis.get_major_ticks():
            if tick.label1.get_visible() and str(tick.label1.get_text() or "").strip():
                px, py = tick.label1.get_transform().transform(tick.label1.get_position())
                tx_m = px * px_to_mm
                if x0_m - 1.0 <= tx_m <= x1_m + 1.0:
                    psp.add_line((tx_m, y0_m), (tx_m, y0_m - 1.1), dxfattribs={"layer": layer_name, "true_color": ezdxf.rgb2int((15, 23, 42))})
                    _add_clean_text(psp, tick.label1.get_text(), tx_m, py * px_to_mm, float(tick.label1.get_fontsize()) * 0.254, rgb=(30, 41, 59), ha="center", va="top", mono=True, layer=layer_name)

    if ax.yaxis.get_visible():
        y_right = (ax.yaxis.get_ticks_position() == "right")
        for tick in ax.yaxis.get_major_ticks():
            lbl = tick.label2 if (y_right and tick.label2.get_visible()) else tick.label1
            if lbl.get_visible() and str(lbl.get_text() or "").strip():
                px, py = lbl.get_transform().transform(lbl.get_position())
                ty_m = py * px_to_mm
                if y0_m - 1.0 <= ty_m <= y1_m + 1.0:
                    x_edge = x1_m if y_right else x0_m
                    x_tick_end = x1_m + 1.1 if y_right else x0_m - 1.1
                    psp.add_line((x_edge, ty_m), (x_tick_end, ty_m), dxfattribs={"layer": layer_name, "true_color": ezdxf.rgb2int((15, 23, 42))})
                    _add_clean_text(psp, lbl.get_text(), px * px_to_mm, ty_m, float(lbl.get_fontsize()) * 0.254, rgb=(30, 41, 59), ha="left" if y_right else "right", va="center", mono=True, layer=layer_name)

    # Texts inside Axes (when rendering Paper Space axes or Panel 2 local callouts)
    if include_data_texts:
        for tx in ax.texts:
            if not tx.get_visible() or not str(tx.get_text() or "").strip():
                continue
            px, py = tx.get_transform().transform(tx.get_position())
            mx, my = px * px_to_mm, py * px_to_mm
            arr_p = getattr(tx, "arrow_patch", None)
            if arr_p is not None and arr_p.get_visible():
                av_mm = arr_p.get_path().transformed(arr_p.get_patch_transform()).vertices * px_to_mm
                ac_rgb = _rgb_tuple(arr_p.get_edgecolor(), None) or _rgb_tuple(arr_p.get_facecolor(), (71, 85, 105))
                if len(av_mm) >= 2 and ac_rgb:
                    psp.add_lwpolyline([(float(v[0]), float(v[1])) for v in av_mm], dxfattribs={"layer": layer_name, "true_color": ezdxf.rgb2int(ac_rgb)})
            bb_patch = tx.get_bbox_patch()
            if bb_patch is not None and bb_patch.get_visible():
                v_mm = bb_patch.get_path().transformed(bb_patch.get_patch_transform()).vertices * px_to_mm
                _add_solid_poly(psp, v_mm, _rgb_tuple(bb_patch.get_facecolor(), (255, 255, 255)), layer_name)
                ec_b = _rgb_tuple(bb_patch.get_edgecolor(), (148, 163, 184))
                if ec_b:
                    psp.add_lwpolyline([(float(v[0]), float(v[1])) for v in v_mm], close=True, dxfattribs={"layer": layer_name, "true_color": ezdxf.rgb2int(ec_b)})
            _add_clean_text(
                psp, tx.get_text(), mx, my, float(tx.get_fontsize()) * 0.254,
                rgb=_rgb_tuple(tx.get_color(), (15, 23, 42)),
                ha=tx.get_ha(), va=tx.get_va(), rot_deg=float(tx.get_rotation() or 0.0),
                mono=("monospace" in str(tx.get_fontfamily()).lower()), layer=layer_name
            )

    # Legend Box, Handles & Labels in Paper Space mm
    leg = ax.get_legend()
    if leg and leg.get_visible():
        fr = leg.get_frame()
        if fr and fr.get_visible():
            fb = fr.get_window_extent()
            fx0, fy0, fx1, fy1 = fb.x0 * px_to_mm, fb.y0 * px_to_mm, fb.x1 * px_to_mm, fb.y1 * px_to_mm
            _add_solid_poly(psp, [(fx0, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1)], _rgb_tuple(fr.get_facecolor(), (255, 255, 255)), layer_name)
            psp.add_lwpolyline([(fx0, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1)], close=True, dxfattribs={"layer": layer_name, "true_color": ezdxf.rgb2int(_rgb_tuple(fr.get_edgecolor(), (203, 213, 225)) or (203, 213, 225))})
        handles = getattr(leg, "legend_handles", None) or getattr(leg, "legendHandles", [])
        for h_art, l_txt in zip(handles, leg.get_texts()):
            tb = l_txt.get_window_extent()
            tx_m, ty_m = tb.x0 * px_to_mm, 0.5 * (tb.y0 + tb.y1) * px_to_mm
            _add_clean_text(psp, l_txt.get_text(), tx_m, ty_m, float(l_txt.get_fontsize()) * 0.254, rgb=_rgb_tuple(l_txt.get_color(), (15, 23, 42)), ha="left", va="center", layer=layer_name)
            if h_art is not None:
                hb = h_art.get_window_extent()
                hx0, hy0, hx1, hy1 = hb.x0 * px_to_mm, hb.y0 * px_to_mm, hb.x1 * px_to_mm, hb.y1 * px_to_mm
                h_col = _rgb_tuple(getattr(h_art, "get_edgecolor", lambda: (2, 132, 199))(), None) or _rgb_tuple(getattr(h_art, "get_color", lambda: (2, 132, 199))(), (2, 132, 199))
                psp.add_line((hx0, 0.5 * (hy0 + hy1)), (hx1, 0.5 * (hy0 + hy1)), dxfattribs={"layer": layer_name, "true_color": ezdxf.rgb2int(h_col or (2, 132, 199))})

def _add_locked_viewport(psp, doc, bbox_mm, target_e, target_n, view_h_m, twist_deg=0.0, frozen_layers=None):
    vp_layer = _ensure_layer(doc, "00_VIEWPORTS", (100, 116, 139))
    x0, y0, x1, y1 = bbox_mm
    w_mm, h_mm = float(x1 - x0), float(y1 - y0)
    cx_mm, cy_mm = 0.5 * (x0 + x1), 0.5 * (y0 + y1)

    vp = psp.add_viewport(
        center=(cx_mm, cy_mm),
        size=(w_mm, h_mm),
        view_center_point=(0.0, 0.0),
        view_height=float(view_h_m),
        dxfattribs={"layer": vp_layer}
    )
    vp.dxf.view_target_point = (float(target_e), float(target_n), 0.0)
    vp.dxf.view_direction_vector = (0.0, 0.0, 1.0)
    vp.dxf.view_twist_angle = float(twist_deg) % 360.0
    vp.dxf.status = 1
    vp.dxf.flags = int(getattr(vp.dxf, "flags", 0) or 0) | 16384

    if abs(twist_deg) > 1e-4:
        try:
            m44 = vp.get_transformation_matrix()
            p0 = m44.transform((float(target_e), float(target_n), 0.0))
            rad_az = math.radians(float(twist_deg))
            p_nne = m44.transform((float(target_e) + math.sin(rad_az), float(target_n) + math.cos(rad_az), 0.0))
            if (p_nne.y - p0.y) < 0 or abs(p_nne.x - p0.x) > abs(p_nne.y - p0.y) * 0.25:
                vp.dxf.view_twist_angle = float(-twist_deg) % 360.0
        except Exception:
            pass

    if frozen_layers:
        vp.frozen_layers = list(frozen_layers)
    return vp

def convert_matplotlib_figs_to_dxf(figs, out_path, native_4panel_metrics=None, populate_msp_cb=None):
    """
    Builds a complete AutoCAD/BricsCAD R2010 DXF where:
      - Model Space contains real-world TWD97 (E, N, Z) CAD entities
      - Paper Space Layout tab(s) match the exact PDF Chart page sizes, viewports, profiles, and tables.
    """
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 6      # Meters
    doc.header["$MEASUREMENT"] = 1   # Metric
    _ensure_styles_and_linetypes(doc)

    if callable(populate_msp_cb):
        populate_msp_cb(doc)

    # First pass for Ad-Hoc figures: extract all geodetic TWD97 axes into Model Space per page
    page_adhoc_layers = {}
    all_adhoc_layers = set()
    if not callable(populate_msp_cb):
        for p_idx, fig in enumerate(figs):
            fig.canvas.draw()
            p_layers = set()
            for ax_i, ax in enumerate(fig.axes):
                x0, x1 = ax.get_xlim()
                y0, y1 = ax.get_ylim()
                if 50000.0 <= 0.5 * (x0 + x1) <= 500000.0 and 2000000.0 <= 0.5 * (y0 + y1) <= 3100000.0:
                    created = _extract_axes_data_to_modelspace(doc, ax, f"ADHOC_P{p_idx + 1}_AX{ax_i + 1}")
                    p_layers.update(created)
                    all_adhoc_layers.update(created)
            page_adhoc_layers[p_idx] = p_layers

    # Second pass: build exact Paper Space Layout tab for every PDF page
    l_sheet = _ensure_layer(doc, "09_LAYOUT_SHEET", (15, 23, 42))
    for p_idx, fig in enumerate(figs):
        fig.canvas.draw()
        dpi = float(fig.dpi)
        px_to_mm = 25.4 / dpi
        w_mm = round(float(fig.get_size_inches()[0]) * 25.4, 2)
        h_mm = round(float(fig.get_size_inches()[1]) * 25.4, 2)

        if native_4panel_metrics is not None:
            tab_name = "A3_4Panel_Chart" if p_idx == 0 else (f"Verification_Report_P{p_idx}" if p_idx > 1 else "Verification_Report")
        else:
            tab_name = f"PDF_Page_{p_idx + 1}"

        if p_idx == 0 and "Layout1" in doc.layouts:
            try:
                doc.layouts.rename("Layout1", tab_name)
                psp = doc.layouts.get(tab_name)
            except Exception:
                psp = doc.layouts.get("Layout1")
        else:
            psp = doc.layouts.new(tab_name)

        psp.page_setup(size=(w_mm, h_mm), margins=(0, 0, 0, 0), units="mm")
        for old_e in list(psp):
            if old_e.dxftype() == "VIEWPORT" and getattr(old_e.dxf, "id", 1) != 1:
                try:
                    psp.delete_entity(old_e)
                except Exception:
                    pass

        # Figure-level suptitle / texts
        for ft in getattr(fig, "texts", []):
            if ft.get_visible() and str(ft.get_text() or "").strip():
                px, py = ft.get_transform().transform(ft.get_position())
                _add_clean_text(psp, ft.get_text(), px * px_to_mm, py * px_to_mm, float(ft.get_fontsize()) * 0.254, rgb=_rgb_tuple(ft.get_color(), (15, 23, 42)), ha=ft.get_ha(), va=ft.get_va(), layer=l_sheet)

        for ax in fig.axes:
            if not ax.get_visible():
                continue
            x0, x1 = ax.get_xlim()
            y0, y1 = ax.get_ylim()
            bb = ax.get_window_extent()
            bb_mm = (bb.x0 * px_to_mm, bb.y0 * px_to_mm, bb.x1 * px_to_mm, bb.y1 * px_to_mm)
            ttl_up = str(ax.get_title() or "").upper()

            is_twd97 = (50000.0 <= 0.5 * (x0 + x1) <= 500000.0 and 2000000.0 <= 0.5 * (y0 + y1) <= 3100000.0)
            is_p2_local = (native_4panel_metrics is not None and "PANEL 2" in ttl_up)

            if is_twd97:
                lbl_lyrs = {ly for ly in page_adhoc_layers.get(p_idx, set()) if ly.endswith('_LABELS')}
                freeze_set = ((all_adhoc_layers - page_adhoc_layers.get(p_idx, set())) | lbl_lyrs) if all_adhoc_layers else None
                _add_locked_viewport(psp, doc, bb_mm, 0.5 * (x0 + x1), 0.5 * (y0 + y1), abs(y1 - y0), twist_deg=0.0, frozen_layers=freeze_set)
                _render_axes_chrome_and_texts_mm(psp, ax, px_to_mm, l_sheet, include_data_texts=(native_4panel_metrics is None))
            elif is_p2_local:
                des_e = float(native_4panel_metrics.get("design_e") or native_4panel_metrics.get("aslaid_e") or 0.0)
                des_n = float(native_4panel_metrics.get("design_n") or native_4panel_metrics.get("aslaid_n") or 0.0)
                des_az = float(native_4panel_metrics.get("design_az") or 0.0)
                _add_locked_viewport(psp, doc, bb_mm, des_e, des_n, abs(y1 - y0), twist_deg=des_az)
                _render_axes_chrome_and_texts_mm(psp, ax, px_to_mm, l_sheet, include_data_texts=True)
            else:
                _render_axes_to_paperspace_mm(psp, doc, ax, dpi, l_sheet)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    doc.saveas(out_path)
    return open(out_path, "rb").read()

def generate_4panel_studio_dxf(
    boxes_dict, metrics, cleaned_xyz, x_local, y_local, z_vals,
    seabed_local_xyz, seabed_full_xyz, workspace_dir="workspace",
    include_history=True, ledger_list=None, scale_p1=250, scale_p2=75,
    show_contours=True, contour_interval=0.05, show_soundings=True,
    spot_spacing=2.0, custom_report_md=None, cad_polys=None, raw_rov_store=None
):
    """Generates the 4-Panel Verification DXF (TWD97 Model Space + Exact PDF Paper Space Layouts)."""
    import gc
    import matplotlib.pyplot as plt
    import mti_4panel_a3 as a3_mod
    from mti_4panel_reports import render_a4_landscape_figures, build_structured_report_markdown

    os.makedirs(workspace_dir, exist_ok=True)
    captured_figs = []
    orig_figure = plt.figure
    orig_close = plt.close
    orig_clf = matplotlib.figure.Figure.clf

    def _spy_figure(*args, **kwargs):
        f = orig_figure(*args, **kwargs)
        captured_figs.append(f)
        return f

    try:
        plt.figure = _spy_figure
        plt.close = lambda *a, **k: None
        matplotlib.figure.Figure.clf = lambda self, *a, **k: None

        a3_mod.generate_a3_4panel_chart(
            boxes_dict, metrics, cleaned_xyz, x_local, y_local, z_vals,
            seabed_local_xyz, seabed_full_xyz, workspace_dir, include_history,
            ledger_list, scale_p1, scale_p2, show_contours, contour_interval,
            show_soundings, spot_spacing, save_pdf=False
        )
        rep_md_use = custom_report_md or build_structured_report_markdown(metrics, include_history, ledger_list, scale_p1, scale_p2)
        render_a4_landscape_figures(metrics, rep_md_use)
    finally:
        plt.figure = orig_figure
        plt.close = orig_close
        matplotlib.figure.Figure.clf = orig_clf

    base_fn = str(metrics.get("base_filename") or "latest_A3_4Panel_Chart").strip()
    out_dxf = os.path.join(workspace_dir, f"{base_fn}.dxf")
    latest_dxf = os.path.join(workspace_dir, "latest_A3_4Panel_Chart.dxf")

    def _populate_cb(doc):
        populate_4panel_modelspace(
            doc, boxes_dict, metrics, cleaned_xyz, seabed_full_xyz,
            cad_polys=cad_polys, ledger_list=ledger_list if include_history else [],
            raw_rov_store=raw_rov_store, show_contours=show_contours,
            contour_interval=contour_interval, show_soundings=show_soundings,
            spot_spacing=spot_spacing
        )

    try:
        dxf_bytes = convert_matplotlib_figs_to_dxf(captured_figs, out_dxf, native_4panel_metrics=metrics, populate_msp_cb=_populate_cb)
        open(latest_dxf, "wb").write(dxf_bytes)
    finally:
        for f in captured_figs:
            try:
                f.clf()
                plt.close(f)
            except Exception:
                pass
        plt.close("all")
        gc.collect()

    return dxf_bytes, f"{base_fn}.dxf"