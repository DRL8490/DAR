import os, re, subprocess

with open("_mti_remarks_toggle.html", "r", encoding="utf-8-sig") as f:
    toggle_block = f.read().lstrip("\ufeff").strip()

t_dash = "templates/mti_dashboard.html"
if not os.path.exists(t_dash):
    raise SystemExit("templates/mti_dashboard.html not found! Run this inside your DAR project root.")

raw_t = open(t_dash, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
raw_t = re.sub(r"\s*<!-- MTI_REMARKS_TOGGLE_START -->.*?<!-- MTI_REMARKS_TOGGLE_END -->", lambda _m: "", raw_t, flags=re.S)
raw_t = re.sub(r'\s*<script id="mtiRemarksToggleUpgrade">.*?</script>', lambda _m: "", raw_t, flags=re.S)

if "</body>" in raw_t:
    raw_t = raw_t.replace("</body>", toggle_block + "\n</body>", 1)
elif "{% endblock %}" in raw_t:
    idx = raw_t.rfind("{% endblock %}")
    raw_t = raw_t[:idx] + toggle_block + "\n" + raw_t[idx:]
else:
    raw_t = raw_t.rstrip() + "\n" + toggle_block + "\n"

open(t_dash, "w", encoding="utf-8").write(raw_t)
print("  -> Added Hide/Show Remarks toggle button to templates/mti_dashboard.html")

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else ("python" if os.path.exists("sync.py") else "py")
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti): add Hide/Show Remarks column toggle button on MTI ledger"], check=False)