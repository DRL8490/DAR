import pandas as pd
import io
from flask import send_file
import os, json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)

db_url = os.environ.get('DATABASE_URL', 'sqlite:///./survey_data.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'super_secret_key_thpp_survey_2026'

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

class Requestor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)

class AppConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schema_data = db.Column(db.Text, default="{}") 

class DropdownOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False) 
    name = db.Column(db.String(100), nullable=False)

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
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)

with app.app_context():
    # db.drop_all() # <-- Keep this commented out unless you need to do a hard reset!
    db.create_all()
    
    survey_tree = {
        "00_Survey_Office": { "Taichung": { "Wuqi Office": ["General", "Internal Meetings", "External Meetings", "Survey Scope Coordination", "Contracts Coordination", "Survey Requests TW", "Survey Requests UAE"] } },
        "01_Onshore_Area_Scope": { "Taichung": { "AHDD": ["General", "Trial Pits", "Thruster Pit", "Crossover Pits", "Grit Tank", "Drainage"], "Tienli": ["General"], "Berth37": ["General"] }, "Tunghsiao": { "Temp Platform": ["General", "Trial Pits", "Thruster Pit", "Crossover Pits", "Grit Tank", "Drainage"], "Inside Plant": ["General", "Trial Pits", "Thruster Pit", "Crossover Pits"] } },
        "02_Nearshore_Area_Scope": { "Taichung": { "Trench 1": ["General", "Dredging", "Pipeline A", "Pipeline B", "SRI", "Backfilling"] }, "Tunghsiao": { "Trench 8": ["General", "Dredging", "Pipeline A", "Pipeline B", "SRI", "Backfilling"] } },
        "03_Offshore_Area_Scope": { "N/A": { "Trench 2": ["General", "Pipelaying A", "Pipelaying B", "Post-Trenching", "SRI"], "Trench 3": ["General", "Pipelaying A", "Pipelaying B", "Post-Trenching", "SRI"], "Trench 4": ["General", "Pipelaying A", "Pipelaying B", "Post-Trenching", "SRI"], "Trench 5": ["General", "Mattress Installation", "Pipelaying A", "Pipelaying B", "Post-Trenching", "Backfilling"], "Trench 6": ["General", "Mattress Installation", "Pipelaying A", "Pipelaying B", "Post-Trenching", "Backfilling"], "Trench 7": ["General", "Dredging_Midline Tie-In", "Pipeline A", "Pipeline B", "Post-Trenching", "SRI", "Backfilling"] } },
        "04_Marine_Area_Scope": { "N/A": { "N/A": ["General", "Pipeline A", "Pipeline B", "Pipeline SRI", "Backfill"] } }
    }
    
    config = AppConfig.query.first()
    if not config: db.session.add(AppConfig(schema_data=json.dumps(survey_tree)))
    else: config.schema_data = json.dumps(survey_tree)
    
    if not DropdownOption.query.first():
        initial_dropdowns = [
            ('Department', 'SURVEY'), ('Department', 'OPERATIONS'), ('Department', 'DREDGING'), ('Department', 'QA/QC'), ('Department', 'ENERGY'), ('Department', 'SAFETY'), ('Department', 'OFFICE/ADMIN'), ('Department', 'LOGISTICS'), ('Department', 'OTHERS (Specify on remarks)'),
            ('TaskCategory', 'Land'), ('TaskCategory', 'Marine'), ('TaskCategory', 'Land+Marine'), ('TaskCategory', 'Office'), ('TaskCategory', 'Others (Specify on remarks)'),
            ('Instrument', 'Rover'), ('Instrument', 'Total Station'), ('Instrument', 'Level Machine'), ('Instrument', 'Measuring Tape'), ('Instrument', 'CAD'), ('Instrument', 'PDS/Terramodel'), ('Instrument', 'Teams'), ('Instrument', 'PC'), ('Instrument', 'Others (Specify on remarks)'),
            ('ActionRequired', 'Stake-out/Marking'), ('ActionRequired', 'As-Built'), ('ActionRequired', 'Meeting/Coordination'), ('ActionRequired', 'Visual Inspection'), ('ActionRequired', 'Report'), ('ActionRequired', 'Request'), ('ActionRequired', 'Drafting'), ('ActionRequired', 'Design'), ('ActionRequired', 'Charting'), ('ActionRequired', 'Quantity Sheet'), ('ActionRequired', 'Others (Specify on remarks)')
        ]
        for cat, name in initial_dropdowns: db.session.add(DropdownOption(category=cat, name=name))
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
        new_user = User(email=email, name=formatted_name, password_hash=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

# --- ADMIN ROUTE ---
@app.route('/system_config_hidden', methods=['GET', 'POST'])
@login_required
def hidden_config():
    config = AppConfig.query.first()
    schema = json.loads(config.schema_data)
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_requestor':
            db.session.add(Requestor(department=request.form.get('department'), name=request.form.get('name').capitalize()))
        elif action == 'add_dropdown':
            db.session.add(DropdownOption(category=request.form.get('category'), name=request.form.get('new_value')))
        else:
            area = request.form.get('area')
            loc = request.form.get('location')
            sub = request.form.get('sub_location')
            scope = request.form.get('work_scope')
            if action == 'add_area' and area:
                if area not in schema: schema[area] = {}
            elif action == 'add_location' and area and loc:
                if area in schema and loc not in schema[area]: schema[area][loc] = {}
            elif action == 'add_subloc' and area and loc and sub:
                if area in schema and loc in schema[area] and sub not in schema[area][loc]: schema[area][loc][sub] = []
            elif action == 'add_scope' and area and loc and sub and scope:
                if area in schema and loc in schema[area] and sub in schema[area][loc]:
                    if scope not in schema[area][loc][sub]: schema[area][loc][sub].append(scope)
            config.schema_data = json.dumps(schema)
        db.session.commit()
        flash('Database Updated!', 'success')
        return redirect(url_for('hidden_config'))
        
    requestors = Requestor.query.all()
    departments = DropdownOption.query.filter_by(category='Department').all()
    return render_template('hidden_admin.html', schema_json=json.dumps(schema), requestors=requestors, departments=departments)

# --- WORKFLOW ROUTES ---
@app.route('/')
@login_required
def dashboard():
    all_tasks = SurveyTask.query.order_by(SurveyTask.start_time.desc()).all()
    return render_template('dashboard.html', name=current_user.name, tasks=all_tasks)

@app.route('/new_task', methods=['GET', 'POST'])
@login_required
def new_task():
    config = AppConfig.query.first()
    schema_json = config.schema_data if config else "{}"
    
    preset_id = request.args.get('preset_id')
    loaded_preset = None
    if preset_id:
        loaded_preset = PresetTask.query.filter_by(id=preset_id, user_id=current_user.id).first()
        if loaded_preset:
            loaded_preset = {c.name: getattr(loaded_preset, c.name) for c in loaded_preset.__table__.columns}
    
    if request.method == 'POST':
        req_dept = request.form.get('requestor_dept')
        req_name = request.form.get('requestor_name')
        merged_requestor = f"{req_dept} - {req_name}"
        
        save_preset = request.form.get('save_preset')
        preset_name = request.form.get('preset_name')
        if save_preset == 'true':
            p_name = preset_name or f"{request.form.get('area')} - {request.form.get('work_scope')}"
            db.session.add(PresetTask(
                user_id=current_user.id, preset_name=p_name, req_dept=req_dept, req_name=req_name,
                assigned_to=request.form.get('assigned_to'), task_category=request.form.get('task_category'),
                area=request.form.get('area'), location=request.form.get('location'), 
                sub_location=request.form.get('sub_location'), work_scope=request.form.get('work_scope'),
                instrument=request.form.get('instrument'), action_required=request.form.get('action_required')
            ))
        
        ref_links = request.form.getlist('reference_link')
        ref_links_str = " | ".join([link for link in ref_links if link.strip()])

        new_survey = SurveyTask(
            surveyor_name=current_user.name, assigned_to=request.form.get('assigned_to'), requestor=merged_requestor,
            task_category=request.form.get('task_category'), instrument=request.form.get('instrument'), action_required=request.form.get('action_required'),
            area=request.form.get('area'), location=request.form.get('location'), sub_location=request.form.get('sub_location'),
            work_scope=request.form.get('work_scope'), remarks=request.form.get('remarks'), reference_links=ref_links_str
        )
        db.session.add(new_survey)
        db.session.commit()
        flash('New task opened successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    requestors = Requestor.query.all()
    req_dict = {}
    for r in requestors:
        if r.department not in req_dict: req_dict[r.department] = []
        req_dict[r.department].append(r.name)
        
    user_presets = PresetTask.query.filter_by(user_id=current_user.id).all()
        
    return render_template('new_task.html', users=User.query.all(), req_dict_json=json.dumps(req_dict), schema_json=schema_json,
                           categories=DropdownOption.query.filter_by(category='TaskCategory').all(), 
                           instruments=DropdownOption.query.filter_by(category='Instrument').all(), 
                           actions=DropdownOption.query.filter_by(category='ActionRequired').all(),
                           loaded_preset=json.dumps(loaded_preset) if loaded_preset else "null",
                           presets=user_presets)

@app.route('/close_task/<int:task_id>', methods=['POST'])
@login_required
def close_task(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    if current_user.name not in [task.surveyor_name, task.assigned_to]:
        flash('Unauthorized.', 'error')
        return redirect(url_for('dashboard'))
        
    closing_remarks = request.form.get('closing_remarks')
    if not closing_remarks:
        flash('Closing remarks are mandatory.', 'error')
        return redirect(url_for('dashboard'))

    task.remarks = f"{task.remarks} | Closed: {closing_remarks}" if task.remarks else f"Closed: {closing_remarks}"
    if request.form.get('deliverable_link'):
        task.deliverable_link = request.form.get('deliverable_link')
        
    task.status = 'Closed'
    task.end_time = datetime.utcnow()
    db.session.commit()
    flash('Task closed and logged!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/cancel_task/<int:task_id>', methods=['POST'])
@login_required
def cancel_task(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    if current_user.name not in [task.surveyor_name, task.assigned_to]:
        flash('Unauthorized.', 'error')
        return redirect(url_for('dashboard'))
        
    cancel_reason = request.form.get('cancel_reason')
    if not cancel_reason:
        flash('Cancel reason is mandatory.', 'error')
        return redirect(url_for('dashboard'))
        
    task.remarks = f"{task.remarks} | CANCELED: {cancel_reason}" if task.remarks else f"CANCELED: {cancel_reason}"
    task.status = 'Canceled'
    task.end_time = datetime.utcnow()
    db.session.commit()
    flash('Task canceled.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/reports')
@login_required
def reports():
    all_tasks = SurveyTask.query.order_by(SurveyTask.start_time.desc()).all()
    return render_template('reports.html', tasks=all_tasks)
@app.route('/export_excel')
@login_required
def export_excel():
    # 1. Grab all tasks from the database
    tasks = SurveyTask.query.order_by(SurveyTask.start_time.asc()).all()
    
    # 2. Map the database columns to your specific Master Register format
    data = []
    for i, task in enumerate(tasks, 1):
        data.append({
            'Tender / Project Ref.': '20012',
            'Sl No': i,
            'Activity Type': task.task_category,
            'Discipline': task.action_required,
            'Requestor Ref. #': '', # Leave blank for manual entry or map later
            'Survey Ref. #': f"THPP-SURV-{task.id:04d}",
            'Requestor': task.requestor,
            'Assigned to': task.assigned_to,
            'Date/Time Received': task.start_time.strftime('%Y-%m-%d %H:%M') if task.start_time else '',
            'Date/Time Completed': task.end_time.strftime('%Y-%m-%d %H:%M') if task.end_time else '',
            'Description of Survey Works / Survey Volume Calculation': f"{task.area} - {task.location or ''} - {task.work_scope}",
            'Special Conditions / Remarks': task.remarks or ''
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    
    # 3. Create the Excel file and inject the custom QA/QC Header Rows
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Start the table on row 3 (index 2) so we have room for the titles
        df.to_excel(writer, index=False, startrow=2, sheet_name='Master Register')
        worksheet = writer.sheets['Master Register']
        
        # Row 1 Title
        worksheet.cell(row=1, column=5, value="SURVEY ACTIVITY MASTER REGISTER")
        
        # Row 2 Title (Dynamically sets the current month/year)
        current_month = datetime.utcnow().strftime("%B %Y").upper()
        worksheet.cell(row=2, column=1, value=f"MONTH OF {current_month} - SURVEY TEAM")
        
        # Auto-adjust column widths for readability
        for column in worksheet.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

    output.seek(0)
    filename = f"2510_QA-20-FM-003-13_Master_SAR-SVR_Register_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
    
    return send_file(output, download_name=filename, as_attachment=True)
@app.route('/pv1_migrate')
@login_required
def pv1_migrate():
    # 1. Update Timezones (UTC to UTC+8)
    tasks = SurveyTask.query.all()
    for t in tasks:
        # Add 8 hours to existing timestamps
        if t.start_time: t.start_time = t.start_time + timedelta(hours=8)
        if t.end_time: t.end_time = t.end_time + timedelta(hours=8)
        
        # 2. Legacy Data Remapper (Protecting your old tasks)
        if t.area == "00_Survey_Office": t.area = "100_Office"
        elif t.area == "01_Onshore_Area_Scope": t.area = "200_Onshore_Area_Scope"
        elif t.area == "02_Nearshore_Area_Scope": t.area = "400_Nearshore_Area_Scope"
        elif t.area == "03_Offshore_Area_Scope": t.area = "500_Offshore_Area_Scope"
        elif t.area == "04_Marine_Area_Scope": t.area = "300_General_Marine"
        
        if t.location == "Taichung": 
            if "100" in t.area: t.location = "110_Taichung"
            elif "200" in t.area: t.location = "211_Taichung"
            elif "400" in t.area: t.location = "411_Taichung"
        elif t.location == "Tunghsiao":
            if "200" in t.area: t.location = "212_Tunghsiao"
            elif "400" in t.area: t.location = "412_Tunghsiao"
            
        if t.location == "Trench 1": t.location = "411-20_Trench 1"
        elif t.location == "Trench 8": t.location = "412-20_Trench 8"
        elif t.location == "Trench 2": t.location = "510_Trench 2"
        elif t.location == "Trench 3": t.location = "511_Trench 3"
        elif t.location == "Trench 4": t.location = "512_Trench 4"
        elif t.location == "Trench 5": t.location = "513_Trench 5"
        elif t.location == "Trench 6": t.location = "514_Trench 6"
        elif t.location == "Trench 7": t.location = "515_Trench 7"
        
        if not t.sub_location: t.sub_location = "N/A"
        
    # 3. Inject new Activity Types & Disciplines
    new_activities = ["Land Survey", "Bathymetric Survey", "Bathymetric & Land Survey", "Volume Calculation", "Drone Survey", "Geophysical Survey", "Lidar Survey", "Excavator Survey", "Tender Survey", "Survey Update", "System Check", "Vessel PDS Update"]
    new_actions = ["Progress Survey", "TSHD/CSD progress survey", "Check survey", "Setting out Survey", "Benchmark Verification Survey", "Stockpile Survey", "GI Survey", "Preloading Survey", "QW Blocks Survey", "QW Bedding Survey", "Concrete Casting Survey", "Pilling Survey", "Maggy/SSS/SBP Pre Survey", "Maggy/SSS/SBP Check Survey", "Maggy/SSS/SBP Progress Survey", "Pre Survey", "Post Survey", "As Build Survey", "Tender Survey", "Design Qty", "Progress Qty", "Tender Qty", "Post Construction Qty / As Build", "Progress Drw", "Pre Survey Drw", "Post Survey Drw", "As Build Drw", "Tender Drw", "Check Survey Drw", "Calibration", "Survey Update", "System Check"]
    
    DropdownOption.query.filter_by(category='TaskCategory').delete()
    DropdownOption.query.filter_by(category='ActionRequired').delete()
    
    for act in new_activities: db.session.add(DropdownOption(category='TaskCategory', name=act))
    for req in new_actions: db.session.add(DropdownOption(category='ActionRequired', name=req))
        
    # 4. Inject the New Project Tree Payload
    fancy_tree = {
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
        "200_Onshore_Area_Scope": {
            "211_Taichung": {
                "N/A": ["211-00_General", "211-90_Others"],
                "211-10_AHDD": ["211-11_General", "211-12_Trial Pits", "211-13_Thruster Pit", "211-14_Crossover Pits", "211-15_Grit Tank", "211-16_Drainage"],
                "211-20_Tienli": ["211-21_General"],
                "211-30_Berth37": ["211-31_General"]
            },
            "212_Tunghsiao": {
                "N/A": ["212-90_Others"],
                "212-10_Temp Platform": ["212-11_General", "212-12_Trial Pits", "212-13_Thruster Pit", "212-14_Crossover Pits", "212-15_Grit Tank", "212-16_Drainage", "212-17_Microtunneling"],
                "212-20_Inside Plant": ["212-21_General", "212-22_Trial Pits", "212-23_Crossover Pits"]
            }
        },
        "300_General_Marine": {
            "N/A": {
                "N/A": ["311_Pre-Surveys", "312_Progress-Surveys", "313_Post-Surveys"],
                "314_Design": ["314-41_General", "314-42_DXF_Backgrounds", "314-43_Routelines", "314-44_3DM+Outlines"],
                "315_Quantity": ["315-51_ICQP_Format", "315-52_CECI_Format", "315-53_Other_Formats"]
            }
        },
        "400_Nearshore_Area_Scope": {
            "411_Taichung": {
                "N/A": ["411-10_General"],
                "411-20_Trench 1": ["411-21_General", "411-22_Dredging", "411-23_Pipelaying A", "411-24_Pipelaying B", "411-25_SRI", "411-26_Backfilling"]
            },
            "412_Tunghsiao": {
                "N/A": ["412-10_General"],
                "412-20_Trench 8": ["412-21_General", "412-22_Dredging", "412-23_Pipelaying A", "412-24_Pipelaying B", "412-25_SRI", "412-26_Backfilling"]
            }
        },
        "500_Offshore_Area_Scope": {
            "510_Trench 2": {
                "N/A": ["510-11_General", "510-12_Pipelaying A", "510-12_Post-Trenching-B", "510-14_SRI-A", "510-15_Pipelaying B", "510-16_Post-Trenching-A", "510-17_SRI-B"]
            },
            "511_Trench 3": {
                "N/A": ["511-11_General", "511-12_Pipelaying A", "511-13_Post-Trenching-A", "511-14_SRI-A", "511-15_Pipelaying B", "511-16_Post-Trenching-B", "511-17_SRI-B"]
            },
            "512_Trench 4": {
                "N/A": ["512-11_General", "512-12_Pipelaying A", "512-13_Post-Trenching-A", "512-14_SRI-A", "512-15_Pipelaying B", "512-16_Post-Trenching-B", "512-17_SRI-B"]
            },
            "513_Trench 5": {
                "N/A": ["513-11_General"],
                "513-12_Pipelaying": ["513-12_Pipelaying-A", "513-12_Pipelaying-B"],
                "513-13_Post-Trenching": ["513-13_Post-Trenching-A", "513-13_Post-Trenching-B"],
                "513-14_SRI": ["513-14_SRI-A", "513-14_SRI-B"],
                "513-15_Backfilling": ["513-15_Backfilling-A", "513-15_Backfilling-B"]
            },
            "514_Trench 6": {
                "N/A": ["514-11_General"],
                "514-12_Pipelaying": ["514-12_Pipelaying-A", "514-12_Pipelaying-B"],
                "514-13_Post-Trenching": ["514-13_Post-Trenching-A", "514-13_Post-Trenching-B"],
                "514-14_SRI": ["514-14_SRI-A", "514-14_SRI-B"],
                "514-15_Backfilling": ["514-15_Backfilling-A", "514-15_Backfilling-B"]
            },
            "515_Trench 7": {
                "N/A": ["515-11_General"],
                "515-12_Pipelaying": ["515-12_Pipelaying-A", "515-12_Pipelaying-B"],
                "515-13_Post-Trenching": ["515-13_Post-Trenching-A", "515-13_Post-Trenching-B"],
                "515-14_SRI": ["515-14_SRI-A", "515-14_SRI-B"],
                "515-15_Backfilling": ["515-15_Backfilling-A", "515-15_Backfilling-B"]
            },
            "516_Midline_Tie-in": {
                "N/A": ["516-11_General", "516-12_Dredging"],
                "516-13_Pipelaying": ["516-12_Pipelaying-A", "516-12_Pipelaying-B"],
                "516-14_Post-Trenching": ["516-13_Post-Trenching-A", "516-13_Post-Trenching-B"],
                "516-15_SRI": ["516-14_SRI-A", "516-14_SRI-B"]
            },
            "517_Crossing-A": {
                "517-10_Crossing-A1": ["517-11_Mattress_Installation-A1", "517-12_Pipelaying-A1", "517-13_SRI-A1"],
                "517-20_Crossing-A2": ["517-21_Mattress_Installation-A1", "517-22_Pipelaying-A1", "517-23_SRI-A1"],
                "517-30_Crossing-A3": ["517-31_Mattress_Installation-A1", "517-33_SRI-A1", "517-51_Pipelaying-A1"]
            },
            "518_Crossing-B": {
                "518-10_Crossing-B1": ["518-11_Mattress_Installation-B1", "518-12_Pipelaying-B1", "518-13_SRI-B1"],
                "518-20_Crossing-B2": ["518-21_Mattress_Installation-B1", "518-22_Pipelaying-B1", "518-23_SRI-B1"],
                "518-30_Crossing-B3": ["518-31_Mattress_Installation-B1", "518-33_SRI-B1", "518-51_Pipelaying-B1"]
            }
        }
    }
    
    config = AppConfig.query.first()
    config.schema_data = json.dumps(fancy_tree)
    
    db.session.commit()
    return "<h1>PV1 MIGRATION COMPLETE!</h1><p>All timezones shifted to UTC+8. Database tree updated. Dropdowns injected. Legacy data remapped safely. You may return to the dashboard.</p>"
if __name__ == '__main__':
    app.run(debug=True, port=5001)