import os
import re
import json
from datetime import datetime, date, timedelta
import requests

LAB_OPEN_HOUR = 8   # 08:00 AM
LAB_CLOSE_HOUR = 20  # 08:00 PM

def time_to_minutes(time_str):
    """Converts 'HH:MM' string to minutes since midnight."""
    try:
        parts = time_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0

def minutes_to_time(minutes):
    """Converts minutes since midnight to 'HH:MM'."""
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def is_time_overlapping(start1, end1, start2, end2):
    """Returns True if interval [start1, end1] overlaps with [start2, end2]."""
    s1, e1 = time_to_minutes(start1), time_to_minutes(end1)
    s2, e2 = time_to_minutes(start2), time_to_minutes(end2)
    return max(s1, s2) < min(e1, e2)

def validate_operating_hours(start_time, end_time):
    """Ensures the requested slot lies strictly within laboratory operating hours (08:00 - 20:00)."""
    s_min = time_to_minutes(start_time)
    e_min = time_to_minutes(end_time)
    open_min = LAB_OPEN_HOUR * 60
    close_min = LAB_CLOSE_HOUR * 60
    
    if s_min < open_min:
        return False, f"Start time {start_time} is before lab opening time ({LAB_OPEN_HOUR:02d}:00)."
    if e_min > close_min:
        return False, f"End time {end_time} exceeds lab closing time ({LAB_CLOSE_HOUR:02d}:00)."
    if e_min <= s_min:
        return False, "End time must be after start time."
    return True, "Valid operating hours."


def calculate_priority_score(project_deadline, project_category, student_dept, equipment_dept, purpose, equipment_specs=""):
    """
    Transparent, Deterministic Multi-Factor Priority & Fairness Scoring Algorithm.
    Factors:
    1. Deadline Proximity (0 to 40 pts)
    2. Project Scope & Category Weight (0 to 30 pts)
    3. Cross-Department Resource Sharing Bonus (0 to 15 pts)
    4. Technical Spec Alignment (0 to 15 pts)
    Total: 0 to 100 points
    """
    score = 0.0
    breakdown = []
    today = date.today()

    if isinstance(project_deadline, str):
        try:
            deadline_date = datetime.strptime(project_deadline, '%Y-%m-%d').date()
        except Exception:
            deadline_date = today + timedelta(days=14)
    else:
        deadline_date = project_deadline

    # 1. Deadline Proximity
    days_to_deadline = (deadline_date - today).days

    if days_to_deadline < 0:
        return 0.0, "Invalid Deadline", "Deadline date has already passed."
    elif days_to_deadline <= 2:
        deadline_pts = 40.0
        breakdown.append(f"Imminent Deadline ({days_to_deadline}d remaining): +40 pts")
    elif days_to_deadline <= 7:
        deadline_pts = 30.0
        breakdown.append(f"Urgent Deadline ({days_to_deadline}d): +30 pts")
    elif days_to_deadline <= 14:
        deadline_pts = 20.0
        breakdown.append(f"Moderate Proximity ({days_to_deadline}d): +20 pts")
    elif days_to_deadline <= 30:
        deadline_pts = 10.0
        breakdown.append(f"Standard Horizon ({days_to_deadline}d): +10 pts")
    else:
        deadline_pts = 5.0
        breakdown.append(f"Long-term Horizon (>30d): +5 pts")
    score += deadline_pts

    # 2. Project Category Weight
    category_weights = {
        'Faculty Sponsored Research': 30.0,
        'Patent / Industrial Prototype': 28.0,
        'Capstone / Final Year Thesis': 25.0,
        'Competitive Hackathon / Conf Paper': 20.0,
        'Academic Coursework / Lab Exam': 12.0,
        'Self-Directed Learning / Hobby': 8.0
    }
    cat_pts = category_weights.get(project_category, 15.0)
    breakdown.append(f"Project Tier ({project_category}): +{cat_pts:.0f} pts")
    score += cat_pts

    # 3. Cross-Department Sharing Equity (Fairness Quota)
    is_cross_dept = (student_dept.strip().lower() != equipment_dept.strip().lower())
    if is_cross_dept:
        cross_pts = 15.0
        breakdown.append(f"Cross-Department Access ({student_dept} -> {equipment_dept}): +15 pts (Fairness Quota)")
    else:
        cross_pts = 8.0
        breakdown.append("Intra-Department Utilization: +8 pts")
    score += cross_pts

    # 4. Technical Spec Alignment & Justification (Anti-Gaming Check)
    purpose_lower = purpose.lower().strip()
    specs_lower = equipment_specs.lower()
    
    # Extract unique technical words from specs
    spec_keywords = set(re.findall(r'\b[a-z]{4,}\b', specs_lower))
    matches = sum(1 for kw in spec_keywords if kw in purpose_lower)
    
    # Meaningful text length check (avoiding single word spamming)
    if len(purpose_lower) >= 80 and matches >= 2:
        align_pts = 15.0
        breakdown.append("Strong Technical Justification & Spec Alignment: +15 pts")
    elif len(purpose_lower) >= 40 and matches >= 1:
        align_pts = 10.0
        breakdown.append("Moderate Justification & Keyword Match: +10 pts")
    elif len(purpose_lower) >= 20:
        align_pts = 6.0
        breakdown.append("Basic Purpose Stated: +6 pts")
    else:
        align_pts = 3.0
        breakdown.append("Minimal Purpose Stated: +3 pts")
    score += align_pts

    final_score = min(round(score, 1), 100.0)

    if final_score >= 80:
        tier = 'Critical Urgency'
    elif final_score >= 65:
        tier = 'High Priority'
    elif final_score >= 45:
        tier = 'Standard'
    else:
        tier = 'Flexible'

    return final_score, tier, " | ".join(breakdown)


def check_conflicts(target_date, start_time, end_time, equipment_id, exclude_booking_id=None):
    """
    Checks all existing bookings for a given equipment and date.
    Returns:
      approved_conflicts: List of confirmed Approved bookings that collide.
      competing_pending: List of Pending bookings that collide.
    """
    from models import BookingRequest
    
    query = BookingRequest.query.filter(
        BookingRequest.equipment_id == equipment_id,
        BookingRequest.booking_date == target_date
    )
    if exclude_booking_id:
        query = query.filter(BookingRequest.id != exclude_booking_id)
        
    all_day_bookings = query.all()
    
    approved_conflicts = []
    competing_pending = []
    
    for b in all_day_bookings:
        if is_time_overlapping(start_time, end_time, b.start_time, b.end_time):
            if b.status == 'Approved':
                approved_conflicts.append(b)
            elif b.status == 'Pending':
                competing_pending.append(b)
                
    return approved_conflicts, competing_pending


def find_feasible_alternative(equipment, target_date, duration_hours, all_equipment_in_category=[]):
    """
    Finds a verified, conflict-free alternative slot or machine.
    Returns structured dict:
      {
        'alt_date': date,
        'alt_start_time': 'HH:MM',
        'alt_end_time': 'HH:MM',
        'alt_duration': int,
        'alt_equipment_id': int,
        'display_slot': str,
        'alt_equipment_name': str
      }
    """
    from models import BookingRequest

    # Standard lab windows to test
    duration = min(duration_hours, equipment.max_slot_hours)
    candidate_start_hours = [9, 13, 16]

    # 1. Search candidate slots on the same machine (Target date, Target date + 1, Target date + 2)
    for day_offset in [0, 1, 2]:
        test_date = target_date + timedelta(days=day_offset)
        
        # Approved bookings on this date
        approved_today = BookingRequest.query.filter(
            BookingRequest.equipment_id == equipment.id,
            BookingRequest.booking_date == test_date,
            BookingRequest.status == 'Approved'
        ).all()
        
        for sh in candidate_start_hours:
            eh = sh + duration
            if eh > LAB_CLOSE_HOUR:
                continue
            
            s_str = f"{sh:02d}:00"
            e_str = f"{eh:02d}:00"
            
            has_collision = any(is_time_overlapping(s_str, e_str, b.start_time, b.end_time) for b in approved_today)
            if not has_collision:
                return {
                    'alt_date': test_date,
                    'alt_start_time': s_str,
                    'alt_end_time': e_str,
                    'alt_duration': duration,
                    'alt_equipment_id': equipment.id,
                    'display_slot': f"{test_date.strftime('%b %d, %Y')} ({s_str} - {e_str})",
                    'alt_equipment_name': equipment.name
                }

    # 2. Search alternative equipment in the same category
    for alt_eq in all_equipment_in_category:
        if alt_eq.id == equipment.id or alt_eq.status != 'Available':
            continue
            
        alt_approved = BookingRequest.query.filter(
            BookingRequest.equipment_id == alt_eq.id,
            BookingRequest.booking_date == target_date,
            BookingRequest.status == 'Approved'
        ).all()
        
        for sh in candidate_start_hours:
            eh = sh + min(duration, alt_eq.max_slot_hours)
            if eh > LAB_CLOSE_HOUR:
                continue
            s_str = f"{sh:02d}:00"
            e_str = f"{eh:02d}:00"
            
            has_collision = any(is_time_overlapping(s_str, e_str, b.start_time, b.end_time) for b in alt_approved)
            if not has_collision:
                return {
                    'alt_date': target_date,
                    'alt_start_time': s_str,
                    'alt_end_time': e_str,
                    'alt_duration': min(duration, alt_eq.max_slot_hours),
                    'alt_equipment_id': alt_eq.id,
                    'display_slot': f"{target_date.strftime('%b %d, %Y')} ({s_str} - {e_str})",
                    'alt_equipment_name': f"{alt_eq.name} ({alt_eq.code})"
                }

    return None


def resolve_conflicts_and_recommend(new_req, equipment, all_equipment_in_category=[]):
    """
    Evaluates all scheduling conflicts (both hard collisions with Approved slots and competing Pending requests).
    Produces structured recommendation and actionable alternative parameters.
    """
    approved_conflicts, competing_pending = check_conflicts(
        target_date=new_req.booking_date,
        start_time=new_req.start_time,
        end_time=new_req.end_time,
        equipment_id=equipment.id,
        exclude_booking_id=new_req.id
    )

    alt_dict = find_feasible_alternative(
        equipment=equipment,
        target_date=new_req.booking_date,
        duration_hours=new_req.duration_hours,
        all_equipment_in_category=all_equipment_in_category
    )

    alt_slot_str = alt_dict['display_slot'] if alt_dict else "No verified open slot found within 72 hours"
    alt_equip_str = alt_dict['alt_equipment_name'] if (alt_dict and alt_dict['alt_equipment_id'] != equipment.id) else None

    # Case A: Hard Collision with an already Approved reservation!
    if approved_conflicts:
        primary = approved_conflicts[0]
        recommendation = (
            f"🚫 HARD CONFLICT: Slot directly overlaps with confirmed Approved Booking #{primary.id} "
            f"({primary.student_name}, {primary.start_time}-{primary.end_time}). "
            f"This slot is occupied. Actionable Feasible Alternative: "
            f"Reschedule to {alt_slot_str} {f'on {alt_equip_str}' if alt_equip_str else ''}."
        )
        return True, primary.id, recommendation, alt_slot_str, alt_equip_str, alt_dict

    # Case B: Competing Pending request(s)
    elif competing_pending:
        competing = competing_pending[0]
        if new_req.priority_score > competing.priority_score:
            recommendation = (
                f"⚠️ Scheduling Contention: Multiple pending requests for this window. "
                f"Request #{new_req.id or 'New'} ({new_req.student_name}) holds higher priority score "
                f"({new_req.priority_score:.1f} vs #{competing.id} at {competing.priority_score:.1f}) "
                f"driven by closer deadline on {new_req.project_deadline.strftime('%b %d')}. "
                f"Recommended for approval; recommend shifting #{competing.id} to {alt_slot_str}."
            )
        else:
            recommendation = (
                f"⚠️ Scheduling Contention: Multiple pending requests for this window. "
                f"Competing Request #{competing.id} ({competing.student_name}) holds higher priority "
                f"({competing.priority_score:.1f} vs {new_req.priority_score:.1f}). "
                f"Recommendation: Allocate slot to #{competing.id}; offer {new_req.student_name} alternative {alt_slot_str}."
            )
        return True, competing.id, recommendation, alt_slot_str, alt_equip_str, alt_dict

    # Case C: Zero collisions
    else:
        recommendation = (
            f"✅ Optimal Allocation: Slot is completely unencumbered for {equipment.name}. "
            f"Priority score: {new_req.priority_score:.1f}/100 ({new_req.priority_tier}). "
            f"Meets all safety prerequisites and operating hours."
        )
        return False, None, recommendation, alt_slot_str, alt_equip_str, alt_dict


# ==========================================
# GenAI Equipment Advisor with Real LLM & Fallback
# ==========================================

def smart_equipment_advisor(prompt, all_equipment):
    """
    Dual-mode Equipment Advisor:
    1. If GEMINI_API_KEY is configured in environment, uses Google Gemini to semantically understand project requirements.
    2. If unconfigured or offline, seamlessly falls back to the transparent heuristic spec-matcher.
    """
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    
    # Try Gemini API if key is present
    if api_key:
        try:
            return _call_gemini_advisor(prompt, all_equipment, api_key)
        except Exception as e:
            print(f"Gemini API request failed ({e}); falling back to heuristic engine.")

    # Heuristic fallback engine
    return _heuristic_advisor(prompt, all_equipment)


def _call_gemini_advisor(prompt, all_equipment, api_key):
    """Queries Gemini 1.5 Flash via REST endpoint to recommend equipment."""
    equipment_catalog = [
        {
            "id": eq.id,
            "code": eq.code,
            "name": eq.name,
            "category": eq.category,
            "department": eq.department_name,
            "lab": eq.lab_name,
            "specs": eq.specs,
            "status": eq.status
        }
        for eq in all_equipment
    ]

    system_instruction = (
        "You are LabLink's AI Campus Laboratory Advisor. Analyze the student's project requirements "
        "and select the best matching equipment strictly from the provided catalog. "
        "Return ONLY valid JSON matching this schema: "
        "{\"matches\": [{\"id\": <equipment_id>, \"confidence\": <int 0-100>, \"rationale\": \"<specific technical reason why it fits>\"}]}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_instruction}\n\nAvailable Equipment Catalog:\n{json.dumps(equipment_catalog)}\n\nStudent Project Request:\n\"{prompt}\""}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=8)
    if resp.status_code == 200:
        res_data = resp.json()
        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        parsed = json.loads(raw_text)
        
        matches = parsed.get('matches', [])
        equipment_map = {eq.id: eq for eq in all_equipment}
        
        results = []
        for m in matches[:4]:
            eq = equipment_map.get(m['id'])
            if eq:
                results.append({
                    'equipment': eq,
                    'confidence': int(m.get('confidence', 80)),
                    'rationale': f"[Gemini AI] {m.get('rationale', 'Compatible hardware specifications.')}",
                    'suggested_action': f"Reserve at {eq.lab_name} ({eq.location})"
                })
        if results:
            return results

    raise RuntimeError(f"Gemini API returned status {resp.status_code}")


def _heuristic_advisor(prompt, all_equipment):
    """
    Transparent Heuristic Spec-Matching Engine.
    Uses domain keyword clusters and token intersection.
    Returns 0 matches for gibberish/irrelevant text (no artificial minimum floor).
    """
    p_lower = prompt.lower().strip()
    if not p_lower:
        return []

    domain_map = {
        'ai': ['deep learning', 'pytorch', 'tensorflow', 'gpu', 'neural', 'transformer', 'llm', 'vision', 'cuda', 'yolo', 'train', 'dataset'],
        'embedded': ['fpga', 'microcontroller', 'verilog', 'vhdl', 'stm32', 'arm', 'iot', 'sensor', 'zynq', 'embedded', 'rtos', 'uart', 'spi'],
        'rf': ['oscilloscope', 'spectrum', 'frequency', 'ghz', 'mhz', 'signal', 'antenna', 'rf', 'modulation', 'waveform', 'impedance', 'circuit'],
        'prototyping': ['3d print', 'cad', 'solidworks', 'chassis', 'enclosure', 'prototype', 'laser cut', 'pla', 'resin', 'mechanical', 'robotics'],
        'biotech': ['spectrophotometer', 'absorbance', 'dna', 'protein', 'chemical', 'nanoparticle', 'uv-vis', 'assay', 'centrifuge', 'molecular']
    }

    prompt_words = set(re.findall(r'\b[a-z]{4,}\b', p_lower))
    # Exclude common stop words
    stop_words = {'this', 'that', 'with', 'from', 'have', 'need', 'want', 'using', 'project', 'build', 'make', 'test'}
    meaningful_words = prompt_words - stop_words

    recommendations = []

    for eq in all_equipment:
        specs_text = (eq.specs + " " + eq.name + " " + eq.category + " " + eq.department_name).lower()
        match_score = 0
        reasons = []

        # 1. Direct keyword intersection
        direct_matches = [w for w in meaningful_words if w in specs_text]
        if direct_matches:
            match_score += len(direct_matches) * 20
            reasons.append(f"Matched specifications: {', '.join(direct_matches[:4])}")

        # 2. Domain cluster match
        for domain, kw_list in domain_map.items():
            prompt_has = any(k in p_lower for k in kw_list)
            spec_has = any(k in specs_text for k in kw_list)
            if prompt_has and spec_has:
                match_score += 35
                reasons.append(f"High compatibility with {domain.upper()} domain experimental setup")

        # Only qualify if there is actual relevant overlap
        if match_score >= 20:
            if eq.status == 'Available':
                match_score += 10
                reasons.append("Currently ready for reservation")

            confidence = min(match_score, 98)
            recommendations.append({
                'equipment': eq,
                'confidence': confidence,
                'rationale': f"[Heuristic Engine] {' • '.join(reasons)}",
                'suggested_action': f"Reserve at {eq.lab_name} ({eq.location})"
            })

    recommendations.sort(key=lambda x: x['confidence'], reverse=True)
    return recommendations[:4]
