import os
import re
import ast
import subprocess

# 1. Patch app.py: Pre-load Echo-4 + Upgrade hidden_config() with Universal Smart Cascade Resolver
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Pre-load Echo-4 into Bathymetric Survey tasks in LEAN_CORE_TASKS
code = code.replace(
    '"instruments": ["MBES  WS166", "SBES", "USBL", "ADCP", "ROV"]',
    '"instruments": ["MBES  WS166", "SBES", "Echo-4", "USBL", "ADCP", "ROV"]'
)
code = code.replace(
    '"instruments": ["USBL", "ROV", "PDS", "EIVA NaviPac", "MBES  WS166", "PC"]',
    '"instruments": ["USBL", "ROV", "PDS", "EIVA NaviPac", "MBES  WS166", "Echo-4", "PC"]'
)

new_hidden_config = '''@app.route('/system_config_hidden', methods=['GET', 'POST'])
@login_required
def hidden_config():
    if not is_user_admin(current_user):
        return redirect(url_for('dashboard'))
    config = AppConfig.query.first()
    master_schema = json.loads(config.schema_data) if config else {}
    for k in ["file_tree", "requestors", "activities"]:
        master_schema.setdefault(k, {})
    if request.method == 'POST':
        form_dict = {k: (v.strip() if isinstance(v, str) else v) for k, v in request.form.items()}
        action = form_dict.get('action', '')
        detail_msg = ""

        # Universal Smart Cascade Resolver (matches explicit names AND auto-detects from schema keys)
        act_type = (
            form_dict.get('activity') or form_dict.get('act_type') or form_dict.get('activity_type')
            or form_dict.get('task_category') or form_dict.get('category') or form_dict.get('act') or ''
        )
        act_req = (
            form_dict.get('action_req') or form_dict.get('act_req') or form_dict.get('action_required')
            or form_dict.get('action_name') or form_dict.get('sub_activity') or form_dict.get('sub_act')
            or form_dict.get('discipline') or form_dict.get('disc') or form_dict.get('new_action') or ''
        )
        inst_raw = (
            form_dict.get('instrument') or form_dict.get('inst') or form_dict.get('new_inst')
            or form_dict.get('inst_name') or form_dict.get('tool') or ''
        )

        # Fallback value-matcher against existing master_schema['activities'] keys
        if not act_type:
            for k, v in form_dict.items():
                if k != 'action' and v in master_schema['activities']:
                    act_type = v
                    break
        if act_type and not act_req and act_type in master_schema['activities']:
            for k, v in form_dict.items():
                if k != 'action' and v != act_type and v in master_schema['activities'][act_type]:
                    act_req = v
                    break
        if act_type and act_req and not inst_raw:
            for k, v in form_dict.items():
                if k != 'action' and v not in (act_type, act_req) and v:
                    inst_raw = v
                    break
        elif act_type and not act_req:
            for k, v in form_dict.items():
                if k != 'action' and v != act_type and v:
                    act_req = v
                    break
        elif not act_type:
            for k, v in form_dict.items():
                if k != 'action' and v:
                    act_type = v
                    break

        if action == 'add_dept':
            dept = form_dict.get('department', '')
            if dept:
                master_schema['requestors'].setdefault(dept, [])
                detail_msg = f"Added Department '{dept}'"
        elif action == 'delete_dept':
            dept = form_dict.get('department', '')
            master_schema['requestors'].pop(dept, None)
            detail_msg = f"Deleted Department '{dept}'"
        elif action == 'add_requestor':
            dept, name = form_dict.get('department', ''), form_dict.get('name', '')
            if dept in master_schema['requestors'] and name and name not in master_schema['requestors'][dept]:
                master_schema['requestors'][dept].append(name)
                master_schema['requestors'][dept].sort()
                detail_msg = f"Added Requestor '{name}' to {dept}"
        elif action == 'delete_requestor':
            dept, name = form_dict.get('department', ''), form_dict.get('name', '')
            if dept in master_schema['requestors'] and name in master_schema['requestors'][dept]:
                master_schema['requestors'][dept].remove(name)
                detail_msg = f"Removed Requestor '{name}' from {dept}"
        elif action == 'add_area':
            area = form_dict.get('area', '')
            if area:
                master_schema['file_tree'].setdefault(area, {})
                detail_msg = f"Added Area '{area}'"
        elif action == 'delete_area':
            area = form_dict.get('area', '')
            master_schema['file_tree'].pop(area, None)
            detail_msg = f"Deleted Area '{area}'"
        elif action == 'add_location':
            area, loc = form_dict.get('area', ''), form_dict.get('location', '')
            if area in master_schema['file_tree'] and loc:
                master_schema['file_tree'][area].setdefault(loc, {})
                detail_msg = f"Added Location '{loc}'"
        elif action == 'delete_location':
            area, loc = form_dict.get('area', ''), form_dict.get('location', '')
            if area in master_schema['file_tree']:
                master_schema['file_tree'][area].pop(loc, None)
                detail_msg = f"Deleted Location '{loc}'"
        elif action == 'add_sub':
            area, loc, sub = form_dict.get('area', ''), form_dict.get('location', ''), form_dict.get('sub_location', '')
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area] and sub:
                master_schema['file_tree'][area][loc].setdefault(sub, [])
                detail_msg = f"Added Sub-Location '{sub}'"
        elif action == 'delete_sub':
            area, loc, sub = form_dict.get('area', ''), form_dict.get('location', ''), form_dict.get('sub_location', '')
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area]:
                master_schema['file_tree'][area][loc].pop(sub, None)
                detail_msg = f"Deleted Sub-Location '{sub}'"
        elif action == 'add_scope':
            area, loc, sub, scope = form_dict.get('area', ''), form_dict.get('location', ''), form_dict.get('sub_location', ''), form_dict.get('scope', '')
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area] and sub in master_schema['file_tree'][area][loc] and scope:
                if scope not in master_schema['file_tree'][area][loc][sub]:
                    master_schema['file_tree'][area][loc][sub].append(scope)
                    master_schema['file_tree'][area][loc][sub].sort()
                    detail_msg = f"Added Work Scope '{scope}'"
        elif action == 'delete_scope':
            area, loc, sub, scope = form_dict.get('area', ''), form_dict.get('location', ''), form_dict.get('sub_location', ''), form_dict.get('scope', '')
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area] and sub in master_schema['file_tree'][area][loc]:
                if scope in master_schema['file_tree'][area][loc][sub]:
                    master_schema['file_tree'][area][loc][sub].remove(scope)
                    detail_msg = f"Removed Work Scope '{scope}'"
        elif action in ('add_activity', 'add_act', 'add_category', 'add_task_category'):
            if act_type:
                master_schema['activities'].setdefault(act_type, {})
                detail_msg = f"Added Activity Type '{act_type}'"
        elif action in ('delete_activity', 'del_activity', 'del_act', 'delete_act', 'delete_category', 'delete_task_category'):
            if act_type:
                master_schema['activities'].pop(act_type, None)
                detail_msg = f"Deleted Activity Type '{act_type}'"
        elif action in ('add_action', 'add_action_req', 'add_act_req', 'add_sub_act', 'add_discipline'):
            if act_type and act_req:
                master_schema['activities'].setdefault(act_type, {}).setdefault(act_req, [])
                detail_msg = f"Added Action '{act_req}' under {act_type}"
        elif action in ('delete_action', 'del_action', 'delete_action_req', 'del_act_req', 'delete_sub_act', 'delete_discipline'):
            if act_type in master_schema['activities'] and act_req:
                master_schema['activities'][act_type].pop(act_req, None)
                detail_msg = f"Removed Action '{act_req}' from {act_type}"
        elif action in ('add_inst', 'add_instrument', 'add_tool', 'add_allowed_instrument'):
            if act_type and act_req and inst_raw:
                master_schema['activities'].setdefault(act_type, {}).setdefault(act_req, [])
                added_list = []
                for single_inst in [x.strip() for x in inst_raw.split(',') if x.strip()]:
                    if single_inst not in master_schema['activities'][act_type][act_req]:
                        master_schema['activities'][act_type][act_req].append(single_inst)
                        added_list.append(single_inst)
                detail_msg = f"Added Instrument '{', '.join(added_list) or inst_raw}' to {act_type} ➔ {act_req}"
        elif action in ('delete_inst', 'del_inst', 'remove_inst', 'delete_instrument', 'del_instrument', 'delete_tool'):
            if act_type in master_schema['activities'] and act_req in master_schema['activities'][act_type]:
                if inst_raw in master_schema['activities'][act_type][act_req]:
                    master_schema['activities'][act_type][act_req].remove(inst_raw)
                    detail_msg = f"Removed Instrument '{inst_raw}' from {act_type} ➔ {act_req}"

        config.schema_data = json.dumps(master_schema)
        db.session.commit()
        flash(f"System Configuration Updated! ({detail_msg})" if detail_msg else "System Configuration Updated!", 'success')
        return redirect(url_for('hidden_config'))
    return render_template('hidden_admin.html', master_schema_json=json.dumps(master_schema))
'''

idx_hc = code.find("@app.route('/system_config_hidden'")
idx_end_hc = code.find("# --- UNIFIED OMNI-SEARCH")
if idx_hc != -1 and idx_end_hc != -1:
    code = code[:idx_hc] + new_hidden_config + "\n" + code[idx_end_hc:]

ast.parse(code)
with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)
print("1. Updated app.py: Pre-loaded Echo-4 and installed Universal Smart Cascade Resolver in hidden_config().")

# 2. Patch templates/hidden_admin.html so selected Activity Type & Action Required stay open after reload
tpl_path = "templates/hidden_admin.html" if os.path.exists("templates/hidden_admin.html") else "hidden_admin.html"
if os.path.exists(tpl_path):
    with open(tpl_path, "r", encoding="utf-8") as f:
        tpl_html = f.read()

    persistence_js = """
<script>
// Auto-restore selected Activity Type & Action Required after form submit reload
document.addEventListener('DOMContentLoaded', function() {
    try {
        document.addEventListener('click', function(e) {
            const el = e.target.closest('option, li, .list-group-item, div');
            if (!el) return;
            const txt = (el.value || el.textContent || '').trim();
            if (typeof masterSchema !== 'undefined' && masterSchema.activities) {
                if (masterSchema.activities[txt]) {
                    localStorage.setItem('cfg_last_act_type', txt);
                } else {
                    const lastAct = localStorage.getItem('cfg_last_act_type');
                    if (lastAct && masterSchema.activities[lastAct] && masterSchema.activities[lastAct][txt]) {
                        localStorage.setItem('cfg_last_act_req', txt);
                    }
                }
            }
        });

        setTimeout(function() {
            const savedAct = localStorage.getItem('cfg_last_act_type');
            const savedReq = localStorage.getItem('cfg_last_act_req');
            if (savedAct) {
                document.querySelectorAll('select, option, li, div').forEach(function(el) {
                    if (el.tagName === 'SELECT' && [...el.options].some(o => o.value === savedAct)) {
                        el.value = savedAct;
                        el.dispatchEvent(new Event('change'));
                    } else if ((el.tagName === 'OPTION' || el.tagName === 'LI' || el.tagName === 'DIV') && el.children.length === 0 && el.textContent.trim() === savedAct) {
                        el.click();
                    }
                });
            }
            setTimeout(function() {
                if (savedReq) {
                    document.querySelectorAll('select, option, li, div').forEach(function(el) {
                        if (el.tagName === 'SELECT' && [...el.options].some(o => o.value === savedReq)) {
                            el.value = savedReq;
                            el.dispatchEvent(new Event('change'));
                        } else if ((el.tagName === 'OPTION' || el.tagName === 'LI' || el.tagName === 'DIV') && el.children.length === 0 && el.textContent.trim() === savedReq) {
                            el.click();
                        }
                    });
                }
            }, 100);
        }, 60);
    } catch (err) {}
});
</script>
</body>"""

    if "cfg_last_act_type" not in tpl_html and "</body>" in tpl_html:
        tpl_html = tpl_html.replace("</body>", persistence_js, 1)
        with open(tpl_path, "w", encoding="utf-8") as f:
            f.write(tpl_html)
        print(f"2. Added selection memory to {tpl_path} so listboxes stay open after reload.")

# 3. Commit and push to GitHub -> Render
email_res = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True)
author_email = email_res.stdout.strip() or "DRL8490@users.noreply.github.com"

subprocess.run(["git", "add", "-A"], check=False)
subprocess.run([
    "git", "commit",
    f"--author=DRL8490 <{author_email}>",
    "-m", "fix: resolve Task Cascade instrument saving in hidden_config and preload Echo-4"
], check=False)
print("3. Pushing to GitHub...")
subprocess.run(["git", "push", "origin", "main"], check=False)
