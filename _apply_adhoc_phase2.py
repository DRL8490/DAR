import os, re, glob, ast, subprocess

print("=== [1/3] Injecting Ad-Hoc PDF Script Button & Modal UI into /mti/studio (mti_blueprint.py) ===")
if not os.path.exists("mti_blueprint.py"):
    raise SystemExit("mti_blueprint.py not found!")

with open("_adhoc_modal_ui.html", "r", encoding="utf-8-sig") as f:
    modal_html = f.read().lstrip("\ufeff").strip()

b_txt = open("mti_blueprint.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")

b_txt = re.sub(
    r"\s*<!-- ADHOC_STUDIO_START -->.*?<!-- ADHOC_STUDIO_END -->",
    lambda _m: "",
    b_txt,
    flags=re.S
)

setup_btn_anchor = '<a href="/mti/setup" target="_blank" class="btn btn-sm btn-outline-info fw-bold me-1"><i class="fas fa-sliders-h me-1"></i>Survey Setup (CAD / Design / Bathy)</a>'
adhoc_top_btn = '<button type="button" id="btnOpenAdhocModal" class="btn btn-sm btn-warning text-dark fw-bold me-1" onclick="window.openAdhocStudio()" title="Open Ad-Hoc Gemini Context &amp; Python PDF Chart Generator"><i class="fas fa-terminal me-1"></i>Ad-Hoc PDF Script</button>'

if 'id="btnOpenAdhocModal"' not in b_txt and setup_btn_anchor in b_txt:
    b_txt = b_txt.replace(setup_btn_anchor, setup_btn_anchor + "\n      " + adhoc_top_btn, 1)

pat_studio = re.compile(r'(STUDIO_HTML_TEMPLATE\s*=\s*r?""".*?)(</body>\s*</html>""")', re.S)
if not pat_studio.search(b_txt):
    raise SystemExit("Could not locate STUDIO_HTML_TEMPLATE closing tag in mti_blueprint.py!")

b_txt = pat_studio.sub(
    lambda m: m.group(1) + "\n" + modal_html + "\n" + m.group(2),
    b_txt,
    count=1
)

ast.parse(b_txt)
open("mti_blueprint.py", "w", encoding="utf-8").write(b_txt)
print("  -> mti_blueprint.py updated & AST-verified.")

print("=== [2/3] Verifying mti_adhoc.py & Clearing Stale PDF Cache ===")
if os.path.exists("mti_adhoc.py"):
    a_txt = open("mti_adhoc.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    ast.parse(a_txt)
    open("mti_adhoc.py", "w", encoding="utf-8").write(a_txt)
    print("  -> mti_adhoc.py AST-verified.")

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try:
        os.remove(p)
    except Exception:
        pass

print("=== [3/3] Syncing Ad-Hoc PDF Chart Studio (Phase 1 + Phase 2) to GitHub & Render ===")
sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else ("python" if os.path.exists("sync.py") else "py")
subprocess.run([sync_py, "sync.py", "feat(mti-studio): add Ad-Hoc PDF Script & Gemini Context studio inside /mti/studio"], check=False)
print("\nPHASE 2 COMPLETE! Refresh /mti/studio and click 'Ad-Hoc PDF Script' in the top bar.")