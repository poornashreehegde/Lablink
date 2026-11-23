import sqlite3
from datetime import date, timedelta
from models import db, Department, Equipment, BookingRequest, User
from ai_engine import calculate_priority_score, resolve_conflicts_and_recommend

def run_migrations():
    """Ensures database schema is updated non-destructively for existing SQLite database."""
    # Ensure tables exist
    db.create_all()

    # Check and add missing columns dynamically
    try:
        engine = db.engine
        with engine.connect() as conn:
            # 1. Equipment table columns
            equip_cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(equipment);").fetchall()]
            if 'assigned_faculty_id' not in equip_cols:
                conn.exec_driver_sql("ALTER TABLE equipment ADD COLUMN assigned_faculty_id INTEGER REFERENCES users(id);")

            # 2. BookingRequest table columns
            req_cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(booking_requests);").fetchall()]
            if 'user_id' not in req_cols:
                conn.exec_driver_sql("ALTER TABLE booking_requests ADD COLUMN user_id INTEGER REFERENCES users(id);")
            if 'was_conflict' not in req_cols:
                conn.exec_driver_sql("ALTER TABLE booking_requests ADD COLUMN was_conflict BOOLEAN DEFAULT 0;")
            if 'ai_alt_date' not in req_cols:
                conn.exec_driver_sql("ALTER TABLE booking_requests ADD COLUMN ai_alt_date DATE;")
            if 'ai_alt_start_time' not in req_cols:
                conn.exec_driver_sql("ALTER TABLE booking_requests ADD COLUMN ai_alt_start_time VARCHAR(10);")
            if 'ai_alt_end_time' not in req_cols:
                conn.exec_driver_sql("ALTER TABLE booking_requests ADD COLUMN ai_alt_end_time VARCHAR(10);")
            if 'ai_alt_duration' not in req_cols:
                conn.exec_driver_sql("ALTER TABLE booking_requests ADD COLUMN ai_alt_duration INTEGER;")
            if 'ai_alt_equipment_id' not in req_cols:
                conn.exec_driver_sql("ALTER TABLE booking_requests ADD COLUMN ai_alt_equipment_id INTEGER REFERENCES equipment(id);")
            conn.commit()
    except Exception as e:
        print(f"Migration note/warning: {e}")


def seed_database():
    """Populates the database with realistic campus labs, users, equipment, and sample requests."""
    # 1. Run migrations first
    run_migrations()

    # 2. Seed Default Administrative & Faculty Users if none exist
    admin_user = User.query.filter_by(username="admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            email="admin@campus.edu",
            full_name="System Administrator",
            role="admin",
            department="Campus Research Administration"
        )
        admin_user.set_password("AdminPassword2026!")
        db.session.add(admin_user)

    # Predefined Faculty Members
    faculty_profiles = [
        {"username": "arvind.cse", "email": "arvind.cse@campus.edu", "full_name": "Dr. Arvind Narayanan", "dept": "Computer Science & AI"},
        {"username": "meera.k", "email": "meera.k@campus.edu", "full_name": "Prof. Meera Kulkarni", "dept": "Computer Science & AI"},
        {"username": "s.radha", "email": "s.radha@campus.edu", "full_name": "Dr. S. Radhakrishnan", "dept": "Electronics & Communication"},
        {"username": "v.sethi", "email": "v.sethi@campus.edu", "full_name": "Prof. Vikram Sethi", "dept": "Electronics & Communication"},
        {"username": "anita.rf", "email": "anita.rf@campus.edu", "full_name": "Dr. Anita Desai", "dept": "Electronics & Communication"},
        {"username": "ramesh.mech", "email": "ramesh.mech@campus.edu", "full_name": "Dr. Ramesh Verma", "dept": "Mechanical & Robotics"},
        {"username": "hr.joshi", "email": "hr.joshi@campus.edu", "full_name": "Prof. H. R. Joshi", "dept": "Mechanical & Robotics"},
        {"username": "k.swami", "email": "k.swami@campus.edu", "full_name": "Dr. K. Swaminathan", "dept": "Mechanical & Robotics"},
        {"username": "sunita.patel", "email": "sunita.patel@campus.edu", "full_name": "Dr. Sunita Patel", "dept": "Biotechnology & Nanotechnology"},
        {"username": "r.hegde", "email": "r.hegde@campus.edu", "full_name": "Prof. Rajesh Hegde", "dept": "Biotechnology & Nanotechnology"},
        {"username": "bsengupta", "email": "bsengupta@campus.edu", "full_name": "Dr. B. Sengupta", "dept": "Physics & Materials Science"},
        {"username": "t.mansoor", "email": "t.mansoor@campus.edu", "full_name": "Prof. Tariq Mansoor", "dept": "Physics & Materials Science"},
    ]

    for fp in faculty_profiles:
        if not User.query.filter_by(username=fp['username']).first():
            u = User(
                username=fp['username'],
                email=fp['email'],
                full_name=fp['full_name'],
                role="faculty",
                department=fp['dept']
            )
            u.set_password("FacultyPassword2026!")
            db.session.add(u)

    # Predefined Demo Students
    student_profiles = [
        {"username": "aarav.s", "email": "aarav.s@campus.edu", "full_name": "Aarav Sharma", "dept": "Electronics & Communication", "sid": "2022-ECE-042"},
        {"username": "priya.r", "email": "priya.r@campus.edu", "full_name": "Priya Ramachandran", "dept": "Computer Science & AI", "sid": "2023-CS-118"},
        {"username": "rohan.v", "email": "rohan.v@campus.edu", "full_name": "Rohan Verma", "dept": "Electronics & Communication", "sid": "2022-ECE-089"},
        {"username": "kavya.n", "email": "kavya.n@campus.edu", "full_name": "Kavya Nair", "dept": "Biotechnology & Nanotechnology", "sid": "2021-BIO-014"},
    ]

    for sp in student_profiles:
        if not User.query.filter_by(username=sp['username']).first():
            s = User(
                username=sp['username'],
                email=sp['email'],
                full_name=sp['full_name'],
                role="student",
                department=sp['dept'],
                student_id=sp['sid']
            )
            s.set_password("StudentPassword2026!")
            db.session.add(s)

    db.session.commit()

    # 3. Seed Departments if missing
    if not Department.query.first():
        depts = [
            Department(name="Computer Science & AI", code="CSE", building="Alan Turing Block, Level 3", badge_color="blue"),
            Department(name="Electronics & Communication", code="ECE", building="J.C. Bose Signal Tower, Level 2", badge_color="emerald"),
            Department(name="Mechanical & Robotics", code="MECH", building="Nikola Tesla Engineering Workshop", badge_color="amber"),
            Department(name="Biotechnology & Nanotechnology", code="BIOTECH", building="Rosalind Franklin Life Sciences Wing", badge_color="purple"),
            Department(name="Physics & Materials Science", code="PHY", building="C.V. Raman Science Complex", badge_color="cyan")
        ]
        db.session.add_all(depts)
        db.session.commit()

    d_cse = Department.query.filter_by(code="CSE").first()
    d_ece = Department.query.filter_by(code="ECE").first()
    d_mech = Department.query.filter_by(code="MECH").first()
    d_bio = Department.query.filter_by(code="BIOTECH").first()
    d_phy = Department.query.filter_by(code="PHY").first()

    # 4. Seed Equipment if missing
    if not Equipment.query.first():
        equipments = [
            Equipment(
                code="EQ-AI-01",
                name="NVIDIA DGX A100 Workstation",
                category="AI & GPU Workstations",
                department_id=d_cse.id,
                department_name=d_cse.name,
                lab_name="Deep Learning & Autonomous Systems Lab",
                location="Turing Block, Room 304",
                faculty_in_charge="Dr. Arvind Narayanan",
                contact_email="arvind.cse@campus.edu",
                specs="4x NVIDIA A100 (320GB Tensor Core VRAM), Dual AMD EPYC 7742 (128 Cores), 1TB DDR4 RAM, NVMe 15TB RAID",
                status="Available",
                icon="server",
                safety_prereqs="Linux Terminal Certification, CUDA environment clearance",
                max_slot_hours=4,
                total_bookings=18
            ),
            Equipment(
                code="EQ-AI-02",
                name="NVIDIA Jetson AGX Orin Dev Station",
                category="AI & GPU Workstations",
                department_id=d_cse.id,
                department_name=d_cse.name,
                lab_name="Edge Robotics & Embedded AI Lab",
                location="Turing Block, Room 310",
                faculty_in_charge="Prof. Meera Kulkarni",
                contact_email="meera.k@campus.edu",
                specs="275 TOPS AI Compute, 64GB 256-bit LPDDR5, JetPack 6.0, CSI Dual Stereo Cameras, ROS2 Humble",
                status="Available",
                icon="cpu",
                safety_prereqs="ESD wrist strap required, Jetson flashing guide completed",
                max_slot_hours=3,
                total_bookings=12
            ),
            Equipment(
                code="EQ-ECE-01",
                name="Keysight Infiniium 4-Channel DSO",
                category="Signal & RF Measurement",
                department_id=d_ece.id,
                department_name=d_ece.name,
                lab_name="Advanced High-Frequency Microwave Lab",
                location="Bose Tower, Room 202",
                faculty_in_charge="Dr. S. Radhakrishnan",
                contact_email="s.radha@campus.edu",
                specs="4 GHz Bandwidth, 20 GSa/s Sample Rate, 10-bit ADC, Protocol Triggering (I2C/SPI/CAN/USB 3.0)",
                status="Available",
                icon="activity",
                safety_prereqs="Probe calibration test check, 50 Ohm impedance matching adherence",
                max_slot_hours=3,
                total_bookings=24
            ),
            Equipment(
                code="EQ-ECE-02",
                name="Xilinx Zynq UltraScale+ FPGA Workbench",
                category="Embedded & FPGA Kits",
                department_id=d_ece.id,
                department_name=d_ece.name,
                lab_name="VLSI Design & System-on-Chip Lab",
                location="Bose Tower, Room 208",
                faculty_in_charge="Prof. Vikram Sethi",
                contact_email="v.sethi@campus.edu",
                specs="Zynq UltraScale+ ZCU102, Quad ARM Cortex-A53, Vivado 2024.1 Enterprise License, FMC Expansion Headers",
                status="Available",
                icon="microchip",
                safety_prereqs="Vivado toolchain training, static-safe antistatic mat usage",
                max_slot_hours=4,
                total_bookings=15
            ),
            Equipment(
                code="EQ-ECE-03",
                name="Rohde & Schwarz Spectrum Analyzer",
                category="Signal & RF Measurement",
                department_id=d_ece.id,
                department_name=d_ece.name,
                lab_name="Wireless & Satellite Communications Lab",
                location="Bose Tower, Room 215",
                faculty_in_charge="Dr. Anita Desai",
                contact_email="anita.rf@campus.edu",
                specs="Frequency range 9 kHz to 6 GHz, DANL -165 dBm, Tracking Generator, EMI pre-compliance measurement filters",
                status="Available",
                icon="radio",
                safety_prereqs="RF maximum input power limit +30 dBm safety warning",
                max_slot_hours=3,
                total_bookings=9
            ),
            Equipment(
                code="EQ-MECH-01",
                name="Stratasys F170 Industrial 3D Printer",
                category="Rapid Prototyping & CAD",
                department_id=d_mech.id,
                department_name=d_mech.name,
                lab_name="Digital Additive Manufacturing Lab",
                location="Tesla Workshop, Room 101",
                faculty_in_charge="Dr. Ramesh Verma",
                contact_email="ramesh.mech@campus.edu",
                specs="Dual Extrusion, PLA/ABS/TPU 92A/Carbon Fiber, Build volume 254 x 254 x 254 mm, Soluble support QSR",
                status="Available",
                icon="printer",
                safety_prereqs="GrabCAD Print sliced file pre-check by lab assistant, thermal safety gloves",
                max_slot_hours=4,
                total_bookings=31
            ),
            Equipment(
                code="EQ-MECH-02",
                name="Universal 60W CO2 Laser Cutter & Engraver",
                category="Rapid Prototyping & CAD",
                department_id=d_mech.id,
                department_name=d_mech.name,
                lab_name="Mechatronics & Robotics Fabrication Shop",
                location="Tesla Workshop, Room 105",
                faculty_in_charge="Prof. H. R. Joshi",
                contact_email="hr.joshi@campus.edu",
                specs="Work area 610 x 305 mm, 60-watt CO2 laser, High-pressure air assist, Cuts acrylic up to 10mm and wood up to 8mm",
                status="Available",
                icon="scissors",
                safety_prereqs="Laser safety goggles OD6+, Exhaust blower validation check, No PVC materials rule",
                max_slot_hours=2,
                total_bookings=28
            ),
            Equipment(
                code="EQ-MECH-03",
                name="Instron 5960 Dual-Column Materials Tester",
                category="Mechanical & Structural Testing",
                department_id=d_mech.id,
                department_name=d_mech.name,
                lab_name="Mechanics of Materials & Fatigue Testing Lab",
                location="Tesla Workshop, Room 112",
                faculty_in_charge="Dr. K. Swaminathan",
                contact_email="k.swami@campus.edu",
                specs="50 kN Load Capacity, Bluehill Universal Software, Extensometer for tensile strain, 3-point flexure jig",
                status="Available",
                icon="gauge",
                safety_prereqs="Interlock safety shield must remain closed during test cycles",
                max_slot_hours=3,
                total_bookings=11
            ),
            Equipment(
                code="EQ-BIO-01",
                name="Shimadzu UV-2600i Spectrophotometer",
                category="Chemical & Biomolecular Analysis",
                department_id=d_bio.id,
                department_name=d_bio.name,
                lab_name="Bioprocess & Molecular Analytics Lab",
                location="Franklin Wing, Room 402",
                faculty_in_charge="Dr. Sunita Patel",
                contact_email="sunita.patel@campus.edu",
                specs="Double-beam optical system, Wavelength 185 to 900 nm, 0.1 nm resolution, Quartz micro-cuvette cells",
                status="Available",
                icon="flask-conical",
                safety_prereqs="Chemical hazard apron, disposable nitrile gloves, bio-waste disposal bag",
                max_slot_hours=3,
                total_bookings=19
            ),
            Equipment(
                code="EQ-BIO-02",
                name="Eppendorf 5430R Refrigerated Centrifuge",
                category="Chemical & Biomolecular Analysis",
                department_id=d_bio.id,
                department_name=d_bio.name,
                lab_name="Recombinant DNA & Genomics Lab",
                location="Franklin Wing, Room 408",
                faculty_in_charge="Prof. Rajesh Hegde",
                contact_email="r.hegde@campus.edu",
                specs="Max RCF 30,130 x g (17,500 rpm), Temperature range -11°C to +40°C, 48-place rotor for 1.5/2.0 mL tubes",
                status="Available",
                icon="disc",
                safety_prereqs="Rotor symmetrical balancing mandatory before spinning, Biosafety Level 1 certified",
                max_slot_hours=2,
                total_bookings=22
            ),
            Equipment(
                code="EQ-PHY-01",
                name="Olympus BX53 Fluorescence Microscope",
                category="Microscopy & Nanophotonics",
                department_id=d_phy.id,
                department_name=d_phy.name,
                lab_name="Advanced Nanomaterials & Optical Imaging Lab",
                location="Raman Complex, Room 102",
                faculty_in_charge="Dr. B. Sengupta",
                contact_email="bsengupta@campus.edu",
                specs="UIS2 optical system, DAPI/FITC/TRITC filter cubes, High-res scientific CMOS camera, 100x Oil immersion objective",
                status="Available",
                icon="scan",
                safety_prereqs="Darkroom protocol training, Mercury lamp cooldown timer compliance",
                max_slot_hours=3,
                total_bookings=14
            ),
            Equipment(
                code="EQ-PHY-02",
                name="Rigaku MiniFlex Benchtop XRD System",
                category="Microscopy & Nanophotonics",
                department_id=d_phy.id,
                department_name=d_phy.name,
                lab_name="X-Ray Crystallography & Solid State Lab",
                location="Raman Complex, Room 106",
                faculty_in_charge="Prof. Tariq Mansoor",
                contact_email="t.mansoor@campus.edu",
                specs="600W X-ray tube (Cu-K alpha), High-speed D/teX Ultra silicon strip detector, PDXL powder diffraction analysis",
                status="Available",
                icon="shield-alert",
                safety_prereqs="Radiation dosimeter badge clearance, Sample powder compaction certification",
                max_slot_hours=3,
                total_bookings=8
            )
        ]
        db.session.add_all(equipments)
        db.session.commit()

    # Link Faculty to Equipment by email
    for eq in Equipment.query.all():
        if not eq.assigned_faculty_id:
            fac = User.query.filter_by(email=eq.contact_email).first()
            if fac:
                eq.assigned_faculty_id = fac.id
    db.session.commit()

    # Link existing bookings to student accounts
    for b in BookingRequest.query.all():
        if not b.user_id:
            stud = User.query.filter_by(email=b.student_email).first()
            if stud:
                b.user_id = stud.id
        if b.conflict_detected:
            b.was_conflict = True
    db.session.commit()
