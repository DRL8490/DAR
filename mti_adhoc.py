import os, io, re, gc, sys, json, math, base64, textwrap, traceback, contextlib
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as patheffects
from matplotlib.backends.backend_pdf import PdfPages

from mti_4panel_math import (
    AREA_LOCATIONS, _box_corners_cw, build_crossing_boxes_from_catalog,
    idw_interpolate, get_or_build_seabed_xyz, load_cad_bg_polylines
)
from mti_4panel_a3 import draw_north_arrow, plot_cad_background, plot_seabed_layer
from mti_raw_rov import load_raw_rov_store, get_raw_rov_corners_tuple
from mti_4panel_reports import (
    CROSSING_SCOPES, norm_mti_date, extract_all_mti_logs, parse_log_entry_fields
)

STARTER_ADHOC_SCRIPT = """# Starter Ad-Hoc MTI Chart (ISO A3 Landscape: Crossing Progress & As-Laid Offset Summary)
fig = plt.figure(figsize=(420.0 / 25.4, 297.0 / 25.4), dpi=150, facecolor="white")
gs = fig.add_gridspec(1, 2, left=0.06, right=0.96, top=0.86, bottom=0.12, wspace=0.18)

fig.suptitle(
    f"AD-HOC MTI SUMMARY CHART  |  {TODAY_ISO}  |  Surveyor: {SURVEYOR_NAME}",
    fontsize=13, fontweight="bold", y=0.95, color="#0f172a"
)

# Left Panel: Installed vs. Remaining Scope per Crossing
ax1 = fig.add_subplot(gs[0, 0])
xings = [x for x, _ in CROSSING_SCOPES]
scopes = [sc for _, sc in CROSSING_SCOPES]
laid = [sum(1 for r in ledger if str(r.get("crossing_id", "")).upper() == x) for x in xings]
rem = [max(0, sc - ld) for sc, ld in zip(scopes, laid)]

y_pos = np.arange(len(xings))
ax1.barh(y_pos, laid, color="#16a34a", label="Installed")
ax1.barh(y_pos, rem, left=laid, color="#cbd5e1", label="Remaining")
ax1.set_yticks(y_pos)
ax1.set_yticklabels(xings, fontweight="bold")
ax1.invert_yaxis()
ax1.set_xlabel("Mattress Count (Units)", fontweight="bold")
ax1.set_title(f"Crossing Progress ({sum(laid)} / {sum(scopes)} Laid)", fontweight="bold")
ax1.grid(True, axis="x", linestyle=":", alpha=0.6)
ax1.legend(loc="lower right")

# Right Panel: Centerline Offset (dCL) of Installed Units vs. 0.50m Tolerance
ax2 = fig.add_subplot(gs[0, 1])
if ledger:
    labels = [f"#{r.get('unit_no','')} {r.get('design_box_id','')}" for r in ledger]
    offs = [float(r.get("cl_offset_m") or 0.0) for r in ledger]
    cols = ["#16a34a" if v <= 0.50 else "#dc2626" for v in offs]
    x_idx = np.arange(len(labels))
    ax2.bar(x_idx, offs, color=cols, width=0.55)
    ax2.axhline(0.50, color="#dc2626", linestyle="--", linewidth=1.4, label="Max Tol (0.50 m)")
    ax2.set_xticks(x_idx)
    ax2.set_xticklabels(labels, rotation=25, ha="right", fontsize=8.5, fontweight="bold")
    ax2.set_ylim(0, max(0.65, max(offs) + 0.15))
    ax2.legend(loc="upper right")
else:
    ax2.text(0.5, 0.5, "No mattress fixes in ledger yet", ha="center", va="center")
ax2.set_ylabel("Centerline Offset dCL (m)", fontweight="bold")
ax2.set_title("As-Laid Radial Offset QA/QC", fontweight="bold")
ax2.grid(True, axis="y", linestyle=":", alpha=0.6)

OUTPUT_FILENAME = f"{TODAY_YYYYMMDD}_MTI_AdHoc_Summary_Chart.pdf"
OUTPUT_FIGS.append(fig)
"""

def build_adhoc_gemini_context(st_data, catalog_list, workspace_dir="workspace", surveyor_name="Duty Surveyor"):
    ledger = list((st_data or {}).get("ledger") or [])
    raw_rov_store = load_raw_rov_store(st_data, workspace_dir, None, ledger, catalog_list)
    raw_logs = extract_all_mti_logs(st_data or {})
    parsed_logs = [parse_log_entry_fields(lg, surveyor_name) for lg in raw_logs]
    log_dates = sorted({p[0] for p in parsed_logs if p[0]}, reverse=True)
    fix_dates = sorted({norm_mti_date(r.get("install_date")) for r in ledger if norm_mti_date(r.get("install_date"))}, reverse=True)

    bathy_ready, cad_ready = [], []
    for loc in AREA_LOCATIONS:
        arr, src = get_or_build_seabed_xyz(workspace_dir, loc, {})
        if src == "SURVEY_BATHY" and len(arr) > 0:
            bathy_ready.append(f"{loc} ({len(arr)} pts)")
        polys = load_cad_bg_polylines(workspace_dir, loc)
        if polys:
            cad_ready.append(f"{loc} ({len(polys)} polylines)")

    ledger_keys = sorted(list(ledger[0].keys())) if ledger else [
        "unit_no", "crossing_id", "design_box_id", "physical_tag", "install_date",
        "usbl_sensor", "surveyor_name", "design_e", "design_n", "design_brg",
        "aslaid_e", "aslaid_n", "aslaid_z", "heading_deg", "cl_offset_m",
        "d_along_m", "d_cross_m", "c1_e", "c1_n", "c2_e", "c2_n", "c3_e", "c3_n",
        "c4_e", "c4_n", "gap_labels", "status", "remarks"
    ]
    raw_log_keys = sorted(list(raw_logs[0].keys())) if raw_logs else [
        "log_date", "log_time", "category", "crossing_id", "asset", "description", "details", "wind", "current", "surveyor"
    ]

    ctx_lines = [
        "=== THPP SUBSEA MTI & DPR-MTI AD-HOC PYTHON CHART GENERATOR CONTEXT ===",
        "You are writing an ad-hoc Python Matplotlib / PdfPages script to run inside the THPP DPR-MTI Module (`/mti/studio`).",
        "Return ONLY raw executable Python code (no external pip installs).",
        "",
        "1. PROJECT & GEODETIC BASELINE:",
        "   - Project: Tung-Hsiao Power Plant 2nd Stage Subsea Gas Pipeline (Client: TPC | Contractor: NMDC | Vessel: DP2 MMA Prestige)",
        "   - Coordinate Reference: TWD97 / TM2 (Easting E, Northing N in meters) | Vertical Datum: TWVD2001 (Depth Z in meters; Concrete Mattress Thickness = 0.30 m)",
        "   - Reporting Principle: Audience-first, signal-over-volume. Fit charts/tables cleanly on Landscape ISO A3 (420x297 mm = 16.54x11.69 in) or Landscape ISO A4 (297x210 mm = 11.69x8.27 in). State each metric once; zero boilerplate filler.",
        "",
        "2. PRE-LOADED VARIABLES & LIVE DATABASE SNAPSHOT (ALREADY IN GLOBAL SCOPE - DO NOT RE-IMPORT FLASK):",
        f"   - `SURVEYOR_NAME`: '{surveyor_name}' | `TODAY_ISO`: '{datetime.utcnow().strftime('%Y-%m-%d')}' | `TODAY_YYYYMMDD`: '{datetime.utcnow().strftime('%Y%m%d')}'",
        f"   - `AREA_LOCATIONS`: {AREA_LOCATIONS}",
        f"   - `CROSSING_SCOPES`: {CROSSING_SCOPES} (Total = 139 mattresses)",
        f"   - `st`: Full MTI state dict (`keys`: {sorted(list((st_data or {}).keys()))})",
        f"   - `ledger`: List of {len(ledger)} installed mattress fix dicts (Active dates: {fix_dates[:8] or ['None']})",
        f"     * `ledger[i]` keys: {ledger_keys}",
        f"   - `raw_logs`: List of {len(raw_logs)} onboard DPR-MTI survey log dicts (`raw_logs[i]` keys: {raw_log_keys})",
        f"   - `parsed_logs`: List of normalized 7-tuples `(date_iso, time_hm, category, area, clean_desc, env_short, surveyor)` (Active dates: {log_dates[:10] or ['None']})",
        f"   - `catalog`: List of {len(catalog_list or [])} design mattress dicts with keys `['layer', 'name', 'design_e', 'design_n', 'bearing']`",
        f"   - Loaded Bathy Locations: {bathy_ready or ['None']}",
        f"   - Loaded CAD DXF Locations: {cad_ready or ['None']}",
        f"   - `raw_rov_points`: Dict of {len(raw_rov_store)} mattresses with ACTUAL unadjusted ROV survey points from Setup Panel 4 (`keys`: {sorted(list(raw_rov_store.keys())) or ['None']}; note: `ledger[i]` c1..c4 are post-processed submittal coords)",
        "",
        "3. PRE-LOADED HELPER FUNCTIONS & LIBRARIES:",
        "   - Libraries ready in scope: `np`, `plt`, `mpatches`, `patheffects`, `PdfPages`, `math`, `re`, `json`, `textwrap`, `datetime`, `io`",
        "   - `get_boxes(crossing_id, target_box_id=None)` -> dict of crossing design boxes `{box_id: {'design_e', 'design_n', 'bearing', 'azimuth', 'corners' (4x2 np.ndarray), 'u_long', 'u_short'}}`",
        "   - `load_bathy(crossing_id)` -> `(N, 3)` float np.ndarray of `[E, N, Z]` bathy soundings (empty `(0, 3)` if none uploaded)",
        "   - `load_cad(crossing_id)` -> list of `[E, N]` polylines for that crossing",
        "   - `idw_interpolate(src_xy, src_z, query_xy, power=2.0)` -> interpolated Z array",
        "   - `box_corners_cw(ce, cn, az_deg, length=6.0, width=3.0)` -> `(corners_4x2, u_long, u_short)`",
        "   - `draw_north_arrow(ax, x_lim, y_lim, north_angle_deg=0.0, sub_label='Grid N')`",
        "   - `plot_seabed_layer(ax, seabed_xyz, x_lim, y_lim, is_zoomed=False, show_contours=True, contour_interval=0.05, show_soundings=True, spot_spacing=2.0, bathy_source='SURVEY_BATHY')`",
        "   - `plot_cad_background(ax, cad_polylines, is_local=False, des_e=0.0, des_n=0.0, u_short=None, u_long=None)`",
        "   - `norm_mti_date(val)` -> `'YYYY-MM-DD'` string",
        "   - `get_raw_rov_corners(box_id)` -> `(corners_4x2_cw, pt_ids_cw, z_vals_cw)` in clockwise NW, NE, SE, SW order from Setup Panel 4 `(None, None, None)` if absent",
        "   - `get_raw_rov_points(box_id)` -> list of all raw ROV fix dicts `[{'pt_id', 'quad', 'e', 'n', 'z'}, ...]` for `box_id`",
        "",
        "4. OUTPUT CONTRACT (REQUIRED AT END OF SCRIPT):",
        "   - Append every Matplotlib figure page in order to `OUTPUT_FIGS` (e.g., `OUTPUT_FIGS.append(fig)`).",
        "   - Set `OUTPUT_FILENAME = f\"{TODAY_YYYYMMDD}_MTI_<ShortDescriptiveName>.pdf\"` (must start with `YYYYMMDD_`).",
        "   - Do NOT call `plt.show()` or `sys.exit()`."
    ]
    return "\n".join(ctx_lines)

def _strip_code_fences(raw_code):
    s = str(raw_code or "").strip()
    s = re.sub(r"^```(?:python|py)?\s*\n", "", s, flags=re.I)
    s = re.sub(r"\n```\s*$", "", s)
    return s.strip()

def execute_adhoc_chart_script(
    script_code, st_data, catalog_list, workspace_dir="workspace",
    surveyor_name="Duty Surveyor", custom_filename=""
):
    os.makedirs(workspace_dir, exist_ok=True)
    clean_code = _strip_code_fences(script_code)
    if not clean_code:
        return {"status": "error", "message": "Script is empty.", "logs": ""}

    plt.close("all")
    ledger = list((st_data or {}).get("ledger") or [])
    raw_rov_store = load_raw_rov_store(st_data, workspace_dir, None, ledger, catalog_list)
    raw_logs = extract_all_mti_logs(st_data or {})
    parsed_logs = [parse_log_entry_fields(lg, surveyor_name) for lg in raw_logs]
    cats = list(catalog_list.values()) if isinstance(catalog_list, dict) else list(catalog_list or [])

    now_utc = datetime.utcnow()
    today_iso = now_utc.strftime("%Y-%m-%d")
    today_ymd = now_utc.strftime("%Y%m%d")

    def _get_boxes(crossing_id="CR-A1_L1", target_box_id=""):
        t_id = target_box_id or f"{crossing_id.split('_')[0]}_M1"
        return build_crossing_boxes_from_catalog(cats, crossing_id, t_id, workspace_dir)

    def _load_bathy(crossing_id="CR-A1_L1"):
        arr, _ = get_or_build_seabed_xyz(workspace_dir, crossing_id, {})
        return arr

    def _load_cad(crossing_id="CR-A1_L1"):
        return load_cad_bg_polylines(workspace_dir, crossing_id)

    output_figs = []
    stdout_buf = io.StringIO()

    exec_ns = {
        "__builtins__": __builtins__,
        "os": os, "io": io, "re": re, "gc": gc, "json": json, "math": math,
        "textwrap": textwrap, "datetime": datetime,
        "np": np, "plt": plt, "matplotlib": matplotlib,
        "mpatches": mpatches, "patheffects": patheffects, "PdfPages": PdfPages,
        "st": st_data or {},
        "ledger": ledger,
        "logs": raw_logs,
        "raw_logs": raw_logs,
        "parsed_logs": parsed_logs,
        "catalog": cats,
        "AREA_LOCATIONS": list(AREA_LOCATIONS),
        "CROSSING_SCOPES": list(CROSSING_SCOPES),
        "WORKSPACE_DIR": workspace_dir,
        "SURVEYOR_NAME": surveyor_name,
        "TODAY_ISO": today_iso,
        "TODAY_YYYYMMDD": today_ymd,
        "get_boxes": _get_boxes,
        "load_bathy": _load_bathy,
        "load_cad": _load_cad,
        "idw_interpolate": idw_interpolate,
        "box_corners_cw": _box_corners_cw,
        "draw_north_arrow": draw_north_arrow,
        "plot_seabed_layer": plot_seabed_layer,
        "plot_cad_background": plot_cad_background,
        "norm_mti_date": norm_mti_date,
        "raw_rov_points": raw_rov_store,
        "get_raw_rov_corners": lambda b_id: get_raw_rov_corners_tuple(raw_rov_store, b_id),
        "get_raw_rov_points": lambda b_id: list((raw_rov_store.get(str(b_id or "").strip().upper()) or {}).get("points") or []),
        "OUTPUT_FIGS": output_figs,
        "OUTPUT_PDF_BYTES": None,
        "OUTPUT_FILENAME": custom_filename or f"{today_ymd}_MTI_AdHoc_Chart.pdf",
    }

    try:
        compiled = compile(clean_code, "<adhoc_mti_script>", "exec")
        with contextlib.redirect_stdout(stdout_buf):
            exec(compiled, exec_ns, exec_ns)
    except Exception:
        tb_str = traceback.format_exc()
        plt.close("all"); gc.collect()
        return {
            "status": "error",
            "message": "Script execution failed. Check traceback below.",
            "logs": (stdout_buf.getvalue() + "\n" + tb_str).strip()
        }

    raw_fn = str(custom_filename or exec_ns.get("OUTPUT_FILENAME") or f"{today_ymd}_MTI_AdHoc_Chart.pdf").strip()
    safe_fn = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(raw_fn))
    if not safe_fn.lower().endswith(".pdf"):
        safe_fn += ".pdf"
    if not re.match(r"^\d{8}_", safe_fn):
        safe_fn = f"{today_ymd}_{safe_fn}"

    pdf_bytes = exec_ns.get("OUTPUT_PDF_BYTES")
    figs = list(exec_ns.get("OUTPUT_FIGS") or [])
    if not figs and not pdf_bytes:
        figs = [plt.figure(num) for num in plt.get_fignums()]

    if not figs and not pdf_bytes:
        plt.close("all"); gc.collect()
        return {
            "status": "error",
            "message": "Script finished without producing any Matplotlib figures (`OUTPUT_FIGS.append(fig)`) or `OUTPUT_PDF_BYTES`.",
            "logs": stdout_buf.getvalue().strip()
        }

    preview_png_b64 = ""
    if figs:
        buf_png = io.BytesIO()
        figs[0].savefig(buf_png, format="png", dpi=125)
        preview_png_b64 = base64.b64encode(buf_png.getvalue()).decode("ascii")

        if not pdf_bytes:
            buf_pdf = io.BytesIO()
            with PdfPages(buf_pdf) as pdf_pages:
                for f in figs:
                    pdf_pages.savefig(f, dpi=150)
            pdf_bytes = buf_pdf.getvalue()

    page_count = len(figs) if figs else 1
    for f in figs:
        try:
            f.clf(); plt.close(f)
        except Exception:
            pass
    plt.close("all"); gc.collect()

    out_path = os.path.join(workspace_dir, safe_fn)
    latest_path = os.path.join(workspace_dir, "latest_MTI_AdHoc_Chart.pdf")
    open(out_path, "wb").write(pdf_bytes)
    open(latest_path, "wb").write(pdf_bytes)

    return {
        "status": "ok",
        "filename": safe_fn,
        "page_count": page_count,
        "image_b64": preview_png_b64,
        "logs": stdout_buf.getvalue().strip() or f"Rendered {page_count} page(s) -> {safe_fn}"
    }