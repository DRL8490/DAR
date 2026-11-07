import os, ast, subprocess

MTI_ACCESS_ROUTES = """
# --- STEP 2: MTI MODULE USER ACCESS CONTROL ---
def get_mti_allowed_uids():
    from app import AppConfig, User, db, is_user_admin
    cfg = AppConfig.query.first()
    schema = json.loads(cfg.schema_data) if (cfg and cfg.schema_data) else {}
    if "mti_allowed_uids" not in schema:
        default_uids = [u.id for u in User.query.all() if is_user_admin(u) or any(k in (u.name or '').lower() for k in ('abror', 'roderick', 'daryll'))]
        schema["mti_allowed_uids"] = default_uids
        if cfg:
            cfg.schema_data = json.dumps(schema)
            db.session.commit()
    return set(int(x) for x in schema.get("mti_allowed_uids", []))

@mti_bp.before_request
def enforce_mti_access():
    from app import is_user_admin
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if is_user_admin(current_user):
        return None
    if int(current_user.id) not in get_mti_allowed_uids():
        flash("Access Denied: Your account is not enabled for the MTI Module.", "error")
        return redirect(url_for('dashboard'))

@mti_bp.route('/toggle_user_access', methods=['POST'])
@login_required
def toggle_user_access():
    from app import AppConfig, db, is_user_admin
    if not is_user_admin(current_user):
        return {"ok": False}, 403
    uid = request.form.get("user_id", type=int)
    allow = request.form.get("allow") == "true"
    cfg = AppConfig.query.first()
    schema = json.loads(cfg.schema_data) if (cfg and cfg.schema_data) else {}
    allowed = set(int(x) for x in schema.get("mti_allowed_uids", get_mti_allowed_uids()))
    allowed.add(uid) if allow else allowed.discard(uid)
    schema["mti_allowed_uids"] = sorted(list(allowed))
    cfg.schema_data = json.dumps(schema)
    db.session.commit()
    return {"ok": True, "user_id": uid, "allowed": allow}

@mti_bp.route('/user_access_list', methods=['GET'])
@login_required
def user_access_list():
    from app import User, is_user_admin
    if not is_user_admin(current_user):
        return {"users": []}
    allowed = get_mti_allowed_uids()
    return {"users": [{"id": u.id, "name": u.name, "username": u.username, "is_admin": is_user_admin(u), "mti": (u.id in allowed or is_user_admin(u))} for u in User.query.order_by(User.id).all()]}
"""

MANAGE_USERS_JS = """
  if (window.location.pathname.indexOf('user') !== -1 || document.title.toLowerCase().indexOf('user') !== -1) {
    fetch('/mti/user_access_list').then(r=>r.json()).then(data=>{
      if (!data.users || !data.users.length || document.getElementById('mtiUserAccessCard')) return;
      var box = document.createElement('div');
      box.id = 'mtiUserAccessCard';
      box.className = 'card shadow-sm border-primary mb-3 mx-auto';
      box.style.maxWidth = '1140px';
      var html = '<div class="card-header bg-dark text-white d-flex justify-content-between align-items-center py-2"><strong>MTI Module Access Permissions (Tick Box per User)</strong><span class="badge bg-info text-dark" id="mtiSaveBadge">Auto-Saves on Tick</span></div><div class="card-body py-2"><div class="row g-2">';
      data.users.forEach(function(u){
        var chk = u.mti ? 'checked' : '';
        var dis = u.is_admin ? 'disabled title="Admin always has access"' : '';
        html += '<div class="col-md-4 col-sm-6"><label class="d-flex align-items-center gap-2 p-2 border rounded bg-light" style="cursor:pointer;"><input type="checkbox" class="form-check-input m-0" '+chk+' '+dis+' onchange="window.toggleMtiUser('+u.id+', this.checked)"> <span class="fw-bold small">'+u.name+'</span> <small class="text-muted">('+u.username+')</small></label></div>';
      });
      html += '</div></div>';
      box.innerHTML = html;
      var container = document.querySelector('.container, .container-fluid') || document.body;
      container.insertBefore(box, container.children[1] || container.firstChild);
    }).catch(function(){});
    window.toggleMtiUser = function(uid, allow){
      var fd = new FormData(); fd.append('user_id', uid); fd.append('allow', allow ? 'true' : 'false');
      fetch('/mti/toggle_user_access', {method:'POST', body:fd}).then(r=>r.json()).then(res=>{
        var b = document.getElementById('mtiSaveBadge');
        if (b && res.ok) { b.className = 'badge bg-success'; b.innerText = 'Saved!'; setTimeout(()=>{ b.className='badge bg-info text-dark'; b.innerText='Auto-Saves on Tick'; }, 1500); }
      });
    };
  }
"""

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")
if "def enforce_mti_access" not in mc:
    mc += "\n" + MTI_ACCESS_ROUTES
    ast.parse(mc)
    with open("mti_blueprint.py", "w", encoding="utf-8") as f:
        f.write(mc)
    print("1. Added MTI user access guard & toggle endpoints to mti_blueprint.py.")

with open("app.py", "r", encoding="utf-8-sig") as f:
    ac = f.read().lstrip("\ufeff")
if "window.toggleMtiUser" not in ac and "}, 60000);" in ac:
    ac = ac.replace("}, 60000);", "}, 60000);\n" + MANAGE_USERS_JS, 1)
    ast.parse(ac)
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(ac)
    print("2. Injected MTI Access Tick Box panel into Manage Users page via app.py.")

subprocess.run(["py", "sync.py", "feat: add MTI module user access tick boxes on Manage Users and route guard"], check=False)
