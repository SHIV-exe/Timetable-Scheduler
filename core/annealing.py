"""Simulated Annealing, Hill Climbing, and Hybrid solver algorithms (Section 8).

Features:
1. Neighbourhood operators: 50% single-session relocation, 50% compatible pairwise swap.
2. Analytic initial temperature estimation (T0) targeting 80% uphill acceptance probability.
3. Geometric cooling schedule: T_k = alpha * T_(k-1) over L steps per temperature (L = len(sessions)).
4. Hill climbing (pure greedy descent with zero temperature).
5. Hybrid chaining: Backtracking / Min-Conflicts for feasibility -> Simulated Annealing for soft quality polish.
"""

import math
import random
import time
from typing import Dict, List, Set, Tuple, Optional, Any
from config import HARD_W
from core.evaluate import evaluate
from core.model import Data, Session


def propose(
    cur: Dict[int, Tuple[int, int, str]],
    sessions: List[Session],
    domains: Dict[int, List[Tuple[int, int, str]]],
    dom_set: Dict[int, Set[Tuple[int, int, str]]],
    rng: random.Random,
) -> Optional[Dict[int, Tuple[int, int, str]]]:
    """Propose a neighbour state by either moving a session or swapping two sessions."""
    cand = dict(cur)
    if rng.random() < 0.5:
        # Move: pick a random session and assign a random domain value
        s = rng.choice(sessions)
        dom = domains[s.sid]
        if len(dom) <= 1:
            return None
        v = rng.choice(dom)
        if v == cur.get(s.sid):
            return None
        cand[s.sid] = v
        return cand
    else:
        # Swap: pick two sessions of identical kind and duration
        if len(sessions) < 2:
            return None
        s, t = rng.sample(sessions, 2)
        if s.length != t.length or s.kind != t.kind:
            return None
        a, b = cur.get(s.sid), cur.get(t.sid)
        if a is None or b is None:
            return None
        # Check domain compatibility in both directions
        if b not in dom_set[s.sid] or a not in dom_set[t.sid]:
            return None
        cand[s.sid], cand[t.sid] = b, a
        return cand


def estimate_T0(
    data: Data,
    sessions: List[Session],
    domains: Dict[int, List[Tuple[int, int, str]]],
    dom_set: Dict[int, Set[Tuple[int, int, str]]],
    cur: Dict[int, Tuple[int, int, str]],
    rng: random.Random,
    p: float = 0.8,
    samples: int = 150,
) -> float:
    """Sample uphill moves to estimate initial temperature T0 giving acceptance probability p."""
    base_cost = evaluate(data, sessions, cur).cost
    ups = []
    for _ in range(samples):
        cand = propose(cur, sessions, domains, dom_set, rng)
        if cand is not None:
            c = evaluate(data, sessions, cand).cost
            d = c - base_cost
            if 0 < d < HARD_W:
                ups.append(d)
    if ups:
        avg_increase = sum(ups) / len(ups)
        return -avg_increase / math.log(p)
    return 10.0


def anneal(
    data: Data,
    sessions: List[Session],
    domains: Dict[int, List[Tuple[int, int, str]]],
    start: Dict[int, Tuple[int, int, str]],
    seed: int = 0,
    alpha: float = 0.95,
    T_min: float = 0.05,
    time_limit: float = 60.0,
) -> Tuple[Dict[int, Tuple[int, int, str]], int, List[int]]:
    """Execute Simulated Annealing search starting from an initial assignment.
    
    Returns:
        (best_assignment, total_iterations, trace_of_best_costs)
    """
    rng = random.Random(seed)
    dom_set = {k: set(v) for k, v in domains.items()}
    cur = dict(start)
    cur_cost = evaluate(data, sessions, cur).cost

    best = dict(cur)
    best_cost = cur_cost
    trace = [best_cost]

    T = estimate_T0(data, sessions, domains, dom_set, cur, rng)
    deadline = time.time() + time_limit
    total_steps = 0
    L = len(sessions)

    while T > T_min and time.time() < deadline:
        for _ in range(L):
            total_steps += 1
            cand = propose(cur, sessions, domains, dom_set, rng)
            if cand is None:
                continue

            c = evaluate(data, sessions, cand).cost
            delta = c - cur_cost

            # Metropolis acceptance criterion
            if delta <= 0 or (T > 1e-6 and rng.random() < math.exp(-delta / T)):
                cur, cur_cost = cand, c
                if c < best_cost:
                    best, best_cost = dict(cand), c

            if total_steps % max(1, L // 2) == 0:
                trace.append(best_cost)

            if time.time() >= deadline:
                break

        T *= alpha

    return best, total_steps, trace


def hill_climb(
    data: Data,
    sessions: List[Session],
    domains: Dict[int, List[Tuple[int, int, str]]],
    start: Dict[int, Tuple[int, int, str]],
    seed: int = 0,
    max_steps: int = 3000,
    time_limit: float = 60.0,
) -> Tuple[Dict[int, Tuple[int, int, str]], int, List[int]]:
    """Greedy local descent (temperature = 0). Accepts only non-worsening moves."""
    rng = random.Random(seed)
    dom_set = {k: set(v) for k, v in domains.items()}
    cur = dict(start)
    cur_cost = evaluate(data, sessions, cur).cost

    best = dict(cur)
    best_cost = cur_cost
    trace = [best_cost]
    deadline = time.time() + time_limit

    steps = 0
    stale = 0
    patience = 500

    while steps < max_steps and time.time() < deadline and stale < patience:
        steps += 1
        cand = propose(cur, sessions, domains, dom_set, rng)
        if cand is None:
            continue
        c = evaluate(data, sessions, cand).cost
        if c <= cur_cost:
            if c < cur_cost:
                stale = 0
            else:
                stale += 1
            cur, cur_cost = cand, c
            if c < best_cost:
                best, best_cost = dict(cand), c
        else:
            stale += 1

        if steps % 50 == 0:
            trace.append(best_cost)

    return best, steps, trace
