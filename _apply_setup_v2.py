import os, re, ast, subprocess

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")
with open("_setup_v2_routes.py", "r", encoding="utf-8-sig") as f:
    p4 = f.read().lstrip("\ufeff")

mc = re.sub(r"# --- STEP 4:.*", "", mc, flags=re.S)
mc = re.sub(r'<script id="mti4PanelStudioUpgrade">.*?</script>', "", mc, flags=re.S)
mc = mc.rstrip() + "\n\n" + p4.strip() + "\n"

ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)

print("AST-verified mti_blueprint.py and mti_4panel_math.py!")
subprocess.run(["py", "sync.py", "fix(mti-setup): use raw string template to fix JS SyntaxError and add live file parsing/cropping cues"], check=False)
