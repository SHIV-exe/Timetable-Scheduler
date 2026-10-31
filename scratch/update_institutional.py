import json
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from core.model import load_from_dict, check_feasibility, assign_teachers, build_sessions, build_domains
from core.evaluate import evaluate
from core import solvers

src_path = "data/institutional_timetable_specification (1).json"
with open(src_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 1. Update teachers to ensure balanced humanities/communication capacity
for t in data["teachers"]:
    if t["name"] in ("Dr Aditi Gaur", "Dr. Ankita Birla", "Dr. Adarsh Kumar"):
        t["max_load"] = 20
        if "HSP-101" not in t["subjects"]:
            t["subjects"].append("HSP-101")
        if "HST-101" not in t["subjects"]:
            t["subjects"].append("HST-101")

# 2. Batches merged with combined capacities
unified_batches = [
    {
        "name": "CSE A",
        "semester": 3,
        "sem_type": "odd",
        "strength": 90,
        "auto_split": True,
        "lunch_period": 5,
        "subjects": ["MAT-201", "CST-201", "CST-203", "ECT-201", "ECT-211", "HST-201"],
        "labs": ["AIP-211", "CSP-201", "ECP-201", "MMP-201"],
        "teacher_map": {}
    },
    {
        "name": "CSE B",
        "semester": 3,
        "sem_type": "odd",
        "strength": 90,
        "auto_split": True,
        "lunch_period": 5,
        "subjects": ["MAT-201", "CST-201", "CST-203", "ECT-201", "ECT-211", "HST-201"],
        "labs": ["AIP-211", "CSP-201", "ECP-201", "MMP-201"],
        "teacher_map": {}
    },
    {
        "name": "AIDE D",
        "semester": 3,
        "sem_type": "odd",
        "strength": 60,
        "auto_split": True,
        "lunch_period": 5,
        "subjects": ["AIT-201", "AIT-203", "AIT-205", "CST-207", "MAT-201", "HST-203"],
        "labs": ["CSP-207", "AIP-203", "AIP-205", "AIP-211"],
        "teacher_map": {}
    },
    {
        "name": "ECE C",
        "semester": 3,
        "sem_type": "odd",
        "strength": 90,
        "auto_split": True,
        "lunch_period": 5,
        "subjects": ["MAT-201", "ECT-201", "ECT-203", "ECT-205", "ECT-207", "CST-241"],
        "labs": ["AIP-211", "ECP-201", "MMP-201", "ECP-203", "CSP-241"],
        "teacher_map": {}
    },
    {
        "name": "YEAR 1 -A",
        "semester": 1,
        "sem_type": "odd",
        "strength": 120,
        "auto_split": True,
        "lunch_period": 4,
        "subjects": ["MAT-103", "AIT-101", "ECT-101", "HST-101", "CST-101"],
        "labs": ["CSP-101", "AIP-111", "ECP-101", "HSP-101"],
        "teacher_map": {}
    },
    {
        "name": "YEAR 1 -B",
        "semester": 1,
        "sem_type": "odd",
        "strength": 120,
        "auto_split": True,
        "lunch_period": 4,
        "subjects": ["MAT-103", "AIT-101", "ECT-101", "HST-101", "CST-101"],
        "labs": ["CSP-101", "AIP-111", "ECP-101", "HSP-101"],
        "teacher_map": {}
    },
    {
        "name": "YEAR 1 -C",
        "semester": 1,
        "sem_type": "odd",
        "strength": 90,
        "auto_split": True,
        "lunch_period": 4,
        "subjects": ["MAT-103", "AIT-101", "ECT-101", "HST-101", "CST-101"],
        "labs": ["CSP-101", "AIP-111", "ECP-101", "HSP-101"],
        "teacher_map": {}
    }
]
data["batches"] = unified_batches

# 3. Compile classes for solver
classes = []
for b in unified_batches:
    st = b["strength"]
    theory = b["subjects"]
    labs = b["labs"]
    lp = b["lunch_period"]
    sem = b["semester"]
    k = (st + 29) // 30
    sub_strength = min(30, (st + k - 1) // k)
    
    # Unified parent cohort for theory
    if theory:
        classes.append({
            "name": b["name"],
            "strength": st,
            "subjects": theory,
            "lunch_period": lp,
            "teacher_map": b.get("teacher_map", {}),
            "parent_class": None,
            "parent_batch": b["name"],
            "semester": sem
        })
    # Sections of 30 for lab slots
    for i in range(1, k + 1):
        classes.append({
            "name": f"{b['name']}{i}",
            "strength": sub_strength,
            "subjects": labs,
            "lunch_period": lp,
            "teacher_map": b.get("teacher_map", {}),
            "parent_class": b["name"],
            "parent_batch": b["name"],
            "sub_index": i,
            "semester": sem
        })

data["classes"] = classes

# 4. Save both files
with open("data/institutional_timetable_specification (1).json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

with open("data/institutional_timetable_specification.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Saved files successfully.")

# 5. Verify feasibility and solver
data_obj = load_from_dict(data)
feas = check_feasibility(data_obj)
print("Feasibility:")
for r in feas:
    print(f"  {r['name']}: {r['passed']}")

teacher_of = assign_teachers(data_obj)
sessions = build_sessions(data_obj, teacher_of)
domains = build_domains(data_obj, sessions)
res = solvers.run("Min-Conflicts", data=data_obj, sessions=sessions, domains=domains, time_limit=10.0)
ev = evaluate(data_obj, sessions, res.asg)
print(f"Solver result: success={res.success}, time={res.time_taken:.3f}s, hard clashes={ev.hard_total}, soft score={ev.soft_total}")

