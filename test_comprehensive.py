import os
import sys
import unittest
from datetime import date, timedelta

# Ensure project path is in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

TEST_DB_PATH = os.path.join(BASE_DIR, 'instance', 'test_lablink.db')
os.environ['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{TEST_DB_PATH}"

from app import app, db
from models import User, Department, Equipment, BookingRequest

class LabLinkComprehensiveTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{TEST_DB_PATH}"
        app.config['SECRET_KEY'] = 'test-secret-key-12345'
        cls.app = app

    def setUp(self):
        self.client = self.app.test_client()

        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()

            # Seed Test Departments
            dept = Department(name="Computer Science & AI", code="CSE", building="Turing Block")
            dept_ece = Department(name="Electronics & Communication", code="ECE", building="Bose Tower")
            db.session.add_all([dept, dept_ece])
            db.session.commit()

            # Seed Users
            admin = User(username="admin", email="admin@campus.edu", full_name="Admin User", role="admin")
            admin.set_password("AdminPass123!")

            fac1 = User(username="fac1", email="fac1@campus.edu", full_name="Dr. Faculty One", role="faculty", department="Computer Science & AI")
            fac1.set_password("FacPass123!")

            fac2 = User(username="fac2", email="fac2@campus.edu", full_name="Dr. Faculty Two", role="faculty", department="Electronics & Communication")
            fac2.set_password("FacPass123!")

            stud1 = User(username="stud1", email="stud1@campus.edu", full_name="Student One", role="student", department="Computer Science & AI", student_id="ST-001")
            stud1.set_password("StudPass123!")

            stud2 = User(username="stud2", email="stud2@campus.edu", full_name="Student Two", role="student", department="Electronics & Communication", student_id="ST-002")
            stud2.set_password("StudPass123!")

            db.session.add_all([admin, fac1, fac2, stud1, stud2])
            db.session.commit()

            # Seed Equipment
            eq1 = Equipment(
                code="EQ-AI-01",
                name="NVIDIA A100 Station",
                category="AI & GPU Workstations",
                department_id=dept.id,
                department_name=dept.name,
                lab_name="Vision Lab",
                location="Room 304",
                faculty_in_charge="Dr. Faculty One",
                contact_email="fac1@campus.edu",
                assigned_faculty_id=fac1.id,
                specs="4x A100 GPUs 80GB, CUDA 12",
                status="Available",
                max_slot_hours=4
            )
            eq2 = Equipment(
                code="EQ-ECE-01",
                name="Keysight DSO",
                category="Signal & RF Measurement",
                department_id=dept_ece.id,
                department_name=dept_ece.name,
                lab_name="RF Lab",
                location="Room 102",
                faculty_in_charge="Dr. Faculty Two",
                contact_email="fac2@campus.edu",
                assigned_faculty_id=fac2.id,
                specs="4 GHz Oscilloscope 20 GSa/s",
                status="Available",
                max_slot_hours=3
            )
            db.session.add_all([eq1, eq2])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @classmethod
    def tearDownClass(cls):
        # Remove test database file
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    def login_helper(self, username, password):
        """Helper to log in a user and set up session."""
        return self.client.post('/login', data={'login_id': username, 'password': password}, follow_redirects=True)

    # ==========================================
    # 1. Registration & Password Hashing Tests
    # ==========================================
    def test_student_registration_and_password_hashing(self):
        """Verify student registration encrypts password and enforces student role."""
        res = self.client.post('/register', data={
            'username': 'newstudent',
            'email': 'new@campus.edu',
            'full_name': 'New Student',
            'department': 'Computer Science & AI',
            'student_id': 'ST-999',
            'password': 'SecurePassword2026!',
            'confirm_password': 'SecurePassword2026!'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            user = User.query.filter_by(username='newstudent').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.role, 'student')  # Enforced student role
            self.assertNotEqual(user.password_hash, 'SecurePassword2026!')  # Hashed
            self.assertTrue(user.check_password('SecurePassword2026!'))
            self.assertFalse(user.check_password('WrongPassword'))

    def test_registration_prevents_duplicate_identity(self):
        """Verify duplicate usernames are rejected."""
        res = self.client.post('/register', data={
            'username': 'stud1',  # Already exists
            'email': 'different@campus.edu',
            'full_name': 'Duplicate User',
            'department': 'Computer Science & AI',
            'student_id': 'ST-003',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        }, follow_redirects=True)
        self.assertIn(b"Username is already taken", res.data)

    # ==========================================
    # 2. Authentication & Role-Based Access Control
    # ==========================================
    def test_unauthenticated_access_restrictions(self):
        """Verify unauthenticated users cannot access admin or booking pages."""
        res_admin = self.client.get('/admin', follow_redirects=False)
        self.assertEqual(res_admin.status_code, 302)
        self.assertIn('/login', res_admin.headers['Location'])

        res_book = self.client.get('/book/1', follow_redirects=False)
        self.assertEqual(res_book.status_code, 302)
        self.assertIn('/login', res_book.headers['Location'])

    def test_student_cannot_access_admin_portal(self):
        """Verify students are blocked with 403 Forbidden when trying to access /admin."""
        self.login_helper('stud1', 'StudPass123!')
        res = self.client.get('/admin')
        self.assertEqual(res.status_code, 403)

    def test_faculty_can_access_admin_portal(self):
        """Verify faculty members can access the approvals portal."""
        self.login_helper('fac1', 'FacPass123!')
        res = self.client.get('/admin')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Approvals", res.data)

    # ==========================================
    # 3. Request Privacy & Scoping
    # ==========================================
    def test_student_sees_only_own_requests(self):
        """Verify students cannot view requests created by other students."""
        today = date.today()
        with self.app.app_context():
            u1 = User.query.filter_by(username='stud1').first()
            u2 = User.query.filter_by(username='stud2').first()
            
            b1 = BookingRequest(
                equipment_id=1, user_id=u1.id, student_name=u1.full_name, student_id=u1.student_id,
                student_email=u1.email, student_dept=u1.department, project_title="Project Alpha",
                project_category="Capstone", project_deadline=today + timedelta(days=5),
                purpose="Vision modeling", booking_date=today + timedelta(days=1),
                start_time="09:00", end_time="12:00", duration_hours=3, status="Pending"
            )
            b2 = BookingRequest(
                equipment_id=1, user_id=u2.id, student_name=u2.full_name, student_id=u2.student_id,
                student_email=u2.email, student_dept=u2.department, project_title="Project Beta",
                project_category="Capstone", project_deadline=today + timedelta(days=5),
                purpose="RF analysis", booking_date=today + timedelta(days=1),
                start_time="13:00", end_time="16:00", duration_hours=3, status="Pending"
            )
            db.session.add_all([b1, b2])
            db.session.commit()

        # Login as Student 1: Should see Project Alpha, but NOT Project Beta
        self.login_helper('stud1', 'StudPass123!')
        res = self.client.get('/requests')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Project Alpha", res.data)
        self.assertNotIn(b"Project Beta", res.data)

    # ==========================================
    # 4. Input Validation & Booking Bounds
    # ==========================================
    def test_booking_rejects_past_date(self):
        """Verify system rejects booking requests for past calendar dates."""
        self.login_helper('stud1', 'StudPass123!')
        past_date = (date.today() - timedelta(days=2)).strftime('%Y-%m-%d')
        deadline = (date.today() + timedelta(days=10)).strftime('%Y-%m-%d')
        
        res = self.client.post('/book/1', data={
            'student_name': 'Student One', 'student_id': 'ST-001', 'student_email': 'stud1@campus.edu',
            'student_dept': 'Computer Science & AI', 'project_title': 'Deep Learning',
            'project_category': 'Capstone / Final Year Thesis', 'project_deadline': deadline,
            'booking_date': past_date, 'start_time': '09:00', 'duration_hours': '2',
            'purpose': 'Testing past date rejection validation.'
        }, follow_redirects=True)
        self.assertIn(b"Cannot book equipment for past dates", res.data)

    def test_booking_rejects_exceeding_max_slot_duration(self):
        """Verify requested duration cannot exceed equipment max_slot_hours."""
        self.login_helper('stud1', 'StudPass123!')
        tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        deadline = (date.today() + timedelta(days=10)).strftime('%Y-%m-%d')
        
        # Equipment 1 has max_slot_hours = 4; requesting 8 hours
        res = self.client.post('/book/1', data={
            'student_name': 'Student One', 'student_id': 'ST-001', 'student_email': 'stud1@campus.edu',
            'student_dept': 'Computer Science & AI', 'project_title': 'Deep Learning',
            'project_category': 'Capstone / Final Year Thesis', 'project_deadline': deadline,
            'booking_date': tomorrow, 'start_time': '09:00', 'duration_hours': '8',
            'purpose': 'Testing duration boundary validation.'
        }, follow_redirects=True)
        self.assertIn(b"exceeds the maximum allowable slot", res.data)

    def test_booking_rejects_outside_operating_hours(self):
        """Verify bookings extending past lab closing time (20:00) are rejected."""
        self.login_helper('stud1', 'StudPass123!')
        tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        deadline = (date.today() + timedelta(days=10)).strftime('%Y-%m-%d')
        
        # 17:00 + 4 hours = 21:00 (Closes at 20:00)
        res = self.client.post('/book/1', data={
            'student_name': 'Student One', 'student_id': 'ST-001', 'student_email': 'stud1@campus.edu',
            'student_dept': 'Computer Science & AI', 'project_title': 'Late Night Lab',
            'project_category': 'Capstone / Final Year Thesis', 'project_deadline': deadline,
            'booking_date': tomorrow, 'start_time': '17:00', 'duration_hours': '4',
            'purpose': 'Testing operating hours validation.'
        }, follow_redirects=True)
        self.assertIn(b"Operating hours violation", res.data)

    # ==========================================
    # 5. Double-Booking Prevention & State Transitions
    # ==========================================
    def test_prevent_double_booking_on_approval(self):
        """CRITICAL: Verify faculty cannot approve a request that overlaps an already Approved reservation."""
        tomorrow = date.today() + timedelta(days=1)
        with self.app.app_context():
            u1 = User.query.filter_by(username='stud1').first()
            u2 = User.query.filter_by(username='stud2').first()
            
            # Booking 1 is already Approved: 09:00 - 12:00
            b1 = BookingRequest(
                equipment_id=1, user_id=u1.id, student_name=u1.full_name, student_id=u1.student_id,
                student_email=u1.email, student_dept=u1.department, project_title="Project Alpha",
                project_category="Capstone", project_deadline=tomorrow + timedelta(days=5),
                purpose="Vision modeling", booking_date=tomorrow,
                start_time="09:00", end_time="12:00", duration_hours=3, status="Approved"
            )
            # Booking 2 is Pending and overlaps: 10:00 - 13:00
            b2 = BookingRequest(
                equipment_id=1, user_id=u2.id, student_name=u2.full_name, student_id=u2.student_id,
                student_email=u2.email, student_dept=u2.department, project_title="Project Beta",
                project_category="Capstone", project_deadline=tomorrow + timedelta(days=5),
                purpose="Competing run", booking_date=tomorrow,
                start_time="10:00", end_time="13:00", duration_hours=3, status="Pending",
                conflict_detected=True
            )
            db.session.add_all([b1, b2])
            db.session.commit()
            b2_id = b2.id

        # Faculty 1 attempts to approve Booking 2
        self.login_helper('fac1', 'FacPass123!')
        res = self.client.post(f'/admin/approve/{b2_id}', follow_redirects=True)
        self.assertIn(b"Double-Booking Prevented", res.data)

        # Confirm in database that Booking 2 is STILL Pending (Not Approved!)
        with self.app.app_context():
            b2_check = BookingRequest.query.get(b2_id)
            self.assertEqual(b2_check.status, 'Pending')

    def test_prevent_duplicate_approval_counter_inflation(self):
        """Verify approving an already approved booking does not increment equipment counter."""
        tomorrow = date.today() + timedelta(days=1)
        with self.app.app_context():
            u1 = User.query.filter_by(username='stud1').first()
            b1 = BookingRequest(
                equipment_id=1, user_id=u1.id, student_name=u1.full_name, student_id=u1.student_id,
                student_email=u1.email, student_dept=u1.department, project_title="Project Alpha",
                project_category="Capstone", project_deadline=tomorrow + timedelta(days=5),
                purpose="Vision modeling", booking_date=tomorrow,
                start_time="14:00", end_time="16:00", duration_hours=2, status="Approved"
            )
            db.session.add(b1)
            db.session.commit()
            b1_id = b1.id
            eq = Equipment.query.get(1)
            initial_count = eq.total_bookings

        self.login_helper('fac1', 'FacPass123!')
        res = self.client.post(f'/admin/approve/{b1_id}', follow_redirects=True)
        self.assertIn(b"is already approved", res.data)

        with self.app.app_context():
            eq_check = Equipment.query.get(1)
            self.assertEqual(eq_check.total_bookings, initial_count)

    # ==========================================
    # 6. Alternative Booking Application
    # ==========================================
    def test_apply_ai_alternate_actually_updates_slot_and_equipment(self):
        """Verify apply_ai_alternate updates date, start_time, end_time and equipment_id before approving."""
        tomorrow = date.today() + timedelta(days=1)
        day_after = date.today() + timedelta(days=2)
        with self.app.app_context():
            u1 = User.query.filter_by(username='stud1').first()
            b = BookingRequest(
                equipment_id=1, user_id=u1.id, student_name=u1.full_name, student_id=u1.student_id,
                student_email=u1.email, student_dept=u1.department, project_title="Vision Run",
                project_category="Capstone", project_deadline=tomorrow + timedelta(days=5),
                purpose="Vision modeling", booking_date=tomorrow,
                start_time="09:00", end_time="13:00", duration_hours=4, status="Pending",
                conflict_detected=True,
                ai_alt_date=day_after,
                ai_alt_start_time="14:00",
                ai_alt_end_time="18:00",
                ai_alt_duration=4,
                ai_alt_equipment_id=1
            )
            db.session.add(b)
            db.session.commit()
            bid = b.id

        self.login_helper('fac1', 'FacPass123!')
        res = self.client.post(f'/admin/apply-ai-alternate/{bid}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            updated_b = BookingRequest.query.get(bid)
            self.assertEqual(updated_b.status, 'Approved')
            self.assertEqual(updated_b.booking_date, day_after)
            self.assertEqual(updated_b.start_time, "14:00")
            self.assertEqual(updated_b.end_time, "18:00")
            self.assertFalse(updated_b.conflict_detected)
            self.assertIn("Rescheduled from", updated_b.faculty_comments)

    # ==========================================
    # 7. AI Advisor & Fallback Behavior
    # ==========================================
    def test_ai_advisor_spec_match_and_gibberish_rejection(self):
        """Verify AI advisor accurately matches technical terms and does not fake confidence for gibberish."""
        # 1. Relevant technical query
        res_tech = self.client.post('/api/chat-advisor', json={'message': 'Need to train PyTorch neural network with CUDA GPU'})
        data_tech = res_tech.get_json()
        self.assertEqual(res_tech.status_code, 200)
        self.assertGreater(len(data_tech['recommendations']), 0)
        self.assertEqual(data_tech['recommendations'][0]['code'], 'EQ-AI-01')

        # 2. Random non-technical gibberish query
        res_gibberish = self.client.post('/api/chat-advisor', json={'message': 'asdfkjhqwertyuiop 999 xyz'})
        data_gibberish = res_gibberish.get_json()
        self.assertEqual(res_gibberish.status_code, 200)
        self.assertEqual(len(data_gibberish['recommendations']), 0)

    # ==========================================
    # 8. Unauthorized Faculty Action
    # ==========================================
    def test_faculty_cannot_approve_unassigned_equipment(self):
        """Verify Faculty 2 (ECE) cannot approve requests for Equipment 1 (CSE/AI)."""
        tomorrow = date.today() + timedelta(days=1)
        with self.app.app_context():
            u1 = User.query.filter_by(username='stud1').first()
            b = BookingRequest(
                equipment_id=1, user_id=u1.id, student_name=u1.full_name, student_id=u1.student_id,
                student_email=u1.email, student_dept=u1.department, project_title="Vision Test",
                project_category="Capstone", project_deadline=tomorrow + timedelta(days=5),
                purpose="Testing", booking_date=tomorrow,
                start_time="14:00", end_time="16:00", duration_hours=2, status="Pending"
            )
            db.session.add(b)
            db.session.commit()
            bid = b.id

        # Faculty 2 logs in and attempts to approve Equipment 1
        self.login_helper('fac2', 'FacPass123!')
        res = self.client.post(f'/admin/approve/{bid}')
        self.assertEqual(res.status_code, 403)


if __name__ == '__main__':
    unittest.main()
