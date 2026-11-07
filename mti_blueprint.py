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

# --- PRELOADED BASELINE MTI REPORT (30 OCT - 07 NOV 2026 DPR WORKBOOK) ---
PRELOADED_MTI_LEDGER = [{'id': 1, 'unit_no': 1, 'is_first_in_array': True, 'unit_type': 'Concrete Mattress', 'crossing_id': 'CR-A1_L1', 'design_box_id': 'CR-A1_M15', 'physical_tag': '#A046', 'install_date': '2026-11-04 14:34', 'usbl_sensor': 'Survey Pole', 'design_e': 194541.443, 'design_n': 2702613.394, 'design_brg': 195.861, 'qaqc_e': 194541.206, 'qaqc_n': 2702613.513, 'qaqc_brg': 196.889, 'aslaid_e': 194541.206, 'aslaid_n': 2702613.513, 'aslaid_z': -18.2, 'cl_offset_m': 0.265, 'heading_deg': 196.889, 'brg_diff_deg': -1.028, 'c1_e': 194540.642, 'c1_n': 2702616.819, 'c1_z': -18.2, 'c2_e': 194543.513, 'c2_n': 2702615.948, 'c2_z': -18.2, 'c3_e': 194541.77, 'c3_n': 2702610.207, 'c3_z': -18.2, 'c4_e': 194538.899, 'c4_n': 2702611.078, 'c4_z': -18.2, 'gap_nw': '', 'gap_ne': '', 'gap_sw': '', 'gap_se': '', 'gap_labels': '1st Unit (N/A)', 'gap1_m': 0.0, 'gap2_m': 0.0, 'gap_m': 0.0, 'env_wind': '', 'env_current': '', 'status': 'Completed', 'remarks': '[Survey Pole] Mattress installed completed (CR-A1_M15) #A046 (14:34 - 16:00:20); dCL=0.265m, dBrg=-1.028 deg'}, {'id': 2, 'unit_no': 2, 'is_first_in_array': False, 'unit_type': 'Concrete Mattress', 'crossing_id': 'CR-A1_L1', 'design_box_id': 'CR-A1_M16', 'physical_tag': '#A007', 'install_date': '2026-11-05 04:20', 'usbl_sensor': 'Survey Pole', 'design_e': 194544.329, 'design_n': 2702612.575, 'design_brg': 195.852, 'qaqc_e': 194544.356, 'qaqc_n': 2702612.753, 'qaqc_brg': 198.397, 'aslaid_e': 194544.356, 'aslaid_n': 2702612.753, 'aslaid_z': -18.35, 'cl_offset_m': 0.18, 'heading_deg': 198.397, 'brg_diff_deg': -2.545, 'c1_e': 194543.879, 'c1_n': 2702616.073, 'c1_z': -18.35, 'c2_e': 194546.726, 'c2_n': 2702615.126, 'c2_z': -18.35, 'c3_e': 194544.833, 'c3_n': 2702609.433, 'c3_z': -18.35, 'c4_e': 194541.986, 'c4_n': 2702610.38, 'c4_z': -18.35, 'gap_nw': '0.02', 'gap_ne': '', 'gap_sw': '0.10', 'gap_se': '', 'gap_labels': 'NW:0.02m | SW:0.10m', 'gap1_m': 0.02, 'gap2_m': 0.1, 'gap_m': 0.1, 'env_wind': '', 'env_current': '', 'status': 'Completed', 'remarks': '[Survey Pole] Mattress installed completed (CR-A1_M16) #A007 (04:20 - 04:40); Gap between Mat is 2cm North and 10cm South; ROV 4-corner fix completed at 05:00'}]

PRELOADED_MTI_LOGS = [{'id': 1, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-10-30 08:15', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / Quayside', 'val1': 'Install the survey equpment and integration', 'val2': 'Window: 08:15 - 15:15', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Install the survey equpment and integration (08:15 - 15:15) [USBL:Survey Pole]'}, {'id': 2, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-10-30 15:15', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / Quayside', 'val1': 'Perform Dimcon', 'val2': 'Window: 15:15 - 19:30', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Perform Dimcon (15:15 - 19:30) [USBL:Survey Pole]'}, {'id': 3, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-10-30 19:30', 'surveyor': 'Roderick', 'ref_id': 'MMA Prestige / Quayside', 'val1': 'Create SD3 as new control point for calibration', 'val2': 'Window: 19:30 - 20:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Create SD3 as new control point for calibration (19:30 - 20:00) [USBL:Survey Pole]'}, {'id': 4, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-10-31 07:00', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / Quayside', 'val1': 'Prepare for calibration', 'val2': 'Window: 07:00 - 07:44', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Prepare for calibration (07:00 - 07:44) [USBL:Survey Pole]'}, {'id': 5, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-10-31 07:44', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / Quayside', 'val1': 'Starting heading alignment, GPS Verification and pitch roll calibration', 'val2': 'Window: 07:44 - 15:30', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Starting heading alignment, GPS Verification and pitch roll calibration — Completed calibration at 15:30 (07:44 - 15:30) [USBL:Survey Pole]'}, {'id': 6, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-10-31 15:30', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / Quayside', 'val1': 'Wet test equipment', 'val2': 'Window: 15:30 - 18:30', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Wet test equipment — Completed wet test equipment at 18:30 (15:30 - 18:30) [USBL:Survey Pole]'}, {'id': 7, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-10-31 18:30', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / Quayside', 'val1': 'Continue system integration', 'val2': 'Window: 18:30 - 22:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Continue system integration (18:30 - 22:00) [USBL:Survey Pole]'}, {'id': 8, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-01 05:00', 'surveyor': 'Roderick', 'ref_id': 'MMA Prestige / Quayside', 'val1': 'Continue node offset check', 'val2': 'Window: 05:00 - 08:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Continue node offset check (05:00 - 08:00) [USBL:Survey Pole]'}, {'id': 9, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-01 09:00', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Vessel cast off to site calibration', 'val2': 'Window: 09:00 - 11:40', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Vessel cast off to site calibration (09:00 - 11:40) [USBL:Survey Pole]'}, {'id': 10, 'event_type': 'Pole down', 'timestamp': '2026-11-01 11:40', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Arrive site and perform DP trial, Deploy SVP and pole', 'val2': 'Window: 11:40 - 12:15', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Arrive site and perform DP trial, Deploy SVP and pole (11:40 - 12:15)'}, {'id': 11, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-01 12:15', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Prepare to launch ROV for recovering the beacon', 'val2': 'Window: 12:15 - 12:28', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Prepare to launch ROV for recovering the beacon (12:15 - 12:28) [USBL:Survey Pole]'}, {'id': 12, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-01 12:28', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'ROV off deck', 'val2': 'Window: 12:28 - 13:40', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'ROV off deck (12:28 - 13:40) [USBL:Survey Pole]'}, {'id': 13, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-01 13:40', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'ROV on deck', 'val2': 'Window: 13:40 - 14:31', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'ROV on deck (13:40 - 14:31) [USBL:Survey Pole]'}, {'id': 14, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-01 14:31', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Starting USBL calibration and processing', 'val2': 'Window: 14:31 - 08:15 (+1d)', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Starting USBL calibration and processing — Calibration vessel and survey pole USBL (14:31 - 08:15 (+1d)) [USBL:Survey Pole]'}, {'id': 15, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-02 08:15', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / Mess Room', 'val1': 'Meeting with client for the status of USBL calibration results due to accuracy issue', 'val2': 'Window: 08:15 - 09:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Meeting with client for the status of USBL calibration results due to accuracy issue (08:15 - 09:00) [USBL:Survey Pole]'}, {'id': 16, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-02 09:00', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Re-perform USBL calibration', 'val2': 'Window: 09:00 - 13:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Re-perform USBL calibration — Completed USBL calibration at 13:00 (09:00 - 13:00) [USBL:Survey Pole]'}, {'id': 17, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-02 13:00', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Prepare to launch ROV for recovering the beacon', 'val2': 'Window: 13:00 - 13:11', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Prepare to launch ROV for recovering the beacon (13:00 - 13:11) [USBL:Survey Pole]'}, {'id': 18, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-02 13:11', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'ROV off deck', 'val2': 'Window: 13:11 - 13:50', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'ROV off deck (13:11 - 13:50) [USBL:Survey Pole]'}, {'id': 19, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-02 13:50', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'ROV on deck due umbilical entangled to cage wire', 'val2': 'Window: 13:50 - 13:55', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'ROV on deck due umbilical entangled to cage wire (13:50 - 13:55) [USBL:Survey Pole]'}, {'id': 20, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-02 13:55', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Aborted to re-launch ROV due to weather', 'val2': 'Window: 13:55 - 16:30', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Aborted to re-launch ROV due to weather (13:55 - 16:30) [USBL:Survey Pole]'}, {'id': 21, 'event_type': 'Pole up', 'timestamp': '2026-11-02 16:30', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Survey pole recovered', 'val2': 'Window: 16:30 - 18:00', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Survey pole recovered (16:30 - 18:00)'}, {'id': 22, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-02 18:00', 'surveyor': 'Abror', 'ref_id': 'Crane Cabin / Helmsman PC', 'val1': 'Preparing data for helmsman, waypoint and background', 'val2': 'Window: 18:00 - 23:30', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Preparing data for helmsman, waypoint and background (18:00 - 23:30) [USBL:Survey Pole]'}, {'id': 23, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-02 23:30', 'surveyor': 'Roderick', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Standby weather and troubleshoot USBL Accuracy ongoing', 'val2': 'Window: 23:30 - 24:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Standby weather and troubleshoot USBL Accuracy ongoing (23:30 - 24:00) [USBL:Survey Pole]'}, {'id': 24, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-03 00:00', 'surveyor': 'Roderick', 'ref_id': 'Crane Cabin / Helmsman PC', 'val1': 'Continue preparing data for helmsman, waypoint and background', 'val2': 'Window: 00:00 - 07:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Continue preparing data for helmsman, waypoint and background (00:00 - 07:00) [USBL:Survey Pole]'}, {'id': 25, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-03 08:25', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / Mess Room', 'val1': 'NMDC induction and toolbox talk in mess room', 'val2': 'Window: 08:25 - 09:30', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'NMDC induction and toolbox talk in mess room (08:25 - 09:30) [USBL:Survey Pole]'}, {'id': 26, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-03 09:30', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / Mess Room', 'val1': 'Daily project meeting', 'val2': 'Window: 09:30 - 10:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Daily project meeting (09:30 - 10:00) [USBL:Survey Pole]'}, {'id': 27, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-03 15:16', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'USBL Calibration report completed and submitted to Seatrench Field Engineer', 'val2': 'Window: 15:16 - 16:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'USBL Calibration report completed and submitted to Seatrench Field Engineer (15:16 - 16:00) [USBL:Survey Pole]'}, {'id': 28, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-03 16:00', 'surveyor': 'Abror', 'ref_id': 'Crane Cabin / Helmsman PC', 'val1': 'Continue preparing data for helmsman, waypoint and background', 'val2': 'Window: 16:00 - 24:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Continue preparing data for helmsman, waypoint and background (16:00 - 24:00) [USBL:Survey Pole]'}, {'id': 29, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-04 07:48', 'surveyor': 'Abror', 'ref_id': 'Echo 4 / CR-A1', 'val1': 'Echo 4 arrived on the Location', 'val2': 'Window: 07:48 - 08:19', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Echo 4 arrived on the Location (07:48 - 08:19) [USBL:Survey Pole]'}, {'id': 30, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-04 08:19', 'surveyor': 'Abror', 'ref_id': 'Echo 4 / CR-A1', 'val1': 'Moved 100 meters to create Echo 4 space, Echo 4 entering beacon location', 'val2': 'Window: 08:19 - 08:25', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Moved 100 meters to create Echo 4 space, Echo 4 entering beacon location (08:19 - 08:25) [USBL:Survey Pole]'}, {'id': 31, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-04 08:25', 'surveyor': 'Abror', 'ref_id': 'Echo 4 / CR-A1', 'val1': 'Echo 4 start survey', 'val2': 'Window: 08:25 - 10:15', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Echo 4 start survey (08:25 - 10:15) [USBL:Survey Pole]'}, {'id': 32, 'event_type': 'Mattress on water', 'timestamp': '2026-11-04 10:15', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M15 (#A046)', 'val1': 'Started lifting the Mattress and put on the water', 'val2': 'Window: 10:15 - 10:20', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Started lifting the Mattress and put on the water (10:15 - 10:20)'}, {'id': 33, 'event_type': 'Mattress on water', 'timestamp': '2026-11-04 10:20', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M15 (#A046)', 'val1': 'Mattress on the seabed and start positioning', 'val2': 'Window: 10:20 - 13:25', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Mattress on the seabed and start positioning (10:20 - 13:25)'}, {'id': 34, 'event_type': 'Mattress on water', 'timestamp': '2026-11-04 13:25', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M15 (#A046)', 'val1': 'Installation mattress on process, adjust heading and stabilize signal', 'val2': 'Window: 13:25 - 14:34', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Installation mattress on process, adjust heading and stabilize signal (13:25 - 14:34)'}, {'id': 35, 'event_type': 'Mattress fix', 'timestamp': '2026-11-04 14:34', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M15 (#A046)', 'val1': 'Act E:194541.206, N:2702613.513, Z:-18.20 (dCL:0.265m)', 'val2': 'Brg:196.889 deg | 1st Unit (N/A) | Mattress installed completed (CR-A1_M15) #A046', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Act E:194541.206, N:2702613.513, Z:-18.20 (dCL:0.265m) — Brg:196.889 deg | 1st Unit (N/A) | Mattress installed completed (CR-A1_M15) #A046 (14:34 - 16:00:20) [USBL:Survey Pole]'}, {'id': 36, 'event_type': 'Mattress on water', 'timestamp': '2026-11-04 16:55', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'Started lifting the Mattress and put on the water', 'val2': 'Window: 16:55 - 17:00', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Started lifting the Mattress and put on the water (16:55 - 17:00)'}, {'id': 37, 'event_type': 'Mattress on water', 'timestamp': '2026-11-04 17:00', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'Started align the mattress to the position and ongoing installation', 'val2': 'Window: 17:00 - 19:30', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Started align the mattress to the position and ongoing installation (17:00 - 19:30)'}, {'id': 38, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-04 19:30', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'ROV stuck inside the lifting frame', 'val2': 'Window: 19:30 - 20:45', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'ROV stuck inside the lifting frame (19:30 - 20:45) [USBL:Survey Pole]'}, {'id': 39, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-04 20:45', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'ROV recovered and lifted up on deck', 'val2': 'Window: 20:45 - 21:55', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'ROV recovered and lifted up on deck (20:45 - 21:55) [USBL:Survey Pole]'}, {'id': 40, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-04 21:55', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'Repair ROV propeller damage', 'val2': 'Window: 21:55 - 24:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Repair ROV propeller damage (21:55 - 24:00) [USBL:Survey Pole]'}, {'id': 41, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-05 00:00', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'ROV repaired and deployed into the water', 'val2': 'Window: 00:00 - 00:15', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'ROV repaired and deployed into the water (00:00 - 00:15) [USBL:Survey Pole]'}, {'id': 42, 'event_type': 'Mattress on water', 'timestamp': '2026-11-05 00:15', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'Mattress deployed in the water to resume placing', 'val2': 'Window: 00:15 - 01:40', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Mattress deployed in the water to resume placing (00:15 - 01:40)'}, {'id': 43, 'event_type': 'Mattress on water', 'timestamp': '2026-11-05 01:40', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'Mattress on the seabed and start alignment', 'val2': 'Window: 01:40 - 01:50', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Mattress on the seabed and start alignment (01:40 - 01:50)'}, {'id': 44, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-05 01:50', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'Beacon Signal lost and intermittent signal return', 'val2': 'Window: 01:50 - 02:20', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Beacon Signal lost and intermittent signal return — 01:50-02:00 & 02:05-02:19 signal lost; restored at 02:20 (01:50 - 02:20) [USBL:Survey Pole]'}, {'id': 45, 'event_type': 'Mattress on water', 'timestamp': '2026-11-05 02:20', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'Continue repositioning of the mattress', 'val2': 'Window: 02:20 - 04:20', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Continue repositioning of the mattress (02:20 - 04:20)'}, {'id': 46, 'event_type': 'Mattress fix', 'timestamp': '2026-11-05 04:20', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'Act E:194544.356, N:2702612.753, Z:-18.35 (dCL:0.180m)', 'val2': 'Brg:198.397 deg | Gap between Mat is 2cm North and 10cm South (CR-A1_M16 #A007)', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Act E:194544.356, N:2702612.753, Z:-18.35 (dCL:0.180m) — Brg:198.397 deg | Gap between Mat is 2cm North and 10cm South (CR-A1_M16 #A007) (04:20 - 04:40) [USBL:Survey Pole]'}, {'id': 47, 'event_type': 'Frame above water', 'timestamp': '2026-11-05 04:40', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'Frame safe release', 'val2': 'Window: 04:40 - 04:45', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Frame safe release (04:40 - 04:45)'}, {'id': 48, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-05 04:45', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'ROV final take and complete the four corner position of the mattress', 'val2': 'Window: 04:45 - 05:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'ROV final take and complete the four corner position of the mattress (04:45 - 05:00) [USBL:Survey Pole]'}, {'id': 49, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-05 05:00', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M16 (#A007)', 'val1': 'ROV recovered from water and placed on deck for maintenance', 'val2': 'Window: 05:00 - 07:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'ROV recovered from water and placed on deck for maintenance (05:00 - 07:00) [USBL:Survey Pole]'}, {'id': 50, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-05 07:00', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Start deploying ROV into the water to continue mattress installation', 'val2': 'Window: 07:00 - 07:05', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Start deploying ROV into the water to continue mattress installation (07:00 - 07:05) [USBL:Survey Pole]'}, {'id': 51, 'event_type': 'Mattress on water', 'timestamp': '2026-11-05 07:05', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Connect mattress frame to crane and deploy into water (CR-A1_M17) #A023', 'val2': 'Window: 07:05 - 09:25', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Connect mattress frame to crane and deploy into water (CR-A1_M17) #A023 (07:05 - 09:25)'}, {'id': 52, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-05 09:25', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Restart USBL System signal beacon lost while mattress installation in process', 'val2': 'Window: 09:25 - 09:35', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Restart USBL System signal beacon lost while mattress installation in process — Assisted by ROV with gap reference (09:25 - 09:35) [USBL:Survey Pole]'}, {'id': 53, 'event_type': 'Mattress on water', 'timestamp': '2026-11-05 09:35', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'USBL system back to normal, continue placing mattress with ROV and Sonar', 'val2': 'Window: 09:35 - 10:47', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'USBL system back to normal, continue placing mattress with ROV and Sonar (09:35 - 10:47)'}, {'id': 54, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-05 10:47', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Restart USBL System signal beacon lost while mattress installation in process', 'val2': 'Window: 10:47 - 10:57', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Restart USBL System signal beacon lost while mattress installation in process (10:47 - 10:57) [USBL:Survey Pole]'}, {'id': 55, 'event_type': 'Mattress on water', 'timestamp': '2026-11-05 10:57', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'USBL system back to normal, continue placing mattress with ROV and Sonar', 'val2': 'Window: 10:57 - 11:30', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'USBL system back to normal, continue placing mattress with ROV and Sonar (10:57 - 11:30)'}, {'id': 56, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-05 11:30', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Restart USBL System signal beacon lost; troubleshoot cable and connector of Survey Pole USBL', 'val2': 'Window: 11:30 - 13:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Restart USBL System signal beacon lost; troubleshoot cable and connector of Survey Pole USBL — Survey pole USBL off, signal result still same (11:30 - 13:00) [USBL:Survey Pole]'}, {'id': 57, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-05 12:15', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Switch to Vessel USBL for navigation system', 'val2': 'Window: 12:15 - 12:20', 'usbl_sensor': 'Vessel', 'env_wind': '', 'env_current': '', 'remarks': 'Switch to Vessel USBL for navigation system — For mattress positioning only; final position to be taken with Survey Pole USBL; Vessel USBL good and stable (12:15 - 12:20) [USBL:Vessel]'}, {'id': 58, 'event_type': 'Mattress on water', 'timestamp': '2026-11-05 12:20', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Continue repositioning of the mattress', 'val2': 'Window: 12:20 - 15:00', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Continue repositioning of the mattress — ROV struggling to adjust mattress heading as per design (12:20 - 15:00)'}, {'id': 59, 'event_type': 'Frame above water', 'timestamp': '2026-11-05 15:00', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Lift up frame on deck to install tagline to assist heading adjustment', 'val2': 'Window: 15:00 - 15:15', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Lift up frame on deck to install tagline to assist heading adjustment (15:00 - 15:15)'}, {'id': 60, 'event_type': 'Mattress on water', 'timestamp': '2026-11-05 15:15', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Lower back the frame into the water after tagline installed', 'val2': 'Window: 15:15 - 15:30', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Lower back the frame into the water after tagline installed (15:15 - 15:30)'}, {'id': 61, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-05 15:30', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Vessel adjust heading as survey guidance in navigation system', 'val2': 'Window: 15:30 - 15:40', 'usbl_sensor': 'Vessel', 'env_wind': '', 'env_current': '', 'remarks': 'Vessel adjust heading as survey guidance in navigation system (15:30 - 15:40) [USBL:Vessel]'}, {'id': 62, 'event_type': 'Mattress on water', 'timestamp': '2026-11-05 15:40', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Continue repositioning of the mattress with tagline', 'val2': 'Window: 15:40 - 16:00', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Continue repositioning of the mattress with tagline (15:40 - 16:00)'}, {'id': 63, 'event_type': 'Mattress on water', 'timestamp': '2026-11-05 16:00', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Attempted Mattress Placement (#A023) with ROV on seabed', 'val2': 'Window: 16:00 - 18:00', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Attempted Mattress Placement (#A023) with ROV on seabed — Seabed not flat; East side matched but West side gap > 20 cm on ROV video; center within tolerance 0.18 m vs design (16:00 - 18:00)'}, {'id': 64, 'event_type': 'Mattress on water', 'timestamp': '2026-11-05 18:36', 'surveyor': 'Abror', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'Continue repositioning of the mattress with ROV and tagline to close gap', 'val2': 'Window: 18:36 - 19:10', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Continue repositioning of the mattress with ROV and tagline to close gap (18:36 - 19:10)'}, {'id': 65, 'event_type': 'Frame above water', 'timestamp': '2026-11-05 19:15', 'surveyor': 'Roderick', 'ref_id': 'CR-A1_M17 (#A023)', 'val1': 'ROV and mattress removed from water and placed back on main deck', 'val2': 'Window: 19:15 - 19:20', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'ROV and mattress removed from water and placed back on main deck (19:15 - 19:20)'}, {'id': 66, 'event_type': 'Pole up', 'timestamp': '2026-11-05 19:25', 'surveyor': 'Roderick', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Survey pole secured and retrieved from water; operations on weather standby', 'val2': 'Window: 19:25 - 07:51 (+1d)', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': "Survey pole secured and retrieved from water; operations on weather standby — Lat 24°25′44.20 Long 120°27′10.72, Heading=38.87° (19:25 - 07:51 (+1d))"}, {'id': 67, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-06 07:51', 'surveyor': 'Abror', 'ref_id': 'Crane Cabin / Helmsman PC', 'val1': 'Preparation for installing remote Helmsman PC in crane cabin', 'val2': 'Window: 07:51 - 08:30', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Preparation for installing remote Helmsman PC in crane cabin (07:51 - 08:30) [USBL:Survey Pole]'}, {'id': 68, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-06 09:30', 'surveyor': 'Abror', 'ref_id': 'Calibration Tripod', 'val1': 'Daily project meeting & Vessel moving into tripod position', 'val2': 'Window: 09:30 - 10:45', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Daily project meeting & Vessel moving into tripod position (09:30 - 10:45) [USBL:Survey Pole]'}, {'id': 69, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-06 10:45', 'surveyor': 'Abror', 'ref_id': 'Calibration Tripod', 'val1': 'Beacon tripod sending signal to USBL', 'val2': 'Window: 10:45 - 10:54', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Beacon tripod sending signal to USBL (10:45 - 10:54) [USBL:Survey Pole]'}, {'id': 70, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-06 10:54', 'surveyor': 'Abror', 'ref_id': 'Calibration Tripod', 'val1': 'ROV off deck and in the surface', 'val2': 'Window: 10:54 - 11:03', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'ROV off deck and in the surface (10:54 - 11:03) [USBL:Survey Pole]'}, {'id': 71, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-06 11:03', 'surveyor': 'Abror', 'ref_id': 'Calibration Tripod', 'val1': 'Tripod beacon found fallen on seabed', 'val2': 'Window: 11:03 - 11:14', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Tripod beacon found fallen on seabed — Found calibration beacon tripod fallen and not standing in proper position (affected calibration result) (11:03 - 11:14) [USBL:Survey Pole]'}, {'id': 72, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-06 11:14', 'surveyor': 'Abror', 'ref_id': 'Calibration Tripod', 'val1': 'ROV recovered on deck', 'val2': 'Window: 11:14 - 11:20', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'ROV recovered on deck (11:14 - 11:20) [USBL:Survey Pole]'}, {'id': 73, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-06 11:20', 'surveyor': 'Abror', 'ref_id': 'Crane Cabin / Helmsman PC', 'val1': 'Install Monitor control unit in crane cabin with wireless Wi-Fi connection', 'val2': 'Window: 11:20 - 15:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Install Monitor control unit in crane cabin with wireless Wi-Fi connection (11:20 - 15:00) [USBL:Survey Pole]'}, {'id': 74, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-06 15:00', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Process current speed data as per recorded data', 'val2': 'Window: 15:00 - 19:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Process current speed data as per recorded data (15:00 - 19:00) [USBL:Survey Pole]'}, {'id': 75, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-06 19:00', 'surveyor': 'Roderick', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Continue to troubleshoot USBL issue with string and signal', 'val2': 'Window: 19:00 - 20:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Continue to troubleshoot USBL issue with string and signal (19:00 - 20:00) [USBL:Survey Pole]'}, {'id': 76, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-06 21:00', 'surveyor': 'Roderick', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Operations remain on standby due to deteriorating weather conditions', 'val2': 'Window: 21:00 - 07:00 (+1d)', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': "Operations remain on standby due to deteriorating weather conditions — Lat 24°25′44.20 Long 120°27′10.72, Heading=38.87° (21:00 - 07:00 (+1d)) [USBL:Survey Pole]"}, {'id': 77, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-07 09:00', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Continue troubleshooting instability of USBL string', 'val2': 'Window: 09:00 - 12:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Continue troubleshooting instability of USBL string — Created new job in Mini-Ranger software and checked current setup wiring (09:00 - 12:00) [USBL:Survey Pole]'}, {'id': 78, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-07 12:00', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Make additional offset on WROV for new node to take fix coordinate reference', 'val2': 'Window: 12:00 - 12:50', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Make additional offset on WROV for new node to take fix coordinate reference (12:00 - 12:50) [USBL:Survey Pole]'}, {'id': 79, 'event_type': 'Pole down', 'timestamp': '2026-11-07 12:50', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Lower survey pole to test system ADCP, USBL and MRU', 'val2': 'Window: 12:50 - 13:30', 'usbl_sensor': '', 'env_wind': '', 'env_current': '', 'remarks': 'Lower survey pole to test system ADCP, USBL and MRU (12:50 - 13:30)'}, {'id': 80, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-07 13:30', 'surveyor': 'Abror', 'ref_id': 'Crane Cabin / Helmsman PC', 'val1': 'Deploy 1 and 2 beacons with crane assist to 20 m water depth to test USBL ping stability', 'val2': 'Window: 13:30 - 15:20', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Deploy 1 and 2 beacons with crane assist to 20 m water depth to test USBL ping stability — 13:40-14:00 (1 beacon at 20m); 14:20-15:20 (2 beacons deployed simultaneously at 20m) (13:30 - 15:20) [USBL:Survey Pole]'}, {'id': 81, 'event_type': 'Survey Issue Reporting', 'timestamp': '2026-11-07 15:20', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Lift up beacon on deck, testing complete — Survey Pole USBL data loss persists', 'val2': 'Window: 15:20 - 15:50', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Lift up beacon on deck, testing complete — Survey Pole USBL data loss persists — Result signal on Survey USBL still same; longer stay in water causes more data loss (15:20 - 15:50) [USBL:Survey Pole]'}, {'id': 82, 'event_type': 'Calib, Setup & TBT', 'timestamp': '2026-11-07 15:50', 'surveyor': 'Abror', 'ref_id': 'MMA Prestige / CR-A1', 'val1': 'Record sea current and continue troubleshooting', 'val2': 'Window: 15:50 - 18:51', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Record sea current and continue troubleshooting (15:50 - 18:51) [USBL:Survey Pole]'}, {'id': 83, 'event_type': 'ROV & Vessel Ops', 'timestamp': '2026-11-07 18:51', 'surveyor': 'Abror', 'ref_id': 'Calibration Tripod', 'val1': 'Prepare ROV to install tripod beacon on the seabed for next installation', 'val2': 'Window: 18:51 - 19:00', 'usbl_sensor': 'Survey Pole', 'env_wind': '', 'env_current': '', 'remarks': 'Prepare ROV to install tripod beacon on the seabed for next installation (18:51 - 19:00) [USBL:Survey Pole]'}]

MTI_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mti_state.json")

def _init_mti_db_table():
    try:
        from app import db
        from sqlalchemy import text
        db.session.execute(text("CREATE TABLE IF NOT EXISTS mti_state_store (k VARCHAR(64) PRIMARY KEY, v TEXT)"))
        db.session.commit()
    except Exception:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass

def load_mti_state():
    st = None
    try:
        _init_mti_db_table()
        from app import db
        from sqlalchemy import text
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
            if os.path.exists(MTI_STATE_FILE):
                with open(MTI_STATE_FILE, "r", encoding="utf-8") as f:
                    st = json.load(f)
        except Exception:
            st = None
    if not isinstance(st, dict):
        st = {}
    for def_k in ("daily_logs", "issues", "rock_bags", "crossings"):
        if def_k not in st:
            st[def_k] = []
    changed = False
    if not st.get("dpr_20261107_clean_v5"):
        st["ledger"] = [dict(x) for x in PRELOADED_MTI_LEDGER]
        st["input_logs"] = [dict(x) for x in PRELOADED_MTI_LOGS]
        st["dpr_20261107_clean_v5"] = True
        changed = True
    for r in st.get("ledger", []):
        if float(r.get("heading_deg") or 0) < 180.0:
            r["heading_deg"] = round(float(r.get("heading_deg") or 15.854) + 180.0, 3)
            changed = True
    if changed:
        save_mti_state(st)
    return st







def save_mti_state(state):
    raw = json.dumps(state, ensure_ascii=False)
    try:
        from app import db, AppConfig
        row = AppConfig.query.filter_by(key="mti_state_v1").first()
        if not row:
            row = AppConfig(key="mti_state_v1", value=raw)
            db.session.add(row)
        else:
            row.value = raw
        db.session.commit()
    except Exception:
        pass
    try:
        dname = os.path.dirname(MTI_STATE_FILE)
        if dname:
            os.makedirs(dname, exist_ok=True)
        with open(MTI_STATE_FILE, "w", encoding="utf-8") as f:
            f.write(raw)
    except Exception:
        pass


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

@mti_bp.route('/import_excel', methods=['POST'])
@login_required
def import_excel():
    import pandas as pd
    f = request.files.get('excel_file')
    if not f or not f.filename:
        flash("Please select an Excel (.xlsx) file to upload.", "warning")
        return redirect(request.referrer or '/mti')
    try:
        xls = pd.ExcelFile(f)
        state = load_mti_state()
        ledger = state.get("ledger", [])
        logs = state.get("input_logs", [])
        imported_f, imported_l = 0, 0
        for s in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=s).dropna(how='all')
            if df.empty:
                continue
            cols = [str(c).lower() for c in df.columns]
            if '1_mattress' in s.lower() or any('aslaid' in c or 'as-laid' in c or 'design_box' in c for c in cols):
                for _, row in df.iterrows():
                    rdict = {str(k).strip(): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                    uno = int(rdict.get('unit_no') or rdict.get('Unit #') or (len(ledger) + 1))
                    box = str(rdict.get('design_box_id') or rdict.get('Design Box ID') or rdict.get('ID') or f'CR-A1_M{uno}')
                    tag = str(rdict.get('physical_tag') or rdict.get('Mattress No (Tag)') or rdict.get('Mattress No') or '')
                    de = float(rdict.get('design_e') or rdict.get('Design Easting (m)') or 194541.443)
                    dn = float(rdict.get('design_n') or rdict.get('Design Northing (m)') or 2702613.394)
                    ae = float(rdict.get('aslaid_e') or rdict.get('As-Laid Easting (m)') or de)
                    an = float(rdict.get('aslaid_n') or rdict.get('As-Laid Northing (m)') or dn)
                    hdg = float(rdict.get('heading_deg') or rdict.get('As-Laid Bearing (Deg)') or 195.854)
                    if hdg < 180.0:
                        hdg = round(hdg + 180.0, 3)
                    cl = round(math.hypot(ae - de, an - dn), 2)
                    corners = compute_4_corners(ae, an, hdg, 6.0, 3.0)
                    entry = {
                        "id": max([int(x.get("id") or 0) for x in ledger] + [0]) + 1,
                        "unit_no": uno, "is_first_in_array": (uno == 1), "unit_type": "Concrete Mattress",
                        "crossing_id": str(rdict.get('crossing_id') or rdict.get('Crossing / Layer') or 'CR-A1_L1'),
                        "design_box_id": box, "physical_tag": tag,
                        "install_date": str(rdict.get('install_date') or rdict.get('Date/Time') or '2026-11-05 03:20'),
                        "usbl_sensor": str(rdict.get('usbl_sensor') or rdict.get('Active USBL') or 'Survey Pole'),
                        "design_e": round(de, 3), "design_n": round(dn, 3),
                        "qaqc_e": round(ae, 3), "qaqc_n": round(an, 3), "qaqc_brg": round(hdg, 3),
                        "aslaid_e": round(ae, 3), "aslaid_n": round(an, 3), "aslaid_z": float(rdict.get('aslaid_z') or -18.20),
                        "cl_offset_m": cl, "heading_deg": round(hdg, 3),
                        "gap_labels": str(rdict.get('gap_labels') or rdict.get('Corner Gaps') or '0.00m'),
                        "gap1_m": float(rdict.get('gap1_m') or 0.0), "gap2_m": float(rdict.get('gap2_m') or 0.0), "gap_m": float(rdict.get('gap_m') or 0.0),
                        "status": str(rdict.get('status') or rdict.get('Status') or 'Completed'),
                        "remarks": str(rdict.get('remarks') or rdict.get('Remarks') or ''),
                        **corners
                    }
                    existing = next((x for x in ledger if str(x.get("design_box_id")) == box), None)
                    if existing:
                        ledger.remove(existing)
                    ledger.append(entry)
                    imported_f += 1
            elif '2_survey' in s.lower() or any('event' in c or 'surveyor' in c for c in cols):
                for _, row in df.iterrows():
                    rdict = {str(k).strip(): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                    logs.append({
                        "id": max([int(x.get("id") or 0) for x in logs] + [0]) + 1,
                        "event_type": str(rdict.get('event_type') or rdict.get('Event Type') or 'Pole down'),
                        "timestamp": str(rdict.get('timestamp') or rdict.get('Date/Time') or '2026-11-05 00:00'),
                        "surveyor": str(rdict.get('surveyor') or rdict.get('Surveyor') or 'Surveyor'),
                        "ref_id": str(rdict.get('ref_id') or rdict.get('Location / Ref ID') or ''),
                        "val1": str(rdict.get('val1') or rdict.get('Primary Parameter / Status') or ''),
                        "val2": str(rdict.get('val2') or rdict.get('Secondary Parameter / Details') or ''),
                        "usbl_sensor": str(rdict.get('usbl_sensor') or rdict.get('Active USBL') or ''),
                        "env_wind": str(rdict.get('env_wind') or rdict.get('Wind') or ''),
                        "env_current": str(rdict.get('env_current') or rdict.get('Current') or ''),
                        "remarks": str(rdict.get('remarks') or rdict.get('Remarks / Action Taken') or rdict.get('Remarks') or '')
                    })
                    imported_l += 1
        state["ledger"] = ledger
        state["input_logs"] = logs
        save_mti_state(state)
        if imported_f == 0 and imported_l == 0:
            flash("The uploaded Excel file had 0 data rows (press Ctrl+S in Excel before uploading). Preloaded baseline report is active.", "warning")
        else:
            flash(f"Imported {imported_f} Mattress Fix(es) and {imported_l} Survey Log(s) from {f.filename}!", "success")
    except Exception as e:
        flash(f"Excel import error: {e}", "danger")
    return redirect(request.referrer or '/mti')
