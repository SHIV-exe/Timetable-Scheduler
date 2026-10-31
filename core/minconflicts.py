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

    def __init__(self, data: Optional[Any] = None):
        self.data = data
        self.T = Counter()  # (teacher_name, (day, period)) -> occupancy count
        self.C = Counter()  # (class_name, (day, period)) -> occupancy count
        self.R = Counter()  # (room_name, (day, period)) -> occupancy count
        self.parent_occ = Counter()  # (parent_batch, (day, period)) -> count
        self.child_occ = Counter()   # (parent_batch, (day, period)) -> count
        self.asg: Dict[int, Tuple[int, int, str]] = {}
        self.total = 0  # Number of H1 + H2 + H3 binary violations

    def _room_cap(self, r: str, kind: str) -> int:
        if self.data and hasattr(self.data, "rooms") and r in self.data.rooms:
            rm = self.data.rooms[r]
            if rm.kind == "lab" and kind == "lab":
                return max(1, rm.capacity // 30)
        return 1

    def add(self, s: Any, v: Tuple[int, int, str]):
        """Assign session s to value v, updating conflict tallies."""
        d, p, r = v
        r_cap = self._room_cap(r, s.kind)
        p_cls = getattr(s, "parent_cls", None)

        for k in range(s.length):
            sl = (d, p + k)
            # Teacher
            t_key = (s.teacher, sl)
            if self.T[t_key] >= 1:
                self.total += 1
            self.T[t_key] += 1

            # Class
            c_key = (s.cls, sl)
            if self.C[c_key] >= 1:
                self.total += 1
            self.C[c_key] += 1

            # Parent / Child Cohort clash
            if p_cls:
                # s is a child section
                if self.parent_occ[(p_cls, sl)] >= 1:
                    self.total += 1
                self.child_occ[(p_cls, sl)] += 1
            else:
                # s is parent batch (or independent class)
                if self.child_occ[(s.cls, sl)] >= 1:
                    self.total += self.child_occ[(s.cls, sl)]
                self.parent_occ[(s.cls, sl)] += 1

            # Room
            r_key = (r, sl)
            if self.R[r_key] >= r_cap:
                self.total += 1
            self.R[r_key] += 1

        self.asg[s.sid] = v

    def remove(self, s: Any) -> Tuple[int, int, str]:
        """Unassign session s, updating conflict tallies."""
        v = self.asg.pop(s.sid)
        d, p, r = v
        r_cap = self._room_cap(r, s.kind)
        p_cls = getattr(s, "parent_cls", None)

        for k in range(s.length):
            sl = (d, p + k)
            # Teacher
            t_key = (s.teacher, sl)
            self.T[t_key] -= 1
            if self.T[t_key] >= 1:
                self.total -= 1

            # Class
            c_key = (s.cls, sl)
            self.C[c_key] -= 1
            if self.C[c_key] >= 1:
                self.total -= 1

            # Parent / Child Cohort clash
            if p_cls:
                self.child_occ[(p_cls, sl)] -= 1
                if self.parent_occ[(p_cls, sl)] >= 1:
                    self.total -= 1
            else:
                self.parent_occ[(s.cls, sl)] -= 1
                if self.child_occ[(s.cls, sl)] >= 1:
                    self.total -= self.child_occ[(s.cls, sl)]

            # Room
            r_key = (r, sl)
            self.R[r_key] -= 1
            if self.R[r_key] >= r_cap:
                self.total -= 1

        return v

    def cost_of(self, s: Any, v: Tuple[int, int, str]) -> int:
        """Calculate conflicts that session s would encounter at value v.
        
        Must be called when session s is currently removed from assignment.
        """
        d, p, r = v
        r_cap = self._room_cap(r, s.kind)
        p_cls = getattr(s, "parent_cls", None)
        cost = 0

        for k in range(s.length):
            sl = (d, p + k)
            cost += self.T[(s.teacher, sl)]
            cost += self.C[(s.cls, sl)]

            if p_cls:
                cost += self.parent_occ[(p_cls, sl)]
            else:
                cost += self.child_occ[(s.cls, sl)]

            if self.R[(r, sl)] >= r_cap:
                cost += 1

        return cost

    def in_conflict(self, s: Any) -> bool:
        """Return True if session s is currently involved in at least one conflict."""
        if s.sid not in self.asg:
            return False
        v = self.asg[s.sid]
        d, p, r = v
        r_cap = self._room_cap(r, s.kind)
        p_cls = getattr(s, "parent_cls", None)

        for k in range(s.length):
            sl = (d, p + k)
            if self.T[(s.teacher, sl)] > 1:
                return True
            if self.C[(s.cls, sl)] > 1:
                return True
            if p_cls and self.parent_occ[(p_cls, sl)] >= 1:
                return True
            if not p_cls and self.child_occ[(s.cls, sl)] >= 1:
                return True
            if self.R[(r, sl)] > r_cap:
                return True
        return False


def greedy_init(
    sessions: List[Any],
    domains: Dict[int, List[Tuple[int, int, str]]],
    rng: random.Random,
    data: Optional[Any] = None,
) -> State:
    """Construct initial complete assignment greedily with randomized tie-breaks."""
    st = State(data=data)
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
    data: Optional[Any] = None,
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
        st = greedy_init(sessions, domains, rng, data=data)
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
