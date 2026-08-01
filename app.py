from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'intimacare-secret-key-2026'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'intimacare.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ============ DATABASE MODELS ============

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    member_since = db.Column(db.DateTime, default=datetime.utcnow)
    is_premium = db.Column(db.Boolean, default=False)
    mood_entries = db.relationship('MoodEntry', backref='user', lazy=True)
    water_logs = db.relationship('WaterLog', backref='user', lazy=True)
    diet_plans = db.relationship('DietPlan', backref='user', lazy=True)

class Doctor(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    qualification = db.Column(db.String(200))
    experience = db.Column(db.Integer)
    specialization = db.Column(db.String(100))
    consultation_fee = db.Column(db.Float, default=0)
    is_verified = db.Column(db.Boolean, default=False)
    is_online = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=0)
    total_ratings = db.Column(db.Integer, default=0)

class MoodEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mood = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, default=date.today)

class WaterLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class DietPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    condition = db.Column(db.String(100))
    meal_type = db.Column(db.String(50))
    food_item = db.Column(db.String(200))
    is_recommended = db.Column(db.Boolean, default=True)
    date = db.Column(db.Date, default=date.today)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='pending')
    consultation_type = db.Column(db.String(20))  # video, chat, clinic
    user = db.relationship('User', backref='appointments')
    doctor = db.relationship('Doctor', backref='appointments')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user:
        return user
    return Doctor.query.get(int(user_id))

# ============ ROUTES ============

@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        gender = request.form.get('gender')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            phone=phone,
            gender=gender
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    mood_today = MoodEntry.query.filter_by(user_id=current_user.id, date=today).first()
    water_today = WaterLog.query.filter_by(user_id=current_user.id, date=today).all()
    water_consumed = sum(w.amount for w in water_today)
    return render_template('dashboard.html', 
                         mood_today=mood_today,
                         water_consumed=water_consumed,
                         water_goal=3.0)

@app.route('/log-mood', methods=['POST'])
@login_required
def log_mood():
    mood = request.form.get('mood')
    today = date.today()
    existing = MoodEntry.query.filter_by(user_id=current_user.id, date=today).first()
    if existing:
        existing.mood = mood
    else:
        entry = MoodEntry(user_id=current_user.id, mood=mood)
        db.session.add(entry)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/log-water', methods=['POST'])
@login_required
def log_water():
    amount = float(request.form.get('amount', 0.25))
    log = WaterLog(user_id=current_user.id, amount=amount)
    db.session.add(log)
    db.session.commit()
    return jsonify({'status': 'success', 'amount': amount})

@app.route('/sexual-health')
@login_required
def sexual_health():
    return render_template('sexual_health.html')

@app.route('/diet-chart')
@login_required
def diet_chart():
    conditions = {
        'low_testosterone': {
            'name': 'Low Testosterone',
            'recommended': ['Eggs', 'Almonds', 'Spinach', 'Salmon', 'Milk', 'Banana', 'Oats', 'Dates'],
            'avoid': ['Alcohol', 'Junk Food', 'Sugary Drinks', 'Fried Food']
        },
        'pcod': {
            'name': 'PCOD',
            'recommended': ['Leafy Greens', 'Berries', 'Nuts', 'Whole Grains', 'Fish', 'Yogurt'],
            'avoid': ['Refined Carbs', 'Processed Food', 'Sugar', 'Red Meat']
        },
        'low_libido': {
            'name': 'Low Libido',
            'recommended': ['Watermelon', 'Dark Chocolate', 'Avocado', 'Garlic', 'Ginger'],
            'avoid': ['Soy Products', 'Trans Fats', 'Alcohol', 'Caffeine']
        }
    }
    return render_template('diet_chart.html', conditions=conditions)

@app.route('/water-reminder')
@login_required
def water_reminder():
    today = date.today()
    water_today = WaterLog.query.filter_by(user_id=current_user.id, date=today).all()
    water_consumed = sum(w.amount for w in water_today)
    return render_template('water_reminder.html', water_consumed=water_consumed, water_goal=3.0)

@app.route('/stress-relief')
@login_required
def stress_relief():
    activities = [
        {'name': 'Meditation', 'description': 'Calm your mind', 'icon': 'fa-spa', 'duration': '10 Min'},
        {'name': 'Relaxing Music', 'description': 'Soothing sounds', 'icon': 'fa-music', 'duration': '15 Min'},
        {'name': 'Breathing Exercise', 'description': 'Reduce stress', 'icon': 'fa-wind', 'duration': '5 Min'},
        {'name': 'Positive Quotes', 'description': 'Inspire your mind', 'icon': 'fa-quote-left', 'duration': '5 Min'},
        {'name': 'Sleep Guide', 'description': 'Better sleep', 'icon': 'fa-moon', 'duration': '20 Min'}
    ]
    return render_template('stress_relief.html', activities=activities)

@app.route('/mental-wellness')
@login_required
def mental_wellness():
    return render_template('mental_wellness.html')

@app.route('/ai-companion')
@login_required
def ai_companion():
    return render_template('ai_companion.html')

@app.route('/send-message', methods=['POST'])
@login_required
def send_message():
    message = request.form.get('message')
    # Simple AI response (replace with actual AI API later)
    responses = {
        'hello': 'Hello! How can I help you today? 😊',
        'stress': 'I understand. Try deep breathing - inhale for 4 seconds, hold for 4, exhale for 4. This helps reduce stress.',
        'diet': 'A balanced diet is essential. Include more fruits, vegetables, and whole grains. Stay hydrated!',
        'sleep': 'For better sleep: maintain a regular schedule, avoid screens before bed, and keep your room cool and dark.',
        'default': 'Thank you for sharing. Remember, your health matters. Would you like tips on diet, exercise, or mental wellness?'
    }
    
    response = responses.get('default')
    for key in responses:
        if key in message.lower():
            response = responses[key]
            break
    
    return jsonify({'response': response})

@app.route('/doctors')
@login_required
def doctors():
    doctors_list = Doctor.query.filter_by(is_verified=True).all()
    return render_template('doctors.html', doctors=doctors_list)

@app.route('/book-appointment/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def book_appointment(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    if request.method == 'POST':
        appointment = Appointment(
            user_id=current_user.id,
            doctor_id=doctor_id,
            date=date.fromisoformat(request.form.get('date')),
            time=request.form.get('time'),
            consultation_type=request.form.get('type')
        )
        db.session.add(appointment)
        db.session.commit()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('book_appointment.html', doctor=doctor)

@app.route('/notifications')
@login_required
def notifications():
    notifications_list = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    return render_template('notifications.html', notifications=notifications_list)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('splash'))

# ============ ADMIN ROUTES ============

@app.route('/admin')
def admin_dashboard():
    users = User.query.count()
    doctors = Doctor.query.count()
    appointments = Appointment.query.count()
    return render_template('admin.html', 
                         total_users=users,
                         total_doctors=doctors,
                         total_appointments=appointments)

# ============ INITIALIZE DB ============

with app.app_context():
    db.create_all()
    
    # Create sample doctors if none exist
    if Doctor.query.count() == 0:
        sample_doctors = [
            Doctor(name='Dr. Amit Verma', email='amit@doctor.com', 
                   password=generate_password_hash('doctor123'),
                   qualification='MBBS, MD', experience=8,
                   specialization='Sexologist', consultation_fee=500,
                   is_verified=True, is_online=True, rating=4.8, total_ratings=120),
            Doctor(name='Dr. Neha Kapoor', email='neha@doctor.com',
                   password=generate_password_hash('doctor123'),
                   qualification='MBBS, MS', experience=10,
                   specialization='Sexologist', consultation_fee=600,
                   is_verified=True, is_online=True, rating=4.9, total_ratings=150),
            Doctor(name='Dr. Rahul Sharma', email='rahul@doctor.com',
                   password=generate_password_hash('doctor123'),
                   qualification='MBBS, DNB', experience=6,
                   specialization='Sexologist', consultation_fee=400,
                   is_verified=True, is_online=False, rating=4.7, total_ratings=98)
        ]
        for doc in sample_doctors:
            db.session.add(doc)
        db.session.commit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
