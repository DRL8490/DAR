import ast, subprocess

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")

mc = mc.replace(
    '"username": u.username',
    '"email": getattr(u, "email", getattr(u, "username", ""))'
).replace(
    '"mti": (u.id in allowed or is_user_admin(u))',
    '"mti": (u.id in allowed)'
)
ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)

TABLE_TICKBOX_JS = """
  if (document.body.innerText.indexOf('User Management & Access Control') !== -1 || window.location.pathname.indexOf('user') !== -1) {
    fetch('/mti/user_access_list').then(r=>r.json()).then(data=>{
      if (!data.users || !data.users.length) return;
      var tbl = document.querySelector('table');
      if (!tbl || document.getElementById('mtiColHdr')) return;
      var hdrRow = tbl.querySelector('thead tr');
      if (hdrRow && hdrRow.children.length >= 4) {
        var th = document.createElement('th');
        th.id = 'mtiColHdr'; th.innerText = 'MTI Access';
        hdrRow.insertBefore(th, hdrRow.lastElementChild);
      }
      var rows = tbl.querySelectorAll('tbody tr');
      rows.forEach(function(tr){
        var rowTxt = tr.innerText.toLowerCase();
        var u = data.users.find(x => (x.email && rowTxt.indexOf(x.email.toLowerCase()) !== -1) || (x.name && rowTxt.indexOf(x.name.toLowerCase()) !== -1));
        var td = document.createElement('td');
        if (u) {
          var chk = u.mti ? 'checked' : '';
          td.innerHTML = '<label class="d-inline-flex align-items-center gap-2 fw-bold small" style="cursor:pointer;"><input type="checkbox" class="form-check-input m-0" style="width:18px;height:18px;cursor:pointer;" '+chk+' onchange="window.toggleMtiUser('+u.id+', this.checked)"><span id="mtiLbl_'+u.id+'" class="badge '+(u.mti?'bg-success':'bg-secondary')+'">'+(u.mti?'Allowed':'No Access')+'</span></label>';
        }
        tr.insertBefore(td, tr.lastElementChild);
      });
    }).catch(function(e){ console.error(e); });
    window.toggleMtiUser = function(uid, allow){
      var fd = new FormData(); fd.append('user_id', uid); fd.append('allow', allow ? 'true' : 'false');
      fetch('/mti/toggle_user_access', {method:'POST', body:fd}).then(r=>r.json()).then(res=>{
        var lbl = document.getElementById('mtiLbl_' + uid);
        if (lbl && res.ok) {
          lbl.className = 'badge ' + (allow ? 'bg-success' : 'bg-secondary');
          lbl.innerText = allow ? 'Allowed' : 'No Access';
        }
      });
    };
  }
"""

with open("app.py", "r", encoding="utf-8-sig") as f:
    ac = f.read().lstrip("\ufeff")

start_marker = "  if (window.location.pathname.indexOf('user') !== -1"
end_marker = "</script></body>'''"
if start_marker in ac and end_marker in ac:
    s_idx = ac.find(start_marker)
    e_idx = ac.find(end_marker, s_idx)
    ac = ac[:s_idx] + TABLE_TICKBOX_JS + "\n})();\n" + ac[e_idx:]
    ast.parse(ac)
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(ac)
    print("Fixed u.email and injected MTI Access tickbox column directly into User Management table!")

subprocess.run(["py", "sync.py", "fix: use User.email for MTI access list and inject MTI Access tickbox column into Manage Users table"], check=False)
