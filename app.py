import os, json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

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

class SurveyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    surveyor_name = db.Column(db.String(100), nullable=False) # The Creator
    assigned_to = db.Column(db.String(100), nullable=True)    # The Assignee
    requestor = db.Column(db.String(100), nullable=True)
    task_category = db.Column(db.String(100), nullable=True) 
    instrument = db.Column(db.String(100), nullable=True) 
    action_required = db.Column(db.String(100), nullable=True) 
    area = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=True) 
    sub_location = db.Column(db.String(100), nullable=True) 
    work_scope = db.Column(db.String(100), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    deliverable_link = db.Column(db.String(500), nullable=True) # NEW COLUMN
    status = db.Column(db.String(20), default="Open")
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)

with app.app_context():
    db.drop_all() # <-- TEMPORARILY UNCOMMENT FOR FIRST DEPLOY, THEN DELETE
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

# --- AUTHENTICATION ROUTES (Omitted for brevity, keep your exact existing ones) ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    # ... KEEP EXISTING CODE ...
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
    # ... KEEP EXISTING CODE ...
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

@app.route('/system_config_hidden', methods=['GET', 'POST'])
@login_required
def hidden_config():
    # ... KEEP EXISTING CODE ...
    config = AppConfig.query.first()
    schema = json.loads(config.schema_data)
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_requestor':
            dept = request.form.get('department')
            name = request.form.get('name').capitalize()
            db.session.add(Requestor(department=dept, name=name))
        elif action == 'add_dropdown':
            cat = request.form.get('category')
            new_val = request.form.get('new_value')
            db.session.add(DropdownOption(category=cat, name=new_val))
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
    open_tasks = SurveyTask.query.filter_by(status='Open').order_by(SurveyTask.start_time.desc()).all()
    return render_template('dashboard.html', name=current_user.name, tasks=open_tasks)

@app.route('/new_task', methods=['GET', 'POST'])
@login_required
def new_task():
    # ... KEEP EXISTING CODE ...
    config = AppConfig.query.first()
    schema_json = config.schema_data if config else "{}"
    if request.method == 'POST':
        new_survey = SurveyTask(
            surveyor_name=current_user.name, assigned_to=request.form.get('assigned_to'), requestor=request.form.get('requestor'),
            task_category=request.form.get('task_category'), instrument=request.form.get('instrument'), action_required=request.form.get('action_required'),
            area=request.form.get('area'), location=request.form.get('location'), sub_location=request.form.get('sub_location'),
            work_scope=request.form.get('work_scope'), remarks=request.form.get('remarks')
        )
        db.session.add(new_survey)
        db.session.commit()
        flash('New task opened successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    users = User.query.all()
    requestors = Requestor.query.all()
    categories = DropdownOption.query.filter_by(category='TaskCategory').all()
    instruments = DropdownOption.query.filter_by(category='Instrument').all()
    actions = DropdownOption.query.filter_by(category='ActionRequired').all()
    
    return render_template('new_task.html', users=users, requestors=requestors, schema_json=schema_json,
                           categories=categories, instruments=instruments, actions=actions)

# UPDATED: Secure Close Task
@app.route('/close_task/<int:task_id>', methods=['POST'])
@login_required
def close_task(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    
    # 1. Security Check
    if current_user.name not in [task.surveyor_name, task.assigned_to]:
        flash('Unauthorized: Only the task creator or assignee can close this task.', 'error')
        return redirect(url_for('dashboard'))
        
    closing_remarks = request.form.get('closing_remarks')
    deliverable_link = request.form.get('deliverable_link')
    
    # 2. Validation
    if not closing_remarks:
        flash('Closing remarks are mandatory.', 'error')
        return redirect(url_for('dashboard'))

    # 3. Update Database
    task.remarks = f"{task.remarks} | Closed: {closing_remarks}" if task.remarks else f"Closed: {closing_remarks}"
    if deliverable_link:
        task.deliverable_link = deliverable_link
        
    task.status = 'Closed'
    task.end_time = datetime.utcnow()
    db.session.commit()
    flash('Task closed and logged!', 'success')
    return redirect(url_for('dashboard'))

# UPDATED: Secure Cancel Task
@app.route('/cancel_task/<int:task_id>', methods=['POST'])
@login_required
def cancel_task(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    
    # 1. Security Check
    if current_user.name not in [task.surveyor_name, task.assigned_to]:
        flash('Unauthorized: Only the task creator or assignee can cancel this task.', 'error')
        return redirect(url_for('dashboard'))
        
    cancel_reason = request.form.get('cancel_reason')
    
    # 2. Validation
    if not cancel_reason:
        flash('Cancel reason is mandatory.', 'error')
        return redirect(url_for('dashboard'))
        
    # 3. Update Database
    task.remarks = f"{task.remarks} | CANCELED: {cancel_reason}" if task.remarks else f"CANCELED: {cancel_reason}"
    task.status = 'Canceled'
    task.end_time = datetime.utcnow()
    db.session.commit()
    flash('Task canceled.', 'error')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)