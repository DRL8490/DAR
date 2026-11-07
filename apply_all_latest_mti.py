import os, re, ast, subprocess

# 0. Pull latest changes first so laptop workspace is in sync
subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)

# 1. Update mti_blueprint.py (South bearing +180, remove Swell, Attempted Mattress Placement, Radio USBL only on 4 allowed buttons)
with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")

mc = mc.replace('"bearing": r[4]', '"bearing": round((r[4] + 180.0) % 360.0, 3)')
mc = mc.replace("15.854", "195.854").replace("Brg:15.9", "Brg:195.9")
if "if hdg < 180.0: hdg = round(hdg + 180.0, 3)" not in mc:
    mc = mc.replace(
        "hdg = round((math.degrees(math.atan2(fe - be, fn - bn)) + 360.0) % 360.0, 3)",
        "hdg = round((math.degrees(math.atan2(fe - be, fn - bn)) + 360.0) % 360.0, 3)\n        if hdg < 180.0: hdg = round(hdg + 180.0, 3)"
    )

mc = mc.replace("Recover to Deck", "Attempted Mattress Placement")
mc = mc.replace('[("Wind", env_w), ("Curr", env_c), ("Swell", env_s)]', '[("Wind", env_w), ("Curr", env_c)]')
mc = mc.replace('"Pole USBL"', '"Survey Pole"').replace('"Survey Pole USBL"', '"Survey Pole"')

old_log_line = 'env_w = (request.form.get("env_wind") or "").strip()'
if 'usbl_s =' not in mc and old_log_line in mc:
    mc = mc.replace(
        old_log_line,
        'evt_t = (request.form.get("event_type") or "Pole down").strip()\n    usbl_s = (request.form.get("usbl_sensor") or "").strip() if evt_t in ("ROV & Vessel Ops", "Calib, Setup & TBT", "Survey Issue Reporting", "Survey Issue") else ""\n    ' + old_log_line,
        1
    )
    mc = re.sub(
        r'env_tag = " \| "\.join\(\[f"\{k\}:\{v\}" for k, v in \[.*?\] if v\]\)',
        'env_tag = " | ".join([f"{k}:{v}" for k, v in [("USBL", usbl_s), ("Wind", env_w), ("Curr", env_c)] if v])',
        mc
    )
else:
    mc = re.sub(
        r'usbl_s = \(request\.form\.get\("usbl_sensor"\).*?\)\.strip\(\)(?:\s*if evt_t in .*? else "")?',
        'evt_t = (request.form.get("event_type") or "Pole down").strip()\n    usbl_s = (request.form.get("usbl_sensor") or "").strip() if evt_t in ("ROV & Vessel Ops", "Calib, Setup & TBT", "Survey Issue Reporting", "Survey Issue") else ""',
        mc
    )

ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)
print("1. Updated mti_blueprint.py cleanly!")

# 2. Update templates/mti_dashboard.html, templates/mti_mobile.html, and inline mti_blueprint.py HTML
RADIO_HTML_BLOCK = """<label class="form-label small fw-bold text-primary mb-1">Active USBL *</label>
        <div class="d-flex align-items-center gap-3 p-1 px-2 border border-primary rounded bg-light" style="min-height:31px;">
          <label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">
            <input type="radio" class="form-check-input m-0" name="usbl_sensor" value="Survey Pole" checked> Survey Pole
          </label>
          <label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">
            <input type="radio" class="form-check-input m-0" name="usbl_sensor" value="Vessel"> Vessel
          </label>
        </div>"""

USBL_FILTERED_JS = """<script id="mtiActiveUsblUpgrade">
(function(){
  const USBL_ALLOWED_EVENTS = new Set(['ROV & Vessel Ops', 'Calib, Setup & TBT', 'Survey Issue Reporting', 'Survey Issue']);

  window.toggleEvtUsblBar = function(evtType){
    const show = USBL_ALLOWED_EVENTS.has((evtType || '').trim());
    document.querySelectorAll('.evt-usbl-selector').forEach(function(bar){
      bar.style.display = show ? 'block' : 'none';
      bar.querySelectorAll('input[name="usbl_sensor"]').forEach(function(inp){
        inp.disabled = !show;
      });
    });
  };

  document.addEventListener('DOMContentLoaded', function(){
    ['eventInputForm', 'mobEvtCard'].forEach(function(id){
      const c = document.getElementById(id);
      const form = c ? (c.tagName === 'FORM' ? c : c.querySelector('form')) : null;
      if (form) {
        let bar = form.querySelector('.evt-usbl-selector');
        if (!bar) {
          bar = document.createElement('div');
          bar.className = 'p-2 mb-2 rounded border border-primary evt-usbl-selector';
          bar.style.background = 'rgba(13,110,253,0.07)';
          const firstRow = form.querySelector('.row');
          if (firstRow) firstRow.parentNode.insertBefore(bar, firstRow.nextSibling);
        }
        bar.style.display = 'none';
        bar.innerHTML = '<div class="d-flex flex-wrap justify-content-between align-items-center gap-2">' +
          '<span class="small fw-bold text-primary"><i class="fas fa-satellite-dish me-1"></i>Active USBL:</span>' +
          '<div class="d-flex align-items-center gap-3">' +
            '<label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">' +
              '<input type="radio" class="form-check-input m-0" name="usbl_sensor" value="Survey Pole" checked disabled> Survey Pole' +
            '</label>' +
            '<label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">' +
              '<input type="radio" class="form-check-input m-0" name="usbl_sensor" value="Vessel" disabled> Vessel' +
            '</label>' +
          '</div></div>';
      }
    });

    const origDesk = window.openEventInputBox;
    if (origDesk && !origDesk._usblWrapped) {
      window.openEventInputBox = function(t){ origDesk(t); window.toggleEvtUsblBar(t); };
      window.openEventInputBox._usblWrapped = true;
    }
    const origMob = window.openMobEvt;
    if (origMob && !origMob._usblWrapped) {
      window.openMobEvt = function(t){ origMob(t); window.toggleEvtUsblBar(t); };
      window.openMobEvt._usblWrapped = true;
    }

    const curEvt = document.getElementById('evtTypeInput')?.value || document.getElementById('mEvtType')?.value || 'Pole down';
    window.toggleEvtUsblBar(curEvt);

    document.querySelectorAll('form[action*="add_fix"]').forEach(function(f){
      const existingCtrl = f.querySelector('select[name="usbl_sensor"], .usbl-pill, input[type="hidden"][name="usbl_sensor"]');
      if (existingCtrl) {
        const col = existingCtrl.closest('.col-md-3, .col-md-4, .col-6, .col-12') || existingCtrl.parentNode;
        col.className = 'col-md-3 col-6';
        col.innerHTML = `<label class="form-label small fw-bold text-primary mb-1">Active USBL *</label>
          <div class="d-flex align-items-center gap-3 p-1 px-2 border border-primary rounded bg-light" style="min-height:31px;">
            <label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">
              <input type="radio" class="form-check-input m-0" name="usbl_sensor" value="Survey Pole" checked> Survey Pole
            </label>
            <label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">
              <input type="radio" class="form-check-input m-0" name="usbl_sensor" value="Vessel"> Vessel
            </label>
          </div>`;
        f.querySelectorAll('#inpQaqcE, #inpQaqcN, #inpQaqcBrg').forEach(inp => {
          const p = inp.closest('.col-md-2, .col-md-3');
          if (p) p.className = 'col-md-3 col-6';
        });
      }
    });
  });
})();
</script>"""

for target in ["templates/mti_dashboard.html", "templates/mti_mobile.html", "mti_blueprint.py"]:
    if not os.path.exists(target): continue
    with open(target, "r", encoding="utf-8-sig") as f: txt = f.read()

    txt = txt.replace("Recover to Deck", "Attempted Mattress Placement")
    txt = txt.replace("Environmental Inputs (Wind, Current & Swell)", "Environmental Inputs (Wind & Current)")
    txt = txt.replace("Environmental Inputs (Wind, Current &amp; Swell)", "Environmental Inputs (Wind &amp; Current)")
    txt = re.sub(r'<div class="col-4"><input type="text" name="env_swell"[^>]*></div>', '', txt)
    txt = re.sub(r'<div class="col-4">(\s*<input type="text" name="env_(?:wind|current)")', r'<div class="col-6">\1', txt)

    txt = re.sub(
        r'<label class="form-label small fw-bold text-primary mb-1">Active USBL Used \*</label>\s*<select name="usbl_sensor".*?</select>',
        RADIO_HTML_BLOCK,
        txt,
        flags=re.S
    )

    if 'id="mtiActiveUsblUpgrade"' in txt:
        txt = re.sub(r'<script id="mtiActiveUsblUpgrade">.*?</script>', USBL_FILTERED_JS, txt, flags=re.S)
    elif '</body>' in txt:
        txt = txt.replace('</body>', USBL_FILTERED_JS + '\n</body>', 1)

    if target.endswith(".py"): ast.parse(txt)
    with open(target, "w", encoding="utf-8") as f: f.write(txt)
    print(f"2. Updated {target} with filtered Survey Pole / Vessel radio buttons!")

# 3. Install Agentic iPhone Hot-Patch Runner (.github/workflows/autopatch.yml & hotpatch.py)
os.makedirs(".github/workflows", exist_ok=True)
WORKFLOW_YAML = """name: iPhone Agentic Hot-Patch Runner
on:
  push:
    branches: [ main ]
    paths:
      - 'hotpatch.py'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  run-patch:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Execute hotpatch.py and push changes to Render
        run: |
          if grep -q "^# IDLE_STATE" hotpatch.py; then
            echo "hotpatch.py is in IDLE_STATE. Nothing to run."
            exit 0
          fi
          git config user.name "DRL8490 Mobile Agent"
          git config user.email "daryll.enano@nmdc-group.com"
          python3 hotpatch.py
          printf "# IDLE_STATE - Paste next Python patch script here in the GitHub iOS app and tap Commit!\\n" > hotpatch.py
          git add -A
          git diff --staged --quiet || git commit -m "feat(mobile-agent): execute hotpatch.py and update codebase"
          git push origin HEAD:main
"""
with open(".github/workflows/autopatch.yml", "w", encoding="utf-8") as f:
    f.write(WORKFLOW_YAML)
with open("hotpatch.py", "w", encoding="utf-8") as f:
    f.write("# IDLE_STATE - Paste next Python patch script here in the GitHub iOS app and tap Commit!\n")

print("3. Installed iPhone Agentic Hot-Patch Runner (.github/workflows/autopatch.yml & hotpatch.py)!")
subprocess.run(["py", "sync.py", "feat: use Survey Pole OR Vessel radio buttons only on checked buttons and install iPhone hotpatch agent"], check=False)
