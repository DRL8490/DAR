import os, re, subprocess

CORNER_GAP_HTML = """<div class="col-md-4" id="gap1Container">
  <div class="p-2 border border-secondary rounded bg-white text-center" style="max-width:280px;margin:0 auto;">
    <div class="d-flex justify-content-between align-items-center mb-1">
      <span class="badge bg-dark text-info" style="font-size:9.5px;">N &uarr; NORTH UP</span>
      <span class="badge bg-light text-dark border" id="lblSvgBrg" style="font-size:9.5px;">Brg: 15.9&deg;</span>
    </div>
    <div class="d-flex justify-content-between px-1 mb-1">
      <input type="number" step="0.01" id="gNW" class="form-control form-control-sm text-center fw-bold" style="width:82px;height:24px;font-size:11px;" placeholder="NW (m)" oninput="syncDirGaps()">
      <input type="number" step="0.01" id="gNE" class="form-control form-control-sm text-center fw-bold" style="width:82px;height:24px;font-size:11px;" placeholder="NE (m)" oninput="syncDirGaps()">
    </div>
    <div class="my-1">
      <svg width="110" height="68" viewBox="0 0 110 68" style="background:#e2e8f0;border-radius:6px;border:1px solid #cbd5e1;">
        <line x1="55" y1="0" x2="55" y2="68" stroke="#94a3b8" stroke-dasharray="2,2"/><line x1="0" y1="34" x2="110" y2="34" stroke="#94a3b8" stroke-dasharray="2,2"/>
        <g id="svgMattRot" transform="rotate(15.854 55 34)">
          <rect x="44" y="12" width="22" height="44" fill="#0284c7" fill-opacity="0.3" stroke="#0369a1" stroke-width="1.8"/>
          <line x1="55" y1="12" x2="55" y2="20" stroke="#dc2626" stroke-width="2"/>
          <circle cx="44" cy="12" r="2.3" fill="#0f172a"/><circle cx="66" cy="12" r="2.3" fill="#0f172a"/>
          <circle cx="44" cy="56" r="2.3" fill="#0f172a"/><circle cx="66" cy="56" r="2.3" fill="#0f172a"/>
        </g>
      </svg>
    </div>
    <div class="d-flex justify-content-between px-1 mt-1">
      <input type="number" step="0.01" id="gSW" class="form-control form-control-sm text-center fw-bold" style="width:82px;height:24px;font-size:11px;" placeholder="SW (m)" oninput="syncDirGaps()">
      <input type="number" step="0.01" id="gSE" class="form-control form-control-sm text-center fw-bold" style="width:82px;height:24px;font-size:11px;" placeholder="SE (m)" oninput="syncDirGaps()">
    </div>
    <input type="hidden" name="gap1_m" id="inpGap1" value="0.00"><input type="hidden" name="gap2_m" id="inpGap2" value="0.00">
  </div>
</div><div id="gap2Container" style="display:none;"></div>
<script>
function updateMattSvg(){
  const hdgEl = document.querySelector('[name="heading_deg"]');
  const b = parseFloat(hdgEl ? hdgEl.value : 0) || 0;
  const g = document.getElementById('svgMattRot');
  if (g) g.setAttribute('transform', `rotate(${b} 55 34)`);
  const lbl = document.getElementById('lblSvgBrg');
  if (lbl) lbl.innerHTML = `Brg: ${b.toFixed(1)}&deg;`;
}
function syncDirGaps(){
  const vals = ['gNW','gNE','gSW','gSE'].map(id => parseFloat(document.getElementById(id)?.value)).filter(v => !isNaN(v));
  document.getElementById('inpGap1').value = (vals[0] ?? 0).toFixed(2);
  document.getElementById('inpGap2').value = (vals[1] ?? vals[0] ?? 0).toFixed(2);
  ['gNW','gNE','gSW','gSE'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.borderColor = el.value === '' ? '#ced4da' : (parseFloat(el.value) <= 0.20 ? '#16a34a' : '#dc2626');
  });
}
document.addEventListener('DOMContentLoaded', function(){
  const sel = document.getElementById('designCatalogSelect');
  if (sel) sel.addEventListener('change', () => setTimeout(updateMattSvg, 10));
  const hdg = document.querySelector('[name="heading_deg"]');
  if (hdg) hdg.addEventListener('input', updateMattSvg);
  updateMattSvg();
});
</script>"""

for target in ["templates/mti_dashboard.html", "mti_blueprint.py"]:
    if not os.path.exists(target): continue
    with open(target, "r", encoding="utf-8-sig") as f: txt = f.read()
    pat = r'<div class="col-md-[24]" id="gap1Container">.*?(?:</script>|<div class="col-md-2" id="gap2Container">.*?</div>)'
    if re.search(pat, txt, flags=re.S):
        txt = re.sub(pat, CORNER_GAP_HTML, txt, count=1, flags=re.S)
        with open(target, "w", encoding="utf-8") as f: f.write(txt)
        print(f"Updated corner gaps & live angle rotation in {target}!")

subprocess.run(["py", "sync.py", "feat: move gap inputs to 4 corners (NW/NE/SW/SE) and auto-rotate mattress SVG on selection"], check=False)
