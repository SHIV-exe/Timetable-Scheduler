# AI Timetable Scheduler: Constraint Satisfaction Problem (CSP)

A complete, production-grade academic scheduling engine that formulates college timetabling as a Constraint Satisfaction Problem (CSP), solving it via systematic search (**Backtracking with MRV, Degree, Forward Checking, and Symmetry Breaking**) and stochastic local repair (**Min-Conflicts Local Search**, **Simulated Annealing**, **Hill Climbing**, and **Hybrid Chaining**).

Built according to the **Premium Utilitarian Minimalism & Editorial UI Protocol** (warm bone palette `#F7F6F3`, high typographic contrast with serif headings, flat bento grids, 1px `#EAEAEA` borders, muted pastels, zero emojis, zero heavy drop shadows).

---

## 1. System Architecture

The repository enforces a strict separation between mathematical modeling, algorithmic search, and presentation layers:

```
timetable-scheduler/
├── app.py                      # Streamlit UI (5-tab interface, imports only from core/)
├── server.py                   # FastAPI server serving the editorial minimalist UI
├── static/                     # Premium Utilitarian Minimalism web interface
│   ├── index.html              # Document-style UI with faux-OS chrome & bento grids
│   ├── styles.css              # Bespoke vanilla CSS tokens, Instrument Serif, Geist Mono
│   └── app.js                  # Client controller with live differential evaluation
├── config.py                   # HARD_W = 1000, soft weights W, default search limits
├── core/                       # Independent algorithm and data library
│   ├── model.py                # Dataclasses, validation, feasibility check, domain builder
│   ├── evaluate.py             # evaluate(), Report: single source of truth for scoring
│   ├── backtracking.py         # plain_bt, BTSolver (MRV, Degree, FC, LCV, Symmetry), ac3
│   ├── minconflicts.py         # State (O(1) incremental counter), greedy_init, min_conflicts
│   ├── annealing.py            # propose, estimate_T0, anneal, hill_climb
│   └── solvers.py              # solvers.run(...) unified dispatcher -> Result
├── data/                       # Standardized verified benchmarks (solvable, zero hard clashing)
│   ├── small.json              # 3 classes, 6 teachers, 4 rooms, 5×6 grid (45 sessions)
│   └── large.json              # 8 classes, 15 teachers, 8 rooms, 5×7 grid (144 sessions)
├── experiments/                # Empirical benchmarking suite
│   ├── make_datasets.py        # Seeded generator & feasibility validator for datasets
│   ├── run_experiments.py      # Automated 120-run benchmark across 10 random seeds
│   └── results/                # CSV tables, SVG convergence plots, and analytical markdown
│       ├── raw.csv             # Complete raw records across all 120 runs
│       ├── summary.csv         # Aggregated means, standard deviations, and success rates
│       ├── mc_trace.svg        # Min-Conflicts logarithmic cost vs iterations trace
│       └── results_report.md   # Detailed analytical answers to Section 11.5 questions
├── tests/                      # Pytest automated test suite
│   ├── test_evaluate.py        # All Section 5.4 validation hand scenarios
│   └── test_solvers.py         # State consistency, solver correctness, and AC-3 tests
├── REPORT.md                   # Full academic report (6-10 pages equivalent)
└── requirements.txt            # Dependency manifest
```

---

## 2. Quickstart & Execution

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Standard dependencies: `pandas`, `pytest`, `fastapi`, `uvicorn` (plus optional `streamlit`, `openpyxl`, `matplotlib`)

### 1. Run the Minimalist Editorial Web Application
Launch the standalone editorial web application:
```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in any modern browser.

### 2. Run the Streamlit Application (Alternative Interface)
If Streamlit is installed:
```bash
streamlit run app.py
```

### 3. Run the Automated Test Suite
Verify that all 12 evaluator and solver unit tests pass:
```bash
python -m pytest
```

### 4. Regenerate Datasets & Run Benchmarks
Generate the verified solvable test problems:
```bash
python experiments/make_datasets.py
```
Execute the full 120-run empirical comparison across all 10 seeds:
```bash
python experiments/run_experiments.py
```

---

## 3. Mathematical Problem Formulation

### 3.1 Variables & Domains
- **Variable**: One session $s \in S$ of a subject for a class.
  - Theory: $1$ period long ($h$ sessions for $h$ weekly hours).
  - Lab: $L$ consecutive periods ($h / L$ sessions, default $L = 2$).
  - Pre-assigned to one teacher via greedy flow matching with load balancing.
- **Value**: A 3-tuple `(day, start_period, room)`.
  - Occupies periods $[p, p + \text{length})$.
  - Filtered upfront by unary constraints (**H4** room capacity, **H5** room type, **H6** teacher availability, **H9** breaks & class lunch).

### 3.2 Constraint Taxonomy

| Code | Constraint Description | Type | Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| **H1** | Teacher double-booking prevention | Binary | Search clash check & incremental counter |
| **H2** | Student cohort double-booking | Binary | Search clash check & incremental counter |
| **H3** | Room double-booking prevention | Binary | Search clash check & incremental counter |
| **H4** | Room capacity $\ge$ class strength | Unary | Upfront domain pruning filter |
| **H5** | Lab subjects in labs, theory in classrooms | Unary | Upfront domain pruning filter |
| **H6** | Teacher availability schedule | Unary | Upfront domain pruning filter |
| **H7** | Exact weekly subject hours delivered | Structural | Guaranteed by session count construction |
| **H8** | Teacher maximum weekly load respected | Structural | Guaranteed by greedy load balancing |
| **H9** | Protected break and cohort lunch periods | Unary | Upfront domain pruning filter |
| **S1** | Minimise free periods (gaps) in student day | Soft ($W = 2$) | Evaluated on teachable intervals |
| **S2** | Spread theory subjects across different days | Soft ($W = 3$) | Penalty for repeating subject on same day |
| **S4** | Respect faculty avoided period preferences | Soft ($W = 1$) | Penalty for assigning avoided period |
| **S5** | Teacher fatigue: max 2 consecutive lectures | Soft ($W = 2$) | Penalty for back-to-back runs $> 2$ |

### 3.3 The Objective Cost Function
$$\text{Cost} = 1000 \times (\text{Hard Violations}) + \sum_{i \in \{1, 2, 4, 5\}} W_{Si} \cdot (\text{Soft Penalties})$$
The multiplier of $1000$ strictly dominates all combined soft penalties, ensuring that algorithms prioritize eliminating physical timetable clashes before fine-tuning ergonomic quality.

---

## 4. Empirical Benchmark Results (Section 11)

Summary across 10 random seeds ($0 \dots 9$) per configuration:

### Small Dataset (3 Classes, 6 Faculty, 4 Rooms, 45 Sessions)
| Algorithmic Method | Success Rate | Avg Time (s) | Std Dev (s) | Avg Work (Nodes/Iters) | Avg Hard Clashes | Avg Soft Penalty |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **BT baseline** | 10/10 | 0.04s | 0.11s | 6,559 nodes | 0.0 | 61.1 |
| **BT heuristics** | 10/10 | 0.02s | 0.01s | **58 nodes** | 0.0 | 64.3 |
| **Min-Conflicts** | 10/10 | 0.00s | 0.00s | **1 iter** | 0.0 | 62.8 |
| **Simulated Annealing** | 10/10 | 1.59s | 0.11s | 9,621 steps | 0.0 | **2.8** |
| **Hill Climbing** | 10/10 | 0.38s | 0.08s | 2,443 steps | 0.0 | 4.3 |
| **Hybrid (BT + SA)** | 10/10 | 1.56s | 0.12s | 9,643 steps | 0.0 | **2.6** |

### Large Dataset (8 Classes, 15 Faculty, 8 Rooms, 144 Sessions)
| Algorithmic Method | Success Rate | Avg Time (s) | Std Dev (s) | Avg Work (Nodes/Iters) | Avg Hard Clashes | Avg Soft Penalty |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **BT baseline** | 7/10 | 0.08s | 0.11s | 6,733 nodes | 43.2 (failed) | 216.6 |
| **BT heuristics** | 10/10 | 0.57s | 0.09s | **219 nodes** | 0.0 | 227.0 |
| **Min-Conflicts** | 10/10 | **0.03s** | 0.00s | **3 iters** | 0.0 | 213.8 |
| **Simulated Annealing** | 10/10 | 12.69s | 0.57s | 31,478 steps | 0.0 | **34.7** |
| **Hill Climbing** | 9/10 | 1.21s | 0.10s | 2,990 steps | 0.1 | 96.6 |
| **Hybrid (BT + SA)** | 10/10 | 13.43s | 0.93s | 31,410 steps | 0.0 | **39.9** |

---

## 5. Key Empirical Conclusions

1. **Heuristic Pruning Efficiency**: Backtracking with MRV + Forward Checking reduced search nodes from 6,559 down to 58 on the small dataset, and conquered the large 144-session dataset in 219 nodes where plain backtracking suffered timeouts.
2. **Local Search Scalability**: Min-Conflicts resolved binary clashes on the large dataset in 0.03s, proving ideal for instant enterprise scheduling.
3. **Quality Ergonomics**: Simulated Annealing and the Hybrid solver reduced soft schedule penalties by over **84%**, eliminating student gaps and faculty fatigue while preserving 0 hard clashes.

---

## 6. Academic Integrity & AI Disclosure
In adherence to institutional academic standards (Section 12.4):
- Generative AI assistance was utilized for boilerplate UI styling, scaffolding experimental test harnesses, and automating benchmark runs.
- All mathematical modeling, CSP variable/domain formulation, incremental State counters, and heuristic constraint algorithms were developed, rigorously verified, and validated against Russell & Norvig's *Artificial Intelligence: A Modern Approach* and Minton et al. (1992).
