import os, re, ast, subprocess

RADIO_HTML_BLOCK = """<label class="form-label small fw-bold text-primary mb-1">Active USBL *</label>
        <div class="d-flex align-items-center gap-3 p-1 px-2 border border-primary rounded bg-light" style="min-height:31px;">
          <label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">
            <input type="radio" class="form-check-input m-0" name="usbl_sensor" value="Survey Pole" checked> Survey Pole
          </label>
          <label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">
            <input type="radio" class="form-check-input m-0" name="usbl_sensor" value="Vessel"> Vessel
          </label>
        </div>"""

USBL_RADIO_JS = """<script id="mtiActiveUsblUpgrade">
document.addEventListener('DOMContentLoaded', function(){
  // 1. Inject Radio Buttons (Survey Pole OR Vessel) into Event Input Boxes (Desktop & Mobile)
  ['eventInputForm', 'mobEvtCard'].forEach(function(id){
    const c = document.getElementById(id);
    const form = c ? (c.tagName === 'FORM' ? c : c.querySelector('form')) : null;
    if (form && !form.querySelector('.evt-usbl-selector')) {
      const bar = document.createElement('div');
      bar.className = 'p-2 mb-2 rounded border border-primary evt-usbl-selector';
      bar.style.background = 'rgba(13,110,253,0.07)';
      bar.innerHTML = '<div class="d-flex flex-wrap justify-content-between align-items-center gap-2">' +
        '<span class="small fw-bold text-primary"><i class="fas fa-satellite-dish me-1"></i>Active USBL:</span>' +
        '<div class="d-flex align-items-center gap-3">' +
          '<label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">' +
            '<input type="radio" class="form-check-input m-0" name="usbl_sensor" value="Survey Pole" checked> Survey Pole' +
          '</label>' +
          '<label class="form-check-label small fw-bold d-inline-flex align-items-center gap-1" style="cursor:pointer;">' +
            '<input type="radio" class="form-check-input m-0" name="usbl_sensor" value="Vessel"> Vessel' +
          '</label>' +
        '</div></div>';
      const firstRow = form.querySelector('.row');
      if (firstRow) firstRow.parentNode.insertBefore(bar, firstRow.nextSibling);
    }
  });

  // 2. Ensure Mattress Fix Form uses Radio Buttons (Survey Pole OR Vessel)
  document.querySelectorAll('form[action*="add_fix"]').forEach(function(f){
    const existingSel = f.querySelector('select[name="usbl_sensor"]');
    if (existingSel) {
      const col = existingSel.closest('.col-md-3, .col-md-4, .col-6, .col-12') || existingSel.parentNode;
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
    }
  });
});
</script>"""

for target in ["templates/mti_dashboard.html", "templates/mti_mobile.html", "mti_blueprint.py"]:
    if not os.path.exists(target):
        continue
    with open(target, "r", encoding="utf-8-sig") as f:
        txt = f.read()

    txt = re.sub(
        r'<label class="form-label small fw-bold text-primary mb-1">Active USBL Used \*</label>\s*<select name="usbl_sensor".*?</select>',
        RADIO_HTML_BLOCK,
        txt,
        flags=re.S
    )

    if 'id="mtiActiveUsblUpgrade"' in txt:
        txt = re.sub(r'<script id="mtiActiveUsblUpgrade">.*?</script>', USBL_RADIO_JS, txt, flags=re.S)
    elif '</body>' in txt:
        txt = txt.replace('</body>', USBL_RADIO_JS + '\n</body>', 1)

    if target.endswith(".py"):
        txt = txt.replace('"Survey Pole USBL"', '"Survey Pole"')
        ast.parse(txt)

    with open(target, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"Updated {target} with Survey Pole OR Vessel radio buttons!")

subprocess.run(["py", "sync.py", "feat: use clean radio buttons (Survey Pole OR Vessel) for Active USBL selector"], check=False)
