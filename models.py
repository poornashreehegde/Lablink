from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='student', nullable=False)  # 'student', 'faculty', 'admin'
    department = db.Column(db.String(100), nullable=True)
    student_id = db.Column(db.String(40), nullable=True)  # Roll number for students
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_faculty(self):
        return self.role in ['faculty', 'admin']

    def is_student(self):
        return self.role == 'student'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'department': self.department,
            'student_id': self.student_id
        }

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(10), nullable=False, unique=True)
    building = db.Column(db.String(100), nullable=False)
    badge_color = db.Column(db.String(50), default="blue")
    
    equipment_list = db.relationship('Equipment', backref='dept_ref', lazy=True)

class Equipment(db.Model):
    __tablename__ = 'equipment'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False)  # AI Workstation, Embedded/FPGA, RF/Signal, 3D Prototyping, Chemical/Biotech
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    department_name = db.Column(db.String(100), nullable=False)
    lab_name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    faculty_in_charge = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    assigned_faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    specs = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='Available')  # Available, Busy, Maintenance
    icon = db.Column(db.String(50), default='cpu')  # Lucide icon identifier
    safety_prereqs = db.Column(db.String(255), default='Standard Lab Coat & Anti-Static Wristband')
    max_slot_hours = db.Column(db.Integer, default=4)
    total_bookings = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('BookingRequest', backref='equipment_ref', lazy=True, foreign_keys='BookingRequest.equipment_id')
    assigned_faculty = db.relationship('User', backref='assigned_equipment_list', foreign_keys=[assigned_faculty_id])

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'category': self.category,
            'department_name': self.department_name,
            'lab_name': self.lab_name,
            'location': self.location,
            'specs': self.specs,
            'status': self.status,
            'icon': self.icon,
            'faculty_in_charge': self.faculty_in_charge,
            'contact_email': self.contact_email,
            'assigned_faculty_id': self.assigned_faculty_id,
            'max_slot_hours': self.max_slot_hours,
            'total_bookings': self.total_bookings
        }

class BookingRequest(db.Model):
    __tablename__ = 'booking_requests'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Student / Requester Details
    student_name = db.Column(db.String(120), nullable=False)
    student_id = db.Column(db.String(40), nullable=False)
    student_email = db.Column(db.String(120), nullable=False)
    student_dept = db.Column(db.String(100), nullable=False)
    
    # Project Details
    project_title = db.Column(db.String(200), nullable=False)
    project_category = db.Column(db.String(80), nullable=False) # Capstone/Thesis, Sponsored Research, Hackathon/Competition, Coursework
    project_deadline = db.Column(db.Date, nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    
    # Time & Slot
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), nullable=False) # e.g. "09:00"
    end_time = db.Column(db.String(10), nullable=False)   # e.g. "13:00"
    duration_hours = db.Column(db.Integer, default=3)
    
    # Workflow Status
    status = db.Column(db.String(30), default='Pending') # Pending, Approved, Rejected, Rescheduled
    faculty_comments = db.Column(db.Text, nullable=True)
    
    # GenAI Engine Outputs & History Tracking
    priority_score = db.Column(db.Float, default=50.0) # 0 - 100
    priority_tier = db.Column(db.String(20), default='Standard') # High, Medium, Standard
    priority_breakdown = db.Column(db.Text, nullable=True) # readable factors
    conflict_detected = db.Column(db.Boolean, default=False)
    was_conflict = db.Column(db.Boolean, default=False) # Preserves historical conflict metric for analytics
    conflicting_booking_id = db.Column(db.Integer, nullable=True)
    ai_recommendation = db.Column(db.Text, nullable=True)
    ai_alternative_slot = db.Column(db.String(200), nullable=True)
    ai_alternative_equipment = db.Column(db.String(200), nullable=True)
    
    # Structured Alternative Details for Accurate 1-Click Application
    ai_alt_date = db.Column(db.Date, nullable=True)
    ai_alt_start_time = db.Column(db.String(10), nullable=True)
    ai_alt_end_time = db.Column(db.String(10), nullable=True)
    ai_alt_duration = db.Column(db.Integer, nullable=True)
    ai_alt_equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='bookings', foreign_keys=[user_id])
    ai_alt_equipment = db.relationship('Equipment', foreign_keys=[ai_alt_equipment_id])
