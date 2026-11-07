import os, re, subprocess

VISUAL_GAP_HTML = """<div class="col-md-4" id="gap1Container">
  <div class="p-2 border border-secondary rounded bg-white text-center" style="max-width:290px;margin:0 auto;">
    <div class="d-flex justify-content-between align-items-center mb-1">
      <span class="badge bg-dark text-info" style="font-size:9.5px;">N &uarr; NORTH UP</span>
      <span class="badge bg-light text-dark border" id="lblSvgBrg" style="font-size:9.5px;">Gaps (&le;0.20m)</span>
    </div>
    <div class="mb-1"><input type="number" step="0.01" id="gN" class="form-control form-control-sm d-inline-block text-center fw-bold" style="width:78px;height:24px;font-size:11px;" placeholder="N (m)" oninput="syncDirGaps()"></div>
    <div class="d-flex justify-content-between align-items-center my-1">
      <input type="number" step="0.01" id="gW" class="form-control form-control-sm text-center fw-bold" style="width:74px;height:24px;font-size:11px;" placeholder="W (m)" oninput="syncDirGaps()">
      <svg width="76" height="58" viewBox="0 0 76 58" style="background:#e2e8f0;border-radius:4px;border:1px solid #cbd5e1;">
        <line x1="38" y1="0" x2="38" y2="58" stroke="#94a3b8" stroke-dasharray="2,2"/><line x1="0" y1="29" x2="76" y2="29" stroke="#94a3b8" stroke-dasharray="2,2"/>
        <g id="svgMattRot" transform="rotate(15.85 38 29)"><rect x="28" y="9" width="20" height="40" fill="#0284c7" fill-opacity="0.3" stroke="#0369a1" stroke-width="1.8"/><line x1="38" y1="9" x2="38" y2="16" stroke="#dc2626" stroke-width="2"/></g>
      </svg>
      <input type="number" step="0.01" id="gE" class="form-control form-control-sm text-center fw-bold" style="width:74px;height:24px;font-size:11px;" placeholder="E (m)" oninput="syncDirGaps()">
    </div>
    <div class="mt-1"><input type="number" step="0.01" id="gS" class="form-control form-control-sm d-inline-block text-center fw-bold" style="width:78px;height:24px;font-size:11px;" placeholder="S (m)" oninput="syncDirGaps()"></div>
    <input type="hidden" name="gap1_m" id="inpGap1" value="0.00"><input type="hidden" name="gap2_m" id="inpGap2" value="0.00">
  </div>
</div><div id="gap2Container" style="display:none;"></div>
<script>
function syncDirGaps(){
  const vals = ['gN','gS','gE','gW'].map(id => parseFloat(document.getElementById(id)?.value)).filter(v => !isNaN(v));
  document.getElementById('inpGap1').value = (vals[0] ?? 0).toFixed(2);
  document.getElementById('inpGap2').value = (vals[1] ?? vals[0] ?? 0).toFixed(2);
  ['gN','gS','gE','gW'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.borderColor = el.value === '' ? '#ced4da' : (parseFloat(el.value) <= 0.20 ? '#16a34a' : '#dc2626');
  });
}
document.addEventListener('input', function(e){
  if (e.target && e.target.name === 'heading_deg') {
    const b = parseFloat(e.target.value) || 0;
    const g = document.getElementById('svgMattRot');
    if (g) g.setAttribute('transform', `rotate(${b} 38 29)`);
  }
});
</script>"""

target = "templates/mti_dashboard.html" if os.path.exists("templates/mti_dashboard.html") else "mti_blueprint.py"
with open(target, "r", encoding="utf-8-sig") as f:
    txt = f.read()

pattern = r'<div class="col-md-2" id="gap1Container">.*?</div>\s*<div class="col-md-2" id="gap2Container">.*?</div>'
if re.search(pattern, txt, flags=re.S):
    txt = re.sub(pattern, VISUAL_GAP_HTML, txt, count=1, flags=re.S)
    with open(target, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"Patched North-Up Visual Gap Box into {target}!")
    subprocess.run(["py", "sync.py", "feat: patch North-Up visual gap input box into MTI form"], check=False)
else:
    print(f"North-Up Gap Box already present or anchor not found in {target}.")
