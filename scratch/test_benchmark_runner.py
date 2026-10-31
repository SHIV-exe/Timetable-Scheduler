import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath("."))
from core.model import load_from_dict, assign_teachers, build_sessions, build_domains
from core.solvers import run
from core.evaluate import evaluate

with open("data/institutional_timetable_specification.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

data = load_from_dict(raw)
teacher_of = assign_teachers(data)
sessions = build_sessions(data, teacher_of)
domains = build_domains(data, sessions)

algos = [
    "Min-Conflicts",
    "Hill Climbing",
    "Simulated Annealing",
    "Backtracking + MRV + LCV + AC-3",
]

results = []
for algo in algos:
    t0 = time.time()
    res = run(algo=algo, data=data, sessions=sessions, domains=domains, seed=42, time_limit=3.0)
    rep = evaluate(data, sessions, res.asg)
    dt = round(time.time() - t0, 3)
    results.append({
        "Method": algo,
        "Success": res.success and rep.hard_total == 0,
        "Time (s)": dt,
        "Work": res.work,
        "Hard Clashes": rep.hard_total,
        "Soft Penalty": rep.soft_total,
    })
    print(f"Finished {algo}: Success={res.success}, Time={dt}s, Hard={rep.hard_total}")

print("All done!")

