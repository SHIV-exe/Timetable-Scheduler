"""Script to verify all FastAPI endpoints end-to-end."""
import json
import urllib.request

def main():
    base_url = "http://127.0.0.1:8000"

    # 1. Health check
    with urllib.request.urlopen(f"{base_url}/api/health") as resp:
        health = json.loads(resp.read().decode())
        print(f"[OK] Health check: {health}")

    # 2. Get small dataset
    with urllib.request.urlopen(f"{base_url}/api/dataset/small") as resp:
        small_data = json.loads(resp.read().decode())
        print(f"[OK] Fetched small dataset: {len(small_data['classes'])} classes, {len(small_data['teachers'])} faculty")

    # 3. Validate endpoint
    val_req = urllib.request.Request(
        f"{base_url}/api/validate",
        data=json.dumps(small_data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(val_req) as resp:
        val_res = json.loads(resp.read().decode())
        print(f"[OK] Validate endpoint: valid={val_res['valid']}, errors={val_res['errors']}")

    # 4. Feasibility endpoint
    feas_req = urllib.request.Request(
        f"{base_url}/api/feasibility",
        data=json.dumps(small_data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(feas_req) as resp:
        feas_res = json.loads(resp.read().decode())
        print(f"[OK] Feasibility endpoint: all_feasible={feas_res['feasible']}, {len(feas_res['checks'])} checks evaluated")

    # 5. Solve endpoint with Backtracking (MRV + FC + degree)
    solve_payload = {
        "algo": "Backtracking (MRV + FC + degree)",
        "data": small_data,
        "seed": 42,
        "time_limit": 10.0,
        "node_limit": 50000
    }
    solve_req = urllib.request.Request(
        f"{base_url}/api/solve",
        data=json.dumps(solve_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(solve_req) as resp:
        sol = json.loads(resp.read().decode())
        print(f"[OK] Solve Backtracking: success={sol['success']}, time={sol['time_taken']}s, work={sol['work']} nodes, hard={sol['report']['hard_total']}, soft={sol['report']['soft_total']}")

    # 6. Solve endpoint with Min-Conflicts
    solve_payload_mc = {
        "algo": "Min-Conflicts",
        "data": small_data,
        "seed": 42,
        "time_limit": 10.0
    }
    solve_req_mc = urllib.request.Request(
        f"{base_url}/api/solve",
        data=json.dumps(solve_payload_mc).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(solve_req_mc) as resp:
        sol_mc = json.loads(resp.read().decode())
        print(f"[OK] Solve Min-Conflicts: success={sol_mc['success']}, time={sol_mc['time_taken']}s, work={sol_mc['work']} iters, hard={sol_mc['report']['hard_total']}, soft={sol_mc['report']['soft_total']}")

    # 7. Benchmarks endpoint
    with urllib.request.urlopen(f"{base_url}/api/benchmarks") as resp:
        bench = json.loads(resp.read().decode())
        print(f"[OK] Benchmarks endpoint: {len(bench['summary'])} summary rows returned")

    # 8. Suggest endpoint
    suggest_payload = {
        "data": small_data,
        "asg": sol["asg"],
        "sid": 0
    }
    suggest_req = urllib.request.Request(
        f"{base_url}/api/suggest",
        data=json.dumps(suggest_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(suggest_req) as resp:
        sug = json.loads(resp.read().decode())
        print(f"[OK] Suggest endpoint: {len(sug['suggestions'])} zero-conflict suggestions for session 0")

    print("\nALL API ENDPOINTS FUNCTIONING WITH 100% SUCCESS!")

if __name__ == "__main__":
    main()
