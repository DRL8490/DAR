import os, sys, io, re, math, json, zlib, base64
from datetime import datetime
import io, json, math, copy, zlib, base64
from datetime import datetime, date
import pandas as pd
from flask import Blueprint, render_template, render_template_string, request, redirect, url_for, flash, send_file
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
    {"layer": r[0], "name": r[1], "design_e": r[2], "design_n": r[3], "bearing": round((r[4] + 180.0) % 360.0, 3), "length": 6.0, "width": 3.0}
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
            "cl_offset_m": 0.12, "heading_deg": 195.854, "gap1_m": 0.00, "gap2_m": 0.00, "gap_m": 0.00,
            "status": "Completed",
            "remarks": "First mattress in array (04-Nov 16:00, CR-A1_M15, Tag #A046); Center & Bearing verified.",
            **compute_4_corners(194541.520, 2702613.300, 195.854)
        },
        {
            "id": 2, "unit_no": 2, "is_first_in_array": False, "unit_type": "Concrete Mattress",
            "crossing_id": "CR-A1_L1", "design_box_id": "CR-A1_M16", "physical_tag": "#A007",
            "install_date": "2026-11-05 04:40", "shift": "Abror (Day) / Roderick (Night)",
            "design_e": 194544.329, "design_n": 2702612.575, "aslaid_e": 194544.450, "aslaid_n": 2702612.485,
            "cl_offset_m": 0.15, "heading_deg": 195.854, "gap1_m": 0.02, "gap2_m": 0.10, "gap_m": 0.10,
            "status": "Completed",
            "remarks": "Installed 05-Nov 04:40 (CR-A1_M16, Tag #A007); Gap 1 (N) = 0.02m, Gap 2 (S) = 0.10m; 4 corners calculated.",
            **compute_4_corners(194544.450, 2702612.485, 195.854)
        },
        {
            "id": 3, "unit_no": 3, "is_first_in_array": False, "unit_type": "Concrete Mattress",
            "crossing_id": "CR-A1_L1", "design_box_id": "CR-A1_M17", "physical_tag": "Pending",
            "install_date": "2026-11-05 19:00", "shift": "Abror (Day) / Roderick (Night)",
            "design_e": 194547.215, "design_n": 2702611.755, "aslaid_e": 194547.360, "aslaid_n": 2702611.650,
            "cl_offset_m": 0.18, "heading_deg": 195.854, "gap1_m": 0.12, "gap2_m": 0.22, "gap_m": 0.22,
            "status": "In Progress",
            "remarks": "Placed on seabed by 19:00 (center delta 0.18m); pending WROV seating adjustment to close >0.20m West edge gap.",
            **compute_4_corners(194547.360, 2702611.650, 195.854)
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
            "ref_id": "CR-A1_M15 (#A046)", "val1": "E:194541.52, N:2702613.30", "val2": "Brg:195.9 deg | 1st Unit",
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
    for r in st.get("ledger", []):
        if float(r.get("heading_deg", 0)) < 180.0:
            r["heading_deg"] = round(float(r.get("heading_deg", 195.854)) + 180.0, 3)
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


    return render_template(
        'mti_dashboard.html',
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
    qaqc_e = request.form.get("qaqc_e", type=float) or 0.0
    qaqc_n = request.form.get("qaqc_n", type=float) or 0.0
    qaqc_brg = request.form.get("qaqc_brg", type=float) or 0.0
    usbl_sensor = (request.form.get("usbl_sensor") or "Survey Pole").strip()

    pts = []
    for i in (1, 2, 3, 4):
        ce = request.form.get(f"c{i}_e", type=float)
        cn = request.form.get(f"c{i}_n", type=float)
        cz = request.form.get(f"c{i}_z", type=float)
        if ce and cn:
            pts.append((ce, cn, cz or 0.0))

    if len(pts) == 4:
        as_e = round(sum(p[0] for p in pts) / 4.0, 3)
        as_n = round(sum(p[1] for p in pts) / 4.0, 3)
        as_z = round(sum(p[2] for p in pts) / 4.0, 3)
        be, bn = (pts[0][0] + pts[1][0]) / 2.0, (pts[0][1] + pts[1][1]) / 2.0
        fe, fn = (pts[2][0] + pts[3][0]) / 2.0, (pts[2][1] + pts[3][1]) / 2.0
        hdg = round((math.degrees(math.atan2(fe - be, fn - bn)) + 360.0) % 360.0, 3)
        if hdg < 180.0:
            hdg = round(hdg + 180.0, 3)
        corners = {f"c{i+1}_e": round(pts[i][0], 3) for i in range(4)}
        corners.update({f"c{i+1}_n": round(pts[i][1], 3) for i in range(4)})
        corners.update({f"c{i+1}_z": round(pts[i][2], 3) for i in range(4)})
    else:
        as_e = request.form.get("aslaid_e", type=float) or qaqc_e
        as_n = request.form.get("aslaid_n", type=float) or qaqc_n
        as_z = request.form.get("aslaid_z", type=float) or 0.0
        hdg = round(request.form.get("heading_deg", type=float) or qaqc_brg or 195.854, 3)
        if hdg < 180.0:
            hdg = round(hdg + 180.0, 3)
        corners = compute_4_corners(as_e, as_n, hdg, 6.0, 3.0)

    cl_off = round(math.hypot(as_e - des_e, as_n - des_n), 2) if (as_e and des_e) else (request.form.get("cl_offset_m", type=float) or 0.0)

    gnw, gne, gsw, gse = [request.form.get(k, "").strip() for k in ("gap_nw", "gap_ne", "gap_sw", "gap_se")]
    g_parts, g_vals = [], []
    if not is_first:
        for lbl, val in [("NW", gnw), ("NE", gne), ("SW", gsw), ("SE", gse)]:
            if val != "":
                try:
                    fv = round(float(val), 2)
                    g_parts.append(f"{lbl}:{fv:.2f}m")
                    g_vals.append(fv)
                except Exception:
                    pass
    if is_first:
        gap_labels, gap1, gap2, max_gap = "1st Unit (N/A)", 0.0, 0.0, 0.0
    elif g_vals:
        gap_labels = " | ".join(g_parts)
        gap1, gap2, max_gap = g_vals[0], (g_vals[1] if len(g_vals) > 1 else g_vals[0]), max(g_vals)
    else:
        gap1 = round(request.form.get("gap1_m", type=float) or 0.0, 2)
        gap2 = round(request.form.get("gap2_m", type=float) or 0.0, 2)
        max_gap = round(max(gap1, gap2), 2)
        gap_labels = f"G1:{gap1:.2f}m | G2:{gap2:.2f}m"

    env_w = (request.form.get("env_wind") or "").strip()
    env_c = (request.form.get("env_current") or "").strip()
    env_s = (request.form.get("env_swell") or "").strip()
    env_tag = " | ".join([f"{k}:{v}" for k, v in [("Wind", env_w), ("Curr", env_c)] if v])

    dt_str = (request.form.get("install_date") or datetime.utcnow().strftime('%Y-%m-%d %H:%M')).strip()
    xing_id = (request.form.get("crossing_id") or "CR-A1_L1").strip()
    box_id = (request.form.get("design_box_id") or f"CR-A1_M{unit_no}").strip()
    tag_id = (request.form.get("physical_tag") or "").strip()
    rem_str = (request.form.get("remarks") or "").strip()
    if usbl_sensor and f"[{usbl_sensor}]" not in rem_str:
        rem_str = f"[{usbl_sensor}] {rem_str}".strip()
    if env_tag and env_tag not in rem_str:
        rem_str = f"{rem_str} [{env_tag}]".strip()

    existing = next((r for r in ledger if int(r.get("unit_no", 0)) == unit_no), None)
    entry = {
        "id": existing["id"] if existing else (max([int(r.get("id", 0)) for r in ledger] + [0]) + 1),
        "unit_no": unit_no, "is_first_in_array": is_first, "unit_type": "Concrete Mattress",
        "crossing_id": xing_id, "design_box_id": box_id, "physical_tag": tag_id,
        "install_date": dt_str, "usbl_sensor": usbl_sensor,
        "design_e": round(des_e, 3), "design_n": round(des_n, 3),
        "qaqc_e": round(qaqc_e or as_e, 3), "qaqc_n": round(qaqc_n or as_n, 3), "qaqc_brg": round(qaqc_brg or hdg, 3),
        "aslaid_e": round(as_e, 3), "aslaid_n": round(as_n, 3), "aslaid_z": round(as_z, 3),
        "cl_offset_m": round(cl_off, 2), "heading_deg": hdg,
        "gap_nw": gnw, "gap_ne": gne, "gap_sw": gsw, "gap_se": gse,
        "gap_labels": gap_labels, "gap1_m": gap1, "gap2_m": gap2, "gap_m": max_gap,
        "env_wind": env_w, "env_current": env_c, "env_swell": env_s,
        "status": request.form.get("status", "Completed"), "remarks": rem_str,
        **corners
    }
    if existing:
        ledger.remove(existing)
    ledger.append(entry)
    state["ledger"] = ledger

    input_logs = state.get("input_logs", [])
    if not existing:
        input_logs.append({
            "id": max([int(x.get("id", 0)) for x in input_logs] + [0]) + 1,
            "event_type": "Mattress fix", "timestamp": dt_str,
            "surveyor": getattr(current_user, "name", "Surveyor"),
            "ref_id": f"{box_id} ({tag_id}) [{usbl_sensor}]",
            "val1": f"Act E:{as_e:.2f}, N:{as_n:.2f}, Z:{as_z:.2f} (dCL:{cl_off:.2f}m)",
            "val2": f"Brg:{hdg:.1f} deg | {gap_labels}",
            "remarks": rem_str
        })
        state["input_logs"] = input_logs

    save_mti_state(state)
    flash(f"Saved Unit #{unit_no} ({box_id} / {tag_id}) via {usbl_sensor}!", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/delete_fix/<int:fix_id>', methods=['POST'])
@login_required
def delete_fix(fix_id):
    state = load_mti_state()
    state["ledger"] = [r for r in state.get("ledger", []) if int(r.get("id", 0)) != fix_id]
    save_mti_state(state)
    flash("Removed entry from MTI Ledger.", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/add_input_log', methods=['POST'])
@login_required
def add_input_log():
    state = load_mti_state()
    input_logs = state.get("input_logs", [])
    log_id = request.form.get("log_id", type=int)
    existing = next((x for x in input_logs if int(x.get("id", 0)) == log_id), None) if log_id else None

    evt_t = (request.form.get("event_type") or "Pole down").strip()
    usbl_s = (request.form.get("usbl_sensor") or "").strip() if evt_t in ("ROV & Vessel Ops", "Calib, Setup & TBT", "Survey Issue Reporting", "Survey Issue") else ""
    env_w = (request.form.get("env_wind") or "").strip()
    env_c = (request.form.get("env_current") or "").strip()
    env_s = (request.form.get("env_swell") or "").strip()
    env_tag = " | ".join([f"{k}:{v}" for k, v in [("USBL", usbl_s), ("Wind", env_w), ("Curr", env_c)] if v])
    rem = (request.form.get("remarks") or "").strip()
    if env_tag and env_tag not in rem:
        rem = f"{rem} [{env_tag}]".strip()

    entry = {
        "id": existing["id"] if existing else (max([int(x.get("id", 0)) for x in input_logs] + [0]) + 1),
        "event_type": evt_t,
        "timestamp": (request.form.get("timestamp") or datetime.utcnow().strftime('%Y-%m-%d %H:%M')).strip(),
        "surveyor": (request.form.get("surveyor") or getattr(current_user, "name", "Surveyor")).strip(),
        "ref_id": (request.form.get("ref_id") or "").strip(),
        "val1": (request.form.get("val1") or "").strip(),
        "val2": (request.form.get("val2") or "").strip(),
        "usbl_sensor": usbl_s,
        "env_wind": env_w, "env_current": env_c, "env_swell": env_s,
        "remarks": rem
    }
    if existing:
        input_logs.remove(existing)
    input_logs.append(entry)
    state["input_logs"] = input_logs
    save_mti_state(state)
    flash(f"Logged '{entry['event_type']}' at {entry['timestamp']}!", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/delete_input_log/<int:log_id>', methods=['POST'])
@login_required
def delete_input_log(log_id):
    state = load_mti_state()
    state["input_logs"] = [x for x in state.get("input_logs", []) if int(x.get("id", 0)) != log_id]
    save_mti_state(state)
    flash("Removed event from Survey Input Log.", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

@mti_bp.route('/update_targets', methods=['POST'])
@login_required
def update_targets():
    state = load_mti_state()
    new_target = request.form.get("target_matt", type=int)
    if new_target and new_target > 0:
        state["campaign_target_mattresses"] = new_target
        save_mti_state(state)
        flash(f"Updated Mattress Target Total to {new_target} units!", "success")
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

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
        return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

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
    return redirect(url_for('mti_bp.mti_mobile') if '/mobile' in (request.referrer or '') else url_for('mti_bp.mti_dashboard'))

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


# --- STEP 2: MTI MODULE USER ACCESS CONTROL ---
def get_mti_allowed_uids():
    from app import AppConfig, User, db, is_user_admin
    cfg = AppConfig.query.first()
    schema = json.loads(cfg.schema_data) if (cfg and cfg.schema_data) else {}
    if "mti_allowed_uids" not in schema:
        default_uids = [u.id for u in User.query.all() if is_user_admin(u) or any(k in (u.name or '').lower() for k in ('abror', 'roderick', 'daryll'))]
        schema["mti_allowed_uids"] = default_uids
        if cfg:
            cfg.schema_data = json.dumps(schema)
            db.session.commit()
    return set(int(x) for x in schema.get("mti_allowed_uids", []))

@mti_bp.before_request
def enforce_mti_access():
    from app import is_user_admin
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if int(current_user.id) not in get_mti_allowed_uids():
        flash("Access Denied: Your account is not enabled for the MTI Module.", "error")
        return redirect(url_for('dashboard'))

@mti_bp.route('/toggle_user_access', methods=['POST'])
@login_required
def toggle_user_access():
    from app import AppConfig, db, is_user_admin
    if not is_user_admin(current_user):
        return {"ok": False}, 403
    uid = request.form.get("user_id", type=int)
    allow = request.form.get("allow") == "true"
    cfg = AppConfig.query.first()
    schema = json.loads(cfg.schema_data) if (cfg and cfg.schema_data) else {}
    allowed = set(int(x) for x in schema.get("mti_allowed_uids", get_mti_allowed_uids()))
    allowed.add(uid) if allow else allowed.discard(uid)
    schema["mti_allowed_uids"] = sorted(list(allowed))
    cfg.schema_data = json.dumps(schema)
    db.session.commit()
    return {"ok": True, "user_id": uid, "allowed": allow}

@mti_bp.route('/user_access_list', methods=['GET'])
@login_required
def user_access_list():
    from app import User, is_user_admin
    if not is_user_admin(current_user):
        return {"users": []}
    allowed = get_mti_allowed_uids()
    return {"users": [{"id": u.id, "name": u.name, "email": getattr(u, "email", getattr(u, "username", "")), "is_admin": is_user_admin(u), "mti": (u.id in allowed)} for u in User.query.order_by(User.id).all()]}


@mti_bp.route('/mobile', methods=['GET'])
@login_required
def mti_mobile():
    from flask import render_template
    state = load_mti_state()
    ledger = sorted(state.get("ledger", []), key=lambda x: int(x.get("unit_no", 999)))
    input_logs = sorted(state.get("input_logs", []), key=lambda x: str(x.get("timestamp", "")), reverse=True)
    completed_matt = sum(1 for r in ledger if r.get("status") == "Completed" and r.get("unit_type", "Concrete Mattress") == "Concrete Mattress")
    return render_template('mti_mobile.html', ledger=ledger, input_logs=input_logs, completed_matt=completed_matt, target_matt=int(state.get("campaign_target_mattresses", 139)), catalog_json=json.dumps(MATTRESS_CATALOG))


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


# --- PURE ASCII PRELOADED DPR DATASET (30 OCT - 07 NOV 2026) & SAFE STORAGE ---
PRELOADED_MTI_LEDGER = [
    {
        "id": 1, "unit_no": 1, "is_first_in_array": True, "unit_type": "Concrete Mattress",
        "crossing_id": "CR-A1_L1", "design_box_id": "CR-A1_M15", "physical_tag": "#A046",
        "install_date": "2026-11-04 14:34", "usbl_sensor": "Survey Pole",
        "design_e": 194541.443, "design_n": 2702613.394, "design_brg": 195.861,
        "qaqc_e": 194541.206, "qaqc_n": 2702613.513, "qaqc_brg": 196.889,
        "aslaid_e": 194541.206, "aslaid_n": 2702613.513, "aslaid_z": -18.20,
        "cl_offset_m": 0.265, "heading_deg": 196.889, "brg_diff_deg": -1.028,
        "c1_e": 194540.642, "c1_n": 2702616.819, "c1_z": -18.20,
        "c2_e": 194543.513, "c2_n": 2702615.948, "c2_z": -18.20,
        "c3_e": 194541.770, "c3_n": 2702610.207, "c3_z": -18.20,
        "c4_e": 194538.899, "c4_n": 2702611.078, "c4_z": -18.20,
        "gap_nw": "", "gap_ne": "", "gap_sw": "", "gap_se": "",
        "gap_labels": "1st Unit (N/A)", "gap1_m": 0.0, "gap2_m": 0.0, "gap_m": 0.0,
        "env_wind": "", "env_current": "",
        "status": "Completed",
        "remarks": "[Survey Pole] Mattress installed completed (CR-A1_M15) #A046 (14:34 - 16:00:20); dCL=0.265m, dBrg=-1.028 deg"
    },
    {
        "id": 2, "unit_no": 2, "is_first_in_array": False, "unit_type": "Concrete Mattress",
        "crossing_id": "CR-A1_L1", "design_box_id": "CR-A1_M16", "physical_tag": "#A007",
        "install_date": "2026-11-05 04:20", "usbl_sensor": "Survey Pole",
        "design_e": 194544.329, "design_n": 2702612.575, "design_brg": 195.852,
        "qaqc_e": 194544.356, "qaqc_n": 2702612.753, "qaqc_brg": 198.397,
        "aslaid_e": 194544.356, "aslaid_n": 2702612.753, "aslaid_z": -18.35,
        "cl_offset_m": 0.180, "heading_deg": 198.397, "brg_diff_deg": -2.545,
        "c1_e": 194543.879, "c1_n": 2702616.073, "c1_z": -18.35,
        "c2_e": 194546.726, "c2_n": 2702615.126, "c2_z": -18.35,
        "c3_e": 194544.833, "c3_n": 2702609.433, "c3_z": -18.35,
        "c4_e": 194541.986, "c4_n": 2702610.380, "c4_z": -18.35,
        "gap_nw": "0.02", "gap_ne": "", "gap_sw": "0.10", "gap_se": "",
        "gap_labels": "NW:0.02m | SW:0.10m", "gap1_m": 0.02, "gap2_m": 0.10, "gap_m": 0.10,
        "env_wind": "", "env_current": "",
        "status": "Completed",
        "remarks": "[Survey Pole] Mattress installed completed (CR-A1_M16) #A007 (04:20 - 04:40); Gap between Mat is 2cm North and 10cm South; ROV 4-corner fix completed at 05:00"
    }
]

_RAW_DPR_TUPLES = [
    ("2026-10-30 08:15", "08:15 - 15:15", "Calib, Setup & TBT", "Abror", "MMA Prestige / Quayside", "Survey Pole", "Install the survey equipment and integration", ""),
    ("2026-10-30 15:15", "15:15 - 19:30", "Calib, Setup & TBT", "Abror", "MMA Prestige / Quayside", "Survey Pole", "Perform Dimcon", ""),
    ("2026-10-30 19:30", "19:30 - 20:00", "Calib, Setup & TBT", "Roderick", "MMA Prestige / Quayside", "Survey Pole", "Create SD3 as new control point for calibration", ""),
    ("2026-10-31 07:00", "07:00 - 07:44", "Calib, Setup & TBT", "Abror", "MMA Prestige / Quayside", "Survey Pole", "Prepare for calibration", ""),
    ("2026-10-31 07:44", "07:44 - 15:30", "Calib, Setup & TBT", "Abror", "MMA Prestige / Quayside", "Survey Pole", "Starting heading alignment, GPS Verification and pitch roll calibration", "Completed calibration at 15:30"),
    ("2026-10-31 15:30", "15:30 - 18:30", "Calib, Setup & TBT", "Abror", "MMA Prestige / Quayside", "Survey Pole", "Wet test equipment", "Completed wet test equipment at 18:30"),
    ("2026-10-31 18:30", "18:30 - 22:00", "Calib, Setup & TBT", "Abror", "MMA Prestige / Quayside", "Survey Pole", "Continue system integration", ""),
    ("2026-11-01 05:00", "05:00 - 08:00", "Calib, Setup & TBT", "Roderick", "MMA Prestige / Quayside", "Survey Pole", "Continue node offset check", ""),
    ("2026-11-01 09:00", "09:00 - 11:40", "ROV & Vessel Ops", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Vessel cast off to site calibration", ""),
    ("2026-11-01 11:40", "11:40 - 12:15", "Pole down", "Abror", "MMA Prestige / CR-A1", "", "Arrive site and perform DP trial, Deploy SVP and pole", ""),
    ("2026-11-01 12:15", "12:15 - 12:28", "ROV & Vessel Ops", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Prepare to launch ROV for recovering the beacon", ""),
    ("2026-11-01 12:28", "12:28 - 13:40", "ROV & Vessel Ops", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "ROV off deck", ""),
    ("2026-11-01 13:40", "13:40 - 14:31", "ROV & Vessel Ops", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "ROV on deck", ""),
    ("2026-11-01 14:31", "14:31 - 08:15 (+1d)", "Calib, Setup & TBT", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Starting USBL calibration and processing", "Calibration vessel and survey pole USBL"),
    ("2026-11-02 08:15", "08:15 - 09:00", "Survey Issue Reporting", "Abror", "MMA Prestige / Mess Room", "Survey Pole", "Meeting with client for the status of USBL calibration results due to accuracy issue", ""),
    ("2026-11-02 09:00", "09:00 - 13:00", "Calib, Setup & TBT", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Re-perform USBL calibration", "Completed USBL calibration at 13:00"),
    ("2026-11-02 13:00", "13:00 - 13:11", "ROV & Vessel Ops", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Prepare to launch ROV for recovering the beacon", ""),
    ("2026-11-02 13:11", "13:11 - 13:50", "ROV & Vessel Ops", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "ROV off deck", ""),
    ("2026-11-02 13:50", "13:50 - 13:55", "Survey Issue Reporting", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "ROV on deck due umbilical entangled to cage wire", ""),
    ("2026-11-02 13:55", "13:55 - 16:30", "ROV & Vessel Ops", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Aborted to re-launch ROV due to weather", ""),
    ("2026-11-02 16:30", "16:30 - 18:00", "Pole up", "Abror", "MMA Prestige / CR-A1", "", "Survey pole recovered", ""),
    ("2026-11-02 18:00", "18:00 - 23:30", "Calib, Setup & TBT", "Abror", "Crane Cabin / Helmsman PC", "Survey Pole", "Preparing data for helmsman, waypoint and background", ""),
    ("2026-11-02 23:30", "23:30 - 24:00", "Survey Issue Reporting", "Roderick", "MMA Prestige / CR-A1", "Survey Pole", "Standby weather and troubleshoot USBL Accuracy ongoing", ""),
    ("2026-11-03 00:00", "00:00 - 07:00", "Calib, Setup & TBT", "Roderick", "Crane Cabin / Helmsman PC", "Survey Pole", "Continue preparing data for helmsman, waypoint and background", ""),
    ("2026-11-03 08:25", "08:25 - 09:30", "Calib, Setup & TBT", "Abror", "MMA Prestige / Mess Room", "Survey Pole", "NMDC induction and toolbox talk in mess room", ""),
    ("2026-11-03 09:30", "09:30 - 10:00", "Calib, Setup & TBT", "Abror", "MMA Prestige / Mess Room", "Survey Pole", "Daily project meeting", ""),
    ("2026-11-03 15:16", "15:16 - 16:00", "Calib, Setup & TBT", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "USBL Calibration report completed and submitted to Seatrench Field Engineer", ""),
    ("2026-11-03 16:00", "16:00 - 24:00", "Calib, Setup & TBT", "Abror", "Crane Cabin / Helmsman PC", "Survey Pole", "Continue preparing data for helmsman, waypoint and background", ""),
    ("2026-11-04 07:48", "07:48 - 08:19", "ROV & Vessel Ops", "Abror", "Echo 4 / CR-A1", "Survey Pole", "Echo 4 arrived on the Location", ""),
    ("2026-11-04 08:19", "08:19 - 08:25", "ROV & Vessel Ops", "Abror", "Echo 4 / CR-A1", "Survey Pole", "Moved 100 meters to create Echo 4 space, Echo 4 entering beacon location", ""),
    ("2026-11-04 08:25", "08:25 - 10:15", "ROV & Vessel Ops", "Abror", "Echo 4 / CR-A1", "Survey Pole", "Echo 4 start survey", ""),
    ("2026-11-04 10:15", "10:15 - 10:20", "Mattress on water", "Abror", "CR-A1_M15 (#A046)", "", "Started lifting the Mattress and put on the water", ""),
    ("2026-11-04 10:20", "10:20 - 13:25", "Mattress on water", "Abror", "CR-A1_M15 (#A046)", "", "Mattress on the seabed and start positioning", ""),
    ("2026-11-04 13:25", "13:25 - 14:34", "Mattress on water", "Abror", "CR-A1_M15 (#A046)", "", "Installation mattress on process, adjust heading and stabilize signal", ""),
    ("2026-11-04 14:34", "14:34 - 16:00:20", "Mattress fix", "Abror", "CR-A1_M15 (#A046)", "Survey Pole", "Act E:194541.206, N:2702613.513, Z:-18.20 (dCL:0.265m)", "Brg:196.889 deg | 1st Unit (N/A) | Mattress installed completed (CR-A1_M15) #A046"),
    ("2026-11-04 16:55", "16:55 - 17:00", "Mattress on water", "Abror", "CR-A1_M16 (#A007)", "", "Started lifting the Mattress and put on the water", ""),
    ("2026-11-04 17:00", "17:00 - 19:30", "Mattress on water", "Abror", "CR-A1_M16 (#A007)", "", "Started align the mattress to the position and ongoing installation", ""),
    ("2026-11-04 19:30", "19:30 - 20:45", "ROV & Vessel Ops", "Roderick", "CR-A1_M16 (#A007)", "Survey Pole", "ROV stuck inside the lifting frame", ""),
    ("2026-11-04 20:45", "20:45 - 21:55", "ROV & Vessel Ops", "Roderick", "CR-A1_M16 (#A007)", "Survey Pole", "ROV recovered and lifted up on deck", ""),
    ("2026-11-04 21:55", "21:55 - 24:00", "Survey Issue Reporting", "Roderick", "CR-A1_M16 (#A007)", "Survey Pole", "Repair ROV propeller damage", ""),
    ("2026-11-05 00:00", "00:00 - 00:15", "ROV & Vessel Ops", "Roderick", "CR-A1_M16 (#A007)", "Survey Pole", "ROV repaired and deployed into the water", ""),
    ("2026-11-05 00:15", "00:15 - 01:40", "Mattress on water", "Roderick", "CR-A1_M16 (#A007)", "", "Mattress deployed in the water to resume placing", ""),
    ("2026-11-05 01:40", "01:40 - 01:50", "Mattress on water", "Roderick", "CR-A1_M16 (#A007)", "", "Mattress on the seabed and start alignment", ""),
    ("2026-11-05 01:50", "01:50 - 02:20", "Survey Issue Reporting", "Roderick", "CR-A1_M16 (#A007)", "Survey Pole", "Beacon Signal lost and intermittent signal return", "01:50-02:00 & 02:05-02:19 signal lost; restored at 02:20"),
    ("2026-11-05 02:20", "02:20 - 04:20", "Mattress on water", "Roderick", "CR-A1_M16 (#A007)", "", "Continue repositioning of the mattress", ""),
    ("2026-11-05 04:20", "04:20 - 04:40", "Mattress fix", "Roderick", "CR-A1_M16 (#A007)", "Survey Pole", "Act E:194544.356, N:2702612.753, Z:-18.35 (dCL:0.180m)", "Brg:198.397 deg | Gap between Mat is 2cm North and 10cm South (CR-A1_M16 #A007)"),
    ("2026-11-05 04:40", "04:40 - 04:45", "Frame above water", "Roderick", "CR-A1_M16 (#A007)", "", "Frame safe release", ""),
    ("2026-11-05 04:45", "04:45 - 05:00", "ROV & Vessel Ops", "Roderick", "CR-A1_M16 (#A007)", "Survey Pole", "ROV final take and complete the four corner position of the mattress", ""),
    ("2026-11-05 05:00", "05:00 - 07:00", "ROV & Vessel Ops", "Roderick", "CR-A1_M16 (#A007)", "Survey Pole", "ROV recovered from water and placed on deck for maintenance", ""),
    ("2026-11-05 07:00", "07:00 - 07:05", "ROV & Vessel Ops", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Start deploying ROV into the water to continue mattress installation", ""),
    ("2026-11-05 07:05", "07:05 - 09:25", "Mattress on water", "Abror", "CR-A1_M17 (#A023)", "", "Connect mattress frame to crane and deploy into water (CR-A1_M17) #A023", ""),
    ("2026-11-05 09:25", "09:25 - 09:35", "Survey Issue Reporting", "Abror", "CR-A1_M17 (#A023)", "Survey Pole", "Restart USBL System signal beacon lost while mattress installation in process", "Assisted by ROV with gap reference"),
    ("2026-11-05 09:35", "09:35 - 10:47", "Mattress on water", "Abror", "CR-A1_M17 (#A023)", "", "USBL system back to normal, continue placing mattress with ROV and Sonar", ""),
    ("2026-11-05 10:47", "10:47 - 10:57", "Survey Issue Reporting", "Abror", "CR-A1_M17 (#A023)", "Survey Pole", "Restart USBL System signal beacon lost while mattress installation in process", ""),
    ("2026-11-05 10:57", "10:57 - 11:30", "Mattress on water", "Abror", "CR-A1_M17 (#A023)", "", "USBL system back to normal, continue placing mattress with ROV and Sonar", ""),
    ("2026-11-05 11:30", "11:30 - 13:00", "Survey Issue Reporting", "Abror", "CR-A1_M17 (#A023)", "Survey Pole", "Restart USBL System signal beacon lost; troubleshoot cable and connector of Survey Pole USBL", "Survey pole USBL off, signal result still same"),
    ("2026-11-05 12:15", "12:15 - 12:20", "Calib, Setup & TBT", "Abror", "CR-A1_M17 (#A023)", "Vessel", "Switch to Vessel USBL for navigation system", "For mattress positioning only; final position to be taken with Survey Pole USBL; Vessel USBL good and stable"),
    ("2026-11-05 12:20", "12:20 - 15:00", "Mattress on water", "Abror", "CR-A1_M17 (#A023)", "", "Continue repositioning of the mattress", "ROV struggling to adjust mattress heading as per design"),
    ("2026-11-05 15:00", "15:00 - 15:15", "Frame above water", "Abror", "CR-A1_M17 (#A023)", "", "Lift up frame on deck to install tagline to assist heading adjustment", ""),
    ("2026-11-05 15:15", "15:15 - 15:30", "Mattress on water", "Abror", "CR-A1_M17 (#A023)", "", "Lower back the frame into the water after tagline installed", ""),
    ("2026-11-05 15:30", "15:30 - 15:40", "ROV & Vessel Ops", "Abror", "CR-A1_M17 (#A023)", "Vessel", "Vessel adjust heading as survey guidance in navigation system", ""),
    ("2026-11-05 15:40", "15:40 - 16:00", "Mattress on water", "Abror", "CR-A1_M17 (#A023)", "", "Continue repositioning of the mattress with tagline", ""),
    ("2026-11-05 16:00", "16:00 - 18:00", "Mattress on water", "Abror", "CR-A1_M17 (#A023)", "", "Attempted Mattress Placement (#A023) with ROV on seabed", "Seabed not flat; East side matched but West side gap > 20 cm on ROV video; center within tolerance 0.18 m vs design"),
    ("2026-11-05 18:36", "18:36 - 19:10", "Mattress on water", "Abror", "CR-A1_M17 (#A023)", "", "Continue repositioning of the mattress with ROV and tagline to close gap", ""),
    ("2026-11-05 19:15", "19:15 - 19:20", "Frame above water", "Roderick", "CR-A1_M17 (#A023)", "", "ROV and mattress removed from water and placed back on main deck", ""),
    ("2026-11-05 19:25", "19:25 - 07:51 (+1d)", "Pole up", "Roderick", "MMA Prestige / CR-A1", "", "Survey pole secured and retrieved from water; operations on weather standby", "Lat 24d25m44.20s Long 120d27m10.72s, Heading=38.87 deg"),
    ("2026-11-06 07:51", "07:51 - 08:30", "Calib, Setup & TBT", "Abror", "Crane Cabin / Helmsman PC", "Survey Pole", "Preparation for installing remote Helmsman PC in crane cabin", ""),
    ("2026-11-06 09:30", "09:30 - 10:45", "ROV & Vessel Ops", "Abror", "Calibration Tripod", "Survey Pole", "Daily project meeting & Vessel moving into tripod position", ""),
    ("2026-11-06 10:45", "10:45 - 10:54", "Calib, Setup & TBT", "Abror", "Calibration Tripod", "Survey Pole", "Beacon tripod sending signal to USBL", ""),
    ("2026-11-06 10:54", "10:54 - 11:03", "ROV & Vessel Ops", "Abror", "Calibration Tripod", "Survey Pole", "ROV off deck and in the surface", ""),
    ("2026-11-06 11:03", "11:03 - 11:14", "Survey Issue Reporting", "Abror", "Calibration Tripod", "Survey Pole", "Tripod beacon found fallen on seabed", "Found calibration beacon tripod fallen and not standing in proper position (affected calibration result)"),
    ("2026-11-06 11:14", "11:14 - 11:20", "ROV & Vessel Ops", "Abror", "Calibration Tripod", "Survey Pole", "ROV recovered on deck", ""),
    ("2026-11-06 11:20", "11:20 - 15:00", "Calib, Setup & TBT", "Abror", "Crane Cabin / Helmsman PC", "Survey Pole", "Install Monitor control unit in crane cabin with wireless Wi-Fi connection", ""),
    ("2026-11-06 15:00", "15:00 - 19:00", "Calib, Setup & TBT", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Process current speed data as per recorded data", ""),
    ("2026-11-06 19:00", "19:00 - 20:00", "Survey Issue Reporting", "Roderick", "MMA Prestige / CR-A1", "Survey Pole", "Continue to troubleshoot USBL issue with string and signal", ""),
    ("2026-11-06 21:00", "21:00 - 07:00 (+1d)", "Calib, Setup & TBT", "Roderick", "MMA Prestige / CR-A1", "Survey Pole", "Operations remain on standby due to deteriorating weather conditions", "Lat 24d25m44.20s Long 120d27m10.72s, Heading=38.87 deg"),
    ("2026-11-07 09:00", "09:00 - 12:00", "Survey Issue Reporting", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Continue troubleshooting instability of USBL string", "Created new job in Mini-Ranger software and checked current setup wiring"),
    ("2026-11-07 12:00", "12:00 - 12:50", "Calib, Setup & TBT", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Make additional offset on WROV for new node to take fix coordinate reference", ""),
    ("2026-11-07 12:50", "12:50 - 13:30", "Pole down", "Abror", "MMA Prestige / CR-A1", "", "Lower survey pole to test system ADCP, USBL and MRU", ""),
    ("2026-11-07 13:30", "13:30 - 15:20", "Calib, Setup & TBT", "Abror", "Crane Cabin / Helmsman PC", "Survey Pole", "Deploy 1 and 2 beacons with crane assist to 20 m water depth to test USBL ping stability", "13:40-14:00 (1 beacon at 20m); 14:20-15:20 (2 beacons deployed simultaneously at 20m)"),
    ("2026-11-07 15:20", "15:20 - 15:50", "Survey Issue Reporting", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Lift up beacon on deck, testing complete - Survey Pole USBL data loss persists", "Result signal on Survey USBL still same; longer stay in water causes more data loss"),
    ("2026-11-07 15:50", "15:50 - 18:51", "Calib, Setup & TBT", "Abror", "MMA Prestige / CR-A1", "Survey Pole", "Record sea current and continue troubleshooting", ""),
    ("2026-11-07 18:51", "18:51 - 19:00", "ROV & Vessel Ops", "Abror", "Calibration Tripod", "Survey Pole", "Prepare ROV to install tripod beacon on the seabed for next installation", "")
]

PRELOADED_MTI_LOGS = []
for _idx, (_ts, _win, _evt, _surv, _ref, _usbl, _act, _rem) in enumerate(_RAW_DPR_TUPLES, 1):
    _frem = f"{_act} - {_rem} ({_win})" if _rem else f"{_act} ({_win})"
    if _usbl:
        _frem += f" [USBL:{_usbl}]"
    PRELOADED_MTI_LOGS.append({
        "id": _idx, "event_type": _evt, "timestamp": _ts, "surveyor": _surv, "ref_id": _ref,
        "val1": _act, "val2": (_rem if _evt == "Mattress fix" else f"Window: {_win}"),
        "usbl_sensor": _usbl, "env_wind": "", "env_current": "", "remarks": _frem
    })

_BASE_LOAD_MTI = load_mti_state

def save_mti_state(state):
    raw = json.dumps(state, ensure_ascii=False)
    try:
        from app import db
        from sqlalchemy import text
        db.session.execute(text("CREATE TABLE IF NOT EXISTS mti_state_store (k VARCHAR(64) PRIMARY KEY, v TEXT)"))
        row = db.session.execute(text("SELECT k FROM mti_state_store WHERE k = 'mti_state_v1'")).fetchone()
        if row:
            db.session.execute(text("UPDATE mti_state_store SET v = :val WHERE k = 'mti_state_v1'"), {"val": raw})
        else:
            db.session.execute(text("INSERT INTO mti_state_store (k, v) VALUES ('mti_state_v1', :val)"), {"val": raw})
        db.session.commit()
    except Exception:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
    try:
        sf = globals().get("MTI_STATE_FILE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "mti_state.json")
        with open(sf, "w", encoding="utf-8") as f:
            f.write(raw)
    except Exception:
        pass

def load_mti_state():
    st = None
    try:
        from app import db
        from sqlalchemy import text
        db.session.execute(text("CREATE TABLE IF NOT EXISTS mti_state_store (k VARCHAR(64) PRIMARY KEY, v TEXT)"))
        row = db.session.execute(text("SELECT v FROM mti_state_store WHERE k = 'mti_state_v1'")).fetchone()
        if row and row[0]:
            st = json.loads(row[0])
    except Exception:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
    if not st:
        try:
            st = _BASE_LOAD_MTI()
        except Exception:
            try:
                from app import db
                db.session.rollback()
            except Exception:
                pass
            st = {}
    if not isinstance(st, dict):
        st = {}
    if not st.get("dpr_20261107_clean_v7"):
        st["ledger"] = [dict(x) for x in PRELOADED_MTI_LEDGER]
        st["input_logs"] = [dict(x) for x in PRELOADED_MTI_LOGS]
        st["dpr_20261107_clean_v7"] = True
        save_mti_state(st)
    return st

# --- STEP 4: CLEAN 4-PANEL STUDIO (/mti/studio) & TABLE-BASED SURVEY SETUP (/mti/setup) ---
import os, re, gc, glob, json, base64
import numpy as np
from flask import jsonify, send_file, render_template_string
from mti_4panel_math import (
    AREA_LOCATIONS, run_rov_4panel_verification, parse_bathy_xyz_text,
    parse_design_catalog_text, parse_dxf_background,
    load_custom_catalog, build_crossing_boxes_from_catalog
)
from mti_4panel_a3 import generate_a3_4panel_chart
from mti_4panel_reports import build_structured_report_markdown, generate_a4_report_pdf, generate_editable_docx

MTI_WS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
_as_bool = lambda v, d=True: d if v is None else str(v).strip().lower() in ("1", "true", "yes", "on")

def _load_setup_meta():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    p = os.path.join(MTI_WS_DIR, "setup_meta.json")
    meta = {"cad": {}, "bathy": {}}
    if os.path.exists(p):
        try:
            meta = json.loads(open(p, "r", encoding="utf-8").read())
        except Exception:
            pass
    try:
        st = load_mti_state()
        db_setup = st.get("survey_setup") or {}
        for k in ("cad", "bathy"):
            for loc, info in (db_setup.get(k) or {}).items():
                if loc not in meta.get(k, {}):
                    meta.setdefault(k, {})[loc] = info
                if k == "bathy" and info.get("pts_compact"):
                    npy_p = os.path.join(MTI_WS_DIR, f"{loc}_seabed.npy")
                    if not os.path.exists(npy_p):
                        np.save(npy_p, np.array(info["pts_compact"], dtype=float))
                elif k == "cad" and info.get("polylines"):
                    cad_p = os.path.join(MTI_WS_DIR, f"{loc}_cad_bg.json")
                    if not os.path.exists(cad_p):
                        open(cad_p, "w", encoding="utf-8").write(json.dumps(info["polylines"]))
    except Exception:
        pass
    return meta

def _save_setup_meta(meta):
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    open(os.path.join(MTI_WS_DIR, "setup_meta.json"), "w", encoding="utf-8").write(json.dumps(meta))
    try:
        st = load_mti_state()
        st["survey_setup"] = meta
        save_mti_state(st)
    except Exception:
        pass

def _purge_cached_pdfs():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    for p in glob.glob(os.path.join(MTI_WS_DIR, "*.pdf")):
        try:
            os.remove(p)
        except Exception:
            pass

def _get_current_user_display_name():
    try:
        from flask import session, g, request
        try:
            from flask_login import current_user
            if current_user and getattr(current_user, "is_authenticated", False):
                for attr in ("full_name", "display_name", "real_name", "name", "surveyor_name", "username", "user", "email"):
                    val = getattr(current_user, attr, None)
                    if val and str(val).strip() and str(val).strip().lower() != "duty surveyor":
                        return str(val).strip()
                u_dict = getattr(current_user, "__dict__", {}) or {}
                for k, val in u_dict.items():
                    if any(w in k.lower() for w in ("name", "user", "surveyor")) and isinstance(val, str) and val.strip():
                        return val.strip()
        except Exception:
            pass
        for g_attr in ("user", "current_user", "username", "user_name", "surveyor"):
            g_val = getattr(g, g_attr, None)
            if isinstance(g_val, str) and g_val.strip():
                return g_val.strip()
            elif hasattr(g_val, "username") or hasattr(g_val, "name"):
                v = getattr(g_val, "full_name", None) or getattr(g_val, "name", None) or getattr(g_val, "username", None)
                if v and str(v).strip():
                    return str(v).strip()
        for k in ("full_name", "display_name", "real_name", "user_name", "username", "name", "surveyor_name", "surveyor", "user", "logged_in_user", "operator"):
            val = session.get(k)
            if isinstance(val, dict):
                for sk in ("full_name", "display_name", "name", "username", "user"):
                    if val.get(sk) and str(val.get(sk)).strip():
                        return str(val.get(sk)).strip()
            elif val and isinstance(val, str) and val.strip() and val.strip().lower() != "duty surveyor":
                return val.strip()
        for k, val in dict(session).items():
            kl = str(k).lower()
            if any(w in kl for w in ("user", "name", "surv")) and isinstance(val, str) and 2 <= len(val.strip()) <= 50:
                if not val.strip().isdigit() and val.strip().lower() != "duty surveyor":
                    return val.strip()
        st = load_mti_state()
        for log_list_key in ("logs", "events", "event_log", "survey_logs"):
            logs = st.get(log_list_key) or []
            for lg in logs:
                if isinstance(lg, dict):
                    for lk in ("surveyor", "surveyor_name", "user", "username", "author", "logged_by"):
                        lv = lg.get(lk)
                        if lv and str(lv).strip() and str(lv).strip().lower() != "duty surveyor":
                            return str(lv).strip()
    except Exception:
        pass
    return "Duty Surveyor"

def _resolve_fix_data(req, ledger):
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
        if k in ("unit_no", "fix_id") and matched:
            continue
        if v is not None and str(v).strip() != "":
            fix_data[k] = v
    if box_q and "design_box_id" not in fix_data:
        fix_data["design_box_id"] = box_q
        req_surv = str(req.get("surveyor_name") or "").strip()
    saved_surv = str(fix_data.get("surveyor_name") or fix_data.get("surveyor") or "").strip()
    cur_u = _get_current_user_display_name()
    if req_surv and req_surv.lower() != "duty surveyor":
        fix_data["surveyor_name"] = req_surv
    elif saved_surv and saved_surv.lower() != "duty surveyor":
        fix_data["surveyor_name"] = saved_surv
    else:
        fix_data["surveyor_name"] = cur_u
    return fix_data

@mti_bp.route('/whoami')
@login_required
def mti_whoami():
    return jsonify({"status": "ok", "user_name": _get_current_user_display_name()})

@mti_bp.after_request
def _mti_ensure_surveyor_saved(response):
    try:
        if request.method == 'POST' and any(p in request.path for p in ('add_fix', 'save_fix', 'edit_fix', 'update_fix')):
            s_name = str(request.form.get('surveyor_name') or _get_current_user_display_name()).strip()
            box_id = str(request.form.get('design_box_id') or request.form.get('box_id') or '').strip()
            if s_name:
                st = load_mti_state()
                ledger = st.get('ledger') or []
                changed = False
                for r in ledger:
                    if box_id and str(r.get('design_box_id', '')).upper() == box_id.upper():
                        r['surveyor_name'] = s_name
                        r['surveyor'] = s_name
                        changed = True
                    elif not r.get('surveyor_name') or str(r.get('surveyor_name')).strip().lower() == 'duty surveyor':
                        r['surveyor_name'] = s_name
                        changed = True
                if changed:
                    save_mti_state(st)
    except Exception:
        pass
    return response

@mti_bp.route('/verify_4panel', methods=['POST'])
@login_required
def verify_4panel():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    _load_setup_meta()
    st = load_mti_state()
    ledger = st.get("ledger", [])
    cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    req = request.get_json(silent=True) or request.form.to_dict()
    fix_data = _resolve_fix_data(req, ledger)

    sc_p1, sc_p2 = int(float(req.get("scale_p1") or 250)), int(float(req.get("scale_p2") or 75))
    inc_hist = _as_bool(req.get("include_history"), True)
    sh_cont, sh_snd = _as_bool(req.get("show_contours"), True), _as_bool(req.get("show_soundings"), True)
    c_int, s_spc = float(req.get("contour_interval") or 0.05), float(req.get("spot_spacing") or 2.0)

    _purge_cached_pdfs()

    if req.get('surveyor_name') or req.get('install_date'):
        for r in ledger:
            if str(r.get('design_box_id','')).upper() == str(fix_data.get('design_box_id','')).upper():
                if req.get('surveyor_name'): r['surveyor_name'] = str(req['surveyor_name']).strip()
                if req.get('install_date'): r['install_date'] = str(req['install_date']).strip()
        try: save_mti_state(st)
        except Exception: pass
    b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full = run_rov_4panel_verification(fix_data, cat_list, MTI_WS_DIR)
    png_b, _ = generate_a3_4panel_chart(b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full, MTI_WS_DIR, inc_hist, ledger, sc_p1, sc_p2, sh_cont, c_int, sh_snd, s_spc, save_pdf=False)
    rep_md = build_structured_report_markdown(metrics, inc_hist, ledger, sc_p1, sc_p2)

    cache_obj = {"fix_data": fix_data, "metrics": metrics, "report_md": rep_md, "scale_p1": sc_p1, "scale_p2": sc_p2, "include_history": inc_hist, "show_contours": sh_cont, "show_soundings": sh_snd, "contour_interval": c_int, "spot_spacing": s_spc}
    open(os.path.join(MTI_WS_DIR, "last_4panel_cache.json"), "w", encoding="utf-8").write(json.dumps(cache_obj, ensure_ascii=False))
    return jsonify({"status": "ok", "image_b64": base64.b64encode(png_b).decode("ascii"), "report_md": rep_md, "metrics": metrics})

def _load_4panel_cache():
    p = os.path.join(MTI_WS_DIR, "last_4panel_cache.json")
    if os.path.exists(p):
        try: return json.loads(open(p, "r", encoding="utf-8").read())
        except Exception: pass
    st = load_mti_state()
    return st.get("last_4panel") or {}

@mti_bp.route('/update_4panel_report', methods=['POST'])
@login_required
def update_4panel_report():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    last = _load_4panel_cache()
    req = request.get_json(silent=True) or request.form.to_dict()
    rep_md = str(req.get("report_md") or last.get("report_md") or "").strip()
    metrics = last.get("metrics") or {"location_id": "CR-A1_M15", "mattress_id": "#A046", "base_filename": "20261104_Mattress_CR-A1_M15_A046"}
    generate_a4_report_pdf(metrics, MTI_WS_DIR, rep_md)
    generate_editable_docx(metrics, rep_md, MTI_WS_DIR)
    last["report_md"] = rep_md
    open(os.path.join(MTI_WS_DIR, "last_4panel_cache.json"), "w", encoding="utf-8").write(json.dumps(last, ensure_ascii=False))
    return jsonify({"status": "ok", "base_filename": metrics.get("base_filename")})

@mti_bp.route('/upload_seabed', methods=['POST'])
@login_required
def upload_seabed():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req_json = request.get_json(silent=True) or {}
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(request.form.get("crossing_id") or req_json.get("crossing_id") or "CR-A1_L1").strip())
    fname = str(request.form.get("filename") or req_json.get("filename") or "").strip()
    pts_json = req_json.get("points_array")
    if pts_json and isinstance(pts_json, list) and len(pts_json) > 0:
        pts_arr = np.array(pts_json, dtype=float)[:, :3]
        pts_arr[:, 2] = np.where((pts_arr[:, 2] > 0) & (pts_arr[:, 2] < 500), -pts_arr[:, 2], pts_arr[:, 2])
    else:
        raw_txt = ""
        f = request.files.get("seabed_file")
        if f and f.filename:
            fname = f.filename
            raw_txt = f.read().decode("utf-8", errors="ignore")
        else:
            raw_txt = str(request.form.get("bathy_xyz_text") or req_json.get("bathy_xyz_text") or "")
        pts_arr = parse_bathy_xyz_text(raw_txt)
    if len(pts_arr) > 0:
        if len(pts_arr) > 2500:
            pts_arr = pts_arr[::max(1, len(pts_arr) // 2500)]
        np.save(os.path.join(MTI_WS_DIR, f"{xing_id}_seabed.npy"), pts_arr)
        if xing_id == "CR-A1_L1":
            np.save(os.path.join(MTI_WS_DIR, "CR-A1_L2_seabed.npy"), pts_arr)
        z_min, z_max = round(float(np.min(pts_arr[:, 2])), 2), round(float(np.max(pts_arr[:, 2])), 2)
        meta = _load_setup_meta()
        meta.setdefault("bathy", {})[xing_id] = {
            "filename": fname or f"{xing_id}_bathy.xyz",
            "points": int(len(pts_arr)),
            "z_min": z_min,
            "z_max": z_max,
            "pts_compact": np.round(pts_arr[::max(1, len(pts_arr) // 800)], 2).tolist()
        }
        _save_setup_meta(meta)
        _purge_cached_pdfs()
        return jsonify({"status": "ok", "crossing_id": xing_id, "filename": fname or f"{xing_id}_bathy.xyz", "points": int(len(pts_arr)), "z_min": z_min, "z_max": z_max})
    return jsonify({"status": "error", "message": "No valid E N Z bathy points found in file."}), 400

@mti_bp.route('/clear_seabed', methods=['POST'])
@login_required
def clear_seabed():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req = request.get_json(silent=True) or request.form.to_dict()
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(req.get("crossing_id") or "ALL").strip())
    meta = _load_setup_meta()
    for fn in os.listdir(MTI_WS_DIR):
        if fn.endswith("_seabed.npy") and (xing_id in ("ALL", "GLOBAL") or fn == f"{xing_id}_seabed.npy"):
            try: os.remove(os.path.join(MTI_WS_DIR, fn))
            except Exception: pass
    if xing_id in ("ALL", "GLOBAL"):
        meta["bathy"] = {}
    else:
        meta.get("bathy", {}).pop(xing_id, None)
    _save_setup_meta(meta)
    _purge_cached_pdfs()
    return jsonify({"status": "ok", "crossing_id": xing_id})

@mti_bp.route('/save_cad_bg', methods=['POST'])
@login_required
def save_cad_bg():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req_json = request.get_json(silent=True) or {}
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(request.form.get("crossing_id") or req_json.get("crossing_id") or "CR-A1_L1").strip())
    fname = str(request.form.get("filename") or req_json.get("filename") or "").strip()
    polylines = req_json.get("polylines_array")
    if not polylines or not isinstance(polylines, list):
        raw_txt = ""
        f = request.files.get("cad_file")
        if f and f.filename:
            fname = f.filename
            raw_txt = f.read().decode("utf-8", errors="ignore")
        else:
            raw_txt = str(request.form.get("cad_text") or req_json.get("cad_text") or "")
        polylines = parse_dxf_background(raw_txt)
        if not polylines and raw_txt.strip():
            cur_poly = []
            for ln in raw_txt.splitlines():
                nums = [float(m) for m in re.findall(r"[+-]?\d+(?:\.\d+)?", ln)]
                if len(nums) >= 2 and abs(nums[0]) > 50000 and abs(nums[1]) > 50000:
                    e, n = (nums[1], nums[0]) if (nums[1] < nums[0] and nums[0] > 1000000) else (nums[0], nums[1])
                    cur_poly.append([round(e, 3), round(n, 3)])
                elif len(cur_poly) >= 2:
                    polylines.append(cur_poly); cur_poly = []
            if len(cur_poly) >= 2:
                polylines.append(cur_poly)
    if polylines:
        open(os.path.join(MTI_WS_DIR, f"{xing_id}_cad_bg.json"), "w", encoding="utf-8").write(json.dumps(polylines))
        n_verts = sum(len(p) for p in polylines)
        meta = _load_setup_meta()
        meta.setdefault("cad", {})[xing_id] = {
            "filename": fname or f"{xing_id}.dxf",
            "polylines": polylines[:250],
            "poly_count": len(polylines),
            "vertices": n_verts
        }
        _save_setup_meta(meta)
        _purge_cached_pdfs()
        return jsonify({"status": "ok", "crossing_id": xing_id, "filename": fname or f"{xing_id}.dxf", "polylines": len(polylines), "vertices": n_verts})
    return jsonify({"status": "error", "message": "No valid DXF LWPOLYLINE/POLYLINE/LINE entities found."}), 400

@mti_bp.route('/clear_cad_bg', methods=['POST'])
@login_required
def clear_cad_bg():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req = request.get_json(silent=True) or request.form.to_dict()
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(req.get("crossing_id") or "CR-A1_L1").strip())
    p = os.path.join(MTI_WS_DIR, f"{xing_id}_cad_bg.json")
    if os.path.exists(p):
        try: os.remove(p)
        except Exception: pass
    meta = _load_setup_meta()
    meta.get("cad", {}).pop(xing_id, None)
    _save_setup_meta(meta)
    _purge_cached_pdfs()
    return jsonify({"status": "ok", "crossing_id": xing_id})

@mti_bp.route('/save_design_catalog', methods=['POST'])
@login_required
def save_design_catalog():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req = request.get_json(silent=True) or request.form.to_dict()
    xing_def = str(req.get("crossing_id") or "CR-A1_L1").strip()
    new_entries = []
    if req.get("box_id") and req.get("design_e") and req.get("design_n"):
        try:
            new_entries.append({
                "layer": xing_def,
                "name": str(req.get("box_id")).strip(),
                "design_e": round(float(req.get("design_e")), 3),
                "design_n": round(float(req.get("design_n")), 3),
                "bearing": round(float(req.get("bearing") or 195.854) % 360.0, 3)
            })
        except Exception:
            pass
    raw_txt = str(req.get("catalog_text") or "")
    f = request.files.get("catalog_file")
    if f and f.filename:
        raw_txt += "\n" + f.read().decode("utf-8", errors="ignore")
    if raw_txt.strip():
        new_entries.extend(parse_design_catalog_text(raw_txt, xing_def))
    if not new_entries:
        return jsonify({"status": "error", "message": "Provide a single Design Box or paste Crossing, Box_ID, E, N, Bearing lines."}), 400
    existing = {str(b.get("name")): b for b in load_custom_catalog(MTI_WS_DIR) if b.get("name")}
    for e in new_entries:
        existing[e["name"]] = e
    saved_list = list(existing.values())
    open(os.path.join(MTI_WS_DIR, "custom_design_catalog.json"), "w", encoding="utf-8").write(json.dumps(saved_list, indent=2))
    _purge_cached_pdfs()
    return jsonify({"status": "ok", "added": len(new_entries), "total_custom": len(saved_list)})

@mti_bp.route('/clear_design_catalog', methods=['POST'])
@login_required
def clear_design_catalog():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    p = os.path.join(MTI_WS_DIR, "custom_design_catalog.json")
    if os.path.exists(p):
        try: os.remove(p)
        except Exception: pass
    _purge_cached_pdfs()
    return jsonify({"status": "ok"})

@mti_bp.route('/setup_status')
@login_required
def mti_setup_status():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    meta = _load_setup_meta()
    cad_meta = meta.get("cad") or {}
    bathy_meta = meta.get("bathy") or {}

    locations_table = []
    for loc in AREA_LOCATIONS:
        c_info = cad_meta.get(loc) or {}
        cad_p = os.path.join(MTI_WS_DIR, f"{loc}_cad_bg.json")
        cad_loaded = os.path.exists(cad_p)
        cad_polys = c_info.get("poly_count", 0)
        if cad_loaded and not cad_polys:
            try:
                d = json.loads(open(cad_p, "r", encoding="utf-8").read())
                cad_polys = len(d.get("polylines", []) if isinstance(d, dict) else d)
            except Exception:
                pass
        b_info = bathy_meta.get(loc) or {}
        npy_p = os.path.join(MTI_WS_DIR, f"{loc}_seabed.npy")
        bathy_loaded = os.path.exists(npy_p)
        b_pts = b_info.get("points", 0)
        z_min, z_max = b_info.get("z_min", 0.0), b_info.get("z_max", 0.0)
        if bathy_loaded and not b_pts:
            try:
                arr = np.load(npy_p)
                b_pts = int(len(arr))
                if b_pts > 0:
                    z_min, z_max = round(float(np.min(arr[:, 2])), 2), round(float(np.max(arr[:, 2])), 2)
            except Exception:
                pass
        locations_table.append({
            "location": loc,
            "cad_loaded": bool(cad_loaded and cad_polys > 0),
            "cad_filename": c_info.get("filename") or (f"{loc}.dxf" if cad_loaded else "No CAD File"),
            "cad_polylines": int(cad_polys),
            "bathy_loaded": bool(bathy_loaded and b_pts > 0),
            "bathy_filename": b_info.get("filename") or (f"{loc}_bathy.xyz" if bathy_loaded else "No Bathy File"),
            "bathy_points": int(b_pts),
            "z_min": z_min,
            "z_max": z_max
        })

    base_cats = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    custom_cats = load_custom_catalog(MTI_WS_DIR)
    merged = {str(b.get("name") or b.get("design_box_id")): dict(b, source="CAD Default") for b in base_cats}
    for cb in custom_cats:
        merged[str(cb.get("name"))] = dict(cb, source="Custom Override")
    return jsonify({
        "status": "ok",
        "locations": locations_table,
        "custom_design_count": len(custom_cats),
        "catalog": list(merged.values())
    })

def _dl_4panel_file(kind, suffix, mime):
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    _load_setup_meta()
    cache = _load_4panel_cache()
    metrics = cache.get("metrics") or {"location_id": "CR-A1_M15", "mattress_id": "#A046", "base_filename": "20261104_Mattress_CR-A1_M15_A046"}
    base = str(request.args.get("file") or metrics.get("base_filename") or "20261104_Mattress_CR-A1_M15_A046").strip()
    p = os.path.join(MTI_WS_DIR, base + suffix)
    rep_md = cache.get("report_md") or ""
    if kind == "a3_pdf" and not os.path.exists(p):
        st = load_mti_state()
        ledger = st.get("ledger", [])
        cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
        fd = cache.get("fix_data") or (ledger[0] if ledger else {})
        b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full = run_rov_4panel_verification(fd, cat_list, MTI_WS_DIR)
        generate_a3_4panel_chart(b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full, MTI_WS_DIR, cache.get("include_history", True), ledger, cache.get("scale_p1", 250), cache.get("scale_p2", 75), cache.get("show_contours", True), cache.get("contour_interval", 0.05), cache.get("show_soundings", True), cache.get("spot_spacing", 2.0), save_pdf=True)
    elif kind == "a4_pdf" and not os.path.exists(p):
        generate_a4_report_pdf(metrics, MTI_WS_DIR, rep_md or None)
    elif kind == "docx" and not os.path.exists(p):
        generate_editable_docx(metrics, rep_md or build_structured_report_markdown(metrics), MTI_WS_DIR)
    return send_file(p, as_attachment=True, download_name=base + suffix, mimetype=mime)

@mti_bp.route('/download_a3_pdf')
@login_required
def download_a3_pdf(): return _dl_4panel_file("a3_pdf", ".pdf", "application/pdf")

@mti_bp.route('/download_a3_png')
@login_required
def download_a3_png(): return _dl_4panel_file("a3_png", ".png", "image/png")

@mti_bp.route('/download_a4_pdf')
@login_required
def download_a4_pdf(): return _dl_4panel_file("a4_pdf", "_A4_Report.pdf", "application/pdf")

@mti_bp.route('/download_docx')
@login_required
def download_docx(): return _dl_4panel_file("docx", "_Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

STUDIO_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>4-Panel Subsea Mattress Verification Studio | DP2 MMA Prestige</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css" rel="stylesheet">
  <style>
    body { background:#0f172a; color:#f8fafc; font-family:system-ui,-apple-system,sans-serif; }
    .studio-card { background:#1e293b; border:1px solid #334155; border-radius:8px; }
    #fpVisBox { background:#ffffff; color:#0f172a; height:555px; overflow-y:auto; white-space:pre-wrap; font-size:12.5px; line-height:1.45; }
    #fpMdBox { background:#0f172a; color:#38bdf8; height:555px; font-size:12px; }
  </style>
</head>
<body>
<div class="container-fluid py-2 px-3">
  <div class="d-flex flex-wrap justify-content-between align-items-center py-2 px-3 mb-2 rounded" style="background:#020617;border:1px solid #1e293b;">
    <div class="d-flex flex-wrap align-items-center gap-2">
      <span class="fw-bold text-info fs-6"><i class="fas fa-drafting-compass me-2"></i>Subsea Mattress 4-Panel Verification &amp; Submittal Studio</span>
      <span id="fpActiveFilename" class="badge bg-primary font-monospace">Loading...</span>
      <span id="fpBathyBadge" class="badge bg-secondary font-monospace">BATHY: CHECKING...</span>
    </div>
    <div class="d-flex flex-wrap gap-1 align-items-center">
      <a href="/mti/setup" target="_blank" class="btn btn-sm btn-outline-info fw-bold me-1"><i class="fas fa-sliders-h me-1"></i>Survey Setup (CAD / Design / Bathy)</a>
      <a id="dlA3Pdf" href="/mti/download_a3_pdf" class="btn btn-sm btn-danger fw-bold"><i class="fas fa-file-pdf me-1"></i>A3 Chart PDF</a>
      <a id="dlA3Png" href="/mti/download_a3_png" class="btn btn-sm btn-info text-dark fw-bold"><i class="fas fa-image me-1"></i>A3 PNG</a>
      <a id="dlA4Pdf" href="/mti/download_a4_pdf" class="btn btn-sm btn-warning text-dark fw-bold"><i class="fas fa-file-alt me-1"></i>A4 Report PDF</a>
      <a id="dlDocx" href="/mti/download_docx" class="btn btn-sm btn-primary fw-bold"><i class="fas fa-file-word me-1"></i>Editable Word (.docx)</a>
      <button type="button" class="btn btn-sm btn-outline-light ms-1" onclick="window.close()">Close</button>
    </div>
  </div>

  <div class="studio-card p-2 mb-2">
    <div class="row g-2 align-items-end">
      <div class="col-md-2 col-12">
        <label class="small fw-bold text-info">Ledger Switcher</label>
        <select id="ledgerSelect" class="form-select form-select-sm fw-bold bg-dark text-warning border-info" onchange="window.selectLedgerUnit(this.value)">
          {% for r in ledger %}
          <option value="{{ r.design_box_id }}" {% if r.design_box_id == init_box %}selected{% endif %}>
            #{{ r.unit_no }}: {{ r.design_box_id }} ({{ r.physical_tag }})
          </option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-1 col-6">
        <label class="small fw-bold text-light">Location ID</label>
        <input type="text" id="inpBoxId" class="form-control form-control-sm fw-bold" value="{{ init_box }}">
      </div>
      <div class="col-md-1 col-6">
        <label class="small fw-bold text-light">Mattress ID</label>
        <input type="text" id="inpTagId" class="form-control form-control-sm fw-bold" value="{{ init_tag }}">
      </div>
      <div class="col-md-2 col-6">
        <label class="small fw-bold text-info">Placement Date &amp; Time</label>
        <input type="text" id="inpInstallDate" class="form-control form-control-sm fw-bold bg-dark text-light border-info" value="{{ init_date }}" placeholder="YYYY-MM-DD HH:MM">
      </div>
      <div class="col-md-2 col-6">
        <label class="small fw-bold text-info">Surveyor Name</label>
        <input type="text" id="inpSurveyor" class="form-control form-control-sm fw-bold bg-dark text-warning border-info" value="{{ init_surveyor }}" placeholder="e.g. Abror / Roderick">
      </div>
      <div class="col-md-1 col-4">
        <label class="small fw-bold text-warning" title="Mattress Thickness (m)">Thick(m)</label>
        <input type="number" step="0.01" id="inpMatThick" class="form-control form-control-sm fw-bold bg-dark text-warning border-secondary" value="0.30">
      </div>
      <div class="col-md-1 col-4">
        <label class="small fw-bold text-light">P1 / P2</label>
        <div class="d-flex gap-1">
          <select id="fpScP1" class="form-select form-select-sm px-1" title="Panel 1 Scale"><option value="200">200</option><option value="250" selected>250</option><option value="300">300</option><option value="400">400</option><option value="500">500</option><option value="750">750</option><option value="1000">1000</option></select>
          <select id="fpScP2" class="form-select form-select-sm px-1" title="Panel 2 Scale"><option value="50">50</option><option value="75" selected>75</option><option value="100">100</option></select>
        </div>
      </div>
      <div class="col-md-1 col-4 d-flex flex-column justify-content-center">
        <div class="form-check form-switch mb-0"><input class="form-check-input" type="checkbox" id="fpSnd" checked><label class="form-check-label small" for="fpSnd">Snd</label></div>
        <div class="form-check form-switch mb-0"><input class="form-check-input" type="checkbox" id="fpCnt" checked><label class="form-check-label small" for="fpCnt">Cnt/Hist</label></div>
      </div>
      <div class="col-md-1 col-12">
        <button type="button" id="btnRefresh4P" class="btn btn-sm btn-success fw-bold w-100" onclick="window.runStudioVerify()"><i class="fas fa-sync-alt"></i> Render</button>
      </div>
    </div>
  </div>
  <div class="row g-2">
    <div class="col-lg-7">
      <div class="studio-card p-2 text-center position-relative" style="min-height:600px;display:flex;align-items:center;justify-content:center;">
        <div id="fpSpinner" class="position-absolute top-50 start-50 translate-middle badge bg-dark border border-info p-3 fs-6" style="display:none;z-index:10;">
          <i class="fas fa-spinner fa-spin text-info me-2"></i>Rendering ISO A3 4-Panel Chart...
        </div>
        <img id="fpPreviewImg" src="" class="img-fluid rounded bg-white" style="max-height:590px;" alt="ISO A3 4-Panel Chart Preview">
      </div>
    </div>
    <div class="col-lg-5">
      <div class="studio-card p-2 d-flex flex-column h-100">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="small fw-bold text-info"><i class="fas fa-edit me-1"></i>Editable ISO A4 &amp; Word (.docx) Report Studio</span>
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-outline-info active" id="tabVis" onclick="window.toggleFpTab(false)">Visual Editor</button>
            <button type="button" class="btn btn-outline-info" id="tabMd" onclick="window.toggleFpTab(true)">Markdown Source</button>
          </div>
        </div>
        <div id="fpVisBox" contenteditable="true" class="form-control mb-2"></div>
        <textarea id="fpMdBox" class="form-control font-monospace mb-2" style="display:none;"></textarea>
        <div class="d-flex align-items-center gap-2">
          <button type="button" class="btn btn-sm btn-primary fw-bold flex-grow-1" onclick="window.apply4PanelReportEdits()"><i class="fas fa-save me-1"></i>Apply Edits to A4 PDF &amp; Word (.docx)</button>
          <span id="fpEditMsg" class="small fw-bold text-warning"></span>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
const LEDGER_DATA = {{ ledger_json | safe }};
const INIT_PARAMS = new URLSearchParams(window.location.search);

window.selectLedgerUnit = function(boxId) {
  const row = LEDGER_DATA.find(r => r.design_box_id === boxId);
  if (row) {
    document.getElementById('inpBoxId').value = row.design_box_id || '';
    document.getElementById('inpTagId').value = row.physical_tag || '';
    if (document.getElementById('inpInstallDate')) document.getElementById('inpInstallDate').value = row.install_date || '';
    if (document.getElementById('inpSurveyor')) document.getElementById('inpSurveyor').value = '{{ init_surveyor }}';
  }
  window.runStudioVerify({ design_box_id: boxId });
};

window.toggleFpTab = function(showMd) {
  const vis = document.getElementById('fpVisBox'), md = document.getElementById('fpMdBox');
  if (showMd) { md.value = vis.innerText; vis.style.display = 'none'; md.style.display = 'block'; }
  else { vis.innerText = md.value; md.style.display = 'none'; vis.style.display = 'block'; }
  document.getElementById('tabVis').classList.toggle('active', !showMd);
  document.getElementById('tabMd').classList.toggle('active', showMd);
};

window.runStudioVerify = function(extra) {
  const payload = Object.assign({}, Object.fromEntries(INIT_PARAMS.entries()), extra || {});
  payload.design_box_id = (extra && extra.design_box_id) || document.getElementById('inpBoxId').value.trim();
  payload.physical_tag = document.getElementById('inpTagId').value.trim();
  if (document.getElementById('inpInstallDate')) payload.install_date = document.getElementById('inpInstallDate').value.trim();
  if (document.getElementById('inpSurveyor')) payload.surveyor_name = document.getElementById('inpSurveyor').value.trim();
  if (document.getElementById('inpMatThick')) payload.mat_thickness_m = document.getElementById('inpMatThick').value;
  if (document.getElementById('inpMatThick')) payload.mat_thickness_m = document.getElementById('inpMatThick').value;
  payload.scale_p1 = document.getElementById('fpScP1').value;
  payload.scale_p2 = document.getElementById('fpScP2').value;
  payload.show_soundings = document.getElementById('fpSnd').checked;
  payload.show_contours = document.getElementById('fpCnt').checked;
  payload.include_history = document.getElementById('fpCnt').checked;

  const btn = document.getElementById('btnRefresh4P'), sp = document.getElementById('fpSpinner');
  btn.disabled = true; sp.style.display = 'block';
  fetch('/mti/verify_4panel', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) })
    .then(r => r.json()).then(d => {
      btn.disabled = false; sp.style.display = 'none';
      if (d.status === 'ok') {
        document.getElementById('fpPreviewImg').src = 'data:image/png;base64,' + d.image_b64;
        document.getElementById('fpMdBox').value = d.report_md || '';
        document.getElementById('fpVisBox').innerText = d.report_md || '';
        if (d.metrics) {
          const fn = d.metrics.base_filename || 'Report';
          document.getElementById('fpActiveFilename').innerText = fn + '.pdf';
          document.getElementById('inpBoxId').value = d.metrics.location_id || '';
          document.getElementById('inpTagId').value = d.metrics.mattress_id || '';
          if (document.getElementById('inpInstallDate') && d.metrics.install_date) document.getElementById('inpInstallDate').value = d.metrics.install_date;
          if (document.getElementById('inpSurveyor') && d.metrics.surveyor_name) document.getElementById('inpSurveyor').value = d.metrics.surveyor_name;
          const bBadge = document.getElementById('fpBathyBadge');
          if (d.metrics.bathy_source === 'SURVEY_BATHY') {
            bBadge.innerText = 'BATHY: ' + d.metrics.bathy_count + ' PTS (' + d.metrics.bathy_z_min + 'm to ' + d.metrics.bathy_z_max + 'm)';
            bBadge.className = 'badge font-monospace bg-success';
          } else {
            bBadge.innerText = 'NO BATHY UPLOADED FOR ' + (d.metrics.crossing_id || 'AREA');
            bBadge.className = 'badge font-monospace bg-warning text-dark';
          }
          const ts = Date.now();
          document.getElementById('dlA3Pdf').href = '/mti/download_a3_pdf?file=' + encodeURIComponent(fn) + '&t=' + ts;
          document.getElementById('dlA3Png').href = '/mti/download_a3_png?file=' + encodeURIComponent(fn) + '&t=' + ts;
          document.getElementById('dlA4Pdf').href = '/mti/download_a4_pdf?file=' + encodeURIComponent(fn) + '&t=' + ts;
          document.getElementById('dlDocx').href = '/mti/download_docx?file=' + encodeURIComponent(fn) + '&t=' + ts;
        }
      }
    }).catch(err => { btn.disabled = false; sp.style.display = 'none'; alert('Render error: ' + err); });
};

window.apply4PanelReportEdits = function() {
  const md = document.getElementById('fpMdBox'), vis = document.getElementById('fpVisBox');
  const txt = (md.style.display !== 'none') ? md.value : vis.innerText;
  md.value = txt;
  const msg = document.getElementById('fpEditMsg');
  msg.innerText = 'Saving...';
  fetch('/mti/update_4panel_report', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ report_md: txt }) })
    .then(r => r.json()).then(d => { msg.innerText = 'Saved A4 PDF & Word!'; setTimeout(() => { msg.innerText = ''; }, 2500); });
};

document.addEventListener('DOMContentLoaded', function() {
  window.runStudioVerify();
});
</script>
</body>
</html>"""

SETUP_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>MTI Survey Setup: Area CAD &amp; Bathy Tables + Design Sheet</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css" rel="stylesheet">
  <style>
    body { background:#0f172a; color:#f8fafc; font-family:system-ui,-apple-system,sans-serif; }
    .setup-card { background:#1e293b; border:1px solid #334155; border-radius:8px; height:100%; }
    .loc-table th, .loc-table td { vertical-align:middle; padding:6px 8px; font-size:12px; }
  </style>
</head>
<body>
<div class="container-fluid py-3 px-3">
  <div class="d-flex flex-wrap justify-content-between align-items-center py-2 px-3 mb-2 rounded" style="background:#020617;border:1px solid #1e293b;">
    <div>
      <span class="fw-bold text-info fs-5"><i class="fas fa-sliders-h me-2"></i>MTI Survey Baseline Setup Manager</span>
      <span class="badge bg-secondary ms-2">1. Area / CAD Files Table  |  2. Design Center &amp; Bearing Sheet  |  3. Area / Bathy Files Table</span>
    </div>
    <div class="d-flex gap-2">
      <a href="/mti/studio" target="_blank" class="btn btn-sm btn-info text-dark fw-bold"><i class="fas fa-drafting-compass me-1"></i>Open 4-Panel Studio</a>
      <a href="/mti" class="btn btn-sm btn-outline-light fw-bold"><i class="fas fa-arrow-left me-1"></i>Back to MTI Dashboard</a>
    </div>
  </div>

  <!-- Live Action Banner -->
  <div id="globalToastBanner" class="alert alert-info py-2 px-3 mb-3 fw-bold small" style="display:none;"></div>

  <!-- Hidden Reusable File Inputs for Per-Row Table Uploads -->
  <input type="file" id="hiddenCadFilePicker" accept=".dxf,.txt,.csv" style="display:none;" onchange="window.handleRowCadUpload(this)">
  <input type="file" id="hiddenBathyFilePicker" accept=".xyz,.csv,.txt" style="display:none;" onchange="window.handleRowBathyUpload(this)">

  <div class="row g-3">
    <!-- CARD 1: CAD BACKGROUND TABLE BY LOCATION -->
    <div class="col-lg-4">
      <div class="setup-card p-3 d-flex flex-column">
        <div class="d-flex justify-content-between align-items-center border-bottom border-secondary pb-2 mb-2">
          <h6 class="fw-bold text-info mb-0"><i class="fas fa-layer-group me-2"></i>1. CAD Background Table (Area vs. CAD File)</h6>
          <span id="cadStatusBadge" class="badge bg-secondary">0 / 8 Loaded</span>
        </div>
        <p class="small text-secondary mb-2">Assign an ASCII <code>.dxf</code> file to each crossing location. Click <strong>Upload</strong> on any row to attach or replace that location's CAD background.</p>

        <div class="table-responsive rounded border border-secondary flex-grow-1" style="background:#0f172a;">
          <table class="table table-dark table-striped table-hover loc-table mb-0">
            <thead>
              <tr class="text-info">
                <th style="width:28%;">Area / Location</th>
                <th style="width:47%;">CAD File (.dxf)</th>
                <th style="width:25%;" class="text-end">Action</th>
              </tr>
            </thead>
            <tbody id="cadTableBody">
              <tr><td colspan="3" class="text-center text-secondary py-3">Loading locations...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- CARD 2: CENTER POINT & BEARING DESIGN INPUT (KEPT INTACT) -->
    <div class="col-lg-4">
      <div class="setup-card p-3 d-flex flex-column">
        <div class="d-flex justify-content-between align-items-center border-bottom border-secondary pb-2 mb-2">
          <h6 class="fw-bold text-warning mb-0"><i class="fas fa-crosshairs me-2"></i>2. Center Point &amp; Bearing Design Sheet</h6>
          <span id="desStatusBadge" class="badge bg-primary">139 Boxes</span>
        </div>
        <p class="small text-secondary mb-2">Add or override Mattress Design Box Center Coordinates (<code>E, N</code> in TWD97) and Design South Bearing (<code>deg</code>). Click any row below to edit.</p>

        <div class="row g-1 mb-2">
          <div class="col-4">
            <label class="small fw-bold text-light">Crossing ID</label>
            <input type="text" id="desXingId" class="form-control form-control-sm bg-dark text-light border-secondary fw-bold" value="CR-A1_L1">
          </div>
          <div class="col-4">
            <label class="small fw-bold text-light">Box Location ID</label>
            <input type="text" id="desBoxId" class="form-control form-control-sm bg-dark text-warning border-secondary fw-bold" placeholder="CR-A1_M15">
          </div>
          <div class="col-4">
            <label class="small fw-bold text-light">South Brg (deg)</label>
            <input type="number" step="0.001" id="desBrg" class="form-control form-control-sm bg-dark text-light border-secondary" placeholder="195.854">
          </div>
          <div class="col-6">
            <label class="small fw-bold text-light">Design Easting E (m)</label>
            <input type="number" step="0.001" id="desEast" class="form-control form-control-sm bg-dark text-light border-secondary" placeholder="194541.443">
          </div>
          <div class="col-6">
            <label class="small fw-bold text-light">Design Northing N (m)</label>
            <input type="number" step="0.001" id="desNorth" class="form-control form-control-sm bg-dark text-light border-secondary" placeholder="2702613.394">
          </div>
        </div>

        <div class="mb-2">
          <label class="small fw-bold text-light">Or Bulk Paste / Upload CSV (<code>Crossing_ID, Box_ID, Design_E, Design_N, Bearing</code>):</label>
          <textarea id="desBulkText" class="form-control form-control-sm font-monospace bg-dark text-warning border-secondary mb-1" rows="2" placeholder="CR-A1_L1, CR-A1_M15, 194541.443, 2702613.394, 195.861"></textarea>
          <input type="file" id="desFileInput" class="form-control form-control-sm bg-dark text-light border-secondary" accept=".csv,.txt">
        </div>

        <div class="d-flex gap-2 mb-2">
          <button type="button" id="btnSaveDes" class="btn btn-sm btn-warning text-dark fw-bold flex-grow-1" onclick="window.saveDesignCatalog()"><i class="fas fa-save me-1"></i>Save Design Box(es)</button>
          <button type="button" class="btn btn-sm btn-outline-danger fw-bold" onclick="window.clearDesignCatalog()" title="Reset custom overrides"><i class="fas fa-undo me-1"></i>Reset</button>
        </div>

        <div class="table-responsive rounded border border-secondary flex-grow-1" style="max-height:220px;overflow-y:auto;background:#0f172a;">
          <table class="table table-sm table-dark table-striped mb-0" style="font-size:11px;">
            <thead class="sticky-top bg-dark"><tr><th>Crossing</th><th>Box ID</th><th>Design E</th><th>Design N</th><th>Brg</th></tr></thead>
            <tbody id="desCatalogTbody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- CARD 3: PRE-SURVEY BATHY TABLE BY LOCATION -->
    <div class="col-lg-4">
      <div class="setup-card p-3 d-flex flex-column">
        <div class="d-flex justify-content-between align-items-center border-bottom border-secondary pb-2 mb-2">
          <h6 class="fw-bold text-success mb-0"><i class="fas fa-water me-2"></i>3. Bathy Soundings Table (Area vs. Bathy File)</h6>
          <span id="bathyStatusBadge" class="badge bg-secondary">0 / 8 Loaded</span>
        </div>
        <p class="small text-secondary mb-2">Assign a pre-survey <code>.xyz</code> / <code>.csv</code> bathy file to each location. Click <strong>Upload</strong> on any row to crop &amp; save real seabed soundings for that crossing.</p>

        <div class="table-responsive rounded border border-secondary flex-grow-1" style="background:#0f172a;">
          <table class="table table-dark table-striped table-hover loc-table mb-0">
            <thead>
              <tr class="text-success">
                <th style="width:28%;">Area / Location</th>
                <th style="width:47%;">Bathy File (.xyz / .csv)</th>
                <th style="width:25%;" class="text-end">Action</th>
              </tr>
            </thead>
            <tbody id="bathyTableBody">
              <tr><td colspan="3" class="text-center text-secondary py-3">Loading locations...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
window._catalogCache = [];
window._activeUploadLoc = 'CR-A1_L1';

window.showSetupBanner = function(msg, cls) {
  const el = document.getElementById('globalToastBanner');
  el.className = 'alert py-2 px-3 mb-3 fw-bold small ' + (cls || 'alert-info');
  el.innerHTML = msg;
  el.style.display = 'block';
};

window.getCrossingBounds = function(xingId) {
  const basePrefix = xingId.split('_')[0];
  let boxes = (window._catalogCache || []).filter(b => b.layer === xingId);
  if (!boxes.length) {
    boxes = (window._catalogCache || []).filter(b => String(b.layer || '').indexOf(basePrefix) === 0);
  }
  if (!boxes.length) return null;
  const es = boxes.map(b => Number(b.design_e));
  const ns = boxes.map(b => Number(b.design_n));
  return {
    eMin: Math.min.apply(null, es) - 90.0,
    eMax: Math.max.apply(null, es) + 90.0,
    nMin: Math.min.apply(null, ns) - 90.0,
    nMax: Math.max.apply(null, ns) + 90.0
  };
};

window.refreshSetupStatus = function() {
  fetch('/mti/setup_status').then(r => r.json()).then(d => {
    if (d.status !== 'ok') return;
    window._catalogCache = d.catalog || [];
    const locs = d.locations || [];

    // 1. Populate CAD Table (Column 1: Area/Location | Column 2: CAD File | Column 3: Upload/Clear)
    let cadLoadedCnt = 0;
    const cadTbody = document.getElementById('cadTableBody');
    cadTbody.innerHTML = locs.map(row => {
      if (row.cad_loaded) cadLoadedCnt += 1;
      const fileCell = row.cad_loaded
        ? ('<div class="fw-bold text-info text-truncate" style="max-width:190px;" title="' + row.cad_filename + '"><i class="fas fa-check-circle me-1"></i>' + row.cad_filename + '</div>' +
           '<small class="text-light">' + row.cad_polylines + ' polyline(s) active</small>')
        : '<span class="text-secondary"><i class="fas fa-minus-circle me-1"></i>No CAD file</span>';
      return (
        '<tr id="cadRow_' + row.location + '">' +
        '<td class="fw-bold text-warning font-monospace">' + row.location + '</td>' +
        '<td id="cadCell_' + row.location + '">' + fileCell + '</td>' +
        '<td class="text-end text-nowrap">' +
          '<button type="button" class="btn btn-xs btn-sm btn-info text-dark fw-bold py-0 px-2 me-1" onclick="window.triggerRowCadPicker(\'' + row.location + '\')"><i class="fas fa-upload me-1"></i>Upload</button>' +
          (row.cad_loaded ? ('<button type="button" class="btn btn-xs btn-sm btn-outline-danger py-0 px-2" onclick="window.clearCadBg(\'' + row.location + '\')" title="Remove CAD file"><i class="fas fa-trash"></i></button>') : '') +
        '</td></tr>'
      );
    }).join('');
    document.getElementById('cadStatusBadge').innerText = cadLoadedCnt + ' / ' + locs.length + ' Loaded';
    document.getElementById('cadStatusBadge').className = 'badge ' + (cadLoadedCnt > 0 ? 'bg-info text-dark' : 'bg-secondary');

    // 2. Populate Design Catalog Table
    const cat = d.catalog || [];
    document.getElementById('desStatusBadge').innerText = cat.length + ' Boxes (' + (d.custom_design_count || 0) + ' Custom)';
    const desTbody = document.getElementById('desCatalogTbody');
    desTbody.innerHTML = cat.map((b, idx) => (
      '<tr style="cursor:pointer;" onclick="window.fillDesignRowByIdx(' + idx + ')">' +
      '<td>' + b.layer + '</td><td class="fw-bold text-warning">' + b.name + '</td>' +
      '<td>' + Number(b.design_e).toFixed(3) + '</td><td>' + Number(b.design_n).toFixed(3) + '</td><td>' + Number(b.bearing).toFixed(2) + '&deg;</td></tr>'
    )).join('');

    // 3. Populate Bathy Table (Column 1: Area/Location | Column 2: Bathy File | Column 3: Upload/Clear)
    let bathyLoadedCnt = 0;
    const bathyTbody = document.getElementById('bathyTableBody');
    bathyTbody.innerHTML = locs.map(row => {
      if (row.bathy_loaded) bathyLoadedCnt += 1;
      const fileCell = row.bathy_loaded
        ? ('<div class="fw-bold text-success text-truncate" style="max-width:190px;" title="' + row.bathy_filename + '"><i class="fas fa-check-circle me-1"></i>' + row.bathy_filename + '</div>' +
           '<small class="text-light">' + row.bathy_points.toLocaleString() + ' pts | Z: ' + row.z_min + 'm to ' + row.z_max + 'm</small>')
        : '<span class="text-secondary"><i class="fas fa-minus-circle me-1"></i>No Bathy file</span>';
      return (
        '<tr id="bathyRow_' + row.location + '">' +
        '<td class="fw-bold text-warning font-monospace">' + row.location + '</td>' +
        '<td id="bathyCell_' + row.location + '">' + fileCell + '</td>' +
        '<td class="text-end text-nowrap">' +
          '<button type="button" class="btn btn-xs btn-sm btn-success fw-bold py-0 px-2 me-1" onclick="window.triggerRowBathyPicker(\'' + row.location + '\')"><i class="fas fa-upload me-1"></i>Upload</button>' +
          (row.bathy_loaded ? ('<button type="button" class="btn btn-xs btn-sm btn-outline-danger py-0 px-2" onclick="window.clearBathySetup(\'' + row.location + '\')" title="Remove Bathy file"><i class="fas fa-trash"></i></button>') : '') +
        '</td></tr>'
      );
    }).join('');
    document.getElementById('bathyStatusBadge').innerText = bathyLoadedCnt + ' / ' + locs.length + ' Loaded';
    document.getElementById('bathyStatusBadge').className = 'badge ' + (bathyLoadedCnt > 0 ? 'bg-success' : 'bg-secondary');
  });
};

window.fillDesignRowByIdx = function(idx) {
  const b = (window._catalogCache || [])[idx];
  if (!b) return;
  document.getElementById('desXingId').value = b.layer || '';
  document.getElementById('desBoxId').value = b.name || '';
  document.getElementById('desEast').value = b.design_e || '';
  document.getElementById('desNorth').value = b.design_n || '';
  document.getElementById('desBrg').value = b.bearing || '';
  window.showSetupBanner('Loaded <strong>' + b.name + '</strong> (' + b.layer + ') into Design Editor.', 'alert-warning');
};

window.triggerRowCadPicker = function(loc) {
  window._activeUploadLoc = loc;
  const picker = document.getElementById('hiddenCadFilePicker');
  picker.value = '';
  picker.click();
};

window.handleRowCadUpload = function(inputEl) {
  const f = inputEl.files && inputEl.files[0];
  if (!f) return;
  const loc = window._activeUploadLoc || 'CR-A1_L1';
  const cell = document.getElementById('cadCell_' + loc);
  if (cell) cell.innerHTML = '<span class="text-info"><i class="fas fa-spinner fa-spin me-1"></i>Uploading &amp; parsing ' + f.name + '...</span>';

  const fd = new FormData();
  fd.append('crossing_id', loc);
  fd.append('filename', f.name);
  fd.append('cad_file', f);

  fetch('/mti/save_cad_bg', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(d => {
      if (d.status === 'ok') {
        window.showSetupBanner('&#10004; Saved CAD file <strong>' + d.filename + '</strong> (' + d.polylines + ' polylines) for <strong>' + d.crossing_id + '</strong>!', 'alert-success');
      } else {
        window.showSetupBanner('CAD Upload Error (' + loc + '): ' + (d.message || 'Invalid DXF'), 'alert-danger');
      }
      window.refreshSetupStatus();
    })
    .catch(err => {
      window.showSetupBanner('CAD Upload Network Error: ' + err, 'alert-danger');
      window.refreshSetupStatus();
    });
};

window.clearCadBg = function(loc) {
  fetch('/mti/clear_cad_bg', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({crossing_id: loc}) })
    .then(() => {
      window.showSetupBanner('Cleared CAD file for <strong>' + loc + '</strong>.', 'alert-secondary');
      window.refreshSetupStatus();
    });
};

window.triggerRowBathyPicker = function(loc) {
  window._activeUploadLoc = loc;
  const picker = document.getElementById('hiddenBathyFilePicker');
  picker.value = '';
  picker.click();
};

window.parseXyzTextClientSide = function(rawText, xingId) {
  const bnd = window.getCrossingBounds(xingId);
  const allPts = [];
  const inBoxPts = [];
  const lines = rawText.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const s = lines[i].trim();
    if (!s) continue;
    const c0 = s.charCodeAt(0);
    if (c0 === 35 || c0 === 47 || c0 === 69 || c0 === 101 || c0 === 88 || c0 === 120) continue;
    const ps = s.replace(/[,;]/g, ' ').trim().split(/\s+/);
    if (ps.length < 3) continue;
    const v0 = parseFloat(ps[0]), v1 = parseFloat(ps[1]), v2 = parseFloat(ps[2]);
    if (isNaN(v0) || isNaN(v1) || isNaN(v2)) continue;
    let e = v0, n = v1, z = v2;
    if (ps.length >= 4 && Math.abs(v0) < 50000 && Math.abs(v1) > 100000 && Math.abs(v2) > 100000) {
      e = v1; n = v2; z = parseFloat(ps[3]);
    }
    if (Math.abs(e) < 50000 || Math.abs(n) < 50000 || isNaN(z)) continue;
    if (n < e && e > 1000000) { const t = e; e = n; n = t; }
    if (z > 0 && z < 500) z = -Math.abs(z);
    const pt = [Math.round(e * 1000) / 1000, Math.round(n * 1000) / 1000, Math.round(z * 1000) / 1000];
    allPts.push(pt);
    if (bnd && e >= bnd.eMin && e <= bnd.eMax && n >= bnd.nMin && n <= bnd.nMax) {
      inBoxPts.push(pt);
    }
  }
  const chosen = (inBoxPts.length >= 4) ? inBoxPts : allPts;
  const maxKeep = 2500;
  if (chosen.length > maxKeep) {
    const step = Math.ceil(chosen.length / maxKeep);
    const thinned = [];
    for (let j = 0; j < chosen.length; j += step) thinned.push(chosen[j]);
    return { points: thinned, totalRead: allPts.length, croppedCount: inBoxPts.length };
  }
  return { points: chosen, totalRead: allPts.length, croppedCount: inBoxPts.length };
};

window.handleRowBathyUpload = function(inputEl) {
  const f = inputEl.files && inputEl.files[0];
  if (!f) return;
  const loc = window._activeUploadLoc || 'CR-A1_L1';
  const cell = document.getElementById('bathyCell_' + loc);
  if (cell) cell.innerHTML = '<span class="text-warning"><i class="fas fa-spinner fa-spin me-1"></i>Reading &amp; cropping ' + f.name + '...</span>';

  const reader = new FileReader();
  reader.onload = function(evt) {
    const parsed = window.parseXyzTextClientSide(evt.target.result || '', loc);
    if (!parsed.points.length) {
      window.showSetupBanner('Bathy Error: No valid E N Z coordinates found in ' + f.name, 'alert-danger');
      window.refreshSetupStatus();
      return;
    }
    if (cell) cell.innerHTML = '<span class="text-info"><i class="fas fa-spinner fa-spin me-1"></i>Saving ' + parsed.points.length.toLocaleString() + ' pts...</span>';
    fetch('/mti/upload_seabed', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        crossing_id: loc,
        filename: f.name,
        points_array: parsed.points
      })
    }).then(r => r.json()).then(d => {
      if (d.status === 'ok') {
        window.showSetupBanner('&#10004; Saved Bathy file <strong>' + d.filename + '</strong> for <strong>' + d.crossing_id + '</strong> (' + d.points.toLocaleString() + ' pts | Z: ' + d.z_min + 'm to ' + d.z_max + 'm)!', 'alert-success');
      } else {
        window.showSetupBanner('Bathy Upload Error: ' + (d.message || 'Error'), 'alert-danger');
      }
      window.refreshSetupStatus();
    }).catch(err => {
      window.showSetupBanner('Bathy Upload Error: ' + err, 'alert-danger');
      window.refreshSetupStatus();
    });
  };
  reader.readAsText(f);
};

window.clearBathySetup = function(loc) {
  fetch('/mti/clear_seabed', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({crossing_id: loc}) })
    .then(() => {
      window.showSetupBanner('Cleared Bathy file for <strong>' + loc + '</strong>.', 'alert-secondary');
      window.refreshSetupStatus();
    });
};

window.saveDesignCatalog = function() {
  const btn = document.getElementById('btnSaveDes');
  btn.disabled = true;
  const fd = new FormData();
  fd.append('crossing_id', document.getElementById('desXingId').value);
  fd.append('box_id', document.getElementById('desBoxId').value);
  fd.append('design_e', document.getElementById('desEast').value);
  fd.append('design_n', document.getElementById('desNorth').value);
  fd.append('bearing', document.getElementById('desBrg').value);
  fd.append('catalog_text', document.getElementById('desBulkText').value);
  const f = document.getElementById('desFileInput').files[0];
  if (f) fd.append('catalog_file', f);
  fetch('/mti/save_design_catalog', { method: 'POST', body: fd }).then(r => r.json()).then(d => {
    btn.disabled = false;
    if (d.status === 'ok') {
      document.getElementById('desBulkText').value = '';
      window.showSetupBanner('&#10004; Saved ' + d.added + ' design box entry/entries!', 'alert-success');
      window.refreshSetupStatus();
    } else window.showSetupBanner(d.message || 'Error saving design catalog.', 'alert-danger');
  }).catch(() => { btn.disabled = false; });
};

window.clearDesignCatalog = function() {
  if (!confirm('Reset all custom design box overrides back to default CAD catalog?')) return;
  fetch('/mti/clear_design_catalog', { method: 'POST' }).then(() => {
    window.showSetupBanner('Reset design catalog to 139 CAD defaults.', 'alert-secondary');
    window.refreshSetupStatus();
  });
};

document.addEventListener('DOMContentLoaded', window.refreshSetupStatus);
</script>
</body>
</html>"""

@mti_bp.route('/studio')
@login_required
def mti_4panel_studio_window():
    st = load_mti_state()
    ledger = st.get("ledger", [])
    req = request.args.to_dict()
    fd = _resolve_fix_data(req, ledger)
    init_box = fd.get("design_box_id") or "CR-A1_M15"
    init_tag = fd.get("physical_tag") or "#A046"
    init_date = fd.get("install_date") or "2026-11-04 14:34"
    init_surveyor = str(req.get("surveyor_name") or _get_current_user_display_name()).strip()
    return render_template_string(STUDIO_HTML_TEMPLATE, ledger=ledger, ledger_json=json.dumps(ledger), init_box=init_box, init_tag=init_tag, init_date=init_date, init_surveyor=init_surveyor)

@mti_bp.route('/setup')
@login_required
def mti_survey_setup_window():
    return render_template_string(SETUP_HTML_TEMPLATE)
