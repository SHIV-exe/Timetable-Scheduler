# Experimental Evaluation & Algorithmic Analysis (Section 11)

This report presents empirical findings from 120 benchmark executions across 6 algorithmic configurations on both standardized college datasets over 10 randomized seeds (0 to 9).

## 1. Benchmark Results Summary Table

### Small Dataset (3 Classes, 6 Teachers, 4 Rooms, 5x6 Grid, 45 Sessions)
| Dataset | Method | Success Rate | Avg Time (s) | Std Time (s) | Avg Work (nodes/iters) | Avg Hard Violations | Avg Soft Penalty (valid runs) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| small | BT baseline | 10/10 | 0.04 | 0.11 | 6559 | 0.0 | 61.1 |
| small | BT heuristics | 10/10 | 0.02 | 0.01 | 58 | 0.0 | 64.3 |
| small | Min-Conflicts | 10/10 | 0.0 | 0.0 | 1 | 0.0 | 62.8 |
| small | Simulated Annealing | 10/10 | 1.59 | 0.11 | 9621 | 0.0 | 2.8 |
| small | Hill Climbing | 10/10 | 0.38 | 0.08 | 2443 | 0.0 | 4.3 |
| small | Hybrid (BT + SA) | 10/10 | 1.56 | 0.12 | 9643 | 0.0 | 2.6 |

### Large Dataset (8 Classes, 15 Teachers, 8 Rooms, 5x7 Grid, 144 Sessions)
| Dataset | Method | Success Rate | Avg Time (s) | Std Time (s) | Avg Work (nodes/iters) | Avg Hard Violations | Avg Soft Penalty (valid runs) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| large | BT baseline | 7/10 | 0.08 | 0.11 | 6733 | 43.2 | 216.6 |
| large | BT heuristics | 10/10 | 0.57 | 0.09 | 219 | 0.0 | 227.0 |
| large | Min-Conflicts | 10/10 | 0.03 | 0.0 | 3 | 0.0 | 213.8 |
| large | Simulated Annealing | 10/10 | 12.69 | 0.57 | 31478 | 0.0 | 34.7 |
| large | Hill Climbing | 9/10 | 1.21 | 0.1 | 2990 | 0.1 | 96.6 |
| large | Hybrid (BT + SA) | 10/10 | 13.43 | 0.93 | 31410 | 0.0 | 39.9 |

---

## 2. Comprehensive Analysis (Section 11.5)

### Q1: Which method was faster?
- On the **Small Dataset**, **Backtracking with Heuristics** and **Min-Conflicts** were practically instantaneous. Heuristic backtracking reduced the search tree from an average of 6,559 node attempts down to merely **58 nodes** (a 99.1% reduction in search space).
- On the **Large Dataset** (144 sessions), **Min-Conflicts** was the fastest method, resolving all conflicts in an average of **0.03 seconds** and **3 iterations**.
- **Plain Backtracking** suffered severely from the curse of dimensionality on the large dataset, timing out on 3 out of 10 runs and averaging 43.2 unresolved hard clashes when stopped. In stark contrast, Backtracking with heuristics maintained a 100% success rate in 0.57s and just 219 nodes.

### Q2: Which gave better soft-constraint quality?
- Backtracking is a systematic feasibility search that halts upon discovering the first zero-violation assignment. Because it does not optimize soft preferences during placement, its average soft penalty score was 64.3 on small and 227.0 on large.
- **Simulated Annealing** and the **Hybrid Solver (BT + SA)** produced the highest quality timetables. Simulated Annealing lowered the soft penalty from 61.1 down to **2.8** on the small dataset, and from 227.0 down to **34.7** on the large dataset (an 84.7% improvement in timetable quality).
- Hill Climbing improved soft score (4.3 on small, 96.6 on large), but frequently became trapped in local minima compared to Simulated Annealing which escaped via Metropolis acceptance.

### Q3: What happens as the problem grows?
- Plain Backtracking grows exponentially O(d^n), quickly rendering unguided systematic search intractable.
- Heuristic improvements (MRV + Forward Checking + Degree + Symmetry Breaking) constrain the branching factor drastically, allowing systematic search to scale to 144 sessions with only 219 nodes expanded.
- Min-Conflicts scales near-linearly for moderately constrained problems (~70% resource utilization) due to O(1) state lookup, but requires random walk (p=0.05) and plateau restarts to avoid cyclic traps.

### Q4: When would you use each method?
1. **Backtracking with Heuristics**: When mathematical proof of satisfiability or unsatisfiability is strictly required, or when scheduling highly constrained departments.
2. **Min-Conflicts**: When large, complex schedules must be synthesized in real-time or within seconds.
3. **Hybrid (BT/MC + Simulated Annealing)**: The recommended production standard for institutional deployment, providing both guaranteed zero hard conflicts and exceptional schedule ergonomics.
