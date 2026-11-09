import os, re, gc, ast, subprocess

# 1. Add fig.clf() and gc.collect() after plt.close(fig) in mti_4panel_a3.py
if os.path.exists("mti_4panel_a3.py"):
    txt = open("mti_4panel_a3.py", "r", encoding="utf-8-sig").read()
    if "import gc" not in txt:
        txt = "import gc\n" + txt
    if "gc.collect()" not in txt:
        txt = txt.replace(
            "plt.close(fig)",
            "fig.clf(); plt.close(fig); plt.close('all'); gc.collect()"
        )
    ast.parse(txt)
    open("mti_4panel_a3.py", "w", encoding="utf-8").write(txt)
    print("Hardened Matplotlib memory release in: mti_4panel_a3.py")

# 2. Add fig.clf() and gc.collect() after plt.close(fig) in mti_4panel_reports.py
if os.path.exists("mti_4panel_reports.py"):
    txt = open("mti_4panel_reports.py", "r", encoding="utf-8-sig").read()
    if "import gc" not in txt:
        txt = "import gc\n" + txt
    if "gc.collect()" not in txt:
        txt = txt.replace(
            "plt.close(fig)",
            "fig.clf(); plt.close(fig); plt.close('all'); gc.collect()"
        )
    ast.parse(txt)
    open("mti_4panel_reports.py", "w", encoding="utf-8").write(txt)
    print("Hardened Matplotlib memory release in: mti_4panel_reports.py")

# 3. Cap IDW source points at 600 in mti_4panel_math.py so large .xyz uploads never spike RAM
if os.path.exists("mti_4panel_math.py"):
    txt = open("mti_4panel_math.py", "r", encoding="utf-8-sig").read()
    txt = txt.replace("if len(src_xy) > 1200:", "if len(src_xy) > 600:")
    txt = txt.replace("len(src_xy) // 1200", "len(src_xy) // 600")
    ast.parse(txt)
    open("mti_4panel_math.py", "w", encoding="utf-8").write(txt)
    print("Capped IDW interpolation RAM ceiling in: mti_4panel_math.py")

# 4. Optimize Procfile to use 1 worker + 4 threads + max-requests worker recycling
if os.path.exists("Procfile"):
    pf = open("Procfile", "r", encoding="utf-8-sig").read().strip()
    if "gunicorn" in pf and "--workers" not in pf and "-w " not in pf:
        pf = "web: gunicorn app:app --workers 1 --threads 4 --timeout 120 --max-requests 80 --max-requests-jitter 15\n"
        open("Procfile", "w", encoding="utf-8").write(pf)
        print("Optimized Gunicorn worker memory config in: Procfile")

subprocess.run(["py", "sync.py", "perf(memory): release Matplotlib raster buffers with gc.collect() and cap Gunicorn/IDW RAM for Render 512MB limit"], check=False)
