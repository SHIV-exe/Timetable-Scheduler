import json
import os
import sys

def build_complete_custom_json():
    period_slots = [
        {"period": 1, "name": "09:00 AM - 10:00 AM", "start": "09:00", "end": "10:00", "is_lunch": False},
        {"period": 2, "name": "10:00 AM - 11:00 AM", "start": "10:00", "end": "11:00", "is_lunch": False},
        {"period": 3, "name": "11:00 AM - 12:00 PM", "start": "11:00", "end": "12:00", "is_lunch": False},
        {"period": 4, "name": "12:00 PM - 01:00 PM", "start": "12:00", "end": "13:00", "is_lunch": True},
        {"period": 5, "name": "01:00 PM - 02:00 PM", "start": "13:00", "end": "14:00", "is_lunch": False},
        {"period": 6, "name": "02:00 PM - 03:00 PM", "start": "14:00", "end": "15:00", "is_lunch": False},
        {"period": 7, "name": "03:00 PM - 04:00 PM", "start": "15:00", "end": "16:00", "is_lunch": False},
    ]

    subjects = [
        {"code": "CS201", "name": "Data Structures", "hours": 4, "type": "theory"},
        {"code": "CS202", "name": "Algorithms & Complexity", "hours": 4, "type": "theory"},
        {"code": "CS203", "name": "Database Management Systems", "hours": 4, "type": "theory"},
        {"code": "CS204", "name": "Operating Systems Internals", "hours": 4, "type": "theory"},
        {"code": "CS201L", "name": "Data Structures Practical Lab", "hours": 2, "type": "lab", "room_type": "lab"},
        {"code": "CS203L", "name": "Database Systems Practical Lab", "hours": 2, "type": "lab", "room_type": "lab"},
        {"code": "COMM1", "name": "Communication Skills & Soft Skills Lab", "hours": 2, "type": "lab", "room_type": "tutorial_room"},
    ]

    rooms = [
        {"name": "LT-1", "capacity": 150, "type": "lecture_theatre"},
        {"name": "LT-2", "capacity": 120, "type": "lecture_theatre"},
        {"name": "Hall-101", "capacity": 100, "type": "classroom"},
        {"name": "Hall-102", "capacity": 70, "type": "classroom"},
        {"name": "Hall-103", "capacity": 70, "type": "classroom"},
        {"name": "TR-101", "capacity": 40, "type": "tutorial_room"},
        {"name": "TR-102", "capacity": 40, "type": "tutorial_room"},
        {"name": "Computing-Lab-1", "capacity": 90, "type": "lab"},
        {"name": "Software-Lab-2", "capacity": 60, "type": "lab"},
        {"name": "Hardware-Lab-3", "capacity": 36, "type": "lab"},
        {"name": "Systems-Lab-4", "capacity": 60, "type": "lab"},
    ]

    teachers = [
        {"name": "Prof. Donald Knuth", "subjects": ["CS201", "CS201L", "CS202"], "unavailable": [["Mon", 1]], "max_load": 18, "avoid_periods": [1]},
        {"name": "Prof. Edsger Dijkstra", "subjects": ["CS202", "CS204"], "unavailable": [["Tue", 7]], "max_load": 18, "avoid_periods": [7]},
        {"name": "Dr. Barbara Liskov", "subjects": ["CS201", "CS201L", "CS204", "COMM1"], "unavailable": [["Wed", 1]], "max_load": 18, "avoid_periods": [1]},
        {"name": "Dr. Edgar Codd", "subjects": ["CS203", "CS203L"], "unavailable": [["Thu", 7]], "max_load": 18, "avoid_periods": [7]},
        {"name": "Dr. Michael Stonebraker", "subjects": ["CS203", "CS203L"], "unavailable": [["Fri", 1]], "max_load": 18, "avoid_periods": [1]},
        {"name": "Prof. Andrew Tanenbaum", "subjects": ["CS204", "CS201"], "unavailable": [["Mon", 7]], "max_load": 18, "avoid_periods": [7]},
        {"name": "Dr. Grace Hopper", "subjects": ["CS201", "CS201L", "CS203", "COMM1"], "unavailable": [["Tue", 1]], "max_load": 18, "avoid_periods": [1]},
        {"name": "Dr. Ken Thompson", "subjects": ["CS204", "CS201L"], "unavailable": [["Wed", 7]], "max_load": 18, "avoid_periods": [7]},
        {"name": "Dr. Leslie Lamport", "subjects": ["CS202", "CS204"], "unavailable": [["Thu", 1]], "max_load": 18, "avoid_periods": [1]},
        {"name": "Prof. John Hopcroft", "subjects": ["CS202", "COMM1"], "unavailable": [["Fri", 7]], "max_load": 18, "avoid_periods": [7]},
        {"name": "Prof. Jeffrey Ullman", "subjects": ["CS202", "CS203"], "unavailable": [["Mon", 2]], "max_load": 18, "avoid_periods": [2]},
        {"name": "Dr. Tim Berners-Lee", "subjects": ["CS203", "CS203L"], "unavailable": [["Tue", 6]], "max_load": 18, "avoid_periods": [6]},
        {"name": "Dr. Radia Perlman", "subjects": ["CS201", "CS201L", "COMM1"], "unavailable": [["Wed", 2]], "max_load": 18, "avoid_periods": [2]},
        {"name": "Prof. Robert Tarjan", "subjects": ["CS201", "CS202"], "unavailable": [["Thu", 6]], "max_load": 18, "avoid_periods": [6]},
        {"name": "Prof. Shafi Goldwasser", "subjects": ["CS202", "CS203L"], "unavailable": [["Fri", 2]], "max_load": 18, "avoid_periods": [2]},
    ]

    # Batches: Unified cohorts as requested by user
    batches = [
        {
            "name": "CSE-A",
            "semester": 3,
            "sem_type": "odd",
            "strength": 120,
            "auto_split": True,
            "lunch_period": 4,
            "subjects": ["CS201", "CS202", "CS203"],
            "labs": ["CS201L", "COMM1"],
            "teacher_map": {}
        },
        {
            "name": "CSE-B",
            "semester": 3,
            "sem_type": "odd",
            "strength": 90,
            "auto_split": True,
            "lunch_period": 4,
            "subjects": ["CS201", "CS202", "CS204"],
            "labs": ["CS201L", "CS203L"],
            "teacher_map": {}
        },
        {
            "name": "IT-A",
            "semester": 3,
            "sem_type": "odd",
            "strength": 60,
            "auto_split": True,
            "lunch_period": 4,
            "subjects": ["CS202", "CS203", "CS204"],
            "labs": ["CS203L", "COMM1"],
            "teacher_map": {}
        },
        {
            "name": "ECE-A",
            "semester": 3,
            "sem_type": "odd",
            "strength": 60,
            "auto_split": True,
            "lunch_period": 4,
            "subjects": ["CS201", "CS203", "CS204"],
            "labs": ["CS201L", "CS203L"],
            "teacher_map": {}
        }
    ]

    # Compile classes for solver
    classes = []
    for b in batches:
        strength = b["strength"]
        theory_subs = b["subjects"]
        lab_subs = b["labs"]
        lunch = b["lunch_period"]

        if b.get("auto_split", True) and lab_subs and strength > 30:
            k = (strength + 29) // 30
            sub_strength = min(30, (strength + k - 1) // k)
            # Parent theory class
            if theory_subs:
                classes.append({
                    "name": b["name"],
                    "strength": strength,
                    "subjects": theory_subs,
                    "lunch_period": lunch,
                    "teacher_map": b.get("teacher_map", {}),
                    "parent_class": None,
                    "parent_batch": b["name"],
                    "semester": b.get("semester", 3)
                })
            # Sub-batches for lab
            for i in range(1, k + 1):
                classes.append({
                    "name": f"{b['name']}{i}",
                    "strength": sub_strength,
                    "subjects": lab_subs,
                    "lunch_period": lunch,
                    "teacher_map": b.get("teacher_map", {}),
                    "parent_class": b["name"],
                    "parent_batch": b["name"],
                    "sub_index": i,
                    "semester": b.get("semester", 3)
                })
        else:
            classes.append({
                "name": b["name"],
                "strength": strength,
                "subjects": theory_subs + lab_subs,
                "lunch_period": lunch,
                "teacher_map": b.get("teacher_map", {}),
                "parent_class": None,
                "parent_batch": b["name"],
                "semester": b.get("semester", 3)
            })

    custom_data = {
        "time": {
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "periods_per_day": 7,
            "break_periods": [],
            "lab_block": 2,
            "period_slots": period_slots
        },
        "subjects": subjects,
        "rooms": rooms,
        "teachers": teachers,
        "batches": batches,
        "classes": classes
    }

    custom_path = os.path.join(os.path.dirname(__file__), "..", "data", "custom.json")
    with open(custom_path, "w", encoding="utf-8") as f:
        json.dump(custom_data, f, indent=2)
    print(f"Successfully generated clean custom.json with {len(batches)} batches ({len(classes)} compiled classes) and {len(rooms)} rooms.")

if __name__ == "__main__":
    build_complete_custom_json()
