import json
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from core.model import load_from_dict, check_feasibility, assign_teachers, build_sessions, build_domains
from core.evaluate import evaluate
from core import solvers

raw = json.load(open("data/institutional_timetable_specification (1).json", encoding="utf-8"))

# Ensure humanities teachers can co-teach HSP-101 and HST-101 and load is sufficient
for t in raw["teachers"]:
    if t["name"] in ("Dr Aditi Gaur", "Dr. Ankita Birla", "Dr. Adarsh Kumar"):
        t["max_load"] = 20
        if "HSP-101" not in t["subjects"]:
            t["subjects"].append("HSP-101")
        if "HST-101" not in t["subjects"]:
            t["subjects"].append("HST-101")

# Compile classes exactly as app.js compileSolverData does
classes = []
for b in raw["batches"]:
    strength = b["strength"]
    theory = b.get("subjects", [])
    labs = b.get("labs", [])
    lp = b.get("lunch_period", 5)
    k = (strength + 29) // 30
    sub_strength = min(30, (strength + k - 1) // k)
    if theory:
        classes.append({
            "name": b["name"],
            "strength": strength,
            "subjects": theory,
            "lunch_period": lp,
            "teacher_map": b.get("teacher_map", {}),
            "parent_class": None,
            "parent_batch": b["name"],
            "semester": b.get("semester", 1)
        })
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
            "semester": b.get("semester", 1)
        })

print(f"Compiled {len(classes)} classes from {len(raw['batches'])} batches.")
raw_compiled = dict(raw)
raw_compiled["classes"] = classes

data_obj = load_from_dict(raw_compiled)
feas = check_feasibility(data_obj)
print("Feasibility results:")
for f in feas:
    print(f"  {f['name']}: passed={f['passed']}, {f['detail']}")

print("\nAssigning teachers and building sessions...")
teacher_of = assign_teachers(data_obj)
sessions = build_sessions(data_obj, teacher_of)
domains = build_domains(data_obj, sessions)
print(f"Total sessions: {len(sessions)}")

print("\nRunning Min-Conflicts solver (time_limit=10s)...")
res = solvers.run("Min-Conflicts", data=data_obj, sessions=sessions, domains=domains, time_limit=10.0)
ev = evaluate(data_obj, sessions, res.asg)
print("Success:", res.success)
print("Work iterations:", res.work)
print("Time taken:", res.time_taken)
print("Hard clashes:", ev.hard_total)
print("Soft score:", ev.soft_total)
