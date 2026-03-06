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
    schema_data = db.Column(db.Text, default="{}") # Stores the dynamic dropdowns as JSON

class SurveyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    surveyor_name = db.Column(db.String(100), nullable=False)
    assigned_to = db.Column(db.String(100), nullable=True) # NEW
    requestor = db.Column(db.String(100), nullable=True)
    task_category = db.Column(db.String(100), nullable=True) # NEW
    instrument = db.Column(db.String(100), nullable=True) # NEW
    action_required = db.Column(db.String(100), nullable=True) # NEW
    area = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=True) 
    sub_location = db.Column(db.String(100), nullable=True) 
    work_scope = db.Column(db.String(100), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="Open")
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)

with app.app_context():
    db.create_all()
    # Initialize blank schema if it doesn't exist
    if not AppConfig.query.first():
        db.session.add(AppConfig(schema_data=json.dumps({"Initialize Project Area": {}})))
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- AUTHENTICATION ROUTES (Unchanged) ---
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

# --- HIDDEN ADMIN ROUTE ---
@app.route('/system_config_hidden', methods=['GET', 'POST'])
@login_required
def hidden_config():
    config = AppConfig.query.first()
    schema = json.loads(config.schema_data)
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_requestor':
            dept = request.form.get('department')
            name = request.form.get('name').capitalize() # Forces Sentence case
            db.session.add(Requestor(department=dept, name=name))
            db.session.commit()
            flash('Requestor Added!', 'success')
            return redirect(url_for('hidden_config'))
            
        # Dynamic Schema Builder
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
        flash('Schema Updated!', 'success')
        return redirect(url_for('hidden_config'))
        
    requestors = Requestor.query.all()
    return render_template('hidden_admin.html', schema_json=json.dumps(schema), requestors=requestors)

# --- WORKFLOW ROUTES ---
@app.route('/')
@login_required
def dashboard():
    open_tasks = SurveyTask.query.filter_by(status='Open').order_by(SurveyTask.start_time.desc()).all()
    return render_template('dashboard.html', name=current_user.name, tasks=open_tasks)

@app.route('/new_task', methods=['GET', 'POST'])
@login_required
def new_task():
    config = AppConfig.query.first()
    schema_json = config.schema_data if config else "{}"
    
    if request.method == 'POST':
        new_survey = SurveyTask(
            surveyor_name=current_user.name,
            assigned_to=request.form.get('assigned_to'),
            requestor=request.form.get('requestor'),
            task_category=request.form.get('task_category'),
            instrument=request.form.get('instrument'),
            action_required=request.form.get('action_required'),
            area=request.form.get('area'),
            location=request.form.get('location'),
            sub_location=request.form.get('sub_location'),
            work_scope=request.form.get('work_scope'),
            remarks=request.form.get('remarks')
        )
        db.session.add(new_survey)
        db.session.commit()
        flash('New task opened successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    users = User.query.all()
    requestors = Requestor.query.all()
    return render_template('new_task.html', users=users, requestors=requestors, schema_json=schema_json)

@app.route('/close_task/<int:task_id>', methods=['POST'])
@login_required
def close_task(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    closing_remarks = request.form.get('closing_remarks')
    if closing_remarks:
        task.remarks = f"{task.remarks} | Closed: {closing_remarks}" if task.remarks else f"Closed: {closing_remarks}"
    task.status = 'Closed'
    task.end_time = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/cancel_task/<int:task_id>', methods=['POST'])
@login_required
def cancel_task(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    cancel_reason = request.form.get('cancel_reason')
    if cancel_reason:
        task.remarks = f"{task.remarks} | CANCELED: {cancel_reason}" if task.remarks else f"CANCELED: {cancel_reason}"
    task.status = 'Canceled'
    task.end_time = datetime.utcnow()
    db.session.commit()
    flash('Task canceled.', 'error')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)