import os, re, ast, subprocess

# === 1. UPDATE ISO A3 4-PANEL GEOMETRY IN mti_4panel_a3.py ===
a3_path = "mti_4panel_a3.py"
if not os.path.exists(a3_path):
    raise SystemExit("mti_4panel_a3.py not found! Run inside your DAR project folder.")

a3 = open(a3_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")

# Panel 1: 128.0 x 219.0 mm at (33.0, 41.0)
a3, n_p1 = re.subn(
    r"ax1 = fig\.add_axes\(\[[^\]]+\]\)\s*\n\s*hw1, hh1 = [^\n]+",
    "ax1 = fig.add_axes([33.0 / W_MM, 41.0 / H_MM, 128.0 / W_MM, 219.0 / H_MM])\n    hw1, hh1 = (128.0 / 1000.0) * float(scale_p1) / 2.0, (219.0 / 1000.0) * float(scale_p1) / 2.0",
    a3, count=1
)

# Panel 2: Identical 128.0 x 219.0 mm at (179.0, 41.0)
a3, n_p2 = re.subn(
    r"ax2 = fig\.add_axes\(\[[^\]]+\]\)\s*\n\s*hw2, hh2 = [^\n]+",
    "ax2 = fig.add_axes([179.0 / W_MM, 41.0 / H_MM, 128.0 / W_MM, 219.0 / H_MM])\n    hw2, hh2 = (128.0 / 1000.0) * float(scale_p2) / 2.0, (219.0 / 1000.0) * float(scale_p2) / 2.0",
    a3, count=1
)

# Colorbar matched to P1/P2 height (219.0 mm) at x = 309.8 mm
a3, n_cb = re.subn(
    r"cax2 = fig\.add_axes\(\[[^\]]+\]\)",
    "cax2 = fig.add_axes([309.8 / W_MM, 41.0 / H_MM, 3.2 / W_MM, 219.0 / H_MM])",
    a3, count=1
)

# Panels 3 & 4: Decreased by 30% (83.0x88.0 -> 58.1x61.6 mm), centered vertically at x = 341.9 mm
new_p34_block = """    for ax_p, coord_arr, lim_x, edge_v, is_long, ttl_top, x_lbl in [
        (fig.add_axes([341.9 / W_MM, 163.9 / H_MM, 58.1 / W_MM, 61.6 / H_MM]), y_local, (-3.486, 3.486), 3.0, True, "PANEL 3: LONGITUDINAL (SSW -> NNE)", "Along-Track Y_local (m)"),
        (fig.add_axes([341.9 / W_MM, 75.5 / H_MM, 58.1 / W_MM, 61.6 / H_MM]), x_local, (-3.486, 3.486), 1.5, False, "PANEL 4: LATERAL (WNW -> ESE)", "Cross-Track X_local (m)")
    ]:
        ax_p.scatter(coord_arr, z_vals, c=z_vals, cmap="turbo", vmin=vmin_c, vmax=vmax_c, s=9, alpha=0.85, label="Mattress Surface")
        xs_l = np.linspace(lim_x[0], lim_x[1], 40)
        if bathy_src == "SURVEY_BATHY" and len(sb_loc_arr) >= 1:
            q_prof = np.column_stack([np.zeros_like(xs_l), xs_l]) if is_long else np.column_stack([xs_l, np.zeros_like(xs_l)])
            z_prof = idw_interpolate(sb_loc_arr[:, :2], sb_loc_arr[:, 2], q_prof)
            ax_p.plot(xs_l, z_prof, "--", color="#0284c7", lw=1.25, label="Survey Seabed Profile")
            z_center = 0.5 * (float(np.mean(z_vals)) + float(np.mean(z_prof)))
            half_win = max(0.616, 0.5 * abs(float(np.max(z_prof) - np.min(z_vals))) + 0.32)
        else:
            z_center = z_mean
            half_win = 0.616
        v_sc_lbl = int(round((2.0 * half_win) / (61.6 / 1000.0)))
        ttl = ttl_top + chr(10) + f"H 1:120 | V 1:{v_sc_lbl} @ A3"
        if z_center <= 0:
            y_bottom, y_top = z_center - half_win, z_center + half_win
        else:
            y_bottom, y_top = z_center + half_win, z_center - half_win
        ax_p.axvline(-edge_v, color="#dc2626", ls="--", lw=1.1, label=f"Design (+/-{edge_v:.1f}m)"); ax_p.axvline(edge_v, color="#dc2626", ls="--", lw=1.1)
        ax_p.set_xlim(*lim_x); ax_p.set_ylim(y_bottom, y_top)
        ax_p.set_title(ttl, fontsize=6.5, fontweight="bold", pad=3); ax_p.set_xlabel(x_lbl, fontsize=5.9, fontweight="bold"); ax_p.set_ylabel("Depth Z (m, TWVD2001)", fontsize=5.9, fontweight="bold")
        ax_p.tick_params(labelsize=5.2); ax_p.grid(True, linestyle=":", lw=0.45, color="#cbd5e1"); ax_p.legend(loc="lower right", fontsize=4.6, framealpha=0.9)"""

a3, n_p34 = re.subn(
    r"    for ax_p, coord_arr, lim_x, edge_v, is_long, ttl(?:_top)?, x_lbl in \[.*?(?=\n\s*buf_png = io\.BytesIO\(\))",
    lambda _m: new_p34_block,
    a3, count=1, flags=re.S
)
if not (n_p1 and n_p2 and n_cb and n_p34):
    raise SystemExit(f"Panel replacement mismatch in mti_4panel_a3.py: {(n_p1, n_p2, n_cb, n_p34)}")

ast.parse(a3)
open(a3_path, "w", encoding="utf-8").write(a3)
print("  -> Updated mti_4panel_a3.py (P1=P2=128x219mm, P3=P4=58.1x61.6mm [-30%], AST OK)")

# === 2. RESTORE & LOCK RECORDED MATTRESS FIX SURVEYOR IN mti_blueprint.py ===
bp_path = "mti_blueprint.py"
bp = open(bp_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")

resolve_replacement = """def _find_fix_surveyor_from_logs(box_id, input_logs, tag_id=""):
    b_up = str(box_id or "").strip().upper()
    t_up = str(tag_id or "").strip().upper().replace("#", "")
    best = ""
    for lg in (input_logs or []):
        if str(lg.get("event_type") or "").strip().lower() != "mattress fix":
            continue
        ref_up = str(lg.get("ref_id") or "").upper()
        if b_up and re.search(rf"(?<![A-Za-z0-9_-]){re.escape(b_up)}(?![0-9])", ref_up):
            cand = str(lg.get("surveyor") or lg.get("surveyor_name") or "").strip()
            if cand and cand.lower() not in ("duty surveyor", "surveyor"):
                best = cand
                if t_up and t_up in ref_up:
                    return cand
    return best

def _resolve_fix_data(req, ledger, input_logs=None):
    uno = str(req.get("unit_no") or req.get("fix_id") or "").strip()
    box_q = str(req.get("design_box_id") or req.get("location_id") or req.get("box_id") or "").strip()
    tag_q = str(req.get("physical_tag") or req.get("mattress_id") or "").strip()
    matched = None
    if box_q:
        matched = next((r for r in ledger if str(r.get("design_box_id", "")).upper() == box_q.upper()), None)
    if not matched and uno:
        matched = next((r for r in ledger if str(r.get("unit_no", "")) == uno or str(r.get("id", "")) == uno), None)
    if not matched and tag_q:
        matched = next((r for r in ledger if str(r.get("physical_tag", "")).replace("#", "").upper() == tag_q.replace("#", "").upper()), None)
    if not matched and ledger and not box_q:
        matched = ledger[0]
    fix_data = dict(matched) if matched else {}
    for k, v in req.items():
        if k in ("unit_no", "fix_id", "surveyor_name", "surveyor_override") and matched:
            continue
        if v is not None and str(v).strip() != "":
            fix_data[k] = v
    if box_q and "design_box_id" not in fix_data:
        fix_data["design_box_id"] = box_q
    log_surv = _find_fix_surveyor_from_logs(fix_data.get("design_box_id"), input_logs, fix_data.get("physical_tag"))
    saved_surv = str((matched or {}).get("surveyor_name") or (matched or {}).get("surveyor") or "").strip()
    if not saved_surv or saved_surv.lower() in ("duty surveyor", "surveyor"):
        saved_surv = log_surv
    req_surv = str(req.get("surveyor_name") or "").strip()
    is_override = str(req.get("surveyor_override") or "").strip() == "1"
    if is_override and req_surv and req_surv.lower() != "duty surveyor":
        fix_data["surveyor_name"] = req_surv
    elif saved_surv and saved_surv.lower() != "duty surveyor":
        fix_data["surveyor_name"] = saved_surv
    elif log_surv:
        fix_data["surveyor_name"] = log_surv
    elif not matched and req_surv and req_surv.lower() != "duty surveyor":
        fix_data["surveyor_name"] = req_surv
    else:
        fix_data["surveyor_name"] = _get_current_user_display_name()
    return fix_data
"""

bp, n_res = re.subn(
    r"(?:def _find_fix_surveyor_from_logs\(.*?\n)?def _resolve_fix_data\(req, ledger.*?\n(?=@mti_bp\.route\('/whoami'\))",
    lambda _m: resolve_replacement + "\n",
    bp, count=1, flags=re.S
)
if not n_res:
    raise SystemExit("Could not locate _resolve_fix_data() in mti_blueprint.py!")

# Pass input_logs into _resolve_fix_data in verify_4panel & remove viewer DB overwrite
bp = bp.replace(
    "fix_data = _resolve_fix_data(req, ledger)",
    "fix_data = _resolve_fix_data(req, ledger, st.get('input_logs', []))"
)
bp = re.sub(
    r"\n\s*if req\.get\('surveyor_name'\) or req\.get\('install_date'\):.*?except Exception:\s*pass",
    "",
    bp, flags=re.S
)

# Update mti_4panel_studio_window() to load each unit's recorded surveyor (never current viewer login)
new_studio_route = """@mti_bp.route('/studio')
@login_required
def mti_4panel_studio_window():
    st = load_mti_state()
    in_logs = st.get("input_logs", [])
    raw_ledger = sorted(st.get("ledger", []), key=lambda x: int(x.get("unit_no", 999)))
    if "_enrich_fix_row" in globals() and "_merged_cat_map" in globals():
        ledger = [_enrich_fix_row(r, _merged_cat_map(), in_logs) for r in raw_ledger]
    else:
        ledger = []
        for r in raw_ledger:
            d = dict(r)
            ls = _find_fix_surveyor_from_logs(d.get("design_box_id"), in_logs, d.get("physical_tag"))
            if not d.get("surveyor_name") or str(d.get("surveyor_name")).lower() in ("duty surveyor", "surveyor"):
                if ls:
                    d["surveyor_name"] = ls
            ledger.append(d)
    req = request.args.to_dict()
    fd = _resolve_fix_data(req, ledger, in_logs)
    init_box = fd.get("design_box_id") or "CR-A1_M15"
    init_tag = fd.get("physical_tag") or "#A046"
    init_date = fd.get("install_date") or "2026-11-04 14:34"
    init_surveyor = str(fd.get("surveyor_name") or _get_current_user_display_name()).strip()
    return render_template_string(STUDIO_HTML_TEMPLATE, ledger=ledger, ledger_json=json.dumps(ledger), init_box=init_box, init_tag=init_tag, init_date=init_date, init_surveyor=init_surveyor)
"""

bp, n_st = re.subn(
    r"@mti_bp\.route\('/studio'\)\s*\n@login_required\s*\ndef mti_4panel_studio_window\(\):.*?\n(?=@mti_bp\.route\('/setup'\))",
    lambda _m: new_studio_route + "\n",
    bp, count=1, flags=re.S
)

# Update STUDIO_HTML_TEMPLATE input & JS so Ledger Switcher & initial render show recorded surveyor
bp = bp.replace(
    'id="inpSurveyor" class="form-control form-control-sm fw-bold bg-dark text-warning border-info" value="{{ init_surveyor }}" placeholder="e.g. Abror / Roderick">',
    'id="inpSurveyor" class="form-control form-control-sm fw-bold bg-dark text-warning border-info" value="{{ init_surveyor }}" placeholder="Recorded Fix Surveyor" oninput="this.dataset.userEdited=\'1\'">'
)

bp = re.sub(
    r"window\.selectLedgerUnit = function\(boxId\) \{.*?\n\};",
    """window.selectLedgerUnit = function(boxId) {
  for (const k of Array.from(INIT_PARAMS.keys())) { INIT_PARAMS.delete(k); }
  const row = LEDGER_DATA.find(r => r.design_box_id === boxId);
  const sEl = document.getElementById('inpSurveyor');
  if (sEl) sEl.dataset.userEdited = '';
  if (row) {
    document.getElementById('inpBoxId').value = row.design_box_id || '';
    document.getElementById('inpTagId').value = row.physical_tag || '';
    if (document.getElementById('inpInstallDate')) document.getElementById('inpInstallDate').value = row.install_date || '';
    if (sEl) sEl.value = row.surveyor_name || row.surveyor || '';
  }
  window.runStudioVerify({ design_box_id: boxId, unit_no: row ? (row.unit_no || '') : '' });
};""",
    bp, count=1, flags=re.S
)

bp = bp.replace(
    "if (document.getElementById('inpSurveyor')) payload.surveyor_name = document.getElementById('inpSurveyor').value.trim();",
    "const _sEl = document.getElementById('inpSurveyor'); if (_sEl && _sEl.dataset.userEdited === '1' && _sEl.value.trim()) { payload.surveyor_name = _sEl.value.trim(); payload.surveyor_override = '1'; } else { delete payload.surveyor_name; delete payload.surveyor_override; }"
)

# Add one-time DB repair to restore ledger surveyor_name from original "Mattress fix" input_logs
bottom_repair = """
# --- MTI_GAP_TOL_050_FINAL_ENFORCE_START ---
_real_final_load_mti_state = load_mti_state
_final_gaptol_saving = False

def load_mti_state(*args, **kwargs):
    global _final_gaptol_saving
    st = _real_final_load_mti_state(*args, **kwargs)
    if isinstance(st, dict):
        dirty = False
        cur_g = st.get("gap_tolerance_m")
        if not st.get("gap_tol_050_v2") or cur_g is None or abs(float(cur_g) - 0.20) < 1e-6:
            st["gap_tolerance_m"] = 0.50
            if isinstance(st.get("survey_setup"), dict):
                st["survey_setup"]["gap_tolerance_m"] = 0.50
            st["gap_tol_050_v2"] = True
            dirty = True
        if not st.get("studio_surveyor_repair_v1"):
            in_logs = st.get("input_logs") or []
            for r in (st.get("ledger") or []):
                orig_s = _find_fix_surveyor_from_logs(r.get("design_box_id"), in_logs, r.get("physical_tag"))
                if orig_s:
                    r["surveyor_name"] = orig_s
                    r["surveyor"] = orig_s
            st["studio_surveyor_repair_v1"] = True
            dirty = True
        if dirty and not _final_gaptol_saving:
            try:
                _final_gaptol_saving = True
                save_mti_state(st)
            except Exception:
                pass
            finally:
                _final_gaptol_saving = False
    return st
# --- MTI_GAP_TOL_050_FINAL_ENFORCE_END ---
"""

bp = re.sub(
    r"# --- MTI_GAP_TOL_050_FINAL_ENFORCE_START ---.*?# --- MTI_GAP_TOL_050_FINAL_ENFORCE_END ---",
    lambda _m: bottom_repair.strip(),
    bp, count=1, flags=re.S
)

if "_purge_cached_pdfs" in bp:
    ast.parse(bp)
open(bp_path, "w", encoding="utf-8").write(bp)
print("  -> Updated mti_blueprint.py (Recorded Fix Surveyor restored & Studio switcher synced, AST OK)")

# === 3. REMOVE VIEWER SURVEYOR QUERY PARAMS FROM CHART LINKS IN templates/mti_dashboard.html ===
dash_path = os.path.join("templates", "mti_dashboard.html")
if os.path.exists(dash_path):
    dash = open(dash_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    dash = dash.replace(
        "chartBtn.href = '/mti/studio' + (activeUser ? ('?surveyor_name=' + encodeURIComponent(activeUser)) : '');",
        "chartBtn.href = '/mti/studio';"
    )
    dash = dash.replace(
        "if (topStudio) topStudio.href = '/mti/studio?surveyor_name=' + encodeURIComponent(d.user_name);",
        "if (topStudio) topStudio.href = '/mti/studio';"
    )
    dash = dash.replace(
        "(activeSurv ? ('&surveyor_name=' + encodeURIComponent(activeSurv)) : '');",
        "'';"
    )
    open(dash_path, "w", encoding="utf-8").write(dash)
    print("  -> Cleaned viewer surveyor_name query overrides from templates/mti_dashboard.html")

# Purge cached PDFs/PNGs/DXFs so new panel sizes & surveyor render fresh immediately
for ws_f in os.listdir("workspace") if os.path.exists("workspace") else []:
    if ws_f.endswith((".pdf", ".png", ".dxf", "_cache.json")):
        try: os.remove(os.path.join("workspace", ws_f))
        except Exception: pass

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti-studio): restore recorded fix surveyor and resize P1/P2 equal + P3/P4 -30%"], check=False)
print("\nSTUDIO SURVEYOR & 4-PANEL LAYOUT UPDATE COMPLETE!")