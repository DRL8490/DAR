import os, re, ast, subprocess

for target in ["templates/mti_dashboard.html", "templates/mti_mobile.html", "mti_blueprint.py"]:
    if not os.path.exists(target):
        continue
    with open(target, "r", encoding="utf-8-sig") as f:
        txt = f.read()

    # 1. Update "Mattress on water": remove "Recover to Deck" and add "Attempted Mattress Placement"
    txt = txt.replace(
        "Overboard / Seabed Align / Tagline / Recover to Deck (#A023)",
        "Overboard / Seabed Align / Tagline / Attempted Mattress Placement (#A023)"
    ).replace(
        "Recover to Deck",
        "Attempted Mattress Placement"
    )

    # 2. Remove Swell input across all buttons (Event Input Strip & Mattress Fix Form) and expand Wind & Current to col-6
    txt = txt.replace(
        "Environmental Inputs (Wind, Current & Swell)",
        "Environmental Inputs (Wind & Current)"
    ).replace(
        "Environmental Inputs (Wind, Current &amp; Swell)",
        "Environmental Inputs (Wind &amp; Current)"
    )

    txt = re.sub(
        r'<div class="col-4"><input type="text" name="env_swell"[^>]*></div>',
        '',
        txt
    )

    txt = re.sub(
        r'<div class="col-4">(\s*<input type="text" name="env_(?:wind|current)")',
        r'<div class="col-6">\1',
        txt
    )

    if target.endswith(".py"):
        txt = txt.replace(
            '[("Wind", env_w), ("Curr", env_c), ("Swell", env_s)]',
            '[("Wind", env_w), ("Curr", env_c)]'
        )
        ast.parse(txt)

    with open(target, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"Updated {target}: removed Swell input & added Attempted Mattress Placement to Mattress on water!")

subprocess.run(["py", "sync.py", "feat: remove swell input across all buttons and replace Recover to Deck with Attempted Mattress Placement"], check=False)
