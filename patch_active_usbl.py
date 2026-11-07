import os, re, ast, subprocess

USBL_GLOBAL_JS = """<script id="mtiActiveUsblUpgrade">
window.setUsblMode = function(btn, val){
  const form = btn.closest('form') || document;
  const inp = form.querySelector('[name="usbl_sensor"]');
  if (inp) inp.value = val;
  form.querySelectorAll('.usbl-pill').forEach(b => {
    const active = (b.getAttribute('data-val') === val);
    b.className = 'btn btn-sm fw-bold usbl-pill ' + (active ? 'btn-primary text-white shadow-sm' : 'btn-outline-primary');
  });
};
document.addEventListener('DOMContentLoaded', function(){
  // 1. Inject Active USBL Selector (Survey Pole vs Vessel) into Event Input Boxes (Desktop & Mobile)
  ['eventInputForm', 'mobEvtCard'].forEach(function(id){
    const c = document.getElementById(id);
    const form = c ? (c.tagName === 'FORM' ? c : c.querySelector('form')) : null;
    if (form && !form.querySelector('.evt-usbl-selector')) {
      const bar = document.createElement('div');
      bar.className = 'p-2 mb-2 rounded border border-primary evt-usbl-selector';
      bar.style.background = 'rgba(13,110,253,0.07)';
      bar.innerHTML = '<div class="d-flex flex-wrap justify-content-between align-items-center gap-2">' +
        '<span class="small fw-bold text-primary"><i class="fas fa-satellite-dish me-1"></i>Active USBL (Survey Pole vs. Vessel):</span>' +
        '<input type="hidden" name="usbl_sensor" value="Survey Pole USBL">' +
        '<div class="btn-group btn-group-sm" role="group">' +
          '<button type="button" class="btn btn-primary fw-bold usbl-pill" data-val="Survey Pole USBL" onclick="setUsblMode(this, \\'Survey Pole USBL\\')">📡 Survey Pole USBL</button>' +
          '<button type="button" class="btn btn-outline-primary fw-bold usbl-pill" data-val="Vessel USBL" onclick="setUsblMode(this, \\'Vessel USBL\\')">🚢 Vessel USBL</button>' +
          '<button type="button" class="btn btn-outline-primary fw-bold usbl-pill" data-val="Vessel Nav + Survey Pole Fix" onclick="setUsblMode(this, \\'Vessel Nav + Survey Pole Fix\\')">🔄 Vessel + Pole</button>' +
        '</div></div>';
      const firstRow = form.querySelector('.row');
      if (firstRow) firstRow.parentNode.insertBefore(bar, firstRow.nextSibling);
    }
  });

  // 2. Ensure Mattress Fix Form has the 1-Tap Active USBL Selector buttons (Survey Pole vs Vessel)
  document.querySelectorAll('form[action*="add_fix"]').forEach(function(f){
    const existingSel = f.querySelector('select[name="usbl_sensor"]');
    if (existingSel) {
      const col = existingSel.closest('.col-md-3, .col-6') || existingSel.parentNode;
      col.className = 'col-md-4 col-12';
      col.innerHTML = `<label class="form-label small fw-bold text-primary mb-1"><i class="fas fa-satellite-dish me-1"></i>Active USBL (Survey Pole vs. Vessel) *</label>
        <input type="hidden" name="usbl_sensor" id="inpUsblSensor" value="Survey Pole USBL">
        <div class="btn-group btn-group-sm w-100" role="group">
          <button type="button" class="btn btn-primary fw-bold usbl-pill" data-val="Survey Pole USBL" onclick="setUsblMode(this, 'Survey Pole USBL')">📡 Survey Pole</button>
          <button type="button" class="btn btn-outline-primary fw-bold usbl-pill" data-val="Vessel USBL" onclick="setUsblMode(this, 'Vessel USBL')">🚢 Vessel USBL</button>
          <button type="button" class="btn btn-outline-primary fw-bold usbl-pill" data-val="Vessel Nav + Survey Pole Fix" onclick="setUsblMode(this, 'Vessel Nav + Survey Pole Fix')">🔄 Both</button>
        </div>`;
      f.querySelectorAll('#inpQaqcE, #inpQaqcN, #inpQaqcBrg').forEach(inp => {
        const p = inp.closest('.col-md-3');
        if (p) p.className = 'col-md-2 col-4';
      });
    } else if (!f.querySelector('[name="usbl_sensor"]')) {
      const bar = document.createElement('div');
      bar.className = 'p-2 mb-2 rounded border border-primary';
      bar.style.background = 'rgba(13,110,253,0.07)';
      bar.innerHTML = `<div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
        <span class="small fw-bold text-primary"><i class="fas fa-satellite-dish me-1"></i>Active USBL (Survey Pole vs. Vessel):</span>
        <input type="hidden" name="usbl_sensor" id="inpUsblSensor" value="Survey Pole USBL">
        <div class="btn-group btn-group-sm" role="group">
          <button type="button" class="btn btn-primary fw-bold usbl-pill" data-val="Survey Pole USBL" onclick="setUsblMode(this, 'Survey Pole USBL')">📡 Survey Pole USBL</button>
          <button type="button" class="btn btn-outline-primary fw-bold usbl-pill" data-val="Vessel USBL" onclick="setUsblMode(this, 'Vessel USBL')">🚢 Vessel USBL</button>
          <button type="button" class="btn btn-outline-primary fw-bold usbl-pill" data-val="Vessel Nav + Survey Pole Fix" onclick="setUsblMode(this, 'Vessel Nav + Survey Pole Fix')">🔄 Vessel + Pole</button>
        </div></div>`;
      f.insertBefore(bar, f.firstElementChild.nextSibling);
    }
  });
});
</script>
</body>"""

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")

mc = mc.replace('"Pole USBL"', '"Survey Pole USBL"').replace('>Pole USBL (Primary)<', '>Survey Pole USBL (Primary)<')
old_log_line = 'env_w = (request.form.get("env_wind") or "").strip()'
new_log_line = 'usbl_s = (request.form.get("usbl_sensor") or "Survey Pole USBL").strip()\n    env_w = (request.form.get("env_wind") or "").strip()'
if 'usbl_s = (request.form.get("usbl_sensor")' not in mc and old_log_line in mc:
    mc = mc.replace(old_log_line, new_log_line, 1)
    mc = re.sub(
        r'env_tag = " \| "\.join\(\[f"\{k\}:\{v\}" for k, v in \[.*?\] if v\]\)',
        'env_tag = " | ".join([f"{k}:{v}" for k, v in [("USBL", usbl_s), ("Wind", env_w), ("Curr", env_c)] if v])',
        mc
    )

ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)

for target in ["templates/mti_dashboard.html", "templates/mti_mobile.html", "mti_blueprint.py"]:
    if not os.path.exists(target): continue
    with open(target, "r", encoding="utf-8-sig") as f: txt = f.read()
    txt = txt.replace('"Pole USBL"', '"Survey Pole USBL"').replace('>Pole USBL (Primary)<', '>Survey Pole USBL (Primary)<')
    if 'id="mtiActiveUsblUpgrade"' not in txt and '</body>' in txt:
        txt = txt.replace('</body>', USBL_GLOBAL_JS, 1)
    with open(target, "w", encoding="utf-8") as f: f.write(txt)
    print(f"Integrated Active USBL selector (Survey Pole vs. Vessel) into {target}!")

subprocess.run(["py", "sync.py", "feat: integrate 1-tap Active USBL selector (Survey Pole USBL vs Vessel USBL) across Event and Mattress Fix forms"], check=False)
