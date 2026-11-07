import os, ast, uuid, subprocess

PWA_ROUTES = """
# --- MOBILE HOME SCREEN SHORTCUT (PWA MANIFEST, SERVICE WORKER & IOS WEBCLIP) ---
@mti_bp.route('/manifest.json')
def mti_manifest():
    from flask import Response
    icon_svg = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'%3E%3Crect width='120' height='120' rx='24' fill='%230b2e4c'/%3E%3Crect x='25' y='25' width='70' height='70' rx='8' fill='%230284c7' stroke='%237dd3fc' stroke-width='6'/%3E%3Ctext x='60' y='68' font-size='26' font-weight='bold' fill='white' text-anchor='middle' font-family='sans-serif'%3EMTI%3C/text%3E%3C/svg%3E"
    manifest = {
        "name": "MMA Prestige MTI Survey Input",
        "short_name": "MTI Input",
        "start_url": "/mti/mobile",
        "scope": "/mti/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#0b2e4c",
        "icons": [{"src": icon_svg, "sizes": "192x192 512x512", "type": "image/svg+xml", "purpose": "any maskable"}]
    }
    return Response(json.dumps(manifest), mimetype='application/manifest+json')

@mti_bp.route('/sw.js')
def mti_sw():
    from flask import Response
    js = "self.addEventListener('install', e => self.skipWaiting()); self.addEventListener('fetch', e => {});"
    return Response(js, mimetype='application/javascript')
"""

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")
if "def mti_manifest" not in mc:
    mc += "\n" + PWA_ROUTES
    ast.parse(mc)
    with open("mti_blueprint.py", "w", encoding="utf-8") as f:
        f.write(mc)

mob_path = "templates/mti_mobile.html"
with open(mob_path, "r", encoding="utf-8-sig") as f:
    html = f.read()

pwa_head = '''<link rel="manifest" href="/mti/manifest.json">
<meta name="theme-color" content="#0b2e4c">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="MTI Input">
</head>'''

pwa_btn = '''<div class="d-flex gap-1">
    <button type="button" id="btnPwaInstall" class="btn btn-sm btn-warning fw-bold text-dark" onclick="triggerPhoneShortcut()">+ Phone Shortcut</button>
    <a href="/mti" class="btn btn-sm btn-outline-info fw-bold">Desktop</a>
  </div>'''

pwa_js = '''let deferredPrompt = null;
if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/mti/sw.js').catch(()=>{}); }
window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferredPrompt = e; });
function triggerPhoneShortcut(){
  if (deferredPrompt) {
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(() => { deferredPrompt = null; });
  } else {
    alert('To add the MTI Input icon to your Phone Home Screen:\\n\\n• iPhone/iPad (Safari): Tap the Share icon at the bottom of the screen, then tap "Add to Home Screen".\\n\\n• Android (Chrome): Tap the 3-dot menu (⋮) at the top right, then tap "Add to Home screen" or "Install app".');
  }
}
</script></body>'''

if 'rel="manifest"' not in html:
    html = html.replace("</head>", pwa_head, 1)
    html = html.replace('<a href="/mti" class="btn btn-sm btn-outline-info fw-bold">Desktop View</a>', pwa_btn, 1)
    html = html.replace("</script></body>", pwa_js, 1)
    with open(mob_path, "w", encoding="utf-8") as f:
        f.write(html)

print("Added 1-Tap Phone Shortcut (PWA + iOS WebApp) to /mti/mobile!")
subprocess.run(["py", "sync.py", "feat: add PWA home screen shortcut installer to /mti/mobile"], check=False)
