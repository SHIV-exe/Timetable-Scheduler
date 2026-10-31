import json
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.model import load_from_dict, validate_raw_data, check_feasibility, assign_teachers, build_sessions, build_domains
from core.evaluate import evaluate
from core import solvers

def test_custom_scheduling_with_split():
    # 9 AM - 5 PM with 7 periods, lunch at P5 (1:00 PM - 2:00 PM)
    period_slots = [
        {"period": 1, "name": "09:00 AM - 10:00 AM", "start": "09:00", "end": "10:00"},
        {"period": 2, "name": "10:00 AM - 11:00 AM", "start": "10:00", "end": "11:00"},
        {"period": 3, "name": "11:00 AM - 12:00 PM", "start": "11:00", "end": "12:00"},
        {"period": 4, "name": "12:00 PM - 01:00 PM", "start": "12:00", "end": "13:00"},
        {"period": 5, "name": "01:00 PM - 02:00 PM", "start": "13:00", "end": "14:00", "is_lunch": True},
        {"period": 6, "name": "02:00 PM - 03:00 PM", "start": "14:00", "end": "15:00"},
        {"period": 7, "name": "03:00 PM - 04:00 PM", "start": "15:00", "end": "16:00"},
    ]

    # Batch A had strength 120, split into 4 sub-batches of 30: A1, A2, A3, A4
    # Batch B had strength 60, split into 2 sub-batches of 30: B1, B2
    raw = {
        "time": {
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "periods_per_day": 7,
            "break_periods": [],
            "lab_block": 2,
            "period_slots": period_slots
        },
        "subjects": [
            {"code": "CS101", "name": "Programming Foundations", "hours": 4, "type": "theory"},
            {"code": "CS102", "name": "Data Structures", "hours": 4, "type": "theory"},
            {"code": "CS101P", "name": "Programming Lab", "hours": 2, "type": "lab", "room_type": "lab"},
            {"code": "COMM1", "name": "Communication Skills Lab", "hours": 2, "type": "lab", "room_type": "tutorial_room"},
        ],
        "rooms": [
            {"name": "LT-1", "capacity": 150, "type": "lecture_theatre"},
            {"name": "TR-1", "capacity": 40, "type": "tutorial_room"},
            {"name": "CR-1", "capacity": 70, "type": "classroom"},
            {"name": "Lab-90", "capacity": 90, "type": "lab"},
            {"name": "Lab-60", "capacity": 60, "type": "lab"},
            {"name": "Lab-36", "capacity": 36, "type": "lab"},
        ],
        "teachers": [
            {"name": "Prof. Smith", "subjects": ["CS101", "CS101P"], "max_load": 20, "unavailable": [], "avoid_periods": []},
            {"name": "Prof. Jones", "subjects": ["CS102", "CS101P"], "max_load": 20, "unavailable": [], "avoid_periods": []},
            {"name": "Prof. Miller", "subjects": ["CS101", "CS101P", "COMM1"], "max_load": 20, "unavailable": [], "avoid_periods": []},
            {"name": "Prof. Davis", "subjects": ["CS102", "COMM1"], "max_load": 20, "unavailable": [], "avoid_periods": []},
        ],
        # Batch A of 120 students:
        # - Theory lectures CS101 & CS102 conducted together in LT-1 for all 120 students
        # - Lab CS101P & COMM1 divided into 4 sections of 30: A1, A2, A3, A4
        "classes": [
            {"name": "Batch-A", "strength": 120, "subjects": ["CS101", "CS102"], "lunch_period": 5, "parent_class": None},
            {"name": "A1", "strength": 30, "subjects": ["CS101P", "COMM1"], "lunch_period": 5, "parent_class": "Batch-A"},
            {"name": "A2", "strength": 30, "subjects": ["CS101P", "COMM1"], "lunch_period": 5, "parent_class": "Batch-A"},
            {"name": "A3", "strength": 30, "subjects": ["CS101P", "COMM1"], "lunch_period": 5, "parent_class": "Batch-A"},
            {"name": "A4", "strength": 30, "subjects": ["CS101P", "COMM1"], "lunch_period": 5, "parent_class": "Batch-A"},
        ]
    }

    errors = validate_raw_data(raw)
    assert not errors, f"Validation errors: {errors}"

    data_obj = load_from_dict(raw)
    checks = check_feasibility(data_obj)
    all_passed = all(c["passed"] for c in checks)
    assert all_passed, f"Feasibility checks failed: {[c for c in checks if not c['passed']]}"

    teacher_of = assign_teachers(data_obj)
    sessions = build_sessions(data_obj, teacher_of)
    domains = build_domains(data_obj, sessions)

    result = solvers.run(
        algo="Min-Conflicts",
        data=data_obj,
        sessions=sessions,
        domains=domains,
        seed=42,
        time_limit=10.0
    )

    assert result.success, f"Min-conflicts failed: {result}"
    rep = evaluate(data_obj, sessions, result.asg)
    assert rep.hard_total == 0, f"Hard violations: {rep.hard_total}"
    print(f"[SUCCESS] Custom scheduling solved with 0 hard clashes in {result.time_taken:.3f}s across {len(sessions)} sessions!")

if __name__ == "__main__":
    test_custom_scheduling_with_split()
