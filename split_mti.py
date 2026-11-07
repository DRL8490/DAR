import os, ast, subprocess

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    code = f.read().lstrip("\ufeff")

start_marker = '    html = """<!DOCTYPE html>'
end_marker = '</html>"""'

if start_marker in code and end_marker in code:
    s_idx = code.find(start_marker)
    e_idx = code.find(end_marker) + len(end_marker)
    html_content = code[s_idx + len('    html = """'):e_idx - 3]

    os.makedirs("templates", exist_ok=True)
    with open("templates/mti_dashboard.html", "w", encoding="utf-8") as tf:
        tf.write(html_content)

    code = code[:s_idx] + code[e_idx:]
    code = code.replace("render_template_string(\n        html,", "render_template(\n        'mti_dashboard.html',")
    code = code.replace("from flask import Blueprint, render_template_string", "from flask import Blueprint, render_template, render_template_string")

    ast.parse(code)
    with open("mti_blueprint.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("1. Extracted templates/mti_dashboard.html! mti_blueprint.py is now lightweight.")
    subprocess.run(["py", "sync.py", "refactor: extract mti_dashboard.html template from mti_blueprint.py"], check=False)
else:
    print("Template already extracted or marker not found.")
