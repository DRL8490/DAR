import os, re, ast, subprocess

# 1. Remove hardcoded Super-Admin status for Abror (Mohamad Hediarto) and Mok (Mok Heng) across app.py & templates/
files = ["app.py"] + ([os.path.join("templates", f) for f in os.listdir("templates") if f.endswith(".html")] if os.path.exists("templates") else [])
for path in files:
    if not os.path.exists(path): continue
    with open(path, "r", encoding="utf-8-sig") as f: txt = f.read().lstrip("\ufeff")
    orig = txt
    out_lines = []
    for line in txt.splitlines():
        low = line.lower()
        if "roderick" not in low and "assigned_to" not in low:
            line = re.sub(r"mohamad\.hediarto@nmdc-group\.com|mok\.heng@nmdc-group\.com", "daryll.enano@nmdc-group.com", line, flags=re.I)
            line = re.sub(r"(['\"])(?:mohamad\s+hediarto|mok\s+heng|mohamad\.hediarto|mok\.heng)\1", r"\1Daryll Enano\1", line, flags=re.I)
            if any(k in low for k in ("daryll", "drl", "super", "admin", "vip", "protected", "initial", "email", "name")):
                line = re.sub(r"(['\"])(?:ABR|MOK)\1", r"\1DRL\1", line)
                line = re.sub(r"(['\"])(?:mohamad|hediarto|abror|mok)\1", r"\1daryll\1", line, flags=re.I)
        out_lines.append(line)
    txt = "\n".join(out_lines)
    if txt != orig:
        if path.endswith(".py"): ast.parse(txt)
        with open(path, "w", encoding="utf-8") as f: f.write(txt)
        print(f"1. Removed hardcoded Super-Admin for Abror & Mok in {path}!")

# 2. Force #2b3035 dark background on #mtiColHdr (never read rgb(255,255,255) from cs.backgroundColor)
FIXED_USERS_JS = """
  if (document.body.innerText.indexOf('User Management & Access Control') !== -1 || window.location.pathname.indexOf('user') !== -1) {
    fetch('/mti/user_access_list').then(r=>r.json()).then(data=>{
      if (!data.users || !data.users.length) return;
      var tbl = document.querySelector('table');
      if (!tbl || document.getElementById('mtiColHdr')) return;
      var hdrRow = tbl.querySelector('thead tr');
      if (hdrRow && hdrRow.children.length >= 4) {
        var refTh = hdrRow.children[3];
        var th = refTh.cloneNode(false);
        th.id = 'mtiColHdr';
        th.innerText = 'MTI Access';
        th.style.setProperty('background', '#2b3035', 'important');
        th.style.setProperty('background-color', '#2b3035', 'important');
        th.style.setProperty('color', '#ffffff', 'important');
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
"""

with open("app.py", "r", encoding="utf-8-sig") as f:
    ac = f.read().lstrip("\ufeff")

s_marker = "  if (document.body.innerText.indexOf('User Management & Access Control')"
e_marker = "</script></body>"
if s_marker in ac and e_marker in ac:
    s_idx = ac.find(s_marker)
    e_idx = ac.find(e_marker, s_idx)
    ac = ac[:s_idx] + FIXED_USERS_JS + "\n})();\n" + ac[e_idx:]
    ast.parse(ac)
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(ac)
    print("2. Forced #2b3035 dark background on #mtiColHdr in app.py!")

subprocess.run(["py", "sync.py", "fix: remove hardcoded Super-Admin for Abror/Mok and force #2b3035 dark header on MTI Access"], check=False)
