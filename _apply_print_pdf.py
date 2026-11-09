import os, re, glob, ast, subprocess

print("=== [1/3] Updating mti_4panel_reports.py (Remove Chart Scales, A4 Landscape, +2 Font Size) ===")
with open("_reports_landscape.py", "r", encoding="utf-8-sig") as f:
    r_txt = f.read().lstrip("\ufeff")
ast.parse(r_txt)
with open("mti_4panel_reports.py", "w", encoding="utf-8") as f:
    f.write(r_txt)
print("  -> mti_4panel_reports.py updated & AST-verified.")

print("=== [2/3] Updating mti_4panel_a3.py (Merge Page 1 A3 Landscape + Page 2 A4 Landscape into Print PDF) ===")
if os.path.exists("mti_4panel_a3.py"):
    a3_txt = open("mti_4panel_a3.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    if "from matplotlib.backends.backend_pdf import PdfPages" not in a3_txt:
        a3_txt = a3_txt.replace("import matplotlib.pyplot as plt", "import matplotlib.pyplot as plt\nfrom matplotlib.backends.backend_pdf import PdfPages", 1)

    a3_txt = a3_txt.replace(
        "show_contours=True, contour_interval=0.05, show_soundings=True, spot_spacing=2.0, save_pdf=True",
        "show_contours=True, contour_interval=0.05, show_soundings=True, spot_spacing=2.0, save_pdf=True, custom_report_md=None"
    )

    old_save_tail = re.search(r"buf_png = io\.BytesIO\(\).*?return png_bytes, pdf_bytes", a3_txt, flags=re.S)
    new_save_tail = """buf_png = io.BytesIO()
    fig.savefig(buf_png, format="png", dpi=125)
    png_bytes = buf_png.getvalue()
    pdf_bytes = b""
    if save_pdf:
        from mti_4panel_reports import render_a4_landscape_figures, build_structured_report_markdown
        buf_pdf = io.BytesIO()
        with PdfPages(buf_pdf) as pdf_pages:
            pdf_pages.savefig(fig, dpi=150)
            fig.clf(); plt.close(fig); gc.collect()
            rep_md_use = custom_report_md or build_structured_report_markdown(metrics, include_history, ledger_list, scale_p1, scale_p2)
            for f_a4 in render_a4_landscape_figures(metrics, rep_md_use):
                pdf_pages.savefig(f_a4, dpi=150)
                f_a4.clf(); plt.close(f_a4)
        plt.close('all'); gc.collect()
        pdf_bytes = buf_pdf.getvalue()
    else:
        fig.clf(); plt.close(fig); plt.close('all'); gc.collect()

    for fn in ("latest_A3_4Panel_Chart", metrics["base_filename"]):
        open(os.path.join(workspace_dir, fn + ".png"), "wb").write(png_bytes)
        if pdf_bytes:
            open(os.path.join(workspace_dir, fn + ".pdf"), "wb").write(pdf_bytes)
    return png_bytes, pdf_bytes"""

    if old_save_tail:
        a3_txt = a3_txt[:old_save_tail.start()] + new_save_tail
    ast.parse(a3_txt)
    open("mti_4panel_a3.py", "w", encoding="utf-8").write(a3_txt)
    print("  -> mti_4panel_a3.py updated & AST-verified.")

print("=== [3/3] Updating mti_blueprint.py ([Print PDF] Button & Report Edit Sync) ===")
if os.path.exists("mti_blueprint.py"):
    b_txt = open("mti_blueprint.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")

    if '_purge_cached_pdfs()\n    return jsonify({"status": "ok", "base_filename"' not in b_txt:
        b_txt = b_txt.replace(
            'return jsonify({"status": "ok", "base_filename": metrics.get("base_filename")})',
            '_purge_cached_pdfs()\n    return jsonify({"status": "ok", "base_filename": metrics.get("base_filename")})'
        )

    b_txt = b_txt.replace(
        'spot_spacing", 2.0), save_pdf=True)',
        'spot_spacing", 2.0), save_pdf=True, custom_report_md=rep_md or None)'
    )

    b_txt = b_txt.replace(
        '<a id="dlA3Pdf" href="/mti/download_a3_pdf" class="btn btn-sm btn-danger fw-bold"><i class="fas fa-file-pdf me-1"></i>A3 Chart PDF</a>',
        '<a id="dlA3Pdf" href="/mti/download_a3_pdf" class="btn btn-sm btn-danger fw-bold" title="Download 2-Page Landscape Print PDF (Page 1: A3 Chart + Page 2: A4 Report)"><i class="fas fa-print me-1"></i>Print PDF</a>'
    )
    b_txt = b_txt.replace(
        '<a id="dlA4Pdf" href="/mti/download_a4_pdf" class="btn btn-sm btn-warning text-dark fw-bold"><i class="fas fa-file-alt me-1"></i>A4 Report PDF</a>',
        '<a id="dlA4Pdf" href="/mti/download_a4_pdf" style="display:none;"></a>'
    )
    b_txt = b_txt.replace(
        'Apply Edits to A4 PDF &amp; Word (.docx)',
        'Apply Edits to Print PDF &amp; Word (.docx)'
    ).replace(
        'Saved A4 PDF & Word!',
        'Saved Print PDF & Word!'
    )

    ast.parse(b_txt)
    open("mti_blueprint.py", "w", encoding="utf-8").write(b_txt)
    print("  -> mti_blueprint.py updated & AST-verified.")

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try: os.remove(p)
    except Exception: pass

sync_py = "python" if os.path.exists(".venv/Scripts/python.exe") else "py"
subprocess.run([sync_py, "sync.py", "feat(mti): remove redundant Chart Scales line, merge A3+A4 into 2-page Landscape Print PDF, and increase A4 font size +2"], check=False)
