# Academic Technical Report: Constraint Satisfaction Problem (CSP) Timetable Optimization

**Project Title:** AI Timetable Scheduler: Systematic vs Local Search in Academic Timetabling  
**Course Code / Module:** CS401 / Artificial Intelligence  
**Date:** October 25, 2026  
**Repository:** `timetable-scheduler/`  

---

## Executive Summary
This report presents the mathematical formulation, algorithmic implementation, empirical benchmarking, and usability design of an automated academic timetable scheduling system. Timetabling is modeled as a Constraint Satisfaction Problem (CSP). We implement and contrast two primary paradigms: **Systematic Depth-First Backtracking** enhanced by Minimum Remaining Values (MRV), Degree heuristic, Forward Checking (FC), and Symmetry Breaking; and **Stochastic Local Search** utilizing Min-Conflicts with random walk plateau escapes, complemented by **Simulated Annealing**, **Hill Climbing**, and a **Hybrid (BT + SA)** pipeline. 

Empirical experiments across 120 seeded runs on both small (45 sessions) and large (144 sessions) college datasets demonstrate that while heuristic backtracking achieves complete guarantees with dramatic search-space reduction (reducing node expansions by 99.1%), Min-Conflicts operates with superior speed on large instances (resolving conflicts in 0.03 seconds). Furthermore, Simulated Annealing and the Hybrid solver reduce schedule ergonomics penalties (student free periods and faculty fatigue) by more than 84% compared to baseline solutions.

---

## 1. Problem Formulation (Modeling & Theory)

### 1.1 Mathematical Representation as a CSP
A Constraint Satisfaction Problem is formally defined as a triple $\langle X, D, C \rangle$:
1. $X = \{s_0, s_1, \dots, s_{N-1}\}$: A finite set of variables, where each variable represents an individual teaching session to be scheduled.
2. $D = \{D(s_0), D(s_1), \dots, D(s_{N-1})\}$: A collection of finite domains specifying all permissible value assignments for each variable.
3. $C = \{C_1, C_2, \dots, C_M\}$: A set of constraints specifying allowable combinations of variable assignments.

### 1.2 Variables ($X$)
To handle multi-period laboratory courses and varying weekly subject frequencies:
- A theory course with $h$ weekly lecture hours is decomposed into $h$ distinct 1-period variables: $(c, \text{sub}, k)$ for $k \in \{0, \dots, h-1\}$.
- A laboratory course with $h$ weekly hours and fixed block length $L$ (default $L = 2$) is decomposed into $h/L$ variables, each representing a continuous block of $L$ periods: $(c, \text{sub}, k)$ for $k \in \{0, \dots, h/L - 1\}$.
- Each session is tied to one class cohort $c$, one subject code $\text{sub}$, and one pre-assigned faculty instructor $t$.

### 1.3 Domains ($D$)
A value assigned to a session variable is a 3-tuple:
$$v = (\text{day}, \text{start\_period}, \text{room}) \in \{0, \dots, |\text{Days}|-1\} \times \{0, \dots, P - L\} \times \text{Rooms}$$
Crucially, unary constraints are pruned upfront during domain generation, eliminating invalid timeslots before search begins:
1. **Room Classification & Capacity (H4, H5):** For a class of strength $S_c$ and session kind $K \in \{\text{theory}, \text{lab}\}$, only rooms where $\text{room.kind} == K$ and $\text{room.capacity} \ge S_c$ are admitted into the domain.
2. **Faculty Availability (H6):** For instructor $t$, any slot $(d, p + k)$ that intersects $t.\text{unavailable}$ is excluded.
3. **Cohort Schedule Structure (H9):** Any slot $(d, p + k)$ coinciding with designated university break periods or the class's assigned lunch period is excluded.

By filtering unary constraints prior to search, the solver never evaluates states that violate room type, room capacity, instructor unavailability, or institutional breaks.

### 1.4 Hard vs. Soft Constraints
- **Hard Constraints ($H$):** Mandatory conditions defining a feasible timetable. Any violation renders the timetable physically invalid.
  - **H1 (Faculty Clashing):** A teacher cannot teach two classes simultaneously.
  - **H2 (Cohort Clashing):** A student cohort cannot attend two sessions simultaneously.
  - **H3 (Facility Clashing):** A room cannot host two classes simultaneously.
  - **H4 (Capacity):** Room size must accommodate student cohort size.
  - **H5 (Room Type):** Laboratories require lab facilities; lectures require lecture halls.
  - **H6 (Teacher Availability):** Teachers cannot be assigned during unavailable slots.
  - **H7 (Curriculum Fulfillment):** Exactly the required weekly hours must be scheduled.
  - **H8 (Workload Cap):** No teacher may exceed their contract maximum weekly hours.
  - **H9 (Institutional Breaks):** No class may be scheduled during breaks or lunch.
- **Soft Constraints ($S$):** Optimization preferences defining an ergonomic timetable.
  - **S1 (Student Idle Gaps, $W=2$):** Penalizes empty teachable periods between a cohort's first and last class of the day. Breaks and lunch periods are excluded from gap counting.
  - **S2 (Subject Dispersion, $W=3$):** Penalizes scheduling multiple theory sessions of the same subject on the same day for a class.
  - **S3 (Laboratory Cohesion):** Satisfied structurally by modeling laboratory sessions as atomic 2-period blocks.
  - **S4 (Faculty Period Preferences, $W=1$):** Penalizes placing a session in a period that a teacher preferred to avoid.
  - **S5 (Faculty Fatigue Mitigation, $W=2$):** Penalizes back-to-back lecture runs exceeding 2 consecutive hours on a single day.

---

## 2. Shared Violation Counter & Cost Function (Section 5)

A central requirement of the system architecture is the single source of truth for schedule evaluation (`core/evaluate.py`). Both systematic and local search algorithms, the manual editor, and the experiment benchmarks rely on this single function:

$$\text{Cost} = 1000 \times \left(\sum_{i=1}^9 H_i + \text{RANGE}\right) + \sum_{j \in \{1, 2, 4, 5\}} W_j \cdot S_j$$

### Why $W_{\text{hard}} = 1000$?
The weight of 1000 guarantees mathematical dominance: a single hard clash incurs a penalty greater than all potential soft penalties combined across the entire institution. This ensures that optimization algorithms never trade a physical clash (e.g., placing two classes in one room) for an aesthetic benefit (e.g., avoiding an afternoon gap).

---

## 3. Algorithmic Implementations & Design Decisions

### 3.1 Systematic Search: Backtracking CSP (`core/backtracking.py`)
1. **Baseline Backtracking:** Depth-first recursive assignment with fixed chronological variable ordering and fixed value ordering. Serves as our unoptimized control baseline.
2. **Minimum Remaining Values (MRV):** Prioritizes the variable with the smallest current domain size ($|D(s)|$). MRV embodies the "fail-first" principle, pruning failing branches at the top of the search tree rather than deep in recursion.
3. **Degree Heuristic:** Breaks ties among variables with equal MRV domain sizes by selecting the variable involved in the greatest number of constraints with unassigned variables.
4. **Forward Checking (FC):** When variable $s$ is assigned value $v$, FC iterates over unassigned variables and removes any value $v'$ that directly clashes with $(s, v)$. If any unassigned variable's domain becomes empty (wipeout), the assignment is immediately rejected and backtracked, detecting dead ends before descending.
5. **Symmetry Breaking:** Theory sessions of the same subject for the same class are interchangeable. By enforcing that session $k$ must be scheduled chronologically after session $k-1$, we eliminate redundant permutations of identical schedules.

### 3.2 Local Search: Min-Conflicts (`core/minconflicts.py`)
Min-Conflicts operates over complete assignments, iteratively repairing conflicts:
1. **Incremental State Counter ($O(1)$ Lookup):** Testing every session against all others is $O(N^2)$. Our `State` class maintains three hash tables (`self.T`, `self.C`, `self.R`) counting occupancies per (teacher, slot), (class, slot), and (room, slot). Conflict evaluation is reduced to $O(L)$ lookups per candidate value.
2. **Initial Assignment:** Constructed via a randomized greedy pass where sessions are placed in minimum-conflict slots.
3. **Variable Selection:** Chosen uniformly at random from the set of sessions currently involved in at least one conflict ($H_1, H_2, H_3$).
4. **Value Selection:** The domain value that minimizes total conflicts is selected. Ties are broken uniformly at random to prevent cyclic loops.
5. **Plateau Escapes:**
   - **Random Walk:** With probability $p_{\text{walk}} = 0.05$, the algorithm chooses a random domain value instead of the greedy choice.
   - **Stagnant Restarts:** If no improvement is observed after 2,000 iterations, the assignment restarts from a fresh greedy configuration (up to 5 restarts).

### 3.3 Optimization Solvers: Simulated Annealing & Hybrid
1. **Simulated Annealing (SA):** Employs two neighbourhood moves: single-session relocation (50%) and pairwise compatible swaps (50%). Temperature is initialized using uphill sampling ($p_0 = 0.8$) and cools geometrically ($T_{k+1} = 0.95 \cdot T_k$) every $L$ steps.
2. **Hybrid (BT + SA):** Employs Backtracking (or Min-Conflicts) to reach a zero-hard-violation feasible solution, and then activates Simulated Annealing exclusively for soft-constraint minimization.

---

## 4. Empirical Evaluation & Experimental Findings

### 4.1 Benchmark Summary Table
Across 10 randomized seeds ($0 \dots 9$) per configuration:

| Dataset | Method | Success Rate | Avg Time (s) | Work (Nodes/Iters) | Hard Clashes | Avg Soft Penalty |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Small** (45 sessions) | BT baseline | 10/10 | 0.04s | 6,559 nodes | 0.0 | 61.1 |
| **Small** | BT heuristics | 10/10 | 0.02s | **58 nodes** | 0.0 | 64.3 |
| **Small** | Min-Conflicts | 10/10 | 0.00s | **1 iter** | 0.0 | 62.8 |
| **Small** | Simulated Annealing | 10/10 | 1.59s | 9,621 steps | 0.0 | **2.8** |
| **Small** | Hill Climbing | 10/10 | 0.38s | 2,443 steps | 0.0 | 4.3 |
| **Small** | Hybrid (BT + SA) | 10/10 | 1.56s | 9,643 steps | 0.0 | **2.6** |
| **Large** (144 sessions) | BT baseline | 7/10 | 0.08s | 6,733 nodes | 43.2 (timeouts) | 216.6 |
| **Large** | BT heuristics | 10/10 | 0.57s | **219 nodes** | 0.0 | 227.0 |
| **Large** | Min-Conflicts | 10/10 | **0.03s** | **3 iters** | 0.0 | 213.8 |
| **Large** | Simulated Annealing | 10/10 | 12.69s | 31,478 steps | 0.0 | **34.7** |
| **Large** | Hill Climbing | 9/10 | 1.21s | 2,990 steps | 0.1 | 96.6 |
| **Large** | Hybrid (BT + SA) | 10/10 | 13.43s | 31,410 steps | 0.0 | **39.9** |

---

## 5. Answers to Core Analytical Questions (Section 11.5)

### 1. Which method was faster?
- On the **Small Dataset**, heuristic backtracking required an average of only **58 node explorations**, compared to 6,559 for baseline backtracking—a **99.1% search space reduction**.
- On the **Large Dataset**, **Min-Conflicts** was the fastest method, converging to zero hard conflicts in an average of **0.03 seconds** and **3 iterations**. Plain backtracking timed out on 30% of runs, while heuristic backtracking completed in 0.57s.

### 2. Which gave better soft-constraint quality?
- Systematic solvers (Backtracking) return the first valid leaf encountered in the tree, ignoring soft penalties during search. Consequently, Backtracking soft penalties averaged 64.3 (small) and 227.0 (large).
- **Simulated Annealing** and the **Hybrid Solver** produced the highest quality schedules, reducing the soft penalty score from 227.0 down to **34.7** on the large dataset (an **84.7% improvement** in educational timetable ergonomics).

### 3. What happens as the problem grows?
- Baseline backtracking scales exponentially $O(d^N)$ and becomes completely unviable on large institutional inputs.
- Heuristic improvements (MRV + FC + Symmetry) flatten the combinatorial tree, allowing systematic search to solve 144 variables in 219 nodes.
- Min-Conflicts scales near-linearly when resource utilization is moderate (~70%), but requires random walk and restart mechanisms to escape plateaus when utilization exceeds 90%.

### 4. When would you use each method?
- **Backtracking with Heuristics:** When an exact mathematical guarantee or a proof of unsatisfiability is strictly required.
- **Min-Conflicts:** When an enterprise system requires near-instant schedule generation for large cohorts.
- **Hybrid Solver:** The gold standard for production deployment, guaranteeing zero hard clashes while optimizing faculty workload and student learning schedules.

---

## 6. Limitations & Future Extensions
1. **Greedy Teacher Assignment:** Teacher assignment is performed upfront via greedy heuristic matching. While effective for balanced loads, teacher assignment is fundamentally a network flow problem and may fail on edge cases where a global bipartite matching exists. Future versions can incorporate maximum flow or Hungarian matching.
2. **Fixed Class Lunch Period:** Each class has one fixed lunch period across all days. Supporting flexible lunch intervals would improve search flexibility.
3. **Multi-Section Faculty Preferences:** Modeling specific room preferences per instructor (e.g., smart board requirements).

---

## 7. Deliverable Checklist (Section 12.6)
- [x] Data entry supports forms, JSON, and CSV with validation and feasibility reports.
- [x] Solvable Small (3 classes, 6 teachers) and Large (8 classes, 15 teachers) datasets created and verified.
- [x] Single source of truth `evaluate()` covering H1–H9 and S1, S2, S4, S5 with 100% test coverage.
- [x] Plain backtracking baseline plus MRV, Degree, Forward Checking, and Symmetry breaking.
- [x] Min-Conflicts with incremental $O(1)$ State counter, random walk, and restarts.
- [x] Bonus algorithms: Simulated Annealing, Hill Climbing, and Hybrid solver implemented.
- [x] Web application featuring 5 tabs, faux-OS window chrome, live manual editing conflict flags, and zero-conflict suggestions.
- [x] Empirical benchmarks run across 120 seeded executions with raw CSVs, summary tables, and convergence trace graphics.
