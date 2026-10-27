import pandas as pd
import io
from flask import send_file
import os, json
import calendar
import traceback
from collections import Counter
from flask import Flask, render_template, render_template_string, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from docxtpl import DocxTemplate 
from sqlalchemy import text, or_, and_
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)

db_url = os.environ.get('DATABASE_URL', 'sqlite:///./survey_data.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'super_secret_key_thpp_survey_2026'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# --- EMAIL & TOKEN CONFIGURATION ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_DEFAULT_SENDER') 
app.config['MAIL_PASSWORD'] = os.environ.get('GMAIL_APP_PASSWORD') 
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

mail = Mail(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# --- VIP ADMIN LIST (SUPER-ADMIN FAILSAFE) ---
ADMIN_EMAILS = [
    'daryll.enano@nmdc-group.com',
    'mohamad.hediarto@nmdc-group.com',
    'mok.heng@nmdc-group.com'
]

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)  
    is_active = db.Column(db.Boolean, default=True)    
    is_admin = db.Column(db.Boolean, default=False)
    initials = db.Column(db.String(10), nullable=True) 

class AppConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schema_data = db.Column(db.Text, default="{}") 

class PresetTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    preset_name = db.Column(db.String(100), nullable=False)
    req_dept = db.Column(db.String(100))
    req_name = db.Column(db.String(100))
    assigned_to = db.Column(db.String(100))
    command_verb = db.Column(db.String(50)) 
    task_category = db.Column(db.String(100))
    area = db.Column(db.String(100))
    location = db.Column(db.String(100))
    sub_location = db.Column(db.String(100))
    work_scope = db.Column(db.String(100))
    instrument = db.Column(db.String(100))
    action_required = db.Column(db.String(100))
    remarks = db.Column(db.Text, nullable=True)

class SurveyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    surveyor_name = db.Column(db.String(100), nullable=False) 
    assigned_to = db.Column(db.String(100), nullable=True)    
    requestor = db.Column(db.String(100), nullable=True)
    command_verb = db.Column(db.String(50), default="PERFORM") 
    task_category = db.Column(db.String(100), nullable=True) 
    instrument = db.Column(db.String(100), nullable=True) 
    action_required = db.Column(db.String(100), nullable=True) 
    area = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=True) 
    sub_location = db.Column(db.String(100), nullable=True) 
    work_scope = db.Column(db.String(100), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    deliverable_link = db.Column(db.String(500), nullable=True) 
    reference_links = db.Column(db.Text, nullable=True) 
    status = db.Column(db.String(30), default="Open")
    is_urgent = db.Column(db.Boolean, default=False) 
    priority = db.Column(db.Integer, default=99)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    execution_date = db.Column(db.Date, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)

class UserActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    user_name = db.Column(db.String(100), nullable=False)
    endpoint = db.Column(db.String(100), nullable=False)
    path = db.Column(db.String(200), nullable=False)
    method = db.Column(db.String(15), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ==============================================================================
# SINGLE SOURCE OF TRUTH: 16 MACRO WORK SCOPES, 14 CORE TASKS & 6 QUICK CHIPS
# Edit any label, KPI prefix, hint, default instrument, or chip right here!
# ==============================================================================
LEAN_MACRO_SCOPES = [
    {
        "id": "MWS-01", "group": "OFC - Office & HQ",
        "label": "OFC - Taichung Survey & NMDC Internal",
        "area": "100_Office", "location": "110_Taichung", "sub_location": "111_Survey_Internal",
        "work_scope": "111-00_OFC_Taichung_Internal", "kpi_prefix": "Taichung Office Internal",
        "hint": "Specify team/topic in Remarks (e.g., ENERGY, Personnel, Internal Meeting)..."
    },
    {
        "id": "MWS-02", "group": "OFC - Office & HQ",
        "label": "OFC - Subcon & Client External (EGST / TPC-POE)",
        "area": "100_Office", "location": "110_Taichung", "sub_location": "113_Project-External",
        "work_scope": "113-10_OFC_External_TPC_Subcon", "kpi_prefix": "Taichung External & Subcon",
        "hint": "Specify EGST, TPC-POE, CRS response, or Subcon Deliverable in Remarks..."
    },
    {
        "id": "MWS-03", "group": "OFC - Office & HQ",
        "label": "OFC - Abu Dhabi HQ (STS / SWS / Admin)",
        "area": "100_Office", "location": "120_Abu_Dhabi", "sub_location": "121_STS",
        "work_scope": "121-00_OFC_Abu_Dhabi_HQ", "kpi_prefix": "Abu Dhabi HQ",
        "hint": "Specify Monthly KPI, WSR, SEM update, Equipment List, or Timesheet in Remarks..."
    },
    {
        "id": "MWS-04", "group": "TC - Taichung Onshore",
        "label": "TC - Taichung Landfall & General Site",
        "area": "200_Onshore-Land", "location": "210_Taichung", "sub_location": "211_General",
        "work_scope": "211-00_TC_Landfall_Site", "kpi_prefix": "Taichung Landside",
        "hint": "Specify TBM, Fence, Carwash, Land Lease, or General Topo details in Remarks..."
    },
    {
        "id": "MWS-05", "group": "TC - Taichung Onshore",
        "label": "TC - AHDD Compound (Pits, Settlement & Corridor)",
        "area": "200_Onshore-Land", "location": "210_Taichung", "sub_location": "212_AHDD",
        "work_scope": "212-00_TC_AHDD_Compound", "kpi_prefix": "Taichung AHDD",
        "hint": "Specify Road Settlement, Thruster Pit, Crossover Pit, Trial Pit, or Grit Tank in Remarks..."
    },
    {
        "id": "MWS-06", "group": "TC - Taichung Onshore",
        "label": "TC - Tienli (Pipe Laydown & Disposal Area)",
        "area": "200_Onshore-Land", "location": "210_Taichung", "sub_location": "213_Tienli",
        "work_scope": "213-00_TC_Tienli", "kpi_prefix": "Taichung Tienli",
        "hint": "Specify Pipe Laydown layout or Stockpile/Disposal details in Remarks..."
    },
    {
        "id": "MWS-07", "group": "TC - Taichung Onshore",
        "label": "TC - Berth 37 (Port Pipe Storage & Quay)",
        "area": "200_Onshore-Land", "location": "210_Taichung", "sub_location": "214_Berth37",
        "work_scope": "214-00_TC_Berth37", "kpi_prefix": "Taichung Berth 37",
        "hint": "Specify Pipe Storage layout, Quay Marking, or Tide Gauge details in Remarks..."
    },
    {
        "id": "MWS-08", "group": "TX - Tunghsiao Onshore",
        "label": "TX - Temp Platform & Microtunneling (All Works)",
        "area": "200_Onshore-Land", "location": "220_Tunghsiao", "sub_location": "221_Temp_Platform",
        "work_scope": "221-00_TX_Temp_Platform", "kpi_prefix": "Tunghsiao Temp Platform",
        "hint": "Specify Thruster Pit, Trial Pit, Welding Area, Sandslope, Filter Layer, or Microtunneling in Remarks..."
    },
    {
        "id": "MWS-09", "group": "TX - Tunghsiao Onshore",
        "label": "TX - Inside Plant (Pits, Boreholes & Corridor)",
        "area": "200_Onshore-Land", "location": "220_Tunghsiao", "sub_location": "222_Inside_Plant",
        "work_scope": "222-00_TX_Inside_Plant", "kpi_prefix": "Tunghsiao Inside Plant",
        "hint": "Specify Inside Plant Trial Pit, Crossover Pit, or Borehole ID in Remarks..."
    },
    {
        "id": "MWS-10", "group": "NS - Nearshore Marine",
        "label": "NS - Nearshore General & Dumping Area",
        "area": "300_Marine", "location": "320_Nearshore", "sub_location": "321_Nearshore_General",
        "work_scope": "321-00_NS_General_Dumping", "kpi_prefix": "Nearshore Dumping Area",
        "hint": "Specify Dumping Box, Nearshore Corridor, or Split Barge area in Remarks..."
    },
    {
        "id": "MWS-11", "group": "NS - Nearshore Marine",
        "label": "NS - Trench 1 (Taichung Nearshore)",
        "area": "300_Marine", "location": "320_Nearshore", "sub_location": "322_Trench_1",
        "work_scope": "322-00_NS_Trench_1", "kpi_prefix": "Nearshore Trench 1",
        "hint": "Specify T1 Dredging, Pipelaying A/B, Overlength, Siltation, or Backfilling in Remarks..."
    },
    {
        "id": "MWS-12", "group": "NS - Nearshore Marine",
        "label": "NS - Trench 8 (Tunghsiao Nearshore)",
        "area": "300_Marine", "location": "320_Nearshore", "sub_location": "323_Trench_8",
        "work_scope": "323-00_NS_Trench_8", "kpi_prefix": "Nearshore Trench 8",
        "hint": "Specify T8 Dredging, Pipelaying A/B, Overlength, Siltation, or Backfilling in Remarks..."
    },
    {
        "id": "MWS-13", "group": "OS - Offshore Marine",
        "label": "OS - Offshore Mainline (Trenches 2 to 7)",
        "area": "300_Marine", "location": "330_Offshore", "sub_location": "331_Offshore_Mainline",
        "work_scope": "331-00_OS_Trenches_2_7", "kpi_prefix": "Offshore Mainline",
        "hint": "Specify Trench # (T2–T7), KP range, Pipelaying A/B, Post-Trenching, or SRI in Remarks..."
    },
    {
        "id": "MWS-14", "group": "OS - Offshore Marine",
        "label": "OS - Midline Tie-In Area",
        "area": "300_Marine", "location": "330_Offshore", "sub_location": "337_Midline_Tie-in",
        "work_scope": "337-00_OS_Midline_Tie_In", "kpi_prefix": "Offshore Midline Tie-in",
        "hint": "Specify Midline Dredging, Pipelaying, or Tie-In KP 52.3–53.0 in Remarks..."
    },
    {
        "id": "MWS-15", "group": "OS - Offshore Marine",
        "label": "OS - Subsea Crossings (All Current & Future Crossings)",
        "area": "300_Marine", "location": "330_Offshore", "sub_location": "338_Subsea_Crossings",
        "work_scope": "338-00_OS_Subsea_Crossings", "kpi_prefix": "Offshore Subsea Crossings",
        "hint": "Specify Crossing ID (A1–B3, CPC, TWTK2, TUN-Datan) & phase (Mattress, SRI, Burial) in Remarks..."
    },
    {
        "id": "MWS-16", "group": "MAR - Marine Eng & Vessels",
        "label": "MAR - Vessels, Equipment & Project-Wide Design/Qty",
        "area": "300_Marine", "location": "310_General", "sub_location": "311_Marine_Engineering",
        "work_scope": "311-00_MAR_Vessels_Design_Qty", "kpi_prefix": "Marine Project-Wide",
        "hint": "Specify Vessel (WS166, Arzana, DLS-4200) or Design/ICQP/CECI format in Remarks..."
    }
]

LEAN_CORE_TASKS = [
    {
        "id": "CT-01", "label": "Monitoring & Settlement Survey (Land)",
        "action_required": "Monitoring Survey", "task_category": "Land Survey",
        "command_verb": "PERFORM", "default_instrument": "Levelling Machine",
        "instruments": ["Levelling Machine", "GNSS Rover", "Total Station"]
    },
    {
        "id": "CT-02", "label": "Topo / Progress / Pre & Post Survey (Land)",
        "action_required": "Progress Survey", "task_category": "Land Survey",
        "command_verb": "PERFORM", "default_instrument": "GNSS Rover",
        "instruments": ["GNSS Rover", "Total Station", "Drone", "Lidar"]
    },
    {
        "id": "CT-03", "label": "As-Built Survey (Land)",
        "action_required": "As-built Survey", "task_category": "Land Survey",
        "command_verb": "PERFORM", "default_instrument": "GNSS Rover",
        "instruments": ["GNSS Rover", "Total Station", "Drone", "Lidar"]
    },
    {
        "id": "CT-04", "label": "Stake-Out / Setting-Out / Marking",
        "action_required": "Stake-Out/Marking", "task_category": "Land Survey",
        "command_verb": "PERFORM", "default_instrument": "GNSS Rover",
        "instruments": ["GNSS Rover", "Total Station"]
    },
    {
        "id": "CT-05", "label": "Check Survey & Benchmark Verification (QA/QC)",
        "action_required": "Check Survey", "task_category": "Land Survey",
        "command_verb": "VERIFY", "default_instrument": "Levelling Machine",
        "instruments": ["Levelling Machine", "Total Station", "GNSS Rover"]
    },
    {
        "id": "CT-06", "label": "Bathymetric Monitoring & Progress Survey",
        "action_required": "Monitoring Survey", "task_category": "Bathymetric Survey",
        "command_verb": "PERFORM", "default_instrument": "MBES  WS166",
        "instruments": ["MBES  WS166", "SBES"]
    },
    {
        "id": "CT-07", "label": "Bathymetric Pre / Post / As-Built Survey",
        "action_required": "Post Survey", "task_category": "Bathymetric Survey",
        "command_verb": "PERFORM", "default_instrument": "MBES  WS166",
        "instruments": ["MBES  WS166", "SBES"]
    },
    {
        "id": "CT-08", "label": "Geophysical Survey & Processing (SSS/Maggy/SBP/GPR)",
        "action_required": "Geophysical Check Survey", "task_category": "Geophysical Survey",
        "command_verb": "PERFORM", "default_instrument": "SSS",
        "instruments": ["SSS", "Maggy", "SBP", "CAD", "Reporting"]
    },
    {
        "id": "CT-09", "label": "File Generation & Design/Background Prep (PDS/DXF/3DM)",
        "action_required": "File Generation", "task_category": "Survey Data Deliverables",
        "command_verb": "PROCESS", "default_instrument": "PDS",
        "instruments": ["PDS", "Civil3D", "CAD", "Terramodel"]
    },
    {
        "id": "CT-10", "label": "Volume & Quantity Calculation (Progress / Design / ICQP)",
        "action_required": "Volume Calculation", "task_category": "Survey Data Deliverables",
        "command_verb": "PROCESS", "default_instrument": "PDS",
        "instruments": ["PDS", "Civil3D", "Terramodel", "Excel"]
    },
    {
        "id": "CT-11", "label": "CAD Drawings (As-Built / Sketch / Settlement / Progress)",
        "action_required": "As-Built Drawing", "task_category": "Survey Data Deliverables",
        "command_verb": "DRAFT", "default_instrument": "CAD",
        "instruments": ["CAD", "Civil3D", "Terramodel"]
    },
    {
        "id": "CT-12", "label": "Charts & Profiles (Bathy / Diff / X-Section / Long-Section)",
        "action_required": "Charting/Xsection", "task_category": "Survey Data Deliverables",
        "command_verb": "DRAFT", "default_instrument": "PDS",
        "instruments": ["PDS", "CAD", "Civil3D"]
    },
    {
        "id": "CT-13", "label": "Vessel Software Config & Calibration (PDS / DTPS / System)",
        "action_required": "Survey Software Configuration", "task_category": "Equipment Configuration",
        "command_verb": "SETUP", "default_instrument": "PDS",
        "instruments": ["PDS", "DTPS", "GNSS Rover", "Total Station", "PC"]
    },
    {
        "id": "CT-14", "label": "Survey Reports, Tech Review & Coordination Meetings",
        "action_required": "Survey Report", "task_category": "Office Admin Works",
        "command_verb": "SUBMIT", "default_instrument": "PC",
        "instruments": ["PC", "Teams", "Face to Face", "Excel"]
    }
]

# PINNED 1-CLICK QUICK CHIPS (Fallback defaults for brand-new users)
QUICK_PICK_CHIPS = [
    {"label": "📏 TC-AHDD • Settlement Monitoring", "scope_id": "MWS-05", "task_id": "CT-01", "default_remark": "Road Settlement Monitoring",               "style": "primary"},
    {"label": "📐 TC-AHDD • CAD Drawing",           "scope_id": "MWS-05", "task_id": "CT-11", "default_remark": "Road Settlement / AHDD Drawing",          "style": "secondary"},
    {"label": "🚤 NS-Dumping Area • Bathy Survey",  "scope_id": "MWS-10", "task_id": "CT-06", "default_remark": "Dumping Area Dredging Monitoring",        "style": "info"},
    {"label": "🚤 NS-Trench 8 • Bathy Survey",      "scope_id": "MWS-12", "task_id": "CT-06", "default_remark": "T8 Dredging Monitoring",                  "style": "info"},
    {"label": "🚤 NS-Trench 1 • Bathy Survey",      "scope_id": "MWS-11", "task_id": "CT-06", "default_remark": "T1 Dredging Monitoring",                  "style": "info"},
    {"label": "⚓ OS-Midline • Bathy Survey",       "scope_id": "MWS-14", "task_id": "CT-06", "default_remark": "Midline Tie-In Dredging Monitoring",      "style": "primary"},
    {"label": "⚓ OS-Crossings • Bathy Survey",     "scope_id": "MWS-15", "task_id": "CT-06", "default_remark": "Crossing Mattress / SRI / Burial Survey", "style": "warning"},
    {"label": "📍 TX-Temp Platform • Stake-Out",    "scope_id": "MWS-08", "task_id": "CT-04", "default_remark": "Temp Platform Stake-Out",                 "style": "success"},
]

# Short display tags and styling for dynamic per-user Quick Picks
SHORT_SCOPE_TAGS = {
    "MWS-01": ("🏢 TC-Office Internal", "secondary"),
    "MWS-02": ("📄 TPC-POE / EGST Ext", "danger"),
    "MWS-03": ("🏛️ Abu Dhabi HQ", "dark"),
    "MWS-04": ("📍 TC-Landfall Site", "primary"),
    "MWS-05": ("📏 TC-AHDD", "primary"),
    "MWS-06": ("📦 TC-Tienli", "primary"),
    "MWS-07": ("⚓ TC-Berth 37", "primary"),
    "MWS-08": ("🚧 TX-Temp Platform", "success"),
    "MWS-09": ("🏭 TX-Inside Plant", "success"),
    "MWS-10": ("🚤 NS-Nearshore/Dumping", "info"),
    "MWS-11": ("🚤 NS-Trench 1", "info"),
    "MWS-12": ("🚤 NS-Trench 8", "info"),
    "MWS-13": ("🌊 OS-Mainline T2-T7", "warning"),
    "MWS-14": ("⚓ OS-Midline Tie-In", "warning"),
    "MWS-15": ("⚓ OS-Subsea Crossings", "warning"),
    "MWS-16": ("🛠️ MAR-Vessels/Design", "dark"),
}

SHORT_TASK_TAGS = {
    "CT-01": "Settlement Monitoring",
    "CT-02": "Topo / Progress Survey",
    "CT-03": "As-Built Survey",
    "CT-04": "Stake-Out / Marking",
    "CT-05": "Check / TBM Verify",
    "CT-06": "Bathy Monitoring",
    "CT-07": "Bathy Pre/Post Survey",
    "CT-08": "Geophysical Survey",
    "CT-09": "File & Design Prep",
    "CT-10": "Volume Calculation",
    "CT-11": "CAD Drawing",
    "CT-12": "Charts & Profiles",
    "CT-13": "Software Config/Calib",
    "CT-14": "Report / Tech Review",
}

# Per-User Historical Baseline Seeds from the 1,809-Task Master Register
USER_HISTORICAL_SEEDS = {
    "mateo": [
        ("MWS-16", "CT-12", 50, "Monitoring Survey Bathy & Profile Chart"),
        ("MWS-10", "CT-12", 17, "Nearshore Overview & Diff Chart"),
        ("MWS-16", "CT-10", 17, "Progress / Design Volume Calculation"),
        ("MWS-15", "CT-11", 15, "Crossing Mattress Installation Sketch Drawing"),
        ("MWS-11", "CT-12", 14, "T1 Monitoring Overview & Diff Chart"),
        ("MWS-16", "CT-09", 13, "PDS / Design File Generation"),
        ("MWS-08", "CT-11", 12, "Temp Platform As-Built / Sketch Drawing"),
        ("MWS-12", "CT-12", 11, "T8 Monitoring Overview & Diff Chart"),
    ],
    "mohamad": [
        ("MWS-08", "CT-11", 45, "Tunghsiao Temp Platform Progress / As-Built Drawing"),
        ("MWS-04", "CT-11", 41, "Taichung Site As-Built / Progress Drawing"),
        ("MWS-16", "CT-13", 35, "PDS / DTPS Survey Software Configuration"),
        ("MWS-05", "CT-01", 35, "AHDD Road Settlement Monitoring"),
        ("MWS-08", "CT-02", 34, "Tunghsiao Weekly Progress Survey"),
        ("MWS-05", "CT-11", 32, "Taichung AHDD As-Built / Settlement Drawing"),
        ("MWS-10", "CT-06", 31, "Nearshore Dumping Area Dredging Monitoring"),
        ("MWS-05", "CT-04", 29, "Taichung AHDD Stake-Out / Marking"),
    ],
    "roderick": [
        ("MWS-05", "CT-01", 80, "AHDD Road Settlement Monitoring Survey"),
        ("MWS-08", "CT-02", 35, "Tunghsiao Temp Platform Progress Survey"),
        ("MWS-04", "CT-11", 30, "Taichung Site Layout / As-Built Drawing"),
        ("MWS-04", "CT-02", 23, "Taichung Weekly Progress / Topo Survey"),
        ("MWS-08", "CT-11", 18, "Tunghsiao Temp Platform As-Built Drawing"),
        ("MWS-05", "CT-11", 15, "Taichung AHDD Settlement / Sketch Drawing"),
        ("MWS-05", "CT-04", 15, "Taichung AHDD Pit Stake-Out / Marking"),
        ("MWS-08", "CT-04", 11, "Tunghsiao Temp Platform Stake-Out / Marking"),
    ],
    "danilo": [
        ("MWS-05", "CT-01", 73, "AHDD Road Settlement Monitoring Survey"),
        ("MWS-05", "CT-11", 55, "Taichung AHDD Settlement / Sketch Drawing"),
        ("MWS-05", "CT-03", 24, "Taichung AHDD As-Built Survey"),
        ("MWS-04", "CT-04", 18, "Taichung Site Stake-Out / Marking"),
        ("MWS-08", "CT-04", 16, "Tunghsiao Temp Platform Stake-Out / Marking"),
        ("MWS-08", "CT-11", 16, "Tunghsiao Temp Platform As-Built Drawing"),
        ("MWS-05", "CT-04", 14, "Taichung AHDD Crossover / Thruster Pit Marking"),
        ("MWS-08", "CT-02", 14, "Tunghsiao Temp Platform Progress Survey"),
    ],
    "daryll": [
        ("MWS-10", "CT-06", 16, "Nearshore Dumping Area Dredging Monitoring"),
        ("MWS-05", "CT-01", 14, "AHDD Road Settlement Monitoring"),
        ("MWS-12", "CT-06", 9, "T8 Dredging Monitoring Survey"),
        ("MWS-16", "CT-13", 9, "WS166 / Survey Equipment Calibration & Check"),
        ("MWS-10", "CT-09", 9, "Nearshore Dumping Area File Generation"),
        ("MWS-11", "CT-06", 8, "T1 Dredging Monitoring Survey"),
        ("MWS-14", "CT-06", 7, "Midline Tie-In Dredging Monitoring"),
        ("MWS-02", "CT-14", 7, "TPC-POE / EGST Subcon Survey Report"),
    ],
    "mok": [
        ("MWS-02", "CT-14", 10, "TPC-POE / External Project Survey Report"),
        ("MWS-04", "CT-14", 5, "Taichung Site Inspection & Coordination"),
        ("MWS-08", "CT-02", 3, "Tunghsiao Temp Platform Progress Survey"),
        ("MWS-04", "CT-13", 2, "Survey System Verification"),
    ]
}

def infer_core_task_id(action_req, task_cat):
    """Maps any task's action_required and task_category to one of the 14 Core Survey Tasks (CT-01..CT-14)."""
    a = (action_req or '').lower().strip()
    c = (task_cat or '').lower().strip()
    for ct in LEAN_CORE_TASKS:
        if ct["action_required"].lower() == a and ct["task_category"].lower() == c:
            return ct["id"]
    if "monitoring" in a:
        return "CT-06" if "bathy" in c else "CT-01"
    if "progress" in a and "drw" not in a and "drawing" not in a and "qty" not in a:
        return "CT-06" if "bathy" in c else "CT-02"
    if "as-built survey" in a or "as build survey" in a:
        return "CT-07" if "bathy" in c else "CT-03"
    if "stake-out" in a or "setting" in a or "marking" in a:
        return "CT-04"
    if "check survey" in a or "benchmark" in a:
        return "CT-08" if "geophys" in c else "CT-05"
    if "pre-survey" in a or "post survey" in a or "post-survey" in a:
        return "CT-07" if "bathy" in c else "CT-02"
    if "geophys" in c or "geophys" in a:
        return "CT-08"
    if "file generation" in a or "background" in a or "guidance" in a or "design creation" in a:
        return "CT-09"
    if "volume" in a or "qty" in a:
        return "CT-10"
    if "drawing" in a or "drw" in a or "sketch" in a or "settlement" in a:
        return "CT-11"
    if "chart" in a or "section" in a or "xsection" in a:
        return "CT-12"
    if "config" in a or "calib" in a or "system check" in a:
        return "CT-13"
    if "report" in a or "meeting" in a or "input" in a or "crs" in a:
        return "CT-14"
    return "CT-02"

def get_active_quick_chips(user_name=None, limit=8):
    """
    Dynamically builds the user's Quick-Pick Chips based on the most frequent tasks
    created or executed by that user in SurveyTask history/logs (plus historical seeds).
    """
    target_user = user_name
    if not target_user and current_user and getattr(current_user, 'is_authenticated', False):
        target_user = current_user.name

    pair_counts = Counter()
    pair_remarks = {}

    if target_user:
        try:
            # 1. Query live SurveyTask history created by OR assigned to this user
            # Tasks created by the user get counted directly; tasks assigned also count toward their workflow history
            user_db_tasks = SurveyTask.query.filter(
                or_(
                    SurveyTask.surveyor_name == target_user,
                    SurveyTask.assigned_to.ilike(f"%{target_user}%")
                ),
                SurveyTask.area != '900_Legacy_Data'
            ).order_by(SurveyTask.start_time.desc()).limit(500).all()

            for t in user_db_tasks:
                s_obj = infer_macro_scope_for_task(t)
                s_id = s_obj["id"] if s_obj else "MWS-04"
                c_id = infer_core_task_id(t.action_required, t.task_category)
                key = (s_id, c_id)
                # Weight tasks created by the user slightly higher if they both created and executed
                weight = 2 if (t.surveyor_name == target_user) else 1
                pair_counts[key] += weight
                clean_rem = extract_opening_remark(t.remarks)
                if clean_rem:
                    pair_remarks.setdefault(key, Counter())[clean_rem] += 1
        except Exception:
            pass

        # 2. Enrich with historical Master Register seeds for this user so Day-1 history is rich
        u_lower = target_user.lower()
        for alias_key, seed_list in USER_HISTORICAL_SEEDS.items():
            if alias_key in u_lower:
                for s_id, c_id, h_cnt, default_rem in seed_list:
                    key = (s_id, c_id)
                    pair_counts[key] += h_cnt
                    if default_rem:
                        pair_remarks.setdefault(key, Counter())[default_rem] += 1
                break

    chips = []
    seen_keys = set()

    for (s_id, c_id), total_cnt in pair_counts.most_common(limit):
        if s_id not in SHORT_SCOPE_TAGS or c_id not in SHORT_TASK_TAGS:
            continue
        scope_tag, style_color = SHORT_SCOPE_TAGS[s_id]
        task_tag = SHORT_TASK_TAGS[c_id]
        best_rem = ""
        if (s_id, c_id) in pair_remarks and len(pair_remarks[(s_id, c_id)]) > 0:
            best_rem = pair_remarks[(s_id, c_id)].most_common(1)[0][0]
        chips.append({
            "label": f"{scope_tag} • {task_tag} ({total_cnt}x)",
            "scope_id": s_id,
            "task_id": c_id,
            "default_remark": best_rem[:80],
            "style": style_color,
            "count": total_cnt
        })
        seen_keys.add((s_id, c_id))

    # 3. Also append any custom Admin-pinned chips from AppConfig if space remains
    try:
        config = AppConfig.query.first()
        if config and config.schema_data:
            data = json.loads(config.schema_data)
            for c in data.get("quick_chips", []):
                k = (c.get("scope_id"), c.get("task_id"))
                if k not in seen_keys and len(chips) < limit:
                    chips.append(c)
                    seen_keys.add(k)
    except Exception:
        pass

    # 4. Pad with fallback defaults if a brand-new user has fewer than 6 chips
    for fb in QUICK_PICK_CHIPS:
        k = (fb["scope_id"], fb["task_id"])
        if k not in seen_keys and len(chips) < limit:
            chips.append(fb)
            seen_keys.add(k)

    return chips

# Pre-seeded Top Historical Omni-Search Pairs from the 1,809-Task Register
HISTORICAL_OMNI_SEEDS = [
    ("MWS-05", "CT-01", 116),
    ("MWS-08", "CT-11", 109),
    ("MWS-05", "CT-11", 101),
    ("MWS-04", "CT-11", 86),
    ("MWS-08", "CT-02", 60),
    ("MWS-16", "CT-12", 54),
    ("MWS-16", "CT-09", 38),
    ("MWS-16", "CT-13", 36),
    ("MWS-12", "CT-06", 36),
    ("MWS-10", "CT-06", 35),
    ("MWS-02", "CT-14", 35),
    ("MWS-04", "CT-10", 34),
    ("MWS-04", "CT-02", 34),
    ("MWS-08", "CT-10", 32),
    ("MWS-05", "CT-03", 32),
    ("MWS-05", "CT-04", 32),
    ("MWS-11", "CT-06", 32),
    ("MWS-12", "CT-09", 32),
    ("MWS-08", "CT-04", 30),
    ("MWS-10", "CT-10", 29),
    ("MWS-12", "CT-13", 26),
    ("MWS-14", "CT-09", 21),
    ("MWS-11", "CT-13", 20),
    ("MWS-15", "CT-11", 18),
    ("MWS-14", "CT-06", 18),
    ("MWS-07", "CT-11", 15),
    ("MWS-15", "CT-06", 12),
    ("MWS-06", "CT-02", 10),
    ("MWS-09", "CT-04", 8),
    ("MWS-13", "CT-06", 8),
    ("MWS-01", "CT-14", 15),
    ("MWS-03", "CT-14", 10),
]

SCOPE_BY_CODE = {s["work_scope"]: s for s in LEAN_MACRO_SCOPES}
SCOPE_BY_ID = {s["id"]: s for s in LEAN_MACRO_SCOPES}
TASK_BY_ID = {t["id"]: t for t in LEAN_CORE_TASKS}

def is_user_admin(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return bool(getattr(user, 'is_admin', False) or (user.email in ADMIN_EMAILS))

def extract_opening_remark(raw_remarks):
    """Returns only the user's opening scope details, stripping system audit trail suffixes."""
    if not raw_remarks:
        return ""
    cleaned = str(raw_remarks)
    for marker in [
        "| Acknowledged & Started by",
        "| Closed:",
        "| CANCELED:",
        "| RESTORED FROM ARCHIVE:",
        "Acknowledged & Started by",
        "Closed:",
        "CANCELED:",
        "RESTORED FROM ARCHIVE:"
    ]:
        if marker in cleaned:
            cleaned = cleaned.split(marker)[0]
    return cleaned.strip(" |")

def extract_closing_or_special_remark(raw_remarks):
    """Extracts the Closing Result for KPI Column L, or returns the full clean remark if no closing tag exists."""
    if not raw_remarks:
        return ""
    raw_str = str(raw_remarks)
    if "Closed:" in raw_str:
        closed_part = raw_str.split("Closed:", 1)[-1].strip(" |")
        opening_part = extract_opening_remark(raw_str)
        return f"{opening_part} | Closed: {closed_part}" if opening_part else f"Closed: {closed_part}"
    return extract_opening_remark(raw_str)

def format_clean_description(task, include_opening_remark=False):
    """
    Formats DTR & KPI Column K description.
    When include_opening_remark=True, appends the user's Opening Remark directly into KPI Column K:
    e.g., 'Taichung AHDD Monitoring Survey - [Road Settlement] Ch 0+120'
    """
    if task.work_scope in SCOPE_BY_CODE:
        prefix = SCOPE_BY_CODE[task.work_scope]["kpi_prefix"]
        disc = task.action_required or ""
        base_phrase = f"{prefix} {disc}".strip()
    else:
        loc = task.location.split('_', 1)[-1].replace('_', ' ') if task.location and task.location != 'N/A' else ''
        sub = task.sub_location.split('_', 1)[-1].replace('_', ' ') if task.sub_location and task.sub_location != 'N/A' else ''
        scope = task.work_scope.split('_', 1)[-1] if task.work_scope and task.work_scope != 'N/A' else ''
        for pfx in ['TC-', 'TX-', 'OFC_', 'TC_', 'TX_', 'NS_', 'OS_', 'MAR_']:
            if scope.startswith(pfx):
                scope = scope[len(pfx):]
        scope = scope.replace('_', ' ')
        raw_parts = [loc, sub, scope, task.action_required]
        clean_parts = [p.strip() for p in raw_parts if p and p.strip().lower() != 'general']
        base_phrase = " ".join(clean_parts)

    if include_opening_remark:
        opening_rem = extract_opening_remark(task.remarks)
        if opening_rem and opening_rem.lower() not in base_phrase.lower():
            return f"{base_phrase} - {opening_rem}" if base_phrase else opening_rem

    return base_phrase

def get_merged_macro_scopes_and_cards(file_tree):
    """Merges the 16 canonical Macro Scopes with any custom scopes added via /system_config_hidden."""
    macro_scopes_list = [dict(s) for s in LEAN_MACRO_SCOPES]
    known_codes = {s["work_scope"] for s in macro_scopes_list}
    for area_k, locs_v in (file_tree or {}).items():
        for loc_k, subs_v in (locs_v or {}).items():
            for sub_k, scopes_v in (subs_v or {}).items():
                for sc_code in (scopes_v or []):
                    if sc_code not in known_codes:
                        clean_lbl = sc_code.split('_', 1)[-1].replace('_', ' ')
                        macro_scopes_list.append({
                            "id": f"CUSTOM-{len(macro_scopes_list)+1}",
                            "group": "Custom Added Scopes",
                            "label": f"Custom - {clean_lbl}",
                            "area": area_k, "location": loc_k, "sub_location": sub_k,
                            "work_scope": sc_code, "kpi_prefix": clean_lbl,
                            "hint": "Enter specific details for this custom work scope..."
                        })
                        known_codes.add(sc_code)

    seed_weights = {(m_id, c_id): w for m_id, c_id, w in HISTORICAL_OMNI_SEEDS}
    omni_cards = []
    for s in macro_scopes_list:
        for ct in LEAN_CORE_TASKS:
            hist_w = seed_weights.get((s["id"], ct["id"]), 0)
            omni_cards.append({
                "scope_id": s["id"],
                "task_id": ct["id"],
                "scope_label": s["label"],
                "scope_group": s["group"],
                "area": s["area"],
                "location": s["location"],
                "sub_location": s["sub_location"],
                "work_scope": s["work_scope"],
                "hint": s["hint"],
                "task_label": ct["label"],
                "action_required": ct["action_required"],
                "task_category": ct["task_category"],
                "command_verb": ct["command_verb"],
                "instrument": ct["default_instrument"],
                "weight": hist_w,
                "display": f"[{ct['command_verb']}] {ct['label']}  @  {s['label']}"
            })
    omni_cards.sort(key=lambda x: (-x["weight"], x["scope_label"], x["task_label"]))
    return macro_scopes_list, omni_cards

def infer_macro_scope_for_task(t):
    if t.work_scope in SCOPE_BY_CODE:
        return SCOPE_BY_CODE[t.work_scope]
    area = (t.area or '').lower()
    loc = (t.location or '').lower()
    sub = (t.sub_location or '').lower()
    ws = (t.work_scope or '').lower()
    combined = f"{area} {loc} {sub} {ws}"

    if '120_abu' in combined or 'sts' in combined or 'sws' in combined:
        return SCOPE_BY_ID['MWS-03']
    if 'project-external' in combined or 'tpc' in combined or 'subcon' in combined:
        return SCOPE_BY_ID['MWS-02']
    if area.startswith('100'):
        return SCOPE_BY_ID['MWS-01']
    if 'ahdd' in combined or '212' in combined:
        return SCOPE_BY_ID['MWS-05']
    if 'tienli' in combined or '213' in combined:
        return SCOPE_BY_ID['MWS-06']
    if 'berth' in combined or '214' in combined:
        return SCOPE_BY_ID['MWS-07']
    if 'inside plant' in combined or '222' in combined:
        return SCOPE_BY_ID['MWS-09']
    if 'tunghsiao' in combined or '220' in combined or '221' in combined:
        return SCOPE_BY_ID['MWS-08']
    if area.startswith('200'):
        return SCOPE_BY_ID['MWS-04']
    if 'trench 1' in combined or 'trench_1' in combined or '322' in combined or 't1' in ws:
        return SCOPE_BY_ID['MWS-11']
    if 'trench 8' in combined or 'trench_8' in combined or '323' in combined or 't8' in ws:
        return SCOPE_BY_ID['MWS-12']
    if 'nearshore' in combined or 'dumping' in combined or '320' in combined:
        return SCOPE_BY_ID['MWS-10']
    if 'midline' in combined or '337' in combined:
        return SCOPE_BY_ID['MWS-14']
    if 'crossing' in combined or '338' in combined or '339' in combined or 'mattress' in combined:
        return SCOPE_BY_ID['MWS-15']
    if '310' in combined or 'design' in combined or 'quantity' in combined or '311' in combined or '312' in combined or '313' in combined:
        return SCOPE_BY_ID['MWS-16']
    if '330' in combined or 'offshore' in combined or 'trench' in combined:
        return SCOPE_BY_ID['MWS-13']
    return SCOPE_BY_ID['MWS-04']

@app.after_request
def log_user_usage(response):
    try:
        if current_user.is_authenticated and request.endpoint:
            ignored = {'static', 'api_preview_kpi'}
            if request.endpoint not in ignored and not request.path.startswith('/static'):
                log_entry = UserActivityLog(
                    user_id=current_user.id,
                    user_name=current_user.name,
                    endpoint=request.endpoint,
                    path=request.path[:195],
                    method=request.method
                )
                db.session.add(log_entry)
                db.session.commit()
    except Exception:
        db.session.rollback()
    return response

with app.app_context():
    db.create_all()
    try:
        db.session.execute(text("UPDATE survey_task SET status = 'Open' WHERE status = 'OPEN_REQUESTS'"))
        db.session.execute(text("UPDATE survey_task SET status = 'In Progress' WHERE status IN ('FIELD_ACQUISITION', 'DATA_PROCESSING', 'QA_QC_REVIEW')"))
        db.session.execute(text("UPDATE survey_task SET status = 'Closed' WHERE status = 'CLOSED'"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    for stmt in [
        'ALTER TABLE survey_task ADD COLUMN command_verb VARCHAR(50) DEFAULT \'PERFORM\'',
        'ALTER TABLE preset_task ADD COLUMN command_verb VARCHAR(50)',
        'ALTER TABLE "user" ADD COLUMN initials VARCHAR(10)',
        'ALTER TABLE survey_task ADD COLUMN priority INTEGER DEFAULT 99',
        'ALTER TABLE survey_task ADD COLUMN execution_date DATE',
        'ALTER TABLE preset_task ADD COLUMN remarks TEXT',
        'ALTER TABLE "user" ADD COLUMN is_active BOOLEAN DEFAULT TRUE',
        'ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT FALSE',
        'ALTER TABLE survey_task ADD COLUMN is_urgent BOOLEAN DEFAULT FALSE',
        'ALTER TABLE "user" ADD COLUMN is_approved BOOLEAN DEFAULT TRUE'
    ]:
        try:
            db.session.execute(text(stmt))
            db.session.commit()
        except Exception:
            db.session.rollback()

    try:
        for vip_email in ADMIN_EMAILS:
            vip_user = User.query.filter_by(email=vip_email).first()
            if vip_user and not vip_user.is_admin:
                vip_user.is_admin = True
        db.session.commit()
    except Exception:
        db.session.rollback()

    lean_file_tree = {}
    for s in LEAN_MACRO_SCOPES:
        lean_file_tree.setdefault(s["area"], {}).setdefault(s["location"], {}).setdefault(s["sub_location"], [])
        if s["work_scope"] not in lean_file_tree[s["area"]][s["location"]][s["sub_location"]]:
            lean_file_tree[s["area"]][s["location"]][s["sub_location"]].append(s["work_scope"])

    lean_activities = {}
    for t in LEAN_CORE_TASKS:
        lean_activities.setdefault(t["task_category"], {})[t["action_required"]] = t["instruments"]

    default_requestors = {
        "Logistic": ["Gabe Venema", "Chiao Lin", "Vicky Zeng", "Jamie Tseng", "Madge Lin"],
        "Survey": ["Mok Wai Heng", "Daryll Enano", "Roderick Gonzales Clavel", "Mohamad Abror Hediarto", "Danilo Bartolome", "Mateo Moralleda"],
        "Offshore": ["Walaa Ezzat Gomaa", "Peter Wu", "Kah Chong Ng", "Chun Lai Low", "Evan Su"],
        "Onshore & Dredging": ["Sven Van Guyse", "Haris Andreou", "Eason Ko", "Shiao-Yin Pai", "Chun-Yuan Cheng", "Ibrahim Yalciner", "Subin Vaniyakandiyil", "Katharine Lien", "Berk Savaser", "Harsha Anudeep Botta", "Ayman Sohad Wahby", "Georgios Zormpas", "Nandhu Chandran Kuttikkattu", "Kevin Shen", "Hunter Hsieh", "Lucas Ho", "Yu-Jen LIN"],
        "Quality": ["Oon Kwee Yin", "Victor Wang", "Win Hua Wong", "Allen Cheng", "Renan Torno", "Jake Lu", "James Huang", "Bill Ku", "Chien-Hua Chang", "Carol Kao", "Tim Dai", "Yuan-His Chang", "Toh Lin Sid", "Khairul Aswan Bin Saari"],
        "HSE": ["Sam Yeh", "Paul Tong", "Raymond Huang", "Sean Chu", "Jacqueline Peng", "Jin Wang", "Jeffrey Liu", "Kong Yong Won", "Jet Lee", "Ben Cheng", "Elson Liu", "Sue Peng", "Noah Hsieh", "Yu-Ju Tang", "Vic Wang"],
        "Subcontracts": ["Stewart Ho"],
        "Procurement": ["Karen Fan"],
        "Project Control": ["Ajith John", "Bijo Mathew", "Shang Tse Lee", "Gerard Gonzales Batucan", "Daniel Widjaja", "Joseph Lin", "Eugenia Shen", "Siew-Peng Yap", "Jessica Liu", "Nestor Esler", "Dennis Laga"],
        "Contract": ["Yoon Choy Low", "Tim Lee", "Li Hao Kuo"],
        "ADM": ["Chih Hua Chen", "Becky Wang", "Sylvia Liu", "Benny Yang"],
        "HR": ["Sophie Tseng", "Veronica Hsu", "Patty Lin"],
        "Finance": ["Sharon", "Jimmy Chiu", "Steven Chnag"],
        "Project": ["Ayman Elsherif", "Eric Van Meerendonk", "Richard Stam", "Alex George", "Leo Ho", "Sathyanarayana Dixit", "Gerald Chen"]
    }

    config = AppConfig.query.first()
    if not config:
        master_config = {"file_tree": lean_file_tree, "requestors": default_requestors, "activities": lean_activities}
        db.session.add(AppConfig(schema_data=json.dumps(master_config)))
        db.session.commit()
    else:
        try:
            existing_schema = json.loads(config.schema_data)
            existing_schema["file_tree"] = lean_file_tree
            existing_schema["activities"] = lean_activities
            if "requestors" not in existing_schema or not existing_schema["requestors"]:
                existing_schema["requestors"] = default_requestors
            config.schema_data = json.dumps(existing_schema)
            db.session.commit()
        except Exception:
            db.session.rollback()

    try:
        non_legacy_tasks = SurveyTask.query.filter(SurveyTask.area != '900_Legacy_Data').all()
        migrated_any = False
        for t in non_legacy_tasks:
            if t.work_scope not in SCOPE_BY_CODE:
                old_scope_clean = t.work_scope.split('_', 1)[-1].replace('_', ' ').strip() if t.work_scope else ''
                for pfx in ['TC-', 'TX-']:
                    if old_scope_clean.startswith(pfx):
                        old_scope_clean = old_scope_clean[len(pfx):].strip()
                target_macro = infer_macro_scope_for_task(t)
                if old_scope_clean and old_scope_clean.lower() not in ['general', 'others', 'all crossing']:
                    curr_rem = t.remarks or ''
                    if old_scope_clean.lower() not in curr_rem.lower():
                        t.remarks = f"[{old_scope_clean}] {curr_rem}".strip() if curr_rem else f"[{old_scope_clean}]"
                t.area = target_macro["area"]
                t.location = target_macro["location"]
                t.sub_location = target_macro["sub_location"]
                t.work_scope = target_macro["work_scope"]
                migrated_any = True
        if migrated_any:
            db.session.commit()
    except Exception:
        db.session.rollback()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def resequence_queue(assigned_to_str):
    if not assigned_to_str:
        return
    active_tasks = SurveyTask.query.filter(
        SurveyTask.status.in_(['Open', 'In Progress']),
        SurveyTask.assigned_to == assigned_to_str
    ).order_by(
        SurveyTask.is_urgent.desc(), 
        SurveyTask.priority.asc(), 
        SurveyTask.start_time.asc()
    ).all()
    for idx, t in enumerate(active_tasks, start=1):
        t.priority = idx
    db.session.commit()

# --- AUTHENTICATION ROUTES ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if not email.endswith('@nmdc-group.com'):
            flash('Registration restricted to @nmdc-group.com emails.', 'error')
            return redirect(url_for('register'))
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email address already exists.', 'error')
            return redirect(url_for('register'))
        email_prefix = email.split('@')[0]
        name_parts = email_prefix.split('.')
        formatted_name = f"{name_parts[0].capitalize()} {name_parts[1].capitalize()}" if len(name_parts) >= 2 else email_prefix.capitalize()
        is_vip = True if email in ADMIN_EMAILS else False
        new_user = User(
            email=email,
            name=formatted_name,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
            is_approved=is_vip,
            is_admin=is_vip
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Admin Account created! Please log in.' if is_vip else 'Account created! Please wait for an Admin to approve your access.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            if not user.is_approved:
                flash('Your account is pending admin approval. Please contact management.', 'error')
                return redirect(url_for('login'))
            if not getattr(user, 'is_active', True): 
                flash('Your account has been deactivated. Please contact an Administrator.', 'error')
                return redirect(url_for('login'))   
            login_user(user)
            return redirect(url_for('admin_dashboard') if is_user_admin(user) else url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = s.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            msg = Message('Password Reset Request - NMDC Survey App', recipients=[email])
            msg.body = f"Hello {user.name},\n\nTo reset your password, visit the following link:\n{reset_url}\n\nRegards,\nTHPP Survey Admin Team"
            try:
                mail.send(msg)
                flash('If an account exists for that email, a password reset link has been sent.', 'success')
            except Exception as e:
                flash(f'Server Error: Could not send email. {str(e)}', 'error')
        else:
            flash('If an account exists for that email, a password reset link has been sent.', 'success')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=900)
    except Exception:
        flash('The password reset link is invalid or has expired.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('reset_password', token=token))
        user = User.query.filter_by(email=email).first()
        if user:
            user.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            db.session.commit()
            flash('Your password has been successfully updated! You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

# --- WORKFLOW & KPI ENGINE ---
from apscheduler.schedulers.background import BackgroundScheduler

def auto_archive_tasks():
    with app.app_context(): 
        threshold = datetime.utcnow() - timedelta(days=31)
        closed_tasks = SurveyTask.query.filter_by(status='Closed').all()
        changed = False
        for t in closed_tasks:
            ref_time = t.end_time or t.start_time
            if ref_time and ref_time < threshold:
                t.status = 'Archived'
                changed = True
        if changed:
            db.session.commit()

def build_kpi_rows(target_year=None, target_month=None):
    all_tasks = SurveyTask.query.filter(SurveyTask.status.in_(['Closed', 'Archived'])).all()
    
    def get_sort_date(t):
        if t.execution_date:
            return datetime.combine(t.execution_date, datetime.min.time())
        if t.start_time:
            return t.start_time
        return datetime.min
        
    all_tasks.sort(key=get_sort_date)
    excluded_keywords = ["external meeting", "internal coordination", "survey report", "damage report", "item", "request", "sem update"]
    
    tasks = [t for t in all_tasks if not (t.action_required and any(ex in t.action_required.lower() for ex in excluded_keywords))]
        
    data = []
    month_counters = {} 
    display_index = 1
    
    for task in tasks:
        actual_date = task.execution_date if task.execution_date else task.start_time
        month_str = actual_date.strftime('%m') if actual_date else '00' 
        year_str = actual_date.strftime('%Y') if actual_date else '0000'
        
        month_counters[month_str] = month_counters.get(month_str, 0) + 1
        seq_num = f"{month_counters[month_str]:03d}"
        req_ref = f"TW_{month_str}{seq_num}"
        survey_ref = f"TW_SU_{month_str}{seq_num}"

        if target_month and target_year:
            if month_str != target_month or year_str != target_year:
                continue

        # Column K now includes both the Macro Scope + Discipline AND the Opening Remark!
        desc_phrase = format_clean_description(task, include_opening_remark=True)
        display_start = task.execution_date.strftime('%Y-%m-%d') if task.execution_date else (task.start_time.strftime('%Y-%m-%d %H:%M') if task.start_time else '')
        display_end = task.execution_date.strftime('%Y-%m-%d') if task.execution_date else (task.end_time.strftime('%Y-%m-%d %H:%M') if task.end_time else '')

        data.append({
            'Tender / Project Ref.': '20012',
            'Sl No': display_index,
            'Activity Type': task.task_category or '',
            'Discipline': task.action_required or '',
            'Requestor Ref. #': req_ref,
            'Survey Ref. #': survey_ref,
            'Requestor': task.requestor or '',
            'Assigned to': task.assigned_to or '',
            'Date/Time Received': display_start,
            'Date/Time Completed': display_end,
            'Description of Survey Works': desc_phrase,
            'Special Conditions / Remarks': extract_closing_or_special_remark(task.remarks)
        })
        display_index += 1
    return data

def auto_backup_kpi():
    with app.app_context(): 
        try:
            now = datetime.utcnow()
            data = build_kpi_rows(target_year=now.strftime('%Y'), target_month=now.strftime('%m'))
            df = pd.DataFrame(data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, startrow=2, sheet_name='Master Register')
                worksheet = writer.sheets['Master Register']
                worksheet.cell(row=1, column=5, value="SURVEY ACTIVITY MASTER REGISTER")
                header_month = now.strftime('%B %Y').upper()
                worksheet.cell(row=2, column=1, value=f"MONTH OF {header_month} - SURVEY TEAM (AUTO-BACKUP)")
                for column in worksheet.columns:
                    max_len = max((len(str(cell.value or '')) for cell in column), default=10)
                    worksheet.column_dimensions[column[0].column_letter].width = max_len + 2
            output.seek(0)
            msg = Message(f"🛡️ THPP Survey - Daily Database Backup ({now.strftime('%Y-%m-%d')})", recipients=ADMIN_EMAILS)
            msg.body = f"Hello Admins,\n\nAttached is the automated daily backup of the Master Register pipeline for {header_month}."
            msg.attach(f"THPP_Backup_{now.strftime('%Y%m%d')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", output.read())
            mail.send(msg)
        except Exception as e:
            print(f"CRITICAL BACKUP ERROR: {str(e)}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=auto_archive_tasks, trigger="interval", hours=12)
scheduler.add_job(func=auto_backup_kpi, trigger="cron", hour=15, minute=59) 
scheduler.start()

def escalate_aging_tasks():
    try:
        jammed_tasks = SurveyTask.query.filter(
            SurveyTask.status.in_(['Closed', 'Canceled', 'Archived']),
            SurveyTask.priority < 99
        ).all()
        if jammed_tasks:
            for t in jammed_tasks:
                t.priority = 99
            db.session.commit()

        threshold = datetime.utcnow() - timedelta(hours=48)
        aging_tasks = SurveyTask.query.filter(
            SurveyTask.status.in_(['Open', 'In Progress']),
            SurveyTask.start_time < threshold,
            SurveyTask.is_urgent == False
        ).all()
        if aging_tasks:
            changed_assignees = set()
            for t in aging_tasks:
                t.is_urgent = True 
                if t.assigned_to:
                    changed_assignees.add(t.assigned_to)
            db.session.commit()
            for assignee in changed_assignees:
                resequence_queue(assignee)
    except Exception as e:
        print(f"Escalation Error: {e}")

@app.route('/')
@login_required
def dashboard():
    session['dashboard_view'] = 'user'
    escalate_aging_tasks()

    # Fetch tasks where current_user is either Assigned OR Creator
    candidate_tasks = SurveyTask.query.filter(
        SurveyTask.status != 'Archived',
        or_(
            SurveyTask.assigned_to.ilike(f"%{current_user.name}%"),
            SurveyTask.surveyor_name == current_user.name
        )
    ).order_by(
        SurveyTask.is_urgent.desc(),
        SurveyTask.priority.asc(),
        SurveyTask.start_time.desc()
    ).limit(350).all()

    my_tasks = []
    delegated_tasks = []
    for t in candidate_tasks:
        assigned_list = [u.strip() for u in (t.assigned_to or '').split(',') if u.strip()]
        if current_user.name in assigned_list:
            my_tasks.append(t)
        elif t.surveyor_name == current_user.name:
            delegated_tasks.append(t)

    config = AppConfig.query.first()
    master_schema = json.loads(config.schema_data) if (config and config.schema_data) else {}
    file_tree = master_schema.get("file_tree", {})
    req_dict = master_schema.get("requestors", {})
    macro_scopes_list, omni_cards = get_merged_macro_scopes_and_cards(file_tree)

    is_admin = is_user_admin(current_user)
    all_users = User.query.filter_by(is_approved=True, is_active=True).order_by(User.name.asc()).all()
    initials_map = {u.name: (u.initials.upper() if u.initials else ((u.name.split()[0][0] + u.name.split()[1][0]).upper() if len(u.name.split()) >= 2 else u.name[:2].upper())) for u in all_users}

    return render_template(
        'dashboard.html',
        name=current_user.name,
        tasks=my_tasks,
        delegated_tasks=delegated_tasks,
        users=all_users,
        is_admin=is_admin,
        initials_map=initials_map,
        scope_map=SCOPE_BY_CODE,
        macro_scopes=macro_scopes_list,
        req_dict_json=json.dumps(req_dict),
        macro_scopes_json=json.dumps(macro_scopes_list),
        core_tasks_json=json.dumps(LEAN_CORE_TASKS),
        omni_cards_json=json.dumps(omni_cards),
        quick_chips_json=json.dumps(get_active_quick_chips(current_user.name))
    )

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not is_user_admin(current_user):
        flash('Access Denied: You do not have Admin privileges.', 'error')
        return redirect(url_for('dashboard'))

    session['dashboard_view'] = 'admin'
    escalate_aging_tasks()
    all_tasks = SurveyTask.query.filter(SurveyTask.status != 'Archived')         .order_by(SurveyTask.is_urgent.desc(), SurveyTask.priority.asc(), SurveyTask.start_time.desc())         .limit(300).all()
    users = User.query.order_by(User.name.asc()).all()
    initials_map = {u.name: (u.initials.upper() if u.initials else ((u.name.split()[0][0] + u.name.split()[1][0]).upper() if len(u.name.split()) >= 2 else u.name[:2].upper())) for u in users}

    now = datetime.utcnow()
    months_data = []
    for i in range(2, -1, -1):
        m = now.month - i
        y = now.year
        if m <= 0:
            m += 12
            y -= 1
        end_day = now.day if i == 0 else calendar.monthrange(y, m)[1]
        months_data.append({'year': y, 'month': m, 'month_name': calendar.month_name[m], 'end_day': end_day, 'key': f"{y}-{m:02d}", 'count': 0})
        
    completed_tasks = SurveyTask.query.filter(SurveyTask.status.in_(['Closed', 'Archived'])).all()
    for t in completed_tasks:
        actual_dt = t.execution_date if t.execution_date else t.start_time
        if actual_dt:
            t_key = actual_dt.strftime('%Y-%m')
            for md in months_data:
                if md['key'] == t_key:
                    md['count'] += 1
                    break
    return render_template('admin_dashboard.html', name=current_user.name, tasks=all_tasks, users=users, kpi_summary_json=json.dumps(months_data), initials_map=initials_map, scope_map=SCOPE_BY_CODE, macro_scopes=LEAN_MACRO_SCOPES)

@app.route('/usage_telemetry')
@login_required
def usage_telemetry():
    if not is_user_admin(current_user):
        flash('Access Denied: Admins only.', 'error')
        return redirect(url_for('dashboard'))

    # Filter parameters
    selected_user = request.args.get('user', '').strip()
    selected_endpoint = request.args.get('endpoint', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = request.args.get('per_page', 100, type=int)
    if per_page not in [50, 100, 250, 500, 1000]:
        per_page = 100

    query = UserActivityLog.query
    if selected_user:
        query = query.filter(UserActivityLog.user_name == selected_user)
    if selected_endpoint:
        query = query.filter(UserActivityLog.endpoint == selected_endpoint)
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, '%Y-%m-%d') - timedelta(hours=8)
            query = query.filter(UserActivityLog.timestamp >= dt_from)
        except Exception:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1) - timedelta(hours=8)
            query = query.filter(UserActivityLog.timestamp < dt_to)
        except Exception:
            pass

    # Query ALL matching logs (no artificial 500 limit!)
    all_matching_logs = query.order_by(UserActivityLog.timestamp.desc()).all()
    total_logs_count = len(all_matching_logs)

    page_counts = Counter(l.endpoint for l in all_matching_logs).most_common()
    user_counts = Counter(l.user_name for l in all_matching_logs).most_common()

    # All distinct users and endpoints for filter dropdowns
    all_distinct_users = sorted([r[0] for r in db.session.query(UserActivityLog.user_name).distinct().all() if r[0]])
    all_distinct_endpoints = sorted([r[0] for r in db.session.query(UserActivityLog.endpoint).distinct().all() if r[0]])

    # Paginate stream
    total_pages = max(1, (total_logs_count + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    start_idx = (page - 1) * per_page
    paginated_logs = all_matching_logs[start_idx:start_idx + per_page]

    # Also compute All-Time Historical Task Participation from SurveyTask (across all database tasks)
    all_db_tasks = SurveyTask.query.filter(SurveyTask.area != '900_Legacy_Data').all()
    hist_assigned_counts = Counter()
    hist_created_counts = Counter()
    hist_closed_counts = Counter()
    for t in all_db_tasks:
        if t.surveyor_name:
            hist_created_counts[t.surveyor_name.strip()] += 1
        for u_part in (t.assigned_to or '').split(','):
            clean_u = u_part.strip()
            if clean_u:
                hist_assigned_counts[clean_u] += 1
                if t.status in ['Closed', 'Archived']:
                    hist_closed_counts[clean_u] += 1

    all_task_users = sorted(set(hist_assigned_counts.keys()) | set(hist_created_counts.keys()))
    historical_user_stats = []
    for u_name in all_task_users:
        historical_user_stats.append({
            'name': u_name,
            'assigned': hist_assigned_counts[u_name],
            'closed': hist_closed_counts[u_name],
            'created': hist_created_counts[u_name],
            'total_touchpoints': hist_assigned_counts[u_name] + hist_created_counts[u_name]
        })
    historical_user_stats.sort(key=lambda x: -x['assigned'])

    html = """
    <!DOCTYPE html>
    <html><head><title>Usage Telemetry - NMDC</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f7f6; }
        .card { border-radius: 10px; border: none; }
        .tw-time { font-family: monospace; font-size: 12.5px; color: #0f5132; font-weight: bold; }
    </style>
    </head>
    <body class="p-4">
    <div class="container-fluid" style="max-width: 1400px;">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
            <div>
                <h3 class="fw-bold mb-0">📈 User Usage & Page Telemetry Center</h3>
                <small class="text-muted">Full unthrottled activity logs (Taiwan Time UTC+8) + All-Time Historical Task Participation</small>
            </div>
            <div class="d-flex gap-2">
                <a href="/export_telemetry_excel?user={{ selected_user }}&endpoint={{ selected_endpoint }}&date_from={{ date_from }}&date_to={{ date_to }}" class="btn btn-success fw-bold">📥 Export Telemetry (.xlsx)</a>
                <a href="/admin_dashboard" class="btn btn-primary fw-bold">⬅ Back to Admin Dashboard</a>
            </div>
        </div>

        <!-- FILTER BAR -->
        <form method="GET" action="/usage_telemetry" class="card shadow-sm p-3 mb-4 bg-white">
            <div class="row g-2 align-items-end">
                <div class="col-md-3">
                    <label class="form-label small fw-bold mb-1">Filter by User</label>
                    <select name="user" class="form-select form-select-sm">
                        <option value="">All Users ({{ all_distinct_users|length }})</option>
                        {% for u in all_distinct_users %}
                        <option value="{{ u }}" {% if u == selected_user %}selected{% endif %}>{{ u }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-3">
                    <label class="form-label small fw-bold mb-1">Filter by Page / Endpoint</label>
                    <select name="endpoint" class="form-select form-select-sm">
                        <option value="">All Endpoints ({{ all_distinct_endpoints|length }})</option>
                        {% for ep in all_distinct_endpoints %}
                        <option value="{{ ep }}" {% if ep == selected_endpoint %}selected{% endif %}>{{ ep }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label small fw-bold mb-1">From Date (TW)</label>
                    <input type="date" name="date_from" value="{{ date_from }}" class="form-control form-control-sm">
                </div>
                <div class="col-md-2">
                    <label class="form-label small fw-bold mb-1">To Date (TW)</label>
                    <input type="date" name="date_to" value="{{ date_to }}" class="form-control form-control-sm">
                </div>
                <div class="col-md-1">
                    <label class="form-label small fw-bold mb-1">Rows/Page</label>
                    <select name="per_page" class="form-select form-select-sm">
                        {% for pp in [50, 100, 250, 500, 1000] %}
                        <option value="{{ pp }}" {% if pp == per_page %}selected{% endif %}>{{ pp }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-1 d-flex gap-1">
                    <button type="submit" class="btn btn-sm btn-dark fw-bold w-100">Filter</button>
                    <a href="/usage_telemetry" class="btn btn-sm btn-outline-secondary">↺</a>
                </div>
            </div>
        </form>

        <div class="row mb-4 g-3">
            <!-- LIVE PAGE TELEMETRY: ALL ENDPOINTS -->
            <div class="col-md-4">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-dark text-white fw-bold d-flex justify-content-between align-items-center">
                        <span>Top Pages / Actions Used (All {{ page_counts|length }})</span>
                        <span class="badge bg-warning text-dark">{{ total_logs_count }} total hits</span>
                    </div>
                    <div style="max-height: 360px; overflow-y: auto;">
                        <ul class="list-group list-group-flush">
                        {% for ep, cnt in page_counts %}
                            <li class="list-group-item d-flex justify-content-between align-items-center py-2">
                                <code>{{ ep }}</code>
                                <span class="badge bg-primary rounded-pill">{{ cnt }} hits</span>
                            </li>
                        {% endfor %}
                        </ul>
                    </div>
                </div>
            </div>

            <!-- LIVE PAGE TELEMETRY: ALL USERS -->
            <div class="col-md-4">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-secondary text-white fw-bold d-flex justify-content-between align-items-center">
                        <span>Live Page Activity by User (Since Oct 26)</span>
                        <span class="badge bg-light text-dark">{{ user_counts|length }} users</span>
                    </div>
                    <div style="max-height: 360px; overflow-y: auto;">
                        <ul class="list-group list-group-flush">
                        {% for uname, cnt in user_counts %}
                            <li class="list-group-item d-flex justify-content-between align-items-center py-2">
                                <strong>{{ uname }}</strong>
                                <span class="badge bg-success rounded-pill">{{ cnt }} actions</span>
                            </li>
                        {% endfor %}
                        </ul>
                    </div>
                </div>
            </div>

            <!-- ALL-TIME HISTORICAL TASK TELEMETRY (FROM SURVEY_TASK DB) -->
            <div class="col-md-4">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-primary text-white fw-bold d-flex justify-content-between align-items-center">
                        <span>🏆 All-Time Task History (Database Tasks)</span>
                        <span class="badge bg-light text-primary">{{ all_db_tasks_count }} tasks</span>
                    </div>
                    <div class="table-responsive" style="max-height: 360px; overflow-y: auto;">
                        <table class="table table-sm table-hover mb-0" style="font-size: 12.5px;">
                            <thead class="table-light" style="position: sticky; top: 0;">
                                <tr><th>Surveyor</th><th class="text-center">Assigned</th><th class="text-center">Closed</th><th class="text-center">Created</th></tr>
                            </thead>
                            <tbody>
                            {% for hs in historical_user_stats %}
                                <tr>
                                    <td><strong>{{ hs.name }}</strong></td>
                                    <td class="text-center"><span class="badge bg-primary">{{ hs.assigned }}</span></td>
                                    <td class="text-center"><span class="badge bg-success">{{ hs.closed }}</span></td>
                                    <td class="text-center"><span class="badge bg-secondary">{{ hs.created }}</span></td>
                                </tr>
                            {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- FULL PAGINATED ACTIVITY STREAM -->
        <div class="card shadow-sm">
            <div class="card-header bg-white fw-bold d-flex justify-content-between align-items-center flex-wrap gap-2 py-3">
                <span>🕒 Full Live Activity Stream (Showing {{ start_idx + 1 if total_logs_count > 0 else 0 }}–{{ start_idx + paginated_logs|length }} of {{ total_logs_count }} logged events)</span>
                <div class="d-flex align-items-center gap-2">
                    <span class="small text-muted">Page {{ page }} of {{ total_pages }}</span>
                    <div class="btn-group btn-group-sm">
                        <a href="/usage_telemetry?user={{ selected_user }}&endpoint={{ selected_endpoint }}&date_from={{ date_from }}&date_to={{ date_to }}&per_page={{ per_page }}&page={{ page - 1 }}" class="btn btn-outline-secondary {% if page <= 1 %}disabled{% endif %}">◀ Prev</a>
                        <a href="/usage_telemetry?user={{ selected_user }}&endpoint={{ selected_endpoint }}&date_from={{ date_from }}&date_to={{ date_to }}&per_page={{ per_page }}&page={{ page + 1 }}" class="btn btn-outline-secondary {% if page >= total_pages %}disabled{% endif %}">Next ▶</a>
                    </div>
                </div>
            </div>
            <div class="table-responsive">
                <table class="table table-sm table-striped table-hover mb-0" style="font-size: 13px;">
                    <thead class="table-dark">
                        <tr>
                            <th>#</th>
                            <th>Taiwan Time (UTC+8)</th>
                            <th>UTC Time</th>
                            <th>User</th>
                            <th>Endpoint</th>
                            <th>Path</th>
                            <th>Method</th>
                        </tr>
                    </thead>
                    <tbody>
                    {% for l in paginated_logs %}
                        <tr>
                            <td class="text-muted">{{ total_logs_count - (start_idx + loop.index0) }}</td>
                            <td class="tw-time">{{ (l.timestamp + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S') }}</td>
                            <td class="text-muted small">{{ l.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                            <td><strong>{{ l.user_name }}</strong></td>
                            <td><code>{{ l.endpoint }}</code></td>
                            <td>{{ l.path }}</td>
                            <td><span class="badge {% if l.method == 'POST' %}bg-warning text-dark{% else %}bg-light text-dark border{% endif %}">{{ l.method }}</span></td>
                        </tr>
                    {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div></body></html>
    """
    return render_template_string(
        html,
        paginated_logs=paginated_logs,
        total_logs_count=total_logs_count,
        page_counts=page_counts,
        user_counts=user_counts,
        all_distinct_users=all_distinct_users,
        all_distinct_endpoints=all_distinct_endpoints,
        selected_user=selected_user,
        selected_endpoint=selected_endpoint,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        start_idx=start_idx,
        timedelta=timedelta,
        historical_user_stats=historical_user_stats,
        all_db_tasks_count=len(all_db_tasks)
    )

@app.route('/export_telemetry_excel')
@login_required
def export_telemetry_excel():
    if not is_user_admin(current_user):
        return "Unauthorized", 403
    selected_user = request.args.get('user', '').strip()
    selected_endpoint = request.args.get('endpoint', '').strip()
    query = UserActivityLog.query
    if selected_user:
        query = query.filter(UserActivityLog.user_name == selected_user)
    if selected_endpoint:
        query = query.filter(UserActivityLog.endpoint == selected_endpoint)
    logs = query.order_by(UserActivityLog.timestamp.desc()).all()
    rows = [{
        'Log ID': l.id,
        'Taiwan Time (UTC+8)': (l.timestamp + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S') if l.timestamp else '',
        'UTC Time': l.timestamp.strftime('%Y-%m-%d %H:%M:%S') if l.timestamp else '',
        'User Name': l.user_name,
        'Endpoint': l.endpoint,
        'Path': l.path,
        'HTTP Method': l.method
    } for l in logs]
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Usage Telemetry')
    output.seek(0)
    return send_file(output, download_name=f"NMDC_Usage_Telemetry_{datetime.utcnow().strftime('%Y%m%d')}.xlsx", as_attachment=True)

@app.route('/update_initials/<int:user_id>', methods=['POST'])
@login_required
def update_initials(user_id):
    if not is_user_admin(current_user):
        return "Unauthorized", 403
    user = User.query.get_or_404(user_id)
    user.initials = request.form.get('initials', '').strip().upper()
    db.session.commit()
    flash(f"Updated initials for {user.name} to '{user.initials}'", 'success')
    return redirect(url_for('manage_users'))

@app.route('/toggle_admin/<int:user_id>', methods=['POST'])
@login_required
def toggle_admin(user_id):
    if not is_user_admin(current_user):
        return "Unauthorized", 403
    user = User.query.get_or_404(user_id)
    if user.email in ADMIN_EMAILS:
        flash('VIP Super-Admins cannot have admin privileges revoked.', 'error')
        return redirect(url_for('manage_users'))
    user.is_admin = not bool(getattr(user, 'is_admin', False))
    db.session.commit()
    flash(f"User {user.name} has been {'promoted to Admin' if user.is_admin else 'set to Standard User'}.", 'success')
    return redirect(url_for('manage_users'))

@app.route('/archive')
@login_required
def archive_page():
    if not is_user_admin(current_user):
        return redirect(url_for('dashboard'))
    archived_tasks = SurveyTask.query.filter_by(status='Archived').order_by(SurveyTask.start_time.desc()).all()
    return render_template('archive.html', tasks=archived_tasks)

@app.route('/restore_task/<int:task_id>', methods=['POST'])
@login_required
def restore_task(task_id):
    if not is_user_admin(current_user):
        return "Unauthorized", 403
    task = SurveyTask.query.get_or_404(task_id)
    task.status = 'Closed'
    restore_note = f"RESTORED FROM ARCHIVE: {datetime.utcnow().strftime('%Y-%m-%d')}"
    task.remarks = f"{task.remarks} | {restore_note}" if task.remarks else restore_note
    db.session.commit()
    resequence_queue(task.assigned_to)
    flash(f'Task {task_id} was successfully restored to the dashboard.', 'success')
    return redirect(request.referrer or url_for('archive_page'))

@app.route('/manage_users')
@login_required
def manage_users():
    if not is_user_admin(current_user):
        return redirect(url_for('dashboard'))
    users = User.query.order_by(User.name.asc()).all()
    return render_template('manage_users.html', users=users, admin_emails=ADMIN_EMAILS)

@app.route('/toggle_active/<int:user_id>', methods=['POST'])
@login_required
def toggle_active(user_id):
    if not is_user_admin(current_user):
        return "Unauthorized", 403
    user = User.query.get_or_404(user_id)
    user.is_active = not getattr(user, 'is_active', True) 
    db.session.commit()
    flash(f"User {user.name} has been {'reactivated' if user.is_active else 'deactivated'}.", 'success')
    return redirect(url_for('manage_users'))

@app.route('/cleanup')
@login_required
def cleanup_tasks():
    if not is_user_admin(current_user):
        return redirect(url_for('dashboard'))
    tasks = SurveyTask.query.order_by(SurveyTask.start_time.desc()).all()
    return render_template('cleanup.html', tasks=tasks)

@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    if not is_user_admin(current_user):
        return "Unauthorized", 403
    task = SurveyTask.query.get_or_404(task_id)
    assigned_str = task.assigned_to
    db.session.delete(task)
    db.session.commit()
    resequence_queue(assigned_str)
    flash(f'Task {task_id} was permanently deleted.', 'success')
    return redirect(url_for('cleanup_tasks'))

@app.route('/approve_user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if not is_user_admin(current_user):
        return "Unauthorized", 403
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash(f'User {user.name} has been approved and can now log in.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not is_user_admin(current_user):
        return "Unauthorized", 403
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.name} has been rejected and deleted.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/migrate', methods=['GET', 'POST'])
@login_required
def migrate_data():
    if not is_user_admin(current_user):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        file = request.files.get('excel_file')
        if not file or not file.filename.endswith(('.xlsx', '.xls')):
            flash('Please upload a valid Excel file.', 'error')
            return redirect(url_for('migrate_data'))
        try:
            excel_file = pd.ExcelFile(file)
            target_sheet = next((s for s in excel_file.sheet_names if 'master' in s.lower() or 'combined' in s.lower()), excel_file.sheet_names[0])
            df_raw = pd.read_excel(file, sheet_name=target_sheet, header=None).fillna('')
            header_row_idx = -1
            col_map = {}
            for idx, row in df_raw.iterrows():
                row_vals = [str(x).strip().lower() for x in row.values]
                if any(k in ' '.join(row_vals) for k in ['from date', 'date/time received', 'description of survey']):
                    header_row_idx = idx
                    for col_idx, val in enumerate(row_vals):
                        if 'from date' in val or 'date/time received' in val: col_map['date'] = col_idx
                        elif 'requestor' in val and 'ref' not in val: col_map['req'] = col_idx
                        elif 'pic' in val or 'assigned to' in val: col_map['pic'] = col_idx
                        elif 'involve' in val: col_map['person'] = col_idx
                        elif 'activity type' in val: col_map['act'] = col_idx
                        elif 'discipline' in val: col_map['disc'] = col_idx
                        elif 'description' in val or 'daily activities' in val: col_map['desc'] = col_idx
                        elif 'detail' in val or 'condition' in val or 'remarks' in val: col_map['rem2'] = col_idx
                    break
            if header_row_idx == -1:
                flash("Error: Could not find headers (like 'From Date' or 'Date/Time Received').", 'error')
                return redirect(url_for('migrate_data'))
            migrated_count = 0
            for idx in range(header_row_idx + 1, len(df_raw)):
                row = df_raw.iloc[idx].values
                def get_val(key):
                    return str(row[col_map[key]]).strip() if key in col_map and col_map[key] < len(row) else ''
                date_val, desc = get_val('date'), get_val('desc')
                if not date_val and not desc:
                    continue
                if '1900-01-07' in date_val:
                    continue
                parsed = pd.to_datetime(date_val, errors='coerce')
                start_date = parsed.to_pydatetime() if not pd.isna(parsed) else datetime.utcnow()
                assigned = get_val('pic') or get_val('person')
                safe_scope = (desc[:95] + '...') if len(desc) > 95 else (desc or "Historical_Task")
                task = SurveyTask(
                    surveyor_name="Legacy_Import",
                    assigned_to=assigned[:100],
                    requestor=get_val('req')[:100],
                    task_category=get_val('act')[:100],
                    action_required=get_val('disc')[:100],
                    instrument="Legacy_Data",
                    area="900_Legacy_Data",
                    location="DPR_Import",
                    sub_location=start_date.strftime('%Y_%m'),
                    work_scope=safe_scope,
                    remarks=get_val('rem2'),
                    status="Closed",
                    priority=99,
                    start_time=start_date,
                    end_time=start_date 
                )
                db.session.add(task)
                migrated_count += 1
            db.session.commit()
            flash(f'Successfully migrated {migrated_count} historical tasks!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Migration Error: {str(e)}', 'error')
            return redirect(url_for('migrate_data'))
    return render_template('migration.html')

@app.route('/system_config_hidden', methods=['GET', 'POST'])
@login_required
def hidden_config():
    if not is_user_admin(current_user):
        return redirect(url_for('dashboard'))
    config = AppConfig.query.first()
    master_schema = json.loads(config.schema_data) if config else {}
    for k in ["file_tree", "requestors", "activities"]:
        master_schema.setdefault(k, {})
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_dept':
            dept = request.form.get('department').strip()
            if dept: master_schema['requestors'].setdefault(dept, [])
        elif action == 'delete_dept':
            master_schema['requestors'].pop(request.form.get('department'), None)
        elif action == 'add_requestor':
            dept, name = request.form.get('department'), request.form.get('name').strip()
            if dept in master_schema['requestors'] and name not in master_schema['requestors'][dept]:
                master_schema['requestors'][dept].append(name)
                master_schema['requestors'][dept].sort()
        elif action == 'delete_requestor':
            dept, name = request.form.get('department'), request.form.get('name')
            if dept in master_schema['requestors'] and name in master_schema['requestors'][dept]:
                master_schema['requestors'][dept].remove(name)
        elif action == 'add_area':
            area = request.form.get('area').strip()
            if area: master_schema['file_tree'].setdefault(area, {})
        elif action == 'delete_area':
            master_schema['file_tree'].pop(request.form.get('area'), None)
        elif action == 'add_location':
            area, loc = request.form.get('area'), request.form.get('location').strip()
            if area in master_schema['file_tree']: master_schema['file_tree'][area].setdefault(loc, {})
        elif action == 'delete_location':
            area, loc = request.form.get('area'), request.form.get('location')
            if area in master_schema['file_tree']: master_schema['file_tree'][area].pop(loc, None)
        elif action == 'add_sub':
            area, loc, sub = request.form.get('area'), request.form.get('location'), request.form.get('sub_location').strip()
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area]:
                master_schema['file_tree'][area][loc].setdefault(sub, [])
        elif action == 'delete_sub':
            area, loc, sub = request.form.get('area'), request.form.get('location'), request.form.get('sub_location')
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area]:
                master_schema['file_tree'][area][loc].pop(sub, None)
        elif action == 'add_scope':
            area, loc, sub, scope = request.form.get('area'), request.form.get('location'), request.form.get('sub_location'), request.form.get('scope').strip()
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area] and sub in master_schema['file_tree'][area][loc]:
                if scope not in master_schema['file_tree'][area][loc][sub]:
                    master_schema['file_tree'][area][loc][sub].append(scope)
                    master_schema['file_tree'][area][loc][sub].sort()
        elif action == 'delete_scope':
            area, loc, sub, scope = request.form.get('area'), request.form.get('location'), request.form.get('sub_location'), request.form.get('scope')
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area] and sub in master_schema['file_tree'][area][loc]:
                if scope in master_schema['file_tree'][area][loc][sub]:
                    master_schema['file_tree'][area][loc][sub].remove(scope)
        config.schema_data = json.dumps(master_schema)
        db.session.commit()
        flash('System Configuration Updated!', 'success')
        return redirect(url_for('hidden_config'))
    return render_template('hidden_admin.html', master_schema_json=json.dumps(master_schema))

# --- UNIFIED OMNI-SEARCH + 16 MACRO WORK SCOPES + 14 CORE TASKS ---
@app.route('/save_quick_chips', methods=['POST'])
@login_required
def save_quick_chips():
    if not is_user_admin(current_user):
        return jsonify({'success': False, 'message': 'Admins only.'}), 403
    try:
        payload = request.get_json() or {}
        chips = payload.get('chips')
        if not isinstance(chips, list):
            return jsonify({'success': False, 'message': 'Invalid chips list.'}), 400
        config = AppConfig.query.first()
        schema = json.loads(config.schema_data) if (config and config.schema_data) else {}
        schema['quick_chips'] = chips
        if not config:
            config = AppConfig(schema_data=json.dumps(schema))
            db.session.add(config)
        else:
            config.schema_data = json.dumps(schema)
        db.session.commit()
        return jsonify({'success': True, 'chips': chips})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/new_task', methods=['GET', 'POST'])
@login_required
def new_task():
    try:
        config = AppConfig.query.first()
        master_schema = json.loads(config.schema_data) if config else {}
        file_tree = master_schema.get("file_tree", {})
        req_dict = master_schema.get("requestors", {})
        
        if request.method == 'POST':
            check_area = request.form.get('area')
            check_scope = request.form.get('work_scope')
            if not check_area or not check_scope:
                flash("Validation Error: Please select a Work Scope.", "error")
                return redirect(request.url)
        
            req_dept = request.form.get('requestor_dept') or 'General'
            req_name = request.form.get('requestor_name')
            merged_requestor = f"{req_dept} - {req_name}"
            
            assigned_list = request.form.getlist('assigned_to')
            assigned_str = ", ".join([a for a in assigned_list if a.strip()])
            command_verb_val = request.form.get('command_verb', 'PERFORM') 
            
            if request.form.get('save_preset') == 'true':
                p_name = request.form.get('preset_name') or f"{check_area} - {check_scope}"
                db.session.add(PresetTask(
                    user_id=current_user.id, preset_name=p_name, req_dept=req_dept, req_name=req_name,
                    assigned_to=assigned_str, command_verb=command_verb_val, task_category=request.form.get('task_category'),
                    area=check_area, location=request.form.get('location'), 
                    sub_location=request.form.get('sub_location'), work_scope=check_scope,
                    instrument=request.form.get('instrument'), action_required=request.form.get('action_required'),
                    remarks=request.form.get('remarks')
                ))
            
            ref_links = request.form.getlist('reference_link')
            ref_links_str = " | ".join([link for link in ref_links if link.strip()])
            is_urgent_val = True if request.form.get('is_urgent') else False
            p_val = request.form.get('priority')
            priority_val = int(p_val) if p_val and p_val.isdigit() else 99

            new_survey = SurveyTask(
                surveyor_name=current_user.name, assigned_to=assigned_str, requestor=merged_requestor,
                command_verb=command_verb_val, task_category=request.form.get('task_category'), 
                instrument=request.form.get('instrument'), action_required=request.form.get('action_required'),
                area=check_area, location=request.form.get('location'), sub_location=request.form.get('sub_location'),
                work_scope=check_scope, remarks=request.form.get('remarks'), reference_links=ref_links_str,
                is_urgent=is_urgent_val, priority=priority_val
            )
            db.session.add(new_survey)
            db.session.commit()      
            resequence_queue(assigned_str)

            flash('New task opened successfully!', 'success')
            return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))

        macro_scopes_list, omni_cards = get_merged_macro_scopes_and_cards(file_tree)
        scope_label_by_code = {s["work_scope"]: s["label"] for s in macro_scopes_list}

        user_tasks = SurveyTask.query.filter(
            or_(
                SurveyTask.surveyor_name == current_user.name,
                SurveyTask.assigned_to.ilike(f"%{current_user.name}%")
            ),
            SurveyTask.area != '900_Legacy_Data'
        ).order_by(SurveyTask.start_time.desc()).limit(250).all()

        pattern_counter = Counter()
        pattern_meta = {}
        req_counter = Counter()
        recent_history = []

        for t in user_tasks:
            if not t.work_scope or not t.action_required:
                continue
            req_person = t.requestor.split(' - ', 1)[-1].strip() if t.requestor and ' - ' in t.requestor else (t.requestor or '')
            if req_person:
                req_counter[req_person] += 1

            sc_lbl = scope_label_by_code.get(t.work_scope, t.work_scope)
            key = (t.work_scope, t.action_required, t.instrument or '', t.task_category or '')
            pattern_counter[key] += 1
            if key not in pattern_meta:
                pattern_meta[key] = {
                    'command_verb': t.command_verb or 'PERFORM',
                    'task_category': t.task_category or '',
                    'action_required': t.action_required or '',
                    'instrument': t.instrument or '',
                    'area': t.area or '',
                    'location': t.location or '',
                    'sub_location': t.sub_location or '',
                    'work_scope': t.work_scope or '',
                    'scope_label': sc_lbl
                }
            recent_history.append({
                'date': (t.execution_date or t.start_time).strftime('%Y-%m-%d') if (t.execution_date or t.start_time) else '',
                'req_name': req_person,
                'command_verb': t.command_verb or 'PERFORM',
                'task_category': t.task_category or '',
                'action_required': t.action_required or '',
                'instrument': t.instrument or '',
                'area': t.area or '',
                'location': t.location or '',
                'sub_location': t.sub_location or '',
                'work_scope': t.work_scope or '',
                'scope_label': sc_lbl,
                'remarks': extract_opening_remark(t.remarks)[:65]
            })

        # Enrich personal pattern_counter with user's historical Master Register seeds
        u_lower = current_user.name.lower()
        for alias_key, seed_list in USER_HISTORICAL_SEEDS.items():
            if alias_key in u_lower:
                for s_id, c_id, h_cnt, default_rem in seed_list:
                    if s_id in SCOPE_BY_ID and c_id in TASK_BY_ID:
                        s_obj = SCOPE_BY_ID[s_id]
                        t_obj = TASK_BY_ID[c_id]
                        key = (s_obj['work_scope'], t_obj['action_required'], t_obj['default_instrument'], t_obj['task_category'])
                        pattern_counter[key] += h_cnt
                        if key not in pattern_meta:
                            pattern_meta[key] = {
                                'command_verb': t_obj['command_verb'],
                                'task_category': t_obj['task_category'],
                                'action_required': t_obj['action_required'],
                                'instrument': t_obj['default_instrument'],
                                'area': s_obj['area'],
                                'location': s_obj['location'],
                                'sub_location': s_obj['sub_location'],
                                'work_scope': s_obj['work_scope'],
                                'scope_label': s_obj['label'],
                                'remarks': default_rem
                            }
                break

        frequent_patterns = []
        for key, cnt in pattern_counter.most_common(100):
            entry = dict(pattern_meta[key])
            entry['count'] = cnt
            frequent_patterns.append(entry)

        if len(frequent_patterns) < 3:
            for oc in omni_cards[:3 - len(frequent_patterns)]:
                frequent_patterns.append({
                    'command_verb': oc['command_verb'],
                    'task_category': oc['task_category'],
                    'action_required': oc['action_required'],
                    'instrument': oc['instrument'],
                    'area': oc['area'],
                    'location': oc['location'],
                    'sub_location': oc['sub_location'],
                    'work_scope': oc['work_scope'],
                    'scope_label': oc['scope_label'],
                    'count': oc['weight']
                })

        top_requestors = [{'name': name, 'count': cnt} for name, cnt in req_counter.most_common(3)]
        user_presets = PresetTask.query.filter_by(user_id=current_user.id).all()
        presets_dict = {
            p.id: {
                'req_dept': p.req_dept or "", 'req_name': p.req_name or "", 'assigned_to': p.assigned_to or "",
                'command_verb': p.command_verb or "PERFORM",
                'task_category': p.task_category or "", 'area': p.area or "", 'location': p.location or "",
                'sub_location': p.sub_location or "", 'work_scope': p.work_scope or "",
                'instrument': p.instrument or "", 'action_required': p.action_required or "",
                'remarks': p.remarks or ""
            } for p in user_presets
        }
            
        return render_template('new_task.html', 
                               current_user_name=current_user.name,
                               users=User.query.filter_by(is_approved=True, is_active=True).order_by(User.name.asc()).all(),
                               req_dict_json=json.dumps(req_dict), 
                               macro_scopes_json=json.dumps(macro_scopes_list),
                               core_tasks_json=json.dumps(LEAN_CORE_TASKS),
                               omni_cards_json=json.dumps(omni_cards),
                               quick_chips_json=json.dumps(get_active_quick_chips(current_user.name)), is_admin=is_user_admin(current_user),
                               presets_json=json.dumps(presets_dict),
                               frequent_patterns_json=json.dumps(frequent_patterns),
                               recent_history_json=json.dumps(recent_history),
                               top_requestors_json=json.dumps(top_requestors),
                               presets=user_presets)
                               
    except Exception as e:
        return f"<h2>DIAGNOSTIC CRASH REPORT (NEW TASK)</h2><p>Error: {str(e)}</p><pre>{traceback.format_exc()}</pre>"        

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    try:
        task = SurveyTask.query.get_or_404(task_id)
        assigned_users = [name.strip() for name in task.assigned_to.split(',')] if task.assigned_to else []
        if not is_user_admin(current_user) and current_user.name != task.surveyor_name and current_user.name not in assigned_users:
            flash('Unauthorized to edit this task.', 'error')
            return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))

        if request.method == 'POST':
            req_dept = request.form.get('requestor_dept')
            req_name = request.form.get('requestor_name')
            task.requestor = f"{req_dept} - {req_name}"
            old_assigned = task.assigned_to
            assigned_list = request.form.getlist('assigned_to')
            task.assigned_to = ", ".join([a for a in assigned_list if a.strip()])
            task.command_verb = request.form.get('command_verb', 'PERFORM')
            task.task_category = request.form.get('task_category')
            task.area = request.form.get('area')
            task.location = request.form.get('location')
            task.sub_location = request.form.get('sub_location')
            task.work_scope = request.form.get('work_scope')
            task.instrument = request.form.get('instrument')
            task.action_required = request.form.get('action_required')
            task.remarks = request.form.get('remarks')
            task.is_urgent = True if request.form.get('is_urgent') else False
            p_val = request.form.get('priority')
            if p_val and p_val.isdigit():
                task.priority = int(p_val)
            exec_date_str = request.form.get('execution_date')
            task.execution_date = datetime.strptime(exec_date_str, '%Y-%m-%d').date() if exec_date_str else None
            ref_links = request.form.getlist('reference_link')
            task.reference_links = " | ".join([link for link in ref_links if link.strip()])
            db.session.commit()
            if old_assigned and old_assigned != task.assigned_to:
                resequence_queue(old_assigned)
            resequence_queue(task.assigned_to)
            flash('Task updated successfully!', 'success')
            return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))

        config = AppConfig.query.first()
        master_schema = json.loads(config.schema_data) if config else {}
        file_tree = master_schema.get("file_tree", {})
        req_dict = master_schema.get("requestors", {})
        activities_data = master_schema.get("activities", {})
        macro_scopes_list, omni_cards = get_merged_macro_scopes_and_cards(file_tree)

        task_dict = {
            'command_verb': task.command_verb or "PERFORM",
            'task_category': task.task_category or "", 'instrument': task.instrument or "",
            'action_required': task.action_required or "", 'area': task.area or "", 'location': task.location or "",
            'sub_location': task.sub_location or "", 'work_scope': task.work_scope or "",
            'req_dept': task.requestor.split(" - ", 1)[0] if task.requestor and " - " in task.requestor else "",
            'req_name': task.requestor.split(" - ", 1)[1] if task.requestor and " - " in task.requestor else ""
        }
        task_id_str = task.start_time.strftime('%Y%m%d-%H%M%S') if task.start_time else f"UNKNOWN-{task.id}"
        return render_template('edit_task.html', 
                               task=task, task_id_str=task_id_str,
                               users=User.query.filter_by(is_approved=True, is_active=True).order_by(User.name.asc()).all(),
                               req_dict_json=json.dumps(req_dict),
                               schema_json=json.dumps(file_tree), 
                               activities_json=json.dumps(activities_data),
                               macro_scopes_json=json.dumps(macro_scopes_list),
                               core_tasks_json=json.dumps(LEAN_CORE_TASKS),
                               omni_cards_json=json.dumps(omni_cards),
                               quick_chips_json=json.dumps(get_active_quick_chips(current_user.name)), is_admin=is_user_admin(current_user),
                               task_json=json.dumps(task_dict))
    except Exception as e:
        return f"<h2>DIAGNOSTIC CRASH REPORT (EDIT TASK)</h2><p>Error: {str(e)}</p><pre>{traceback.format_exc()}</pre>"

@app.route('/ajax_update_task_status', methods=['POST'])
@login_required
def ajax_update_task_status():
    try:
        data = request.get_json()
        task = SurveyTask.query.get_or_404(data.get('task_id'))
        new_status = data.get('new_status')
        assigned_users = [name.strip() for name in task.assigned_to.split(',')] if task.assigned_to else []
        if not is_user_admin(current_user) and current_user.name not in assigned_users and current_user.name != task.surveyor_name:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        task.status = new_status
        if new_status in ['Closed', 'Canceled', 'Archived']:
            task.priority = 99
        if new_status == 'In Progress' and 'Acknowledged' not in (task.remarks or ''):
            ack_note = f"Acknowledged & Started by {current_user.name}"
            task.remarks = f"{task.remarks} | {ack_note}" if task.remarks else ack_note
        db.session.commit()
        resequence_queue(task.assigned_to)
        return jsonify({'success': True, 'remarks': task.remarks, 'priority': task.priority})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/ajax_modal_action', methods=['POST'])
@login_required
def ajax_modal_action():
    try:
        data = request.get_json() or {}
        task = SurveyTask.query.get_or_404(data.get('task_id'))
        action = data.get('action')
        assigned_users = [name.strip() for name in task.assigned_to.split(',')] if task.assigned_to else []
        if not is_user_admin(current_user) and current_user.name not in assigned_users and current_user.name != task.surveyor_name:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        old_assigned = task.assigned_to
        if action == 'acknowledge':
            task.status = 'In Progress'
            if 'Acknowledged' not in (task.remarks or ''):
                ack_note = f"Acknowledged & Started by {current_user.name}"
                task.remarks = f"{task.remarks} | {ack_note}" if task.remarks else ack_note
        elif action == 'close':
            closing_remarks = (data.get('closing_remarks') or '').strip()
            if not closing_remarks:
                return jsonify({'success': False, 'message': 'Closing remarks are mandatory.'}), 400
            if data.get('deliverable_link'):
                task.deliverable_link = data.get('deliverable_link').strip()
            task.remarks = f"{task.remarks} | Closed: {closing_remarks}" if task.remarks else f"Closed: {closing_remarks}"
            task.status = 'Closed'
            task.priority = 99
            task.end_time = datetime.utcnow()
        elif action == 'cancel':
            cancel_reason = (data.get('cancel_reason') or '').strip()
            if not cancel_reason:
                return jsonify({'success': False, 'message': 'Cancellation reason is mandatory.'}), 400
            task.remarks = f"{task.remarks} | CANCELED: {cancel_reason}" if task.remarks else f"CANCELED: {cancel_reason}"
            task.status = 'Canceled'
            task.priority = 99
            task.end_time = datetime.utcnow()
        elif action == 'quick_edit':
            if 'priority' in data and str(data['priority']).isdigit():
                task.priority = int(data['priority'])
            if 'is_urgent' in data:
                task.is_urgent = bool(data['is_urgent'])
            if 'assigned_to' in data and str(data['assigned_to']).strip():
                task.assigned_to = str(data['assigned_to']).strip()
            if 'work_scope' in data and data['work_scope'] in SCOPE_BY_CODE:
                ms = SCOPE_BY_CODE[data['work_scope']]
                task.area = ms['area']
                task.location = ms['location']
                task.sub_location = ms['sub_location']
                task.work_scope = ms['work_scope']
            if 'execution_date' in data:
                exec_str = (data.get('execution_date') or '').strip()
                task.execution_date = datetime.strptime(exec_str, '%Y-%m-%d').date() if exec_str else None
        db.session.commit()
        if old_assigned and old_assigned != task.assigned_to:
            resequence_queue(old_assigned)
        resequence_queue(task.assigned_to)
        return jsonify({
            'success': True,
            'task': {
                'id': task.id, 'status': task.status, 'priority': task.priority, 'is_urgent': task.is_urgent,
                'assigned_to': task.assigned_to or '', 'work_scope': task.work_scope or '', 'macro_label': SCOPE_BY_CODE[task.work_scope]['label'] if task.work_scope in SCOPE_BY_CODE else task.work_scope, 'remarks': task.remarks or '', 'deliverable_link': task.deliverable_link or '',
                'date': task.execution_date.strftime('%Y-%m-%d') if task.execution_date else (task.start_time.strftime('%Y-%m-%d') if task.start_time else ''),
                'execution_date': task.execution_date.strftime('%Y-%m-%d') if task.execution_date else '',
                'start': task.execution_date.strftime('%Y-%m-%d (Backdated)') if task.execution_date else (task.start_time.strftime('%Y-%m-%d %H:%M') if task.start_time else ''),
                'end': task.end_time.strftime('%Y-%m-%d %H:%M') if task.end_time else 'Pending'
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/mark_in_progress/<int:task_id>', methods=['POST'])
@login_required
def mark_in_progress(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    task.status = 'In Progress'
    ack_note = f"Acknowledged & Started by {current_user.name}"
    task.remarks = f"{task.remarks} | {ack_note}" if task.remarks else ack_note
    db.session.commit()
    resequence_queue(task.assigned_to)
    flash('Task acknowledged! It is now In Progress.', 'success')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/close_task/<int:task_id>', methods=['POST'])
@login_required
def close_task(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    closing_remarks = request.form.get('closing_remarks')
    if not closing_remarks:
        flash('Closing remarks are mandatory.', 'error')
        return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))
    task.remarks = f"{task.remarks} | Closed: {closing_remarks}" if task.remarks else f"Closed: {closing_remarks}"
    if request.form.get('deliverable_link'):
        task.deliverable_link = request.form.get('deliverable_link')
    task.status = 'Closed'
    task.priority = 99
    task.end_time = datetime.utcnow()
    db.session.commit()
    resequence_queue(task.assigned_to)
    flash('Task closed and logged!', 'success')
    return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))

@app.route('/cancel_task/<int:task_id>', methods=['POST'])
@login_required
def cancel_task(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    cancel_reason = request.form.get('cancel_reason')
    task.remarks = f"{task.remarks} | CANCELED: {cancel_reason}" if task.remarks else f"CANCELED: {cancel_reason}"
    task.status = 'Canceled'
    task.priority = 99
    task.end_time = datetime.utcnow()
    db.session.commit()
    resequence_queue(task.assigned_to)
    flash('Task canceled.', 'error')
    return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))

@app.route('/delete_preset/<int:preset_id>', methods=['POST'])
@login_required
def delete_preset(preset_id):
    preset = PresetTask.query.get_or_404(preset_id)
    if preset.user_id == current_user.id or is_user_admin(current_user):
        db.session.delete(preset)
        db.session.commit()
        flash(f"Preset '{preset.preset_name}' deleted.", 'success')
    return redirect(request.referrer or url_for('new_task'))
    
# --- REPORT GENERATOR ROUTES (DTR & KPI EXCEL ONLY) ---
@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/api/preview_kpi', methods=['GET'])
@login_required
def api_preview_kpi():
    try:
        kpi_month = request.args.get('kpi_month', '').strip()
        target_year, target_month = kpi_month.split('-', 1) if (kpi_month and '-' in kpi_month) else (None, None)
        rows = build_kpi_rows(target_year=target_year, target_month=target_month)
        return jsonify({'success': True, 'count': len(rows), 'rows': rows})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/generate_dtr', methods=['POST'])
@login_required
def generate_dtr():
    try:
        from copy import deepcopy
        from docx import Document

        # Collect dates from multi-date CSV, multiple inputs, date range, or single date input
        raw_dates = set()

        csv_dates = (request.form.get('selected_dates_csv') or '').strip()
        if csv_dates:
            for part in csv_dates.split(','):
                if part.strip():
                    raw_dates.add(part.strip())

        for d_str in request.form.getlist('dtr_date'):
            if d_str and d_str.strip():
                raw_dates.add(d_str.strip())

        range_start = (request.form.get('dtr_start_date') or '').strip()
        range_end = (request.form.get('dtr_end_date') or '').strip()
        if range_start and range_end:
            dt_s = datetime.strptime(range_start, '%Y-%m-%d')
            dt_e = datetime.strptime(range_end, '%Y-%m-%d')
            if dt_s > dt_e:
                dt_s, dt_e = dt_e, dt_s
            curr_dt = dt_s
            while curr_dt <= dt_e and (curr_dt - dt_s).days <= 62:
                raw_dates.add(curr_dt.strftime('%Y-%m-%d'))
                curr_dt += timedelta(days=1)

        if not raw_dates:
            flash('Please select at least one date to generate the DTR.', 'error')
            return redirect(url_for('reports'))

        sorted_dates = sorted(
            [datetime.strptime(d, '%Y-%m-%d') for d in raw_dates]
        )

        add_page_break = (request.form.get('page_break', 'true') == 'true')
        skip_empty_dates = (request.form.get('skip_empty', 'false') == 'true')

        open_tasks = SurveyTask.query.filter_by(status='Open').all()
        outstanding_list = sorted(list({
            format_clean_description(t, include_opening_remark=True)
            for t in open_tasks if format_clean_description(t)
        }))

        template_path = os.path.join(app.root_path, 'static', 'report_templates', 'DTR_Template.docx')
        rendered_streams = []
        included_dates = []

        for target_date in sorted_dates:
            next_day = target_date + timedelta(days=1)
            daily_tasks = SurveyTask.query.filter(
                SurveyTask.status.in_(['Closed', 'Archived']),
                or_(
                    SurveyTask.execution_date == target_date.date(),
                    and_(
                        SurveyTask.execution_date == None,
                        SurveyTask.start_time >= target_date,
                        SurveyTask.start_time < next_day
                    )
                )
            ).all()

            if skip_empty_dates and len(daily_tasks) == 0 and len(sorted_dates) > 1:
                continue

            dtr_groups = {}
            for t in daily_tasks:
                task_bullet = format_clean_description(t, include_opening_remark=True)
                assigned = t.assigned_to if t.assigned_to else t.surveyor_name
                surveyors = [s.strip() for s in assigned.split(',') if s.strip()]

                group_type, boat_name = "inline", ""
                raw_remark = t.remarks or ""
                if "WS166" in str(t.instrument) or "WS166" in raw_remark:
                    group_key, group_type, boat_name = "EGST Hydro Survey", "hydro", "WS166"
                elif "Arzana" in str(t.instrument) or "Arzana" in str(t.work_scope) or "Arzana" in raw_remark:
                    group_key, group_type = "Arzana", "vessel"
                elif t.area and t.area.startswith('100'):
                    group_key, group_type = "Wuqi Office", "inline"
                elif t.area and t.area.startswith('200'):
                    group_key, group_type = "Onshore-Land", "inline"
                else:
                    group_key, group_type = "Marine Offshore", "inline"

                if group_key not in dtr_groups:
                    dtr_groups[group_key] = {"title": group_key, "type": group_type, "surveyors": set(), "tasks": [], "boat": boat_name}
                for s in surveyors:
                    dtr_groups[group_key]["surveyors"].add(s)
                dtr_groups[group_key]["tasks"].append(task_bullet)

            report_blocks = []
            sort_order = ["Wuqi Office", "EGST Hydro Survey", "Arzana", "Onshore-Land", "Marine Offshore"]
            for key in sort_order:
                if key in dtr_groups:
                    dtr_groups[key]["surveyors"] = ", ".join(sorted(list(dtr_groups[key]["surveyors"])))
                    report_blocks.append(dtr_groups[key])
            for key, data in dtr_groups.items():
                if key not in sort_order:
                    data["surveyors"] = ", ".join(sorted(list(data["surveyors"])))
                    report_blocks.append(data)

            doc = DocxTemplate(template_path)
            doc.render({
                'target_date': target_date.strftime('%d.%m.%Y'),
                'day_of_week': target_date.strftime('%A'),
                'report_blocks': report_blocks,
                'outstanding_tasks': outstanding_list
            })
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)
            rendered_streams.append(buf)
            included_dates.append(target_date)

        if not rendered_streams:
            flash('No completed tasks found across the selected dates.', 'error')
            return redirect(url_for('reports'))

        if len(rendered_streams) == 1:
            single_dt = included_dates[0]
            return send_file(
                rendered_streams[0],
                download_name=f"{single_dt.strftime('%Y%m%d')}-DTR-Report.docx",
                as_attachment=True
            )

        # Combine multiple rendered Word documents into a single .docx file
        master_doc = Document(rendered_streams[0])
        for sub_stream in rendered_streams[1:]:
            if add_page_break:
                master_doc.add_page_break()
            sub_doc = Document(sub_stream)
            sect_pr = master_doc.element.body.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr')
            for element in sub_doc.element.body:
                if element.tag.endswith('sectPr'):
                    continue
                cloned_el = deepcopy(element)
                if sect_pr is not None:
                    sect_pr.addprevious(cloned_el)
                else:
                    master_doc.element.body.append(cloned_el)

        combined_output = io.BytesIO()
        master_doc.save(combined_output)
        combined_output.seek(0)

        first_str = included_dates[0].strftime('%Y%m%d')
        last_str = included_dates[-1].strftime('%Y%m%d')
        dl_name = f"{first_str}_to_{last_str}-DTR-Report ({len(included_dates)} Days).docx"
        return send_file(combined_output, download_name=dl_name, as_attachment=True)

    except Exception as e:
        flash(f'DTR Generation Failed. Error: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/export_excel', methods=['POST'])
@login_required
def export_excel():
    try:
        kpi_month = request.form.get('kpi_month') 
        target_year, target_month = kpi_month.split('-') if kpi_month else (None, None)
        data = build_kpi_rows(target_year=target_year, target_month=target_month)
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, startrow=2, sheet_name='Master Register')
            worksheet = writer.sheets['Master Register']
            worksheet.cell(row=1, column=5, value="SURVEY ACTIVITY MASTER REGISTER")
            header_month = datetime.strptime(kpi_month, "%Y-%m").strftime('%B %Y').upper() if kpi_month else datetime.utcnow().strftime('%B %Y').upper()
            worksheet.cell(row=2, column=1, value=f"MONTH OF {header_month} - SURVEY TEAM")
            for column in worksheet.columns:
                max_len = max((len(str(cell.value or '')) for cell in column), default=10)
                worksheet.column_dimensions[column[0].column_letter].width = max_len + 2
        output.seek(0)
        return send_file(output, download_name=f"Master_Register_{kpi_month or 'All'}.xlsx", as_attachment=True)
    except Exception as e:
        flash(f'KPI Excel Generation Failed. Error: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/wipe_all_presets')
@login_required
def wipe_all_presets():
    if not is_user_admin(current_user):
        return redirect(url_for('dashboard'))
    deleted_count = db.session.query(PresetTask).delete()
    db.session.commit()
    flash(f'Successfully deleted {deleted_count} old presets across all users.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
