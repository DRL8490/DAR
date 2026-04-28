import pandas as pd
import io
from flask import send_file
import os, json
import traceback
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from docxtpl import DocxTemplate  # <--- NEW ENGINE IMPORTED HERE
from sqlalchemy import text # <--- REQUIRED FOR URGENT COLUMN DB UPGRADE
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)

db_url = os.environ.get('DATABASE_URL', 'sqlite:///./survey_data.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'super_secret_key_thpp_survey_2026'
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
    status = db.Column(db.String(20), default="Open")
    is_urgent = db.Column(db.Boolean, default=False) # <--- URGENT FLAG ADDED
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)

with app.app_context():
    db.create_all()
    # Safely inject the Active column
    # Safely inject the Remarks column into existing Preset tables
    try:
        db.session.execute(text('ALTER TABLE preset_task ADD COLUMN remarks TEXT'))
        db.session.commit()
    except Exception:
        db.session.rollback()
    try:
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN is_active BOOLEAN DEFAULT TRUE'))
        db.session.commit()
    except Exception:
        db.session.rollback() 
        try:
            db.session.execute(text('ALTER TABLE user ADD COLUMN is_active BOOLEAN DEFAULT 1'))
            db.session.commit()
        except Exception:
            db.session.rollback()
    # Safely inject the Urgent column into your existing database without deleting tasks
    # Safely inject the Urgent column into your existing database
    try:
        db.session.execute(text('ALTER TABLE survey_task ADD COLUMN is_urgent BOOLEAN DEFAULT FALSE'))
        db.session.commit()
    except Exception:
        db.session.rollback() # Ignores if the column already exists
# NEW: Safely inject the Approval column (Defaults True for existing users)
    try:
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN is_approved BOOLEAN DEFAULT TRUE'))
        db.session.commit()
    except Exception:
        db.session.rollback()
    # 18. THE INDEXING: Creates a high-speed lookup table for filters
    try:
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_status ON survey_task(status)'))
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_urgent ON survey_task(is_urgent)'))
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_start ON survey_task(start_time)'))
        db.session.commit()
    except Exception:
        db.session.rollback()    
    # 1. THE NEW MASTER JSON ENGINE
    master_config = {
        "file_tree": {
            "100_Office": {
                "110_Taichung": {
                    "111_Survey_Internal": ["111-00_General", "111-10_Personnel_Files", "111-20_Personnel_Planning", "111-30_Survey_Subcon"],
                    "112_NMDC_Internal": ["112-00_General", "112-10_Admin", "112-20_Subcon_Tech_Review", "112-30_ENERGY"],
                    "113_Project-External": ["113-00_General", "113-10_TPC-POE"]
                },
                "120_Abu_Dhabi": {
                    "121_STS": ["121-10_KPI", "121-20_WSR"],
                    "122_ADMIN": ["122-00_General", "122-10_Timesheet", "122-20_TRF"],
                    "123_SWS": ["123-10_Equipment_List", "123-20_SEM", "123-30_AHO"]
                }
            },
            "200_Onshore-Land": {
                "210_Taichung": {
                    "211_General": ["211-00_General"],
                    "212_AHDD": ["212-00_General", "212-10_Trial Pits", "212-20_Thruster Pit", "212-30_Crossover Pits", "212-40_Grit Tank", "212-50_Drainage"],
                    "213_Tienli": ["213-00_General"],
                    "214_Berth37": ["214-00_General"],
                    "219_Others": ["219-00_Others"]
                },
                "220_Tunghsiao": {
                    "221_Temp Platform": ["221-00_General", "221-10_Trial Pits", "221-20_Thruster Pit", "221-30_Crossover Pits", "221-40_Grit Tank", "221-50_Drainage", "221-60_Microtunneling"],
                    "222_Inside Plant": ["222-00_General", "222-10_Trial Pits", "222-20_Crossover Pits"],
                    "229_Others": ["229-00_Others"]
                }
            },
            "300_Marine": {
                "310_General": {
                    "311_Surveys": ["311-10_Pre-Surveys", "311-20_Progress-Surveys", "311-30_Post-Surveys"],
                    "312_Design": ["312-00_General", "312-10_DXF_Backgrounds", "312-20_Routelines", "312-30_3DM+Outlines"],
                    "313_Quantity": ["313-10_ICQP_Format", "313-20_CECI_Format", "313-30_Other_Formats"]
                },
                "320_Nearshore": {
                    "321_General": ["321-00_General"],
                    "322_Trench 1": ["322-00_General", "322-10_Dredging", "322-20_Pipelaying A", "322-30_Pipelaying B", "322-40_SRI", "322-50_Backfilling"],
                    "323_Trench 8": ["323-00_General", "323-10_Dredging", "323-20_Pipelaying A", "323-30_Pipelaying B", "323-40_SRI", "323-50_Backfilling"]
                },
                "330_Offshore": {
                    "331_Trench 2": ["331-00_General", "331-10_Pipelaying A", "331-20_Post-Trenching-A", "331-30_SRI-A", "331-40_Pipelaying B", "331-50_Post-Trenching-B", "331-60_SRI-B"],
                    "332_Trench 3": ["332-00_General", "332-10_Pipelaying A", "332-20_Post-Trenching-A", "332-30_SRI-A", "332-40_Pipelaying B", "332-50_Post-Trenching-B", "332-60_SRI-B"],
                    "333_Trench 4": ["333-00_General", "333-10_Pipelaying A", "333-20_Post-Trenching-A", "333-30_SRI-A", "333-40_Pipelaying B", "333-50_Post-Trenching-B", "333-60_SRI-B"],
                    "334_Trench 5": ["334-00_General", "334-10_Pipelaying A", "334-20_Post-Trenching-A", "334-30_SRI-A", "334-40_Pipelaying B", "334-50_Post-Trenching-B", "334-60_SRI-B", "334-70_Backfilling A", "334-80_Backfilling B"],
                    "335_Trench 6": ["335-00_General", "335-10_Pipelaying A", "335-20_Post-Trenching-A", "335-30_SRI-A", "335-40_Pipelaying B", "335-50_Post-Trenching-B", "335-60_SRI-B", "335-70_Backfilling A", "335-80_Backfilling B"],
                    "336_Trench 7": ["336-00_General", "336-10_Pipelaying A", "336-20_Post-Trenching-A", "336-30_SRI-A", "336-40_Pipelaying B", "336-50_Post-Trenching-B", "336-60_SRI-B", "336-70_Backfilling A", "336-80_Backfilling B"],
                    "337_Midline_Tie-in": ["337-00_General", "337-10_Dredging", "337-20_Pipelaying A", "337-30_Pipelaying B", "337-40_Post-Trenching-A", "337-50_Post-Trenching-B", "337-60_SRI-A", "337-70_SRI-B"],
                    "338_Crossing-A": ["338-11_A1 Mattress Installation", "338-12_A1 Pipelaying", "338-13_A1 SRI", "338-21_A2 Mattress Installation", "338-22_A2 Pipelaying", "338-23_A2 SRI", "338-31_A3 Mattress Installation", "338-32_A3 Pipelaying", "338-33_A3 SRI"],
                    "339_Crossing-B": ["339-11_B1 Mattress Installation", "339-12_B1 Pipelaying", "339-13_B1 SRI", "339-21_B2 Mattress Installation", "339-22_B2 Pipelaying", "339-23_B2 SRI", "339-31_B3 Mattress Installation", "339-32_B3 Pipelaying", "339-33_B3 SRI"]
                }
            }
        },
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
    
# 2. SEED THE DATABASE
    config = AppConfig.query.first()
    if not config: 
        # Only inject the hardcoded data if the database is 100% empty
        db.session.add(AppConfig(schema_data=json.dumps(master_config)))
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
        
        # Auto-approve if they are in the VIP Admin list, otherwise require approval
        is_approved = True if email in ADMIN_EMAILS else False
        
        new_user = User(email=email, name=formatted_name, password_hash=generate_password_hash(password, method='pbkdf2:sha256'), is_approved=is_approved)
        db.session.add(new_user)
        db.session.commit()
        
        if is_approved:
            flash('Admin Account created! Please log in.', 'success')
        else:
            flash('Account created! Please wait for an Admin to approve your access.', 'success')
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
            if not getattr(user, 'is_active', True): # <--- NEW: Blocks deactivated accounts
                flash('Your account has been deactivated. Please contact an Administrator.', 'error')
                return redirect(url_for('login'))   
            login_user(user)
            if user.email in ADMIN_EMAILS:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
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
            # Generate a secure token tied specifically to their email
            token = s.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            
            # Draft the email
            msg = Message('Password Reset Request - NMDC Survey App', recipients=[email])
            msg.body = f"Hello {user.name},\n\nTo reset your password, visit the following link:\n{reset_url}\n\nIf you did not make this request, simply ignore this email.\n\nRegards,\nTHPP Survey Admin Team"
            
            try:
                mail.send(msg)
                flash('If an account exists for that email, a password reset link has been sent.', 'success')
            except Exception as e:
                flash(f'Server Error: Could not send email. {str(e)}', 'error')
        else:
            # SECURITY BEST PRACTICE: Even if the email doesn't exist, say we sent it to prevent hackers from "guessing" active emails
            flash('If an account exists for that email, a password reset link has been sent.', 'success')
            
        return redirect(url_for('login'))
        
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # The token expires after 900 seconds (15 minutes)
        email = s.loads(token, salt='password-reset-salt', max_age=900)
    except:
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
# --- WORKFLOW ROUTES ---

# 16. THE AUTO-ARCHIVE (Background Job Engine)
from apscheduler.schedulers.background import BackgroundScheduler

def auto_archive_tasks():
    with app.app_context(): # Required to access database in the background
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
            print(f"Auto-Archive Complete: Moved tasks to archive.")
# 17. THE NIGHTLY KPI BACKUP (Background Job)
def auto_backup_kpi():
    with app.app_context(): # Required to access database and mail in the background
        try:
            # Gather all data exactly like the Export Excel route
            all_tasks = SurveyTask.query.filter(SurveyTask.status.in_(['Closed', 'Archived'])).order_by(SurveyTask.start_time.asc()).all()
            excluded_keywords = ["external meeting", "internal coordination", "survey report", "damage report", "item", "request", "sem update"]
            
            tasks = []
            for t in all_tasks:
                if t.action_required and any(ex in t.action_required.lower() for ex in excluded_keywords):
                    continue
                tasks.append(t)
            
            # Identify the current target month and year
            now = datetime.utcnow()
            target_month_str = now.strftime('%m')
            target_year_str = now.strftime('%Y')
            
            data = []
            month_counters = {} 
            display_index = 1
            
            for task in tasks:
                month_str = task.start_time.strftime('%m') if task.start_time else '00' 
                year_str = task.start_time.strftime('%Y') if task.start_time else '0000'
                
                # 1. ALWAYS count the task to preserve accurate Sequence Numbers (e.g. TW_03005)
                if month_str not in month_counters: month_counters[month_str] = 1
                else: month_counters[month_str] += 1
                    
                seq_num = f"{month_counters[month_str]:03d}"
                req_ref = f"TW_{month_str}{seq_num}"
                survey_ref = f"TW_SU_{month_str}{seq_num}"

                # 2. THE FILTER: Skip adding to the Excel file if it is not the current month
                if month_str != target_month_str or year_str != target_year_str:
                    continue

                loc = task.location.split('_', 1)[-1].replace('_', ' ') if task.location and task.location != 'N/A' else ''
                sub = task.sub_location.split('_', 1)[-1].replace('_', ' ') if task.sub_location and task.sub_location != 'N/A' else ''
                scope = task.work_scope.split('_', 1)[-1].replace('_', ' ') if task.work_scope and task.work_scope != 'N/A' else ''
                
                raw_parts = [loc, sub, scope, task.action_required]
                clean_parts = [p.strip() for p in raw_parts if p and p.strip().lower() != 'general']
                desc_phrase = " ".join(clean_parts)

                data.append({
                    'Tender / Project Ref.': '20012', 'Sl No': display_index, 'Activity Type': task.task_category, 'Discipline': task.action_required,
                    'Requestor Ref. #': req_ref, 'Survey Ref. #': survey_ref, 'Requestor': task.requestor, 'Assigned to': task.assigned_to,
                    'Date/Time Received': task.start_time.strftime('%Y-%m-%d %H:%M') if task.start_time else '',
                    'Date/Time Completed': task.end_time.strftime('%Y-%m-%d %H:%M') if task.end_time else '',
                    'Description of Survey Works': desc_phrase, 'Special Conditions / Remarks': task.remarks or ''
                })
                display_index += 1
            
            df = pd.DataFrame(data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, startrow=2, sheet_name='Master Register')
                worksheet = writer.sheets['Master Register']
                worksheet.cell(row=1, column=5, value="SURVEY ACTIVITY MASTER REGISTER")
                
                # Update the header to explicitly show the filtered month
                header_month = now.strftime('%B %Y').upper()
                worksheet.cell(row=2, column=1, value=f"MONTH OF {header_month} - SURVEY TEAM (AUTO-BACKUP)")
                
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try: max_length = max(max_length, len(str(cell.value)))
                        except: pass
                    worksheet.column_dimensions[column[0].column_letter].width = (max_length + 2)

            output.seek(0)
            
            # Email the generated Excel payload to the Admins
            msg = Message(f"🛡️ THPP Survey - Daily Database Backup ({now.strftime('%Y-%m-%d')})", recipients=ADMIN_EMAILS)
            msg.body = f"Hello Admins,\n\nAttached is the automated daily backup of the Master Register pipeline for {header_month}.\n\nKeep up the great work!\n- THPP Survey Server"
            msg.attach(f"THPP_Backup_{now.strftime('%Y%m%d')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", output.read())
            
            mail.send(msg)
            print("Daily Backup Executed and Emailed.")
        except Exception as e:
            print(f"CRITICAL BACKUP ERROR: {str(e)}")

# Start the background chron-job
scheduler = BackgroundScheduler()
scheduler.add_job(func=auto_archive_tasks, trigger="interval", hours=12)
# NEW: Triggers exactly at 11:59 PM local time (15:59 UTC)
scheduler.add_job(func=auto_backup_kpi, trigger="cron", hour=15, minute=59) 
scheduler.start()

@app.route('/archive')
@login_required
def archive_page():
    if current_user.email not in ADMIN_EMAILS:
        flash('Access Denied: You do not have permission to view the archive.', 'error')
        return redirect(url_for('dashboard'))
    
    archived_tasks = SurveyTask.query.filter_by(status='Archived').order_by(SurveyTask.start_time.desc()).all()
    return render_template('archive.html', tasks=archived_tasks)

@app.route('/restore_task/<int:task_id>', methods=['POST'])
@login_required
def restore_task(task_id):
    if current_user.email not in ADMIN_EMAILS:
        return "Unauthorized", 403
        
    task = SurveyTask.query.get_or_404(task_id)
    try:
        task.status = 'Closed'
        restore_note = f"RESTORED FROM ARCHIVE: {datetime.utcnow().strftime('%Y-%m-%d')}"
        task.remarks = f"{task.remarks} | {restore_note}" if task.remarks else restore_note
        db.session.commit()
        flash(f'Task {task_id} was successfully restored to the dashboard.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error restoring task: {str(e)}', 'error')
        
    return redirect(request.referrer or url_for('archive_page'))
@app.route('/manage_users')
@login_required
def manage_users():
    if current_user.email not in ADMIN_EMAILS:
        flash('Access Denied: Admins only.', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.order_by(User.name.asc()).all()
    return render_template('manage_users.html', users=users)

@app.route('/toggle_active/<int:user_id>', methods=['POST'])
@login_required
def toggle_active(user_id):
    if current_user.email not in ADMIN_EMAILS:
        return "Unauthorized", 403
    user = User.query.get_or_404(user_id)
    user.is_active = not getattr(user, 'is_active', True) 
    db.session.commit()
    status = "reactivated" if user.is_active else "deactivated"
    flash(f'User {user.name} has been {status}.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/cleanup')
@login_required
def cleanup_tasks():
    if current_user.email not in ADMIN_EMAILS:
        flash('Access Denied: You do not have permission to view this page.', 'error')
        return redirect(url_for('dashboard'))
    
    tasks = SurveyTask.query.order_by(SurveyTask.start_time.desc()).all()
    return render_template('cleanup.html', tasks=tasks)

@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    if current_user.email not in ADMIN_EMAILS:
        return "Unauthorized", 403
        
    task = SurveyTask.query.get_or_404(task_id)
    try:
        db.session.delete(task)
        db.session.commit()
        flash(f'Task {task_id} was permanently deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting task: {str(e)}', 'error')
        
    return redirect(url_for('cleanup_tasks'))
@app.route('/approve_user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if current_user.email not in ADMIN_EMAILS:
        return "Unauthorized", 403
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash(f'User {user.name} has been approved and can now log in.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.email not in ADMIN_EMAILS:
        return "Unauthorized", 403
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.name} has been rejected and deleted.', 'success')
    return redirect(url_for('admin_dashboard'))
@app.route('/migrate', methods=['GET', 'POST'])
@login_required
def migrate_data():
    if current_user.email not in ADMIN_EMAILS:
        flash('Access Denied: Admins only.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        file = request.files.get('excel_file')
        if not file or not file.filename.endswith(('.xlsx', '.xls')):
            flash('Please upload a valid Excel file.', 'error')
            return redirect(url_for('migrate_data'))

        try:
            excel_file = pd.ExcelFile(file)
            target_sheet = next((s for s in excel_file.sheet_names if 'master' in s.lower()), excel_file.sheet_names[0])

            # 1. READ RAW GRID (No Headers)
            df_raw = pd.read_excel(file, sheet_name=target_sheet, header=None)
            df_raw = df_raw.fillna('')

            header_row_idx = -1
            col_map = {}

            # 2. SCAN FOR COORDINATES
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
                flash("Error: Could not find headers (like 'From Date'). Check file format.", 'error')
                return redirect(url_for('migrate_data'))

            migrated_count = 0

            # 3. EXTRACT BY COORDINATES (Skipping the header row)
            for idx in range(header_row_idx + 1, len(df_raw)):
                row = df_raw.iloc[idx].values
                
                def get_val(key):
                    if key in col_map and col_map[key] < len(row):
                        return str(row[col_map[key]]).strip()
                    return ''

                date_val = get_val('date')
                desc = get_val('desc')

                if not date_val and not desc:
                    continue

                try:
                    clean_date = str(date_val).strip().lower()
                    if not clean_date or clean_date in ['nat', 'nan', 'none']:
                        start_date = datetime.utcnow()
                    else:
                        parsed = pd.to_datetime(date_val, errors='coerce')
                        if pd.isna(parsed):
                            start_date = datetime.utcnow()
                        else:
                            start_date = parsed.to_pydatetime()
                except:
                    start_date = datetime.utcnow()

                req = get_val('req')
                pic = get_val('pic')
                person = get_val('person')
                assigned = pic if pic else person
                
                act = get_val('act')
                disc = get_val('disc')
                
                rem1 = get_val('rem1')
                rem2 = get_val('rem2')
                store = get_val('store')
                
                safe_scope = (desc[:95] + '...') if len(desc) > 95 else desc
                if not safe_scope: safe_scope = "Historical_Task"
                
                full_remarks = []
                if desc and len(desc) > 95: full_remarks.append(f"Full Description: {desc}")
                if rem1: full_remarks.append(f"Details: {rem1}")
                if rem2: full_remarks.append(f"Remarks: {rem2}")
                if store: full_remarks.append(f"Legacy Path: {store}")
                combined_remarks = " | ".join(full_remarks)

                year_month = start_date.strftime('%Y_%m')

                task = SurveyTask(
                    surveyor_name="Legacy_Import",
                    assigned_to=assigned[:100],
                    requestor=req[:100],
                    task_category=act[:100],
                    action_required=disc[:100],
                    instrument="Legacy_Data",
                    area="900_Legacy_Data",
                    location="DPR_Import",
                    sub_location=year_month,
                    work_scope=safe_scope,
                    remarks=combined_remarks,
                    status="Closed",
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

@app.route('/')
@login_required
def dashboard():
    session['dashboard_view'] = 'user'
    # 17. THE PAGINATION: Limit to 300 to protect mobile memory and JS Filters
    all_tasks = SurveyTask.query.filter(SurveyTask.status != 'Archived') \
        .order_by(SurveyTask.is_urgent.desc(), SurveyTask.start_time.desc()) \
        .limit(300).all()
    is_admin = current_user.email in ADMIN_EMAILS
    return render_template('dashboard.html', name=current_user.name, tasks=all_tasks, is_admin=is_admin)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.email not in ADMIN_EMAILS:
        flash('Access Denied: You do not have Admin privileges.', 'error')
        return redirect(url_for('dashboard'))

    session['dashboard_view'] = 'admin'
    # 17. THE PAGINATION: Limit to 300
    all_tasks = SurveyTask.query.filter(SurveyTask.status != 'Archived') \
        .order_by(SurveyTask.is_urgent.desc(), SurveyTask.start_time.desc()) \
        .limit(300).all()
    users = User.query.order_by(User.name.asc()).all()
    return render_template('admin_dashboard.html', name=current_user.name, tasks=all_tasks, users=users)
@app.route('/system_config_hidden', methods=['GET', 'POST'])
@login_required
def hidden_config():
    config = AppConfig.query.first()
    master_schema = json.loads(config.schema_data) if config else {}
    
    if "file_tree" not in master_schema: master_schema["file_tree"] = {}
    if "requestors" not in master_schema: master_schema["requestors"] = {}
    if "activities" not in master_schema: master_schema["activities"] = {}

    if current_user.email not in ADMIN_EMAILS:
        flash('Access Denied: Admins only.', 'error')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_dept':
            dept = request.form.get('department').strip()
            if dept and dept not in master_schema['requestors']: master_schema['requestors'][dept] = []
        elif action == 'delete_dept':
            dept = request.form.get('department')
            if dept in master_schema['requestors']: del master_schema['requestors'][dept]
        elif action == 'add_requestor':
            dept = request.form.get('department')
            name = request.form.get('name').strip()
            if dept in master_schema['requestors'] and name not in master_schema['requestors'][dept]:
                master_schema['requestors'][dept].append(name)
                master_schema['requestors'][dept].sort()
        elif action == 'delete_requestor':
            dept = request.form.get('department')
            name = request.form.get('name')
            if dept in master_schema['requestors'] and name in master_schema['requestors'][dept]:
                master_schema['requestors'][dept].remove(name)

        elif action == 'add_activity':
            act = request.form.get('activity').strip()
            if act and act not in master_schema['activities']: master_schema['activities'][act] = {}
        elif action == 'delete_activity':
            act = request.form.get('activity')
            if act in master_schema['activities']: del master_schema['activities'][act]
        elif action == 'add_action':
            act = request.form.get('activity')
            req_action = request.form.get('req_action').strip()
            if act in master_schema['activities'] and req_action not in master_schema['activities'][act]:
                master_schema['activities'][act][req_action] = []
        elif action == 'delete_action':
            act = request.form.get('activity')
            req_action = request.form.get('req_action')
            if act in master_schema['activities'] and req_action in master_schema['activities'][act]:
                del master_schema['activities'][act][req_action]
        elif action == 'add_instrument':
            act = request.form.get('activity')
            req_action = request.form.get('req_action')
            inst = request.form.get('instrument').strip()
            if act in master_schema['activities'] and req_action in master_schema['activities'][act]:
                if inst not in master_schema['activities'][act][req_action]:
                    master_schema['activities'][act][req_action].append(inst)
                    master_schema['activities'][act][req_action].sort()
        elif action == 'delete_instrument':
            act = request.form.get('activity')
            req_action = request.form.get('req_action')
            inst = request.form.get('instrument')
            if act in master_schema['activities'] and req_action in master_schema['activities'][act]:
                if inst in master_schema['activities'][act][req_action]:
                    master_schema['activities'][act][req_action].remove(inst)
# --- FILE TREE ACTIONS ---
        elif action == 'add_area':
            area = request.form.get('area').strip()
            if area and area not in master_schema['file_tree']:
                master_schema['file_tree'][area] = {}
        elif action == 'delete_area':
            area = request.form.get('area')
            if area in master_schema['file_tree']:
                del master_schema['file_tree'][area]

        elif action == 'add_location':
            area = request.form.get('area')
            loc = request.form.get('location').strip()
            if area in master_schema['file_tree'] and loc not in master_schema['file_tree'][area]:
                master_schema['file_tree'][area][loc] = {}
        elif action == 'delete_location':
            area = request.form.get('area')
            loc = request.form.get('location')
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area]:
                del master_schema['file_tree'][area][loc]

        elif action == 'add_sub':
            area = request.form.get('area')
            loc = request.form.get('location')
            sub = request.form.get('sub_location').strip()
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area]:
                if sub not in master_schema['file_tree'][area][loc]:
                    master_schema['file_tree'][area][loc][sub] = []
        elif action == 'delete_sub':
            area = request.form.get('area')
            loc = request.form.get('location')
            sub = request.form.get('sub_location')
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area]:
                if sub in master_schema['file_tree'][area][loc]:
                    del master_schema['file_tree'][area][loc][sub]

        elif action == 'add_scope':
            area = request.form.get('area')
            loc = request.form.get('location')
            sub = request.form.get('sub_location')
            scope = request.form.get('scope').strip()
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area] and sub in master_schema['file_tree'][area][loc]:
                if scope not in master_schema['file_tree'][area][loc][sub]:
                    master_schema['file_tree'][area][loc][sub].append(scope)
                    master_schema['file_tree'][area][loc][sub].sort()
        elif action == 'delete_scope':
            area = request.form.get('area')
            loc = request.form.get('location')
            sub = request.form.get('sub_location')
            scope = request.form.get('scope')
            if area in master_schema['file_tree'] and loc in master_schema['file_tree'][area] and sub in master_schema['file_tree'][area][loc]:
                if scope in master_schema['file_tree'][area][loc][sub]:
                    master_schema['file_tree'][area][loc][sub].remove(scope)
        config.schema_data = json.dumps(master_schema)
        db.session.commit()
        flash('System Configuration Updated!', 'success')
        return redirect(url_for('hidden_config'))
        
    return render_template('hidden_admin.html', master_schema_json=json.dumps(master_schema))
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
            # --- STRICT BACKEND VALIDATION ---
            check_area = request.form.get('area')
            check_scope = request.form.get('work_scope')
        
            if not check_area or check_area.strip() == '':
                flash("Validation Error: You must select an Area.", "error")
                return redirect(request.url)
            if not check_scope or check_scope.strip() == '':
                flash("Validation Error: You must select a Work Scope.", "error")
                return redirect(request.url)
            # ---------------------------------
        
            req_dept = request.form.get('requestor_dept')
            req_name = request.form.get('requestor_name')
            merged_requestor = f"{req_dept} - {req_name}"
            
            assigned_list = request.form.getlist('assigned_to')
            assigned_str = ", ".join([a for a in assigned_list if a.strip()])
            
            save_preset = request.form.get('save_preset')
            preset_name = request.form.get('preset_name')
            if save_preset == 'true':
                p_name = preset_name or f"{request.form.get('area')} - {request.form.get('work_scope')}"
                db.session.add(PresetTask(
                    user_id=current_user.id, preset_name=p_name, req_dept=req_dept, req_name=req_name,
                    assigned_to=assigned_str, task_category=request.form.get('task_category'),
                    area=request.form.get('area'), location=request.form.get('location'), 
                    sub_location=request.form.get('sub_location'), work_scope=request.form.get('work_scope'),
                    instrument=request.form.get('instrument'), action_required=request.form.get('action_required'),
                    remarks=request.form.get('remarks') # <--- ADD THIS LINE
                ))
            
            ref_links = request.form.getlist('reference_link')
            ref_links_str = " | ".join([link for link in ref_links if link.strip()])

            is_urgent_val = True if request.form.get('is_urgent') else False

            new_survey = SurveyTask(
                surveyor_name=current_user.name, assigned_to=assigned_str, requestor=merged_requestor,
                task_category=request.form.get('task_category'), instrument=request.form.get('instrument'), action_required=request.form.get('action_required'),
                area=request.form.get('area'), location=request.form.get('location'), sub_location=request.form.get('sub_location'),
                work_scope=request.form.get('work_scope'), remarks=request.form.get('remarks'), reference_links=ref_links_str,
                is_urgent=is_urgent_val
            )
            db.session.add(new_survey)
            db.session.commit()      
            flash('New task opened successfully!', 'success')
            return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))
            
        # --- NEW: BUILD THE UNIQUE USER JSON DICTIONARY ---
        user_presets = PresetTask.query.filter_by(user_id=current_user.id).all()
        presets_dict = {}
        for p in user_presets:
            presets_dict[p.id] = {
                'req_dept': p.req_dept or "", 'req_name': p.req_name or "", 'assigned_to': p.assigned_to or "",
                'task_category': p.task_category or "", 'area': p.area or "", 'location': p.location or "",
                'sub_location': p.sub_location or "", 'work_scope': p.work_scope or "",
                'instrument': p.instrument or "", 'action_required': p.action_required or "",
                'remarks': p.remarks or ""
            }
            
        return render_template('new_task.html', 
                               users=User.query.filter_by(is_approved=True, is_active=True).order_by(User.name.asc()).all(),
                               req_dict_json=json.dumps(req_dict), 
                               schema_json=json.dumps(file_tree),
                               activities_json=json.dumps(activities_data),
                               presets_json=json.dumps(presets_dict),
                               presets=user_presets)
                               
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"<h2>DIAGNOSTIC CRASH REPORT (NEW TASK)</h2><p>Error: {str(e)}</p><pre>{error_details}</pre>"        
@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    try:
        task = SurveyTask.query.get_or_404(task_id)
        
        assigned_users = [name.strip() for name in task.assigned_to.split(',')] if task.assigned_to else []
        is_admin = current_user.email in ADMIN_EMAILS
        
        if not is_admin and current_user.name != task.surveyor_name and current_user.name not in assigned_users:
            flash('Unauthorized to edit this task.', 'error')
            return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))

        if request.method == 'POST':
            # --- STRICT BACKEND VALIDATION ---
            check_area = request.form.get('area')
            check_scope = request.form.get('work_scope')
            
            if not check_area or check_area.strip() == '':
                flash("Validation Error: You must select an Area.", "error")
                return redirect(request.url)
            if not check_scope or check_scope.strip() == '':
                flash("Validation Error: You must select a Work Scope.", "error")
                return redirect(request.url)
            # ---------------------------------

            req_dept = request.form.get('requestor_dept')
            req_name = request.form.get('requestor_name')
            task.requestor = f"{req_dept} - {req_name}"
            
            assigned_list = request.form.getlist('assigned_to')
            task.assigned_to = ", ".join([a for a in assigned_list if a.strip()])
            
            task.task_category = request.form.get('task_category')
            task.area = request.form.get('area')
            task.location = request.form.get('location')
            task.sub_location = request.form.get('sub_location')
            task.work_scope = request.form.get('work_scope')
            task.instrument = request.form.get('instrument')
            task.action_required = request.form.get('action_required')
            task.remarks = request.form.get('remarks')
            task.is_urgent = True if request.form.get('is_urgent') else False

            ref_links = request.form.getlist('reference_link')
            task.reference_links = " | ".join([link for link in ref_links if link.strip()])

            db.session.commit()
            flash('Task updated successfully!', 'success')
            return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))

        config = AppConfig.query.first()
        master_schema = json.loads(config.schema_data) if config else {}
        file_tree = master_schema.get("file_tree", {})
        req_dict = master_schema.get("requestors", {})
        activities_data = master_schema.get("activities", {})
            
        task_dict = {
            'task_category': task.task_category or "", 'instrument': task.instrument or "",
            'action_required': task.action_required or "", 'area': task.area or "", 'location': task.location or "",
            'sub_location': task.sub_location or "", 'work_scope': task.work_scope or ""
        }
        
        if task.requestor and " - " in task.requestor:
            task_dict['req_dept'], task_dict['req_name'] = task.requestor.split(" - ", 1)
        else:
            task_dict['req_dept'], task_dict['req_name'] = "", ""

        try:
            task_id_str = task.start_time.strftime('%Y%m%d-%H%M%S') if task.start_time else f"UNKNOWN-{task.id}"
        except Exception:
            task_id_str = str(task.start_time)

        class ShimOption:
            def __init__(self, name): self.name = name

        categories = sorted([ShimOption(k) for k in activities_data.keys()], key=lambda x: x.name)
        actions_set, instruments_set = set(), set()
        for acts in activities_data.values():
            for act, insts in acts.items():
                actions_set.add(act)
                instruments_set.update(insts)
        
        actions = sorted([ShimOption(a) for a in actions_set], key=lambda x: x.name)
        instruments = sorted([ShimOption(i) for i in instruments_set], key=lambda x: x.name)

        return render_template('edit_task.html', 
                               task=task, task_id_str=task_id_str,
                               users=User.query.filter_by(is_approved=True, is_active=True).order_by(User.name.asc()).all(),
                               req_dict_json=json.dumps(req_dict), 
                               schema_json=json.dumps(file_tree), 
                               activities_json=json.dumps(activities_data),
                               categories=categories, instruments=instruments, actions=actions,
                               task_json=json.dumps(task_dict))
                                  
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"<div style='padding:20px; border:2px solid red;'><h2 style='color:red;'>CRASH</h2><p>{str(e)}</p><pre>{error_details}</pre></div>"

@app.route('/close_task/<int:task_id>', methods=['POST'])
@login_required
def close_task(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    assigned_users = [name.strip() for name in task.assigned_to.split(',')] if task.assigned_to else []
    is_admin = current_user.email in ADMIN_EMAILS
    
    if not is_admin and current_user.name != task.surveyor_name and current_user.name not in assigned_users:
        flash('Unauthorized.', 'error')
        return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))
    closing_remarks = request.form.get('closing_remarks')
    if not closing_remarks:
        flash('Closing remarks are mandatory.', 'error')
        return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))

    task.remarks = f"{task.remarks} | Closed: {closing_remarks}" if task.remarks else f"Closed: {closing_remarks}"
    if request.form.get('deliverable_link'):
        task.deliverable_link = request.form.get('deliverable_link')
        
    task.status = 'Closed'
    task.end_time = datetime.utcnow()
    db.session.commit()
    flash('Task closed and logged!', 'success')
    return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))

@app.route('/cancel_task/<int:task_id>', methods=['POST'])
@login_required
def cancel_task(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    assigned_users = [name.strip() for name in task.assigned_to.split(',')] if task.assigned_to else []
    is_admin = current_user.email in ADMIN_EMAILS
    
    if not is_admin and current_user.name != task.surveyor_name and current_user.name not in assigned_users:
        flash('Unauthorized.', 'error')
        return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))
    cancel_reason = request.form.get('cancel_reason')
    if not cancel_reason:
        flash('Cancel reason is mandatory.', 'error')
        return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))
        
    task.remarks = f"{task.remarks} | CANCELED: {cancel_reason}" if task.remarks else f"CANCELED: {cancel_reason}"
    task.status = 'Canceled'
    task.end_time = datetime.utcnow()
    db.session.commit()
    flash('Task canceled.', 'error')
    return redirect(url_for('admin_dashboard') if session.get('dashboard_view') == 'admin' else url_for('dashboard'))
    
# --- REPORT GENERATOR ROUTES ---
@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/generate_dtr', methods=['POST'])
@login_required
def generate_dtr():
    try:
        target_date_str = request.form.get('dtr_date')
        if not target_date_str: return redirect(url_for('reports'))

        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
        next_day = target_date + timedelta(days=1)
        
        # 1. GET CLOSED TASKS FOR DTR BODY
        daily_tasks = SurveyTask.query.filter(
            SurveyTask.start_time >= target_date,
            SurveyTask.start_time < next_day,
            SurveyTask.status == 'Closed' 
        ).all()

        dtr_groups = {}
        for t in daily_tasks:
            loc = t.location.split('_', 1)[-1].replace('_', ' ') if t.location and t.location != 'N/A' else ''
            sub = t.sub_location.split('_', 1)[-1].replace('_', ' ') if t.sub_location and t.sub_location != 'N/A' else ''
            scope = t.work_scope.split('_', 1)[-1].replace('_', ' ') if t.work_scope and t.work_scope != 'N/A' else ''
            
            raw_parts = [loc, sub, scope, t.action_required]
            clean_parts = [p.strip() for p in raw_parts if p and p.strip().lower() != 'general']
            t.action_phrase = " ".join(clean_parts)
            
            raw_remark = t.remarks or ""
            opening_remark = raw_remark.split("| Closed:")[0].split("| CANCELED:")[0].strip()

            assigned = t.assigned_to if t.assigned_to else t.surveyor_name
            surveyors = [s.strip() for s in assigned.split(',') if s.strip()]

            group_type = "inline"
            boat_name = ""
            
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
                
            task_bullet = t.action_phrase
            if opening_remark: task_bullet = f"{task_bullet} - {opening_remark}" if task_bullet else opening_remark
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

        # 2. GET OPEN TASKS FOR OUTSTANDING ACTIONS 
        open_tasks = SurveyTask.query.filter_by(status='Open').all()
        outstanding_set = set() # Use a set to prevent duplicate lines
        for t in open_tasks:
            loc = t.location.split('_', 1)[-1].replace('_', ' ') if t.location and t.location != 'N/A' else ''
            sub = t.sub_location.split('_', 1)[-1].replace('_', ' ') if t.sub_location and t.sub_location != 'N/A' else ''
            scope = t.work_scope.split('_', 1)[-1].replace('_', ' ') if t.work_scope and t.work_scope != 'N/A' else ''
            raw = [loc, sub, scope, t.action_required]
            clean = [p.strip() for p in raw if p and p.strip().lower() != 'general']
            phrase = " ".join(clean)
            if phrase:
                outstanding_set.add(phrase)

        template_path = os.path.join(app.root_path, 'static', 'report_templates', 'DTR_Template.docx')
        doc = DocxTemplate(template_path)
        context = {
            'target_date': target_date.strftime('%d.%m.%Y'),
            'day_of_week': target_date.strftime('%A'),
            'report_blocks': report_blocks,
            'outstanding_tasks': list(outstanding_set)
        }
        doc.render(context)
        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return send_file(output, download_name=f"{target_date.strftime('%Y%m%d')}-DTR-Report.docx", as_attachment=True)
    except Exception as e:
        flash(f'DTR Generation Failed. Ensure DTR_Template.docx exists. Error: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/generate_wsr', methods=['POST'])
@login_required
def generate_wsr():
    try:
        week_str = request.form.get('wsr_week')
        if not week_str: return redirect(url_for('reports'))
        year, week = map(int, week_str.split('-W'))
        start_date = datetime.strptime(f'{year}-W{week}-1', "%Y-W%W-%w")
        
        days_data = []
        for i in range(7):
            current_day = start_date + timedelta(days=i)
            next_day = current_day + timedelta(days=1)
            
            daily_tasks = SurveyTask.query.filter(
                SurveyTask.start_time >= current_day,
                SurveyTask.start_time < next_day,
                SurveyTask.status == 'Closed'
            ).all()
            
            dtr_groups = {}
            for t in daily_tasks:
                loc = t.location.split('_', 1)[-1].replace('_', ' ') if t.location and t.location != 'N/A' else ''
                sub = t.sub_location.split('_', 1)[-1].replace('_', ' ') if t.sub_location and t.sub_location != 'N/A' else ''
                scope = t.work_scope.split('_', 1)[-1].replace('_', ' ') if t.work_scope and t.work_scope != 'N/A' else ''
                clean_parts = [p.strip() for p in [loc, sub, scope, t.action_required] if p and p.strip().lower() != 'general']
                t.action_phrase = " ".join(clean_parts)
                opening_remark = (t.remarks or "").split("| Closed:")[0].split("| CANCELED:")[0].strip()
                surveyors = [s.strip() for s in (t.assigned_to or t.surveyor_name).split(',') if s.strip()]

                group_type, boat_name = "inline", ""
                if "WS166" in str(t.instrument) or "WS166" in opening_remark: group_key, group_type, boat_name = "EGST Hydro Survey", "hydro", "WS166"
                elif "Arzana" in str(t.instrument) or "Arzana" in str(t.work_scope) or "Arzana" in opening_remark: group_key, group_type = "Arzana", "vessel"
                elif t.area and t.area.startswith('100'): group_key = "Wuqi Office"
                elif t.area and t.area.startswith('200'): group_key = "Onshore-Land"
                else: group_key = "Marine Offshore"

                if group_key not in dtr_groups: dtr_groups[group_key] = {"title": group_key, "type": group_type, "surveyors": set(), "tasks": [], "boat": boat_name}
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
                    
            days_data.append({'date_string': current_day.strftime('%d.%m.%Y %A'), 'blocks': report_blocks})
            
        template_path = os.path.join(app.root_path, 'static', 'report_templates', 'WSR_Template.docx')
        doc = DocxTemplate(template_path)
        context = {'start_date': start_date.strftime('%d.%m.%Y'), 'end_date': (start_date + timedelta(days=6)).strftime('%d.%m.%Y'), 'days': days_data}
        doc.render(context)
        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return send_file(output, download_name=f"WSR_{week_str}.docx", as_attachment=True)
    except Exception as e:
        flash(f'WSR Generation Failed. Ensure WSR_Template.docx exists. Error: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/generate_tpc', methods=['POST'])
@login_required
def generate_tpc():
    try:
        week_str = request.form.get('tpc_week')
        if not week_str: return redirect(url_for('reports'))
        
        year, week = map(int, week_str.split('-W'))
        
        # 1. Grab the Monday of the selected week
        monday_date = datetime.strptime(f'{year}-W{week}-1', "%Y-W%W-%w")
        
        # 2. Rewind 3 days to get the previous Friday (Start Date)
        start_date = monday_date - timedelta(days=3)
        
        # 3. Add 7 full days for the database query cutoff (Strictly covers up to Thursday 23:59:59)
        query_end_date = start_date + timedelta(days=7)
        
        # 4. Display End Date (Thursday) for the Word Document tags
        display_end_date = start_date + timedelta(days=6)
        
        weekly_tasks = SurveyTask.query.filter(
            SurveyTask.start_time >= start_date, 
            SurveyTask.start_time < query_end_date, 
            SurveyTask.status == 'Closed'
        ).all()
        
        done_set = set()
        for t in weekly_tasks:
            loc = t.location.split('_', 1)[-1].replace('_', ' ') if t.location and t.location != 'N/A' else ''
            scope = t.work_scope.split('_', 1)[-1].replace('_', ' ') if t.work_scope and t.work_scope != 'N/A' else ''
            clean_parts = [p.strip() for p in [loc, scope, t.action_required] if p and p.strip().lower() != 'general']
            phrase = " ".join(clean_parts)
            if phrase: done_set.add(phrase)
            
        open_tasks = SurveyTask.query.filter_by(status='Open').all()
        planned_set = set()
        for t in open_tasks:
            loc = t.location.split('_', 1)[-1].replace('_', ' ') if t.location and t.location != 'N/A' else ''
            scope = t.work_scope.split('_', 1)[-1].replace('_', ' ') if t.work_scope and t.work_scope != 'N/A' else ''
            clean_parts = [p.strip() for p in [loc, scope, t.action_required] if p and p.strip().lower() != 'general']
            phrase = " ".join(clean_parts)
            if phrase: planned_set.add(phrase)
            
        template_path = os.path.join(app.root_path, 'static', 'report_templates', 'TPC_Template.docx')
        doc = DocxTemplate(template_path)
        
        context = {
            'start_date': start_date.strftime('%d %b %Y'), 
            'end_date': display_end_date.strftime('%d %b %Y'),
            'done_activities': list(done_set), 
            'planned_activities': list(planned_set)
        }
        doc.render(context)
        
        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        
        # Generates a clean filename like: TPC_Report_20260227_to_20260305.docx
        filename = f"TPC_Report_{start_date.strftime('%Y%m%d')}_to_{display_end_date.strftime('%Y%m%d')}.docx"
        return send_file(output, download_name=filename, as_attachment=True)
        
    except Exception as e:
        flash(f'TPC Generation Failed. Ensure TPC_Template.docx exists. Error: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/export_excel', methods=['POST'])
@login_required
def export_excel():
    try:
        kpi_month = request.form.get('kpi_month') 
        target_year, target_month = None, None
        if kpi_month:
            target_year, target_month = kpi_month.split('-')

            # Grab only completed work (both active Closed and 30-day Archived tasks)
            all_tasks = SurveyTask.query.filter(SurveyTask.status.in_(['Closed', 'Archived'])).order_by(SurveyTask.start_time.asc()).all()
        
        # KPI FILTER FIX: Case-insensitive substring match handles both singular and plurals
        excluded_keywords = ["external meeting", "internal coordination", "survey report", "damage report", "item", "request", "sem update"]
        
        tasks = []
        for t in all_tasks:
            if t.action_required:
                if any(ex in t.action_required.lower() for ex in excluded_keywords):
                    continue
            tasks.append(t)
        
        data = []
        month_counters = {} 
        display_index = 1
        
        for task in tasks:
            month_str = task.start_time.strftime('%m') if task.start_time else '00' 
            year_str = task.start_time.strftime('%Y') if task.start_time else '0000'
            
            if month_str not in month_counters: month_counters[month_str] = 1
            else: month_counters[month_str] += 1
                
            seq_num = f"{month_counters[month_str]:03d}"
            req_ref = f"TW_{month_str}{seq_num}"
            survey_ref = f"TW_SU_{month_str}{seq_num}"

            if target_month and target_year:
                if month_str != target_month or year_str != target_year:
                    continue

            loc = task.location.split('_', 1)[-1].replace('_', ' ') if task.location and task.location != 'N/A' else ''
            sub = task.sub_location.split('_', 1)[-1].replace('_', ' ') if task.sub_location and task.sub_location != 'N/A' else ''
            scope = task.work_scope.split('_', 1)[-1].replace('_', ' ') if task.work_scope and task.work_scope != 'N/A' else ''
            
            raw_parts = [loc, sub, scope, task.action_required]
            clean_parts = [p.strip() for p in raw_parts if p and p.strip().lower() != 'general']
            desc_phrase = " ".join(clean_parts)

            data.append({
                'Tender / Project Ref.': '20012', 'Sl No': display_index, 'Activity Type': task.task_category, 'Discipline': task.action_required,
                'Requestor Ref. #': req_ref, 'Survey Ref. #': survey_ref, 'Requestor': task.requestor, 'Assigned to': task.assigned_to,
                'Date/Time Received': task.start_time.strftime('%Y-%m-%d %H:%M') if task.start_time else '',
                'Date/Time Completed': task.end_time.strftime('%Y-%m-%d %H:%M') if task.end_time else '',
                'Description of Survey Works': desc_phrase, 'Special Conditions / Remarks': task.remarks or ''
            })
            display_index += 1
        
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, startrow=2, sheet_name='Master Register')
            worksheet = writer.sheets['Master Register']
            worksheet.cell(row=1, column=5, value="SURVEY ACTIVITY MASTER REGISTER")
            
            header_month = datetime.strptime(kpi_month, "%Y-%m").strftime('%B %Y').upper() if kpi_month else datetime.utcnow().strftime('%B %Y').upper()
            worksheet.cell(row=2, column=1, value=f"MONTH OF {header_month} - SURVEY TEAM")
            
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try: max_length = max(max_length, len(str(cell.value)))
                    except: pass
                worksheet.column_dimensions[column[0].column_letter].width = (max_length + 2)

        output.seek(0)
        return send_file(output, download_name=f"Master_Register_{kpi_month or 'All'}.xlsx", as_attachment=True)
    except Exception as e:
        flash(f'KPI Excel Generation Failed. Error: {str(e)}', 'error')
        return redirect(url_for('reports'))
@app.route('/wipe_all_presets')
@login_required
def wipe_all_presets():
    # Security Check: Only VIP Admins can trigger this
    if current_user.email not in ADMIN_EMAILS:
        flash('Access Denied: Admins only.', 'error')
        return redirect(url_for('dashboard'))
        
    try:
        # Delete every row in the PresetTask table
        deleted_count = db.session.query(PresetTask).delete()
        db.session.commit()
        flash(f'Blank Slate Achieved! Successfully deleted {deleted_count} old presets across all users.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error wiping presets: {str(e)}', 'error')
        
    return redirect(url_for('admin_dashboard'))
if __name__ == '__main__':
    app.run(debug=True, port=5001)
