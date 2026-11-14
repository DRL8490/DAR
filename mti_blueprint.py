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

def compute_4_corners(center_e, center_n, bearing_deg, length_m=6.0, width_m=3.0, default_z=0.0):
    b = float(bearing_deg or 195.854) % 360.0
    s_brg = (b + 180.0) % 360.0 if b < 180.0 else b
    az_rad = math.radians((s_brg - 180.0) % 360.0)
    sin_a, cos_a = math.sin(az_rad), math.cos(az_rad)
    dl, dw = length_m / 2.0, width_m / 2.0
    corners = {}
    for idx, (sl, sw) in enumerate([(+1, -1), (+1, +1), (-1, +1), (-1, -1)], start=1):
        corners[f"c{idx}_e"] = round(center_e + sl * dl * sin_a + sw * dw * cos_a, 3)
        corners[f"c{idx}_n"] = round(center_n + sl * dl * cos_a - sw * dw * sin_a, 3)
        corners[f"c{idx}_z"] = round(float(default_z or 0.0), 3)
    return corners

def _merged_cat_map():
    cm = {str(c["name"]).upper(): dict(c) for c in MATTRESS_CATALOG if c.get("name")}
    if "load_custom_catalog" in globals() and "MTI_WS_DIR" in globals():
        for cb in load_custom_catalog(MTI_WS_DIR):
            if cb.get("name"):
                cm[str(cb["name"]).upper()] = dict(cb)
    return cm

def _strip_auto_rem_tags(rem_raw):
    s = re.sub(r"^(?:\[(?:Survey Pole(?:\s+USBL)?|Vessel(?:\s+USBL)?|Vessel Nav \+ Pole Fix|USBL:[^\]]+)\]\s*)+", "", str(rem_raw or ""), flags=re.I).strip()
    return re.sub(r"(?:\s*\[(?:USBL:[^\]]*\|?\s*)?(?:Wind:[^\]]*|Curr:[^\]]*)\])+\s*$", "", s, flags=re.I).strip()

def _enrich_fix_row(r, cat_map, input_logs=None):
    d = dict(r)
    b_up = str(d.get("design_box_id") or "").strip().upper()
    cat_it = cat_map.get(b_up) or {}
    d["design_brg"] = round(float(d.get("design_brg") or cat_it.get("bearing") or d.get("heading_deg") or 195.854), 3)
    d["qaqc_e"] = d.get("qaqc_e") or d.get("aslaid_e") or d.get("design_e") or 0.0
    d["qaqc_n"] = d.get("qaqc_n") or d.get("aslaid_n") or d.get("design_n") or 0.0
    d["qaqc_brg"] = d.get("qaqc_brg") or d.get("heading_deg") or d["design_brg"]
    rem_raw = str(d.get("remarks") or "")
    if not d.get("usbl_sensor"):
        d["usbl_sensor"] = "Vessel" if "[vessel" in rem_raw.lower() else "Survey Pole"
    for key, pat in (("env_wind", r"Wind\s*:\s*([^\]|]+)"), ("env_current", r"Curr\s*:\s*([^\]|]+)")):
        if not d.get(key):
            m = re.search(pat, rem_raw, re.I)
            if m: d[key] = m.group(1).strip()
    g_lbl = str(d.get("gap_labels") or "")
    for q in ("nw", "ne", "sw", "se"):
        if not str(d.get(f"gap_{q}") or "").strip():
            mq = re.search(rf"\b{q.upper()}\s*:\s*([0-9.]+)", g_lbl, re.I)
            if mq: d[f"gap_{q}"] = mq.group(1)
    if not any(str(d.get(f"gap_{q}") or "").strip() for q in ("nw", "ne", "sw", "se")) and not d.get("is_first_in_array"):
        g1_v, g2_v = float(d.get("gap1_m") or 0.0), float(d.get("gap2_m") or 0.0)
        if g1_v > 0: d["gap_nw"] = f"{g1_v:.2f}"
        if g2_v > 0: d["gap_sw"] = f"{g2_v:.2f}"
    surv = str(d.get("surveyor_name") or d.get("surveyor") or "").strip()
    if not surv or surv.lower() == "duty surveyor":
        for lg in (input_logs or []):
            if str(lg.get("event_type") or "") == "Mattress fix" and b_up and b_up in str(lg.get("ref_id") or "").upper():
                cand = str(lg.get("surveyor") or "").strip()
                if cand and cand.lower() != "duty surveyor":
                    surv = cand
                    break
    d["surveyor_name"] = surv
    d["clean_remarks"] = _strip_auto_rem_tags(rem_raw)
    return d


DEFAULT_MTI_STATE = {
    "campaign_target_mattresses": 139,
    "campaign_target_rockbags": 28,
    "cl_tolerance_m": 0.50,
    "gap_tolerance_m": 0.50,
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
    ledger = [_enrich_fix_row(r, _merged_cat_map(), state.get("input_logs")) for r in sorted(state.get("ledger", []), key=lambda x: int(x.get("unit_no", 999)))]
    input_logs = sorted(state.get("input_logs", []), key=lambda x: str(x.get("timestamp", "")), reverse=True)

    target_matt = int(state.get("campaign_target_mattresses", 139))
    target_rb = int(state.get("campaign_target_rockbags", 28))
    cl_tol = float(state.get("cl_tolerance_m", 0.50))
    gap_tol = float(state.get("gap_tolerance_m", 0.50))

    completed_matt = sum(1 for r in ledger if r.get("status") == "Completed" and r.get("unit_type", "Concrete Mattress") == "Concrete Mattress")
    completed_rb = sum(1 for r in ledger if r.get("status") == "Completed" and r.get("unit_type") == "Rock Bag")
    in_prog_cnt = sum(1 for r in ledger if r.get("status") == "In Progress")
    tol_pass_cnt = sum(
        1 for r in ledger
        if r.get("status") == "Completed"
        and float(r.get("cl_offset_m", 0)) <= cl_tol
        and (bool(r.get("is_first_in_array")) or float(r.get("gap_m") or 0) <= gap_tol)
    )

    pct_matt = round((completed_matt / target_matt) * 100, 1) if target_matt else 0.0
    now_dt_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M')
    today_str = datetime.utcnow().strftime('%Y-%m-%d')


    return render_template(
        'mti_dashboard.html',
        ledger=ledger,
        ledger_json=json.dumps(ledger),
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
        catalog_json=json.dumps(list(_merged_cat_map().values()))
    )

@mti_bp.route('/add_fix', methods=['POST'])
@login_required
def add_fix():
    state = load_mti_state()
    ledger = state.get("ledger", [])
    cat_map = _merged_cat_map()

    fix_id = request.form.get("fix_id", type=int)
    unit_no = request.form.get("unit_no", type=int) or (max([int(r.get("unit_no", 0)) for r in ledger] + [0]) + 1)
    existing = next((r for r in ledger if int(r.get("id", 0)) == fix_id), None) if fix_id else None
    if not existing and not str(request.form.get("fix_id") or "").strip():
        if request.form.get("corners_ui_bound") != "1":
            existing = next((r for r in ledger if int(r.get("unit_no", 0)) == unit_no), None)
    ex = dict(existing) if existing else {}

    xing_id = (request.form.get("crossing_id") or ex.get("crossing_id") or "CR-A1_L1").strip()
    box_id = (request.form.get("design_box_id") or ex.get("design_box_id") or f"CR-A1_M{unit_no}").strip()
    tag_id = (request.form.get("physical_tag") or ex.get("physical_tag") or "").strip()
    cat_it = cat_map.get(box_id.upper()) or {}

    des_e = request.form.get("design_e", type=float)
    des_n = request.form.get("design_n", type=float)
    des_brg = request.form.get("design_brg", type=float)
    des_e = float(ex.get("design_e") or cat_it.get("design_e") or 0.0) if des_e is None else des_e
    des_n = float(ex.get("design_n") or cat_it.get("design_n") or 0.0) if des_n is None else des_n
    des_brg = float(ex.get("design_brg") or cat_it.get("bearing") or 195.854) if (des_brg is None or abs(des_brg) < 1e-6) else des_brg

    usbl_raw = (request.form.get("usbl_sensor") or ex.get("usbl_sensor") or "Survey Pole").strip()
    usbl_sensor = "Vessel" if ("vessel" in usbl_raw.lower() and "pole" not in usbl_raw.lower()) else ("Survey Pole" if "pole" in usbl_raw.lower() else usbl_raw)

    qaqc_e = request.form.get("qaqc_e", type=float) or float(ex.get("qaqc_e") or ex.get("aslaid_e") or des_e or 0.0)
    qaqc_n = request.form.get("qaqc_n", type=float) or float(ex.get("qaqc_n") or ex.get("aslaid_n") or des_n or 0.0)
    qaqc_brg = request.form.get("qaqc_brg", type=float) or float(ex.get("qaqc_brg") or ex.get("heading_deg") or des_brg)

    form_as_z = request.form.get("aslaid_z", type=float)
    prev_as_z = float(ex.get("aslaid_z") or 0.0)
    fallback_z = form_as_z if (form_as_z is not None and abs(form_as_z) > 1e-6) else prev_as_z

    pts = []
    for i in (1, 2, 3, 4):
        ce, cn, cz = request.form.get(f"c{i}_e", type=float), request.form.get(f"c{i}_n", type=float), request.form.get(f"c{i}_z", type=float)
        if ce and cn:
            pts.append((ce, cn, cz if (cz is not None and abs(cz) > 1e-6) else float(ex.get(f"c{i}_z") or fallback_z or 0.0)))

    if len(pts) != 4 and existing and request.form.get("corners_ui_bound") != "1":
        ex_pts = [(float(ex[f"c{i}_e"]), float(ex[f"c{i}_n"]), float(ex.get(f"c{i}_z") or fallback_z or 0.0)) for i in (1, 2, 3, 4) if ex.get(f"c{i}_e") and ex.get(f"c{i}_n")]
        if len(ex_pts) == 4:
            pts = ex_pts

    if len(pts) == 4:
        as_e = round(sum(p[0] for p in pts) / 4.0, 3)
        as_n = round(sum(p[1] for p in pts) / 4.0, 3)
        mean_cz = round(sum(p[2] for p in pts) / 4.0, 3)
        if form_as_z is not None and abs(form_as_z) > 1e-6 and abs(form_as_z - prev_as_z) > 1e-3 and abs(mean_cz - prev_as_z) <= 1e-2:
            as_z = round(form_as_z, 3)
            pts = [(p[0], p[1], as_z) for p in pts]
        else:
            as_z = mean_cz if abs(mean_cz) > 1e-6 else round(fallback_z, 3)
        be, bn = (pts[0][0] + pts[1][0]) / 2.0, (pts[0][1] + pts[1][1]) / 2.0
        fe, fn = (pts[2][0] + pts[3][0]) / 2.0, (pts[2][1] + pts[3][1]) / 2.0
        hdg = round((math.degrees(math.atan2(fe - be, fn - bn)) + 360.0) % 360.0, 3)
        hdg = round(hdg + 180.0, 3) if hdg < 180.0 else hdg
        corners = {f"c{i+1}_e": round(pts[i][0], 3) for i in range(4)}
        corners.update({f"c{i+1}_n": round(pts[i][1], 3) for i in range(4)})
        corners.update({f"c{i+1}_z": round(pts[i][2] if abs(pts[i][2]) > 1e-6 else as_z, 3) for i in range(4)})
    else:
        as_e = request.form.get("aslaid_e", type=float) or qaqc_e
        as_n = request.form.get("aslaid_n", type=float) or qaqc_n
        as_z = round(fallback_z, 3)
        hdg = round(request.form.get("heading_deg", type=float) or qaqc_brg or des_brg, 3)
        hdg = round(hdg + 180.0, 3) if hdg < 180.0 else hdg
        corners = compute_4_corners(as_e, as_n, hdg, 6.0, 3.0, as_z)

    cl_off = round(math.hypot(as_e - des_e, as_n - des_n), 2) if (as_e and des_e) else round(float(request.form.get("cl_offset_m", type=float) or 0.0), 2)

    gnw, gne, gsw, gse = [str(request.form.get(k) or "").strip() for k in ("gap_nw", "gap_ne", "gap_sw", "gap_se")]
    chk_first = str(request.form.get("is_first_in_array") or "").strip().lower() in ("true", "1", "on", "yes")
    is_first = chk_first or (unit_no == 1 and not any([gnw, gne, gsw, gse]))

    g_parts, g_vals = [], []
    if not is_first:
        for lbl, val in [("NW", gnw), ("NE", gne), ("SW", gsw), ("SE", gse)]:
            if val != "":
                try:
                    fv = round(float(val), 2)
                    g_parts.append(f"{lbl}:{fv:.2f}m"); g_vals.append(fv)
                except Exception:
                    pass
    if is_first:
        gnw, gne, gsw, gse = "", "", "", ""
        gap_labels, gap1, gap2, max_gap = "1st Unit (N/A)", 0.0, 0.0, 0.0
    elif g_vals:
        gap_labels = " | ".join(g_parts)
        gap1, gap2, max_gap = g_vals[0], (g_vals[1] if len(g_vals) > 1 else g_vals[0]), max(g_vals)
    else:
        gap1 = round(request.form.get("gap1_m", type=float) or float(ex.get("gap1_m") or 0.0), 2)
        gap2 = round(request.form.get("gap2_m", type=float) or float(ex.get("gap2_m") or 0.0), 2)
        max_gap = round(max(gap1, gap2), 2)
        prev_lbl = str(ex.get("gap_labels") or "").strip()
        gap_labels = prev_lbl if (prev_lbl and "1st unit" not in prev_lbl.lower() and max_gap > 0) else (f"G1:{gap1:.2f}m | G2:{gap2:.2f}m" if max_gap > 0 else "N/A")

    env_w = str(request.form.get("env_wind") if request.form.get("env_wind") is not None else ex.get("env_wind", "")).strip()
    env_c = str(request.form.get("env_current") if request.form.get("env_current") is not None else ex.get("env_current", "")).strip()
    env_s = str(request.form.get("env_swell") if request.form.get("env_swell") is not None else ex.get("env_swell", "")).strip()
    env_tag = " | ".join([f"{k}:{v}" for k, v in [("Wind", env_w), ("Curr", env_c)] if v])

    dt_str = (request.form.get("install_date") or ex.get("install_date") or datetime.utcnow().strftime('%Y-%m-%d %H:%M')).strip()
    cur_usr = _get_current_user_display_name() if "_get_current_user_display_name" in globals() else getattr(current_user, "name", "Duty Surveyor")
    surv_name = (request.form.get("surveyor_name") or ex.get("surveyor_name") or ex.get("surveyor") or cur_usr).strip()

    rem_str = _strip_auto_rem_tags(request.form.get("remarks") if request.form.get("remarks") is not None else ex.get("remarks", ""))
    if usbl_sensor: rem_str = f"[{usbl_sensor}] {rem_str}".strip()
    if env_tag: rem_str = f"{rem_str} [{env_tag}]".strip()

    entry = {
        "id": int(ex["id"]) if existing else (max([int(r.get("id", 0)) for r in ledger] + [0]) + 1),
        "unit_no": unit_no, "is_first_in_array": is_first, "unit_type": ex.get("unit_type") or "Concrete Mattress",
        "crossing_id": xing_id, "design_box_id": box_id, "physical_tag": tag_id,
        "install_date": dt_str, "usbl_sensor": usbl_sensor, "surveyor_name": surv_name, "surveyor": surv_name,
        "design_e": round(des_e, 3), "design_n": round(des_n, 3), "design_brg": round(des_brg, 3),
        "qaqc_e": round(qaqc_e or as_e, 3), "qaqc_n": round(qaqc_n or as_n, 3), "qaqc_brg": round(qaqc_brg or hdg, 3),
        "aslaid_e": round(as_e, 3), "aslaid_n": round(as_n, 3), "aslaid_z": round(as_z, 3),
        "cl_offset_m": round(cl_off, 2), "heading_deg": hdg, "brg_diff_deg": round(((hdg - des_brg + 180.0) % 360.0) - 180.0, 3),
        "gap_nw": gnw, "gap_ne": gne, "gap_sw": gsw, "gap_se": gse,
        "gap_labels": gap_labels, "gap1_m": gap1, "gap2_m": gap2, "gap_m": max_gap,
        "env_wind": env_w, "env_current": env_c, "env_swell": env_s,
        "status": request.form.get("status") or ex.get("status") or "Completed", "remarks": rem_str, **corners
    }
    if existing:
        ledger[ledger.index(existing)] = entry
    else:
        ledger.append(entry)
    state["ledger"] = ledger

    if not existing:
        input_logs = state.get("input_logs", [])
        input_logs.append({
            "id": max([int(x.get("id", 0)) for x in input_logs] + [0]) + 1,
            "event_type": "Mattress fix", "timestamp": dt_str, "surveyor": surv_name,
            "ref_id": f"{box_id} ({tag_id}) [{usbl_sensor}]",
            "val1": f"Act E:{as_e:.2f}, N:{as_n:.2f}, Z:{as_z:.2f} (dCL:{cl_off:.2f}m)",
            "val2": f"Brg:{hdg:.1f} deg | {gap_labels}", "remarks": rem_str
        })
        state["input_logs"] = input_logs

    if "_purge_cached_pdfs" in globals():
        try: _purge_cached_pdfs()
        except Exception: pass
    save_mti_state(state)
    flash(f"{'Updated' if existing else 'Saved'} Unit #{unit_no} ({box_id} / {tag_id}) via {usbl_sensor}!", "success")
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
    ledger = [_enrich_fix_row(r, _merged_cat_map(), state.get("input_logs")) for r in sorted(state.get("ledger", []), key=lambda x: int(x.get("unit_no", 999)))]
    input_logs = sorted(state.get("input_logs", []), key=lambda x: str(x.get("timestamp", "")), reverse=True)
    completed_matt = sum(1 for r in ledger if r.get("status") == "Completed" and r.get("unit_type", "Concrete Mattress") == "Concrete Mattress")
    return render_template('mti_mobile.html', ledger=ledger, ledger_json=json.dumps(ledger), input_logs=input_logs, completed_matt=completed_matt, target_matt=int(state.get("campaign_target_mattresses", 139)), cl_tol=float(state.get("cl_tolerance_m", 0.50)), gap_tol=float(state.get("gap_tolerance_m", 0.50)), catalog_json=json.dumps(list(_merged_cat_map().values())))


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
    if not st.get("gap_tol_050_v2") or abs(float(st.get("gap_tolerance_m") or 0.0) - 0.20) < 1e-6:
        st["gap_tolerance_m"] = 0.50
        if isinstance(st.get("survey_setup"), dict) and "gap_tolerance_m" in st["survey_setup"]:
            st["survey_setup"]["gap_tolerance_m"] = 0.50
        st["gap_tol_050_v2"] = True
        save_mti_state(st)
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
from mti_4panel_reports import build_structured_report_markdown, generate_a4_report_pdf, generate_editable_docx, generate_mti_dpr_pdf, extract_all_mti_logs, parse_log_entry_fields, norm_mti_date

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
    for p in glob.glob(os.path.join(MTI_WS_DIR, "*.pdf")) + glob.glob(os.path.join(MTI_WS_DIR, "*.dxf")):
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
    _purge_cached_pdfs()
    return jsonify({"status": "ok", "base_filename": metrics.get("base_filename")})

@mti_bp.route('/upload_seabed', methods=['POST'])
@login_required
def upload_seabed():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req_json = request.get_json(silent=True) or {}
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(request.form.get("crossing_id") or req_json.get("crossing_id") or "CR-A1_L1").strip())
    fname = str(request.form.get("filename") or req_json.get("filename") or "").strip()
    neg_flag = _as_bool(req_json.get("negate_z") if "negate_z" in req_json else request.form.get("negate_z"), False)
    pts_json = req_json.get("points_array")
    if pts_json and isinstance(pts_json, list) and len(pts_json) > 0:
        pts_arr = np.array(pts_json, dtype=float)[:, :3]
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
        if neg_flag:
            pts_arr[:, 2] = pts_arr[:, 2] * -1.0
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
            "negate_z": bool(neg_flag),
            "pts_compact": np.round(pts_arr[::max(1, len(pts_arr) // 800)], 2).tolist()
        }
        _save_setup_meta(meta)
        _purge_cached_pdfs()
        return jsonify({"status": "ok", "crossing_id": xing_id, "filename": fname or f"{xing_id}_bathy.xyz", "points": int(len(pts_arr)), "z_min": z_min, "z_max": z_max, "negate_z": bool(neg_flag)})
    return jsonify({"status": "error", "message": "No valid E N Z bathy points found in file."}), 400

@mti_bp.route('/negate_bathy_z', methods=['POST'])
@login_required
def negate_bathy_z():
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    req = request.get_json(silent=True) or request.form.to_dict()
    xing_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(req.get("crossing_id") or "CR-A1_L1").strip())
    neg_flag = _as_bool(req.get("negate_z"), False)
    meta = _load_setup_meta()
    b_info = meta.setdefault("bathy", {}).get(xing_id) or {}
    npy_p = os.path.join(MTI_WS_DIR, f"{xing_id}_seabed.npy")
    if not os.path.exists(npy_p):
        return jsonify({"status": "error", "message": f"No bathy file loaded for {xing_id}."}), 400
    arr = np.load(npy_p).astype(float)
    arr[:, 2] = arr[:, 2] * -1.0
    np.save(npy_p, arr)
    if xing_id == "CR-A1_L1" and os.path.exists(os.path.join(MTI_WS_DIR, "CR-A1_L2_seabed.npy")):
        np.save(os.path.join(MTI_WS_DIR, "CR-A1_L2_seabed.npy"), arr)
    z_min, z_max = round(float(np.min(arr[:, 2])), 2), round(float(np.max(arr[:, 2])), 2)
    b_info["z_min"] = z_min
    b_info["z_max"] = z_max
    b_info["negate_z"] = bool(neg_flag)
    b_info["pts_compact"] = np.round(arr[::max(1, len(arr) // 800)], 2).tolist()
    meta["bathy"][xing_id] = b_info
    _save_setup_meta(meta)
    _purge_cached_pdfs()
    return jsonify({"status": "ok", "crossing_id": xing_id, "negate_z": bool(neg_flag), "z_min": z_min, "z_max": z_max, "points": int(len(arr))})

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
            "negate_z": bool(b_info.get("negate_z", False)),
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
        generate_a3_4panel_chart(b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full, MTI_WS_DIR, cache.get("include_history", True), ledger, cache.get("scale_p1", 250), cache.get("scale_p2", 75), cache.get("show_contours", True), cache.get("contour_interval", 0.05), cache.get("show_soundings", True), cache.get("spot_spacing", 2.0), save_pdf=True, custom_report_md=rep_md or None)
    elif kind == "a4_pdf" and not os.path.exists(p):
        generate_a4_report_pdf(metrics, MTI_WS_DIR, rep_md or None)
    elif kind == "docx" and not os.path.exists(p):
        generate_editable_docx(metrics, rep_md or build_structured_report_markdown(metrics), MTI_WS_DIR)
    elif kind == "dxf" and not os.path.exists(p):
        from mti_dxf_export import generate_4panel_studio_dxf
        st = load_mti_state()
        ledger = st.get("ledger", [])
        cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
        fd = cache.get("fix_data") or (ledger[0] if ledger else {})
        b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full = run_rov_4panel_verification(fd, cat_list, MTI_WS_DIR)
        raw_store = load_raw_rov_store(st, MTI_WS_DIR, None, ledger, cat_list) if "load_raw_rov_store" in globals() else {}
        generate_4panel_studio_dxf(
            b_dict, metrics, c_xyz, xl, yl, zv, sb_loc, sb_full, MTI_WS_DIR,
            cache.get("include_history", True), ledger,
            cache.get("scale_p1", 250), cache.get("scale_p2", 75),
            cache.get("show_contours", True), cache.get("contour_interval", 0.05),
            cache.get("show_soundings", True), cache.get("spot_spacing", 2.0),
            custom_report_md=rep_md or None,
            cad_polys=metrics.get("cad_polylines") or [],
            raw_rov_store=raw_store
        )
        if not os.path.exists(p):
            alt_p = os.path.join(MTI_WS_DIR, str(metrics.get("base_filename") or "") + ".dxf")
            p = alt_p if os.path.exists(alt_p) else os.path.join(MTI_WS_DIR, "latest_A3_4Panel_Chart.dxf")
    return send_file(p, as_attachment=True, download_name=base + suffix, mimetype=mime)


def _collect_state_with_all_logs():
    st = dict(load_mti_state() or {})
    if not extract_all_mti_logs(st):
        for g_name, g_obj in list(globals().items()):
            if "log" in g_name.lower() and hasattr(g_obj, "query"):
                try:
                    rows = g_obj.query.all()
                    st["input_logs"] = [
                        {c.name: str(getattr(r, c.name) or "") for c in r.__table__.columns}
                        for r in rows if hasattr(r, "__table__")
                    ]
                    if st["input_logs"]:
                        break
                except Exception:
                    pass
    return st

@mti_bp.route('/dpr_dates')
@login_required
def mti_dpr_dates():
    st = _collect_state_with_all_logs()
    ledger = list(st.get("ledger") or [])
    raw_logs = extract_all_mti_logs(st)
    counts = {}
    for r in ledger:
        d = norm_mti_date(r.get("install_date"))
        if d:
            counts.setdefault(d, {"fixes": 0, "logs": 0})["fixes"] += 1
    for lg in raw_logs:
        d, _, _, _, _, _, _ = parse_log_entry_fields(lg)
        if d:
            counts.setdefault(d, {"fixes": 0, "logs": 0})["logs"] += 1
    active_dates = sorted(counts.keys(), reverse=True)
    from datetime import datetime as _dt
    latest_date = active_dates[0] if active_dates else _dt.utcnow().strftime("%Y-%m-%d")
    return jsonify({
        "status": "ok",
        "latest_date": latest_date,
        "active_dates": active_dates,
        "counts": counts,
        "total_logs": len(raw_logs),
        "user_name": _get_current_user_display_name()
    })

@mti_bp.route('/create_pdf_dpr')
@mti_bp.route('/create_pdf_dpr/<path:req_filename>')
@login_required
def create_pdf_dpr(req_filename=None):
    import io as _io
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    st = _collect_state_with_all_logs()
    dt_q = str(request.args.get("date") or "").strip()
    if not dt_q and req_filename:
        m_fn = re.search(r"(\d{8})", str(req_filename))
        if m_fn:
            dt_q = m_fn.group(1)
    surv_q = str(request.args.get("surveyor_name") or _get_current_user_display_name()).strip()
    pdf_bytes, fn_out, _ = generate_mti_dpr_pdf(st, target_date_str=dt_q, surveyor_name=surv_q, workspace_dir=MTI_WS_DIR)
    return send_file(_io.BytesIO(pdf_bytes), as_attachment=True, download_name=fn_out, mimetype="application/pdf")

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

@mti_bp.route('/download_dxf')
@login_required
def download_dxf(): return _dl_4panel_file("dxf", ".dxf", "application/dxf")

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
      <button type="button" id="btnOpenAdhocModal" class="btn btn-sm btn-warning text-dark fw-bold me-1" onclick="window.openAdhocStudio()" title="Open Ad-Hoc Gemini Context &amp; Python PDF Chart Generator"><i class="fas fa-terminal me-1"></i>Ad-Hoc PDF Script</button>
      <a id="dlA3Pdf" href="/mti/download_a3_pdf" class="btn btn-sm btn-danger fw-bold" title="Download 2-Page Landscape Print PDF (Page 1: A3 Chart + Page 2: A4 Report)"><i class="fas fa-print me-1"></i>Print PDF</a>
      <a id="dlA3Png" href="/mti/download_a3_png" class="btn btn-sm btn-info text-dark fw-bold"><i class="fas fa-image me-1"></i>A3 PNG</a>
      <a id="dlDxf" href="/mti/download_dxf" class="btn btn-sm btn-success fw-bold" title="Download CAD (.dxf) with TWD97 Model Space &amp; PDF-Matched Paper Space Layout"><i class="fas fa-layer-group me-1"></i>CAD (.dxf)</a>
      <a id="dlA4Pdf" href="/mti/download_a4_pdf" style="display:none;"></a>
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
          <i class="fas fa-spinner fa-spin text-info me-2"></i>Rendering 4-Panel Verification Chart...
        </div>
        <img id="fpPreviewImg" src="" class="img-fluid rounded bg-white" style="max-height:590px;" alt="ISO A3 4-Panel Chart Preview">
      </div>
    </div>
    <div class="col-lg-5">
      <div class="studio-card p-2 d-flex flex-column h-100">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="small fw-bold text-info"><i class="fas fa-edit me-1"></i>Editable Verification Report &amp; Word (.docx) Studio</span>
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-outline-info active" id="tabVis" onclick="window.toggleFpTab(false)">Visual Editor</button>
            <button type="button" class="btn btn-outline-info" id="tabMd" onclick="window.toggleFpTab(true)">Markdown Source</button>
          </div>
        </div>
        <div id="fpVisBox" contenteditable="true" class="form-control mb-2"></div>
        <textarea id="fpMdBox" class="form-control font-monospace mb-2" style="display:none;"></textarea>
        <div class="d-flex align-items-center gap-2">
          <button type="button" class="btn btn-sm btn-primary fw-bold flex-grow-1" onclick="window.apply4PanelReportEdits()"><i class="fas fa-save me-1"></i>Apply Edits to Print PDF &amp; Word (.docx)</button>
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
          if (document.getElementById('dlDxf')) document.getElementById('dlDxf').href = '/mti/download_dxf?file=' + encodeURIComponent(fn) + '&t=' + ts;
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
    .then(r => r.json()).then(d => { msg.innerText = 'Saved Print PDF & Word!'; setTimeout(() => { msg.innerText = ''; }, 2500); });
};

document.addEventListener('DOMContentLoaded', function() {
  window.runStudioVerify();
});
</script>

<!-- ADHOC_STUDIO_START -->
<style>
  #adhocModalOverlay {
    position: fixed; inset: 0; z-index: 9999; display: none;
    background: rgba(2, 6, 23, 0.92); backdrop-filter: blur(3px);
    padding: 12px; overflow-y: auto;
  }
  .adhoc-shell {
    background: #0f172a; border: 1px solid #334155; border-radius: 10px;
    max-width: 1760px; margin: 0 auto; min-height: calc(100vh - 26px);
    display: flex; flex-direction: column; box-shadow: 0 20px 50px rgba(0,0,0,0.75);
  }
  .adhoc-panel {
    background: #1e293b; border: 1px solid #334155; border-radius: 8px;
  }
  #adhocUserReqBox {
    background: #020617; color: #facc15; border: 1px solid #0284c7;
    font-size: 12.5px; line-height: 1.4;
  }
  #adhocContextBox {
    background: #020617; color: #cbd5e1; border: 1px solid #334155;
    font-size: 11.5px; line-height: 1.38; height: 390px; resize: vertical;
  }
  #adhocScriptBox {
    background: #020617; color: #38bdf8; border: 1px solid #334155;
    font-size: 12px; line-height: 1.42; height: 270px; resize: vertical;
    tab-size: 4;
  }
  #adhocConsoleBox {
    background: #020617; color: #e2e8f0; border: 1px solid #334155;
    font-size: 11.5px; max-height: 130px; overflow-y: auto; white-space: pre-wrap;
  }
</style>

<div id="adhocModalOverlay" role="dialog" aria-modal="true" aria-label="Ad-Hoc MTI PDF Chart Studio">
  <div class="adhoc-shell p-2 px-3">
    <div class="d-flex flex-wrap justify-content-between align-items-center pb-2 mb-2 border-bottom border-secondary">
      <div class="d-flex flex-wrap align-items-center gap-2">
        <span class="fw-bold text-warning fs-6"><i class="fas fa-terminal me-2"></i>Ad-Hoc MTI PDF Chart &amp; DPR Extraction Studio</span>
        <span class="badge bg-dark border border-info text-info font-monospace">1. Copy Context to Gemini -&gt; 2. Paste Python Script -&gt; 3. Generate PDF</span>
      </div>
      <div class="d-flex flex-wrap align-items-center gap-2">
        <select id="adhocSnippetSelect" class="form-select form-select-sm bg-dark text-warning border-secondary fw-bold" style="width:240px;" onchange="window.selectAdhocSnippet(this.value)">
          <option value="__STARTER__">-- Starter Summary Script --</option>
        </select>
        <button type="button" class="btn btn-sm btn-outline-light fw-bold" onclick="window.closeAdhocStudio()"><i class="fas fa-times me-1"></i>Close (Esc)</button>
      </div>
    </div>

    <div class="row g-2 flex-grow-1">
      <!-- LEFT COLUMN: GEMINI CONTEXT & REQUEST BUILDER -->
      <div class="col-lg-5 d-flex flex-column">
        <div class="adhoc-panel p-2 d-flex flex-column h-100">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <span class="small fw-bold text-info"><i class="fas fa-robot me-1"></i>Step 1: MTI Charting Context + DPR Extraction Request (Copy to Gemini)</span>
            <button type="button" class="btn btn-sm btn-outline-info py-0 px-2 fw-bold" onclick="window.loadAdhocContext(true)" title="Refresh live database counts and loaded bathy/CAD status"><i class="fas fa-sync-alt me-1"></i>Refresh DB Snapshot</button>
          </div>

          <label class="small fw-bold text-warning mb-1" for="adhocUserReqBox">What do you want to extract or plot from the DPR-MTI Module?</label>
          <textarea id="adhocUserReqBox" class="form-control form-control-sm font-monospace mb-2" rows="3" placeholder="Example: Plot an ISO A3 Landscape chart showing CR-A3 CAD &amp; bathy contours on the left, and a timeline of wind/current standby logs vs. mattresses placed on 2026-11-08 on the right." oninput="window.rebuildAdhocFullPrompt()"></textarea>

          <div class="d-flex justify-content-between align-items-center mb-1">
            <label class="small fw-bold text-light mb-0" for="adhocContextBox">Combined MTI Context + Request (Ready to Copy &amp; Paste into Gemini):</label>
            <span id="adhocCopyStatus" class="small fw-bold text-success"></span>
          </div>
          <textarea id="adhocContextBox" class="form-control font-monospace mb-2 flex-grow-1" spellcheck="false"></textarea>

          <button type="button" class="btn btn-sm btn-info text-dark fw-bold w-100 py-2" onclick="window.copyAdhocGeminiPrompt()">
            <i class="fas fa-copy me-1"></i>Copy Full Context + Request for Gemini
          </button>
        </div>
      </div>

      <!-- RIGHT COLUMN: PYTHON SCRIPT INPUT, PREVIEW & PDF DOWNLOAD -->
      <div class="col-lg-7 d-flex flex-column">
        <div class="adhoc-panel p-2 d-flex flex-column h-100">
          <div class="d-flex flex-wrap justify-content-between align-items-center mb-1 gap-1">
            <span class="small fw-bold text-warning"><i class="fas fa-code me-1"></i>Step 2: Paste Gemini Python Script &amp; Generate Ad-Hoc PDF</span>
            <div class="d-flex gap-1">
              <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2 text-light" onclick="window.pasteFromClipboardToScript()" title="Paste clipboard into script editor"><i class="fas fa-paste me-1"></i>Paste Code</button>
              <button type="button" class="btn btn-sm btn-outline-warning py-0 px-2" onclick="window.resetAdhocStarter()" title="Load starter example script">Reset Starter</button>
            </div>
          </div>

          <textarea id="adhocScriptBox" class="form-control font-monospace mb-2" spellcheck="false" placeholder="# Paste Python Matplotlib / PdfPages script from Gemini here..."></textarea>

                    <div class="row g-2 align-items-end mb-2">
            <div class="col-md-3 col-6">
              <label class="small fw-bold text-light">Optional PDF/DXF Name</label>
              <input type="text" id="adhocFilenameInp" class="form-control form-control-sm bg-dark text-light border-secondary font-monospace" placeholder="YYYYMMDD_MTI_Custom.pdf">
            </div>
            <div class="col-md-3 col-6">
              <label class="small fw-bold text-light">Save Reusable Snippet As</label>
              <input type="text" id="adhocSaveTitleInp" class="form-control form-control-sm bg-dark text-warning border-secondary" placeholder="Optional preset name">
            </div>
            <div class="col-md-2 col-4">
              <button type="button" id="btnRunAdhoc" class="btn btn-sm btn-success fw-bold w-100" onclick="window.runAdhocScript()">
                <i class="fas fa-play me-1"></i>Generate
              </button>
            </div>
            <div class="col-md-2 col-4">
              <a id="btnDlAdhocPdf" href="/mti/download_adhoc_pdf" target="_blank" class="btn btn-sm btn-danger fw-bold w-100 disabled" aria-disabled="true">
                <i class="fas fa-file-pdf me-1"></i>PDF
              </a>
            </div>
            <div class="col-md-2 col-4">
              <a id="btnDlAdhocDxf" href="/mti/download_adhoc_dxf" target="_blank" class="btn btn-sm btn-info text-dark fw-bold w-100 disabled" aria-disabled="true" title="Download TWD97 Model Space + Paper Space Layout DXF">
                <i class="fas fa-layer-group me-1"></i>CAD (.dxf)
              </a>
            </div>
          </div>

          <div id="adhocConsoleBox" class="rounded p-2 font-monospace mb-2">Ready. Click "Generate Ad-Hoc PDF" to run the script against live DPR-MTI data.</div>

          <div class="rounded border border-secondary bg-white text-center p-2 flex-grow-1 d-flex align-items-center justify-content-center position-relative" style="min-height:250px;">
            <span id="adhocEmptyPreviewMsg" class="text-secondary small fw-bold">Ad-Hoc PDF Page 1 Preview will appear here after execution.</span>
            <img id="adhocPreviewImg" src="" class="img-fluid rounded" style="max-height:300px;display:none;" alt="Ad-Hoc Chart Preview">
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
(function() {
  window._adhocBaseContext = '';
  window._adhocStarterScript = '';
  window._adhocSavedSnippets = [];

  function ensureAdhocTopButton() {
    if (document.getElementById('btnOpenAdhocModal')) return;
    const setupLink = document.querySelector('a[href="/mti/setup"]');
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'btnOpenAdhocModal';
    btn.className = 'btn btn-sm btn-warning text-dark fw-bold me-1';
    btn.innerHTML = '<i class="fas fa-terminal me-1"></i>Ad-Hoc PDF Script';
    btn.onclick = window.openAdhocStudio;
    if (setupLink && setupLink.parentNode) {
      setupLink.parentNode.insertBefore(btn, setupLink.nextSibling);
    }
  }

  window.rebuildAdhocFullPrompt = function() {
    const reqEl = document.getElementById('adhocUserReqBox');
    const ctxEl = document.getElementById('adhocContextBox');
    if (!ctxEl) return;
    const userReq = (reqEl && reqEl.value.trim())
      ? reqEl.value.trim()
      : '[Describe the chart, table, or data extraction you want from the DPR-MTI Module here]';
    ctxEl.value = (window._adhocBaseContext || 'Loading MTI context...') +
      '\n\n=== 5. SPECIFIC AD-HOC CHART / DPR-MTI EXTRACTION REQUEST ===\n' +
      userReq +
      '\n\nWrite ONLY the complete Python code using the pre-loaded DPR-MTI variables above, appending figure(s) to `OUTPUT_FIGS` and setting `OUTPUT_FILENAME`.';
  };

  function refreshSnippetDropdown(snips) {
    window._adhocSavedSnippets = snips || [];
    const sel = document.getElementById('adhocSnippetSelect');
    if (!sel) return;
    let html = '<option value="__STARTER__">-- Starter Summary Script --</option>';
    window._adhocSavedSnippets.forEach(function(s, idx) {
      const safeT = String(s.title || ('Snippet ' + (idx + 1))).replace(/</g, '&lt;');
      html += '<option value="' + idx + '">' + safeT + '</option>';
    });
    sel.innerHTML = html;
  }

  window.selectAdhocSnippet = function(val) {
    const codeEl = document.getElementById('adhocScriptBox');
    const fnEl = document.getElementById('adhocFilenameInp');
    if (!codeEl) return;
    if (val === '__STARTER__') {
      codeEl.value = window._adhocStarterScript || '';
      if (fnEl) fnEl.value = '';
      return;
    }
    const item = (window._adhocSavedSnippets || [])[ parseInt(val, 10) ];
    if (item) {
      codeEl.value = item.script_code || '';
      if (fnEl && item.filename) fnEl.value = item.filename;
    }
  };

  window.loadAdhocContext = function(forceReload) {
    if (window._adhocBaseContext && !forceReload) {
      window.rebuildAdhocFullPrompt();
      return;
    }
    fetch('/mti/adhoc_context')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d && d.status === 'ok') {
          window._adhocBaseContext = d.context_text || '';
          window._adhocStarterScript = d.starter_script || '';
          refreshSnippetDropdown(d.saved_snippets || []);
          const codeEl = document.getElementById('adhocScriptBox');
          if (codeEl && !codeEl.value.trim()) {
            codeEl.value = window._adhocStarterScript;
          }
          window.rebuildAdhocFullPrompt();
        }
      })
      .catch(function(err) {
        const ctxEl = document.getElementById('adhocContextBox');
        if (ctxEl) ctxEl.value = 'Error loading context: ' + err;
      });
  };

  window.openAdhocStudio = function() {
    const ov = document.getElementById('adhocModalOverlay');
    if (ov) ov.style.display = 'block';
    window.loadAdhocContext(false);
  };

  window.closeAdhocStudio = function() {
    const ov = document.getElementById('adhocModalOverlay');
    if (ov) ov.style.display = 'none';
  };

  window.copyAdhocGeminiPrompt = function() {
    const ctxEl = document.getElementById('adhocContextBox');
    const stEl = document.getElementById('adhocCopyStatus');
    if (!ctxEl) return;
    ctxEl.select();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(ctxEl.value).then(function() {
        if (stEl) { stEl.innerText = 'Copied! Paste into Gemini.'; setTimeout(function(){ stEl.innerText = ''; }, 3000); }
      });
    } else {
      document.execCommand('copy');
      if (stEl) { stEl.innerText = 'Copied! Paste into Gemini.'; setTimeout(function(){ stEl.innerText = ''; }, 3000); }
    }
  };

  window.pasteFromClipboardToScript = function() {
    const codeEl = document.getElementById('adhocScriptBox');
    if (navigator.clipboard && navigator.clipboard.readText && codeEl) {
      navigator.clipboard.readText().then(function(txt) {
        if (txt) codeEl.value = txt;
      }).catch(function() { codeEl.focus(); });
    }
  };

  window.resetAdhocStarter = function() {
    const codeEl = document.getElementById('adhocScriptBox');
    if (codeEl) codeEl.value = window._adhocStarterScript || '';
  };

  window.runAdhocScript = function() {
    const btn = document.getElementById('btnRunAdhoc');
    const con = document.getElementById('adhocConsoleBox');
    const img = document.getElementById('adhocPreviewImg');
    const emptyMsg = document.getElementById('adhocEmptyPreviewMsg');
    const dlBtn = document.getElementById('btnDlAdhocPdf');
    const survInp = document.getElementById('inpSurveyor');

    const payload = {
      script_code: document.getElementById('adhocScriptBox').value,
      filename: document.getElementById('adhocFilenameInp').value.trim(),
      save_title: document.getElementById('adhocSaveTitleInp').value.trim(),
      surveyor_name: survInp ? survInp.value.trim() : ''
    };

    btn.disabled = true;
    con.style.color = '#38bdf8';
    con.innerText = 'Executing Python script against live DPR-MTI data...';

    fetch('/mti/run_adhoc_chart', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      btn.disabled = false;
      if (d.status === 'ok') {
        con.style.color = '#4ade80';
        con.innerText = 'SUCCESS (' + d.page_count + ' page PDF): ' + d.filename + '\n' + (d.logs || '');
        if (d.image_b64) {
          img.src = 'data:image/png;base64,' + d.image_b64;
          img.style.display = 'inline-block';
          if (emptyMsg) emptyMsg.style.display = 'none';
        }
        if (dlBtn) {
          dlBtn.href = '/mti/download_adhoc_pdf/' + encodeURIComponent(d.filename) + '?t=' + Date.now();
          dlBtn.classList.remove('disabled');
          dlBtn.removeAttribute('aria-disabled');
        }
        const dlDxfBtn = document.getElementById('btnDlAdhocDxf');
        if (dlDxfBtn) {
          const dxfFn = d.dxf_filename || String(d.filename || 'latest_MTI_AdHoc_Chart.dxf').replace(/\.pdf$/i, '.dxf');
          dlDxfBtn.href = '/mti/download_adhoc_dxf/' + encodeURIComponent(dxfFn) + '?t=' + Date.now();
          dlDxfBtn.classList.remove('disabled');
          dlDxfBtn.removeAttribute('aria-disabled');
        }
        if (d.saved_snippets) {
          refreshSnippetDropdown(d.saved_snippets);
          document.getElementById('adhocSaveTitleInp').value = '';
        }
      } else {
        con.style.color = '#f87171';
        con.innerText = (d.message || 'Execution error') + '\n' + (d.logs || '');
      }
    })
    .catch(function(err) {
      btn.disabled = false;
      con.style.color = '#f87171';
      con.innerText = 'Network / Server Error: ' + err;
    });
  };

  document.addEventListener('keydown', function(ev) {
    if (ev.key === 'Escape') window.closeAdhocStudio();
  });

  function initAdhocBoot() {
    ensureAdhocTopButton();
    if (new URLSearchParams(window.location.search).get('adhoc') === '1') {
      window.openAdhocStudio();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdhocBoot);
  } else {
    initAdhocBoot();
  }
})();
</script>
<!-- ADHOC_STUDIO_END -->
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
      const negChecked = row.negate_z ? 'checked' : '';
      const negBoxHtml = '<div class="form-check d-inline-block me-2 align-middle" title="If checked, Z value of the loaded file is multiplied by -1">' +
        '<input class="form-check-input border-warning" type="checkbox" id="negZ_' + row.location + '" ' + negChecked + ' onchange="window.toggleRowNegateZ(\'' + row.location + '\', this.checked)">' +
        '<label class="form-check-label small text-warning fw-bold" for="negZ_' + row.location + '">Negate Z (&times;-1)</label></div>';
      return (
        '<tr id="bathyRow_' + row.location + '">' +
        '<td class="fw-bold text-warning font-monospace">' + row.location + '</td>' +
        '<td id="bathyCell_' + row.location + '">' + fileCell + '</td>' +
        '<td class="text-end text-nowrap">' +
          negBoxHtml +
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

window.toggleRowNegateZ = function(loc, isChecked) {
  const cell = document.getElementById('bathyCell_' + loc);
  if (!cell || cell.innerText.indexOf('No Bathy file') !== -1) return;
  fetch('/mti/negate_bathy_z', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ crossing_id: loc, negate_z: isChecked })
  }).then(r => r.json()).then(d => {
    if (d.status === 'ok') {
      window.showSetupBanner('&#10004; Negate Z (' + (isChecked ? 'ON' : 'OFF') + '): Multiplied Z by -1 for <strong>' + loc + '</strong> (New Z: ' + d.z_min + 'm to ' + d.z_max + 'm)', 'alert-info');
      window.refreshSetupStatus();
    }
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
    // Preserve raw Z sign from file; server applies negate_z if checked
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
        negate_z: !!(document.getElementById('negZ_' + loc) && document.getElementById('negZ_' + loc).checked),
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

<!-- RAW_ROV_PANEL4_START -->
<style>
  #rawRovPanel4Card {
    background: #161f2e; border: 1px solid #2a3950; border-radius: 10px;
    padding: 16px 18px; color: #e2e8f0; box-shadow: 0 8px 24px rgba(0,0,0,0.35);
  }
  #rawRovTextInp {
    background: #0b1120; color: #38bdf8; border: 1px solid #334155;
    font-size: 12px; line-height: 1.42; resize: vertical; tab-size: 12;
  }
  #rawRovTextInp::placeholder { color: #64748b; }
  #rawRovTargetBox {
    background: #0f172a; color: #facc15; border: 1px solid #334155; font-size: 12.5px;
  }
  .raw-rov-tbl {
    background: #1c2536; border: 1px solid #334155; border-radius: 6px; overflow: hidden;
  }
  .raw-rov-tbl thead th {
    background: #0f172a; color: #f8fafc; font-size: 12px; border-bottom: 1px solid #334155; padding: 8px 10px;
  }
  .raw-rov-tbl tbody td {
    border-color: #2d3748; padding: 8px 10px; vertical-align: middle; font-size: 12px; color: #e2e8f0;
  }
</style>

<div id="rawRovPanel4Mount" class="col-12 mt-3" style="display:none;">
  <div id="rawRovPanel4Card">
    <div class="d-flex flex-wrap justify-content-between align-items-center mb-1 gap-2">
      <div class="fw-bold" style="color:#22c55e;font-size:1.06rem;">
        <i class="fas fa-crosshairs me-2"></i>4. Raw ROV Points per As-Laid Mattress (Actual Unadjusted Fixes)
      </div>
      <span id="rawRovLoadedBadge" class="badge" style="background:#16a34a;font-size:12px;padding:5px 10px;">0 / 0 Loaded</span>
    </div>
    <div class="small mb-3" style="color:#94a3b8;">
      Store actual unadjusted ROV survey points per as-laid mattress separately from the post-processed 4-corner submittal ledger. Paste Excel or text rows (<code style="color:#f472b6;">Point_ID  E  N  Z</code>) or upload a <code style="color:#f472b6;">.txt</code> / <code style="color:#f472b6;">.csv</code> / <code style="color:#f472b6;">.xyz</code> file.
    </div>

    <div id="rawRovBanner" class="alert py-1 px-2 small fw-bold mb-2" style="display:none;"></div>

    <div class="row g-3">
      <div class="col-lg-5">
        <div class="p-2 rounded" style="background:#0f172a;border:1px solid #2d3748;">
          <label class="form-label small fw-bold text-info mb-1" for="rawRovTargetBox">Select As-Laid Mattress</label>
          <select id="rawRovTargetBox" class="form-select form-select-sm fw-bold font-monospace mb-1">
            <option value="__AUTO__">-- Auto-Detect Mattress from Point ID (Bulk Paste) --</option>
          </select>
          <div id="rawRovBoxHint" class="small font-monospace mb-2" style="color:#94a3b8;font-size:11px;">
            Bulk mode auto-matches IDs like CRA1M15_NW, C1_NW_A1M16, C1_NW_A3M18.
          </div>

          <div class="d-flex justify-content-between align-items-center mb-1">
            <label class="form-label small fw-bold text-light mb-0" for="rawRovTextInp">Raw ROV Coordinates (Point_ID, E, N, Z)</label>
            <button type="button" id="btnClearRawRovBox" class="btn btn-xs btn-sm btn-outline-secondary py-0 px-2 text-light" style="font-size:11px;">Clear Input</button>
          </div>
          <textarea id="rawRovTextInp" class="form-control form-control-sm font-monospace mb-2" rows="8" spellcheck="false" placeholder="CRA1M15_NW   194540.8   2702617   -54.615&#10;CRA1M15_NE   194543.7   2702616   -54.606&#10;CRA1M15_SW   194539.1   2702611   -54.643&#10;CRA1M15_SE   194542.0   2702610   -53.246"></textarea>

          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
            <div class="d-flex align-items-center gap-3">
              <div class="form-check mb-0" title="If checked, Z values are multiplied by -1">
                <input class="form-check-input border-warning" type="checkbox" id="rawRovNegateZ">
                <label class="form-check-label small text-warning fw-bold" for="rawRovNegateZ">Negate Z (&times;-1)</label>
              </div>
              <div class="form-check mb-0" title="Append points to existing mattress record instead of replacing">
                <input class="form-check-input border-info" type="checkbox" id="rawRovAppendMode">
                <label class="form-check-label small text-info fw-bold" for="rawRovAppendMode">Append</label>
              </div>
            </div>
            <div class="d-flex gap-1">
              <input type="file" id="rawRovFilePicker" accept=".txt,.csv,.xyz,.pts" style="display:none;">
              <button type="button" id="btnLoadRawRovFile" class="btn btn-sm btn-outline-info fw-bold py-1 px-2"><i class="fas fa-folder-open me-1"></i>Load File</button>
              <button type="button" id="btnSaveRawRov" class="btn btn-sm btn-success fw-bold py-1 px-3"><i class="fas fa-save me-1"></i>Save Raw ROV</button>
            </div>
          </div>
        </div>
      </div>

      <div class="col-lg-7">
        <div class="raw-rov-tbl table-responsive" style="max-height:345px;overflow-y:auto;">
          <table class="table table-dark table-hover table-sm mb-0">
            <thead>
              <tr>
                <th>As-Laid Mattress</th>
                <th>Raw ROV Points (Unadjusted)</th>
                <th class="text-end">Action</th>
              </tr>
            </thead>
            <tbody id="rawRovTableBody">
              <tr><td colspan="3" class="text-center text-secondary py-3">Loading raw ROV records...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
(function() {
  window._rawRovState = { store: {}, aslaid: [], catalog: [] };
  window._rawRovUploadBoxTarget = '';

  function escHtml(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function mountPanel4IntoSetupGrid() {
    const mountEl = document.getElementById('rawRovPanel4Mount');
    if (!mountEl) return;
    let bathyHeading = null;
    document.querySelectorAll('div, h5, h6, span').forEach(function(el) {
      if (!bathyHeading && el.children.length <= 2 && (el.textContent || '').indexOf('3. Bathy Soundings Table') !== -1) {
        bathyHeading = el;
      }
    });
    if (bathyHeading) {
      const col3 = bathyHeading.closest('[class*="col-"]');
      if (col3 && col3.parentNode) {
        col3.parentNode.appendChild(mountEl);
        mountEl.style.display = 'block';
        return;
      }
    }
    const mainCont = document.querySelector('.container-fluid, .container') || document.body;
    mainCont.appendChild(mountEl);
    mountEl.style.display = 'block';
  }

  function showRawBanner(htmlMsg, cls) {
    const b = document.getElementById('rawRovBanner');
    if (!b) return;
    b.className = 'alert py-1 px-2 small fw-bold mb-2 ' + (cls || 'alert-info');
    b.innerHTML = htmlMsg;
    b.style.display = 'block';
    setTimeout(function() { b.style.display = 'none'; }, 5500);
  }

  function renderRawRovUI() {
    const st = window._rawRovState;
    const store = st.store || {};
    const aslaid = st.aslaid || [];
    const cat = st.catalog || [];

    const loadedAslaid = aslaid.filter(function(u) { return !!store[u.box_id]; }).length;
    const extraKeys = Object.keys(store).filter(function(k) {
      return !aslaid.some(function(u) { return u.box_id === k; });
    });
    const badge = document.getElementById('rawRovLoadedBadge');
    if (badge) {
      badge.textContent = loadedAslaid + ' / ' + aslaid.length + ' Loaded' + (extraKeys.length ? (' (+' + extraKeys.length + ' staged)') : '');
    }

    const sel = document.getElementById('rawRovTargetBox');
    const prevVal = sel ? sel.value : '__AUTO__';
    if (sel) {
      let optHtml = '<option value="__AUTO__">-- Auto-Detect Mattress from Point ID (Bulk Paste) --</option>';
      if (aslaid.length > 0) {
        optHtml += '<optgroup label="As-Laid Mattresses (Installed Ledger)">';
        aslaid.forEach(function(u) {
          const bId = escHtml(u.box_id);
          const mark = store[u.box_id] ? (' [' + store[u.box_id].count + ' raw pts]') : ' [No raw pts]';
          optHtml += '<option value="' + bId + '">#' + escHtml(u.unit_no) + ': ' + bId + ' (' + escHtml(u.tag) + ')' + mark + '</option>';
        });
        optHtml += '</optgroup>';
      }
      if (cat.length > 0) {
        optHtml += '<optgroup label="All Design Mattress Boxes (139)">';
        cat.forEach(function(c) {
          const cName = escHtml(c.name);
          optHtml += '<option value="' + cName + '">' + cName + ' (' + escHtml(c.layer) + ')</option>';
        });
        optHtml += '</optgroup>';
      }
      sel.innerHTML = optHtml;
      if (Array.from(sel.options).some(function(o) { return o.value === prevVal; })) {
        sel.value = prevVal;
      }
    }

    const tbody = document.getElementById('rawRovTableBody');
    if (!tbody) return;
    const rowsToRender = [];
    aslaid.forEach(function(u) {
      rowsToRender.push({
        box_id: u.box_id,
        sub: '#' + u.unit_no + ' | ' + u.tag + ' | ' + (u.install_date || ''),
        rec: store[u.box_id] || null
      });
    });
    extraKeys.sort().forEach(function(k) {
      rowsToRender.push({
        box_id: k,
        sub: 'Staged Raw ROV',
        rec: store[k]
      });
    });

    if (rowsToRender.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" class="text-center text-secondary py-3">No as-laid mattresses or raw ROV fixes recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = rowsToRender.map(function(item) {
      const bId = escHtml(item.box_id);
      const rec = item.rec;
      let midCell = '<span class="text-secondary"><i class="fas fa-minus-circle me-1"></i>No Raw ROV points</span>';
      if (rec && rec.count > 0) {
        const cMap = rec.corners || {};
        const cSumm = ['NW', 'NE', 'SE', 'SW'].map(function(q) {
          return cMap[q] ? (q + ':' + Number(cMap[q].e).toFixed(1) + ',' + Number(cMap[q].n).toFixed(0)) : (q + ':-');
        }).join(' | ');
        midCell = '<div class="fw-bold" style="color:#22c55e;"><i class="fas fa-check-circle me-1"></i>' +
          rec.count + ' raw pts | Z: ' + Number(rec.z_min).toFixed(2) + 'm to ' + Number(rec.z_max).toFixed(2) + 'm</div>' +
          '<div class="font-monospace text-light" style="font-size:10.8px;opacity:0.88;">' + escHtml(cSumm) + '</div>';
      }
      const delBtn = rec
        ? ('<button type="button" class="btn btn-xs btn-sm btn-outline-danger py-0 px-2 js-raw-del" data-box="' + bId + '" title="Remove raw ROV points"><i class="fas fa-trash"></i></button>')
        : '';
      return (
        '<tr>' +
          '<td><div class="fw-bold text-warning font-monospace">' + bId + '</div>' +
          '<div class="text-secondary" style="font-size:10.8px;">' + escHtml(item.sub) + '</div></td>' +
          '<td>' + midCell + '</td>' +
          '<td class="text-end text-nowrap">' +
            '<button type="button" class="btn btn-xs btn-sm btn-outline-info fw-bold py-0 px-2 me-1 js-raw-edit" data-box="' + bId + '" title="Load into input box to inspect or edit">Edit</button>' +
            '<button type="button" class="btn btn-xs btn-sm btn-success fw-bold py-0 px-2 me-1 js-raw-upload" data-box="' + bId + '" title="Upload .txt/.csv/.xyz raw ROV file"><i class="fas fa-upload me-1"></i>Upload</button>' +
            delBtn +
          '</td>' +
        '</tr>'
      );
    }).join('');
  }

  function onTargetChange(val) {
    const hint = document.getElementById('rawRovBoxHint');
    const inp = document.getElementById('rawRovTextInp');
    if (val === '__AUTO__') {
      if (hint) hint.textContent = 'Bulk mode auto-matches IDs like CRA1M15_NW, C1_NW_A1M16, C1_NW_A3M18.';
      return;
    }
    const rec = (window._rawRovState.store || {})[val];
    const asl = (window._rawRovState.aslaid || []).find(function(u) { return u.box_id === val; });
    if (rec && rec.raw_text && inp) {
      inp.value = rec.raw_text;
    }
    if (hint) {
      hint.textContent = (asl ? ('Ledger center: E ' + Number(asl.aslaid_e || 0).toFixed(3) + ', N ' + Number(asl.aslaid_n || 0).toFixed(3) + ' | ') : '') +
        (rec ? ('Stored Raw ROV: ' + rec.count + ' pts (Updated ' + (rec.updated_at || '') + ')') : ('No raw ROV points saved yet for ' + val + '. Paste E, N, Z lines below.'));
    }
  }

  function refreshRawRovStatus() {
    fetch('/mti/raw_rov_status')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d && d.status === 'ok') {
          window._rawRovState.store = d.raw_rov_points || {};
          window._rawRovState.aslaid = d.aslaid_units || [];
          window._rawRovState.catalog = d.catalog_boxes || [];
          renderRawRovUI();
        }
      })
      .catch(function() {});
  }

  function submitRawRovPayload(rawText, targetBox) {
    const btn = document.getElementById('btnSaveRawRov');
    if (btn) btn.disabled = true;
    fetch('/mti/save_raw_rov', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        raw_text: rawText,
        target_box_id: targetBox,
        negate_z: !!(document.getElementById('rawRovNegateZ') && document.getElementById('rawRovNegateZ').checked),
        append_mode: !!(document.getElementById('rawRovAppendMode') && document.getElementById('rawRovAppendMode').checked)
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (btn) btn.disabled = false;
      if (d && d.status === 'ok') {
        showRawBanner('&#10004; Saved Raw ROV fixes for: <strong>' + escHtml((d.updated_boxes || []).join(', ')) + '</strong>', 'alert-success');
        refreshRawRovStatus();
      } else {
        showRawBanner(escHtml((d && d.message) || 'Could not parse valid TWD97 E/N points.'), 'alert-danger');
      }
    })
    .catch(function(err) {
      if (btn) btn.disabled = false;
      showRawBanner('Network error saving Raw ROV points: ' + escHtml(err), 'alert-danger');
    });
  }

  function bindPanel4Events() {
    const sel = document.getElementById('rawRovTargetBox');
    if (sel) sel.addEventListener('change', function() { onTargetChange(sel.value); });

    const btnClr = document.getElementById('btnClearRawRovBox');
    if (btnClr) btnClr.addEventListener('click', function() {
      const inp = document.getElementById('rawRovTextInp');
      if (inp) inp.value = '';
    });

    const picker = document.getElementById('rawRovFilePicker');
    const btnLoad = document.getElementById('btnLoadRawRovFile');
    if (btnLoad && picker) {
      btnLoad.addEventListener('click', function() {
        window._rawRovUploadBoxTarget = sel ? sel.value : '__AUTO__';
        picker.click();
      });
      picker.addEventListener('change', function() {
        const f = picker.files && picker.files[0];
        if (!f) return;
        const reader = new FileReader();
        reader.onload = function(ev) {
          const txt = String(ev.target.result || '');
          const inp = document.getElementById('rawRovTextInp');
          if (inp) inp.value = txt;
          const tBox = window._rawRovUploadBoxTarget || (sel ? sel.value : '__AUTO__');
          submitRawRovPayload(txt, tBox);
          picker.value = '';
        };
        reader.readAsText(f);
      });
    }

    const btnSave = document.getElementById('btnSaveRawRov');
    if (btnSave) {
      btnSave.addEventListener('click', function() {
        const inp = document.getElementById('rawRovTextInp');
        const txt = (inp ? inp.value : '').trim();
        if (!txt) {
          showRawBanner('Please paste Raw ROV coordinates (Point_ID, E, N, Z) before saving.', 'alert-warning');
          return;
        }
        submitRawRovPayload(txt, sel ? sel.value : '__AUTO__');
      });
    }

    const tbody = document.getElementById('rawRovTableBody');
    if (tbody) {
      tbody.addEventListener('click', function(ev) {
        const editBtn = ev.target.closest('.js-raw-edit');
        if (editBtn) {
          const bId = editBtn.getAttribute('data-box') || '';
          if (sel && bId) {
            sel.value = bId;
            onTargetChange(bId);
          }
          const inp = document.getElementById('rawRovTextInp');
          if (inp) inp.focus();
          return;
        }
        const upBtn = ev.target.closest('.js-raw-upload');
        if (upBtn && picker) {
          const bId = upBtn.getAttribute('data-box') || '';
          window._rawRovUploadBoxTarget = bId;
          if (sel && bId) sel.value = bId;
          picker.click();
          return;
        }
        const delBtn = ev.target.closest('.js-raw-del');
        if (delBtn) {
          const bId = delBtn.getAttribute('data-box') || '';
          if (!bId || !confirm('Remove stored Raw ROV points for ' + bId + '? (Post-processed submittal ledger will NOT be affected.)')) return;
          fetch('/mti/delete_raw_rov', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ box_id: bId })
          })
          .then(function(r) { return r.json(); })
          .then(function(d) {
            if (d && d.status === 'ok') {
              showRawBanner('Removed Raw ROV points for <strong>' + escHtml(bId) + '</strong>.', 'alert-info');
              refreshRawRovStatus();
            }
          });
        }
      });
    }
  }

  function bootPanel4() {
    mountPanel4IntoSetupGrid();
    bindPanel4Events();
    refreshRawRovStatus();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootPanel4);
  } else {
    bootPanel4();
  }
})();
</script>
<!-- RAW_ROV_PANEL4_END -->
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

# --- AD-HOC GEMINI CONTEXT & PYTHON PDF CHART ENGINE ROUTES ---
from mti_adhoc import STARTER_ADHOC_SCRIPT, build_adhoc_gemini_context, execute_adhoc_chart_script

@mti_bp.route('/adhoc_context')
@login_required
def mti_adhoc_context():
    _load_setup_meta()
    st = _collect_state_with_all_logs() if '_collect_state_with_all_logs' in globals() else load_mti_state()
    cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    surv_name = _get_current_user_display_name() if '_get_current_user_display_name' in globals() else 'Duty Surveyor'
    ctx_text = build_adhoc_gemini_context(st, cat_list, MTI_WS_DIR, surv_name)
    saved_snippets = list((st or {}).get("adhoc_snippets") or [])
    return jsonify({
        "status": "ok",
        "context_text": ctx_text,
        "starter_script": STARTER_ADHOC_SCRIPT,
        "saved_snippets": saved_snippets,
        "surveyor_name": surv_name
    })

@mti_bp.route('/run_adhoc_chart', methods=['POST'])
@login_required
def mti_run_adhoc_chart():
    _load_setup_meta()
    req = request.get_json(silent=True) or request.form.to_dict()
    script_code = str(req.get("script_code") or "").strip()
    custom_fn = str(req.get("filename") or "").strip()
    save_title = str(req.get("save_title") or "").strip()

    st = _collect_state_with_all_logs() if '_collect_state_with_all_logs' in globals() else load_mti_state()
    cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    surv_name = str(req.get("surveyor_name") or (_get_current_user_display_name() if '_get_current_user_display_name' in globals() else 'Duty Surveyor')).strip()

    res = execute_adhoc_chart_script(
        script_code=script_code,
        st_data=st,
        catalog_list=cat_list,
        workspace_dir=MTI_WS_DIR,
        surveyor_name=surv_name,
        custom_filename=custom_fn
    )

    if res.get("status") == "ok" and save_title:
        try:
            st_save = load_mti_state()
            snips = list(st_save.get("adhoc_snippets") or [])
            snips = [s for s in snips if s.get("title") != save_title]
            snips.insert(0, {"title": save_title, "script_code": script_code, "filename": res.get("filename", "")})
            st_save["adhoc_snippets"] = snips[:20]
            save_mti_state(st_save)
            res["saved_snippets"] = st_save["adhoc_snippets"]
        except Exception:
            pass
    return jsonify(res)

@mti_bp.route('/download_adhoc_pdf')
@mti_bp.route('/download_adhoc_pdf/<path:req_fn>')
@login_required
def mti_download_adhoc_pdf(req_fn=None):
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    fn = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(str(req_fn or request.args.get("file") or "latest_MTI_AdHoc_Chart.pdf")))
    p = os.path.join(MTI_WS_DIR, fn)
    if not os.path.exists(p):
        p = os.path.join(MTI_WS_DIR, "latest_MTI_AdHoc_Chart.pdf")
    return send_file(p, as_attachment=True, download_name=fn, mimetype="application/pdf")

@mti_bp.route('/download_adhoc_dxf')
@mti_bp.route('/download_adhoc_dxf/<path:req_fn>')
@login_required
def mti_download_adhoc_dxf(req_fn=None):
    os.makedirs(MTI_WS_DIR, exist_ok=True)
    fn = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(str(req_fn or request.args.get("file") or "latest_MTI_AdHoc_Chart.dxf")))
    if fn.lower().endswith(".pdf"):
        fn = fn[:-4] + ".dxf"
    p = os.path.join(MTI_WS_DIR, fn)
    if not os.path.exists(p):
        p = os.path.join(MTI_WS_DIR, "latest_MTI_AdHoc_Chart.dxf")
    return send_file(p, as_attachment=True, download_name=fn, mimetype="application/dxf")

# --- PANEL 4: RAW ROV POINTS PER AS-LAID MATTRESS ROUTES ---
from mti_raw_rov import load_raw_rov_store, save_raw_rov_store, parse_and_merge_raw_rov_text

@mti_bp.route('/raw_rov_status')
@login_required
def mti_raw_rov_status():
    st = load_mti_state()
    ledger = list((st or {}).get("ledger") or [])
    cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    store = load_raw_rov_store(st, MTI_WS_DIR, save_mti_state, ledger, cat_list)

    aslaid_units = []
    for idx, r in enumerate(sorted(ledger, key=lambda x: int(float(x.get("unit_no") or 9999))), start=1):
        b_id = str(r.get("design_box_id") or "").strip().upper()
        if not b_id:
            continue
        aslaid_units.append({
            "unit_no": int(float(r.get("unit_no") or idx)),
            "box_id": b_id,
            "tag": str(r.get("physical_tag") or "-").strip(),
            "crossing_id": str(r.get("crossing_id") or "").strip(),
            "install_date": str(r.get("install_date") or "").strip(),
            "aslaid_e": r.get("aslaid_e") or r.get("qaqc_e") or 0.0,
            "aslaid_n": r.get("aslaid_n") or r.get("qaqc_n") or 0.0,
            "has_raw": b_id in store,
            "raw_count": int((store.get(b_id) or {}).get("count") or 0)
        })

    catalog_boxes = [
        {"name": str(c.get("name") or "").strip().upper(), "layer": str(c.get("layer") or "").strip()}
        for c in cat_list if c.get("name")
    ]
    return jsonify({
        "status": "ok",
        "raw_rov_points": store,
        "aslaid_units": aslaid_units,
        "catalog_boxes": catalog_boxes
    })

@mti_bp.route('/save_raw_rov', methods=['POST'])
@login_required
def mti_save_raw_rov():
    req = request.get_json(silent=True) or request.form.to_dict()
    raw_txt = str(req.get("raw_text") or "").strip()
    if not raw_txt and "raw_file" in request.files:
        f = request.files["raw_file"]
        if f:
            raw_txt = f.read().decode("utf-8", errors="ignore")

    target_box = str(req.get("target_box_id") or "").strip()
    neg_z = _as_bool(req.get("negate_z"), False) if "_as_bool" in globals() else bool(req.get("negate_z"))
    app_mode = _as_bool(req.get("append_mode"), False) if "_as_bool" in globals() else bool(req.get("append_mode"))

    st = load_mti_state()
    ledger = list((st or {}).get("ledger") or [])
    cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    cur_store = load_raw_rov_store(st, MTI_WS_DIR, None, ledger, cat_list)

    new_store, updated_boxes, skipped = parse_and_merge_raw_rov_text(
        raw_txt, cur_store, target_box_id=target_box, negate_z=neg_z,
        append_mode=app_mode, ledger=ledger, catalog=cat_list
    )
    if not updated_boxes:
        return jsonify({
            "status": "error",
            "message": "No valid TWD97 E/N points matched a Mattress ID. Select a Target As-Laid Mattress in the dropdown if point IDs do not include the Box ID."
        }), 400

    save_raw_rov_store(new_store, st, save_mti_state, MTI_WS_DIR)
    return jsonify({
        "status": "ok",
        "updated_boxes": updated_boxes,
        "skipped_lines": skipped,
        "total_boxes": len(new_store)
    })

@mti_bp.route('/delete_raw_rov', methods=['POST'])
@login_required
def mti_delete_raw_rov():
    req = request.get_json(silent=True) or request.form.to_dict()
    b_id = str(req.get("box_id") or "").strip().upper()
    st = load_mti_state()
    ledger = list((st or {}).get("ledger") or [])
    cat_list = list(MATTRESS_CATALOG.values()) if isinstance(MATTRESS_CATALOG, dict) else list(MATTRESS_CATALOG)
    cur_store = load_raw_rov_store(st, MTI_WS_DIR, None, ledger, cat_list)
    if b_id == "__ALL__":
        cur_store = {}
    else:
        for k in [k for k in list(cur_store.keys()) if str(k).upper() == b_id]:
            cur_store.pop(k, None)
    save_raw_rov_store(cur_store, st, save_mti_state, MTI_WS_DIR)
    return jsonify({"status": "ok", "deleted": b_id, "total_boxes": len(cur_store)})

# --- MTI_GAP_TOL_050_FINAL_ENFORCE_START ---
_real_final_load_mti_state = load_mti_state
_final_gaptol_saving = False

def load_mti_state(*args, **kwargs):
    global _final_gaptol_saving
    st = _real_final_load_mti_state(*args, **kwargs)
    if isinstance(st, dict):
        cur_g = st.get("gap_tolerance_m")
        if not st.get("gap_tol_050_v2") or cur_g is None or abs(float(cur_g) - 0.20) < 1e-6:
            st["gap_tolerance_m"] = 0.50
            if isinstance(st.get("survey_setup"), dict):
                st["survey_setup"]["gap_tolerance_m"] = 0.50
            st["gap_tol_050_v2"] = True
            if not _final_gaptol_saving:
                try:
                    _final_gaptol_saving = True
                    save_mti_state(st)
                except Exception:
                    pass
                finally:
                    _final_gaptol_saving = False
    return st
# --- MTI_GAP_TOL_050_FINAL_ENFORCE_END ---
