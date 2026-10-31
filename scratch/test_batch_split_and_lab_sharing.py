import json
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.model import load_from_dict, validate_raw_data, check_feasibility, assign_teachers, build_sessions, build_domains
from core.evaluate import evaluate
from core import solvers

def test_batch_splitting_and_lab_sharing():
    period_slots = [
        {"period": 1, "name": "09:00 AM - 10:00 AM", "start": "09:00", "end": "10:00", "is_lunch": False},
        {"period": 2, "name": "10:00 AM - 11:00 AM", "start": "10:00", "end": "11:00", "is_lunch": False},
        {"period": 3, "name": "11:00 AM - 12:00 PM", "start": "11:00", "end": "12:00", "is_lunch": False},
        {"period": 4, "name": "12:00 PM - 01:00 PM", "start": "12:00", "end": "13:00", "is_lunch": True},
        {"period": 5, "name": "01:00 PM - 02:00 PM", "start": "13:00", "end": "14:00", "is_lunch": False},
        {"period": 6, "name": "02:00 PM - 03:00 PM", "start": "14:00", "end": "15:00", "is_lunch": False},
        {"period": 7, "name": "03:00 PM - 04:00 PM", "start": "15:00", "end": "16:00", "is_lunch": False},
    ]

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
            {"code": "CS102P", "name": "Data Structures Lab", "hours": 2, "type": "lab", "room_type": "lab"},
            {"code": "COMM1", "name": "Communication Skills Lab", "hours": 2, "type": "lab", "room_type": "tutorial_room"},
        ],
        "rooms": [
            {"name": "LT-1", "capacity": 150, "type": "lecture_theatre"},
            {"name": "Hall-101", "capacity": 100, "type": "classroom"},
            {"name": "Hall-102", "capacity": 70, "type": "classroom"},
            {"name": "TR-1", "capacity": 40, "type": "tutorial_room"},
            {"name": "Lab-90", "capacity": 90, "type": "lab"},
            {"name": "Lab-60", "capacity": 60, "type": "lab"},
            {"name": "Lab-36", "capacity": 36, "type": "lab"},
        ],
        "teachers": [
            {"name": "Prof. Smith", "subjects": ["CS101", "CS101P"], "max_load": 20, "unavailable": [], "avoid_periods": []},
            {"name": "Prof. Jones", "subjects": ["CS102", "CS102P"], "max_load": 20, "unavailable": [], "avoid_periods": []},
            {"name": "Prof. Miller", "subjects": ["CS101", "CS101P", "COMM1"], "max_load": 20, "unavailable": [], "avoid_periods": []},
            {"name": "Prof. Davis", "subjects": ["CS102", "CS102P"], "max_load": 20, "unavailable": [], "avoid_periods": []},
            {"name": "Prof. Wilson", "subjects": ["COMM1", "CS101P"], "max_load": 20, "unavailable": [], "avoid_periods": []},
            {"name": "Prof. Taylor", "subjects": ["CS101", "CS102"], "max_load": 20, "unavailable": [], "avoid_periods": []},
        ],
        # Batch A (120): theory together, 4 lab sections (A1..A4)
        # Batch B (60): theory together, 2 lab sections (B1..B2)
        "classes": [
            # Batch A theory:
            {"name": "Batch-A", "strength": 120, "subjects": ["CS101", "CS102"], "lunch_period": 4, "parent_class": None},
            # Batch A lab sections:
            {"name": "Batch-A1", "strength": 30, "subjects": ["CS101P", "COMM1"], "lunch_period": 4, "parent_class": "Batch-A"},
            {"name": "Batch-A2", "strength": 30, "subjects": ["CS101P", "COMM1"], "lunch_period": 4, "parent_class": "Batch-A"},
            {"name": "Batch-A3", "strength": 30, "subjects": ["CS101P", "COMM1"], "lunch_period": 4, "parent_class": "Batch-A"},
            {"name": "Batch-A4", "strength": 30, "subjects": ["CS101P", "COMM1"], "lunch_period": 4, "parent_class": "Batch-A"},
            # Batch B theory:
            {"name": "Batch-B", "strength": 60, "subjects": ["CS101", "CS102"], "lunch_period": 4, "parent_class": None},
            # Batch B lab sections:
            {"name": "Batch-B1", "strength": 30, "subjects": ["CS102P"], "lunch_period": 4, "parent_class": "Batch-B"},
            {"name": "Batch-B2", "strength": 30, "subjects": ["CS102P"], "lunch_period": 4, "parent_class": "Batch-B"},
        ]
    }

    errors = validate_raw_data(raw)
    assert not errors, f"Validation errors: {errors}"

    data_obj = load_from_dict(raw)
    checks = check_feasibility(data_obj)
    for c in checks:
        print(f"Check: {c['name']} -> {c['passed']} ({c['detail']})")
        assert c["passed"], f"Feasibility check failed: {c}"

    teacher_of = assign_teachers(data_obj)
    sessions = build_sessions(data_obj, teacher_of)
    domains = build_domains(data_obj, sessions)

    result = solvers.run(
        algo="Min-Conflicts",
        data=data_obj,
        sessions=sessions,
        domains=domains,
        seed=42,
        time_limit=15.0
    )

    print(f"Result: success={result.success}, work={result.work}, time={result.time_taken:.3f}s")
    rep = evaluate(data_obj, sessions, result.asg)
    print(f"Hard total: {rep.hard_total}, Breakdown: {dict(rep.hard)}, Messages: {rep.messages[:5]}")
    assert rep.hard_total == 0, f"Hard violations: {rep.messages}"
    bt_result = solvers.run(
        algo="Backtracking (MRV + FC + degree)",
        data=data_obj,
        sessions=sessions,
        domains=domains,
        seed=42,
        time_limit=15.0
    )
    print(f"BT Result: success={bt_result.success}, nodes={bt_result.work}, time={bt_result.time_taken:.3f}s")
    bt_rep = evaluate(data_obj, sessions, bt_result.asg)
    assert bt_rep.hard_total == 0, f"BT Hard violations: {bt_rep.messages}"
    print("[SUCCESS] Both Min-Conflicts and Backtracking solved with 0 hard clashes!")

if __name__ == "__main__":
    test_batch_splitting_and_lab_sharing()
