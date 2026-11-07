import os, ast, subprocess

KEEPALIVE_HOOK = """
# --- 12-MINUTE INACTIVITY AUTO-REFRESH & RENDER KEEP-ALIVE ---
@app.route('/ping', methods=['GET'])
def render_keepalive_ping():
    return "OK", 200

@app.after_request
def inject_inactivity_refresh(response):
    if response.content_type and 'text/html' in response.content_type and response.status_code == 200:
        try:
            html_text = response.get_data(as_text=True)
            if '</body>' in html_text and 'id="renderIdleRefresh"' not in html_text:
                idle_js = '''<script id="renderIdleRefresh">
(function(){
  var idleLimit = 12 * 60 * 1000, lastAct = Date.now();
  ['mousemove','mousedown','keydown','touchstart','scroll'].forEach(function(ev){
    document.addEventListener(ev, function(){ lastAct = Date.now(); }, {passive:true});
  });
  setInterval(function(){
    fetch('/ping', {cache:'no-store'}).catch(function(){});
    if (Date.now() - lastAct >= idleLimit) { window.location.reload(); }
  }, 60000);
})();
</script></body>'''
                response.set_data(html_text.replace('</body>', idle_js, 1))
        except Exception:
            pass
    return response
"""

with open("app.py", "r", encoding="utf-8-sig") as f:
    code = f.read().lstrip("\ufeff")

if "def inject_inactivity_refresh" not in code:
    idx = code.rfind("if __name__ ==")
    code = (code[:idx] + KEEPALIVE_HOOK + "\n" + code[idx:]) if idx != -1 else (code + "\n" + KEEPALIVE_HOOK)
    ast.parse(code)
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("Step 1 Complete: 12-minute inactivity refresh injected globally into app.py!")
    subprocess.run(["py", "sync.py", "feat: add global 12-minute inactivity auto-refresh and /ping keep-alive"], check=False)
else:
    print("Step 1 already installed in app.py.")
