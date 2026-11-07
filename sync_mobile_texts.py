import os, re, subprocess

path = "templates/mti_mobile.html"
with open(path, "r", encoding="utf-8-sig") as f:
    html = f.read()

# 1. Align Mobile Event Card labels & IDs with Desktop
old_evt = html[html.find('<div id="mobEvtCard"'):html.find('<div id="mobFixCard"')]
new_evt = """<div id="mobEvtCard" class="m-card border-info" style="display:none;">
    <form action="/mti/add_input_log" method="POST"><input type="hidden" name="event_type" id="mEvtType" value="Pole down">
      <div class="d-flex justify-content-between align-items-center mb-2"><h6 class="fw-bold text-info mb-0" id="mEvtTitle">Log Event: Pole down</h6><button type="button" class="btn-close btn-close-white" onclick="document.getElementById('mobEvtCard').style.display='none'"></button></div>
      <div class="row g-2 mb-2"><div class="col-7"><label class="small fw-bold">Date/Time</label><input type="text" name="timestamp" id="mEvtTs" class="form-control" required></div><div class="col-5"><label class="small fw-bold">Surveyor</label><input type="text" name="surveyor" value="{{ current_user.name }}" class="form-control" required></div></div>
      <div class="mb-2"><label class="small fw-bold" id="mLblRef">Location / Crossing ID</label><input type="text" name="ref_id" id="mEvtRef" value="CR-A1_L1" class="form-control"></div>
      <div class="mb-2"><label class="small fw-bold text-info" id="mLbl1">Pole Lock & Pin Status *</label><input type="text" name="val1" id="mEvtVal1" class="form-control" required></div>
      <div class="mb-2"><label class="small fw-bold text-info" id="mLbl2">USBL & ADCP Telemetry Check</label><input type="text" name="val2" id="mEvtVal2" class="form-control"></div>
      <div class="mb-3"><label class="small fw-bold" id="mLblRem">Remarks / Action Taken</label><input type="text" name="remarks" id="mEvtRem" class="form-control" required></div>
      <button type="submit" class="btn btn-info fw-bold w-100 py-2">Save Log</button>
    </form>
  </div>
  """
html = html.replace(old_evt, new_evt, 1)

# 2. Align Mobile Mattress Fix labels & visible Design E/N fields with Desktop
html = html.replace("Mattress Fix (139 CAD Units)", "Mattress Fix Input Box (4 Corners Auto-Calculated in Background)")
html = html.replace(">1st Unit<", ">1st Mattress (No Gaps)<")
html = html.replace(">Xing<", ">Xing / Layer<")
html = html.replace(">Tag ID *<", ">Mattress Tag ID<").replace('placeholder="#A046"', 'placeholder="e.g., #A046"')
html = html.replace(
    '<input type="hidden" name="design_e" id="mDesE" value="194541.443"><input type="hidden" name="design_n" id="mDesN" value="2702613.394">',
    '<div class="row g-2 mb-2"><div class="col-6"><label class="small fw-bold">Design E</label><input type="number" step="0.001" name="design_e" id="mDesE" value="194541.443" class="form-control" oninput="calcMobOff()" required></div><div class="col-6"><label class="small fw-bold">Design N</label><input type="number" step="0.001" name="design_n" id="mDesN" value="2702613.394" class="form-control" oninput="calcMobOff()" required></div></div>'
)
html = html.replace(">As-laid Center E *<", ">As-laid E *<").replace(">As-laid Center N *<", ">As-laid N *<")
html = html.replace('>Remarks *<', '>Remarks<').replace('placeholder="Touchdown notes..."', 'placeholder="Notes..."')
html = html.replace('>Save Mattress Fix<', '>Save Fix<')

# 3. Inject Desktop EVENT_CONFIGS into openMobEvt(t)
old_fn = "function openMobEvt(t){ document.getElementById('mobFixCard').style.display='none'; const c=document.getElementById('mobEvtCard'); c.style.display='block'; document.getElementById('mEvtType').value=t; document.getElementById('mEvtTitle').innerText='Log: '+t; document.getElementById('mEvtTs').value=nowStr(); c.scrollIntoView({behavior:'smooth'}); }"
new_fn = """const EVENT_CONFIGS = {
  "Pole down": {r:"Location / Crossing ID",dr:"CR-A1_L1",l1:"Pole Lock & Pin Status *",p1:"Down & Locked in Working Position",l2:"USBL & ADCP Telemetry Check",p2:"Ranger 2 HPT & RDI ADCP Online",pr:"Over-the-side pole deployed prior to subsea operations..."},
  "Pole up": {r:"Location / Crossing ID",dr:"CR-A1_L1",l1:"Pole Stowed Status *",p1:"Recovered & Secured on Deck Cradle",l2:"Reason for Recovery",p2:"Transit / Weather / Maintenance",pr:"USBL/ADCP pole raised and locked above waterline..."},
  "Mattress on water": {r:"Xing / Box / Tag ID *",dr:"CR-A1_M{{ ledger|length + 1 }}",l1:"Mattress Physical Tag # *",p1:"e.g., #A046",l2:"Water Depth / Beacon Status",p2:"Transponder Ch 1 & 2 Tracking OK",pr:"Mattress overboarded through splash zone; WROV following descent..."},
  "Frame above water": {r:"Xing / Box / Tag ID *",dr:"CR-A1_M{{ ledger|length }}",l1:"Acoustic Release Status *",p1:"4-Hook Release Confirmed by WROV",l2:"Frame Deck Status",p2:"Frame Above Water & Landed on Deck",pr:"Deployment frame recovered cleanly; preparing next mattress..."},
  "ADCP input": {r:"Crossing / Station ID",dr:"CR-A1_L1",l1:"Surface / Mid Current (m/s or kt & Dir) *",p1:"e.g., Surf: 0.45 m/s @ 210 deg",l2:"Near-Seabed Current (m/s or kt & Dir)",p2:"e.g., Seabed: 0.25 m/s @ 195 deg",pr:"ADCP current profile logged prior to mattress touchdown..."},
  "Wind Input": {r:"Vessel / Location",dr:"MMA Prestige (CR-A1)",l1:"Wind Speed (kt or m/s) & Direction (deg) *",p1:"e.g., 18 kt @ 035 deg (NE)",l2:"Wave Height Hs (m) & Swell",p2:"e.g., Hs = 0.8 m (Within <=1.0m limit)",pr:"Bridge anemometer & sea state observation..."},
  "Survey Issue Reporting": {r:"System / Sensor Affected *",dr:"USBL / WROV / NaviPac",l1:"Issue / Fault Description *",p1:"e.g., USBL acoustic dropout / ROV tether",l2:"Operational Impact / Downtime",p2:"e.g., 25 min troubleshooting on DP",pr:"Root cause and corrective action taken by onboard survey team..."}
};
function openMobEvt(t){
  const cfg = EVENT_CONFIGS[t]; if(!cfg) return;
  document.getElementById('mobFixCard').style.display='none';
  const c = document.getElementById('mobEvtCard'); c.style.display='block';
  document.getElementById('mEvtType').value = t;
  document.getElementById('mEvtTitle').innerText = 'Log Event: ' + t;
  document.getElementById('mEvtTs').value = nowStr();
  document.getElementById('mLblRef').innerText = cfg.r;
  document.getElementById('mEvtRef').value = cfg.dr;
  document.getElementById('mLbl1').innerText = cfg.l1;
  document.getElementById('mEvtVal1').value = ''; document.getElementById('mEvtVal1').placeholder = cfg.p1;
  document.getElementById('mLbl2').innerText = cfg.l2;
  document.getElementById('mEvtVal2').value = ''; document.getElementById('mEvtVal2').placeholder = cfg.p2;
  document.getElementById('mEvtRem').value = ''; document.getElementById('mEvtRem').placeholder = cfg.pr;
  c.scrollIntoView({behavior:'smooth'});
}"""
html = html.replace(old_fn, new_fn, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(html)
print("Synced all mobile input box labels, placeholders, and fields with desktop!")
subprocess.run(["py", "sync.py", "fix: unify mobile input box labels, placeholders, and fields with desktop MTI view"], check=False)
