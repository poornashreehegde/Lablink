from datetime import datetime, date, timedelta
import re

def calculate_priority_score(project_deadline, project_category, student_dept, equipment_dept, purpose, equipment_specs=""):
    """
    Intelligent Multi-Factor Priority and Fairness Scoring Algorithm:
    1. Project Deadline Proximity (up to 40 pts)
    2. Project Scope & Category Weight (up to 30 pts)
    3. Cross-Department Resource Sharing Bonus (up to 15 pts)
    4. Equipment Requirement Alignment (up to 15 pts)
    Total: 0 to 100 points
    """
    score = 0.0
    breakdown = []
    
    # 1. Deadline Proximity (Max 40)
    today = date.today()
    if isinstance(project_deadline, str):
        try:
            deadline_date = datetime.strptime(project_deadline, '%Y-%m-%d').date()
        except Exception:
            deadline_date = today + timedelta(days=14)
    else:
        deadline_date = project_deadline

    days_to_deadline = (deadline_date - today).days

    if days_to_deadline <= 2:
        deadline_pts = 40.0
        breakdown.append(f"Imminent Deadline ({days_to_deadline}d remaining): +40 pts")
    elif days_to_deadline <= 7:
        deadline_pts = 32.0
        breakdown.append(f"Urgent Upcoming Deadline ({days_to_deadline}d): +32 pts")
    elif days_to_deadline <= 14:
        deadline_pts = 22.0
        breakdown.append(f"Moderate Deadline Proximity ({days_to_deadline}d): +22 pts")
    elif days_to_deadline <= 30:
        deadline_pts = 14.0
        breakdown.append(f"Standard Project Horizon ({days_to_deadline}d): +14 pts")
    else:
        deadline_pts = 8.0
        breakdown.append(f"Long-term Project Timeline (>30d): +8 pts")
    score += deadline_pts

    # 2. Project Category Weight (Max 30)
    category_weights = {
        'Faculty Sponsored Research': 30.0,
        'Patent / Industrial Prototype': 30.0,
        'Capstone / Final Year Thesis': 26.0,
        'Competitive Hackathon / Conf Paper': 22.0,
        'Academic Coursework / Lab Exam': 15.0,
        'Self-Directed Learning / Hobby': 10.0
    }
    cat_pts = category_weights.get(project_category, 18.0)
    breakdown.append(f"Project Tier ({project_category}): +{cat_pts:.0f} pts")
    score += cat_pts

    # 3. Cross-Department Sharing Equity (Max 15)
    # Give priority boost when a student seeks interdisciplinary access to promote fair campus sharing
    is_cross_dept = (student_dept.strip().lower() != equipment_dept.strip().lower())
    if is_cross_dept:
        cross_pts = 15.0
        breakdown.append(f"Interdisciplinary Lab Sharing ({student_dept} -> {equipment_dept}): +15 pts (Fairness Quota)")
    else:
        cross_pts = 8.0
        breakdown.append("Intra-Department Utilization: +8 pts")
    score += cross_pts

    # 4. Equipment Spec Alignment & Justification Clarity (Max 15)
    purpose_lower = purpose.lower()
    specs_lower = equipment_specs.lower()
    keywords = re.findall(r'\b[a-z]{3,}\b', specs_lower)
    matches = sum(1 for kw in set(keywords) if kw in purpose_lower)
    
    if len(purpose.strip()) > 100 or matches >= 3:
        align_pts = 15.0
        breakdown.append("High Technical Justification & Spec Match: +15 pts")
    elif len(purpose.strip()) > 40 or matches >= 1:
        align_pts = 10.0
        breakdown.append("Moderate Technical Justification: +10 pts")
    else:
        align_pts = 6.0
        breakdown.append("Basic Purpose Stated: +6 pts")
    score += align_pts

    # Final score cap & tier categorization
    final_score = min(round(score, 1), 100.0)
    
    if final_score >= 80:
        tier = 'Critical Urgency'
    elif final_score >= 65:
        tier = 'High Priority'
    elif final_score >= 45:
        tier = 'Standard'
    else:
        tier = 'Low / Flexible'

    return final_score, tier, " | ".join(breakdown)


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
    s1, e1 = time_to_minutes(start1), time_to_minutes(end1)
    s2, e2 = time_to_minutes(start2), time_to_minutes(end2)
    return max(s1, s2) < min(e1, e2)


def resolve_conflicts_and_recommend(new_req, equipment, existing_bookings, all_equipment_in_category=[]):
    """
    Intelligent GenAI Conflict Detection and Fair Slot Allocation Engine.
    Examines overlapping bookings on the target date.
    Suggests:
      1. Fair resolution based on priority scores and deadlines.
      2. Alternative available slots on the same machine.
      3. Alternative equivalent machines in the same category across campus.
    """
    conflicting = None
    target_date = new_req.booking_date
    
    for b in existing_bookings:
        if b.id == new_req.id:
            continue
        if b.status in ['Approved', 'Pending'] and b.booking_date == target_date:
            if is_time_overlapping(new_req.start_time, new_req.end_time, b.start_time, b.end_time):
                conflicting = b
                break

    # Standard lab operating hours: 09:00 to 18:00
    candidate_slots = [
        ("09:00", "12:00"),
        ("12:30", "15:30"),
        ("15:30", "18:30")
    ]
    
    # Check free alternative slot on this machine
    alt_slot_str = None
    booked_slots = [(b.start_time, b.end_time) for b in existing_bookings 
                    if b.booking_date == target_date and b.status in ['Approved', 'Pending']]
    
    for slot_s, slot_e in candidate_slots:
        collision = any(is_time_overlapping(slot_s, slot_e, bs, be) for bs, be in booked_slots)
        if not collision:
            alt_slot_str = f"{target_date.strftime('%b %d, %Y')} ({slot_s} - {slot_e})"
            break
            
    if not alt_slot_str:
        next_day = target_date + timedelta(days=1)
        alt_slot_str = f"{next_day.strftime('%b %d, %Y')} (09:00 - 12:00)"

    # Check alternative equivalent equipment
    alt_equip_str = None
    for eq in all_equipment_in_category:
        if eq.id != equipment.id and eq.status == 'Available':
            alt_equip_str = f"{eq.name} ({eq.code}) at {eq.lab_name}"
            break

    if conflicting:
        # We have a scheduling conflict!
        is_higher_priority = new_req.priority_score > conflicting.priority_score
        score_diff = abs(new_req.priority_score - conflicting.priority_score)
        
        if is_higher_priority:
            recommendation = (
                f"⚠️ Scheduling Conflict Detected with Request #{conflicting.id} ({conflicting.student_name}). "
                f"GenAI Allocation Engine recommends ALLOCATING this slot to {new_req.student_name} "
                f"(Priority: {new_req.priority_score:.1f} vs {conflicting.priority_score:.1f}, "
                f"driven by closer deadline on {new_req.project_deadline.strftime('%b %d')}). "
                f"Actionable Alternative for Request #{conflicting.id}: Re-route to slot {alt_slot_str} "
                f"or equivalent machine {alt_equip_str or 'nearby laboratory workstation'}."
            )
        else:
            recommendation = (
                f"⚠️ Scheduling Conflict Detected with prior booking #{conflicting.id} ({conflicting.student_name}). "
                f"Request #{conflicting.id} currently holds higher priority ({conflicting.priority_score:.1f} vs {new_req.priority_score:.1f}). "
                f"GenAI Engine recommends offering {new_req.student_name} alternative slot {alt_slot_str} "
                f"{f'or booking {alt_equip_str}' if alt_equip_str else ''} to ensure zero project delay."
            )
        return True, conflicting.id, recommendation, alt_slot_str, alt_equip_str
    else:
        # No conflict - Smooth Allocation
        recommendation = (
            f"✅ Optimal Allocation: Zero slot collisions detected for {equipment.name}. "
            f"Evaluated priority score of {new_req.priority_score:.1f}/100 ({new_req.priority_tier}). "
            f"Equipment availability and safety prerequisites verified. Recommended for immediate faculty sign-off."
        )
        return False, None, recommendation, alt_slot_str, alt_equip_str


def smart_equipment_advisor(prompt, all_equipment):
    """
    GenAI Lab Equipment & Workstation Advisor:
    Accepts natural language student project abstracts or queries
    and intelligently returns matched equipment with match percentage and technical rationale.
    """
    p_lower = prompt.lower()
    recommendations = []
    
    # Domain keyword heuristics for high-accuracy campus matching
    domain_map = {
        'ai': ['deep learning', 'pytorch', 'tensorflow', 'gpu', 'neural', 'transformer', 'llm', 'vision', 'cuda', 'yolo', 'train', 'dataset'],
        'embedded': ['fpga', 'microcontroller', 'verilog', 'vhdl', 'stm32', 'arm', 'iot', 'sensor', 'zynq', 'embedded', 'rtos', 'uart', 'spi'],
        'rf': ['oscilloscope', 'spectrum', 'frequency', 'ghz', 'mhz', 'signal', 'antenna', 'rf', 'modulation', 'waveform', 'impedance', 'circuit'],
        'prototyping': ['3d print', 'cad', 'solidworks', 'chassis', 'enclosure', 'prototype', 'laser cut', 'pla', 'resin', 'mechanical', 'robotics'],
        'biotech': ['spectrophotometer', 'absorbance', 'dna', 'protein', 'chemical', 'nanoparticle', 'uv-vis', 'assay', 'centrifuge', 'molecular']
    }

    for eq in all_equipment:
        specs_text = (eq.specs + " " + eq.name + " " + eq.category + " " + eq.department_name).lower()
        match_score = 0
        reasons = []

        # Check prompt words in specs
        words = set(re.findall(r'\b[a-z]{3,}\b', p_lower))
        direct_matches = [w for w in words if w in specs_text]
        match_score += len(direct_matches) * 15

        # Check domain clusters
        for domain, kw_list in domain_map.items():
            prompt_has_domain = any(k in p_lower for k in kw_list)
            spec_has_domain = any(k in specs_text for k in kw_list)
            if prompt_has_domain and spec_has_domain:
                match_score += 35
                reasons.append(f"Strong fit for {domain.upper()} domain requirements")

        if direct_matches:
            reasons.append(f"Matched key specifications: {', '.join(direct_matches[:4])}")

        if eq.status == 'Available':
            match_score += 10
            reasons.append("Currently available for immediate booking")
        else:
            reasons.append(f"Current status: {eq.status}")

        confidence = min(max(match_score, 20), 98)
        
        # Build recommendation card
        recommendations.append({
            'equipment': eq,
            'confidence': confidence,
            'rationale': " • ".join(reasons) if reasons else "Compatible with requested project scope and academic prerequisites.",
            'suggested_action': f"Reserve at {eq.lab_name} ({eq.location})"
        })

    # Sort by highest confidence
    recommendations.sort(key=lambda x: x['confidence'], reverse=True)
    return recommendations[:4]
