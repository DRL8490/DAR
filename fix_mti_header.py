import ast, subprocess

# 1. Enforce tickbox strictly for all users (so unticked Admins like Danilo/Mok Heng are also blocked)
with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")

mc = mc.replace(
    "    if is_user_admin(current_user):\n        return None\n",
    ""
)
ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)

# 2. Fix the white header cell & style the Allowed / No Access pills on Manage Users
FIXED_TABLE_JS = """
  if (document.body.innerText.indexOf('User Management & Access Control') !== -1 || window.location.pathname.indexOf('user') !== -1) {
    fetch('/mti/user_access_list').then(r=>r.json()).then(data=>{
      if (!data.users || !data.users.length) return;
      var tbl = document.querySelector('table');
      if (!tbl || document.getElementById('mtiColHdr')) return;
      var hdrRow = tbl.querySelector('thead tr');
      if (hdrRow && hdrRow.children.length >= 4) {
        var refTh = hdrRow.children[3];
        var th = document.createElement('th');
        th.id = 'mtiColHdr'; th.className = refTh.className;
        th.style.cssText = window.getComputedStyle(refTh).cssText;
        th.style.backgroundColor = 'transparent'; th.style.color = '#ffffff';
        th.innerText = 'MTI Access';
        hdrRow.insertBefore(th, hdrRow.lastElementChild);
      }
      var pillStyle = function(ok){
        return 'display:inline-block;padding:3px 10px;border-radius:12px;font-size:11.5px;font-weight:700;' + (ok ? 'background:#dcfce7;color:#166534;' : 'background:#f1f5f9;color:#64748b;');
      };
      tbl.querySelectorAll('tbody tr').forEach(function(tr){
        var rowTxt = tr.innerText.toLowerCase();
        var u = data.users.find(x => (x.email && rowTxt.indexOf(x.email.toLowerCase()) !== -1) || (x.name && rowTxt.indexOf(x.name.toLowerCase()) !== -1));
        var td = document.createElement('td');
        td.style.verticalAlign = 'middle';
        if (u) {
          var chk = u.mti ? 'checked' : '';
          td.innerHTML = '<label style="display:inline-flex;align-items:center;gap:8px;cursor:pointer;margin:0;"><input type="checkbox" style="width:17px;height:17px;cursor:pointer;accent-color:#0d6efd;" '+chk+' onchange="window.toggleMtiUser('+u.id+', this.checked)"><span id="mtiLbl_'+u.id+'" style="'+pillStyle(u.mti)+'">'+(u.mti?'Allowed':'No Access')+'</span></label>';
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
"""

with open("app.py", "r", encoding="utf-8-sig") as f:
    ac = f.read().lstrip("\ufeff")

s_marker = "  if (document.body.innerText.indexOf('User Management & Access Control')"
e_marker = "</script></body>'''"
if s_marker in ac and e_marker in ac:
    s_idx = ac.find(s_marker)
    e_idx = ac.find(e_marker, s_idx)
    ac = ac[:s_idx] + FIXED_TABLE_JS + "\n})();\n" + ac[e_idx:]
    ast.parse(ac)
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(ac)
    print("Fixed dark MTI Access header, pill badges, and strict tickbox enforcement!")

subprocess.run(["py", "sync.py", "fix: style MTI Access column header and pills on Manage Users and strictly enforce tickbox"], check=False)
