from datetime import date, timedelta
from models import db, Department, Equipment, BookingRequest
from ai_engine import calculate_priority_score, resolve_conflicts_and_recommend

def seed_database():
    """Populates the database with realistic campus labs, equipment, and sample requests."""
    # Only seed if empty
    if Department.query.first():
        return

    # 1. Departments
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

    # 2. Specialised Equipment
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

    # 3. Seed Realistic Bookings with Simulated Conflict & GenAI Evaluation
    today = date.today()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    next_week = today + timedelta(days=7)

    eq_a100 = Equipment.query.filter_by(code="EQ-AI-01").first()
    eq_dso = Equipment.query.filter_by(code="EQ-ECE-01").first()
    eq_printer = Equipment.query.filter_by(code="EQ-MECH-01").first()

    # Request 1: Approved - Capstone on A100
    p1_score, p1_tier, p1_break = calculate_priority_score(
        project_deadline=tomorrow + timedelta(days=3),
        project_category="Capstone / Final Year Thesis",
        student_dept="Electronics & Communication",
        equipment_dept=eq_a100.department_name,
        purpose="Training vision-transformer on 250k multimodal satellite images for disaster detection. Interdisciplinary collaboration.",
        equipment_specs=eq_a100.specs
    )
    b1 = BookingRequest(
        equipment_id=eq_a100.id,
        student_name="Aarav Sharma",
        student_id="2022-ECE-042",
        student_email="aarav.s@campus.edu",
        student_dept="Electronics & Communication",
        project_title="DisasterNet: Multimodal Satellite Vision Transformer",
        project_category="Capstone / Final Year Thesis",
        project_deadline=tomorrow + timedelta(days=3),
        purpose="Training vision-transformer on 250k multimodal satellite images for disaster detection. Interdisciplinary collaboration.",
        booking_date=tomorrow,
        start_time="09:00",
        end_time="13:00",
        duration_hours=4,
        status="Approved",
        faculty_comments="Approved based on imminent thesis defense and verified PyTorch code checkpoints.",
        priority_score=p1_score,
        priority_tier=p1_tier,
        priority_breakdown=p1_break,
        conflict_detected=False,
        ai_recommendation="✅ Optimal Allocation: Zero slot collisions. Strong cross-department merit (+15 pts). Pre-approved."
    )

    # Request 2: Deliberate Conflict Demonstration on A100!
    # Student requests same date (tomorrow) at 10:00 - 13:00 (overlaps with b1)
    p2_score, p2_tier, p2_break = calculate_priority_score(
        project_deadline=tomorrow + timedelta(days=1), # Even more urgent! (Tomorrow + 1d)
        project_category="Faculty Sponsored Research",
        student_dept="Computer Science & AI",
        equipment_dept=eq_a100.department_name,
        purpose="Final fine-tuning benchmarking run for IEEE ICRA paper submission due in 48 hours. Requires 80GB VRAM multi-GPU memory.",
        equipment_specs=eq_a100.specs
    )
    b2 = BookingRequest(
        equipment_id=eq_a100.id,
        student_name="Priya Ramachandran",
        student_id="2023-CS-118",
        student_email="priya.r@campus.edu",
        student_dept="Computer Science & AI",
        project_title="SafeNav-Autonomous: Real-time Point Cloud Diffusion",
        project_category="Faculty Sponsored Research",
        project_deadline=tomorrow + timedelta(days=1),
        purpose="Final fine-tuning benchmarking run for IEEE ICRA paper submission due in 48 hours. Requires 80GB VRAM multi-GPU memory.",
        booking_date=tomorrow,
        start_time="10:00",
        end_time="14:00",
        duration_hours=4,
        status="Pending",
        priority_score=p2_score,
        priority_tier=p2_tier,
        priority_breakdown=p2_break,
        conflict_detected=True,
        conflicting_booking_id=1,
        ai_recommendation=(
            f"⚠️ Scheduling Conflict Detected with Request #1 (Aarav Sharma, 09:00-13:00). "
            f"GenAI Optimization Engine prioritizes Request #2 ({p2_score:.1f} vs {p1_score:.1f}) due to imminent 48h IEEE research deadline. "
            f"Fair Feasible Alternate for Aarav Sharma: Reschedule to tomorrow afternoon (14:00 - 18:00) with zero loss of compute time."
        ),
        ai_alternative_slot=f"{tomorrow.strftime('%b %d, %Y')} (14:00 - 18:00)",
        ai_alternative_equipment="NVIDIA Jetson AGX Orin Dev Station (EQ-AI-02)"
    )

    # Request 3: Pending DSO request
    p3_score, p3_tier, p3_break = calculate_priority_score(
        project_deadline=next_week,
        project_category="Competitive Hackathon / Conf Paper",
        student_dept="Electronics & Communication",
        equipment_dept=eq_dso.department_name,
        purpose="Debugging differential high-speed SPI bus signals on drone flight controller board for National Robotics League.",
        equipment_specs=eq_dso.specs
    )
    b3 = BookingRequest(
        equipment_id=eq_dso.id,
        student_name="Rohan Verma",
        student_id="2022-ECE-089",
        student_email="rohan.v@campus.edu",
        student_dept="Electronics & Communication",
        project_title="AeroSwarm: Quadcopter Telemetry Interconnect",
        project_category="Competitive Hackathon / Conf Paper",
        project_deadline=next_week,
        purpose="Debugging differential high-speed SPI bus signals on drone flight controller board for National Robotics League.",
        booking_date=day_after,
        start_time="14:00",
        end_time="17:00",
        duration_hours=3,
        status="Pending",
        priority_score=p3_score,
        priority_tier=p3_tier,
        priority_breakdown=p3_break,
        conflict_detected=False,
        ai_recommendation="✅ Optimal Allocation: Slot is completely unencumbered. High justification clarity. Recommended for approval."
    )

    # Request 4: Rapid prototyping 3D printer
    p4_score, p4_tier, p4_break = calculate_priority_score(
        project_deadline=today + timedelta(days=12),
        project_category="Capstone / Final Year Thesis",
        student_dept="Biotechnology & Nanotechnology",
        equipment_dept=eq_printer.department_name,
        purpose="Fabricating biocompatible microfluidic chip housing with custom optical channel wells.",
        equipment_specs=eq_printer.specs
    )
    b4 = BookingRequest(
        equipment_id=eq_printer.id,
        student_name="Kavya Nair",
        student_id="2021-BIO-014",
        student_email="kavya.n@campus.edu",
        student_dept="Biotechnology & Nanotechnology",
        project_title="Lab-on-a-Chip Microfluidic Diagnostic Cassette",
        project_category="Capstone / Final Year Thesis",
        project_deadline=today + timedelta(days=12),
        purpose="Fabricating biocompatible microfluidic chip housing with custom optical channel wells.",
        booking_date=day_after,
        start_time="10:00",
        end_time="14:00",
        duration_hours=4,
        status="Approved",
        faculty_comments="Cross-department project approved. Lab technician assigned to supervise print slice setup.",
        priority_score=p4_score,
        priority_tier=p4_tier,
        priority_breakdown=p4_break,
        conflict_detected=False,
        ai_recommendation="✅ Optimal Allocation: Interdisciplinary sharing boost applied (+15 pts). Machine available."
    )

    db.session.add_all([b1, b2, b3, b4])
    db.session.commit()
