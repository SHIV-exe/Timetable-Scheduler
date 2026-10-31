import os
import sys
import json
import time
import pandas as pd

sys.path.insert(0, os.path.abspath("."))
from core.model import load_from_dict, assign_teachers, build_sessions, build_domains
from core.solvers import run
from core.evaluate import evaluate

inst_path = "data/institutional_timetable_specification.json"
with open(inst_path, "r", encoding="utf-8") as f:
    raw = json.load(f)

data = load_from_dict(raw)
teacher_of = assign_teachers(data)
sessions = build_sessions(data, teacher_of)
domains = build_domains(data, sessions)

print(f"Benchmarking Institutional: {len(sessions)} sessions, {len(data.classes)} classes, {len(data.rooms)} rooms")

algos = [
    ("Min-Conflicts", 10.0),
    ("BT heuristics", 3.0),
    ("Hill Climbing", 3.0),
    ("Simulated Annealing", 4.0),
    ("Hybrid (BT + SA)", 4.0),
    ("BT baseline", 2.0),
]

inst_records = []
for algo_name, limit in algos:
    print(f"Testing {algo_name} (limit={limit}s)...", flush=True)
    t0 = time.perf_counter()
    res = run(algo=algo_name, data=data, sessions=sessions, domains=domains, seed=42, time_limit=limit)
    rep = evaluate(data, sessions, res.asg)
    elapsed = round(res.time_taken, 3)
    success = (res.success and rep.hard_total == 0)
    
    rec = {
        "Dataset": "institutional",
        "Method": algo_name,
        "Success Rate": "1/1" if success else "0/1",
        "Avg Time (s)": elapsed,
        "Std Time (s)": 0.0,
        "Avg Work (nodes/iters)": res.work,
        "Avg Hard Violations": rep.hard_total,
        "Avg Soft Penalty (valid runs)": rep.soft_total,
        "Hard Breakdown": dict(rep.hard),
        "Soft Breakdown": dict(rep.soft),
        "Output Summary": f"{'Clash-Free (0 Clashes)' if rep.hard_total == 0 else f'{rep.hard_total} Clashes'} · {res.work} iters · {elapsed}s"
    }
    inst_records.append(rec)
    print(f"  Result: Success={success}, Time={elapsed}s, Clashes={rep.hard_total}, Soft={rep.soft_total}")

os.makedirs("experiments/results", exist_ok=True)
json_path = "experiments/results/benchmark_runs.json"
existing_runs = {}
if os.path.exists(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            existing_runs = json.load(f)
    except Exception:
        existing_runs = {}

existing_runs["institutional"] = {
    "dataset": "institutional",
    "display_name": "Institutional Specification (7 Batches, 29 Classes)",
    "sessions_count": len(sessions),
    "classes_count": len(data.classes),
    "rooms_count": len(data.rooms),
    "teachers_count": len(data.teachers),
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "records": inst_records
}

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(existing_runs, f, indent=2)

print("Saved benchmark_runs.json successfully!")

