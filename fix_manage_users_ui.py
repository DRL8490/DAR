import ast, subprocess

FIXED_USERS_UI_JS = """
  if (document.body.innerText.indexOf('User Management & Access Control') !== -1 || window.location.pathname.indexOf('user') !== -1) {
    fetch('/mti/user_access_list').then(r=>r.json()).then(data=>{
      if (!data.users || !data.users.length) return;
      var tbl = document.querySelector('table');
      if (!tbl || document.getElementById('mtiColHdr')) return;
      var hdrRow = tbl.querySelector('thead tr');
      if (hdrRow && hdrRow.children.length >= 4) {
        var refTh = hdrRow.children[3];
        var cs = window.getComputedStyle(refTh);
        var bg = (cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backgroundColor !== 'transparent') ? cs.backgroundColor : '#343a40';
        var th = document.createElement('th');
        th.id = 'mtiColHdr'; th.className = refTh.className;
        th.innerText = 'MTI Access';
        th.style.cssText = 'background-color:' + bg + ' !important;color:#ffffff !important;padding:' + cs.padding + ';font-size:' + cs.fontSize + ';font-weight:' + cs.fontWeight + ';vertical-align:middle;white-space:nowrap;border:none;';
        hdrRow.insertBefore(th, hdrRow.lastElementChild);
        Array.from(hdrRow.children).forEach(function(h){ h.style.whiteSpace = 'nowrap'; });
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
        Array.from(tr.children).forEach(function(cell, idx){
          if (idx > 0) cell.style.whiteSpace = 'nowrap';
        });
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
"""

with open("app.py", "r", encoding="utf-8-sig") as f:
    ac = f.read().lstrip("\ufeff")

s_marker = "  if (document.body.innerText.indexOf('User Management & Access Control')"
e_marker = "</script></body>'''"
if s_marker in ac and e_marker in ac:
    s_idx = ac.find(s_marker)
    e_idx = ac.find(e_marker, s_idx)
    ac = ac[:s_idx] + FIXED_USERS_UI_JS + "\n})();\n" + ac[e_idx:]
    ast.parse(ac)
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(ac)
    print("Fixed dark MTI Access header background and single-line nowrap alignment in app.py!")

subprocess.run(["py", "sync.py", "fix: lock dark background on MTI Access header and enforce single-line nowrap on Manage Users rows"], check=False)
