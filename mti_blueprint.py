import io
import json
import math
import copy
from datetime import datetime, date
import pandas as pd
from flask import Blueprint, render_template_string, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user

mti_bp = Blueprint('mti_bp', __name__, url_prefix='/mti')

import zlib, base64
MATTRESS_B64 = "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"
MATTRESS_CATALOG = [
    {"layer": r[0], "name": r[1], "design_e": r[2], "design_n": r[3], "bearing": r[4], "length": 6.0, "width": 3.0}
    for r in json.loads(zlib.decompress(base64.b64decode(MATTRESS_B64)).decode("utf-8"))
]

def compute_4_corners(center_e, center_n, bearing_deg, length_m=6.0, width_m=3.0):
    """Calculates 4 corner coordinates (C1..C4) in the background (saved in DB/Excel, hidden from UI)."""
    rad = math.radians(float(bearing_deg or 0.0))
    sin_b, cos_b = math.sin(rad), math.cos(rad)
    dl, dw = length_m / 2.0, width_m / 2.0
    signs = [(+1, -1), (+1, +1), (-1, +1), (-1, -1)]
    corners = {}
    for idx, (sl, sw) in enumerate(signs, start=1):
        corners[f"c{idx}_e"] = round(center_e + sl * dl * sin_b + sw * dw * cos_b, 3)
        corners[f"c{idx}_n"] = round(center_n + sl * dl * cos_b - sw * dw * sin_b, 3)
    return corners

DEFAULT_MTI_STATE = {
    "campaign_target_mattresses": 139,
    "campaign_target_rockbags": 28,
    "cl_tolerance_m": 0.50,
    "gap_tolerance_m": 0.20,
    "ledger": [
        {
            "id": 1, "unit_no": 1, "is_first_in_array": True, "unit_type": "Concrete Mattress",
            "crossing_id": "CR-A1_L1", "design_box_id": "CR-A1_M15", "physical_tag": "#A046",
            "install_date": "2026-11-04", "shift": "Abror (Day) / Roderick (Night)",
            "design_e": 194541.443, "design_n": 2702613.394, "aslaid_e": 194541.520, "aslaid_n": 2702613.300,
            "cl_offset_m": 0.12, "heading_deg": 15.854, "gap1_m": 0.00, "gap2_m": 0.00, "gap_m": 0.00,
            "status": "Completed",
            "remarks": "First mattress in array (04-Nov 16:00, CR-A1_M15, Tag #A046); Center & Bearing verified.",
            **compute_4_corners(194541.520, 2702613.300, 15.854)
        },
        {
            "id": 2, "unit_no": 2, "is_first_in_array": False, "unit_type": "Concrete Mattress",
            "crossing_id": "CR-A1_L1", "design_box_id": "CR-A1_M16", "physical_tag": "#A007",
            "install_date": "2026-11-05", "shift": "Abror (Day) / Roderick (Night)",
            "design_e": 194544.329, "design_n": 2702612.575, "aslaid_e": 194544.450, "aslaid_n": 2702612.485,
            "cl_offset_m": 0.15, "heading_deg": 15.854, "gap1_m": 0.02, "gap2_m": 0.10, "gap_m": 0.10,
            "status": "Completed",
            "remarks": "Installed 05-Nov 04:40 (CR-A1_M16, Tag #A007); Gap 1 (N) = 0.02m, Gap 2 (S) = 0.10m; 4 corners calculated.",
            **compute_4_corners(194544.450, 2702612.485, 15.854)
        },
        {
            "id": 3, "unit_no": 3, "is_first_in_array": False, "unit_type": "Concrete Mattress",
            "crossing_id": "CR-A1_L1", "design_box_id": "CR-A1_M17", "physical_tag": "Pending",
            "install_date": "2026-11-05", "shift": "Abror (Day) / Roderick (Night)",
            "design_e": 194547.215, "design_n": 2702611.755, "aslaid_e": 194547.360, "aslaid_n": 2702611.650,
            "cl_offset_m": 0.18, "heading_deg": 15.854, "gap1_m": 0.12, "gap2_m": 0.22, "gap_m": 0.22,
            "status": "In Progress",
            "remarks": "Placed on seabed by 19:00 (center delta 0.18m); pending WROV seating adjustment to close >0.20m West edge gap.",
            **compute_4_corners(194547.360, 2702611.650, 15.854)
        }
    ],
    "time_logs": [
        {
            "id": 1, "log_date": "2026-11-04", "surveyors": "Abror (07-19), Roderick (19-07)",
            "hrs_positioning": 6.5, "hrs_survey_troubleshooting": 4.0, "hrs_rov_recovery": 3.5, "hrs_deck_dp": 6.0, "hrs_standby": 4.0,
            "notes": "Completed Mattress #1 (CR-A1_M15, #A046) at 16:00; resolved USBL beacon telemetry and WROV tether check."
        },
        {
            "id": 2, "log_date": "2026-11-05", "surveyors": "Abror (07-19), Roderick (19-07)",
            "hrs_positioning": 8.0, "hrs_survey_troubleshooting": 3.0, "hrs_rov_recovery": 4.5, "hrs_deck_dp": 5.5, "hrs_standby": 3.0,
            "notes": "Completed Mattress #2 (CR-A1_M16, #A007) at 04:40 (Gaps: 0.02m & 0.10m); Mattress #3 (CR-A1_M17) on seabed at 19:00."
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
    st = schema["mti_state"]
    if st.get("campaign_target_mattresses") != 139 or any("gap1_m" not in r for r in st.get("ledger", [])):
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
                        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
                            <h6 class="fw-bold text-primary mb-0">Onboard Surveyor Mattress Placement Input Form (4 Corners Auto-Calculated in Background)</h6>
                            <div class="d-flex align-items-center gap-2">
                                <label class="small fw-bold text-success mb-0">Auto-Fill from 139 CAD Design Mattresses:</label>
                                <select id="designCatalogSelect" class="form-select form-select-sm border-success fw-bold" style="width: 280px;" onchange="onSelectDesignMattress()">
                                    <option value="">-- Choose Design Mattress (139) --</option>
                                </select>
                            </div>
                        </div>
                        <div class="row g-2 mb-2 align-items-end">
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Unit #</label>
                                <input type="number" name="unit_no" id="inpUnitNo" class="form-control form-control-sm fw-bold" value="{{ ledger|length + 1 }}" min="1" max="300" oninput="toggleGapInputs()" required>
                            </div>
                            <div class="col-md-3">
                                <div class="form-check form-switch pb-1">
                                    <input class="form-check-input" type="checkbox" id="chkFirstMattress" name="is_first_in_array" value="true" onchange="toggleGapInputs()">
                                    <label class="form-check-label small fw-bold text-primary" for="chkFirstMattress">1st Mattress in Array (No Gaps)</label>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small fw-bold mb-1">Crossing / DXF Layer</label>
                                <input type="text" name="crossing_id" class="form-control form-control-sm" value="CR-A1_L1" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Design Box ID</label>
                                <input type="text" name="design_box_id" class="form-control form-control-sm" value="CR-A1_M{{ ledger|length + 1 }}" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Physical Tag</label>
                                <input type="text" name="physical_tag" class="form-control form-control-sm" placeholder="e.g., #A046" required>
                            </div>
                        </div>
                        <div class="row g-2 mb-2">
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Date</label>
                                <input type="date" name="install_date" value="{{ today_str }}" class="form-control form-control-sm" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Design Center E</label>
                                <input type="number" step="0.001" name="design_e" id="inpDesE" class="form-control form-control-sm" placeholder="194541.443" oninput="calcOffset()" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Design Center N</label>
                                <input type="number" step="0.001" name="design_n" id="inpDesN" class="form-control form-control-sm" placeholder="2702613.394" oninput="calcOffset()" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1 text-primary">As-Laid Center E *</label>
                                <input type="number" step="0.001" name="aslaid_e" id="inpAsE" class="form-control form-control-sm border-primary fw-bold" placeholder="194541.520" oninput="calcOffset()" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1 text-primary">As-Laid Center N *</label>
                                <input type="number" step="0.001" name="aslaid_n" id="inpAsN" class="form-control form-control-sm border-primary fw-bold" placeholder="2702613.300" oninput="calcOffset()" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">CL Offset (m)</label>
                                <input type="number" step="0.01" name="cl_offset_m" id="inpClOff" class="form-control form-control-sm fw-bold bg-white" placeholder="Auto" required>
                            </div>
                        </div>
                        <div class="row g-2 align-items-end">
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1 text-primary">As-Laid Bearing (&deg;) *</label>
                                <input type="number" step="0.001" name="heading_deg" class="form-control form-control-sm border-primary fw-bold" value="15.854" required>
                            </div>
                            <div class="col-md-2" id="gap1Container">
                                <label class="form-label small fw-bold mb-1 text-success">Adj. Gap 1 (m) *</label>
                                <input type="number" step="0.01" name="gap1_m" id="inpGap1" class="form-control form-control-sm border-success fw-bold" value="0.05">
                            </div>
                            <div class="col-md-2" id="gap2Container">
                                <label class="form-label small fw-bold mb-1 text-success">Adj. Gap 2 (m) *</label>
                                <input type="number" step="0.01" name="gap2_m" id="inpGap2" class="form-control form-control-sm border-success fw-bold" value="0.10">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Status</label>
                                <select name="status" class="form-select form-select-sm fw-bold">
                                    <option value="Completed">Completed</option>
                                    <option value="In Progress">In Progress</option>
                                    <option value="Planned">Planned</option>
                                </select>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Remarks</label>
                                <input type="text" name="remarks" class="form-control form-control-sm" placeholder="Notes..." required>
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
                                <th>Bearing (&deg;)</th>
                                <th>Adj. Gaps (1 &amp; 2)</th>
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
                                    {% if r.is_first_in_array or r.unit_no == 1 %}
                                        <span class="badge bg-light text-secondary border">1st Unit (N/A)</span>
                                    {% else %}
                                        <span class="{{ 'pass-pill' if gap_ok else 'fail-pill' }}" title="Max Gap: {{ '%.2f'|format(r.gap_m|float) }}m">
                                            G1: {{ "%.2f"|format(r.gap1_m|default(r.gap_m)|float) }}m | G2: {{ "%.2f"|format(r.gap2_m|default(r.gap_m)|float) }}m
                                        </span>
                                    {% endif %}
                                </td>
                                <td>
                                    <span class="badge {{ 'bg-success' if r.status == 'Completed' else ('bg-info text-dark' if r.status == 'In Progress' else 'bg-warning text-dark') }}">
                                        {{ r.status }}
                                    </span>
                                </td>
                                <td class="small text-muted" style="max-width: 220px;">{{ r.remarks }}</td>
                                <td class="text-end text-nowrap">
                                    <button type="button" class="btn btn-sm btn-outline-primary py-0 px-1 me-1" title="Edit Unit #{{ r.unit_no }}"
                                            data-unit="{{ r.unit_no }}"
                                            data-first="{{ 'true' if (r.is_first_in_array or r.unit_no == 1) else 'false' }}"
                                            data-crossing="{{ r.crossing_id }}"
                                            data-box="{{ r.design_box_id }}"
                                            data-tag="{{ r.physical_tag }}"
                                            data-date="{{ r.install_date }}"
                                            data-des-e="{{ '%.3f'|format(r.design_e|float) }}"
                                            data-des-n="{{ '%.3f'|format(r.design_n|float) }}"
                                            data-as-e="{{ '%.3f'|format(r.aslaid_e|float) }}"
                                            data-as-n="{{ '%.3f'|format(r.aslaid_n|float) }}"
                                            data-cl="{{ '%.2f'|format(r.cl_offset_m|float) }}"
                                            data-hdg="{{ '%.3f'|format(r.heading_deg|float) }}"
                                            data-gap1="{{ '%.2f'|format(r.gap1_m|default(r.gap_m)|float) }}"
                                            data-gap2="{{ '%.2f'|format(r.gap2_m|default(r.gap_m)|float) }}"
                                            data-status="{{ r.status }}"
                                            data-remarks="{{ r.remarks }}"
                                            onclick="editFixRow(this)">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <form action="/mti/delete_fix/{{ r.id }}" method="POST" style="display:inline;" onsubmit="return confirm('Delete Unit #{{ r.unit_no }} from ledger?');">
                                        <button type="submit" class="btn btn-sm btn-outline-danger py-0 px-1" title="Delete Unit #{{ r.unit_no }}"><i class="fas fa-trash"></i></button>
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
                            <div class="d-flex justify-content-between align-items-center border-top pt-2 mt-1 gap-2">
                                <div class="small text-muted">{{ tl.notes }}</div>
                                <div class="text-nowrap">
                                    <button type="button" class="btn btn-sm btn-outline-primary py-0 px-1 me-1" title="Edit {{ tl.log_date }} Shift Log"
                                            data-date="{{ tl.log_date }}"
                                            data-surv="{{ tl.surveyors }}"
                                            data-pos="{{ tl.hrs_positioning }}"
                                            data-trb="{{ tl.hrs_survey_troubleshooting }}"
                                            data-rov="{{ tl.hrs_rov_recovery }}"
                                            data-dp="{{ tl.hrs_deck_dp }}"
                                            data-stb="{{ tl.hrs_standby }}"
                                            data-notes="{{ tl.notes }}"
                                            onclick="editTimeLogRow(this)">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <form action="/mti/delete_timelog/{{ tl.id }}" method="POST" style="display:inline;" onsubmit="return confirm('Delete 24h Shift Log for {{ tl.log_date }}?');">
                                        <button type="submit" class="btn btn-sm btn-outline-danger py-0 px-1" title="Delete Shift Log"><i class="fas fa-trash"></i></button>
                                    </form>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    const DESIGN_CATALOG = {{ catalog_json | default('[]') | safe }};
    const catalogByName = {};
    document.addEventListener('DOMContentLoaded', function() {
        const sel = document.getElementById('designCatalogSelect');
        if (sel && DESIGN_CATALOG.length) {
            const groups = {};
            DESIGN_CATALOG.forEach(item => {
                catalogByName[item.name] = item;
                groups[item.layer] = groups[item.layer] || [];
                groups[item.layer].push(item);
            });
            for (const [layerName, items] of Object.entries(groups)) {
                const og = document.createElement('optgroup');
                og.label = `${layerName} (${items.length} Mattresses)`;
                items.forEach(it => {
                    og.appendChild(new Option(`${it.name} - E:${it.design_e.toFixed(2)}, N:${it.design_n.toFixed(2)}, Brg:${it.bearing.toFixed(1)} deg`, it.name));
                });
                sel.appendChild(og);
            }
        }
        toggleGapInputs();
    });

    function onSelectDesignMattress() {
        const name = document.getElementById('designCatalogSelect').value;
        const it = catalogByName[name];
        if (!it) return;
        document.querySelector('[name="crossing_id"]').value = it.layer;
        document.querySelector('[name="design_box_id"]').value = it.name;
        document.getElementById('inpDesE').value = it.design_e.toFixed(3);
        document.getElementById('inpDesN').value = it.design_n.toFixed(3);
        document.querySelector('[name="heading_deg"]').value = it.bearing.toFixed(3);
        calcOffset();
    }

    function toggleGapInputs() {
        const unitNo = parseInt(document.getElementById('inpUnitNo').value || '1', 10);
        const isFirst = document.getElementById('chkFirstMattress').checked || (unitNo === 1);
        const g1Box = document.getElementById('gap1Container');
        const g2Box = document.getElementById('gap2Container');
        const g1Inp = document.getElementById('inpGap1');
        const g2Inp = document.getElementById('inpGap2');
        if (isFirst) {
            g1Box.style.opacity = '0.35';
            g2Box.style.opacity = '0.35';
            g1Inp.value = '0.00';
            g2Inp.value = '0.00';
            g1Inp.readOnly = true;
            g2Inp.readOnly = true;
        } else {
            g1Box.style.opacity = '1';
            g2Box.style.opacity = '1';
            g1Inp.readOnly = false;
            g2Inp.readOnly = false;
        }
    }

    function editFixRow(btn) {
        const d = btn.dataset;
        const drawerEl = document.getElementById('addFixDrawer');
        if (drawerEl && !drawerEl.classList.contains('show')) {
            new bootstrap.Collapse(drawerEl, { toggle: true });
        }
        const f = drawerEl.querySelector('form');
        f.querySelector('[name="unit_no"]').value = d.unit;
        const chkFirst = document.getElementById('chkFirstMattress');
        if (chkFirst) chkFirst.checked = (d.first === 'true');
        f.querySelector('[name="crossing_id"]').value = d.crossing;
        f.querySelector('[name="design_box_id"]').value = d.box;
        f.querySelector('[name="physical_tag"]').value = d.tag;
        f.querySelector('[name="install_date"]').value = d.date;
        document.getElementById('inpDesE').value = d.desE;
        document.getElementById('inpDesN').value = d.desN;
        document.getElementById('inpAsE').value = d.asE;
        document.getElementById('inpAsN').value = d.asN;
        document.getElementById('inpClOff').value = d.cl;
        f.querySelector('[name="heading_deg"]').value = d.hdg;
        if (document.getElementById('inpGap1')) document.getElementById('inpGap1').value = d.gap1;
        if (document.getElementById('inpGap2')) document.getElementById('inpGap2').value = d.gap2;
        f.querySelector('[name="status"]').value = d.status;
        f.querySelector('[name="remarks"]').value = d.remarks;
        if (typeof toggleGapInputs === 'function') toggleGapInputs();
        drawerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function editTimeLogRow(btn) {
        const d = btn.dataset;
        const drawerEl = document.getElementById('addTimeLogDrawer');
        if (drawerEl && !drawerEl.classList.contains('show')) {
            new bootstrap.Collapse(drawerEl, { toggle: true });
        }
        const f = drawerEl.querySelector('form');
        f.querySelector('[name="log_date"]').value = d.date;
        f.querySelector('[name="surveyors"]').value = d.surv;
        f.querySelector('[name="hrs_positioning"]').value = d.pos;
        f.querySelector('[name="hrs_survey_troubleshooting"]').value = d.trb;
        f.querySelector('[name="hrs_rov_recovery"]').value = d.rov;
        f.querySelector('[name="hrs_deck_dp"]').value = d.dp;
        f.querySelector('[name="hrs_standby"]').value = d.stb;
        f.querySelector('[name="notes"]').value = d.notes;
        drawerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

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
        today_str=today_str,
        catalog_json=json.dumps(MATTRESS_CATALOG)
    )

@mti_bp.route('/add_fix', methods=['POST'])
@login_required
def add_fix():
    state = load_mti_state()
    ledger = state.get("ledger", [])
    unit_no = request.form.get("unit_no", type=int) or (len(ledger) + 1)
    is_first = (request.form.get("is_first_in_array") == "true") or (unit_no == 1)
    des_e = request.form.get("design_e", type=float) or 0.0
    des_n = request.form.get("design_n", type=float) or 0.0
    as_e = request.form.get("aslaid_e", type=float) or 0.0
    as_n = request.form.get("aslaid_n", type=float) or 0.0
    hdg = round(request.form.get("heading_deg", type=float) or 0.0, 3)
    cl_off = request.form.get("cl_offset_m", type=float)
    if cl_off is None:
        cl_off = round(math.hypot(as_e - des_e, as_n - des_n), 2)

    if is_first:
        gap1, gap2, max_gap = 0.0, 0.0, 0.0
    else:
        gap1 = round(request.form.get("gap1_m", type=float) or 0.0, 2)
        gap2 = round(request.form.get("gap2_m", type=float) or 0.0, 2)
        max_gap = round(max(gap1, gap2), 2)

    # Calculate 4 corners (6m x 3m) in the background (stored in state & Excel, not displayed on UI)
    corners = compute_4_corners(as_e, as_n, hdg, 6.0, 3.0)

    existing = next((r for r in ledger if int(r.get("unit_no", 0)) == unit_no), None)
    entry = {
        "id": existing["id"] if existing else (max([int(r.get("id", 0)) for r in ledger] + [0]) + 1),
        "unit_no": unit_no,
        "is_first_in_array": is_first,
        "unit_type": request.form.get("unit_type", "Concrete Mattress"),
        "crossing_id": (request.form.get("crossing_id") or "CR-A1_L1").strip(),
        "design_box_id": (request.form.get("design_box_id") or f"CR-A1_M{unit_no}").strip(),
        "physical_tag": (request.form.get("physical_tag") or "").strip(),
        "install_date": request.form.get("install_date") or datetime.utcnow().strftime('%Y-%m-%d'),
        "shift": "Abror & Roderick",
        "design_e": round(des_e, 3),
        "design_n": round(des_n, 3),
        "aslaid_e": round(as_e, 3),
        "aslaid_n": round(as_n, 3),
        "cl_offset_m": round(cl_off, 2),
        "heading_deg": hdg,
        "gap1_m": gap1,
        "gap2_m": gap2,
        "gap_m": max_gap,
        "status": request.form.get("status", "Completed"),
        "remarks": (request.form.get("remarks") or "").strip(),
        **corners
    }
    if existing:
        ledger.remove(existing)
    ledger.append(entry)
    state["ledger"] = ledger
    save_mti_state(state)
    flash(f"Saved Unit #{unit_no} ({entry['design_box_id']} / {entry['physical_tag']}) - 4 corners calculated in background!", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))




@mti_bp.route('/delete_timelog/<int:tlog_id>', methods=['POST'])
@login_required
def delete_timelog(tlog_id):
    state = load_mti_state()
    state["time_logs"] = [t for t in state.get("time_logs", []) if int(t.get("id", 0)) != tlog_id]
    save_mti_state(state)
    flash("Removed 24-Hour Shift Time Audit entry.", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))
