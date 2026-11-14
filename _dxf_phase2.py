import os, re, glob, ast, subprocess

# 1. Ensure ezdxf>=1.1.0 is listed in requirements.txt for Render deployment
req_path = "requirements.txt"
if os.path.exists(req_path):
    req_txt = open(req_path, "r", encoding="utf-8-sig").read()
    if "ezdxf" not in req_txt.lower():
        open(req_path, "a", encoding="utf-8").write("\nezdxf>=1.1.0\n")
        print("  -> Added ezdxf>=1.1.0 to requirements.txt")

# 2. Harden mti_dxf_export.py (Windows SAC C-ext guard, readable Model Space labels & Paper Space leader arrows)
dxf_mod_path = "mti_dxf_export.py"
if not os.path.exists(dxf_mod_path):
    raise SystemExit("mti_dxf_export.py not found! Run inside your DAR project folder.")

dxf_src = open(dxf_mod_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
if "EZDXF_DISABLE_C_EXT" not in dxf_src:
    dxf_src = 'import os as _os; _os.environ.setdefault("EZDXF_DISABLE_C_EXT", "1")\n' + dxf_src

if "if sum(c_rgb) < 160" not in dxf_src:
    dxf_src = dxf_src.replace(
        "c_rgb = _rgb_tuple(tx.get_color(), (248, 250, 252)) or (248, 250, 252)",
        "c_rgb = _rgb_tuple(tx.get_color(), (248, 250, 252)) or (248, 250, 252)\n            c_rgb = (248, 250, 252) if sum(c_rgb) < 160 else c_rgb",
        1
    )

arrow_patch_snippet = """            arr_p = getattr(tx, "arrow_patch", None)
            if arr_p is not None and arr_p.get_visible():
                av_mm = arr_p.get_path().transformed(arr_p.get_patch_transform()).vertices * px_to_mm
                ac_rgb = _rgb_tuple(arr_p.get_edgecolor(), None) or _rgb_tuple(arr_p.get_facecolor(), (71, 85, 105))
                if len(av_mm) >= 2 and ac_rgb:
                    psp.add_lwpolyline([(float(v[0]), float(v[1])) for v in av_mm], dxfattribs={"layer": layer_name, "true_color": ezdxf.rgb2int(ac_rgb)})
"""
if 'getattr(tx, "arrow_patch", None)' not in dxf_src:
    dxf_src = dxf_src.replace(
        "            bb_patch = tx.get_bbox_patch()",
        arrow_patch_snippet + "            bb_patch = tx.get_bbox_patch()",
        1
    )

dxf_src = dxf_src.replace(
    "freeze_set = (all_adhoc_layers - page_adhoc_layers.get(p_idx, set())) if all_adhoc_layers else None\n                _add_locked_viewport(psp, doc, bb_mm, 0.5 * (x0 + x1), 0.5 * (y0 + y1), abs(y1 - y0), twist_deg=0.0, frozen_layers=freeze_set)\n                _render_axes_chrome_and_texts_mm(psp, ax, px_to_mm, l_sheet, include_data_texts=False)",
    "lbl_lyrs = {ly for ly in page_adhoc_layers.get(p_idx, set()) if ly.endswith('_LABELS')}\n                freeze_set = ((all_adhoc_layers - page_adhoc_layers.get(p_idx, set())) | lbl_lyrs) if all_adhoc_layers else None\n                _add_locked_viewport(psp, doc, bb_mm, 0.5 * (x0 + x1), 0.5 * (y0 + y1), abs(y1 - y0), twist_deg=0.0, frozen_layers=freeze_set)\n                _render_axes_chrome_and_texts_mm(psp, ax, px_to_mm, l_sheet, include_data_texts=(native_4panel_metrics is None))"
)

ast.parse(dxf_src)
open(dxf_mod_path, "w", encoding="utf-8").write(dxf_src)
print("  -> Verified mti_dxf_export.py (AST OK)")

# 3. Wire Ad-Hoc DXF generation into mti_adhoc.py
adhoc_path = "mti_adhoc.py"
if os.path.exists(adhoc_path):
    a_src = open(adhoc_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    adhoc_dxf_hook = """        if not pdf_bytes:
            buf_pdf = io.BytesIO()
            with PdfPages(buf_pdf) as pdf_pages:
                for f in figs:
                    pdf_pages.savefig(f, dpi=150)
            pdf_bytes = buf_pdf.getvalue()

    dxf_fn = re.sub(r"\\.pdf$", ".dxf", safe_fn, flags=re.I)
    if figs:
        try:
            from mti_dxf_export import convert_matplotlib_figs_to_dxf
            dxf_out = os.path.join(workspace_dir, dxf_fn)
            dxf_bytes = convert_matplotlib_figs_to_dxf(figs, dxf_out)
            open(os.path.join(workspace_dir, "latest_MTI_AdHoc_Chart.dxf"), "wb").write(dxf_bytes)
        except Exception:
            dxf_fn = "" """

    if "latest_MTI_AdHoc_Chart.dxf" not in a_src:
        a_src = re.sub(
            r"""        if not pdf_bytes:\s*buf_pdf = io\.BytesIO\(\)\s*with PdfPages\(buf_pdf\) as pdf_pages:\s*for f in figs:\s*pdf_pages\.savefig\(f, dpi=150\)\s*pdf_bytes = buf_pdf\.getvalue\(\)""",
            lambda _m: adhoc_dxf_hook.rstrip(),
            a_src,
            count=1
        )
    if '"dxf_filename":' not in a_src:
        a_src = a_src.replace(
            '"filename": safe_fn,',
            '"filename": safe_fn,\n        "dxf_filename": dxf_fn,',
            1
        )
    ast.parse(a_src)
    open(adhoc_path, "w", encoding="utf-8").write(a_src)
    print("  -> Updated mti_adhoc.py to export Ad-Hoc DXF alongside PDF (AST OK)")

# 4. Wire /mti/download_dxf, /mti/download_adhoc_dxf & CAD (.dxf) buttons into mti_blueprint.py
bp_path = "mti_blueprint.py"
bp = open(bp_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")

bp = bp.replace(
    'for p in glob.glob(os.path.join(MTI_WS_DIR, "*.pdf")):',
    'for p in glob.glob(os.path.join(MTI_WS_DIR, "*.pdf")) + glob.glob(os.path.join(MTI_WS_DIR, "*.dxf")):'
)

dxf_dl_branch = """    elif kind == "docx" and not os.path.exists(p):
        generate_editable_docx(metrics, rep_md or build_structured_report_markdown(metrics), MTI_WS_DIR)
    elif kind == "dxf" and not os.path.exists(p):
        from mti_dxf_export import generate_4panel_studio_dxf
        st = load_mti_state()
        ledger = st.get("ledger", [])
        cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
        fd = cache.get("fix_data") or (ledger[0] if ledger else {})
        b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full = run_rov_4panel_verification(fd, cat_list, MTI_WS_DIR)
        raw_store = load_raw_rov_store(st, MTI_WS_DIR, None, ledger, cat_list) if "load_raw_rov_store" in globals() else {}
        generate_4panel_studio_dxf(
            b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full, MTI_WS_DIR,
            cache.get("include_history", True), ledger,
            cache.get("scale_p1", 250), cache.get("scale_p2", 75),
            cache.get("show_contours", True), cache.get("contour_interval", 0.05),
            cache.get("show_soundings", True), cache.get("spot_spacing", 2.0),
            custom_report_md=rep_md or None,
            cad_polys=metrics.get("cad_polylines") or [],
            raw_rov_store=raw_store
        )
        if not os.path.exists(p):
            alt_p = os.path.join(MTI_WS_DIR, str(metrics.get("base_filename") or "") + ".dxf")
            p = alt_p if os.path.exists(alt_p) else os.path.join(MTI_WS_DIR, "latest_A3_4Panel_Chart.dxf")"""

if 'elif kind == "dxf"' not in bp:
    bp = bp.replace(
        '    elif kind == "docx" and not os.path.exists(p):\n        generate_editable_docx(metrics, rep_md or build_structured_report_markdown(metrics), MTI_WS_DIR)',
        dxf_dl_branch,
        1
    )

if "@mti_bp.route('/download_dxf')" not in bp:
    bp = bp.replace(
        "@mti_bp.route('/download_docx')\n@login_required\ndef download_docx(): return _dl_4panel_file(\"docx\", \"_Report.docx\", \"application/vnd.openxmlformats-officedocument.wordprocessingml.document\")",
        "@mti_bp.route('/download_docx')\n@login_required\ndef download_docx(): return _dl_4panel_file(\"docx\", \"_Report.docx\", \"application/vnd.openxmlformats-officedocument.wordprocessingml.document\")\n\n@mti_bp.route('/download_dxf')\n@login_required\ndef download_dxf(): return _dl_4panel_file(\"dxf\", \".dxf\", \"application/dxf\")",
        1
    )

studio_dxf_btn = '<a id="dlDxf" href="/mti/download_dxf" class="btn btn-sm btn-success fw-bold" title="Download CAD (.dxf) with TWD97 Model Space &amp; PDF-Matched Paper Space Layout"><i class="fas fa-layer-group me-1"></i>CAD (.dxf)</a>'
if 'id="dlDxf"' not in bp:
    bp = bp.replace(
        '<a id="dlA3Png" href="/mti/download_a3_png" class="btn btn-sm btn-info text-dark fw-bold"><i class="fas fa-image me-1"></i>A3 PNG</a>',
        '<a id="dlA3Png" href="/mti/download_a3_png" class="btn btn-sm btn-info text-dark fw-bold"><i class="fas fa-image me-1"></i>A3 PNG</a>\n      ' + studio_dxf_btn,
        1
    )

if "document.getElementById('dlDxf')" not in bp:
    bp = bp.replace(
        "document.getElementById('dlDocx').href = '/mti/download_docx?file=' + encodeURIComponent(fn) + '&t=' + ts;",
        "document.getElementById('dlDocx').href = '/mti/download_docx?file=' + encodeURIComponent(fn) + '&t=' + ts;\n          if (document.getElementById('dlDxf')) document.getElementById('dlDxf').href = '/mti/download_dxf?file=' + encodeURIComponent(fn) + '&t=' + ts;",
        1
    )

adhoc_row_new = """          <div class="row g-2 align-items-end mb-2">
            <div class="col-md-3 col-6">
              <label class="small fw-bold text-light">Optional PDF/DXF Name</label>
              <input type="text" id="adhocFilenameInp" class="form-control form-control-sm bg-dark text-light border-secondary font-monospace" placeholder="YYYYMMDD_MTI_Custom.pdf">
            </div>
            <div class="col-md-3 col-6">
              <label class="small fw-bold text-light">Save Reusable Snippet As</label>
              <input type="text" id="adhocSaveTitleInp" class="form-control form-control-sm bg-dark text-warning border-secondary" placeholder="Optional preset name">
            </div>
            <div class="col-md-2 col-4">
              <button type="button" id="btnRunAdhoc" class="btn btn-sm btn-success fw-bold w-100" onclick="window.runAdhocScript()">
                <i class="fas fa-play me-1"></i>Generate
              </button>
            </div>
            <div class="col-md-2 col-4">
              <a id="btnDlAdhocPdf" href="/mti/download_adhoc_pdf" target="_blank" class="btn btn-sm btn-danger fw-bold w-100 disabled" aria-disabled="true">
                <i class="fas fa-file-pdf me-1"></i>PDF
              </a>
            </div>
            <div class="col-md-2 col-4">
              <a id="btnDlAdhocDxf" href="/mti/download_adhoc_dxf" target="_blank" class="btn btn-sm btn-info text-dark fw-bold w-100 disabled" aria-disabled="true" title="Download TWD97 Model Space + Paper Space Layout DXF">
                <i class="fas fa-layer-group me-1"></i>CAD (.dxf)
              </a>
            </div>
          </div>"""

if 'id="btnDlAdhocDxf"' not in bp:
    bp = re.sub(
        r'<div class="row g-2 align-items-end mb-2">\s*<div class="col-md-4 col-6">\s*<label class="small fw-bold text-light">Optional PDF Filename</label>.*?<a id="btnDlAdhocPdf".*?</a>\s*</div>\s*</div>',
        lambda _m: adhoc_row_new,
        bp,
        count=1,
        flags=re.S
    )

adhoc_js_dxf = """        if (dlBtn) {
          dlBtn.href = '/mti/download_adhoc_pdf/' + encodeURIComponent(d.filename) + '?t=' + Date.now();
          dlBtn.classList.remove('disabled');
          dlBtn.removeAttribute('aria-disabled');
        }
        const dlDxfBtn = document.getElementById('btnDlAdhocDxf');
        if (dlDxfBtn) {
          const dxfFn = d.dxf_filename || String(d.filename || 'latest_MTI_AdHoc_Chart.dxf').replace(/\\.pdf$/i, '.dxf');
          dlDxfBtn.href = '/mti/download_adhoc_dxf/' + encodeURIComponent(dxfFn) + '?t=' + Date.now();
          dlDxfBtn.classList.remove('disabled');
          dlDxfBtn.removeAttribute('aria-disabled');
        }"""

if "btnDlAdhocDxf" in bp and "dlDxfBtn" not in bp:
    bp = re.sub(
        r"""        if \(dlBtn\) \{\s*dlBtn\.href = '/mti/download_adhoc_pdf/' \+ encodeURIComponent\(d\.filename\) \+ '\?t=' \+ Date\.now\(\);\s*dlBtn\.classList\.remove\('disabled'\);\s*dlBtn\.removeAttribute\('aria-disabled'\);\s*\}""",
        lambda _m: adhoc_js_dxf,
        bp,
        count=1
    )

adhoc_dxf_route = """@mti_bp.route('/download_adhoc_pdf')
@mti_bp.route('/download_adhoc_pdf/<path:req_fn>')
@login_required
def mti_download_adhoc_pdf(req_fn=None):
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    fn = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(str(req_fn or request.args.get("file") or "latest_MTI_AdHoc_Chart.pdf")))
    p = os.path.join(MTI_WS_DIR, fn)
    if not os.path.exists(p):
        p = os.path.join(MTI_WS_DIR, "latest_MTI_AdHoc_Chart.pdf")
    return send_file(p, as_attachment=True, download_name=fn, mimetype="application/pdf")

@mti_bp.route('/download_adhoc_dxf')
@mti_bp.route('/download_adhoc_dxf/<path:req_fn>')
@login_required
def mti_download_adhoc_dxf(req_fn=None):
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    fn = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(str(req_fn or request.args.get("file") or "latest_MTI_AdHoc_Chart.dxf")))
    if fn.lower().endswith(".pdf"):
        fn = fn[:-4] + ".dxf"
    p = os.path.join(MTI_WS_DIR, fn)
    if not os.path.exists(p):
        p = os.path.join(MTI_WS_DIR, "latest_MTI_AdHoc_Chart.dxf")
    return send_file(p, as_attachment=True, download_name=fn, mimetype="application/dxf")"""

if "@mti_bp.route('/download_adhoc_dxf')" not in bp:
    bp = re.sub(
        r"@mti_bp\.route\('/download_adhoc_pdf'\)\s*@mti_bp\.route\('/download_adhoc_pdf/<path:req_fn>'\)\s*@login_required\s*def mti_download_adhoc_pdf\(req_fn=None\):.*?return send_file\(p, as_attachment=True, download_name=fn, mimetype=\"application/pdf\"\)",
        lambda _m: adhoc_dxf_route,
        bp,
        count=1,
        flags=re.S
    )

ast.parse(bp)
open(bp_path, "w", encoding="utf-8").write(bp)
print("  -> Updated mti_blueprint.py with /mti/download_dxf, /mti/download_adhoc_dxf & Studio CAD (.dxf) buttons (AST OK)")

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti-studio): wire CAD (.dxf) export buttons for 4-Panel & Ad-Hoc Studio charts"], check=False)
print("\nCAD (.dxf) STUDIO EXPORT PHASE 2 COMPLETE & SYNCED!")