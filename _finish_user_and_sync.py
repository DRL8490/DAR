import os, re, glob, ast, subprocess

print("=== [1/2] Updating mti_blueprint.py (Pre-fill Surveyor Name with Current Logged-In User) ===")
if os.path.exists("mti_blueprint.py"):
    b_txt = open("mti_blueprint.py", "r", encoding="utf-8-sig").read().lstrip("\ufeff")

    helper_code = """def _get_current_user_display_name():
    try:
        from flask import session
        from flask_login import current_user
        if current_user and getattr(current_user, "is_authenticated", False):
            for attr in ("full_name", "display_name", "real_name", "name", "surveyor_name", "username", "email"):
                val = getattr(current_user, attr, None)
                if val and str(val).strip():
                    return str(val).strip()
        for k in ("full_name", "display_name", "user_name", "name", "surveyor_name", "username"):
            val = session.get(k)
            if val and str(val).strip():
                return str(val).strip()
    except Exception:
        pass
    return "Duty Surveyor"
"""
    if "def _get_current_user_display_name():" not in b_txt:
        b_txt = b_txt.replace("def _resolve_fix_data(req, ledger):", helper_code + "\ndef _resolve_fix_data(req, ledger):", 1)

    if 'fix_data["surveyor_name"] = str(req.get("surveyor_name") or _get_current_user_display_name()).strip()' not in b_txt:
        b_txt = b_txt.replace(
            "    return fix_data",
            '    fix_data["surveyor_name"] = str(req.get("surveyor_name") or _get_current_user_display_name()).strip()\n    return fix_data',
            1
        )

    # Line-anchored regex so keyword arg init_surveyor=init_surveyor) inside render_template_string() is untouched
    b_txt = re.sub(
        r'(?m)^(\s*init_surveyor\s*=\s*)[^\n]+$',
        r'\1_get_current_user_display_name()',
        b_txt
    )

    b_txt = b_txt.replace(
        "if (document.getElementById('inpSurveyor')) document.getElementById('inpSurveyor').value = row.surveyor_name || row.surveyor || 'Duty Surveyor';",
        "if (document.getElementById('inpSurveyor')) document.getElementById('inpSurveyor').value = '{{ init_surveyor }}';"
    )

    b_txt = b_txt.replace(
        '<option value="400">400</option></select>',
        '<option value="400">400</option><option value="500">500</option><option value="750">750</option><option value="1000">1000</option></select>'
    ).replace(
        '<option value="400">1:400</option></select>',
        '<option value="400">1:400</option><option value="500">1:500</option><option value="750">1:750</option><option value="1000">1:1000</option></select>'
    )

    ast.parse(b_txt)
    open("mti_blueprint.py", "w", encoding="utf-8").write(b_txt)
    print("  -> mti_blueprint.py updated & AST-verified.")

print("=== [2/2] Updating templates/mti_dashboard.html & Syncing to GitHub/Render ===")
t_dash = "templates/mti_dashboard.html"
if os.path.exists(t_dash):
    d_txt = open(t_dash, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    d_txt = d_txt.replace(
        'value="Duty Surveyor"',
        'value="{{ (current_user.full_name or current_user.display_name or current_user.name or current_user.username) if (current_user is defined and current_user.is_authenticated) else session.get(\'user_name\', session.get(\'username\', \'Duty Surveyor\')) }}"'
    )
    open(t_dash, "w", encoding="utf-8").write(d_txt)
    print("  -> templates/mti_dashboard.html updated.")

os.makedirs("workspace", exist_ok=True)
for p in glob.glob(os.path.join("workspace", "*.pdf")):
    try: os.remove(p)
    except Exception: pass

sync_py = "python" if os.path.exists(".venv/Scripts/python.exe") else "py"
subprocess.run([sync_py, "sync.py", "fix(mti): clip overflowing P1 DXF/box labels to axis frame and pre-fill Surveyor Name with current user"], check=False)
