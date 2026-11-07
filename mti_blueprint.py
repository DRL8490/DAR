import io, json, math, copy, zlib, base64
from datetime import datetime, date
import pandas as pd
from flask import Blueprint, render_template_string, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user

mti_bp = Blueprint('mti_bp', __name__, url_prefix='/mti')

MATTRESS_B64 = (
    "eNqFmT2SHTcMhO+ieM0ifgiSoeXUTpyqVL7/Ldwc9nBVqzd4ijbQpyUbTQA9+vHj21///vGn/Pe3fPvgj//gR5nerJVo/qG9amgr"
    "Ez9LbWU0//nxCtONuRTXIObFpOWYEetFZiemJfobzDfWtMyYxKRUixxrvJvjkO1guN+HJFSQ6rgOoVpGzaHOi1VcjHrILHNESg1S"
    "VurQQ0nk1CSFMsUgNYp5TympxMb6O8R6afoGo0GalH5TUXodOUV/mJY+KP319y3H7NONXQ5WzXOM/rBRWqOtxIvKG6x9mtiNmBWb"
    "bzAaxOF3pRtFS+u5Q6Qf76vckkDU9gajRxqcVW9JapmWe0RoEpMiHgerQ1JM63ky1ejIOgueQI7dXSTKFFqyDqj6BrtdMvG+aK7a"
    "8UBzl+jdRdA5qH8N/AtvKD/PpnUqguYxR15tbefZeOjBJF5g+gsWpyGYHUfO6DnVT0NQiYPJb0/7ZvRu4AMOHO1Sw9qsBabyKDri"
    "BaEkWrHdCEAobpQxRqaX/ZyBWBmWEFvugd5pfiOt+Mx+SyODu9wHw6SIhAgSuIsFETQ4zZhOBnfZHd6iVpxMvjJGxi6VVVRxHNN1"
    "NEGbx4u0+XF1j/YCUSITftONtFEELfARsQuxKriBEAkIMJ4RJ4IH20nAMJgmj0QjEZhvk4heY+sRCSLor9fEWUiFRZ+Jvgm0nHEZ"
    "WZbiRTF6H5FBBMMwGhGUI5N4EkH1hVVBV9ZM4jUGLwajL4yMosMlGouQQZ8S1gUPWzOVZZff4OVKATCeNFNZWP61SFVWxlaVEoTl"
    "18DkY2VszaVEZ6EBFO/kHE3xfhKhhQ7AOKmNxTG87FRpesAwUiurg99pqdI0ARaA1lgd3M1SpekCLGyjsjpLwkxqpQtQxcrroFCe"
    "KK30wPLKZHHQ2zxTWukBeBLzYzPY1DztGjQBrN8nXzQWLs+UVrrAZ6nO62BseKa00gXY63SyOpghnimtdEEz3IfVkdU5M6XpgtZw"
    "H7bB1UcyqWkCdMvbN2hWLVWaHoj1KlkdtMSWKW30QGB3M1an6uW7Z4YuCMdey+pgdrRMaaMLomOn2tUZmFEtU9rogsDuNZwMNMiU"
    "NrqgC+5jZLxEorTRBN1wHSWiV0J6ZmiCHrgOkVriq9LfP9eo73fMtDUAve59yNf6hlchqG3V/hrTjUFu6aSw+8JHKWWkEMCMGFZM"
    "NJUc8411OJXbqKOnRJ851ni1takIMbS5tcQmVPCMaED++cuu9SihOikEYR2kosRaKxNqkGocX4vCzzB9Rk1SA1u2HwodNoN2yoSI"
    "MGG/T7gXkhSjP/rqWvcR7dpPU4z+QHNpp2TrCUeO2XGjjfuQiGKaCyI0SKBl9vuQsGMOtU8LNz9Q7W90vP2xmgaPqGgGnrtK+qf1"
    "lUfEzHXJbSV0SNfrQ8fGsCCN3FdCi2AeDL8Pibk1ckmUHsFq2+0+5PqYkUuidw+Z6GntYGK5JKrnzfi8D7k2rFwStfNobNyHtOI9"
    "t5b6eTUa9yHZ6DKsnWcjR8mVAn6n9BfqNglWZob85ePwnmP9XG3aceSQr1W7kRMyJVbFdpiTtrIzfhHytM3xglEycO1+m2DQTq+Y"
    "9cTsmCmQIfrNzP1F5pFxMisn22bwQitq/cw0MuidomSW9zVhgsy8P9aBwYqxfPTI7KgpA92wCRlkGmz3XxgO2O8namKvKH2vwFoR"
    "6dS5YsQLRInAB1WJ6PXV5hExIg1xSYhgeerxjDgRNIYNrEQ35RloBGbpe/0FEtfLe0T2cqFIwHNvv0D8CqqPSCeyNAoiK87YMzKI"
    "xDVwN7K+UyQSTyIDd2FV1pTPJGbUVNkry2Zw/0xjRk1FClZnXVagS+7PpKmyvq6QQK/LVGbSVITgbqwMWoBnMjNq6vVZm6VZoyXT"
    "mVETf5DjWRsMCEeDemZoAfRoHyzO+jlVmh5Yw8dYnZXnUqVpAtxhDlZnBbpMApoAPVaNxUGea5nUTJqIpzgOy4M22zKpmTWRgK6d"
    "ZDN+bfXPDF2AJXJ2lmd9lc6kZtbU9S1DWR5ZaSaRmlkT4wn38c2sPJdJzayJ5R33YXlWosskoAvQL2ZndfDCA5PkmaELEINVWR4E"
    "ukilpgsQgz1YnrriTCY1bYC1pwuDIwJdZFIzbOqamsHgONfmnrRPhk3Fmqr3R7QV6DKpGTYVucKD4Xle38mfEboAA7ALU/0aPpnU"
    "zJoa65s2U/0YlxzPDF0Q6z9A+J1m7AdL5uf/A4IcXQ=="
)

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
            "install_date": "2026-11-04 16:00", "shift": "Abror (Day) / Roderick (Night)",
            "design_e": 194541.443, "design_n": 2702613.394, "aslaid_e": 194541.520, "aslaid_n": 2702613.300,
            "cl_offset_m": 0.12, "heading_deg": 15.854, "gap1_m": 0.00, "gap2_m": 0.00, "gap_m": 0.00,
            "status": "Completed",
            "remarks": "First mattress in array (04-Nov 16:00, CR-A1_M15, Tag #A046); Center & Bearing verified.",
            **compute_4_corners(194541.520, 2702613.300, 15.854)
        },
        {
            "id": 2, "unit_no": 2, "is_first_in_array": False, "unit_type": "Concrete Mattress",
            "crossing_id": "CR-A1_L1", "design_box_id": "CR-A1_M16", "physical_tag": "#A007",
            "install_date": "2026-11-05 04:40", "shift": "Abror (Day) / Roderick (Night)",
            "design_e": 194544.329, "design_n": 2702612.575, "aslaid_e": 194544.450, "aslaid_n": 2702612.485,
            "cl_offset_m": 0.15, "heading_deg": 15.854, "gap1_m": 0.02, "gap2_m": 0.10, "gap_m": 0.10,
            "status": "Completed",
            "remarks": "Installed 05-Nov 04:40 (CR-A1_M16, Tag #A007); Gap 1 (N) = 0.02m, Gap 2 (S) = 0.10m; 4 corners calculated.",
            **compute_4_corners(194544.450, 2702612.485, 15.854)
        },
        {
            "id": 3, "unit_no": 3, "is_first_in_array": False, "unit_type": "Concrete Mattress",
            "crossing_id": "CR-A1_L1", "design_box_id": "CR-A1_M17", "physical_tag": "Pending",
            "install_date": "2026-11-05 19:00", "shift": "Abror (Day) / Roderick (Night)",
            "design_e": 194547.215, "design_n": 2702611.755, "aslaid_e": 194547.360, "aslaid_n": 2702611.650,
            "cl_offset_m": 0.18, "heading_deg": 15.854, "gap1_m": 0.12, "gap2_m": 0.22, "gap_m": 0.22,
            "status": "In Progress",
            "remarks": "Placed on seabed by 19:00 (center delta 0.18m); pending WROV seating adjustment to close >0.20m West edge gap.",
            **compute_4_corners(194547.360, 2702611.650, 15.854)
        }
    ],
    "input_logs": [
        {
            "id": 1, "event_type": "Pole down", "timestamp": "2026-11-04 14:30", "surveyor": "Abror",
            "ref_id": "CR-A1_L1", "val1": "Locked & Verified", "val2": "USBL + ADCP Active",
            "remarks": "Over-the-side survey pole deployed to working depth."
        },
        {
            "id": 2, "event_type": "Mattress on water", "timestamp": "2026-11-04 15:25", "surveyor": "Abror",
            "ref_id": "CR-A1_M15 (#A046)", "val1": "Tag #A046 Overboarded", "val2": "Beacon Ch 1 & 2 OK",
            "remarks": "Mattress #1 lowered through splash zone; WROV monitoring descent."
        },
        {
            "id": 3, "event_type": "Mattress fix", "timestamp": "2026-11-04 16:00", "surveyor": "Abror",
            "ref_id": "CR-A1_M15 (#A046)", "val1": "E:194541.52, N:2702613.30", "val2": "Brg:15.9 deg | 1st Unit",
            "remarks": "Touchdown fix verified on seabed (CL Offset 0.12m)."
        },
        {
            "id": 4, "event_type": "Frame above water", "timestamp": "2026-11-04 16:20", "surveyor": "Abror",
            "ref_id": "CR-A1_M15 (#A046)", "val1": "Acoustic Release OK", "val2": "Frame on Deck",
            "remarks": "Deployment frame recovered above water and secured on deck."
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
    changed = False
    if st.get("campaign_target_mattresses") != 139:
        st["campaign_target_mattresses"] = 139
        changed = True
    if "input_logs" not in st:
        st["input_logs"] = copy.deepcopy(DEFAULT_MTI_STATE["input_logs"])
        changed = True
    if changed:
        config.schema_data = json.dumps(schema)
        db.session.commit()
    return st

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
    input_logs = sorted(state.get("input_logs", []), key=lambda x: str(x.get("timestamp", "")), reverse=True)

    target_matt = int(state.get("campaign_target_mattresses", 139))
    target_rb = int(state.get("campaign_target_rockbags", 28))
    cl_tol = float(state.get("cl_tolerance_m", 0.50))
    gap_tol = float(state.get("gap_tolerance_m", 0.20))

    completed_matt = sum(1 for r in ledger if r.get("status") == "Completed" and r.get("unit_type", "Concrete Mattress") == "Concrete Mattress")
    completed_rb = sum(1 for r in ledger if r.get("status") == "Completed" and r.get("unit_type") == "Rock Bag")
    in_prog_cnt = sum(1 for r in ledger if r.get("status") == "In Progress")
    tol_pass_cnt = sum(
        1 for r in ledger
        if r.get("status") == "Completed"
        and float(r.get("cl_offset_m", 0)) <= cl_tol
        and float(r.get("gap_m", 0)) <= gap_tol
    )

    pct_matt = round((completed_matt / target_matt) * 100, 1) if target_matt else 0.0
    now_dt_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M')
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
        .pass-pill { background: #dcfce7; color: #166534; border: 1px solid #86efac; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 11.5px; display: inline-block; white-space: nowrap; }
        .fail-pill { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 11.5px; display: inline-block; white-space: nowrap; }
        .mono { font-family: monospace; font-size: 12.5px; }
        .evt-btn { font-weight: 700; font-size: 12px; padding: 8px 10px; border-radius: 8px; text-align: left; display: flex; align-items: center; gap: 6px; transition: all 0.15s; border: 1px solid #cbd5e1; background: #ffffff; color: #1e293b; width: 100%; }
        .evt-btn:hover, .evt-btn.active { background: #0f4c75; color: #ffffff; border-color: #0f4c75; transform: translateY(-1px); box-shadow: 0 3px 8px rgba(15,76,117,0.2); }
        .evt-btn.btn-issue:hover, .evt-btn.btn-issue.active { background: #dc2626; border-color: #dc2626; color: #ffffff; }
        .evt-btn.btn-fix:hover, .evt-btn.btn-fix.active { background: #16a34a; border-color: #16a34a; color: #ffffff; }
    </style>
</head>
<body>
<div class="container-fluid" style="max-width: 1460px;">
    <div class="hero-banner d-flex justify-content-between align-items-center flex-wrap gap-3">
        <div>
            <div style="font-size: 11px; font-weight: 800; color: #7dd3fc; text-transform: uppercase; letter-spacing: 0.8px;">
                DP2 MMA PRESTIGE • TUNG-HSIAO 2ND STAGE SUBSEA GAS PIPELINE PROJECT
            </div>
            <h3 class="fw-bold mb-1">Subsea Mattress &amp; Rock Bag Installation (MTI) Operations Tracker</h3>
            <div style="font-size: 13px; color: #e2e8f0;">
                139 CAD Design Mattresses • Tolerances: Centerline Offset &le; &plusmn;{{ "%.2f"|format(cl_tol) }} m | Inter-Mattress Gap &le; {{ "%.2f"|format(gap_tol) }} m
            </div>
        </div>
        <div class="d-flex gap-2 flex-wrap">
            <a href="/mti/export_excel" class="btn btn-success fw-bold"><i class="fas fa-file-excel me-1"></i> Export MTI Ledger &amp; Logs (.xlsx)</a>
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
                        <input type="number" name="target_matt" value="{{ target_matt }}" min="1" max="500" class="form-control form-control-sm py-0 px-1 text-center fw-bold" style="width: 58px; height: 22px; font-size: 11px;">
                        <button type="submit" class="btn btn-sm btn-outline-primary py-0 px-1" style="font-size: 10px; height: 22px;">Set Target</button>
                    </form>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="kpi-card border-start border-4 border-info">
                <div class="text-muted small fw-bold text-uppercase">Active / Ongoing Deployment</div>
                <h3 class="fw-bold text-info mt-1 mb-0">{{ in_prog_cnt }} Unit(s)</h3>
                <small class="text-muted d-block mt-2">Rock Bags Scope: {{ completed_rb }} / {{ target_rb }} laid</small>
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
                    <button type="submit" class="btn btn-sm btn-warning fw-bold text-nowrap">Sync to DPR</button>
                </form>
                <small class="text-muted d-block mt-1">Logs daily MTI &amp; event inputs into SurveyTask</small>
            </div>
        </div>
    </div>

    <div class="row g-4">
        <!-- LEFT / MAIN: CUMULATIVE SUBSEA MATTRESS & ROCK BAG FIX LEDGER -->
        <div class="col-lg-7">
            <div class="card shadow-sm border-0 mb-4" style="border-radius: 12px;">
                <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center py-3" style="border-radius: 12px 12px 0 0;">
                    <span class="fw-bold"><i class="fas fa-th-list text-info me-1"></i> Cumulative Subsea Mattress &amp; Rock Bag Fix Ledger ({{ ledger|length }} Logged)</span>
                    <button class="btn btn-sm btn-success fw-bold" type="button" onclick="openMattressFixBox()">
                        <i class="fas fa-plus"></i> + Log New Mattress / Rock Bag Fix
                    </button>
                </div>

                <!-- COLLAPSIBLE MATTRESS FIX FORM (OPENED BY "+ Log New..." OR "Mattress fix" BUTTON) -->
                <div class="collapse border-bottom bg-light p-3" id="addFixDrawer">
                    <form action="/mti/add_fix" method="POST" id="mattressFixForm">
                        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
                            <h6 class="fw-bold text-success mb-0"><i class="fas fa-crosshairs me-1"></i> Mattress Fix Input Box (4 Corners Auto-Calculated in Background)</h6>
                            <div class="d-flex align-items-center gap-2">
                                <label class="small fw-bold text-success mb-0">Select Design Mattress (1 of 139):</label>
                                <select id="designCatalogSelect" class="form-select form-select-sm border-success fw-bold" style="width: 260px;" onchange="onSelectDesignMattress()">
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
                                    <label class="form-check-label small fw-bold text-primary" for="chkFirstMattress">1st Mattress (No Gaps)</label>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small fw-bold mb-1">Date/Time</label>
                                <input type="text" name="install_date" id="inpFixDateTime" value="{{ today_str }} {{ now_dt_str.split('T')[-1] }}" class="form-control form-control-sm" placeholder="YYYY-MM-DD HH:MM" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Xing / Layer</label>
                                <input type="text" name="crossing_id" class="form-control form-control-sm" value="CR-A1_L1" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Box ID</label>
                                <input type="text" name="design_box_id" class="form-control form-control-sm" value="CR-A1_M{{ ledger|length + 1 }}" required>
                            </div>
                        </div>
                        <div class="row g-2 mb-2">
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Mattress Tag ID</label>
                                <input type="text" name="physical_tag" class="form-control form-control-sm fw-bold" placeholder="e.g., #A046" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Design E</label>
                                <input type="number" step="0.001" name="design_e" id="inpDesE" class="form-control form-control-sm" placeholder="194541.443" oninput="calcOffset()" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1">Design N</label>
                                <input type="number" step="0.001" name="design_n" id="inpDesN" class="form-control form-control-sm" placeholder="2702613.394" oninput="calcOffset()" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1 text-primary">As-laid E *</label>
                                <input type="number" step="0.001" name="aslaid_e" id="inpAsE" class="form-control form-control-sm border-primary fw-bold" placeholder="194541.520" oninput="calcOffset()" required>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small fw-bold mb-1 text-primary">As-laid N *</label>
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
                                <label class="form-label small fw-bold mb-1 text-success">Gap 1 (m) *</label>
                                <input type="number" step="0.01" name="gap1_m" id="inpGap1" class="form-control form-control-sm border-success fw-bold" value="0.05">
                            </div>
                            <div class="col-md-2" id="gap2Container">
                                <label class="form-label small fw-bold mb-1 text-success">Gap 2 (m) *</label>
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
                                <button type="submit" class="btn btn-sm btn-success fw-bold w-100"><i class="fas fa-save"></i> Save Fix</button>
                            </div>
                        </div>
                    </form>
                </div>

                <!-- EXACT 6 REQUESTED COLUMNS: Date/Time | Xing/Box/ID | As-laid Center (E,N) | As-Laid Bearing | Gaps | Remarks -->
                <div class="table-responsive">
                    <table class="table table-hover table-striped align-middle mb-0" style="font-size: 12.5px;">
                        <thead class="table-secondary">
                            <tr>
                                <th>Date/Time</th>
                                <th>Xing/Box/ID</th>
                                <th>As-laid Center (E,N)</th>
                                <th>As-Laid Bearing</th>
                                <th>Gaps</th>
                                <th>Remarks</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                        {% for r in ledger %}
                            {% set cl_ok = (r.cl_offset_m|float <= cl_tol) %}
                            {% set gap_ok = (r.gap_m|float <= gap_tol) %}
                            <tr>
                                <td class="text-nowrap fw-semibold">
                                    <span class="text-muted small me-1">#{{ r.unit_no }}</span>{{ r.install_date }}
                                </td>
                                <td>
                                    <strong>{{ r.crossing_id }}</strong><br>
                                    <span class="badge bg-secondary">{{ r.design_box_id }}</span>
                                    <span class="badge bg-info text-dark">{{ r.physical_tag }}</span>
                                </td>
                                <td class="mono">
                                    E: {{ "%.2f"|format(r.aslaid_e|float) }}<br>
                                    N: {{ "%.2f"|format(r.aslaid_n|float) }}
                                    <div class="mt-1">
                                        <span class="{{ 'pass-pill' if cl_ok else 'fail-pill' }}" title="Centerline Offset">
                                            &Delta;CL: {{ "%.2f"|format(r.cl_offset_m|float) }} m
                                        </span>
                                    </div>
                                </td>
                                <td class="fw-bold">{{ "%.1f"|format(r.heading_deg|float) }}&deg;</td>
                                <td>
                                    {% if r.is_first_in_array or r.unit_no == 1 %}
                                        <span class="badge bg-light text-secondary border">1st Unit (N/A)</span>
                                    {% else %}
                                        <span class="{{ 'pass-pill' if gap_ok else 'fail-pill' }}" title="Max Gap: {{ '%.2f'|format(r.gap_m|float) }}m">
                                            G1: {{ "%.2f"|format(r.gap1_m|default(r.gap_m)|float) }}m | G2: {{ "%.2f"|format(r.gap2_m|default(r.gap_m)|float) }}m
                                        </span>
                                    {% endif %}
                                </td>
                                <td class="small text-muted" style="max-width: 240px;">
                                    <span class="badge {{ 'bg-success' if r.status == 'Completed' else ('bg-info text-dark' if r.status == 'In Progress' else 'bg-warning text-dark') }} me-1">{{ r.status }}</span>
                                    {{ r.remarks }}
                                </td>
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

        <!-- RIGHT: ONBOARD SURVEY INPUT LOG (8 QUICK-ACTION EVENT BUTTONS) -->
        <div class="col-lg-5">
            <div class="card shadow-sm border-0 mb-4" style="border-radius: 12px;">
                <div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center py-3" style="border-radius: 12px 12px 0 0;">
                    <span class="fw-bold"><i class="fas fa-keyboard text-warning me-1"></i> Onboard Survey Input Log ({{ input_logs|length }} Events)</span>
                    <span class="badge bg-dark text-warning">Click Any Button to Open Input Box</span>
                </div>

                <div class="card-body p-3">
                    <!-- 8 ACTION BUTTONS GRID -->
                    <div class="row g-2 mb-3">
                        <div class="col-6 col-md-3">
                            <button type="button" class="evt-btn" id="btnEvtPoleDown" onclick="openEventInputBox('Pole down')">
                                <i class="fas fa-arrow-down text-primary"></i> Pole down
                            </button>
                        </div>
                        <div class="col-6 col-md-3">
                            <button type="button" class="evt-btn" id="btnEvtPoleUp" onclick="openEventInputBox('Pole up')">
                                <i class="fas fa-arrow-up text-info"></i> Pole up
                            </button>
                        </div>
                        <div class="col-6 col-md-3">
                            <button type="button" class="evt-btn" id="btnEvtMattWater" onclick="openEventInputBox('Mattress on water')">
                                <i class="fas fa-water text-primary"></i> Mattress on water
                            </button>
                        </div>
                        <div class="col-6 col-md-3">
                            <button type="button" class="evt-btn btn-fix" id="btnEvtMattFix" onclick="openMattressFixBox()">
                                <i class="fas fa-crosshairs text-success"></i> Mattress fix
                            </button>
                        </div>
                        <div class="col-6 col-md-3">
                            <button type="button" class="evt-btn" id="btnEvtFrameUp" onclick="openEventInputBox('Frame above water')">
                                <i class="fas fa-anchor text-secondary"></i> Frame above water
                            </button>
                        </div>
                        <div class="col-6 col-md-3">
                            <button type="button" class="evt-btn" id="btnEvtAdcp" onclick="openEventInputBox('ADCP input')">
                                <i class="fas fa-tachometer-alt text-info"></i> ADCP input
                            </button>
                        </div>
                        <div class="col-6 col-md-3">
                            <button type="button" class="evt-btn" id="btnEvtWind" onclick="openEventInputBox('Wind Input')">
                                <i class="fas fa-wind text-warning"></i> Wind Input
                            </button>
                        </div>
                        <div class="col-6 col-md-3">
                            <button type="button" class="evt-btn btn-issue" id="btnEvtIssue" onclick="openEventInputBox('Survey Issue Reporting')">
                                <i class="fas fa-exclamation-triangle text-danger"></i> Survey Issue
                            </button>
                        </div>
                    </div>

                    <!-- DYNAMIC INPUT BOX FOR THE SELECTED EVENT BUTTON -->
                    <div id="dynamicEventBox" class="p-3 mb-3 bg-light border border-primary rounded" style="display: none;">
                        <form action="/mti/add_input_log" method="POST" id="eventInputForm">
                            <input type="hidden" name="log_id" id="evtLogId" value="">
                            <input type="hidden" name="event_type" id="evtTypeInput" value="Pole down">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 class="fw-bold text-primary mb-0" id="evtBoxTitle">Log Event: Pole down</h6>
                                <button type="button" class="btn-close small" onclick="document.getElementById('dynamicEventBox').style.display='none';"></button>
                            </div>
                            <div class="row g-2 mb-2">
                                <div class="col-md-5">
                                    <label class="form-label small fw-bold mb-1">Date/Time</label>
                                    <input type="text" name="timestamp" id="evtTimestamp" value="{{ today_str }} {{ now_dt_str.split('T')[-1] }}" class="form-control form-control-sm" placeholder="YYYY-MM-DD HH:MM" required>
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label small fw-bold mb-1" id="lblRefId">Crossing / Box / ID</label>
                                    <input type="text" name="ref_id" id="evtRefId" value="CR-A1_L1" class="form-control form-control-sm">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label small fw-bold mb-1">Surveyor</label>
                                    <input type="text" name="surveyor" id="evtSurveyor" value="Abror / Roderick" class="form-control form-control-sm" required>
                                </div>
                            </div>
                            <div class="row g-2 mb-2">
                                <div class="col-md-6">
                                    <label class="form-label small fw-bold mb-1 text-primary" id="lblVal1">Parameter 1</label>
                                    <input type="text" name="val1" id="evtVal1" class="form-control form-control-sm border-primary" required>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small fw-bold mb-1 text-primary" id="lblVal2">Parameter 2</label>
                                    <input type="text" name="val2" id="evtVal2" class="form-control form-control-sm border-primary">
                                </div>
                            </div>
                            <div class="row g-2 align-items-end">
                                <div class="col-md-9">
                                    <label class="form-label small fw-bold mb-1" id="lblRemarks">Remarks / Action Taken</label>
                                    <input type="text" name="remarks" id="evtRemarks" class="form-control form-control-sm" placeholder="Enter event details..." required>
                                </div>
                                <div class="col-md-3">
                                    <button type="submit" class="btn btn-sm btn-primary fw-bold w-100"><i class="fas fa-save"></i> Save Log</button>
                                </div>
                            </div>
                        </form>
                    </div>

                    <!-- CHRONOLOGICAL STREAM OF LOGGED INPUT EVENTS -->
                    <div style="max-height: 520px; overflow-y: auto;">
                        {% for il in input_logs %}
                            {% set is_issue = (il.event_type == 'Survey Issue Reporting') %}
                            {% set is_fix = (il.event_type == 'Mattress fix') %}
                            <div class="p-2 mb-2 bg-light border-start border-4 {{ 'border-danger' if is_issue else ('border-success' if is_fix else 'border-primary') }} rounded shadow-sm">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <div>
                                        <span class="badge {{ 'bg-danger' if is_issue else ('bg-success' if is_fix else 'bg-primary') }} me-1">{{ il.event_type }}</span>
                                        <strong class="mono text-dark">{{ il.timestamp }}</strong>
                                        {% if il.ref_id %}
                                            <span class="badge bg-secondary ms-1">{{ il.ref_id }}</span>
                                        {% endif %}
                                    </div>
                                    <div class="text-nowrap">
                                        <small class="text-muted me-1">{{ il.surveyor }}</small>
                                        <button type="button" class="btn btn-sm btn-outline-primary py-0 px-1 me-1" title="Edit Event"
                                                data-id="{{ il.id }}"
                                                data-type="{{ il.event_type }}"
                                                data-ts="{{ il.timestamp }}"
                                                data-surv="{{ il.surveyor }}"
                                                data-ref="{{ il.ref_id }}"
                                                data-val1="{{ il.val1 }}"
                                                data-val2="{{ il.val2 }}"
                                                data-rem="{{ il.remarks }}"
                                                onclick="editEventLogRow(this)">
                                            <i class="fas fa-edit"></i>
                                        </button>
                                        <form action="/mti/delete_input_log/{{ il.id }}" method="POST" style="display:inline;" onsubmit="return confirm('Delete this {{ il.event_type }} log entry?');">
                                            <button type="submit" class="btn btn-sm btn-outline-danger py-0 px-1"><i class="fas fa-trash"></i></button>
                                        </form>
                                    </div>
                                </div>
                                <div class="small fw-semibold text-dark">
                                    {{ il.val1 }}{% if il.val2 %} <span class="text-muted">|</span> {{ il.val2 }}{% endif %}
                                </div>
                                {% if il.remarks %}
                                    <div class="small text-muted">{{ il.remarks }}</div>
                                {% endif %}
                            </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    const DESIGN_CATALOG = {{ catalog_json | default('[]') | safe }};
    const catalogByName = {};

    const EVENT_CONFIGS = {
        "Pole down": {
            lblRef: "Location / Crossing ID", defRef: "CR-A1_L1",
            lbl1: "Pole Lock & Pin Status *", ph1: "Down & Locked in Working Position",
            lbl2: "USBL & ADCP Telemetry Check", ph2: "Ranger 2 HPT & RDI ADCP Online",
            phRem: "Over-the-side pole deployed prior to subsea operations..."
        },
        "Pole up": {
            lblRef: "Location / Crossing ID", defRef: "CR-A1_L1",
            lbl1: "Pole Stowed Status *", ph1: "Recovered & Secured on Deck Cradle",
            lbl2: "Reason for Recovery", ph2: "Transit / Weather / Maintenance",
            phRem: "USBL/ADCP pole raised and locked above waterline..."
        },
        "Mattress on water": {
            lblRef: "Xing / Box / Tag ID *", defRef: "CR-A1_M{{ ledger|length + 1 }}",
            lbl1: "Mattress Physical Tag # *", ph1: "e.g., #A046",
            lbl2: "Water Depth / Beacon Status", ph2: "Transponder Ch 1 & 2 Tracking OK",
            phRem: "Mattress overboarded through splash zone; WROV following descent..."
        },
        "Frame above water": {
            lblRef: "Xing / Box / Tag ID *", defRef: "CR-A1_M{{ ledger|length }}",
            lbl1: "Acoustic Release Status *", ph1: "4-Hook Release Confirmed by WROV",
            lbl2: "Frame Deck Status", ph2: "Frame Above Water & Landed on Deck",
            phRem: "Deployment frame recovered cleanly; preparing next mattress..."
        },
        "ADCP input": {
            lblRef: "Crossing / Station ID", defRef: "CR-A1_L1",
            lbl1: "Surface / Mid Current (m/s or kt & Dir) *", ph1: "e.g., Surf: 0.45 m/s @ 210 deg",
            lbl2: "Near-Seabed Current (m/s or kt & Dir)", ph2: "e.g., Seabed: 0.25 m/s @ 195 deg",
            phRem: "ADCP current profile logged prior to mattress touchdown..."
        },
        "Wind Input": {
            lblRef: "Vessel / Location", defRef: "MMA Prestige (CR-A1)",
            lbl1: "Wind Speed (kt or m/s) & Direction (deg) *", ph1: "e.g., 18 kt @ 035 deg (NE)",
            lbl2: "Wave Height Hs (m) & Swell", ph2: "e.g., Hs = 0.8 m (Within <=1.0m limit)",
            phRem: "Bridge anemometer & sea state observation..."
        },
        "Survey Issue Reporting": {
            lblRef: "System / Sensor Affected *", defRef: "USBL / WROV / NaviPac",
            lbl1: "Issue / Fault Description *", ph1: "e.g., USBL acoustic dropout / ROV tether",
            lbl2: "Operational Impact / Downtime", ph2: "e.g., 25 min troubleshooting on DP",
            phRem: "Root cause and corrective action taken by onboard survey team..."
        }
    };

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

    function nowFormatted() {
        const now = new Date();
        const yyyy = now.getFullYear();
        const mm = String(now.getMonth() + 1).padStart(2, '0');
        const dd = String(now.getDate()).padStart(2, '0');
        const hh = String(now.getHours()).padStart(2, '0');
        const min = String(now.getMinutes()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd} ${hh}:${min}`;
    }

    function openMattressFixBox() {
        const drawerEl = document.getElementById('addFixDrawer');
        if (drawerEl && !drawerEl.classList.contains('show')) {
            new bootstrap.Collapse(drawerEl, { toggle: true });
        }
        document.getElementById('inpFixDateTime').value = nowFormatted();
        drawerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        document.getElementById('inpAsE').focus();
    }

    function openEventInputBox(evtType) {
        const cfg = EVENT_CONFIGS[evtType];
        if (!cfg) return;
        const box = document.getElementById('dynamicEventBox');
        document.getElementById('evtLogId').value = '';
        document.getElementById('evtTypeInput').value = evtType;
        document.getElementById('evtBoxTitle').innerText = 'Log Event: ' + evtType;
        document.getElementById('evtTimestamp').value = nowFormatted();
        document.getElementById('lblRefId').innerText = cfg.lblRef;
        document.getElementById('evtRefId').value = cfg.defRef;
        document.getElementById('lblVal1').innerText = cfg.lbl1;
        document.getElementById('evtVal1').value = '';
        document.getElementById('evtVal1').placeholder = cfg.ph1;
        document.getElementById('lblVal2').innerText = cfg.lbl2;
        document.getElementById('evtVal2').value = '';
        document.getElementById('evtVal2').placeholder = cfg.ph2;
        document.getElementById('evtRemarks').value = '';
        document.getElementById('evtRemarks').placeholder = cfg.phRem;
        box.style.display = 'block';
        document.getElementById('evtVal1').focus();
    }

    function editEventLogRow(btn) {
        const d = btn.dataset;
        openEventInputBox(d.type);
        document.getElementById('evtLogId').value = d.id;
        document.getElementById('evtBoxTitle').innerText = 'Edit Event: ' + d.type;
        document.getElementById('evtTimestamp').value = d.ts;
        document.getElementById('evtSurveyor').value = d.surv;
        document.getElementById('evtRefId').value = d.ref;
        document.getElementById('evtVal1').value = d.val1;
        document.getElementById('evtVal2').value = d.val2;
        document.getElementById('evtRemarks').value = d.rem;
        document.getElementById('dynamicEventBox').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

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
        toggleGapInputs();
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
        input_logs=input_logs,
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
        now_dt_str=now_dt_str,
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

    corners = compute_4_corners(as_e, as_n, hdg, 6.0, 3.0)
    dt_str = (request.form.get("install_date") or datetime.utcnow().strftime('%Y-%m-%d %H:%M')).strip()
    xing_id = (request.form.get("crossing_id") or "CR-A1_L1").strip()
    box_id = (request.form.get("design_box_id") or f"CR-A1_M{unit_no}").strip()
    tag_id = (request.form.get("physical_tag") or "").strip()
    rem_str = (request.form.get("remarks") or "").strip()

    existing = next((r for r in ledger if int(r.get("unit_no", 0)) == unit_no), None)
    entry = {
        "id": existing["id"] if existing else (max([int(r.get("id", 0)) for r in ledger] + [0]) + 1),
        "unit_no": unit_no,
        "is_first_in_array": is_first,
        "unit_type": request.form.get("unit_type", "Concrete Mattress"),
        "crossing_id": xing_id,
        "design_box_id": box_id,
        "physical_tag": tag_id,
        "install_date": dt_str,
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
        "remarks": rem_str,
        **corners
    }
    if existing:
        ledger.remove(existing)
    ledger.append(entry)
    state["ledger"] = ledger

    input_logs = state.get("input_logs", [])
    gap_summary = "1st Unit" if is_first else f"G1:{gap1:.2f}m, G2:{gap2:.2f}m"
    if not existing:
        input_logs.append({
            "id": max([int(x.get("id", 0)) for x in input_logs] + [0]) + 1,
            "event_type": "Mattress fix",
            "timestamp": dt_str,
            "surveyor": getattr(current_user, "name", "Surveyor"),
            "ref_id": f"{box_id} ({tag_id})",
            "val1": f"E:{as_e:.2f}, N:{as_n:.2f} (dCL:{cl_off:.2f}m)",
            "val2": f"Brg:{hdg:.1f} deg | {gap_summary}",
            "remarks": rem_str
        })
        state["input_logs"] = input_logs

    save_mti_state(state)
    flash(f"Saved Unit #{unit_no} ({box_id} / {tag_id}) to Ledger & Input Log!", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/delete_fix/<int:fix_id>', methods=['POST'])
@login_required
def delete_fix(fix_id):
    state = load_mti_state()
    state["ledger"] = [r for r in state.get("ledger", []) if int(r.get("id", 0)) != fix_id]
    save_mti_state(state)
    flash("Removed entry from MTI Ledger.", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/add_input_log', methods=['POST'])
@login_required
def add_input_log():
    state = load_mti_state()
    input_logs = state.get("input_logs", [])
    log_id = request.form.get("log_id", type=int)
    existing = next((x for x in input_logs if int(x.get("id", 0)) == log_id), None) if log_id else None

    entry = {
        "id": existing["id"] if existing else (max([int(x.get("id", 0)) for x in input_logs] + [0]) + 1),
        "event_type": (request.form.get("event_type") or "Pole down").strip(),
        "timestamp": (request.form.get("timestamp") or datetime.utcnow().strftime('%Y-%m-%d %H:%M')).strip(),
        "surveyor": (request.form.get("surveyor") or getattr(current_user, "name", "Surveyor")).strip(),
        "ref_id": (request.form.get("ref_id") or "").strip(),
        "val1": (request.form.get("val1") or "").strip(),
        "val2": (request.form.get("val2") or "").strip(),
        "remarks": (request.form.get("remarks") or "").strip()
    }
    if existing:
        input_logs.remove(existing)
    input_logs.append(entry)
    state["input_logs"] = input_logs
    save_mti_state(state)
    flash(f"Logged '{entry['event_type']}' at {entry['timestamp']}!", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/delete_input_log/<int:log_id>', methods=['POST'])
@login_required
def delete_input_log(log_id):
    state = load_mti_state()
    state["input_logs"] = [x for x in state.get("input_logs", []) if int(x.get("id", 0)) != log_id]
    save_mti_state(state)
    flash("Removed event from Survey Input Log.", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/update_targets', methods=['POST'])
@login_required
def update_targets():
    state = load_mti_state()
    new_target = request.form.get("target_matt", type=int)
    if new_target and new_target > 0:
        state["campaign_target_mattresses"] = new_target
        save_mti_state(state)
        flash(f"Updated Mattress Target Total to {new_target} units!", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/sync_to_dpr', methods=['POST'])
@login_required
def sync_to_dpr():
    from app import SurveyTask, db
    state = load_mti_state()
    sync_date_str = request.form.get("sync_date") or datetime.utcnow().strftime('%Y-%m-%d')
    sync_dt = datetime.strptime(sync_date_str, '%Y-%m-%d').date()

    day_fixes = [r for r in state.get("ledger", []) if str(r.get("install_date", "")).startswith(sync_date_str)]
    day_events = [e for e in state.get("input_logs", []) if str(e.get("timestamp", "")).startswith(sync_date_str)]

    if not day_fixes and not day_events:
        flash(f"No MTI fixes or input events found on {sync_date_str} to sync.", "error")
        return redirect(url_for('mti_bp.mti_dashboard'))

    comp_units = [f"#{r['unit_no']} ({r['design_box_id']}/{r['physical_tag']}, dCL={r['cl_offset_m']}m)" for r in day_fixes if r.get("status") == "Completed"]
    prog_units = [f"#{r['unit_no']} ({r['design_box_id']})" for r in day_fixes if r.get("status") == "In Progress"]
    evt_summaries = [f"[{e['timestamp'].split(' ')[-1]} {e['event_type']}] {e['val1']}" for e in sorted(day_events, key=lambda x: x.get('timestamp', ''))]

    opening_str = f"MMA Prestige Subsea Mattress Installation Witnessing ({sync_date_str})"
    closing_parts = []
    if comp_units:
        closing_parts.append("Completed & Verified: " + "; ".join(comp_units))
    if prog_units:
        closing_parts.append("Ongoing: " + ", ".join(prog_units))
    if evt_summaries:
        closing_parts.append("Shift Events: " + "; ".join(evt_summaries[:8]))
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
    flash(f"Synced {sync_date_str} MTI fixes & event inputs into the DPR & KPI Master Register!", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/export_excel', methods=['GET'])
@login_required
def export_excel():
    state = load_mti_state()
    df_ledger = pd.DataFrame(state.get("ledger", []))
    df_events = pd.DataFrame(state.get("input_logs", []))
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_ledger.to_excel(writer, index=False, sheet_name='1_Mattress_Fix_Ledger')
        df_events.to_excel(writer, index=False, sheet_name='2_Survey_Input_Log')
    output.seek(0)
    return send_file(
        output,
        download_name=f"MMA_Prestige_MTI_Ledger_{datetime.utcnow().strftime('%Y%m%d')}.xlsx",
        as_attachment=True
    )
