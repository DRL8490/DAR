import os, re, subprocess

POLE_DOWN_CFG = '"Pole down": {lblRef:"Location / Crossing ID",defRef:"CR-A1_L1",lbl1:"USBL & ADCP Telemetry Check *",ph1:"Ranger 2 HPT & RDI ADCP Online",lbl2:"",ph2:"",phRem:"Over-the-side pole deployed prior to subsea operations...",r:"Location / Crossing ID",dr:"CR-A1_L1",l1:"USBL & ADCP Telemetry Check *",p1:"Ranger 2 HPT & RDI ADCP Online",l2:"",p2:"",pr:"Over-the-side pole deployed prior to subsea operations..."}'

SINGLE_BOX_JS = """
    const LoggedUser = "{{ current_user.name }}";
    const syncPoleDownAndUser = function(evtType){
      const isSingle = (evtType === 'Pole down');
      const dV2 = document.getElementById('evtVal2')?.closest('.col-md-6');
      const dV1 = document.getElementById('evtVal1')?.closest('.col-md-6, .col-md-12');
      if (dV2 && dV1) { dV2.style.display = isSingle ? 'none' : ''; dV1.className = isSingle ? 'col-md-12' : 'col-md-6'; }
      const mV2 = document.getElementById('mEvtVal2')?.closest('.mb-2');
      if (mV2) mV2.style.display = isSingle ? 'none' : '';
      const sDesk = document.getElementById('evtSurveyor');
      if (sDesk && !document.getElementById('evtLogId')?.value) sDesk.value = LoggedUser;
    };
    const _oDesk = window.openEventInputBox;
    if (_oDesk) window.openEventInputBox = function(t){ _oDesk(t); syncPoleDownAndUser(t); };
    const _oMob = window.openMobEvt;
    if (_oMob) window.openMobEvt = function(t){ _oMob(t); syncPoleDownAndUser(t); };
"""

MOBILE_THEME_AND_NIGHT_BTN = """<style id="mobBrightTheme">
  body { background:#eef4f8 !important; color:#0f172a !important; transition:background 0.2s,color 0.2s; }
  .m-card { background:#ffffff !important; border:1.5px solid #cbd5e1 !important; color:#0f172a !important; box-shadow:0 3px 8px rgba(15,23,42,0.06); }
  .tap-btn { background:#ffffff !important; border:2px solid #94a3b8 !important; color:#0f172a !important; box-shadow:0 2px 5px rgba(15,23,42,0.05); }
  .tap-btn:active { background:#e0f2fe !important; border-color:#0284c7 !important; }
  .tap-btn.btn-fix { background:#dcfce7 !important; border-color:#16a34a !important; color:#14532d !important; }
  .tap-btn.btn-issue { background:#fee2e2 !important; border-color:#dc2626 !important; color:#7f1d1d !important; }
  .tap-btn i.text-light { color:#475569 !important; }
  #mGapWrap { background:#f8fafc !important; border:1.5px solid #94a3b8 !important; color:#0f172a !important; }
  #mGapWrap svg { background:#e2e8f0 !important; border-color:#94a3b8 !important; }
  .m-card .btn-close-white { filter:invert(1) grayscale(100%) brightness(20%); }
  body.night-mode { background:#0f172a !important; color:#f8fafc !important; }
  body.night-mode .m-card { background:#1e293b !important; border-color:#334155 !important; color:#f8fafc !important; }
  body.night-mode .tap-btn { background:#1e293b !important; border-color:#475569 !important; color:#f8fafc !important; }
  body.night-mode .tap-btn.btn-fix { background:#064e3b !important; border-color:#16a34a !important; color:#f8fafc !important; }
  body.night-mode .tap-btn.btn-issue { background:#450a0a !important; border-color:#dc2626 !important; color:#f8fafc !important; }
  body.night-mode .tap-btn i.text-light { color:#f8fafc !important; }
  body.night-mode #mGapWrap { background:#0f172a !important; border-color:#475569 !important; color:#f8fafc !important; }
  body.night-mode #mGapWrap svg { background:#1e293b !important; border-color:#475569 !important; }
  body.night-mode .m-card .btn-close-white { filter:none; }
</style>
<script id="mobNightModeScript">
function toggleNightMode(){
  const isN = document.body.classList.toggle('night-mode');
  localStorage.setItem('mti_mob_night', isN ? '1' : '0');
  const b = document.getElementById('btnNightToggle');
  if (b) b.innerHTML = isN ? '<i class="fas fa-sun text-warning"></i> Day' : '<i class="fas fa-moon"></i> Night';
}
document.addEventListener('DOMContentLoaded', function(){
  if (localStorage.getItem('mti_mob_night') === '1') {
    document.body.classList.add('night-mode');
    const b = document.getElementById('btnNightToggle');
    if (b) b.innerHTML = '<i class="fas fa-sun text-warning"></i> Day';
  }
});
</script>
</body>"""

for target in ["templates/mti_dashboard.html", "templates/mti_mobile.html", "mti_blueprint.py"]:
    if not os.path.exists(target): continue
    with open(target, "r", encoding="utf-8-sig") as f: txt = f.read()
    txt = txt.replace('value="Abror / Roderick"', 'value="{{ current_user.name }}"')
    txt = txt.replace('id="mLbl1">Pole Lock & Pin Status *<', 'id="mLbl1">USBL & ADCP Telemetry Check *<')
    txt = re.sub(r'"Pole down":\s*\{[^}]+\}', POLE_DOWN_CFG, txt)
    if 'const toggleEvtEnv =' in txt and 'syncPoleDownAndUser' not in txt:
        txt = txt.replace('const toggleEvtEnv =', SINGLE_BOX_JS + '\n    const toggleEvtEnv =', 1)
    if target == "templates/mti_mobile.html":
        if 'id="btnNightToggle"' not in txt:
            txt = txt.replace('id="btnPwaInstall"', 'id="btnNightToggle" class="btn btn-sm btn-dark fw-bold border-secondary" onclick="toggleNightMode()"><i class="fas fa-moon"></i> Night</button>\n    <button type="button" id="btnPwaInstall"', 1)
        txt = txt.replace('style="background:#0f172a;border-left:4px solid #38bdf8;"', 'class="p-2 mb-2 rounded border-start border-4 border-info" style="background:rgba(14,165,233,0.08);"')
        if 'id="mobBrightTheme"' not in txt:
            txt = txt.replace('</body>', MOBILE_THEME_AND_NIGHT_BTN, 1)
    with open(target, "w", encoding="utf-8") as f: f.write(txt)
    print(f"Updated {target}!")

subprocess.run(["py", "sync.py", "feat: remove Pole Lock status on Pole down, default Surveyor to user name, and add brighter mobile theme + Night Mode toggle"], check=False)
