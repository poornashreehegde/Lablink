from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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
    specs = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='Available')  # Available, Busy, Maintenance
    icon = db.Column(db.String(50), default='cpu')  # Lucide icon identifier
    safety_prereqs = db.Column(db.String(255), default='Standard Lab Coat & Anti-Static Wristband')
    max_slot_hours = db.Column(db.Integer, default=4)
    total_bookings = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('BookingRequest', backref='equipment_ref', lazy=True)

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
            'max_slot_hours': self.max_slot_hours,
            'total_bookings': self.total_bookings
        }

class BookingRequest(db.Model):
    __tablename__ = 'booking_requests'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    
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
    
    # GenAI Engine Outputs
    priority_score = db.Column(db.Float, default=50.0) # 0 - 100
    priority_tier = db.Column(db.String(20), default='Standard') # High, Medium, Standard
    priority_breakdown = db.Column(db.Text, nullable=True) # JSON / readable factors
    conflict_detected = db.Column(db.Boolean, default=False)
    conflicting_booking_id = db.Column(db.Integer, nullable=True)
    ai_recommendation = db.Column(db.Text, nullable=True)
    ai_alternative_slot = db.Column(db.String(200), nullable=True)
    ai_alternative_equipment = db.Column(db.String(200), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
