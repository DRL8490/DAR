import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURATION ---
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

class SurveyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    surveyor_name = db.Column(db.String(100), nullable=False)
    requestor = db.Column(db.String(100), nullable=True) # Who asked for the survey
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
            
        # Extract name from email (First.Last@...)
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

# --- WORKFLOW ROUTES ---
@app.route('/')
@login_required
def dashboard():
    # Show only tasks that are currently Open
    open_tasks = SurveyTask.query.filter_by(status='Open').order_by(SurveyTask.start_time.desc()).all()
    return render_template('dashboard.html', name=current_user.name, tasks=open_tasks)

@app.route('/new_task', methods=['GET', 'POST'])
@login_required
def new_task():
    if request.method == 'POST':
        new_survey = SurveyTask(
            surveyor_name=current_user.name,
            requestor=request.form.get('requestor'),
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
    return render_template('new_task.html')

@app.route('/close_task/<int:task_id>', methods=['POST'])
@login_required
def close_task(task_id):
    task = SurveyTask.query.get_or_404(task_id)
    closing_remarks = request.form.get('closing_remarks')
    
    if closing_remarks:
        task.remarks = f"{task.remarks} | Closing Note: {closing_remarks}" if task.remarks else f"Closing Note: {closing_remarks}"
    
    task.status = 'Closed'
    task.end_time = datetime.utcnow()
    db.session.commit()
    flash('Task closed and logged to database!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)