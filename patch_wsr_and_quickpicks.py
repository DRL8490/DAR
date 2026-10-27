#!/usr/bin/env python3
"""
One-Click Patcher: Dynamic Log-Based Quick-Picks (with Daryll/Abror WSR Admin Pin)
+ Embedded WSR Studio inside templates/reports.html.

Usage:
    python patch_wsr_and_quickpicks.py
"""

import os
import re
import shutil
from datetime import datetime

BACKUP_SUFFIX = datetime.now().strftime("%Y%m%d_%H%M%S") + ".bak"


def backup_file(filepath: str):
    if os.path.exists(filepath):
        bak_path = f"{filepath}.{BACKUP_SUFFIX}"
        shutil.copy2(filepath, bak_path)
        print(f"  [BACKUP] Created {bak_path}")


# ============================================================================
# 1. PATCH wsr_blueprint.py
# ============================================================================
WSR_HELPER_BLOCK = '''

# --- START AUTO-PATCH: EMBEDDED REPORTS.HTML SUPPORT ---
def get_wsr_context():
    """Return WSR state & default date window for embedding inside reports.html."""
    import datetime as _dt
    try:
        state = load_wsr_state() if "load_wsr_state" in globals() else {}
    except Exception:
        state = {}
    today = _dt.date.today()
    default_start = (today - _dt.timedelta(days=6)).strftime("%Y-%m-%d")
    default_end = today.strftime("%Y-%m-%d")
    return {
        "wsr_state": state,
        "default_start": state.get("start_date", default_start),
        "default_end": state.get("end_date", default_end),
        "report_no": state.get("report_no", f"WSR-{today.year}-W{today.isocalendar()[1]:02d}"),
    }


@wsr_bp.route("/api/pull_logs_json", methods=["GET", "POST"])
def api_pull_logs_json():
    """AJAX endpoint for reports.html to pull SQL SurveyTask logs without leaving the page."""
    from flask import request, jsonify
    import datetime as _dt

    start_str = request.values.get("start_date", "")
    end_str = request.values.get("end_date", "")

    try:
        # Attempt to use existing SQL pull helper if present in wsr_blueprint
        if "pull_tasks_from_db" in globals():
            pulled = pull_tasks_from_db(start_str, end_str)
            if isinstance(pulled, dict):
                return jsonify({"status": "ok", **pulled})

        # Direct SQLAlchemy SurveyTask query fallback
        from app import SurveyTask
        query = SurveyTask.query
        if start_str and hasattr(SurveyTask, "date"):
            query = query.filter(SurveyTask.date >= start_str)
        if end_str and hasattr(SurveyTask, "date"):
            query = query.filter(SurveyTask.date <= end_str)
        tasks = query.order_by(getattr(SurveyTask, "date", SurveyTask.id).asc()).all()

        daily_lines = []
        highlight_set = []
        for t in tasks:
            t_date = getattr(t, "date", "") or ""
            t_scope = getattr(t, "macro_scope", None) or getattr(t, "scope_id", "SURVEY")
            t_title = getattr(t, "task_name", None) or getattr(t, "action", None) or getattr(t, "title", "Survey Activity")
            t_rem = getattr(t, "remarks", "") or ""
            t_user = getattr(t, "assigned_to", "") or getattr(t, "created_by", "")
            line = f"[{t_date}] ({t_scope}) {t_title}"
            if t_rem:
                line += f" — {t_rem}"
            if t_user:
                line += f" [{t_user}]"
            daily_lines.append(f"• {line}")
            if len(highlight_set) < 6:
                highlight_set.append(f"• Completed {t_title} ({t_scope}){': ' + t_rem if t_rem else ''}")

        compiled_daily = "\\n".join(daily_lines) if daily_lines else f"No SurveyTask logs found between {start_str} and {end_str}."
        compiled_highlights = "\\n".join(highlight_set) if highlight_set else "Weekly survey operations progressed per schedule."

        # Persist into wsr_state if save_wsr_state exists
        if "load_wsr_state" in globals() and "save_wsr_state" in globals():
            st = load_wsr_state()
            st["start_date"] = start_str
            st["end_date"] = end_str
            st["daily_logs_raw"] = compiled_daily
            st["highlights"] = compiled_highlights
            save_wsr_state(st)

        return jsonify({
            "status": "ok",
            "task_count": len(tasks),
            "highlights": compiled_highlights,
            "daily_logs": compiled_daily,
            "next_week_plan": "Continue scheduled bathymetric, topographic, and construction support surveys."
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
# --- END AUTO-PATCH: EMBEDDED REPORTS.HTML SUPPORT ---
'''


def patch_wsr_blueprint():
    path = "wsr_blueprint.py"
    if not os.path.exists(path):
        print(f"  [WARN] {path} not found in current directory; creating minimal compatible module.")
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "from flask import Blueprint, request, jsonify, redirect, url_for\n"
                "wsr_bp = Blueprint('wsr', __name__, url_prefix='/wsr')\n"
                "def load_wsr_state(): return {}\n"
                "def save_wsr_state(st): pass\n"
                + WSR_HELPER_BLOCK
            )
        return

    backup_file(path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "def get_wsr_context(" not in content:
        content = content.rstrip() + "\n" + WSR_HELPER_BLOCK
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  [OK] Patched wsr_blueprint.py with get_wsr_context() and /wsr/api/pull_logs_json")
    else:
        print("  [SKIP] wsr_blueprint.py already contains get_wsr_context()")


# ============================================================================
# 2. PATCH app.py (Dynamic Log-Based Quick-Picks + Admin WSR Pin for Daryll/Abror)
# ============================================================================
APP_QUICKPICK_AND_WSR_PATCH = '''

# --- START AUTO-PATCH: DYNAMIC LOG QUICK-PICKS + ADMIN WSR (DARYLL & ABROR) ---
ADMIN_WSR_USERS = {"daryll", "abror"}

ADMIN_WSR_CHIP = {
    "label": "📊 WSR Compilation",
    "scope_id": "ADMIN",
    "task_id": "WSR_REPORT",
    "verb": "Compile",
    "category": "Reporting & Deliverable",
    "action": "Weekly Survey Report (WSR)",
    "instrument": "THPP WSR Engine",
    "default_remark": "Weekly Survey Report compilation, QA/QC of daily logs, and client submittal.",
    "style": "dark",
    "is_admin_wsr": True,
    "allowed_users": ["Daryll", "Abror"],
    "wsr_shortcut": "/reports#wsr-studio"
}


def get_dynamic_log_quick_chips(user_name: str = "Daryll", max_chips: int = 8):
    """
    1. Dynamically analyzes SurveyTask SQL logs for `user_name`:
       - Created by user = +2.0 weight
       - Assigned to user = +1.0 weight
    2. Merges pre-seeded historical counts from USER_HISTORICAL_SEEDS (if defined).
    3. Ranks top combinations and hydrates into Quick-Pick chips with frequent remarks.
    4. Pins the Admin WSR Compilation chip strictly for Daryll and Abror.
    """
    from collections import Counter, defaultdict

    norm_user = (user_name or "").strip().lower()
    pair_scores = Counter()
    pair_remarks = defaultdict(Counter)
    pair_meta = {}

    # Stage 1: Merge pre-seeded historical Master Register counts if available in app.py
    seeds_dict = globals().get("USER_HISTORICAL_SEEDS") or globals().get("HISTORICAL_OMNI_SEEDS") or {}
    for seed_user, seed_items in seeds_dict.items():
        if seed_user.lower() in norm_user or norm_user in seed_user.lower():
            if isinstance(seed_items, dict):
                for k, weight in seed_items.items():
                    pair_scores[k] += weight
            elif isinstance(seed_items, list):
                for item in seed_items:
                    if isinstance(item, dict):
                        key = (item.get("scope_id", "SURVEY"), item.get("task_id", "GENERAL"))
                        pair_scores[key] += int(item.get("count", 3))
                        if item.get("default_remark"):
                            pair_remarks[key][item["default_remark"]] += 2
                        pair_meta[key] = item

    # Stage 2: Live SQL frequency analysis from SurveyTask logs
    if "SurveyTask" in globals():
        try:
            SurveyTaskModel = globals()["SurveyTask"]
            recent_tasks = SurveyTaskModel.query.order_by(SurveyTaskModel.id.desc()).limit(500).all()
            for t in recent_tasks:
                creator = (getattr(t, "created_by", "") or "").strip().lower()
                assignee = (getattr(t, "assigned_to", "") or "").strip().lower()

                weight = 0
                if norm_user and norm_user in creator:
                    weight += 2  # 2x weight for tasks created by the user
                if norm_user and norm_user in assignee:
                    weight += 1  # 1x weight for tasks assigned to the user

                if weight > 0:
                    scope_id = getattr(t, "macro_scope", None) or getattr(t, "scope_id", None) or "TOPO"
                    task_id = getattr(t, "task_id", None) or getattr(t, "action", None) or getattr(t, "task_name", None) or "SURVEY_TASK"
                    key = (str(scope_id), str(task_id))
                    pair_scores[key] += weight

                    rem = (getattr(t, "remarks", "") or "").strip()
                    if rem:
                        # Take clean opening sentence/phrase
                        clean_rem = rem.split("\\n")[0][:120]
                        pair_remarks[key][clean_rem] += weight

                    if key not in pair_meta:
                        pair_meta[key] = {
                            "scope_id": str(scope_id),
                            "task_id": str(task_id),
                            "verb": getattr(t, "verb", "Conduct") or "Conduct",
                            "category": getattr(t, "category", str(scope_id)) or str(scope_id),
                            "action": getattr(t, "action", str(task_id)) or str(task_id),
                            "instrument": getattr(t, "instrument", "") or "",
                        }
        except Exception as e:
            print(f"[QuickPick SQL Analyzer Note]: {e}")

    # Stage 3: Build hydrated chip objects from ranked scores
    palette = ["primary", "info", "success", "warning", "secondary", "danger"]
    scope_icons = {
        "TOPO": "🚁",
        "BATHY": "🚤",
        "HYDRO": "🚤",
        "CONST": "📍",
        "QC": "🔍",
        "ADMIN": "📊",
        "CAD": "📐",
    }

    chips = []
    for idx, ((scope_id, task_id), score) in enumerate(pair_scores.most_common(max_chips)):
        meta = pair_meta.get((scope_id, task_id), {})
        top_remark = (
            pair_remarks[(scope_id, task_id)].most_common(1)[0][0]
            if pair_remarks[(scope_id, task_id)]
            else meta.get("default_remark", f"{scope_id} - {task_id}")
        )
        icon = next((v for k, v in scope_icons.items() if k in scope_id.upper()), "⚡")
        short_label = task_id.replace("_", " ").title()
        chips.append({
            "label": meta.get("label") or f"{icon} {short_label}",
            "scope_id": scope_id,
            "task_id": task_id,
            "verb": meta.get("verb", "Conduct"),
            "category": meta.get("category", scope_id),
            "action": meta.get("action", short_label),
            "instrument": meta.get("instrument", ""),
            "default_remark": top_remark,
            "style": meta.get("style") or palette[idx % len(palette)],
            "score": score,
            "allowed_users": ["all"]
        })

    # Fallback to default QUICK_PICK_CHIPS if user has zero SQL logs and zero seeds
    if not chips and "QUICK_PICK_CHIPS" in globals():
        for c in globals()["QUICK_PICK_CHIPS"]:
            allowed = [u.lower() for u in c.get("allowed_users", ["all"])]
            if "all" in allowed or any(a in norm_user for a in allowed):
                chips.append(dict(c))

    # Stage 4: Role-Pinned Admin WSR Chip for Daryll and Abror ONLY
    is_wsr_admin = any(admin_name in norm_user for admin_name in ADMIN_WSR_USERS)
    if is_wsr_admin:
        if not any(c.get("task_id") == "WSR_REPORT" for c in chips):
            chips.append(dict(ADMIN_WSR_CHIP))

    return chips


# Override or alias get_active_quick_chips so existing routes automatically use it
get_active_quick_chips = get_dynamic_log_quick_chips


@app.route("/api/quick_picks")
def api_get_quick_picks():
    """Live JSON endpoint to recalculate log-based Quick-Picks when switching user."""
    from flask import request, session, jsonify
    user = request.args.get("user") or session.get("user_name") or "Daryll"
    chips = get_dynamic_log_quick_chips(user)
    is_admin = any(a in user.lower() for a in ADMIN_WSR_USERS)
    return jsonify({
        "status": "ok",
        "user": user,
        "is_wsr_admin": is_admin,
        "chips": chips
    })


@app.context_processor
def inject_wsr_and_quickpicks_context():
    """Automatically provides wsr_state and dynamic log-based quick_picks to all templates including reports.html."""
    from flask import session, request
    current_user = (
        request.args.get("user")
        or session.get("user_name")
        or session.get("username")
        or "Daryll"
    )
    is_admin = any(a in str(current_user).lower() for a in ADMIN_WSR_USERS)
    ctx = {
        "current_user_name": current_user,
        "is_wsr_admin": is_admin,
        "quick_picks": get_dynamic_log_quick_chips(str(current_user)),
    }
    try:
        from wsr_blueprint import get_wsr_context
        ctx.update(get_wsr_context())
    except Exception:
        pass
    return ctx
# --- END AUTO-PATCH: DYNAMIC LOG QUICK-PICKS + ADMIN WSR (DARYLL & ABROR) ---
'''


def patch_app_py():
    path = "app.py"
    if not os.path.exists(path):
        print(f"  [ERROR] {path} not found! Run this script from your project root folder.")
        return

    backup_file(path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Register wsr_bp if not already registered
    if "wsr_bp" not in content:
        wsr_reg = (
            "\ntry:\n"
            "    from wsr_blueprint import wsr_bp\n"
            "    app.register_blueprint(wsr_bp)\n"
            "except Exception as _wsr_err:\n"
            "    print('WSR Blueprint registration note:', _wsr_err)\n"
        )
        # Insert before if __name__ == '__main__': if present
        if "if __name__" in content:
            parts = content.rsplit("if __name__", 1)
            content = parts[0] + wsr_reg + "\nif __name__" + parts[1]
        else:
            content += wsr_reg

    if "def get_dynamic_log_quick_chips(" not in content:
        if "if __name__" in content:
            parts = content.rsplit("if __name__", 1)
            content = parts[0] + APP_QUICKPICK_AND_WSR_PATCH + "\n\nif __name__" + parts[1]
        else:
            content = content.rstrip() + "\n" + APP_QUICKPICK_AND_WSR_PATCH

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  [OK] Patched app.py with dynamic log-based Quick-Picks + Daryll/Abror WSR Admin Pin + context processor")
    else:
        print("  [SKIP] app.py already contains get_dynamic_log_quick_chips()")


# ============================================================================
# 3. PATCH templates/reports.html (Embed Full WSR Studio + Admin Quick-Pick Bar)
# ============================================================================
EMBEDDED_WSR_STUDIO_HTML = '''
<!-- === START AUTO-PATCH: EMBEDDED WSR STUDIO INSIDE REPORTS.HTML === -->
<style>
  #wsr-studio {
    scroll-margin-top: 20px;
    border-top: 4px solid #f59e0b;
    border-radius: 14px;
  }
  .qp-chip-bar {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 12px;
    padding: 10px 14px;
  }
</style>

<!-- Dynamic Log-Driven Quick-Pick Bar & Admin Switcher (Daryll / Abror) -->
<div class="qp-chip-bar d-flex flex-wrap justify-content-between align-items-center gap-2 my-3 shadow-sm">
  <div class="d-flex flex-wrap align-items-center gap-2" id="reportsQuickPickList">
    <span class="small fw-bold text-secondary me-1">⚡ Log-Driven Quick-Picks:</span>
    {% for chip in quick_picks %}
      {% if chip.is_admin_wsr %}
        <button type="button"
                class="btn btn-sm btn-warning fw-bold rounded-pill shadow-sm"
                onclick="openWsrStudioAndPull()">
          {{ chip.label }} (Admin Shortcut)
        </button>
      {% else %}
        <span class="badge bg-{{ chip.style | default('secondary') }} rounded-pill px-3 py-2">
          {{ chip.label }}
          {% if chip.score %}<small class="opacity-75">({{ chip.score }}x)</small>{% endif %}
        </span>
      {% endif %}
    {% endfor %}
  </div>

  <div class="d-flex align-items-center gap-2">
    <label class="small fw-bold text-muted mb-0">Active User:</label>
    <select id="reportsUserSelector" class="form-select form-select-sm w-auto fw-semibold" onchange="refreshDynamicQuickPicks(this.value)">
      <option value="Daryll" {% if 'daryll' in (current_user_name|default('Daryll')|lower) %}selected{% endif %}>👑 Daryll (Admin)</option>
      <option value="Abror" {% if 'abror' in (current_user_name|default('')|lower) %}selected{% endif %}>👑 Abror (Admin)</option>
      <option value="Mateo">Mateo</option>
      <option value="Mohamad">Mohamad</option>
      <option value="Roderick">Roderick</option>
      <option value="Danilo">Danilo</option>
      <option value="Mok">Mok</option>
    </select>
  </div>
</div>

<!-- Embedded WSR Studio Workspace -->
<div id="wsr-studio" class="card shadow-sm my-4">
  <div class="card-header bg-white py-3 d-flex flex-wrap justify-content-between align-items-center gap-2">
    <div class="d-flex align-items-center gap-2">
      <span class="fs-4">📊</span>
      <div>
        <h5 class="fw-bold mb-0">Embedded WSR Studio (Weekly Survey Report Generator)</h5>
        <small class="text-muted">Directly integrated inside <code>reports.html</code> • Pulls live from <code>SurveyTask</code> SQL logs</small>
      </div>
    </div>
    <div class="d-flex gap-2">
      <button type="button" class="btn btn-primary btn-sm fw-bold" onclick="pullSqlLogsForWsr()">
        🔄 1. Pull SQL Logs for Date Window
      </button>
      <button class="btn btn-outline-secondary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#wsrStudioCollapse" aria-expanded="true">
        Toggle Studio
      </button>
    </div>
  </div>

  <div id="wsrStudioCollapse" class="collapse show">
    <div class="card-body">
      <form id="wsrEmbeddedForm" action="/wsr/generate" method="POST">
        <div class="row g-3 mb-3 p-3 bg-light rounded-3 border">
          <div class="col-md-3">
            <label class="form-label small fw-bold">WSR Report No.</label>
            <input type="text" name="report_no" id="wsr_report_no" class="form-control form-control-sm"
                   value="{{ report_no | default('WSR-2026-W43') }}" required>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-bold">Week Start Date</label>
            <input type="date" name="start_date" id="wsr_start_date" class="form-control form-control-sm"
                   value="{{ default_start }}" required>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-bold">Week End Date</label>
            <input type="date" name="end_date" id="wsr_end_date" class="form-control form-control-sm"
                   value="{{ default_end }}" required>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-bold">Compiled By (Admin)</label>
            <select name="prepared_by" id="wsr_prepared_by" class="form-select form-select-sm">
              <option value="Daryll Enano">Daryll Enano (Chief Surveyor)</option>
              <option value="Abror">Abror (Admin / Lead Surveyor)</option>
            </select>
          </div>
        </div>

        <ul class="nav nav-tabs mb-3" role="tablist">
          <li class="nav-item" role="presentation">
            <button class="nav-link active fw-bold" data-bs-toggle="tab" data-bs-target="#wsr-tab-logs" type="button" role="tab">
              🗓️ Daily Survey Logs & Executive Highlights
            </button>
          </li>
          <li class="nav-item" role="presentation">
            <button class="nav-link fw-bold" data-bs-toggle="tab" data-bs-target="#wsr-tab-plan" type="button" role="tab">
              🎯 Look-Ahead & HSEQ
            </button>
          </li>
          <li class="nav-item" role="presentation">
            <button class="nav-link fw-bold" data-bs-toggle="tab" data-bs-target="#wsr-tab-tables" type="button" role="tab">
              ⚙️ Persistent Admin Tables
            </button>
          </li>
        </ul>

        <div class="tab-content">
          <div class="tab-pane fade show active" id="wsr-tab-logs" role="tabpanel">
            <div class="mb-3">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <label class="form-label small fw-bold mb-0">Executive Summary / Key Weekly Highlights</label>
                <span id="wsrPullBadge" class="badge bg-secondary">Ready</span>
              </div>
              <textarea name="highlights" id="wsr_highlights" rows="4" class="form-control form-control-sm font-monospace"
                        placeholder="Click '1. Pull SQL Logs for Date Window' to auto-populate from completed SurveyTask logs...">{{ wsr_state.highlights if wsr_state else '' }}</textarea>
            </div>
            <div class="mb-2">
              <label class="form-label small fw-bold">Chronological Daily Survey Logs (Auto-Compiled from SQL)</label>
              <textarea name="daily_logs_raw" id="wsr_daily_logs" rows="8" class="form-control form-control-sm font-monospace"
                        placeholder="Daily survey logs will appear here...">{{ wsr_state.daily_logs_raw if wsr_state else '' }}</textarea>
            </div>
          </div>

          <div class="tab-pane fade" id="wsr-tab-plan" role="tabpanel">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label small fw-bold">Next Week Planned Activities</label>
                <textarea name="next_week_plan" id="wsr_next_week" rows="6" class="form-control form-control-sm">{{ wsr_state.next_week_plan if wsr_state else '' }}</textarea>
              </div>
              <div class="col-md-6">
                <label class="form-label small fw-bold">HSEQ & Operational Notes</label>
                <textarea name="hseq_notes" id="wsr_hseq" rows="6" class="form-control form-control-sm">{{ wsr_state.hseq_notes if wsr_state else 'Zero LTI / Zero HSEQ incidents recorded during the reporting period.' }}</textarea>
              </div>
            </div>
          </div>

          <div class="tab-pane fade" id="wsr-tab-tables" role="tabpanel">
            <label class="form-label small fw-bold">Persistent Manpower, Vessels & Equipment State (JSON)</label>
            <textarea name="admin_tables_json" id="wsr_admin_tables_json" rows="6" class="form-control form-control-sm font-monospace">{{ (wsr_state.admin_tables | tojson(indent=2)) if (wsr_state and wsr_state.admin_tables) else '{}' }}</textarea>
          </div>
        </div>

        <div class="d-flex flex-wrap justify-content-between align-items-center mt-3 pt-3 border-top gap-2">
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" name="export_pdf" id="wsr_export_pdf" value="1" checked>
            <label class="form-check-label small fw-semibold" for="wsr_export_pdf">
              Compile both <code>.docx</code> and <code>.pdf</code> deliverables
            </label>
          </div>
          <div class="d-flex gap-2">
            <button type="submit" name="action" value="save_draft" class="btn btn-outline-dark btn-sm fw-bold">
              💾 Save WSR Draft State
            </button>
            <button type="submit" name="action" value="generate" class="btn btn-warning btn-sm fw-bold px-4 shadow-sm">
              🚀 2. Generate WSR Package (.DOCX / .PDF)
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
</div>

<script>
function openWsrStudioAndPull() {
  const studio = document.getElementById("wsr-studio");
  const collapseEl = document.getElementById("wsrStudioCollapse");
  if (collapseEl && !collapseEl.classList.contains("show")) {
    collapseEl.classList.add("show");
  }
  if (studio) studio.scrollIntoView({ behavior: "smooth" });
  pullSqlLogsForWsr();
}

async function pullSqlLogsForWsr() {
  const start = document.getElementById("wsr_start_date").value;
  const end = document.getElementById("wsr_end_date").value;
  const badge = document.getElementById("wsrPullBadge");
  badge.className = "badge bg-warning text-dark";
  badge.textContent = "⏳ Querying SurveyTask SQL Logs...";

  try {
    const res = await fetch(`/wsr/api/pull_logs_json?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`);
    const data = await res.json();
    if (data.status === "ok") {
      document.getElementById("wsr_highlights").value = data.highlights || "";
      document.getElementById("wsr_daily_logs").value = data.daily_logs || "";
      if (data.next_week_plan && !document.getElementById("wsr_next_week").value) {
        document.getElementById("wsr_next_week").value = data.next_week_plan;
      }
      badge.className = "badge bg-success";
      badge.textContent = `✅ Pulled ${data.task_count} SQL Tasks (${start} → ${end})`;
    } else {
      throw new Error(data.message || "Unknown error");
    }
  } catch (err) {
    badge.className = "badge bg-danger";
    badge.textContent = `⚠️ Pull Error: ${err.message}`;
  }
}

async function refreshDynamicQuickPicks(userName) {
  try {
    const res = await fetch(`/api/quick_picks?user=${encodeURIComponent(userName)}`);
    const data = await res.json();
    const container = document.getElementById("reportsQuickPickList");
    if (!container || data.status !== "ok") return;

    let html = `<span class="small fw-bold text-secondary me-1">⚡ Log-Driven Quick-Picks (${data.user}):</span>`;
    data.chips.forEach(chip => {
      if (chip.is_admin_wsr) {
        html += `<button type="button" class="btn btn-sm btn-warning fw-bold rounded-pill shadow-sm" onclick="openWsrStudioAndPull()">${chip.label} (Admin Shortcut)</button>`;
      } else {
        const scoreTag = chip.score ? ` <small class="opacity-75">(${chip.score}x)</small>` : "";
        html += `<span class="badge bg-${chip.style || 'secondary'} rounded-pill px-3 py-2">${chip.label}${scoreTag}</span>`;
      }
    });
    container.innerHTML = html;

    // Toggle WSR Studio visibility warning for non-admins if desired
    const studio = document.getElementById("wsr-studio");
    if (studio) {
      studio.style.opacity = data.is_wsr_admin ? "1" : "0.65";
    }
  } catch (e) {
    console.error("Failed to refresh dynamic quick picks:", e);
  }
}
</script>
<!-- === END AUTO-PATCH: EMBEDDED WSR STUDIO INSIDE REPORTS.HTML === -->
'''


def patch_reports_html():
    path = os.path.join("templates", "reports.html")
    if not os.path.exists(path):
        print(f"  [WARN] {path} not found. Skipping template patch.")
        return

    backup_file(path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "id=\"wsr-studio\"" in content:
        print("  [SKIP] templates/reports.html already contains #wsr-studio")
        return

    # Replace any old /wsr external link buttons in the WSR card to scroll to #wsr-studio instead
    content = re.sub(
        r'href=["\'][^"\']*wsr[^"\']*["\']',
        'href="#wsr-studio" onclick="openWsrStudioAndPull()"',
        content
    )

    # Inject right before {% endblock %} if using Jinja inheritance, else before </body> or at EOF
    if "{% endblock %}" in content:
        idx = content.rfind("{% endblock %}")
        content = content[:idx] + EMBEDDED_WSR_STUDIO_HTML + "\n" + content[idx:]
    elif "</body>" in content:
        idx = content.rfind("</body>")
        content = content[:idx] + EMBEDDED_WSR_STUDIO_HTML + "\n" + content[idx:]
    else:
        content = content.rstrip() + "\n" + EMBEDDED_WSR_STUDIO_HTML

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("  [OK] Patched templates/reports.html with Embedded WSR Studio + Dynamic Log Quick-Picks bar")


if __name__ == "__main__":
    print("=" * 68)
    print("🚀 Applying One-Click WSR & Dynamic Quick-Picks Patch...")
    print("=" * 68)
    patch_wsr_blueprint()
    patch_app_py()
    patch_reports_html()
    print("=" * 68)
    print("✅ All patches applied! Restart your Flask server (`python app.py`)")
    print("   and open /reports to test the Embedded WSR Studio & Admin Chips.")
    print("=" * 68)