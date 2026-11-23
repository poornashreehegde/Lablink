# LabLink — Campus Laboratory Resource-Sharing Platform

> **GenAI-Powered Campus Laboratory Democratization & Fair Slot Allocation Engine**

LabLink connects students, researchers, and faculty across academic departments to discover, share, and schedule specialized research equipment, development workstations, and laboratory test benches. By eliminating interdisciplinary silos, LabLink maximizes expensive institutional equipment utilization while ensuring fair access through an automated **GenAI Conflict Resolution and Priority Scoring Engine**.

---

## 🌟 Key Features

### 1. Cross-Department Equipment Discovery & Catalog
- **Campus-Wide Hardware Registry**: Browse high-demand facilities across Computer Science, Electronics & Communication, Mechanical Mechatronics, Biotechnology, and Physics.
- **Real-Time Availability Indicators**: Instant visual status badges (`Available`, `Busy / In Use`, `Maintenance`) with live 7-day schedule timelines.
- **Granular Hardware Specs**: Detailed compute architectures (e.g., 4x NVIDIA A100 VRAM, Keysight 4 GHz DSO, Stratasys industrial 3D printers, UV-Vis Spectrophotometers).
- **Safety Prerequisites Auditing**: Displays mandatory lab protocols (ESD wristbands, laser safety goggles, cleanroom certifications) before booking.

### 2. Role-Based Access Control (RBAC) & Authentication
- **Three Distinct Roles**:
  - **Student**: Register, discover hardware, submit project access requests, and track own requests privately.
  - **Faculty**: Supervise assigned equipment and labs, review pending bookings, approve/reject requests, and apply AI alternative slots.
  - **Admin**: System-wide oversight, manage department listings, assign faculty to equipment, and adjust user roles.
- **Secure Sessions**: Protected by HTTP-only cookies, password hashing with Werkzeug (`scrypt`), and session CSRF tokens.

### 3. Intelligent Project-Based Slot Booking
- Students reserve hardware with required project metadata:
  - **Academic Context**: Student ID, Email, Department.
  - **Project Classification**: Capstone / Thesis, Faculty Sponsored Research, Competitive Hackathon, Coursework.
  - **Submission Deadline**: Mandatory chronological validation (deadline &ge; booking date &ge; today).
  - **Operating Hours Enforcement**: Bookings validated strictly within laboratory hours (08:00 AM – 08:00 PM).
  - **Duration Guards**: Enforces maximum allowable slot duration per equipment (no negative or zero values).

### 4. GenAI Conflict Resolver & Double-Booking Prevention
- **Multi-Factor Priority Scoring (0 - 100)**:
  - **Deadline Proximity (up to 40 pts)**: Students with imminent deadlines (< 48 hours) receive urgent prioritization.
  - **Research Impact (up to 30 pts)**: Sponsored patents and thesis projects are weighed fairly against coursework.
  - **Cross-Department Sharing Equity (up to 15 pts)**: Interdisciplinary bonus promotes campus democratization.
  - **Spec Alignment Justification (up to 15 pts)**: Evaluates technical fit between project abstract and equipment specs.
- **Active Double-Booking Prevention**:
  - Re-evaluates availability against all existing approved bookings at the moment of approval.
  - Strictly prevents approving two overlapping reservations on the same machine.
  - Prevents duplicate approval counter inflation.

### 5. Accurate AI Alternative Slot Application
- When scheduling collisions occur, the engine searches for open conflict-free windows on the same machine or equivalent equipment across campus.
- Clicking **"Apply AI Alternate Slot"** actually updates the database record with the new `booking_date`, `start_time`, `end_time`, `duration_hours`, and `equipment_id` before confirming approval.

### 6. Dual-Mode GenAI Equipment Advisor
- **Live Google Gemini Integration**: Connects via Google GenAI REST API when `GEMINI_API_KEY` is present in the environment.
- **Heuristic Fallback Engine**: If no API key is provided, seamlessly and transparently falls back to the deterministic keyword spec-matcher without hallucinating false confidence.
- Available via the dedicated `/ai-advisor` page and the global floating assistant.

### 7. Institutional Resource Utilisation Analytics
- **Cross-Department Sharing Ratio**: Calculated dynamically from verified database records.
- **Historical Conflict Metric**: Preserves conflict audit history even after resolution.
- **Interactive Visualizations**: Powered by Chart.js for department booking volume and category demand shares.

---

## 🛠️ Technology Stack

- **Backend**: Python 3, Flask 3.1, Flask-SQLAlchemy 3.1, Werkzeug
- **Database**: SQLite (Zero configuration, lightweight, portable)
- **Frontend**: HTML5, Modern Responsive UI with Tailwind CSS (CDN)
- **Data Visualization**: Chart.js (CDN)
- **Iconography & Design**: Lucide Icons (CDN), Plus Jakarta Sans Typography
- **Repository Footprint**: Ultra-lightweight (~0.35 MB), strictly complying with the < 10 MB competition limit!

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ installed on your system.
- Git installed.

### 2. Setup & Installation
```bash
# Clone the repository
git clone <YOUR_PUBLIC_GITHUB_REPO_URL>
cd lablink

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the sample environment file:
```bash
cp .env.example .env
```
*(Optional: add `GEMINI_API_KEY=your_key_here` to enable live Gemini 1.5 Flash recommendations).*

### 4. Run the Application
```bash
python app.py
```
Open your web browser and visit: **`http://127.0.0.1:5000`**

### Pre-Seeded Evaluation Accounts
| Role | Username / Email | Password | Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `AdminPassword2026!` | University-wide access & user management |
| **Faculty** | `arvind.cse` | `FacultyPassword2026!` | In-charge of Deep Learning A100 Workstation |
| **Faculty** | `s.radha` | `FacultyPassword2026!` | In-charge of High-Frequency DSO |
| **Student** | `priya.r` | `StudentPassword2026!` | CSE Student (SafeNav Project) |
| **Student** | `aarav.s` | `StudentPassword2026!` | ECE Student (DisasterNet Project) |

---

## 🧪 Automated Testing Suite

LabLink includes two automated test suites:

### 1. Comprehensive Functionality & Security Test Suite
Tests authentication, RBAC, request privacy, past date rejection, slot duration bounds, operating hours, double-booking prevention, duplicate approval prevention, AI alternative updates, and faculty scoping on an isolated test database:
```bash
python test_comprehensive.py
```

### 2. Route & API Verification Suite
Tests public endpoints, unauthenticated redirect protection, and authenticated role endpoints:
```bash
python test_app.py
```

---

## 📂 Project Directory Structure

```
lablink/
├── app.py                     # Main Flask web application, route handlers, & error controllers
├── models.py                  # SQLAlchemy ORM models (User, Equipment, Department, BookingRequest)
├── auth.py                    # Session auth, RBAC decorators, & CSRF token validators
├── ai_engine.py               # Priority scoring, double-booking checks, & Gemini/Heuristic advisor
├── seed_data.py               # Database migration, schema updates, & campus demo dataset
├── test_comprehensive.py      # Automated 14-test verification suite (isolated test DB)
├── test_app.py                # Route & API endpoint verification script
├── requirements.txt           # Minimal Python dependencies
├── .env.example               # Template for environment variables & API keys
├── .gitignore                 # Strict repository hygiene (< 10 MB compliance)
├── README.md                  # Comprehensive documentation
├── static/
│   ├── css/custom.css         # Glassmorphism styling & priority meters
│   └── js/                    # Static scripts
└── templates/
    ├── base.html              # Layout, navbar, user profile pill, & floating AI assistant
    ├── index.html             # Equipment discovery catalog & filter bar
    ├── equipment_detail.html  # Hardware specs, safety rules, & live 7-day schedule
    ├── book.html              # Project-based booking form with boundary validation
    ├── requests.html          # Student request tracker & AI priority breakdown
    ├── admin.html             # Faculty approval console & 1-click alternate resolution
    ├── admin_equipment.html   # Admin faculty equipment assignment portal
    ├── admin_users.html       # Admin user directory & role management portal
    ├── analytics.html         # Resource utilization & Chart.js visualizations
    ├── ai_advisor.html        # Natural language equipment recommendation page
    ├── login.html             # Secure user sign-in page with evaluation credentials
    ├── register.html          # Public student registration page
    └── error.html             # Custom styled error page (400, 403, 404, 500)
```

---

## 📋 Competition Compliance Checklist

- [x] **Repository Size**: Total project size is ~0.35 MB (Well below the 10 MB limit).
- [x] **Branch Requirement**: Configured on a single `main` branch with no extra branches.
- [x] **Public Visibility**: Ready to be pushed to your public GitHub repository.
- [x] **Security**: Secrets and database binaries excluded via `.gitignore`.
- [x] **Verification**: All 14 automated functionality & security tests passing.
