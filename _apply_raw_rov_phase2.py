import os, re, glob, ast, subprocess

print("=== [1/3] Mounting Panel 4 (Raw ROV Points per As-Laid Mattress) onto /mti/setup ===")
if not os.path.exists("mti_blueprint.py"):
    raise SystemExit("mti_blueprint.py not found!")

with open("_raw_rov_panel4.html", "r", encoding="utf-8-sig") as f:
    panel4_html = f.read().lstrip("\ufeff").strip()

b_txt = open("mti_blueprint.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")

b_txt = re.sub(
    r"\s*<!-- RAW_ROV_PANEL4_START -->.*?<!-- RAW_ROV_PANEL4_END -->",
    lambda _m: "",
    b_txt,
    flags=re.S
)

injected = False
for q3 in ('"' * 3, "'" * 3):
    pat_setup = re.compile(r"(SETUP_HTML_TEMPLATE\s*=\s*r?" + q3 + r".*?)(</body>)", re.S)
    if pat_setup.search(b_txt):
        b_txt = pat_setup.sub(
            lambda m: m.group(1) + "\n" + panel4_html + "\n" + m.group(2),
            b_txt,
            count=1
        )
        injected = True
        break

if os.path.exists("templates/mti_setup.html"):
    t_setup = open("templates/mti_setup.html", "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    t_setup = re.sub(
        r"\s*<!-- RAW_ROV_PANEL4_START -->.*?<!-- RAW_ROV_PANEL4_END -->",
        lambda _m: "",
        t_setup,
        flags=re.S
    )
    if "</body>" in t_setup:
        t_setup = t_setup.replace("</body>", panel4_html + "\n</body>", 1)
    else:
        t_setup = t_setup.rstrip() + "\n" + panel4_html + "\n"
    open("templates/mti_setup.html", "w", encoding="utf-8").write(t_setup)
    injected = True
    print("  -> Injected Panel 4 into templates/mti_setup.html")

if not injected:
    raise SystemExit("Could not locate SETUP_HTML_TEMPLATE or templates/mti_setup.html!")

ast.parse(b_txt)
open("mti_blueprint.py", "w", encoding="utf-8").write(b_txt)
print("  -> mti_blueprint.py updated & AST-verified.")

print("=== [2/3] Verifying MTI Modules AST & Clearing Stale PDF Cache ===")
for mod_fn in ("mti_raw_rov.py", "mti_adhoc.py", "mti_4panel_math.py", "mti_4panel_a3.py", "mti_4panel_reports.py"):
    if os.path.exists(mod_fn):
        m_src = open(mod_fn, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
        ast.parse(m_src)
        open(mod_fn, "w", encoding="utf-8").write(m_src)
        print(f"  -> AST OK: {mod_fn}")

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try:
        os.remove(p)
    except Exception:
        pass

print("=== [3/3] Syncing Panel 4 Raw ROV Setup (Phase 1 + Phase 2) to GitHub & Render ===")
sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else ("python" if os.path.exists("sync.py") else "py")
subprocess.run([sync_py, "sync.py", "feat(mti-setup): add Panel 4 Raw ROV Points per As-Laid Mattress input & storage"], check=False)
print("\nPHASE 2 COMPLETE! Open /mti/setup and scroll below Panel 3 to use Panel 4.")