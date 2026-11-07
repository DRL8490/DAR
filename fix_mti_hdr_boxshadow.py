import os, re, ast, subprocess

NEW_IDLE_SCRIPT = """<style id="mtiHdrForceDark">
  th#mtiColHdr, .table thead th#mtiColHdr, thead tr th#mtiColHdr {
    background: #2c3034 !important;
    background-color: #2c3034 !important;
    color: #ffffff !important;
    box-shadow: none !important;
    --bs-table-bg: #2c3034 !important;
    --bs-table-accent-bg: #2c3034 !important;
    --bs-table-bg-type: #2c3034 !important;
    --bs-table-bg-state: #2c3034 !important;
    white-space: nowrap !important;
    vertical-align: middle !important;
  }
</style>
<script id="renderIdleRefresh">
(function(){
  var idleLimit = 12 * 60 * 1000, lastAct = Date.now();
  ['mousemove','mousedown','keydown','touchstart','scroll'].forEach(function(ev){
    document.addEventListener(ev, function(){ lastAct = Date.now(); }, {passive:true});
  });
  setInterval(function(){
    fetch('/ping', {cache:'no-store'}).catch(function(){});
    if (Date.now() - lastAct >= idleLimit) { window.location.reload(); }
  }, 60000);
  if (document.body.innerText.indexOf('User Management') !== -1 || window.location.pathname.indexOf('user') !== -1) {
    fetch('/mti/user_access_list').then(r=>r.json()).then(data=>{
      if (!data.users || !data.users.length) return;
      var tbl = document.querySelector('table');
      if (!tbl || document.getElementById('mtiColHdr')) return;
      var hdrRow = tbl.querySelector('thead tr') || tbl.querySelector('tr');
      if (hdrRow && hdrRow.children.length >= 4) {
        var refTh = hdrRow.children[3];
        var th = refTh.cloneNode(true);
        th.id = 'mtiColHdr';
        th.innerHTML = '<span style="color:#ffffff !important;font-weight:700;">MTI Access</span>';
        th.style.setProperty('background', '#2c3034', 'important');
        th.style.setProperty('background-color', '#2c3034', 'important');
        th.style.setProperty('color', '#ffffff', 'important');
        th.style.setProperty('box-shadow', 'none', 'important');
        th.style.setProperty('--bs-table-bg', '#2c3034', 'important');
        th.style.setProperty('--bs-table-accent-bg', '#2c3034', 'important');
        th.style.setProperty('white-space', 'nowrap', 'important');
        th.style.setProperty('vertical-align', 'middle', 'important');
        hdrRow.insertBefore(th, hdrRow.lastElementChild);
      }
      var pillStyle = function(ok){
        return 'display:inline-block;padding:3px 10px;border-radius:12px;font-size:11.5px;font-weight:700;white-space:nowrap;' + (ok ? 'background:#dcfce7;color:#166534;' : 'background:#f1f5f9;color:#64748b;');
      };
      tbl.querySelectorAll('tbody tr').forEach(function(tr){
        var rowTxt = tr.innerText.toLowerCase();
        var u = data.users.find(x => (x.email && rowTxt.indexOf(x.email.toLowerCase()) !== -1) || (x.name && rowTxt.indexOf(x.name.toLowerCase()) !== -1));
        var td = document.createElement('td');
        td.style.cssText = 'vertical-align:middle;white-space:nowrap;';
        if (u) {
          var chk = u.mti ? 'checked' : '';
          td.innerHTML = '<label style="display:inline-flex;align-items:center;gap:8px;cursor:pointer;margin:0;white-space:nowrap;"><input type="checkbox" style="width:17px;height:17px;cursor:pointer;accent-color:#0d6efd;" '+chk+' onchange="window.toggleMtiUser('+u.id+', this.checked)"><span id="mtiLbl_'+u.id+'" style="'+pillStyle(u.mti)+'">'+(u.mti?'Allowed':'No Access')+'</span></label>';
        }
        tr.insertBefore(td, tr.lastElementChild);
      });
      window.mtiPillStyle = pillStyle;
    }).catch(function(e){ console.error(e); });
    window.toggleMtiUser = function(uid, allow){
      var fd = new FormData(); fd.append('user_id', uid); fd.append('allow', allow ? 'true' : 'false');
      fetch('/mti/toggle_user_access', {method:'POST', body:fd}).then(r=>r.json()).then(res=>{
        var lbl = document.getElementById('mtiLbl_' + uid);
        if (lbl && res.ok) {
          lbl.setAttribute('style', window.mtiPillStyle(allow));
          lbl.innerText = allow ? 'Allowed' : 'No Access';
        }
      });
    };
  }
})();
</script></body>"""

with open("app.py", "r", encoding="utf-8-sig") as f:
    ac = f.read().lstrip("\ufeff")

pat = r'(?:<style id="mtiHdrForceDark">.*?</style>\s*)?<script id="renderIdleRefresh">.*?</script>\s*</body>'
if re.search(pat, ac, flags=re.S):
    ac = re.sub(pat, NEW_IDLE_SCRIPT, ac, count=1, flags=re.S)
    ast.parse(ac)
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(ac)
    print("SUCCESS: Replaced renderIdleRefresh block with box-shadow:none and --bs-table-bg:#2c3034!")
else:
    print("WARNING: renderIdleRefresh pattern not found in app.py!")

subprocess.run(["py", "sync.py", "fix: clear Bootstrap inset box-shadow and --bs-table-bg on MTI Access header cell"], check=False)
