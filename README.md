# LabLink — Campus Laboratory Resource-Sharing Platform

> **GenAI-Powered Campus Lab Democratization & Fair Slot Allocation Engine**

LabLink connects students, researchers, and faculty across academic departments to discover, share, and schedule specialized research equipment, development workstations, and laboratory test benches. By eliminating interdisciplinary silos, LabLink maximizes expensive institutional equipment utilization while ensuring fair access through an automated **GenAI Conflict Resolution and Priority Scoring Engine**.

---

## 🌟 Key Features

### 1. Cross-Department Equipment Discovery & Catalog
- **Campus-Wide Hardware Registry**: Browse high-demand facilities across Computer Science, Electronics & Communication, Mechanical Mechatronics, Biotechnology, and Physics.
- **Real-Time Availability Indicators**: Instant visual status badges (`Available`, `Busy / In Use`, `Maintenance`) with live 7-day schedule timelines.
- **Granular Hardware Specs**: Detailed compute architectures (e.g., 4x NVIDIA A100 VRAM, Keysight 4 GHz DSO, Stratasys industrial 3D printers, UV-Vis Spectrophotometers).
- **Safety Prerequisites Auditing**: Displays mandatory lab protocols (ESD wristbands, laser safety goggles, cleanroom certifications) before booking.

### 2. Intelligent Project-Based Slot Booking
- Students reserve hardware by providing structured project metadata:
  - **Academic Context**: Student ID, Email, Department.
  - **Project Classification**: Capstone / Thesis, Faculty Sponsored Research, Competitive Hackathon, Coursework.
  - **Submission Deadline**: Crucial input factor for objective scheduling prioritization.
  - **Technical Justification**: Natural language description of why specialized equipment is essential.

### 3. GenAI Conflict Resolver & Fair Allocation Algorithm
When multiple research teams request overlapping time windows on scarce equipment:
- **Multi-Factor Priority Scoring (0 - 100)**:
  - **Deadline Proximity (up to 40 pts)**: Students with imminent deadlines (< 48 hours) receive urgent prioritization.
  - **Research Impact (up to 30 pts)**: Sponsored patents and thesis projects are weighed fairly against coursework.
  - **Cross-Department Sharing Equity (up to 15 pts)**: Interdisciplinary bonus promotes campus democratization.
  - **Spec Alignment Justification (up to 15 pts)**: Evaluates technical fit between project abstract and equipment specs.
- **Automated Conflict Resolution**:
  - Detects time collisions across active bookings.
  - Synthesizes clear natural-language allocation recommendations.
  - Automatically identifies feasible alternative slots on the same machine or equivalent hardware in nearby campus labs with zero research delay.

### 4. Faculty & Lab Administrator Portal
- **Collision Alert Center**: Highlights scheduling conflicts with side-by-side priority comparisons.
- **One-Click AI Resolution**: "Apply AI Alternate Slot" button instantly reschedules and confirms without manual back-and-forth.
- **Direct Approval Workflow**: 1-click Approve or Reject with audit remarks.

### 5. Campus Utilisation & Sharing Analytics
- **Cross-Department Sharing Ratio**: Real-time KPI tracking interdisciplinary access density (e.g. 72.5%).
- **Interactive Visualizations**: Powered by Chart.js for department booking volume and category demand shares.
- **Equipment ROI Leaderboard**: Highlights highest-utilized institutional assets.

### 6. GenAI Lab Equipment Advisor & Floating Chatbot
- Natural language query interface: Type project requirements (e.g., *"We need to train a YOLO vision model on 250k images"* or *"Need to measure 2.4 GHz RF waveform impedance"*), and the AI returns matched equipment with match percentage and technical rationale.
- Global floating AI Assistant accessible across every page.

---

## 🛠️ Technology Stack

- **Backend**: Python 3, Flask 3.1, Flask-SQLAlchemy 3.1
- **Database**: SQLite (Zero configuration, lightweight, portable)
- **Frontend**: HTML5, Modern Responsive UI with Tailwind CSS (CDN)
- **Data Visualization**: Chart.js (CDN)
- **Iconography & Design**: Lucide Icons (CDN), Plus Jakarta Sans Typography
- **Repository Footprint**: Ultra-lightweight (~0.26 MB), strictly complying with the < 10 MB size limit!

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

### 3. Run the Application
```bash
python app.py
```
Open your web browser and visit: **`http://127.0.0.1:5000`**

*The application automatically creates the SQLite database and seeds 12 realistic campus equipment entries, departments, and sample booking requests with live simulated conflicts ready to demonstrate.*

---

## 🧪 Testing & Verification

A route verification suite is included:
```bash
python test_app.py
```
Validates all endpoints (`/`, `/equipment/1`, `/book/1`, `/requests`, `/admin`, `/analytics`, `/ai-advisor`, and `/api/chat-advisor`).

---

## 📂 Project Directory Structure

```
lablink/
├── app.py                # Main Flask application & route controllers
├── models.py             # SQLAlchemy models (Equipment, Department, BookingRequest)
├── ai_engine.py          # GenAI Conflict Resolution & Priority Scoring algorithms
├── seed_data.py          # Campus equipment & simulated conflict demo data
├── test_app.py           # Verification test suite
├── requirements.txt      # Lightweight dependencies
├── .gitignore            # Strict repository hygiene (< 10 MB compliance)
├── README.md             # Project documentation
├── static/
│   ├── css/custom.css    # Custom styles & glassmorphism utilities
│   └── js/               # Frontend scripts
└── templates/
    ├── base.html         # Global layout with navigation & floating AI Assistant
    ├── index.html        # Equipment discovery catalog & filter bar
    ├── equipment_detail.html # Specs, safety protocols & live 7-day schedule
    ├── book.html         # Project-based booking form with GenAI scoring
    ├── requests.html     # Student request tracker & AI recommendation view
    ├── admin.html        # Faculty approval console & conflict resolution center
    ├── analytics.html    # Resource utilization & cross-department charts
    └── ai_advisor.html   # Natural language equipment recommendation page
```

---

## 📋 Competition Compliance Checklist

- [x] **Repository Size**: Total project size is ~0.26 MB (Well below the 10 MB limit).
- [x] **Branch Requirement**: Configured on a single `main` branch with no extra branches.
- [x] **Public Visibility**: Ready to be pushed to your public GitHub repository.
- [x] **Documentation**: Full problem statement coverage, architecture explanation, and demo guide.
