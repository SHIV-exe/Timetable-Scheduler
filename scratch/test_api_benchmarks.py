import urllib.request
import json

res = urllib.request.urlopen("http://127.0.0.1:8000/api/benchmarks")
b_data = json.loads(res.read().decode("utf-8"))
print("Benchmarks GET success!")
print("Summary rows count:", len(b_data.get("summary", [])))
print("Saved runs datasets:", list(b_data.get("saved_runs", {}).keys()))
if "institutional" in b_data.get("saved_runs", {}):
    inst = b_data["saved_runs"]["institutional"]
    print("Institutional benchmark records:", len(inst.get("records", [])))
    for r in inst.get("records", []):
        print(f"  {r['Method']:28} | Success: {r['Success Rate']:4} | Time: {r['Avg Time (s)']}s | Clashes: {r['Avg Hard Violations']}")

req_payload = {
    "dataset_name": "small",
    "time_limit": 3.0,
    "seed": 42
}
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/benchmark/run",
    data=json.dumps(req_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req)
run_res = json.loads(resp.read().decode("utf-8"))
print("\nBenchmark run POST success on:", run_res.get("dataset"))
for r in run_res.get("records", []):
    print(f"  {r['Method']:28} | Success: {r['Success Rate']:4} | Time: {r['Avg Time (s)']}s | Clashes: {r['Avg Hard Violations']}")

