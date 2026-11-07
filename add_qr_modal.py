import os, subprocess

QR_BTN = '<button type="button" class="btn btn-light fw-bold text-dark" onclick="openQrModal()"><i class="fas fa-qrcode me-1"></i> Scan QR</button>\n            <a href="/mti/mobile"'

QR_MODAL = """
<div class="modal fade" id="qrMobileModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered modal-sm">
    <div class="modal-content border-0 shadow-lg" style="border-radius:14px;">
      <div class="modal-header bg-dark text-white py-2" style="border-radius:14px 14px 0 0;">
        <h6 class="modal-title fw-bold mb-0"><i class="fas fa-mobile-alt text-warning me-1"></i> Scan for Mobile Input</h6>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body text-center p-3">
        <div class="small fw-bold text-muted mb-2">Point phone camera at QR code to open MTI Mobile Input:</div>
        <img id="mtiQrImg" src="" alt="MTI Mobile QR" class="img-fluid border rounded p-2 mb-2 bg-white" style="width:220px;height:220px;">
        <div class="input-group input-group-sm mb-2">
          <input type="text" id="mtiMobUrlTxt" class="form-control text-center fw-bold" readonly>
          <button class="btn btn-outline-primary fw-bold" type="button" onclick="navigator.clipboard.writeText(document.getElementById('mtiMobUrlTxt').value);this.innerText='Copied!';">Copy</button>
        </div>
        <div class="small text-start bg-light p-2 rounded border" style="font-size:11px;">
          <strong>1.</strong> Scan QR &amp; log in on your phone.<br>
          <strong>2.</strong> Tap <strong>+ Phone Shortcut</strong> at top-right to save the app icon to your Home Screen.
        </div>
      </div>
    </div>
  </div>
</div>
<script>
function openQrModal(){
  var url = window.location.origin + '/mti/mobile';
  document.getElementById('mtiMobUrlTxt').value = url;
  document.getElementById('mtiQrImg').src = 'https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=8&data=' + encodeURIComponent(url);
  new bootstrap.Modal(document.getElementById('qrMobileModal')).show();
}
</script>
</body>"""

for target in ["templates/mti_dashboard.html", "mti_blueprint.py"]:
    if not os.path.exists(target): continue
    with open(target, "r", encoding="utf-8-sig") as f: txt = f.read()
    if 'id="qrMobileModal"' not in txt and '<a href="/mti/mobile"' in txt:
        txt = txt.replace('<a href="/mti/mobile"', QR_BTN, 1)
        txt = txt.replace('</body>', QR_MODAL, 1)
        with open(target, "w", encoding="utf-8") as f: f.write(txt)
        print(f"Added Mobile QR Code modal to {target}!")

subprocess.run(["py", "sync.py", "feat: add scannable Mobile Input QR code modal to MTI desktop header"], check=False)
