"""Min-Conflicts local search solver module for AI Timetable Scheduler.

Implements:
1. Fast incremental State class tracking teacher, class, and room slot occupancies in O(1).
   Ensures State.total == H1 + H2 + H3 from evaluate().
2. Greedy randomized initial assignment.
3. Plateau escapes via random walk (p_walk) and stagnant restarts.
4. Per-iteration cost tracing for visual convergence analysis.
"""

from collections import Counter
import random
import time
from typing import Dict, List, Tuple, Optional, Any, Iterator


class State:
    """Incremental conflict counter maintaining exact H1+H2+H3 violation totals."""

    def __init__(self):
        self.T = Counter()  # (teacher_name, (day, period)) -> occupancy count
        self.C = Counter()  # (class_name, (day, period)) -> occupancy count
        self.R = Counter()  # (room_name, (day, period)) -> occupancy count
        self.asg: Dict[int, Tuple[int, int, str]] = {}
        self.total = 0  # Number of H1 + H2 + H3 binary violations

    def _keys(self, s: Any, v: Tuple[int, int, str]) -> Iterator[Tuple[Counter, Tuple[str, Tuple[int, int]]]]:
        d, p, r = v
        for k in range(s.length):
            sl = (d, p + k)
            yield self.T, (s.teacher, sl)
            yield self.C, (s.cls, sl)
            yield self.R, (r, sl)

    def add(self, s: Any, v: Tuple[int, int, str]):
        """Assign session s to value v, updating conflict tallies."""
        for table, key in self._keys(s, v):
            if table[key] >= 1:
                self.total += 1
            table[key] += 1
        self.asg[s.sid] = v

    def remove(self, s: Any) -> Tuple[int, int, str]:
        """Unassign session s, updating conflict tallies."""
        v = self.asg.pop(s.sid)
        for table, key in self._keys(s, v):
            table[key] -= 1
            if table[key] >= 1:
                self.total -= 1
        return v

    def cost_of(self, s: Any, v: Tuple[int, int, str]) -> int:
        """Calculate conflicts that session s would encounter at value v.
        
        Must be called when session s is currently removed from assignment.
        """
        return sum(table[key] for table, key in self._keys(s, v))

    def in_conflict(self, s: Any) -> bool:
        """Return True if session s is currently involved in at least one conflict."""
        if s.sid not in self.asg:
            return False
        v = self.asg[s.sid]
        for table, key in self._keys(s, v):
            if table[key] > 1:
                return True
        return False


def greedy_init(sessions: List[Any], domains: Dict[int, List[Tuple[int, int, str]]], rng: random.Random) -> State:
    """Construct initial complete assignment greedily with randomized tie-breaks."""
    st = State()
    order = list(sessions)
    rng.shuffle(order)
    for s in order:
        scores = [(st.cost_of(s, v), v) for v in domains[s.sid]]
        min_c = min(c for c, _ in scores)
        best_vals = [v for c, v in scores if c == min_c]
        st.add(s, rng.choice(best_vals))
    return st


def min_conflicts(
    sessions: List[Any],
    domains: Dict[int, List[Tuple[int, int, str]]],
    seed: int = 0,
    max_iters: int = 20_000,
    p_walk: float = 0.05,
    restart_after: int = 2000,
    max_restarts: int = 5,
    time_limit: float = 120.0,
    trace: Optional[List[int]] = None,
) -> Tuple[Dict[int, Tuple[int, int, str]], int, bool]:
    """Execute Min-Conflicts local search algorithm.
    
    Returns:
        (assignment, iterations_executed, is_success)
    """
    rng = random.Random(seed)
    deadline = time.time() + time_limit
    total_iters = 0

    best_overall_asg = None
    best_overall_total = float("inf")

    for restart_idx in range(max_restarts + 1):
        st = greedy_init(sessions, domains, rng)
        restart_best = st.total
        stale = 0

        if st.total < best_overall_total:
            best_overall_total = st.total
            best_overall_asg = dict(st.asg)

        for _ in range(max_iters):
            total_iters += 1
            if trace is not None:
                trace.append(1000 * st.total)

            if st.total == 0:
                return dict(st.asg), total_iters, True

            if time.time() > deadline:
                return (best_overall_asg if best_overall_asg is not None else dict(st.asg)), total_iters, False

            # Select a conflicted variable uniformly at random
            conflicted = [x for x in sessions if st.in_conflict(x)]
            if not conflicted:
                # No conflicts remaining
                return dict(st.asg), total_iters, True

            s = rng.choice(conflicted)
            st.remove(s)

            # Plateau escape: random walk step with probability p_walk
            if rng.random() < p_walk:
                v = rng.choice(domains[s.sid])
            else:
                # Min-conflicts step: choose domain value minimizing conflicts
                scores = [(st.cost_of(s, w), w) for w in domains[s.sid]]
                min_c = min(c for c, _ in scores)
                best_vals = [w for c, w in scores if c == min_c]
                v = rng.choice(best_vals)

            st.add(s, v)

            if st.total < restart_best:
                restart_best = st.total
                stale = 0
                if st.total < best_overall_total:
                    best_overall_total = st.total
                    best_overall_asg = dict(st.asg)
            else:
                stale += 1

            if stale >= restart_after:
                # Progress stalled: trigger restart
                break

    return (best_overall_asg if best_overall_asg is not None else dict(st.asg)), total_iters, (best_overall_total == 0)
