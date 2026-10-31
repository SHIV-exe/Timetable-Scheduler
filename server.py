"""FastAPI backend server for AI Timetable Scheduler.

Provides RESTful endpoints for validation, feasibility arithmetic, solver execution,
live constraint evaluation, conflict-free slot suggestions, and benchmark inspection.
Serves the editorial minimalist web application on port 8000.
"""

import json
import os
import sys
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.model import (
    load_from_dict,
    validate_raw_data,
    check_feasibility,
    assign_teachers,
    build_sessions,
    build_domains,
    get_template_dict,
)
from core.evaluate import evaluate
from core import solvers

app = FastAPI(title="Constraint Satisfaction Timetable Scheduler API")


class SolveRequest(BaseModel):
    algo: str
    data: Dict[str, Any]
    seed: int = 0
    time_limit: float = 30.0
    node_limit: int = 500_000


class EvaluateRequest(BaseModel):
    data: Dict[str, Any]
    asg: Dict[str, List[Any]]  # sid string -> [day, period, room]


class SuggestRequest(BaseModel):
    data: Dict[str, Any]
    asg: Dict[str, List[Any]]
    sid: int


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/api/dataset/{name}")
def get_dataset(name: str):
    name_clean = name.lower().strip()
    if name_clean in ("small", "large", "custom"):
        path = os.path.join(os.path.dirname(__file__), "data", f"{name_clean}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        if name_clean == "custom":
            return None
        raise HTTPException(status_code=404, detail=f"Dataset {name_clean}.json not found on disk.")
    elif name_clean in ("institutional", "institutional_specification", "institutional_timetable_specification"):
        candidates = [
            os.path.join(os.path.dirname(__file__), "data", "institutional_timetable_specification.json"),
            os.path.join(os.path.dirname(__file__), "data", "institutional_timetable_specification (1).json"),
        ]
        for c in candidates:
            if os.path.exists(c):
                with open(c, "r", encoding="utf-8") as f:
                    return json.load(f)
        raise HTTPException(status_code=404, detail="Institutional specification JSON not found.")
    elif name_clean == "template":
        return get_template_dict()
    raise HTTPException(status_code=400, detail="Dataset must be 'small', 'large', 'custom', 'institutional', or 'template'.")


@app.post("/api/dataset/custom")
def save_custom_dataset(raw: Dict[str, Any] = Body(...)):
    """Save custom configured timetable dataset to data/custom.json."""
    errors = validate_raw_data(raw)
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    custom_path = os.path.join(data_dir, "custom.json")
    with open(custom_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2)
    return {"saved": True, "valid": len(errors) == 0, "errors": errors}


@app.post("/api/validate")
def api_validate(raw: Dict[str, Any] = Body(...)):
    errors = validate_raw_data(raw)
    return {"valid": len(errors) == 0, "errors": errors}


@app.post("/api/feasibility")
def api_feasibility(raw: Dict[str, Any] = Body(...)):
    errors = validate_raw_data(raw)
    if errors:
        return {"valid": False, "errors": errors, "checks": []}
    data_obj = load_from_dict(raw)
    checks = check_feasibility(data_obj)
    all_passed = all(c["passed"] for c in checks)
    return {"valid": True, "feasible": all_passed, "checks": checks}


@app.post("/api/solve")
def api_solve(req: SolveRequest):
    errors = validate_raw_data(req.data)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    try:
        data_obj = load_from_dict(req.data)
        teacher_of = assign_teachers(data_obj)
        sessions = build_sessions(data_obj, teacher_of)
        domains = build_domains(data_obj, sessions)

        result = solvers.run(
            algo=req.algo,
            data=data_obj,
            sessions=sessions,
            domains=domains,
            seed=req.seed,
            time_limit=req.time_limit,
            node_limit=req.node_limit,
        )

        rep = evaluate(data_obj, sessions, result.asg)

        # Convert asg keys to int strings for JSON serialization
        ser_asg = {str(k): list(v) for k, v in result.asg.items()}
        ser_sessions = [
            {
                "sid": s.sid,
                "cls": s.cls,
                "subject": s.subject,
                "teacher": s.teacher,
                "kind": s.kind,
                "length": s.length,
                "idx": s.idx,
            }
            for s in sessions
        ]

        return {
            "success": result.success,
            "work": result.work,
            "time_taken": round(result.time_taken, 4),
            "asg": ser_asg,
            "sessions": ser_sessions,
            "report": rep.to_dict(),
            "trace": result.trace[:300] if result.trace else [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/evaluate")
def api_evaluate(req: EvaluateRequest):
    errors = validate_raw_data(req.data)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    data_obj = load_from_dict(req.data)
    teacher_of = assign_teachers(data_obj)
    sessions = build_sessions(data_obj, teacher_of)

    parsed_asg = {
        int(k): (int(v[0]), int(v[1]), str(v[2]))
        for k, v in req.asg.items()
    }

    rep = evaluate(data_obj, sessions, parsed_asg)
    return rep.to_dict()


@app.post("/api/suggest")
def api_suggest(req: SuggestRequest):
    """Find values in session's domain that create 0 new hard conflicts."""
    data_obj = load_from_dict(req.data)
    teacher_of = assign_teachers(data_obj)
    sessions = build_sessions(data_obj, teacher_of)
    domains = build_domains(data_obj, sessions)

    target_session = next((s for s in sessions if s.sid == req.sid), None)
    if not target_session:
        raise HTTPException(status_code=404, detail="Session ID not found")

    base_asg = {int(k): (int(v[0]), int(v[1]), str(v[2])) for k, v in req.asg.items()}
    base_rep = evaluate(data_obj, sessions, base_asg)

    dom = domains[req.sid]
    suggestions = []

    for v in dom:
        trial_asg = dict(base_asg)
        trial_asg[req.sid] = v
        trial_rep = evaluate(data_obj, sessions, trial_asg)

        # Check if hard violations increased
        if trial_rep.hard_total <= base_rep.hard_total:
            suggestions.append({
                "day_idx": v[0],
                "day_name": data_obj.days[v[0]],
                "start_period": v[1] + 1,  # 1-indexed for display
                "room": v[2],
                "hard_violations": trial_rep.hard_total,
                "soft_penalty": trial_rep.soft_total,
                "cost": trial_rep.cost,
            })

    # Sort suggestions by lowest soft penalty
    suggestions.sort(key=lambda x: (x["hard_violations"], x["soft_penalty"]))
    return {"suggestions": suggestions[:15]}


class BenchmarkRunRequest(BaseModel):
    data: Optional[Dict[str, Any]] = None
    dataset_name: Optional[str] = None
    dataset_key: Optional[str] = None
    algorithms: Optional[List[str]] = None
    time_limit: Optional[float] = 5.0
    seed: Optional[int] = 42


@app.post("/api/benchmark/run")
def api_benchmark_run(req: BenchmarkRunRequest):
    """Execute benchmark across algorithms on any dataset and return comparative outputs."""
    raw_data = req.data
    dataset_label = "Custom / Active Dataset"

    ds_name = req.dataset_name or req.dataset_key
    if not raw_data and ds_name:
        name_clean = ds_name.lower().strip()
        dataset_label = f"{name_clean.capitalize()} Dataset"
        candidates = [
            os.path.join(os.path.dirname(__file__), "data", f"{name_clean}.json"),
            os.path.join(os.path.dirname(__file__), "data", "institutional_timetable_specification.json"),
            os.path.join(os.path.dirname(__file__), "data", "institutional_timetable_specification (1).json"),
        ]
        for c in candidates:
            if os.path.exists(c):
                with open(c, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                break

    if not raw_data:
        c_path = os.path.join(os.path.dirname(__file__), "data", "custom.json")
        if os.path.exists(c_path):
            with open(c_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        else:
            raise HTTPException(status_code=400, detail="No dataset provided or found to benchmark.")

    try:
        data_obj = load_from_dict(raw_data)
        teacher_of = assign_teachers(data_obj)
        sessions = build_sessions(data_obj, teacher_of)
        domains = build_domains(data_obj, sessions)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to prepare dataset for benchmark: {str(e)}")

    algos_to_test = req.algorithms or [
        "Min-Conflicts",
        "BT heuristics",
        "Hill Climbing",
        "Simulated Annealing",
        "Hybrid (BT + SA)",
        "BT baseline",
    ]

    time_limit = float(req.time_limit or 5.0)
    seed = int(req.seed if req.seed is not None else 42)
    num_sessions = len(sessions)
    records = []

    for algo in algos_to_test:
        limit = time_limit
        if "baseline" in algo.lower() and num_sessions > 40:
            limit = min(2.0, time_limit)

        try:
            res = solvers.run(
                algo=algo,
                data=data_obj,
                sessions=sessions,
                domains=domains,
                seed=seed,
                time_limit=limit,
            )
            rep = evaluate(data_obj, sessions, res.asg)
            success = bool(res.success and rep.hard_total == 0)
            elapsed = round(res.time_taken, 3)

            rec = {
                "Dataset": dataset_label,
                "Method": algo,
                "Success": success,
                "Success Rate": "1/1" if success else "0/1",
                "Avg Time (s)": elapsed,
                "Std Time (s)": 0.0,
                "Avg Work (nodes/iters)": res.work,
                "Avg Hard Violations": rep.hard_total,
                "Avg Soft Penalty (valid runs)": rep.soft_total,
                "Hard Breakdown": dict(rep.hard),
                "Soft Breakdown": dict(rep.soft),
                "Output Summary": f"{'Clash-Free (0 Clashes)' if rep.hard_total == 0 else f'{rep.hard_total} Clashes'} · {res.work} iters · {elapsed}s",
            }
            records.append(rec)
        except Exception as err:
            records.append({
                "Dataset": dataset_label,
                "Method": algo,
                "Success": False,
                "Success Rate": "0/1",
                "Avg Time (s)": 0.0,
                "Std Time (s)": 0.0,
                "Avg Work (nodes/iters)": 0,
                "Avg Hard Violations": -1,
                "Avg Soft Penalty (valid runs)": -1,
                "Hard Breakdown": {},
                "Soft Breakdown": {},
                "Output Summary": f"Error: {str(err)}",
            })

    results_dir = os.path.join(os.path.dirname(__file__), "experiments", "results")
    os.makedirs(results_dir, exist_ok=True)
    json_path = os.path.join(results_dir, "benchmark_runs.json")
    saved_runs = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                saved_runs = json.load(f)
        except Exception:
            saved_runs = {}

    run_key = f"{dataset_label.lower().replace(' ', '_')}_{int(time.time())}"
    saved_runs[run_key] = {
        "dataset": dataset_label,
        "display_name": f"{dataset_label} ({len(sessions)} Sessions, {len(data_obj.classes)} Classes)",
        "sessions_count": len(sessions),
        "classes_count": len(data_obj.classes),
        "rooms_count": len(data_obj.rooms),
        "teachers_count": len(data_obj.teachers),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "records": records,
    }

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(saved_runs, f, indent=2)
    except Exception:
        pass

    return {
        "dataset": dataset_label,
        "sessions_count": len(sessions),
        "classes_count": len(data_obj.classes),
        "rooms_count": len(data_obj.rooms),
        "teachers_count": len(data_obj.teachers),
        "records": records,
        "run_key": run_key,
    }


@app.get("/api/benchmarks")
def api_benchmarks():
    summary_path = os.path.join(os.path.dirname(__file__), "experiments", "results", "summary.csv")
    raw_path = os.path.join(os.path.dirname(__file__), "experiments", "results", "raw.csv")
    runs_path = os.path.join(os.path.dirname(__file__), "experiments", "results", "benchmark_runs.json")

    summary_data = []
    if os.path.exists(summary_path):
        try:
            import pandas as pd
            df = pd.read_csv(summary_path)
            summary_data = df.to_dict(orient="records")
        except Exception:
            pass

    saved_runs = {}
    if os.path.exists(runs_path):
        try:
            with open(runs_path, "r", encoding="utf-8") as f:
                saved_runs = json.load(f)
        except Exception:
            saved_runs = {}

    return {
        "summary": summary_data,
        "saved_runs": saved_runs,
        "has_raw": os.path.exists(raw_path),
    }


# Mount static files for the single page web application
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
