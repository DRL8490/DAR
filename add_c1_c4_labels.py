import os, re, ast, subprocess

NEW_SVG_BLOCK = """<svg width="140" height="84" viewBox="0 0 140 84" style="background:#e2e8f0;border-radius:6px;border:1px solid #cbd5e1;">
            <line x1="70" y1="0" x2="70" y2="84" stroke="#94a3b8" stroke-dasharray="2,2"/><line x1="0" y1="42" x2="140" y2="42" stroke="#94a3b8" stroke-dasharray="2,2"/>
            <g id="svgMattRot" transform="rotate(15.854 70 42)">
              <rect x="58" y="18" width="24" height="48" fill="#0284c7" fill-opacity="0.28" stroke="#0369a1" stroke-width="1.8"/>
              <line x1="70" y1="54" x2="70" y2="66" stroke="#dc2626" stroke-width="2.2"/>
              <circle cx="58" cy="18" r="2.8" fill="#16a34a"/><circle cx="82" cy="18" r="2.8" fill="#16a34a"/>
              <circle cx="82" cy="66" r="2.8" fill="#16a34a"/><circle cx="58" cy="66" r="2.8" fill="#16a34a"/>
              <text id="svgTxtC1" x="47" y="16" font-size="9.5" font-weight="800" fill="#0f172a" text-anchor="middle" transform="rotate(-15.854 47 13)">C1</text>
              <text id="svgTxtC2" x="93" y="16" font-size="9.5" font-weight="800" fill="#0f172a" text-anchor="middle" transform="rotate(-15.854 93 13)">C2</text>
              <text id="svgTxtC3" x="93" y="72" font-size="9.5" font-weight="800" fill="#0f172a" text-anchor="middle" transform="rotate(-15.854 93 69)">C3</text>
              <text id="svgTxtC4" x="47" y="72" font-size="9.5" font-weight="800" fill="#0f172a" text-anchor="middle" transform="rotate(-15.854 47 69)">C4</text>
            </g>
          </svg>"""

for target in ["templates/mti_dashboard.html", "templates/mti_mobile.html", "mti_blueprint.py"]:
    if not os.path.exists(target): continue
    with open(target, "r", encoding="utf-8-sig") as f: txt = f.read()

    txt = re.sub(r'<svg width="110" height="68" viewBox="0 0 110 68".*?</svg>', NEW_SVG_BLOCK, txt, count=1, flags=re.S)

    txt = txt.replace("Corner 1 (C1: E, N, Z)", "Corner 1 (C1 - NW: E, N, Z)")
    txt = txt.replace("Corner 2 (C2: E, N, Z)", "Corner 2 (C2 - NE: E, N, Z)")
    txt = txt.replace("Corner 3 (C3: E, N, Z)", "Corner 3 (C3 - SE: E, N, Z)")
    txt = txt.replace("Corner 4 (C4: E, N, Z)", "Corner 4 (C4 - SW: E, N, Z)")
    txt = txt.replace('placeholder="NW (m)"', 'placeholder="C1 / NW (m)" style="width:92px;height:24px;font-size:11px;"')
    txt = txt.replace('placeholder="NE (m)"', 'placeholder="C2 / NE (m)" style="width:92px;height:24px;font-size:11px;"')
    txt = txt.replace('placeholder="SW (m)"', 'placeholder="C4 / SW (m)" style="width:92px;height:24px;font-size:11px;"')
    txt = txt.replace('placeholder="SE (m)"', 'placeholder="C3 / SE (m)" style="width:92px;height:24px;font-size:11px;"')

    txt = txt.replace(
        "const rad = brg * Math.PI / 180.0, sb = Math.sin(rad), cb = Math.cos(rad);",
        "const rad = ((brg - 180.0) * Math.PI / 180.0), sb = Math.sin(rad), cb = Math.cos(rad);"
    )
    txt = txt.replace(
        "const fe = (pts[0][0]+pts[1][0])/2.0, fn = (pts[0][1]+pts[1][1])/2.0;\n    const be = (pts[2][0]+pts[3][0])/2.0, bn = (pts[2][1]+pts[3][1])/2.0;",
        "const be = (pts[0][0]+pts[1][0])/2.0, bn = (pts[0][1]+pts[1][1])/2.0;\n    const fe = (pts[2][0]+pts[3][0])/2.0, fn = (pts[2][1]+pts[3][1])/2.0;"
    )
    old_rot_js = "if (g) g.setAttribute('transform', `rotate(${brg} 55 34)`);"
    new_rot_js = """const rot = ((brg - 180.0) + 360.0) % 360.0;
    if (g) g.setAttribute('transform', `rotate(${rot} 70 42)`);
    [['svgTxtC1',47,13],['svgTxtC2',93,13],['svgTxtC3',93,69],['svgTxtC4',47,69]].forEach(c => {
      const el = document.getElementById(c[0]);
      if (el) el.setAttribute('transform', `rotate(${-rot} ${c[1]} ${c[2]})`);
    });"""
    txt = txt.replace(old_rot_js, new_rot_js)

    if target.endswith(".py"):
        txt = txt.replace(
            "fe, fn = (pts[0][0] + pts[1][0]) / 2.0, (pts[0][1] + pts[1][1]) / 2.0\n        be, bn = (pts[2][0] + pts[3][0]) / 2.0, (pts[2][1] + pts[3][1]) / 2.0",
            "be, bn = (pts[0][0] + pts[1][0]) / 2.0, (pts[0][1] + pts[1][1]) / 2.0\n        fe, fn = (pts[2][0] + pts[3][0]) / 2.0, (pts[2][1] + pts[3][1]) / 2.0"
        )
        ast.parse(txt)

    with open(target, "w", encoding="utf-8") as f: f.write(txt)
    print(f"Added C1, C2, C3, C4 corner labels to Box 1 SVG and Line 4 in {target}!")

subprocess.run(["py", "sync.py", "feat: add C1, C2, C3, C4 corner labels to North-Up gap diagram matching Line 4 ROV inputs"], check=False)
