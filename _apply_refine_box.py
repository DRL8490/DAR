import os, re, glob, ast, subprocess

print("=== [1/3] Updating mti_blueprint.py (Current User Detection, Ledger Tagging & Studio Sync) ===")
if os.path.exists("mti_blueprint.py"):
    b_txt = open("mti_blueprint.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")

    improved_helper = """def _get_current_user_display_name():
    try:
        from flask import session, g, request
        try:
            from flask_login import current_user
            if current_user and getattr(current_user, "is_authenticated", False):
                for attr in ("full_name", "display_name", "real_name", "name", "surveyor_name", "username", "user", "email"):
                    val = getattr(current_user, attr, None)
                    if val and str(val).strip() and str(val).strip().lower() != "duty surveyor":
                        return str(val).strip()
                u_dict = getattr(current_user, "__dict__", {}) or {}
                for k, val in u_dict.items():
                    if any(w in k.lower() for w in ("name", "user", "surveyor")) and isinstance(val, str) and val.strip():
                        return val.strip()
        except Exception:
            pass
        for g_attr in ("user", "current_user", "username", "user_name", "surveyor"):
            g_val = getattr(g, g_attr, None)
            if isinstance(g_val, str) and g_val.strip():
                return g_val.strip()
            elif hasattr(g_val, "username") or hasattr(g_val, "name"):
                v = getattr(g_val, "full_name", None) or getattr(g_val, "name", None) or getattr(g_val, "username", None)
                if v and str(v).strip():
                    return str(v).strip()
        for k in ("full_name", "display_name", "real_name", "user_name", "username", "name", "surveyor_name", "surveyor", "user", "logged_in_user", "operator"):
            val = session.get(k)
            if isinstance(val, dict):
                for sk in ("full_name", "display_name", "name", "username", "user"):
                    if val.get(sk) and str(val.get(sk)).strip():
                        return str(val.get(sk)).strip()
            elif val and isinstance(val, str) and val.strip() and val.strip().lower() != "duty surveyor":
                return val.strip()
        for k, val in dict(session).items():
            kl = str(k).lower()
            if any(w in kl for w in ("user", "name", "surv")) and isinstance(val, str) and 2 <= len(val.strip()) <= 50:
                if not val.strip().isdigit() and val.strip().lower() != "duty surveyor":
                    return val.strip()
        st = load_mti_state()
        for log_list_key in ("logs", "events", "event_log", "survey_logs"):
            logs = st.get(log_list_key) or []
            for lg in logs:
                if isinstance(lg, dict):
                    for lk in ("surveyor", "surveyor_name", "user", "username", "author", "logged_by"):
                        lv = lg.get(lk)
                        if lv and str(lv).strip() and str(lv).strip().lower() != "duty surveyor":
                            return str(lv).strip()
    except Exception:
        pass
    return "Duty Surveyor"
"""
    if "def _get_current_user_display_name():" in b_txt:
        b_txt = re.sub(
            r"def _get_current_user_display_name\(\):.*?(?=\ndef _resolve_fix_data)",
            improved_helper.strip() + "\n",
            b_txt,
            flags=re.S
        )
    else:
        b_txt = b_txt.replace("def _resolve_fix_data(req, ledger):", improved_helper + "\ndef _resolve_fix_data(req, ledger):", 1)

    b_txt = re.sub(
        r'fix_data\["surveyor_name"\]\s*=\s*[^\n]+\n\s*return fix_data',
        '    return fix_data',
        b_txt
    )
    new_res_tail = (
        '    req_surv = str(req.get("surveyor_name") or "").strip()\n'
        '    saved_surv = str(fix_data.get("surveyor_name") or fix_data.get("surveyor") or "").strip()\n'
        '    cur_u = _get_current_user_display_name()\n'
        '    if req_surv and req_surv.lower() != "duty surveyor":\n'
        '        fix_data["surveyor_name"] = req_surv\n'
        '    elif saved_surv and saved_surv.lower() != "duty surveyor":\n'
        '        fix_data["surveyor_name"] = saved_surv\n'
        '    else:\n'
        '        fix_data["surveyor_name"] = cur_u\n'
        '    return fix_data'
    )
    if 'req_surv = str(req.get("surveyor_name")' not in b_txt:
        b_txt = b_txt.replace("    return fix_data", new_res_tail, 1)

    whoami_route = """
@mti_bp.route('/whoami')
@login_required
def mti_whoami():
    return jsonify({"status": "ok", "user_name": _get_current_user_display_name()})

@mti_bp.after_request
def _mti_ensure_surveyor_saved(response):
    try:
        if request.method == 'POST' and any(p in request.path for p in ('add_fix', 'save_fix', 'edit_fix', 'update_fix')):
            s_name = str(request.form.get('surveyor_name') or _get_current_user_display_name()).strip()
            box_id = str(request.form.get('design_box_id') or request.form.get('box_id') or '').strip()
            if s_name:
                st = load_mti_state()
                ledger = st.get('ledger') or []
                changed = False
                for r in ledger:
                    if box_id and str(r.get('design_box_id', '')).upper() == box_id.upper():
                        r['surveyor_name'] = s_name
                        r['surveyor'] = s_name
                        changed = True
                    elif not r.get('surveyor_name') or str(r.get('surveyor_name')).strip().lower() == 'duty surveyor':
                        r['surveyor_name'] = s_name
                        changed = True
                if changed:
                    save_mti_state(st)
    except Exception:
        pass
    return response
"""
    if "def mti_whoami():" not in b_txt:
        b_txt = b_txt.replace("@mti_bp.route('/verify_4panel'", whoami_route.lstrip() + "\n@mti_bp.route('/verify_4panel'", 1)

    b_txt = re.sub(
        r'(?m)^(\s*init_surveyor\s*=\s*)[^\n]+$',
        r'\1str(req.get("surveyor_name") or _get_current_user_display_name()).strip()',
        b_txt
    )

    ast.parse(b_txt)
    open("mti_blueprint.py", "w", encoding="utf-8").write(b_txt)
    print("  -> mti_blueprint.py updated & AST-verified.")

print("=== [2/3] Updating templates/mti_dashboard.html (Remove Line 4 Z Boxes & Pre-fill Current User) ===")
with open("_refined_dash_js.html", "r", encoding="utf-8-sig") as f:
    s5 = f.read().lstrip("\ufeff").strip()

for t_path in ("templates/mti_dashboard.html", "mti_blueprint.py"):
    if not os.path.exists(t_path):
        continue
    raw_t = open(t_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    raw_t = raw_t.replace("E, N, Z OF 4-CORNERS OF MATTRESS", "E, N OF 4-CORNERS OF MATTRESS")
    for idx, d_lbl in [(1, "NW"), (2, "NE"), (3, "SE"), (4, "SW")]:
        raw_t = raw_t.replace(f"Corner {idx} (C{idx} - {d_lbl}: E, N, Z)", f"Corner {idx} (C{idx} - {d_lbl}: E, N)")

    def _hide_z_inp(m):
        tag = m.group(1)
        if 'type=' in tag:
            tag = re.sub(r'\btype\s*=\s*["\'][^"\']*["\']', 'type="hidden"', tag)
        else:
            tag = tag.replace('<input ', '<input type="hidden" ')
        if 'style=' not in tag:
            tag = tag[:-1] + ' style="display:none;">'
        return tag

    raw_t = re.sub(r'(<input\b[^>]*?\b(?:name|id)\s*=\s*["\']c[1-4]_z["\'][^>]*?>)', _hide_z_inp, raw_t, flags=re.I)

    if t_path == "templates/mti_dashboard.html":
        raw_t = re.sub(r'<script id="mti4PanelStudioUpgrade">.*?</script>', '', raw_t, flags=re.S)
        if "</body>" in raw_t:
            raw_t = raw_t.replace("</body>", s5 + "\n</body>", 1)
        elif "{% endblock %}" in raw_t:
            idx = raw_t.rfind("{% endblock %}")
            raw_t = raw_t[:idx] + s5 + "\n" + raw_t[idx:]
        else:
            raw_t = raw_t.rstrip() + "\n" + s5 + "\n"
    else:
        ast.parse(raw_t)
    open(t_path, "w", encoding="utf-8").write(raw_t)
    print(f"  -> Updated Line 4 Z-inputs & Surveyor Name sync in: {t_path}")

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try: os.remove(p)
    except Exception: pass

print("=== [3/3] Pushing Update to GitHub & Render ===")
sync_py = "python" if os.path.exists(".venv/Scripts/python.exe") else "py"
subprocess.run([sync_py, "sync.py", "feat(mti): pre-fill Surveyor Name with current user across form/4-panel/report and remove Line 4 Z input boxes"], check=False)
