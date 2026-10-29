"""Unified solver dispatcher and Result abstraction for AI Timetable Scheduler.

Conforms to Section 10 interface contract:
solvers.run(algo, data, sessions, domains, seed, time_limit) -> Result(asg, success, work, time_taken, trace)
Never imports Streamlit, ensuring algorithms can be called by CLI, experiments, and GUI alike.
"""

from dataclasses import dataclass, field
import random
import time
from typing import Dict, List, Tuple, Optional, Any

from core.model import Data, Session
from core.backtracking import plain_bt, BTSolver, Budget
from core.minconflicts import min_conflicts, greedy_init
from core.annealing import anneal, hill_climb
from core.evaluate import evaluate


@dataclass
class Result:
    asg: Dict[int, Tuple[int, int, str]]
    success: bool
    work: int  # Nodes expanded for systematic search, or iterations for local search
    time_taken: float = 0.0
    trace: List[int] = field(default_factory=list)


def run(
    algo: str,
    data: Data,
    sessions: List[Session],
    domains: Dict[int, List[Tuple[int, int, str]]],
    seed: int = 0,
    time_limit: float = 60.0,
    node_limit: int = 500_000,
) -> Result:
    """Execute the requested algorithm with unified parameters and return a Result object."""
    t0 = time.perf_counter()
    rng = random.Random(seed)

    algo_norm = algo.lower().strip()

    if "plain" in algo_norm or algo_norm == "bt baseline":
        stats = {"nodes": 0}
        budget = Budget(node_limit=node_limit, time_limit=time_limit)
        asg = plain_bt(sessions, domains, stats, budget, rng=rng)
        elapsed = time.perf_counter() - t0
        success = asg is not None and len(asg) == len(sessions)
        return Result(asg=(asg or {}), success=success, work=stats["nodes"], time_taken=elapsed)

    elif "mrv" in algo_norm or "heuristic" in algo_norm or algo_norm == "bt heuristics":
        solver = BTSolver(
            sessions=sessions,
            domains=domains,
            mrv=True,
            degree=True,
            lcv=False,
            fc=True,
            symmetry=True,
            node_limit=node_limit,
            time_limit=time_limit,
            rng=rng,
        )
        asg = solver.solve()
        elapsed = time.perf_counter() - t0
        success = asg is not None and len(asg) == len(sessions)
        return Result(asg=(asg or {}), success=success, work=solver.nodes, time_taken=elapsed)

    elif "bt + fc only" in algo_norm:
        solver = BTSolver(
            sessions=sessions,
            domains=domains,
            mrv=False,
            degree=False,
            lcv=False,
            fc=True,
            symmetry=False,
            node_limit=node_limit,
            time_limit=time_limit,
            rng=rng,
        )
        asg = solver.solve()
        elapsed = time.perf_counter() - t0
        success = asg is not None and len(asg) == len(sessions)
        return Result(asg=(asg or {}), success=success, work=solver.nodes, time_taken=elapsed)

    elif "bt + mrv only" in algo_norm:
        solver = BTSolver(
            sessions=sessions,
            domains=domains,
            mrv=True,
            degree=False,
            lcv=False,
            fc=False,
            symmetry=False,
            node_limit=node_limit,
            time_limit=time_limit,
            rng=rng,
        )
        asg = solver.solve()
        elapsed = time.perf_counter() - t0
        success = asg is not None and len(asg) == len(sessions)
        return Result(asg=(asg or {}), success=success, work=solver.nodes, time_taken=elapsed)

    elif "bt + symmetry only" in algo_norm:
        solver = BTSolver(
            sessions=sessions,
            domains=domains,
            mrv=False,
            degree=False,
            lcv=False,
            fc=False,
            symmetry=True,
            node_limit=node_limit,
            time_limit=time_limit,
            rng=rng,
        )
        asg = solver.solve()
        elapsed = time.perf_counter() - t0
        success = asg is not None and len(asg) == len(sessions)
        return Result(asg=(asg or {}), success=success, work=solver.nodes, time_taken=elapsed)

    elif "min-conflicts" in algo_norm or algo_norm == "minconflicts":
        trace: List[int] = []
        asg, iters, success = min_conflicts(
            sessions=sessions,
            domains=domains,
            seed=seed,
            max_iters=20_000,
            p_walk=0.05,
            restart_after=2000,
            max_restarts=5,
            time_limit=time_limit,
            trace=trace,
        )
        elapsed = time.perf_counter() - t0
        return Result(asg=asg, success=success, work=iters, time_taken=elapsed, trace=trace)

    elif "simulated annealing" in algo_norm or algo_norm == "sa":
        # Initialize with greedy start or fast min-conflicts attempt
        trace: List[int] = []
        init_st = greedy_init(sessions, domains, rng)
        start_asg = dict(init_st.asg)
        best_asg, steps, trace = anneal(
            data=data,
            sessions=sessions,
            domains=domains,
            start=start_asg,
            seed=seed,
            time_limit=time_limit,
        )
        elapsed = time.perf_counter() - t0
        rep = evaluate(data, sessions, best_asg)
        return Result(asg=best_asg, success=(rep.hard_total == 0), work=steps, time_taken=elapsed, trace=trace)

    elif "hill climb" in algo_norm:
        init_st = greedy_init(sessions, domains, rng)
        best_asg, steps, trace = hill_climb(
            data=data,
            sessions=sessions,
            domains=domains,
            start=dict(init_st.asg),
            seed=seed,
            time_limit=time_limit,
        )
        elapsed = time.perf_counter() - t0
        rep = evaluate(data, sessions, best_asg)
        return Result(asg=best_asg, success=(rep.hard_total == 0), work=steps, time_taken=elapsed, trace=trace)

    elif "hybrid" in algo_norm:
        # Phase 1: Reach feasibility using BTSolver (or fallback to Min-Conflicts if BT struggles)
        solver = BTSolver(
            sessions=sessions,
            domains=domains,
            mrv=True,
            degree=True,
            lcv=False,
            fc=True,
            symmetry=True,
            node_limit=node_limit,
            time_limit=min(20.0, time_limit * 0.4),
            rng=rng,
        )
        phase1_asg = solver.solve()
        work1 = solver.nodes

        if phase1_asg is None:
            # Fallback to Min-Conflicts for phase 1 feasibility
            mc_trace: List[int] = []
            phase1_asg, mc_iters, mc_ok = min_conflicts(
                sessions=sessions,
                domains=domains,
                seed=seed,
                max_iters=10_000,
                time_limit=min(20.0, time_limit * 0.4),
                trace=mc_trace,
            )
            work1 += mc_iters

        # Phase 2: Soft constraint polishing using Simulated Annealing
        rem_time = max(5.0, time_limit - (time.perf_counter() - t0))
        best_asg, sa_steps, trace = anneal(
            data=data,
            sessions=sessions,
            domains=domains,
            start=phase1_asg,
            seed=seed,
            time_limit=rem_time,
        )
        elapsed = time.perf_counter() - t0
        rep = evaluate(data, sessions, best_asg)
        return Result(
            asg=best_asg,
            success=(rep.hard_total == 0),
            work=work1 + sa_steps,
            time_taken=elapsed,
            trace=trace,
        )

    else:
        raise ValueError(f"Unknown algorithm: '{algo}'")
