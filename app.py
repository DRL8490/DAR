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

# --- VIP ADMIN LIST ---
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

# --- POINT #7: USER USAGE TELEMETRY MODEL ---
class UserActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    user_name = db.Column(db.String(100), nullable=False)
    endpoint = db.Column(db.String(100), nullable=False)
    path = db.Column(db.String(200), nullable=False)
    method = db.Column(db.String(15), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

def is_user_admin(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return bool(getattr(user, 'is_admin', False) or (user.email in ADMIN_EMAILS))

def extract_opening_remark(raw_remarks):
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

def format_clean_description(task):
    """Formats DTR & KPI description cleanly while stripping TC-/TX- disambiguation tags."""
    loc = task.location.split('_', 1)[-1].replace('_', ' ') if task.location and task.location != 'N/A' else ''
    sub = task.sub_location.split('_', 1)[-1].replace('_', ' ') if task.sub_location and task.sub_location != 'N/A' else ''
    scope = task.work_scope.split('_', 1)[-1] if task.work_scope and task.work_scope != 'N/A' else ''
    for prefix in ['TC-', 'TX-']:
        if scope.startswith(prefix):
            scope = scope[len(prefix):]
    scope = scope.replace('_', ' ')
    raw_parts = [loc, sub, scope, task.action_required]
    clean_parts = [p.strip() for p in raw_parts if p and p.strip().lower() != 'general']
    return " ".join(clean_parts)

# --- POINT #7: AUTOMATIC PAGE & ACTION TELEMETRY LOGGER ---
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
    # --- REVERSE MIGRATION: Restore Legacy Statuses ---
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

    # Ensure VIP Admins have is_admin = True
    try:
        for vip_email in ADMIN_EMAILS:
            vip_user = User.query.filter_by(email=vip_email).first()
            if vip_user and not vip_user.is_admin:
                vip_user.is_admin = True
        db.session.commit()
    except Exception:
        db.session.rollback()

    # --- REVISED LOCATION TREE WITH TC=TAICHUNG & TX=TUNGHSIAO TAGS ---
    revised_file_tree = {
        "100_Office": {
            "110_Taichung": {
                "111_Survey_Internal": ["111-00_TC-Survey_General", "111-10_TC-Personnel_Files", "111-20_TC-Personnel_Planning", "111-30_TC-Survey_Subcon"],
                "112_NMDC_Internal": ["112-00_TC-NMDC_General", "112-10_TC-Admin", "112-20_TC-Subcon_Tech_Review", "112-30_TC-ENERGY"],
                "113_Project-External": ["113-00_TC-External_General", "113-10_TC-TPC-POE"]
            },
            "120_Abu_Dhabi": {
                "121_STS": ["121-10_KPI", "121-20_WSR"],
                "122_ADMIN": ["122-00_AD-Admin_General", "122-10_Timesheet", "122-20_TRF"],
                "123_SWS": ["123-10_Equipment_List", "123-20_SEM", "123-30_AHO"]
            }
        },
        "200_Onshore-Land": {
            "210_Taichung": {
                "211_General": ["211-00_TC-General"],
                "212_AHDD": ["212-00_TC-AHDD_General", "212-10_TC-Trial_Pits", "212-20_TC-Thruster_Pit", "212-30_TC-Crossover_Pits", "212-40_TC-Grit_Tank", "212-50_TC-Drainage"],
                "213_Tienli": ["213-00_TC-Tienli_General"],
                "214_Berth37": ["214-00_TC-Berth37_General"],
                "219_Others": ["219-00_TC-Others"]
            },
            "220_Tunghsiao": {
                "221_Temp Platform": ["221-00_TX-Temp_Platform_General", "221-10_TX-Trial_Pits", "221-20_TX-Thruster_Pit", "221-30_TX-Crossover_Pits", "221-40_TX-Grit_Tank", "221-50_TX-Drainage", "221-60_TX-Microtunneling"],
                "222_Inside Plant": ["222-00_TX-Inside_Plant_General", "222-10_TX-IP_Trial_Pits", "222-20_TX-IP_Crossover_Pits"],
                "229_Others": ["229-00_TX-Others"]
            }
        },
        "300_Marine": {
            "310_General": {
                "311_Surveys": ["311-10_Marine_Pre-Surveys", "311-20_Marine_Progress-Surveys", "311-30_Marine_Post-Surveys"],
                "312_Design": ["312-00_Design_General", "312-10_DXF_Backgrounds", "312-20_Routelines", "312-30_3DM+Outlines"],
                "313_Quantity": ["313-10_ICQP_Format", "313-20_CECI_Format", "313-30_Other_Formats"]
            },
            "320_Nearshore": {
                "321_General": ["321-00_Nearshore_General"],
                "322_Trench 1": ["322-00_T1_General", "322-10_T1_Dredging", "322-20_T1_Pipelaying_A", "322-30_T1_Pipelaying_B", "322-40_T1_SRI", "322-50_T1_Backfilling"],
                "323_Trench 8": ["323-00_T8_General", "323-10_T8_Dredging", "323-20_T8_Pipelaying_A", "323-30_T8_Pipelaying_B", "323-40_T8_SRI", "323-50_T8_Backfilling"]
            },
            "330_Offshore": {
                "331_Trench 2": ["331-00_T2_General", "331-10_T2_Pipelaying_A", "331-20_T2_Post-Trenching-A", "331-30_T2_SRI-A", "331-40_T2_Pipelaying_B", "331-50_T2_Post-Trenching-B", "331-60_T2_SRI-B"],
                "332_Trench 3": ["332-00_T3_General", "332-10_T3_Pipelaying_A", "332-20_T3_Post-Trenching-A", "332-30_T3_SRI-A", "332-40_T3_Pipelaying_B", "332-50_T3_Post-Trenching-B", "332-60_T3_SRI-B"],
                "333_Trench 4": ["333-00_T4_General", "333-10_T4_Pipelaying_A", "333-20_T4_Post-Trenching-A", "333-30_T4_SRI-A", "333-40_T4_Pipelaying_B", "333-50_T4_Post-Trenching-B", "333-60_T4_SRI-B"],
                "334_Trench 5": ["334-00_T5_General", "334-10_T5_Pipelaying_A", "334-20_T5_Post-Trenching-A", "334-30_T5_SRI-A", "334-40_T5_Pipelaying_B", "334-50_T5_Post-Trenching-B", "334-60_T5_SRI-B", "334-70_T5_Backfilling_A", "334-80_T5_Backfilling_B"],
                "335_Trench 6": ["335-00_T6_General", "335-10_T6_Pipelaying_A", "335-20_T6_Post-Trenching-A", "335-30_T6_SRI-A", "335-40_T6_Pipelaying_B", "335-50_T6_Post-Trenching-B", "335-60_T6_SRI-B", "335-70_T6_Backfilling_A", "335-80_T6_Backfilling_B"],
                "336_Trench 7": ["336-00_T7_General", "336-10_T7_Pipelaying_A", "336-20_T7_Post-Trenching-A", "336-30_T7_SRI-A", "336-40_T7_Pipelaying_B", "336-50_T7_Post-Trenching-B", "336-60_T7_SRI-B", "336-70_T7_Backfilling_A", "336-80_T7_Backfilling_B"],
                "337_Midline_Tie-in": ["337-00_Midline_General", "337-10_Midline_Dredging", "337-20_Midline_Pipelaying_A", "337-30_Midline_Pipelaying_B", "337-40_Midline_Post-Trenching-A", "337-50_Midline_Post-Trenching-B", "337-60_Midline_SRI-A", "337-70_Midline_SRI-B"],
                "338_Crossing-A": ["338-11_A1 Mattress Installation", "338-12_A1 Pipelaying", "338-13_A1 SRI", "338-21_A2 Mattress Installation", "338-22_A2 Pipelaying", "338-23_A2 SRI", "338-31_A3 Mattress Installation", "338-32_A3 Pipelaying", "338-33_A3 SRI"],
                "339_Crossing-B": ["339-11_B1 Mattress Installation", "339-12_B1 Pipelaying", "339-13_B1 SRI", "339-21_B2 Mattress Installation", "339-22_B2 Pipelaying", "339-23_B2 SRI", "339-31_B3 Mattress Installation", "339-32_B3 Pipelaying", "339-33_B3 SRI"]
            }
        }
    }

    master_config = {
        "file_tree": revised_file_tree,
        "requestors": {
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
        },
        "activities": {
            "Office Admin Works": {
                "Internal Coordination Meetings": ["Face to Face", "Teams", "PC"],
                "External Meetings": ["Face to Face", "Teams", "PC"],
                "Survey Input - ICQP": ["Face to Face", "Teams", "PC"],
                "Survey Input - Others": ["Face to Face", "Teams", "PC"],
                "Survey Reports": ["Teams", "PC", "Excel"]
            },
            "Land Survey": {
                "Pre-Survey": ["GNSS Rover", "Total Station", "Lidar", "Drone"],
                "Progress Survey": ["GNSS Rover", "Total Station", "Lidar", "Drone"],
                "Post-Survey": ["GNSS Rover", "Total Station", "Lidar", "Drone"],
                "As-built Survey": ["GNSS Rover", "Total Station", "Lidar", "Drone"],
                "Check Survey": ["GNSS Rover", "Total Station", "Levelling Machine"],
                "Tender Survey": ["GNSS Rover", "Total Station", "Lidar", "Drone"],
                "Setting-Out Survey": ["GNSS Rover", "Total Station"],
                "Stake-Out/Marking": ["GNSS Rover", "Total Station"],
                "Benchmark Verification": ["GNSS Rover", "Total Station"],
                "Stockpile Survey": ["GNSS Rover", "Total Station", "Lidar Equipment", "Drone"],
                "GI Survey": ["GNSS Rover", "Total Station"]
            },
            "Bathymetric Survey": {
                "Tender Survey": ["MBES  WS166", "SBES"],
                "Pre-Survey": ["MBES  WS166", "SBES"],
                "Progress Survey": ["MBES  WS166", "SBES"],
                "Post Survey": ["MBES  WS166", "SBES"],
                "As-Built Survey": ["MBES  WS166", "SBES"]
            },
            "Geophysical Survey": {
                "Geophysical Presurvey": ["Maggy", "SSS", "SBP"],
                "Geophysical Check Survey": ["Maggy", "SSS", "SBP"],
                "Geophysical Progress survey": ["Maggy", "SSS", "SBP"],
                "Geophysical Survey Post-Processing": ["Reporting", "CAD"]
            },
            "Survey Data Deliverables": {
                "Design Creation/Revision": ["PDS", "Terramodel", "Civil3D", "CAD"],
                "Volume Calculation": ["PDS", "Terramodel", "Civil3D"],
                "Data Volume Calculation": ["PDS", "Terramodel", "Civil3D", "Excel"]
            },
            "Equipment Configuration": {
                "Background Files Creation": ["PDS", "Terramodel", "Civil3D", "CAD"],
                "Guidance Files Creation": ["PDS", "Terramodel", "Civil3D", "CAD"],
                "Survey Software Configuration": ["PDS", "DTPS", "Terramodel", "Civil3D", "CAD", "PC"],
                "Survey Calibration/Troubleshooting": ["PDS", "DTPS", "CAD", "PC", "Others"]
            }
        }
    }
    
    config = AppConfig.query.first()
    if not config: 
        db.session.add(AppConfig(schema_data=json.dumps(master_config)))
        db.session.commit()
    else:
        try:
            existing_schema = json.loads(config.schema_data)
            if "212-20_TC-Thruster_Pit" not in json.dumps(existing_schema.get("file_tree", {})):
                existing_schema["file_tree"] = revised_file_tree
                config.schema_data = json.dumps(existing_schema)
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

        desc_phrase = format_clean_description(task)
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
            'Special Conditions / Remarks': extract_opening_remark(task.remarks)
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
    all_tasks = SurveyTask.query.filter(SurveyTask.status != 'Archived') \
        .order_by(SurveyTask.is_urgent.desc(), SurveyTask.priority.asc(), SurveyTask.start_time.desc()) \
        .limit(300).all()
    is_admin = is_user_admin(current_user)
    all_users = User.query.order_by(User.name.asc()).all()
    initials_map = {u.name: (u.initials.upper() if u.initials else ((u.name.split()[0][0] + u.name.split()[1][0]).upper() if len(u.name.split()) >= 2 else u.name[:2].upper())) for u in all_users}
    return render_template('dashboard.html', name=current_user.name, tasks=all_tasks, users=all_users, is_admin=is_admin, initials_map=initials_map)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not is_user_admin(current_user):
        flash('Access Denied: You do not have Admin privileges.', 'error')
        return redirect(url_for('dashboard'))

    session['dashboard_view'] = 'admin'
    escalate_aging_tasks()
    all_tasks = SurveyTask.query.filter(SurveyTask.status != 'Archived') \
        .order_by(SurveyTask.is_urgent.desc(), SurveyTask.priority.asc(), SurveyTask.start_time.desc()) \
        .limit(300).all()
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
    return render_template('admin_dashboard.html', name=current_user.name, tasks=all_tasks, users=users, kpi_summary_json=json.dumps(months_data), initials_map=initials_map)

# --- POINT #7: ADMIN TELEMETRY DASHBOARD ---
@app.route('/usage_telemetry')
@login_required
def usage_telemetry():
    if not is_user_admin(current_user):
        flash('Access Denied: Admins only.', 'error')
        return redirect(url_for('dashboard'))
    logs = UserActivityLog.query.order_by(UserActivityLog.timestamp.desc()).limit(500).all()
    page_counts = Counter(l.endpoint for l in logs)
    user_counts = Counter(l.user_name for l in logs)
    html = """
    <!DOCTYPE html>
    <html><head><title>Usage Telemetry - NMDC</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body class="bg-light p-4">
    <div class="container">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h3 class="fw-bold mb-0">📈 User Usage & Page Telemetry</h3>
            <a href="/admin_dashboard" class="btn btn-primary">⬅ Back to Admin Dashboard</a>
        </div>
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card shadow-sm"><div class="card-header bg-dark text-white fw-bold">Top Pages / Actions Used</div>
                <ul class="list-group list-group-flush">
                {% for ep, cnt in page_counts %}
                    <li class="list-group-item d-flex justify-content-between"><code>{{ ep }}</code><span class="badge bg-primary">{{ cnt }} hits</span></li>
                {% endfor %}
                </ul></div>
            </div>
            <div class="col-md-6">
                <div class="card shadow-sm"><div class="card-header bg-secondary text-white fw-bold">Most Active Users</div>
                <ul class="list-group list-group-flush">
                {% for uname, cnt in user_counts %}
                    <li class="list-group-item d-flex justify-content-between"><strong>{{ uname }}</strong><span class="badge bg-success">{{ cnt }} actions</span></li>
                {% endfor %}
                </ul></div>
            </div>
        </div>
        <div class="card shadow-sm">
            <div class="card-header bg-white fw-bold">Recent Activity Stream (Latest 100)</div>
            <div class="table-responsive"><table class="table table-sm table-striped mb-0">
                <thead><tr><th>Timestamp (UTC)</th><th>User</th><th>Endpoint</th><th>Path</th><th>Method</th></tr></thead>
                <tbody>
                {% for l in logs[:100] %}
                    <tr><td>{{ l.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td><td><strong>{{ l.user_name }}</strong></td><td><code>{{ l.endpoint }}</code></td><td>{{ l.path }}</td><td>{{ l.method }}</td></tr>
                {% endfor %}
                </tbody>
            </table></div>
        </div>
    </div></body></html>
    """
    return render_template_string(html, logs=logs, page_counts=page_counts.most_common(12), user_counts=user_counts.most_common(12))

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
            target_sheet = next((s for s in excel_file.sheet_names if 'master' in s.lower()), excel_file.sheet_names[0])
            df_raw = pd.read_excel(file, sheet_name=target_sheet, header=None).fillna('')
            header_row_idx = -1
            col_map = {}
            for idx, row in df_raw.iterrows():
                row_vals = [str(x).strip().lower() for x in row.values]
                if 'from date' in row_vals or 'description of survey daily activities' in row_vals:
                    header_row_idx = idx
                    for col_idx, val in enumerate(row_vals):
                        if 'from date' in val: col_map['date'] = col_idx
                        elif 'requestor' in val: col_map['req'] = col_idx
                        elif 'pic' in val or 'assigned to' in val: col_map['pic'] = col_idx
                        elif 'involve' in val: col_map['person'] = col_idx
                        elif 'activity type' in val: col_map['act'] = col_idx
                        elif 'discipline' in val: col_map['disc'] = col_idx
                        elif 'description' in val or 'daily activities' in val: col_map['desc'] = col_idx
                        elif 'detail' in val or 'condition' in val: col_map['rem1'] = col_idx
                        elif 'remarks' in val: col_map['rem2'] = col_idx
                        elif 'store' in val: col_map['store'] = col_idx
                    break
            if header_row_idx == -1:
                flash("Error: Could not find headers (like 'From Date').", 'error')
                return redirect(url_for('migrate_data'))
            migrated_count = 0
            for idx in range(header_row_idx + 1, len(df_raw)):
                row = df_raw.iloc[idx].values
                def get_val(key):
                    return str(row[col_map[key]]).strip() if key in col_map and col_map[key] < len(row) else ''
                date_val, desc = get_val('date'), get_val('desc')
                if not date_val and not desc:
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

# --- POINT #8: NEW TASK WITH TOP 3 FREQUENT & PAGINATED FULL HISTORY ---
@app.route('/new_task', methods=['GET', 'POST'])
@login_required
def new_task():
    try:
        config = AppConfig.query.first()
        master_schema = json.loads(config.schema_data) if config else {}
        file_tree = master_schema.get("file_tree", {})
        req_dict = master_schema.get("requestors", {})
        activities_data = master_schema.get("activities", {})
        
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
            
        # Build Personal Task History & Frequency Ranking
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
                    'work_scope': t.work_scope or ''
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
                'remarks': extract_opening_remark(t.remarks)[:60]
            })

        frequent_patterns = []
        for key, cnt in pattern_counter.most_common(100):
            entry = dict(pattern_meta[key])
            entry['count'] = cnt
            frequent_patterns.append(entry)

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
                               schema_json=json.dumps(file_tree),
                               activities_json=json.dumps(activities_data),
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
        task_dict = {
            'command_verb': task.command_verb or "PERFORM",
            'task_category': task.task_category or "", 'instrument': task.instrument or "",
            'action_required': task.action_required or "", 'area': task.area or "", 'location': task.location or "",
            'sub_location': task.sub_location or "", 'work_scope': task.work_scope or "",
            'req_dept': task.requestor.split(" - ", 1)[0] if task.requestor and " - " in task.requestor else "",
            'req_name': task.requestor.split(" - ", 1)[1] if task.requestor and " - " in task.requestor else ""
        }
        task_id_str = task.start_time.strftime('%Y%m%d-%H%M%S') if task.start_time else f"UNKNOWN-{task.id}"
        class ShimOption:
            def __init__(self, name): self.name = name
        categories = sorted([ShimOption(k) for k in activities_data.keys()], key=lambda x: x.name)
        actions_set, instruments_set = set(), set()
        for acts in activities_data.values():
            for act, insts in acts.items():
                actions_set.add(act)
                instruments_set.update(insts)
        return render_template('edit_task.html', 
                               task=task, task_id_str=task_id_str,
                               users=User.query.filter_by(is_approved=True, is_active=True).order_by(User.name.asc()).all(),
                               req_dict_json=json.dumps(req_dict), schema_json=json.dumps(file_tree), 
                               activities_json=json.dumps(activities_data),
                               categories=categories,
                               instruments=sorted([ShimOption(i) for i in instruments_set], key=lambda x: x.name),
                               actions=sorted([ShimOption(a) for a in actions_set], key=lambda x: x.name),
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
                'assigned_to': task.assigned_to or '', 'remarks': task.remarks or '', 'deliverable_link': task.deliverable_link or '',
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
    
# --- REPORT GENERATOR ROUTES (DTR & KPI EXCEL ONLY; WSR & TPC REMOVED) ---
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
        target_date_str = request.form.get('dtr_date')
        if not target_date_str: return redirect(url_for('reports'))
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
        next_day = target_date + timedelta(days=1)
        
        daily_tasks = SurveyTask.query.filter(
            SurveyTask.status == 'Closed',
            or_(
                SurveyTask.execution_date == target_date.date(),
                and_(SurveyTask.execution_date == None, SurveyTask.start_time >= target_date, SurveyTask.start_time < next_day)
            )
        ).all()

        dtr_groups = {}
        for t in daily_tasks:
            t.action_phrase = format_clean_description(t)
            opening_remark = extract_opening_remark(t.remarks)
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
            for s in surveyors: dtr_groups[group_key]["surveyors"].add(s)
            task_bullet = f"{t.action_phrase} - {opening_remark}" if opening_remark and t.action_phrase else (t.action_phrase or opening_remark)
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

        open_tasks = SurveyTask.query.filter_by(status='Open').all()
        outstanding_set = {format_clean_description(t) for t in open_tasks if format_clean_description(t)}

        template_path = os.path.join(app.root_path, 'static', 'report_templates', 'DTR_Template.docx')
        doc = DocxTemplate(template_path)
        doc.render({
            'target_date': target_date.strftime('%d.%m.%Y'),
            'day_of_week': target_date.strftime('%A'),
            'report_blocks': report_blocks,
            'outstanding_tasks': list(outstanding_set)
        })
        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return send_file(output, download_name=f"{target_date.strftime('%Y%m%d')}-DTR-Report.docx", as_attachment=True)
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