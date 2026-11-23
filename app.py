import os
import time
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, g, session
from models import db, Department, Equipment, BookingRequest, User
from auth import (
    login_user, logout_user, get_current_user, login_required, role_required,
    get_csrf_token, validate_csrf
)
from ai_engine import (
    calculate_priority_score, resolve_conflicts_and_recommend, smart_equipment_advisor,
    validate_operating_hours, check_conflicts, find_feasible_alternative,
    time_to_minutes, minutes_to_time, LAB_OPEN_HOUR, LAB_CLOSE_HOUR
)
from seed_data import seed_database

app = Flask(__name__)

# Security: Load secret key from environment variable

is_production = os.environ.get('APP_ENV') == 'production'
secret_key = os.environ.get('SECRET_KEY')

if is_production and not secret_key:
    raise RuntimeError("SECRET_KEY must be configured in production.")

app.config['SECRET_KEY'] = secret_key or 'local-development-secret-key'
app.config['SESSION_COOKIE_SECURE'] = is_production

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# SQLite database path (supports DATABASE_URL / SQLALCHEMY_DATABASE_URI environment variable)
instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
os.makedirs(instance_dir, exist_ok=True)
default_db_uri = f"sqlite:///{os.path.join(instance_dir, 'lablink.db')}"

database_url = (
    os.environ.get('DATABASE_URL')
    or os.environ.get('SQLALCHEMY_DATABASE_URI')
    or default_db_uri
)

if database_url.startswith('postgres://'):
    database_url = database_url.replace(
        'postgres://', 'postgresql+psycopg://', 1
    )
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace(
        'postgresql://', 'postgresql+psycopg://', 1
    )

app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Rate-limiting storage for AI endpoint (in-memory per IP)
_ai_rate_limits = {}

# Initialize database and schema migrations
with app.app_context():
    seed_database()


@app.before_request
def csrf_protect_and_user_loader():
    """Validates CSRF token on state-changing requests and attaches current_user to g."""
    g.user = get_current_user()
    
    # CSRF verification on POST requests
    if request.method == 'POST':
        # Exempt in automated testing when CSRF is disabled
        if app.config.get('TESTING') and not app.config.get('WTF_CSRF_ENABLED', True):
            return
        # Exempt chat API if it uses JSON
        if request.path.startswith('/api/'):
            return
            
        token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
        if not validate_csrf(token):
            flash("Security check failed: Invalid or expired CSRF token. Please try again.", "error")
            return redirect(request.referrer or url_for('index'))


@app.context_processor
def inject_global_template_context():
    """Injected into all templates for authentication state, stats, and CSRF token."""
    total_equip = Equipment.query.count()
    
    current_u = get_current_user()
    if current_u and current_u.is_faculty():
        if current_u.is_admin():
            pending_count = BookingRequest.query.filter_by(status='Pending').count()
            conflict_count = BookingRequest.query.filter_by(status='Pending', conflict_detected=True).count()
        else:
            # Only count for equipment assigned to this faculty
            assigned_ids = [e.id for e in current_u.assigned_equipment_list]
            pending_count = BookingRequest.query.filter(
                BookingRequest.status == 'Pending',
                BookingRequest.equipment_id.in_(assigned_ids)
            ).count() if assigned_ids else 0
            conflict_count = BookingRequest.query.filter(
                BookingRequest.status == 'Pending',
                BookingRequest.conflict_detected == True,
                BookingRequest.equipment_id.in_(assigned_ids)
            ).count() if assigned_ids else 0
    else:
        pending_count = BookingRequest.query.filter_by(status='Pending').count()
        conflict_count = BookingRequest.query.filter_by(status='Pending', conflict_detected=True).count()

    return {
        'current_user': current_u,
        'csrf_token': get_csrf_token,
        'global_total_equip': total_equip,
        'global_pending_count': pending_count,
        'global_conflict_count': conflict_count,
        'current_year': datetime.now().year,
        'lab_open_hour': LAB_OPEN_HOUR,
        'lab_close_hour': LAB_CLOSE_HOUR
    }


# ==========================================
# Authentication Routes (Register, Login, Logout)
# ==========================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Public registration for students only. Faculty and Admin accounts require trusted provisioning."""
    if get_current_user():
        return redirect(url_for('index'))

    departments = Department.query.all()

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        department = request.form.get('department', '').strip()
        student_id = request.form.get('student_id', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Input validation
        if not username or not email or not full_name or not student_id or not password:
            flash("All fields are required for student registration.", "error")
            return render_template('register.html', departments=departments)

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template('register.html', departments=departments)

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template('register.html', departments=departments)

        if User.query.filter_by(username=username).first():
            flash("Username is already taken. Please choose another.", "error")
            return render_template('register.html', departments=departments)

        if User.query.filter_by(email=email).first():
            flash("An account with this email address already exists.", "error")
            return render_template('register.html', departments=departments)

        # STRICT RBAC: Public registration ALWAYS assigns role='student'
        new_student = User(
            username=username,
            email=email,
            full_name=full_name,
            role='student',
            department=department,
            student_id=student_id
        )
        new_student.set_password(password)

        db.session.add(new_student)
        db.session.commit()

        flash("Account created successfully! You can now sign in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html', departments=departments)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Secure user login supporting student, faculty, and admin roles."""
    if get_current_user():
        return redirect(url_for('index'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip().lower()
        password = request.form.get('password', '')
        next_url = request.form.get('next', '').strip()

        if not login_id or not password:
            flash("Please enter both username/email and password.", "error")
            return render_template('login.html', next=next_url)

        # Look up by username or email
        user = User.query.filter(
            (User.username == login_id) | (User.email == login_id)
        ).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.full_name} ({user.role.title()})!", "success")

            # Route redirect based on role or next_url
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            elif user.is_faculty():
                return redirect(url_for('admin_portal'))
            else:
                return redirect(url_for('index'))
        else:
            flash("Invalid credentials. Please verify your login details.", "error")
            return render_template('login.html', next=next_url)

    next_url = request.args.get('next', '')
    return render_template('login.html', next=next_url)


@app.route('/logout')
def logout():
    """Terminates session and logs user out."""
    logout_user()
    flash("You have been signed out safely.", "info")
    return redirect(url_for('login'))


# ==========================================
# Core Application Views & Catalog
# ==========================================

@app.route('/')
def index():
    """Discovery & Catalog View."""
    search_query = request.args.get('q', '').strip()
    selected_dept = request.args.get('dept', '').strip()
    selected_cat = request.args.get('cat', '').strip()
    selected_status = request.args.get('status', '').strip()

    query = Equipment.query

    if search_query:
        query = query.filter(
            (Equipment.name.ilike(f'%{search_query}%')) |
            (Equipment.specs.ilike(f'%{search_query}%')) |
            (Equipment.code.ilike(f'%{search_query}%')) |
            (Equipment.lab_name.ilike(f'%{search_query}%'))
        )
    if selected_dept:
        query = query.filter_by(department_name=selected_dept)
    if selected_cat:
        query = query.filter_by(category=selected_cat)
    if selected_status:
        query = query.filter_by(status=selected_status)

    equipments = query.order_by(Equipment.total_bookings.desc()).all()
    departments = Department.query.all()
    categories = sorted(list(set(e.category for e in Equipment.query.all())))

    # Overview metrics strictly calculated from database
    total_equipment = Equipment.query.count()
    available_equipment = Equipment.query.filter_by(status='Available').count()
    all_approved = BookingRequest.query.filter_by(status='Approved').all()
    total_approved_bookings = len(all_approved)
    
    # Calculate genuine cross-department sharing percentage
    cross_dept_count = sum(1 for b in all_approved if b.student_dept != b.equipment_ref.department_name)
    cross_share_pct = round((cross_dept_count / total_approved_bookings * 100), 1) if total_approved_bookings > 0 else 0.0

    return render_template(
        'index.html',
        equipments=equipments,
        departments=departments,
        categories=categories,
        search_query=search_query,
        selected_dept=selected_dept,
        selected_cat=selected_cat,
        selected_status=selected_status,
        total_equipment=total_equipment,
        available_equipment=available_equipment,
        total_approved_bookings=total_approved_bookings,
        cross_share_pct=cross_share_pct
    )


@app.route('/equipment/<int:equipment_id>')
def equipment_detail(equipment_id):
    """Detailed view for a specific equipment piece with live availability schedule."""
    equipment = Equipment.query.get_or_404(equipment_id)
    
    # Bookings for the next 7 days
    today = date.today()
    week_end = today + timedelta(days=7)
    upcoming_bookings = BookingRequest.query.filter(
        BookingRequest.equipment_id == equipment.id,
        BookingRequest.booking_date >= today,
        BookingRequest.booking_date <= week_end,
        BookingRequest.status.in_(['Approved', 'Pending'])
    ).order_by(BookingRequest.booking_date, BookingRequest.start_time).all()

    # Equivalent equipment in same category
    alternative_equipment = Equipment.query.filter(
        Equipment.category == equipment.category,
        Equipment.id != equipment.id
    ).limit(3).all()

    return render_template(
        'equipment_detail.html',
        equipment=equipment,
        upcoming_bookings=upcoming_bookings,
        alternative_equipment=alternative_equipment,
        today=today
    )


# ==========================================
# Intelligent Booking Workflow
# ==========================================

@app.route('/book/<int:equipment_id>', methods=['GET', 'POST'])
@login_required
def book_equipment(equipment_id):
    """Project-based intelligent booking request creation with strict backend validation."""
    equipment = Equipment.query.get_or_404(equipment_id)
    departments = Department.query.all()
    current_u = get_current_user()

    if request.method == 'POST':
        student_name = request.form.get('student_name', '').strip()
        student_id = request.form.get('student_id', '').strip()
        student_email = request.form.get('student_email', '').strip()
        student_dept = request.form.get('student_dept', '').strip()
        project_title = request.form.get('project_title', '').strip()
        project_category = request.form.get('project_category', 'Capstone / Final Year Thesis')
        deadline_str = request.form.get('project_deadline', '')
        booking_date_str = request.form.get('booking_date', '')
        start_time = request.form.get('start_time', '09:00').strip()
        duration_raw = request.form.get('duration_hours', '3')
        purpose = request.form.get('purpose', '').strip()

        # 1. Server-side Input Validation & Length Limits
        if not student_name or not student_id or not student_email or not student_dept or not project_title or not purpose:
            flash("All project details and requester fields are mandatory.", "error")
            return redirect(url_for('book_equipment', equipment_id=equipment.id))

        if len(project_title) > 200 or len(purpose) > 2000:
            flash("Project title must be under 200 characters and purpose under 2000 characters.", "error")
            return redirect(url_for('book_equipment', equipment_id=equipment.id))

        # 2. Integer validation for duration
        try:
            duration_hours = int(duration_raw)
        except (ValueError, TypeError):
            flash("Duration must be a valid positive number of hours.", "error")
            return redirect(url_for('book_equipment', equipment_id=equipment.id))

        if duration_hours <= 0:
            flash("Booking duration must be at least 1 hour.", "error")
            return redirect(url_for('book_equipment', equipment_id=equipment.id))

        if duration_hours > equipment.max_slot_hours:
            flash(f"Requested duration ({duration_hours}h) exceeds the maximum allowable slot ({equipment.max_slot_hours}h) for {equipment.name}.", "error")
            return redirect(url_for('book_equipment', equipment_id=equipment.id))

        # 3. Date parsing & Chronological boundary checks
        today = date.today()
        try:
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
            project_deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except Exception:
            flash("Invalid date format provided. Please select valid calendar dates.", "error")
            return redirect(url_for('book_equipment', equipment_id=equipment.id))

        if booking_date < today:
            flash("Cannot book equipment for past dates. Please pick today or a future date.", "error")
            return redirect(url_for('book_equipment', equipment_id=equipment.id))

        if project_deadline < today:
            flash("Project submission deadline cannot be in the past.", "error")
            return redirect(url_for('book_equipment', equipment_id=equipment.id))

        if booking_date > project_deadline:
            flash("Booking date cannot be scheduled after the project deadline has already passed.", "error")
            return redirect(url_for('book_equipment', equipment_id=equipment.id))

        # 4. Calculate End Time accurately (No silent truncation)
        start_min = time_to_minutes(start_time)
        end_min = start_min + duration_hours * 60
        end_time = minutes_to_time(end_min)

        # 5. Operating hours validation (08:00 - 20:00)
        valid_hours, hours_reason = validate_operating_hours(start_time, end_time)
        if not valid_hours:
            flash(f"Operating hours violation: {hours_reason}", "error")
            return redirect(url_for('book_equipment', equipment_id=equipment.id))

        # 6. Priority & Fairness Scoring
        score, tier, breakdown = calculate_priority_score(
            project_deadline=project_deadline,
            project_category=project_category,
            student_dept=student_dept,
            equipment_dept=equipment.department_name,
            purpose=purpose,
            equipment_specs=equipment.specs
        )

        # 7. Preliminary model construction
        new_request = BookingRequest(
            equipment_id=equipment.id,
            user_id=current_u.id,
            student_name=student_name,
            student_id=student_id,
            student_email=student_email,
            student_dept=student_dept,
            project_title=project_title,
            project_category=project_category,
            project_deadline=project_deadline,
            purpose=purpose,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration_hours,
            status='Pending',
            priority_score=score,
            priority_tier=tier,
            priority_breakdown=breakdown
        )

        # 8. Evaluate all conflicts (Hard collisions vs Competing pending)
        all_same_cat = Equipment.query.filter_by(category=equipment.category).all()
        has_conflict, conf_id, ai_rec, alt_slot, alt_equip, alt_dict = resolve_conflicts_and_recommend(
            new_req=new_request,
            equipment=equipment,
            all_equipment_in_category=all_same_cat
        )

        new_request.conflict_detected = has_conflict
        new_request.was_conflict = has_conflict
        new_request.conflicting_booking_id = conf_id
        new_request.ai_recommendation = ai_rec
        new_request.ai_alternative_slot = alt_slot
        new_request.ai_alternative_equipment = alt_equip

        # Save structured alternative details for 1-click execution
        if alt_dict:
            new_request.ai_alt_date = alt_dict['alt_date']
            new_request.ai_alt_start_time = alt_dict['alt_start_time']
            new_request.ai_alt_end_time = alt_dict['alt_end_time']
            new_request.ai_alt_duration = alt_dict['alt_duration']
            new_request.ai_alt_equipment_id = alt_dict['alt_equipment_id']

        db.session.add(new_request)
        db.session.commit()

        if has_conflict:
            flash("Booking request registered! A scheduling collision was identified; GenAI calculated priority rankings and generated feasible alternatives for faculty review.", "warning")
        else:
            flash(f"Booking submitted successfully! Evaluated with priority score of {score}/100 ({tier}).", "success")

        return redirect(url_for('view_requests'))

    default_booking_date = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    default_deadline = (date.today() + timedelta(days=14)).strftime('%Y-%m-%d')

    return render_template(
        'book.html',
        equipment=equipment,
        departments=departments,
        current_u=current_u,
        default_booking_date=default_booking_date,
        default_deadline=default_deadline
    )


# ==========================================
# Student Request Tracker
# ==========================================

@app.route('/requests')
@login_required
def view_requests():
    """Students track their own requests; Faculty & Admin view department-wide requests."""
    status_filter = request.args.get('status', '').strip()
    current_u = get_current_user()

    # RBAC Privacy: Students only see their own requests
    if current_u.is_student():
        query = BookingRequest.query.filter_by(user_id=current_u.id)
    elif current_u.is_faculty() and not current_u.is_admin():
        # Faculty sees requests for their assigned equipment
        assigned_ids = [e.id for e in current_u.assigned_equipment_list]
        query = BookingRequest.query.filter(BookingRequest.equipment_id.in_(assigned_ids)) if assigned_ids else BookingRequest.query.filter_by(id=-1)
    else:
        # Admin sees all requests
        query = BookingRequest.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    bookings = query.order_by(BookingRequest.created_at.desc()).all()
    return render_template('requests.html', bookings=bookings, status_filter=status_filter)


# ==========================================
# Faculty & Admin Portal
# ==========================================

@app.route('/admin')
@role_required('faculty', 'admin')
def admin_portal():
    """Faculty & Administrator Console for review, conflict resolution, and lab management."""
    status_filter = request.args.get('status', 'Pending').strip()
    current_u = get_current_user()

    # Role-based query filtering
    if current_u.is_admin():
        base_query = BookingRequest.query
        conflicts_query = BookingRequest.query.filter_by(status='Pending', conflict_detected=True)
        departments = Department.query.all()
    else:
        # Faculty member: only show equipment assigned to this faculty member
        assigned_ids = [e.id for e in current_u.assigned_equipment_list]
        if not assigned_ids:
            base_query = BookingRequest.query.filter_by(id=-1)
            conflicts_query = BookingRequest.query.filter_by(id=-1)
        else:
            base_query = BookingRequest.query.filter(BookingRequest.equipment_id.in_(assigned_ids))
            conflicts_query = BookingRequest.query.filter(
                BookingRequest.status == 'Pending',
                BookingRequest.conflict_detected == True,
                BookingRequest.equipment_id.in_(assigned_ids)
            )
        departments = Department.query.filter_by(name=current_u.department).all()

    if status_filter == 'All':
        bookings = base_query.order_by(BookingRequest.created_at.desc()).all()
    else:
        bookings = base_query.filter_by(status=status_filter).order_by(BookingRequest.priority_score.desc()).all()

    conflicts = conflicts_query.all()

    return render_template(
        'admin.html',
        bookings=bookings,
        conflicts=conflicts,
        status_filter=status_filter,
        departments=departments
    )


@app.route('/admin/approve/<int:booking_id>', methods=['POST'])
@role_required('faculty', 'admin')
def approve_booking(booking_id):
    """
    CRITICAL APPROVAL HANDLER:
    1. Enforces faculty authorization (assigned equipment only).
    2. Validates state machine (prevent double approval / counter inflation).
    3. RECHECKS AVAILABILITY: Prevents approving overlapping reservations!
    """
    current_u = get_current_user()
    b = BookingRequest.query.get_or_404(booking_id)

    # 1. Authorization check
    if not current_u.is_admin() and b.equipment_ref.assigned_faculty_id != current_u.id:
        flash("Unauthorized: You can only approve requests for your assigned equipment.", "error")
        abort(403)

    # 2. State machine check
    if b.status == 'Approved':
        flash(f"Request #{b.id} is already approved. Cannot approve multiple times.", "info")
        return redirect(url_for('admin_portal'))

    # 3. RECHECK AVAILABILITY AGAINST ALL APPROVED RESERVATIONS
    approved_conflicts, _ = check_conflicts(
        target_date=b.booking_date,
        start_time=b.start_time,
        end_time=b.end_time,
        equipment_id=b.equipment_id,
        exclude_booking_id=b.id
    )

    if approved_conflicts:
        colliding = approved_conflicts[0]
        flash(
            f"❌ Double-Booking Prevented! Cannot approve Request #{b.id} because the slot directly overlaps with "
            f"already Approved Reservation #{colliding.id} ({colliding.student_name}, {colliding.start_time} - {colliding.end_time}). "
            f"Please apply an alternative slot or reject.",
            "error"
        )
        return redirect(url_for('admin_portal'))

    # 4. Safe State Transition
    b.status = 'Approved'
    b.conflict_detected = False
    b.faculty_comments = request.form.get('comments', '').strip() or f"Approved by {current_u.full_name}."
    
    # Increment counter strictly once upon transition
    b.equipment_ref.total_bookings += 1

    db.session.commit()
    flash(f"Request #{b.id} for {b.student_name} approved successfully!", "success")
    return redirect(url_for('admin_portal'))


@app.route('/admin/reject/<int:booking_id>', methods=['POST'])
@role_required('faculty', 'admin')
def reject_booking(booking_id):
    """Faculty rejects booking with an audited explanation."""
    current_u = get_current_user()
    b = BookingRequest.query.get_or_404(booking_id)

    if not current_u.is_admin() and b.equipment_ref.assigned_faculty_id != current_u.id:
        flash("Unauthorized: You can only reject requests for your assigned equipment.", "error")
        abort(403)

    if b.status == 'Rejected':
        flash(f"Request #{b.id} is already marked as rejected.", "info")
        return redirect(url_for('admin_portal'))

    reason = request.form.get('comments', '').strip() or "Slot could not be allocated due to scheduling constraints."
    b.status = 'Rejected'
    b.faculty_comments = f"Rejected by {current_u.full_name}: {reason}"
    db.session.commit()

    flash(f"Request #{b.id} for {b.student_name} marked as rejected.", "info")
    return redirect(url_for('admin_portal'))


@app.route('/admin/apply-ai-alternate/<int:booking_id>', methods=['POST'])
@role_required('faculty', 'admin')
def apply_ai_alternate(booking_id):
    """
    CORRECT ALTERNATIVE BOOKING RESOLUTION:
    1. Validates the recommended alternate date, time, and target equipment.
    2. Rechecks that the alternative slot has zero conflicts with approved bookings.
    3. Validates operating hours & max duration limits.
    4. ACTUALLY UPDATES booking_date, start_time, end_time, duration, and equipment_id!
    5. Only then marks Approved with faculty explanation.
    """
    current_u = get_current_user()
    b = BookingRequest.query.get_or_404(booking_id)

    if not current_u.is_admin() and b.equipment_ref.assigned_faculty_id != current_u.id:
        flash("Unauthorized: You can only manage requests for your assigned equipment.", "error")
        abort(403)

    if b.status == 'Approved':
        flash(f"Request #{b.id} is already approved.", "info")
        return redirect(url_for('admin_portal'))

    # If structured alternate values are missing, compute them dynamically
    alt_date = b.ai_alt_date
    alt_start = b.ai_alt_start_time
    alt_end = b.ai_alt_end_time
    alt_duration = b.ai_alt_duration or b.duration_hours
    alt_equip_id = b.ai_alt_equipment_id or b.equipment_id

    if not (alt_date and alt_start and alt_end):
        # Dynamically compute alternative
        target_eq = Equipment.query.get(alt_equip_id)
        all_same_cat = Equipment.query.filter_by(category=target_eq.category).all()
        alt_dict = find_feasible_alternative(target_eq, b.booking_date, b.duration_hours, all_same_cat)
        
        if not alt_dict:
            flash("Could not find a conflict-free alternative slot to apply. Please manually reschedule or reject.", "error")
            return redirect(url_for('admin_portal'))
            
        alt_date = alt_dict['alt_date']
        alt_start = alt_dict['alt_start_time']
        alt_end = alt_dict['alt_end_time']
        alt_duration = alt_dict['alt_duration']
        alt_equip_id = alt_dict['alt_equipment_id']

    target_eq = Equipment.query.get_or_404(alt_equip_id)

    # 1. Operating hours check
    valid_hours, reason = validate_operating_hours(alt_start, alt_end)
    if not valid_hours:
        flash(f"Alternative slot invalid: {reason}", "error")
        return redirect(url_for('admin_portal'))

    # 2. Check collisions against Approved bookings on target equipment
    approved_conflicts, _ = check_conflicts(
        target_date=alt_date,
        start_time=alt_start,
        end_time=alt_end,
        equipment_id=target_eq.id,
        exclude_booking_id=b.id
    )

    if approved_conflicts:
        flash("The proposed alternative slot has since been taken by another approved reservation. Re-evaluating alternatives.", "error")
        return redirect(url_for('admin_portal'))

    # 3. ACTUAL UPDATE OF BOOKING DATA & TIME (Fixes existing bug!)
    orig_slot_info = f"{b.booking_date.strftime('%b %d')} ({b.start_time}-{b.end_time})"
    b.booking_date = alt_date
    b.start_time = alt_start
    b.end_time = alt_end
    b.duration_hours = alt_duration
    b.equipment_id = target_eq.id
    b.status = 'Approved'
    b.conflict_detected = False
    b.faculty_comments = f"Rescheduled from {orig_slot_info} to {alt_date.strftime('%b %d')} ({alt_start}-{alt_end}) on {target_eq.name} via GenAI Fair Alternative by {current_u.full_name}."
    
    # Increment target equipment counter
    target_eq.total_bookings += 1

    db.session.commit()
    flash(f"Successfully rescheduled and approved Request #{b.id} for {b.student_name} on {target_eq.name} at {alt_date.strftime('%b %d')} ({alt_start} - {alt_end})!", "success")
    return redirect(url_for('admin_portal'))


# ==========================================
# Administrative Management (Users & Equipment)
# ==========================================

@app.route('/admin/manage-equipment')
@role_required('admin')
def admin_manage_equipment():
    """Admin-only portal to view and reassign faculty to laboratory equipment."""
    all_equipment = Equipment.query.order_by(Equipment.department_name).all()
    all_faculty = User.query.filter(User.role.in_(['faculty', 'admin'])).all()
    return render_template('admin_equipment.html', equipments=all_equipment, faculty_list=all_faculty)


@app.route('/admin/assign-faculty/<int:equipment_id>', methods=['POST'])
@role_required('admin')
def admin_assign_faculty(equipment_id):
    """Admin reassigns laboratory equipment to a faculty member."""
    eq = Equipment.query.get_or_404(equipment_id)
    faculty_user_id = request.form.get('faculty_id')

    if faculty_user_id:
        fac_user = User.query.get_or_404(int(faculty_user_id))
        eq.assigned_faculty_id = fac_user.id
        eq.faculty_in_charge = fac_user.full_name
        eq.contact_email = fac_user.email
        db.session.commit()
        flash(f"{eq.name} successfully assigned to {fac_user.full_name}.", "success")
    return redirect(url_for('admin_manage_equipment'))


@app.route('/admin/manage-users')
@role_required('admin')
def admin_manage_users():
    """Admin-only portal to view all users and adjust roles."""
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=all_users)


@app.route('/admin/update-user-role/<int:user_id>', methods=['POST'])
@role_required('admin')
def admin_update_user_role(user_id):
    """Admin updates role of a user."""
    u = User.query.get_or_404(user_id)
    new_role = request.form.get('role', 'student')
    if new_role in ['student', 'faculty', 'admin']:
        u.role = new_role
        db.session.commit()
        flash(f"User {u.username} role updated to {new_role.title()}.", "success")
    return redirect(url_for('admin_manage_users'))


# ==========================================
# Analytics Dashboard (Pure Database Calculations)
# ==========================================

@app.route('/analytics')
def analytics():
    """Institutional Resource Intelligence & Sharing Analytics computed purely from database."""
    all_equipment = Equipment.query.all()
    all_bookings = BookingRequest.query.all()
    approved_bookings = [b for b in all_bookings if b.status == 'Approved']
    total_approved = len(approved_bookings)

    # Cross-department sharing ratio (genuine formula)
    cross_dept_count = sum(1 for b in approved_bookings if b.student_dept.strip().lower() != b.equipment_ref.department_name.strip().lower())
    cross_dept_pct = round((cross_dept_count / total_approved * 100), 1) if total_approved > 0 else 0.0

    # Department-wise booking count
    dept_stats = {d.name: 0 for d in Department.query.all()}
    for b in approved_bookings:
        dname = b.equipment_ref.department_name
        dept_stats[dname] = dept_stats.get(dname, 0) + 1

    # Top utilized equipment
    top_equipment = sorted(all_equipment, key=lambda x: x.total_bookings, reverse=True)[:5]

    # Category breakdown
    cat_stats = {}
    for eq in all_equipment:
        cat_stats[eq.category] = cat_stats.get(eq.category, 0) + eq.total_bookings

    # Accurate conflict tracking
    total_conflicts = len([b for b in all_bookings if b.conflict_detected or b.was_conflict])
    resolved_conflicts = len([b for b in all_bookings if b.was_conflict and b.status == 'Approved'])

    return render_template(
        'analytics.html',
        total_equipment=len(all_equipment),
        total_bookings=len(all_bookings),
        total_approved=total_approved,
        cross_dept_pct=cross_dept_pct,
        dept_stats=dept_stats,
        top_equipment=top_equipment,
        cat_stats=cat_stats,
        total_conflicts=total_conflicts,
        resolved_conflicts=resolved_conflicts
    )


# ==========================================
# GenAI Advisor Endpoints
# ==========================================

@app.route('/ai-advisor', methods=['GET', 'POST'])
def ai_advisor():
    """Natural Language Lab Equipment & Workstation Recommendation View."""
    query = request.args.get('q', '').strip()
    if request.method == 'POST':
        query = request.form.get('query', '').strip()

    recommendations = []
    if query:
        all_equipment = Equipment.query.all()
        recommendations = smart_equipment_advisor(query, all_equipment)

    is_gemini_active = bool(os.environ.get('GEMINI_API_KEY'))

    return render_template(
        'ai_advisor.html',
        query=query,
        recommendations=recommendations,
        is_gemini_active=is_gemini_active
    )


@app.route('/api/chat-advisor', methods=['POST'])
def api_chat_advisor():
    """AJAX endpoint for the global floating AI Assistant with rate limiting and length bounds."""
    # Rate limiting per IP: Max 20 requests per minute
    client_ip = request.remote_addr or 'unknown'
    now = time.time()
    recent_requests = [t for t in _ai_rate_limits.get(client_ip, []) if now - t < 60]
    
    if len(recent_requests) >= 20:
        return jsonify({'error': 'Rate limit exceeded. Please wait a minute before sending more queries.'}), 429
        
    recent_requests.append(now)
    _ai_rate_limits[client_ip] = recent_requests

    data = request.get_json() or {}
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    if len(message) > 500:
        return jsonify({'error': 'Message exceeds 500 characters limit.'}), 400

    all_equipment = Equipment.query.all()
    results = smart_equipment_advisor(message, all_equipment)

    formatted_results = []
    for r in results:
        eq = r['equipment']
        formatted_results.append({
            'id': eq.id,
            'name': eq.name,
            'code': eq.code,
            'category': eq.category,
            'lab': eq.lab_name,
            'location': eq.location,
            'status': eq.status,
            'confidence': r['confidence'],
            'rationale': r['rationale'],
            'book_url': url_for('book_equipment', equipment_id=eq.id)
        })

    is_gemini = bool(os.environ.get('GEMINI_API_KEY'))
    engine_label = "Google Gemini AI" if is_gemini else "LabLink Heuristic Engine"

    return jsonify({
        'reply': f"[{engine_label}] Analyzed campus laboratory facilities and identified {len(formatted_results)} matched resources:",
        'recommendations': formatted_results
    })


# ==========================================
# Custom Error Handlers
# ==========================================

@app.errorhandler(400)
def bad_request(e):
    return render_template('error.html', code=400, title="Bad Request", message="The request could not be processed due to invalid syntax or parameters."), 400

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, title="Access Forbidden", message="You do not have permissions to access this administrative resource."), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, title="Page Not Found", message="The requested laboratory page or resource does not exist."), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('error.html', code=500, title="Internal Server Error", message="An unexpected error occurred. The laboratory operations team has been notified."), 500


if __name__ == '__main__':
    # Production security: debug mode off by default unless explicitly specified in FLASK_DEBUG
    is_debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1']
    app.run(host='127.0.0.1', port=5000, debug=is_debug)
