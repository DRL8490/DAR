import io
import json
import math
import copy
from datetime import datetime, date
import pandas as pd
from flask import Blueprint, render_template_string, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user

mti_bp = Blueprint('mti_bp', __name__, url_prefix='/mti')

DEFAULT_MTI_STATE = {
    "campaign_target_mattresses": 25,
    "campaign_target_rockbags": 28,
    "cl_tolerance_m": 0.50,
    "gap_tolerance_m": 0.20,
    "ledger": [
        {
            "id": 1,
            "unit_no": 1,
            "unit_type": "Concrete Mattress",
            "crossing_id": "CR-A1",
            "design_box_id": "CR-A1_M15",
            "physical_tag": "#A046",
            "install_date": "2026-11-04",
            "shift": "Abror & Roderick",
            "design_e": 0.00,
            "design_n": 0.00,
            "aslaid_e": 0.00,
            "aslaid_n": 0.00,
            "cl_offset_m": 0.12,
            "heading_deg": 284.5,
            "gap_m": 0.00,
            "status": "Completed",
            "remarks": "Installed 04-Nov at 16:00 (CR-A1_M15, Tag #A046); 6-step WROV/USBL deployment verified."
        },
        {
            "id": 2,
            "unit_no": 2,
            "unit_type": "Concrete Mattress",
            "crossing_id": "CR-A1",
            "design_box_id": "CR-A1_M16",
            "physical_tag": "#A007",
            "install_date": "2026-11-05",
            "shift": "Abror & Roderick",
            "design_e": 0.00,
            "design_n": 0.00,
            "aslaid_e": 0.00,
            "aslaid_n": 0.00,
            "cl_offset_m": 0.15,
            "heading_deg": 284.2,
            "gap_m": 0.10,
            "status": "Completed",
            "remarks": "Installed 05-Nov at 04:40 (CR-A1_M16, Tag #A007); 2cm North & 10cm South gap; 4-corner fixes completed at 05:00."
        },
        {
            "id": 3,
            "unit_no": 3,
            "unit_type": "Concrete Mattress",
            "crossing_id": "CR-A1",
            "design_box_id": "CR-A1_M17",
            "physical_tag": "Pending",
            "install_date": "2026-11-05",
            "shift": "Abror & Roderick",
            "design_e": 0.00,
            "design_n": 0.00,
            "aslaid_e": 0.00,
            "aslaid_n": 0.00,
            "cl_offset_m": 0.18,
            "heading_deg": 284.8,
            "gap_m": 0.22,
            "status": "In Progress",
            "remarks": "Placed on seabed by 19:00 (center delta 0.18m); pending seating adjustment to close >20cm West edge gap."
        }
    ],
    "time_logs": [
        {
            "id": 1,
            "log_date": "2026-11-04",
            "surveyors": "Abror, Roderick",
            "hrs_positioning": 6.5,
            "hrs_survey_troubleshooting": 4.0,
            "hrs_rov_recovery": 3.5,
            "hrs_deck_dp": 6.0,
            "hrs_standby": 4.0,
            "notes": "Completed Mattress #1 (CR-A1_M15, #A046) at 16:00; resolved USBL beacon telemetry and WROV tether check."
        },
        {
            "id": 2,
            "log_date": "2026-11-05",
            "surveyors": "Abror, Roderick",
            "hrs_positioning": 8.0,
            "hrs_survey_troubleshooting": 3.0,
            "hrs_rov_recovery": 4.5,
            "hrs_deck_dp": 5.5,
            "hrs_standby": 3.0,
            "notes": "Completed Mattress #2 (CR-A1_M16, #A007) at 04:40 (4-corner fix 05:00); Mattress #3 placed at 19:00 (0.18m delta, closing >20cm West gap)."
        }
    ]
}

def load_mti_state():
    from app import AppConfig, db
    config = AppConfig.query.first()
    if not config:
        schema = {"mti_state": copy.deepcopy(DEFAULT_MTI_STATE)}
        config = AppConfig(schema_data=json.dumps(schema))
        db.session.add(config)
        db.session.commit()
        return copy.deepcopy(DEFAULT_MTI_STATE)
    try:
        schema = json.loads(config.schema_data) if config.schema_data else {}
    except Exception:
        schema = {}
    if "mti_state" not in schema or not isinstance(schema["mti_state"], dict):
        schema["mti_state"] = copy.deepcopy(DEFAULT_MTI_STATE)
        config.schema_data = json.dumps(schema)
        db.session.commit()
    st = schema["mti_state"]
    if st.get("campaign_target_mattresses") == 141 and any(r.get("design_box_id") == "MB-001" for r in st.get("ledger", [])):
        schema["mti_state"] = copy.deepcopy(DEFAULT_MTI_STATE)
        config.schema_data = json.dumps(schema)
        db.session.commit()
    return schema["mti_state"]

def save_mti_state(mti_state):
    from app import AppConfig, db
    config = AppConfig.query.first()
    try:
        schema = json.loads(config.schema_data) if (config and config.schema_data) else {}
    except Exception:
        schema = {}
    schema["mti_state"] = mti_state
    if not config:
        config = AppConfig(schema_data=json.dumps(schema))
        db.session.add(config)
    else:
        config.schema_data = json.dumps(schema)
    db.session.commit()

@mti_bp.route('/', methods=['GET'])
@login_required
def mti_dashboard():
    state = load_mti_state()
    ledger = sorted(state.get("ledger", []), key=lambda x: int(x.get("unit_no", 999)))
    time_logs = sorted(state.get("time_logs", []), key=lambda x: x.get("log_date", ""), reverse=True)

    target_matt = int(state.get("campaign_target_mattresses", 141))
    target_rb = int(state.get("campaign_target_rockbags", 28))
    cl_tol = float(state.get("cl_tolerance_m", 0.50))
    gap_tol = float(state.get("gap_tolerance_m", 0.20))

    completed_matt = sum(1 for r in ledger if r.get("status") == "Completed" and r.get("unit_type") == "Concrete Mattress")
    completed_rb = sum(1 for r in ledger if r.get("status") == "Completed" and r.get("unit_type") == "Rock Bag")
    in_prog_cnt = sum(1 for r in ledger if r.get("status") == "In Progress")
    tol_pass_cnt = sum(
        1 for r in ledger
        if r.get("status") == "Completed"
        and float(r.get("cl_offset_m", 0)) <= cl_tol
        and float(r.get("gap_m", 0)) <= gap_tol
    )

    pct_matt = round((completed_matt / target_matt) * 100, 1) if target_matt else 0.0
    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MMA Prestige MTI Tracker - NMDC</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #f0f4f8; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .hero-banner { background: linear-gradient(90deg, #0b2e4c 0%, #0f4c75 100%); color: white; border-radius: 12px; padding: 18px 24px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
        .kpi-card { background: white; border-radius: 10px; padding: 15px 18px; border: none; box-shadow: 0 2px 6px rgba(0,0,0,0.06); height: 100%; }
        .pass-pill { background: #dcfce7; color: #166534; border: 1px solid #86efac; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 11.5px; }
        .fail-pill { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 11.5px; }
        .mono { font-family: monospace; font-size: 12.5px; }
    </style>
</head>
<body>
<div class="container-fluid" style="max-width: 1440px;">
    <div class="hero-banner d-flex justify-content-between align-items-center flex-wrap gap-3">
        <div>
            <div style="font-size: 11px; font-weight: 800; color: #7dd3fc; text-transform: uppercase; letter-spacing: 0.8px;">
                DP2 MMA PRESTIGE • TUNG-HSIAO 2ND STAGE SUBSEA GAS PIPELINE PROJECT
            </div>
            <h3 class="fw-bold mb-1">🧱 Subsea Mattress &amp; Rock Bag Installation (MTI) Operations Auditor</h3>
            <div style="font-size: 13px; color: #e2e8f0;">
                6-Step WROV/USBL Deployment Ledger • Tolerances: Centerline Offset &le; &plusmn;{{ "%.2f"|format(cl_tol) }} m | Inter-Mattress Gap &le; {{ "%.2f"|format(gap_tol) }} m
            </div>
        </div>
        <div class="d-flex gap-2 flex-wrap">
            <a href="/mti/export_excel" class="btn btn-success fw-bold"><i class="fas fa-file-excel me-1"></i> Export MTI Ledger (.xlsx)</a>
            <a href="/reports" class="btn btn-info fw-bold text-dark"><i class="fas fa-chart-pie me-1"></i> Reports Hub</a>
            <a href="/admin_dashboard" class="btn btn-outline-light fw-bold"><i class="fas fa-arrow-left me-1"></i> Admin Dashboard</a>
        </div>
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show shadow-sm">
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <!-- CAMPAIGN KPI CARDS -->
    <div class="row g-3 mb-4">
        <div class="col-md-3">
            <div class="kpi-card border-start border-4 border-primary">
                <div class="text-muted small fw-bold text-uppercase">Concrete Mattresses Laid</div>
                <div class="d-flex justify-content-between align-items-baseline mt-1">
                    <h3 class="fw-bold text-primary mb-0">{{ completed_matt }} / {{ target_matt }}</h3>
                    <span class="badge bg-primary">{{ pct_matt }}%</span>
                </div>
                <div class="progress mt-2" style="height: 7px;">
                    <div class="progress-bar bg-primary" style="width: {{ pct_matt }}%;"></div>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-1">
                    <small class="text-muted">{{ target_matt - completed_matt }} remaining</small>
                    <form action="/mti/update_targets" method="POST" class="d-inline-flex align-items-center gap-1">
                        <input type="number" name="target_matt" value="{{ target_matt }}" min="1" max="500" class="form-control form-control-sm py-0 px-1 text-center fw-bold" style="width: 58px; height: 22px; font-size: 11px;" title="Target Mattresses">
                        <button type="submit" class="btn btn-sm btn-outline-primary py-0 px-1" style="font-size: 10px; height: 22px;">Set Target</button>
                    </form>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="kpi-card border-start border-4 border-info">
                <div class="text-muted small fw-bold text-uppercase">Active / Ongoing Deployment</div>
                <h3 class="fw-bold text-info mt-1 mb-0">{{ in_prog_cnt }} Unit(s)</h3>
                <small class="text-muted d-block mt-2">Rock Bags Scope: {{ completed_rb }} / {{ target_rb }} laid (Dec 2026)</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="kpi-card border-start border-4 border-success">
                <div class="text-muted small fw-bold text-uppercase">QA/QC Tolerance Compliance</div>
                <h3 class="fw-bold text-success mt-1 mb-0">{{ tol_pass_cnt }} / {{ completed_matt + completed_rb }} Verified</h3>
                <small class="text-muted d-block mt-2">&plusmn;{{ "%.2f"|format(cl_tol) }}m CL &amp; &le;{{ "%.2f"|format(gap_tol) }}m Gap Checks</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="kpi-card border-start border-4 border-warning">
                <div class="text-muted small fw-bold text-uppercase">1-Click DPR Board Sync</div>
                <form action="/mti/sync_to_dpr" method="POST" class="mt-2 d-flex gap-2">
                    <input type="date" name="sync_date" value="{{ today_str }}" class="form-control form-control-sm" required>
                    <button type="submit" class="btn btn-sm btn-warning fw-bold text-nowrap">⚡ Sync to DPR</button>
                </form>
                <small class="text-muted d-block mt-1">Logs daily MTI progress directly into SurveyTask</small>
            </div>
        </div>
    </div>

    <div class="row g-4">
        <!-- LEFT / MAIN: SUBSEA MATTRESS & ROCK BAG FIX LEDGER -->
        <div class="col-lg-8">
            <div class="card shadow-sm border-0 mb-4" style="border-radius: 12px;">
                <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center py-3" style="border-radius: 12px 12px 0 0;">
                    <span class="fw-bold"><i class="fas fa-th-list text-info me-1"></i> Cumulative Subsea Mattress &amp; Rock Bag Fix Ledger ({{ ledger|length }} Logged)</span>
                    <button class="btn btn-sm btn-success fw-bold" data-bs-toggle="collapse" data-bs-target="#addFixDrawer">
                        <i class="fas fa-plus"></i> + Log New Mattress / Rock Bag Fix
                    </button>
                </div>

                <!-- COLLAPSIBLE ADD / UPDATE FIX FORM -->
                <div class="collapse border-bottom bg-light p-3" id="addFixDrawer">
                    <form action="/mti/add_fix" method="POST">
                        <h6 class="fw-bold text-primary mb-2">Log or Update Subsea Unit Placement Fix (TWD97 TM2)</h6>
                        <div class="row g-2 mb-2">
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Unit #</label>
                                <input type="number" name="unit_no" class="form-control form-control-sm fw-bold" value="{{ ledger|length + 1 }}" min="1" max="300" required>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small fw-bold mb-1">Unit Type</label>
                                <select name="unit_type" class="form-select form-select-sm">
                                    <option value="Concrete Mattress">Concrete Mattress</option>
                                    <option value="Rock Bag">Rock Bag</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small fw-bold mb-1">Crossing / Zone ID</label>
                                <input type="text" name="crossing_id" class="form-control form-control-sm" value="Crossing A1" placeholder="e.g., Crossing A1, FEM-1" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Design Box ID</label>
                                <input type="text" name="design_box_id" class="form-control form-control-sm" value="MB-{{ '%03d'|format(ledger|length + 1) }}" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Physical Tag</label>
                                <input type="text" name="physical_tag" class="form-control form-control-sm" placeholder="e.g., A040-04" required>
                            </div>
                        </div>
                        <div class="row g-2 mb-2">
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Date</label>
                                <input type="date" name="install_date" value="{{ today_str }}" class="form-control form-control-sm" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Design Easting</label>
                                <input type="number" step="0.01" name="design_e" id="inpDesE" class="form-control form-control-sm" placeholder="198444.35" oninput="calcOffset()" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Design Northing</label>
                                <input type="number" step="0.01" name="design_n" id="inpDesN" class="form-control form-control-sm" placeholder="2681121.90" oninput="calcOffset()" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">As-Laid Easting</label>
                                <input type="number" step="0.01" name="aslaid_e" id="inpAsE" class="form-control form-control-sm" placeholder="198444.50" oninput="calcOffset()" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">As-Laid Northing</label>
                                <input type="number" step="0.01" name="aslaid_n" id="inpAsN" class="form-control form-control-sm" placeholder="2681121.82" oninput="calcOffset()" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">CL Offset (m)</label>
                                <input type="number" step="0.01" name="cl_offset_m" id="inpClOff" class="form-control form-control-sm fw-bold" placeholder="Auto" required>
                            </div>
                        </div>
                        <div class="row g-2 align-items-end">
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Heading (&deg;T)</label>
                                <input type="number" step="0.1" name="heading_deg" class="form-control form-control-sm" value="284.5" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Gap (m)</label>
                                <input type="number" step="0.01" name="gap_m" class="form-control form-control-sm" value="0.15" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Status</label>
                                <select name="status" class="form-select form-select-sm fw-bold">
                                    <option value="Completed">Completed</option>
                                    <option value="In Progress">In Progress</option>
                                    <option value="Planned">Planned</option>
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold mb-1">Surveyor Verification Remarks</label>
                                <input type="text" name="remarks" class="form-control form-control-sm" placeholder="6-step touchdown & acoustic release verified..." required>
                            </div>
                            <div class="col-md-2">
                                <button type="submit" class="btn btn-sm btn-primary fw-bold w-100"><i class="fas fa-save"></i> Save Fix</button>
                            </div>
                        </div>
                    </form>
                </div>

                <div class="table-responsive">
                    <table class="table table-hover table-striped align-middle mb-0" style="font-size: 12.5px;">
                        <thead class="table-secondary">
                            <tr>
                                <th>#</th>
                                <th>Date</th>
                                <th>Crossing / Box / Tag</th>
                                <th>As-Laid Center (E, N)</th>
                                <th>CL Offset</th>
                                <th>Hdg (&deg;)</th>
                                <th>Gap</th>
                                <th>Status</th>
                                <th>Remarks</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                        {% for r in ledger %}
                            {% set cl_ok = (r.cl_offset_m|float <= cl_tol) %}
                            {% set gap_ok = (r.gap_m|float <= gap_tol) %}
                            <tr>
                                <td class="fw-bold">#{{ r.unit_no }}</td>
                                <td class="text-nowrap">{{ r.install_date }}</td>
                                <td>
                                    <strong>{{ r.crossing_id }}</strong><br>
                                    <span class="badge bg-secondary">{{ r.design_box_id }}</span>
                                    <span class="badge bg-info text-dark">{{ r.physical_tag }}</span>
                                </td>
                                <td class="mono">
                                    E: {{ "%.2f"|format(r.aslaid_e|float) }}<br>
                                    N: {{ "%.2f"|format(r.aslaid_n|float) }}
                                </td>
                                <td>
                                    <span class="{{ 'pass-pill' if cl_ok else 'fail-pill' }}">
                                        {{ "%.2f"|format(r.cl_offset_m|float) }} m
                                    </span>
                                </td>
                                <td class="fw-semibold">{{ "%.1f"|format(r.heading_deg|float) }}&deg;</td>
                                <td>
                                    <span class="{{ 'pass-pill' if gap_ok else 'fail-pill' }}">
                                        {{ "%.2f"|format(r.gap_m|float) }} m
                                    </span>
                                </td>
                                <td>
                                    <span class="badge {{ 'bg-success' if r.status == 'Completed' else ('bg-info text-dark' if r.status == 'In Progress' else 'bg-warning text-dark') }}">
                                        {{ r.status }}
                                    </span>
                                </td>
                                <td class="small text-muted" style="max-width: 220px;">{{ r.remarks }}</td>
                                <td class="text-end">
                                    <form action="/mti/delete_fix/{{ r.id }}" method="POST" style="display:inline;" onsubmit="return confirm('Delete Unit #{{ r.unit_no }} from ledger?');">
                                        <button type="submit" class="btn btn-sm btn-outline-danger py-0 px-1"><i class="fas fa-trash"></i></button>
                                    </form>
                                </td>
                            </tr>
                        {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- RIGHT: 24-HOUR SHIFT TIME AUDIT BUCKETS -->
        <div class="col-lg-4">
            <div class="card shadow-sm border-0 mb-4" style="border-radius: 12px;">
                <div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center py-3" style="border-radius: 12px 12px 0 0;">
                    <span class="fw-bold"><i class="fas fa-clock text-warning me-1"></i> 24-Hour Shift Time Audit Log</span>
                    <button class="btn btn-sm btn-warning fw-bold text-dark" data-bs-toggle="collapse" data-bs-target="#addTimeLogDrawer">
                        + Log 24h Shift
                    </button>
                </div>

                <div class="collapse border-bottom bg-light p-3" id="addTimeLogDrawer">
                    <form action="/mti/add_timelog" method="POST">
                        <div class="row g-2 mb-2">
                            <div class="col-6">
                                <label class="form-label small fw-bold mb-1">Log Date</label>
                                <input type="date" name="log_date" value="{{ today_str }}" class="form-control form-control-sm" required>
                            </div>
                            <div class="col-6">
                                <label class="form-label small fw-bold mb-1">Shift Surveyors</label>
                                <input type="text" name="surveyors" value="Abror, Roderick" class="form-control form-control-sm" required>
                            </div>
                        </div>
                        <div class="row g-2 mb-2">
                            <div class="col-6">
                                <label class="form-label small fw-bold mb-1">1. Mattress Positioning (h)</label>
                                <input type="number" step="0.5" name="hrs_positioning" value="8.0" class="form-control form-control-sm" required>
                            </div>
                            <div class="col-6">
                                <label class="form-label small fw-bold mb-1">2. Survey Calib/Trouble (h)</label>
                                <input type="number" step="0.5" name="hrs_survey_troubleshooting" value="2.0" class="form-control form-control-sm" required>
                            </div>
                            <div class="col-6">
                                <label class="form-label small fw-bold mb-1">3. ROV Breakdown/Rec (h)</label>
                                <input type="number" step="0.5" name="hrs_rov_recovery" value="2.0" class="form-control form-control-sm" required>
                            </div>
                            <div class="col-6">
                                <label class="form-label small fw-bold mb-1">4. Deck Rigging / DP (h)</label>
                                <input type="number" step="0.5" name="hrs_deck_dp" value="8.0" class="form-control form-control-sm" required>
                            </div>
                            <div class="col-12">
                                <label class="form-label small fw-bold mb-1">5. Weather / Tide / Client Standby (h)</label>
                                <input type="number" step="0.5" name="hrs_standby" value="4.0" class="form-control form-control-sm" required>
                            </div>
                        </div>
                        <div class="mb-2">
                            <label class="form-label small fw-bold mb-1">24-Hour Operational Shift Summary</label>
                            <textarea name="notes" rows="2" class="form-control form-control-sm" placeholder="Summary of mattresses laid, USBL/ROV events..." required></textarea>
                        </div>
                        <button type="submit" class="btn btn-sm btn-dark fw-bold w-100">Save 24-Hour Time Audit</button>
                    </form>
                </div>

                <div class="card-body p-3">
                    {% for tl in time_logs %}
                        {% set total_h = (tl.hrs_positioning|float) + (tl.hrs_survey_troubleshooting|float) + (tl.hrs_rov_recovery|float) + (tl.hrs_deck_dp|float) + (tl.hrs_standby|float) %}
                        <div class="p-3 mb-3 bg-light border rounded">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <strong class="text-primary">📅 {{ tl.log_date }} ({{ tl.surveyors }})</strong>
                                <span class="badge {{ 'bg-success' if total_h == 24.0 else 'bg-warning text-dark' }}">{{ "%.1f"|format(total_h) }} / 24.0 hrs</span>
                            </div>
                            <div class="row g-1 small mb-2">
                                <div class="col-6">🎯 Positioning: <strong>{{ tl.hrs_positioning }}h</strong></div>
                                <div class="col-6">🛰️ Survey Trouble: <strong>{{ tl.hrs_survey_troubleshooting }}h</strong></div>
                                <div class="col-6">🤖 ROV Recovery: <strong>{{ tl.hrs_rov_recovery }}h</strong></div>
                                <div class="col-6">⚓ Deck/DP Setup: <strong>{{ tl.hrs_deck_dp }}h</strong></div>
                                <div class="col-12">⏳ Standby/Weather: <strong>{{ tl.hrs_standby }}h</strong></div>
                            </div>
                            <div class="small text-muted border-top pt-1">{{ tl.notes }}</div>
                        </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    function calcOffset() {
        const de = parseFloat(document.getElementById('inpDesE').value);
        const dn = parseFloat(document.getElementById('inpDesN').value);
        const ae = parseFloat(document.getElementById('inpAsE').value);
        const an = parseFloat(document.getElementById('inpAsN').value);
        if (!isNaN(de) && !isNaN(dn) && !isNaN(ae) && !isNaN(an)) {
            const dist = Math.hypot(ae - de, an - dn);
            document.getElementById('inpClOff').value = dist.toFixed(2);
        }
    }
</script>
</body>
</html>"""
    return render_template_string(
        html,
        ledger=ledger,
        time_logs=time_logs,
        target_matt=target_matt,
        target_rb=target_rb,
        cl_tol=cl_tol,
        gap_tol=gap_tol,
        completed_matt=completed_matt,
        completed_rb=completed_rb,
        in_prog_cnt=in_prog_cnt,
        tol_pass_cnt=tol_pass_cnt,
        pct_matt=pct_matt,
        today_str=today_str
    )

@mti_bp.route('/add_fix', methods=['POST'])
@login_required
def add_fix():
    state = load_mti_state()
    ledger = state.get("ledger", [])
    unit_no = request.form.get("unit_no", type=int) or (len(ledger) + 1)
    des_e = request.form.get("design_e", type=float) or 0.0
    des_n = request.form.get("design_n", type=float) or 0.0
    as_e = request.form.get("aslaid_e", type=float) or 0.0
    as_n = request.form.get("aslaid_n", type=float) or 0.0
    cl_off = request.form.get("cl_offset_m", type=float)
    if cl_off is None:
        cl_off = round(math.hypot(as_e - des_e, as_n - des_n), 2)

    existing = next((r for r in ledger if int(r.get("unit_no", 0)) == unit_no), None)
    entry = {
        "id": existing["id"] if existing else (max([int(r.get("id", 0)) for r in ledger] + [0]) + 1),
        "unit_no": unit_no,
        "unit_type": request.form.get("unit_type", "Concrete Mattress"),
        "crossing_id": (request.form.get("crossing_id") or "Crossing A1").strip(),
        "design_box_id": (request.form.get("design_box_id") or f"MB-{unit_no:03d}").strip(),
        "physical_tag": (request.form.get("physical_tag") or "").strip(),
        "install_date": request.form.get("install_date") or datetime.utcnow().strftime('%Y-%m-%d'),
        "shift": "Abror & Roderick",
        "design_e": des_e,
        "design_n": des_n,
        "aslaid_e": as_e,
        "aslaid_n": as_n,
        "cl_offset_m": round(cl_off, 2),
        "heading_deg": round(request.form.get("heading_deg", type=float) or 0.0, 1),
        "gap_m": round(request.form.get("gap_m", type=float) or 0.0, 2),
        "status": request.form.get("status", "Completed"),
        "remarks": (request.form.get("remarks") or "").strip()
    }
    if existing:
        ledger.remove(existing)
    ledger.append(entry)
    state["ledger"] = ledger
    save_mti_state(state)
    flash(f"Saved Unit #{unit_no} ({entry['design_box_id']} / {entry['physical_tag']}) to MTI Ledger!", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/delete_fix/<int:fix_id>', methods=['POST'])
@login_required
def delete_fix(fix_id):
    state = load_mti_state()
    state["ledger"] = [r for r in state.get("ledger", []) if int(r.get("id", 0)) != fix_id]
    save_mti_state(state)
    flash("Removed entry from MTI Ledger.", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/add_timelog', methods=['POST'])
@login_required
def add_timelog():
    state = load_mti_state()
    tlogs = state.get("time_logs", [])
    log_date = request.form.get("log_date") or datetime.utcnow().strftime('%Y-%m-%d')
    existing = next((t for t in tlogs if t.get("log_date") == log_date), None)
    entry = {
        "id": existing["id"] if existing else (max([int(t.get("id", 0)) for t in tlogs] + [0]) + 1),
        "log_date": log_date,
        "surveyors": (request.form.get("surveyors") or "Abror, Roderick").strip(),
        "hrs_positioning": round(request.form.get("hrs_positioning", type=float) or 0.0, 1),
        "hrs_survey_troubleshooting": round(request.form.get("hrs_survey_troubleshooting", type=float) or 0.0, 1),
        "hrs_rov_recovery": round(request.form.get("hrs_rov_recovery", type=float) or 0.0, 1),
        "hrs_deck_dp": round(request.form.get("hrs_deck_dp", type=float) or 0.0, 1),
        "hrs_standby": round(request.form.get("hrs_standby", type=float) or 0.0, 1),
        "notes": (request.form.get("notes") or "").strip()
    }
    if existing:
        tlogs.remove(existing)
    tlogs.append(entry)
    state["time_logs"] = tlogs
    save_mti_state(state)
    flash(f"Saved 24-Hour Shift Time Audit for {log_date}!", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/sync_to_dpr', methods=['POST'])
@login_required
def sync_to_dpr():
    from app import SurveyTask, db, resequence_queue
    state = load_mti_state()
    sync_date_str = request.form.get("sync_date") or datetime.utcnow().strftime('%Y-%m-%d')
    sync_dt = datetime.strptime(sync_date_str, '%Y-%m-%d').date()

    day_fixes = [r for r in state.get("ledger", []) if r.get("install_date") == sync_date_str]
    day_tlog = next((t for t in state.get("time_logs", []) if t.get("log_date") == sync_date_str), None)

    if not day_fixes and not day_tlog:
        flash(f"No MTI fixes or time logs found for {sync_date_str} to sync.", "error")
        return redirect(url_for('mti_bp.mti_dashboard'))

    comp_units = [f"#{r['unit_no']} ({r['design_box_id']}/{r['physical_tag']}, CL={r['cl_offset_m']}m, Gap={r['gap_m']}m)" for r in day_fixes if r.get("status") == "Completed"]
    prog_units = [f"#{r['unit_no']} ({r['design_box_id']})" for r in day_fixes if r.get("status") == "In Progress"]

    opening_str = f"MMA Prestige Subsea Mattress Installation Witnessing ({sync_date_str})"
    closing_parts = []
    if comp_units:
        closing_parts.append("Completed & Verified: " + "; ".join(comp_units))
    if prog_units:
        closing_parts.append("Ongoing: " + ", ".join(prog_units))
    if day_tlog:
        closing_parts.append(
            f"24h Audit [Pos: {day_tlog['hrs_positioning']}h, Survey: {day_tlog['hrs_survey_troubleshooting']}h, "
            f"ROV: {day_tlog['hrs_rov_recovery']}h, Deck/DP: {day_tlog['hrs_deck_dp']}h, Standby: {day_tlog['hrs_standby']}h]. {day_tlog['notes']}"
        )
    full_rem = f"{opening_str} | Closed: {' | '.join(closing_parts)}"

    existing_task = SurveyTask.query.filter(
        SurveyTask.execution_date == sync_dt,
        SurveyTask.remarks.ilike(f"%{opening_str}%")
    ).first()

    if existing_task:
        existing_task.remarks = full_rem
        existing_task.status = "Closed"
    else:
        new_t = SurveyTask(
            surveyor_name=current_user.name,
            assigned_to="Daryll Enano, Mohamad Abror Hediarto, Roderick Gonzales Clavel",
            requestor="Offshore - Walaa Ezzat Gomaa",
            command_verb="VERIFY",
            task_category="Bathymetric Survey",
            action_required="Check Survey",
            instrument="USBL",
            area="300_Marine",
            location="330_Offshore",
            sub_location="338_Subsea_Crossings",
            work_scope="338-00_OS_Subsea_Crossings",
            remarks=full_rem,
            status="Closed",
            is_urgent=False,
            priority=99,
            start_time=datetime.combine(sync_dt, datetime.min.time()),
            execution_date=sync_dt,
            end_time=datetime.utcnow()
        )
        db.session.add(new_t)
    db.session.commit()
    flash(f"Synced {sync_date_str} MTI progress directly into the DPR & KPI Master Register!", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/export_excel', methods=['GET'])
@login_required
def export_excel():
    state = load_mti_state()
    df_ledger = pd.DataFrame(state.get("ledger", []))
    df_tlogs = pd.DataFrame(state.get("time_logs", []))
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_ledger.to_excel(writer, index=False, sheet_name='1_Mattress_Fix_Ledger')
        df_tlogs.to_excel(writer, index=False, sheet_name='2_24h_Time_Audit_Log')
    output.seek(0)
    return send_file(
        output,
        download_name=f"MMA_Prestige_MTI_Ledger_{datetime.utcnow().strftime('%Y%m%d')}.xlsx",
        as_attachment=True
    )

@mti_bp.route('/update_targets', methods=['POST'])
@login_required
def update_targets():
    state = load_mti_state()
    new_target = request.form.get("target_matt", type=int)
    if new_target and new_target > 0:
        state["campaign_target_mattresses"] = new_target
        save_mti_state(state)
        flash(f"Updated Mattress Target Array Total to {new_target} units!", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))
