"""Dataset generation script for AI Timetable Scheduler (Section 11.1).

Constructs and verifies:
- data/small.json: 3 classes, 6 teachers, 4 rooms (3 classrooms, 1 lab), 5 days x 6 periods.
- data/large.json: 8 classes, 15 teachers, 8 rooms (6 classrooms, 2 labs), 5 days x 7 periods.

Both datasets include teacher unavailable slots (exercising H6), avoided periods (exercising S4),
and varying room capacities vs class strengths (exercising H4).
Each dataset is validated and confirmed solvable with 0 hard violations.
"""

import json
import os
import random
import sys
from typing import Dict, Any

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.model import (
    validate_raw_data,
    load_from_dict,
    check_feasibility,
    assign_teachers,
    build_sessions,
    build_domains,
)
from core.solvers import run
from core.evaluate import evaluate


def generate_small_dataset() -> Dict[str, Any]:
    """Generate small college dataset adhering strictly to Section 11.1 specification:
    3 classes, 6 teachers (max load 12), 4 rooms (3 classrooms, 1 lab),
    5 days x 6 periods, lunch period 4 (1-indexed).
    Per class: 14 theory + 2 lab = 16 hours.
    Total theory = 42 hrs, Total lab = 6 hrs.
    """
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    periods = 6

    # 4 theory subjects + 1 lab subject
    # Theory hours: MATH (4), PHY (3), CHEM (3), CS (4) = 14 hrs
    # Lab hours: CSLAB (2) = 2 hrs
    # Total per class = 16 hrs
    subjects = [
        {"code": "MATH101", "name": "Linear Algebra & Calculus", "hours": 4, "type": "theory"},
        {"code": "PHY101", "name": "Applied Physics", "hours": 3, "type": "theory"},
        {"code": "CHEM101", "name": "Engineering Chemistry", "hours": 3, "type": "theory"},
        {"code": "CS101", "name": "Computer Programming", "hours": 4, "type": "theory"},
        {"code": "CS101L", "name": "Programming Laboratory", "hours": 2, "type": "lab"},
    ]

    # 6 Teachers with max_load 12. Total capacity = 72 hrs. Demand = 48 hrs.
    # Avg load = 8 hrs.
    teachers = [
        {
            "name": "Dr. Alan Turing",
            "subjects": ["CS101", "CS101L"],
            "unavailable": [["Mon", 1]],
            "max_load": 12,
            "avoid_periods": [1],
        },
        {
            "name": "Prof. Ada Lovelace",
            "subjects": ["CS101", "CS101L"],
            "unavailable": [["Fri", 6]],
            "max_load": 12,
            "avoid_periods": [6],
        },
        {
            "name": "Dr. Carl Gauss",
            "subjects": ["MATH101"],
            "unavailable": [["Wed", 1]],
            "max_load": 12,
            "avoid_periods": [1, 6],
        },
        {
            "name": "Dr. Katherine Johnson",
            "subjects": ["MATH101"],
            "unavailable": [["Tue", 6]],
            "max_load": 12,
            "avoid_periods": [5],
        },
        {
            "name": "Dr. Marie Curie",
            "subjects": ["CHEM101"],
            "unavailable": [["Thu", 1]],
            "max_load": 12,
            "avoid_periods": [2],
        },
        {
            "name": "Dr. Richard Feynman",
            "subjects": ["PHY101"],
            "unavailable": [["Mon", 6]],
            "max_load": 12,
            "avoid_periods": [6],
        },
    ]

    # 3 Classes: Class A (40), Class B (50), Class C (35)
    classes = [
        {
            "name": "CS-A",
            "strength": 40,
            "subjects": ["MATH101", "PHY101", "CHEM101", "CS101", "CS101L"],
            "lunch_period": 4,
            "teacher_map": {},
        },
        {
            "name": "CS-B",
            "strength": 50,
            "subjects": ["MATH101", "PHY101", "CHEM101", "CS101", "CS101L"],
            "lunch_period": 4,
            "teacher_map": {},
        },
        {
            "name": "CS-C",
            "strength": 35,
            "subjects": ["MATH101", "PHY101", "CHEM101", "CS101", "CS101L"],
            "lunch_period": 4,
            "teacher_map": {},
        },
    ]

    # 4 Rooms: 3 Classrooms (capacities 45, 55, 60), 1 Lab (capacity 60)
    rooms = [
        {"name": "CR-101", "capacity": 45, "type": "classroom"},
        {"name": "CR-102", "capacity": 55, "type": "classroom"},
        {"name": "CR-103", "capacity": 60, "type": "classroom"},
        {"name": "LAB-1", "capacity": 60, "type": "lab"},
    ]

    return {
        "time": {
            "days": days,
            "periods_per_day": periods,
            "break_periods": [],
            "lab_block": 2,
        },
        "subjects": subjects,
        "teachers": teachers,
        "classes": classes,
        "rooms": rooms,
    }


def generate_large_dataset() -> Dict[str, Any]:
    """Generate large college dataset adhering strictly to Section 11.1 specification:
    8 classes, 15 teachers (max load 14), 8 rooms (6 classrooms, 2 labs),
    5 days x 7 periods, lunch period 4 (1-indexed).
    Per class: 16 theory + 4 lab = 20 hours.
    Total theory = 128 hrs, Total lab = 32 hrs. Total demand = 160 hrs.
    Avg teacher load = 160 / 15 = 10.67 hrs.
    """
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    periods = 7

    # 4 theory subjects + 2 lab subjects
    # Theory: DS (4), ALGO (4), DB (4), OS (4) = 16 hrs
    # Labs: DSLAB (2), DBLAB (2) = 4 hrs
    # Total = 20 hrs per class
    subjects = [
        {"code": "CS201", "name": "Data Structures", "hours": 4, "type": "theory"},
        {"code": "CS202", "name": "Algorithms", "hours": 4, "type": "theory"},
        {"code": "CS203", "name": "Database Systems", "hours": 4, "type": "theory"},
        {"code": "CS204", "name": "Operating Systems", "hours": 4, "type": "theory"},
        {"code": "CS201L", "name": "Data Structures Lab", "hours": 2, "type": "lab"},
        {"code": "CS203L", "name": "Database Lab", "hours": 2, "type": "lab"},
    ]

    # 15 Teachers with max load 14. Total capacity = 210 hrs. Total demand = 160 hrs.
    teachers = [
        {"name": "Prof. Donald Knuth", "subjects": ["CS201", "CS201L", "CS202"], "unavailable": [["Mon", 1]], "max_load": 14, "avoid_periods": [1]},
        {"name": "Prof. Edsger Dijkstra", "subjects": ["CS202", "CS204"], "unavailable": [["Tue", 7]], "max_load": 14, "avoid_periods": [7]},
        {"name": "Dr. Barbara Liskov", "subjects": ["CS201", "CS201L", "CS204"], "unavailable": [["Wed", 1]], "max_load": 14, "avoid_periods": [1]},
        {"name": "Dr. Edgar Codd", "subjects": ["CS203", "CS203L"], "unavailable": [["Thu", 7]], "max_load": 14, "avoid_periods": [7]},
        {"name": "Dr. Michael Stonebraker", "subjects": ["CS203", "CS203L"], "unavailable": [["Fri", 1]], "max_load": 14, "avoid_periods": [1, 2]},
        {"name": "Prof. Andrew Tanenbaum", "subjects": ["CS204"], "unavailable": [["Mon", 7]], "max_load": 14, "avoid_periods": [7]},
        {"name": "Dr. Grace Hopper", "subjects": ["CS201", "CS201L", "CS203"], "unavailable": [["Tue", 1]], "max_load": 14, "avoid_periods": [1]},
        {"name": "Dr. Ken Thompson", "subjects": ["CS204"], "unavailable": [["Wed", 7]], "max_load": 14, "avoid_periods": [7]},
        {"name": "Dr. Leslie Lamport", "subjects": ["CS202", "CS204"], "unavailable": [["Thu", 1]], "max_load": 14, "avoid_periods": [2]},
        {"name": "Prof. John Hopcroft", "subjects": ["CS202"], "unavailable": [["Fri", 7]], "max_load": 14, "avoid_periods": [7]},
        {"name": "Prof. Jeffrey Ullman", "subjects": ["CS202", "CS203"], "unavailable": [["Mon", 2]], "max_load": 14, "avoid_periods": [2]},
        {"name": "Dr. Tim Berners-Lee", "subjects": ["CS203", "CS203L"], "unavailable": [["Tue", 6]], "max_load": 14, "avoid_periods": [6]},
        {"name": "Dr. Radia Perlman", "subjects": ["CS201", "CS201L"], "unavailable": [["Wed", 2]], "max_load": 14, "avoid_periods": [6]},
        {"name": "Prof. Robert Tarjan", "subjects": ["CS201", "CS202"], "unavailable": [["Thu", 6]], "max_load": 14, "avoid_periods": [1]},
        {"name": "Prof. Shafi Goldwasser", "subjects": ["CS202", "CS204"], "unavailable": [["Fri", 2]], "max_load": 14, "avoid_periods": [2]},
    ]

    # 8 Classes
    classes = []
    class_names = ["CSE-2A", "CSE-2B", "CSE-2C", "CSE-2D", "IT-2A", "IT-2B", "ECE-2A", "ECE-2B"]
    strengths = [55, 50, 48, 52, 45, 42, 58, 46]
    for name, st in zip(class_names, strengths):
        classes.append({
            "name": name,
            "strength": st,
            "subjects": ["CS201", "CS202", "CS203", "CS204", "CS201L", "CS203L"],
            "lunch_period": 4,
            "teacher_map": {},
        })

    # 8 Rooms: 6 Classrooms + 2 Labs
    rooms = [
        {"name": "Hall-101", "capacity": 65, "type": "classroom"},
        {"name": "Hall-102", "capacity": 60, "type": "classroom"},
        {"name": "Hall-103", "capacity": 60, "type": "classroom"},
        {"name": "Hall-104", "capacity": 55, "type": "classroom"},
        {"name": "Hall-105", "capacity": 55, "type": "classroom"},
        {"name": "Hall-106", "capacity": 50, "type": "classroom"},
        {"name": "Sys-Lab-A", "capacity": 65, "type": "lab"},
        {"name": "Data-Lab-B", "capacity": 60, "type": "lab"},
    ]

    return {
        "time": {
            "days": days,
            "periods_per_day": periods,
            "break_periods": [],
            "lab_block": 2,
        },
        "subjects": subjects,
        "teachers": teachers,
        "classes": classes,
        "rooms": rooms,
    }


def main():
    os.makedirs("data", exist_ok=True)

    # 1. Generate and save Small Dataset
    small_raw = generate_small_dataset()
    errors_small = validate_raw_data(small_raw)
    assert not errors_small, f"Small dataset validation failed: {errors_small}"

    small_data = load_from_dict(small_raw)
    feas_small = check_feasibility(small_data)
    print("=== Small Dataset Feasibility Checks ===")
    for c in feas_small:
        status = "PASS" if c["passed"] else "FAIL"
        print(f"[{status}] {c['name']}: {c['detail']}")
        assert c["passed"], f"Feasibility failed for small dataset: {c['name']}"

    # Verify small dataset is solvable
    t_map_small = assign_teachers(small_data)
    sess_small = build_sessions(small_data, t_map_small)
    dom_small = build_domains(small_data, sess_small)
    print(f"Small dataset: {len(sess_small)} sessions across {len(small_data.classes)} classes.")

    res_small = run("Backtracking (MRV + FC + degree)", small_data, sess_small, dom_small, seed=42, time_limit=15)
    rep_small = evaluate(small_data, sess_small, res_small.asg)
    assert rep_small.hard_total == 0, f"Small dataset solution has hard violations: {rep_small.messages}"
    print(f"Small dataset solved with 0 hard violations! Soft penalty: {rep_small.soft_total}, Work: {res_small.work} nodes.")

    with open("data/small.json", "w", encoding="utf-8") as f:
        json.dump(small_raw, f, indent=2)
    print("Saved data/small.json\n")

    # 2. Generate and save Large Dataset
    large_raw = generate_large_dataset()
    errors_large = validate_raw_data(large_raw)
    assert not errors_large, f"Large dataset validation failed: {errors_large}"

    large_data = load_from_dict(large_raw)
    feas_large = check_feasibility(large_data)
    print("=== Large Dataset Feasibility Checks ===")
    for c in feas_large:
        status = "PASS" if c["passed"] else "FAIL"
        print(f"[{status}] {c['name']}: {c['detail']}")
        assert c["passed"], f"Feasibility failed for large dataset: {c['name']}"

    # Verify large dataset is solvable
    t_map_large = assign_teachers(large_data)
    sess_large = build_sessions(large_data, t_map_large)
    dom_large = build_domains(large_data, sess_large)
    print(f"Large dataset: {len(sess_large)} sessions across {len(large_data.classes)} classes.")

    res_large = run("Min-Conflicts", large_data, sess_large, dom_large, seed=42, time_limit=30)
    rep_large = evaluate(large_data, sess_large, res_large.asg)
    assert rep_large.hard_total == 0, f"Large dataset solution has hard violations: {rep_large.messages}"
    print(f"Large dataset solved with 0 hard violations! Soft penalty: {rep_large.soft_total}, Work: {res_large.work} iters.")

    with open("data/large.json", "w", encoding="utf-8") as f:
        json.dump(large_raw, f, indent=2)
    print("Saved data/large.json\n")

    print("Both datasets successfully created and verified solvable!")


if __name__ == "__main__":
    main()
