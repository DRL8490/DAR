import ast, subprocess, os

with open("write_mti_raw.txt", "r", encoding="utf-8-sig") as f:
    clean_code = f.read().lstrip("\ufeff")

ast.parse(clean_code)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(clean_code)
os.remove("write_mti_raw.txt")
print("1. Verified and wrote BOM-free mti_blueprint.py with 6-column Ledger and 8-button Survey Input Log!")

subprocess.run(["py", "sync.py", "feat: update MTI ledger to 6 columns and replace audit log with 8-button Survey Input Log"], check=False)
