"""Backtracking CSP solver module for AI Timetable Scheduler.

Implements:
1. Plain Backtracking baseline (un-optimized recursive search).
2. Advanced BTSolver with modular toggles for ablation studies:
   - MRV (Minimum Remaining Values variable ordering)
   - Degree Heuristic (tie-breaking by degree of unassigned neighbors)
   - Forward Checking (fail-early domain pruning)
   - Symmetry Breaking (lexicographic ordering of interchangeable sessions)
   - LCV (Least Constraining Value ordering)
   - Seeded value randomization for reproducible experiments
3. AC-3 (Arc Consistency 3) preprocessing.
"""

from collections import deque
import random
import sys
import time
from typing import Dict, List, Set, Tuple, Optional, Any

# Ensure sufficient recursion depth for scheduling hundreds of sessions
sys.setrecursionlimit(10000)


class Timeout(Exception):
    """Raised when search exceeds the allotted node or time budget."""
    pass


class Budget:
    """Helper to monitor node and time limits during baseline search."""

    def __init__(self, node_limit: int = 500_000, time_limit: float = 60.0):
        self.node_limit = node_limit
        self.deadline = time.time() + time_limit

    def check(self, stats: Dict[str, Any]):
        if stats["nodes"] >= self.node_limit or time.time() >= self.deadline:
            raise Timeout()


def clash(s: Any, a: Tuple[int, int, str], t: Any, b: Tuple[int, int, str], data: Optional[Any] = None) -> bool:
    """Return True if session s at value a and session t at value b violate H1, H2, or H3."""
    # a and b are (day, start_period, room)
    if a[0] != b[0]:
        return False  # Different days do not clash
    # Check half-open interval overlap [start, start + length)
    if not (a[1] < b[1] + t.length and b[1] < a[1] + s.length):
        return False  # Periods do not overlap
    # H1: Teacher clash
    if s.teacher == t.teacher:
        return True
    # H2: Cohort clash (same class or parent/child cohort)
    if s.cls == t.cls:
        return True
    s_parent = getattr(s, "parent_cls", None)
    t_parent = getattr(t, "parent_cls", None)
    if (s_parent and s_parent == t.cls) or (t_parent and t_parent == s.cls):
        return True
    # H3: Room clash
    if a[2] == b[2]:
        room_name = a[2]
        if data and hasattr(data, "rooms") and room_name in data.rooms:
            room = data.rooms[room_name]
            if room.kind == "lab" and s.kind == "lab" and t.kind == "lab":
                s_str = data.classes[s.cls].strength if (hasattr(data, "classes") and s.cls in data.classes) else 30
                t_str = data.classes[t.cls].strength if (hasattr(data, "classes") and t.cls in data.classes) else 30
                if s_str + t_str <= room.capacity:
                    return False  # Can share lab room if combined capacity fits
        return True
    return False


def order_clash(s: Any, a: Tuple[int, int, str], t: Any, b: Tuple[int, int, str]) -> bool:
    """Symmetry breaking: sessions of the same (class, subject) are placed in index order."""
    if s.cls != t.cls or s.subject != t.subject:
        return False
    return (s.idx < t.idx) != ((a[0], a[1]) < (b[0], b[1]))


def plain_bt(
    sessions: List[Any],
    domains: Dict[int, List[Tuple[int, int, str]]],
    stats: Dict[str, Any],
    budget: Budget,
    rng: Optional[random.Random] = None,
) -> Optional[Dict[int, Tuple[int, int, str]]]:
    """Plain Backtracking baseline: fixed variable order, no inference, no heuristics."""
    S = {s.sid: s for s in sessions}
    asg: Dict[int, Tuple[int, int, str]] = {}

    # Pre-sort or shuffle domain values for each session
    val_lists = {}
    for sid, d in domains.items():
        v_list = list(d)
        if rng is not None:
            rng.shuffle(v_list)
        else:
            v_list.sort()
        val_lists[sid] = v_list

    def rec(i: int) -> bool:
        if i == len(sessions):
            return True
        s = sessions[i]
        for v in val_lists[s.sid]:
            stats["nodes"] += 1
            budget.check(stats)
            if all(not clash(s, v, S[t_id], b) for t_id, b in asg.items()):
                asg[s.sid] = v
                if rec(i + 1):
                    return True
                del asg[s.sid]
        return False

    try:
        return asg if rec(0) else None
    except Timeout:
        return None


class BTSolver:
    """Improved Backtracking CSP solver with configurable heuristics and inference."""

    def __init__(
        self,
        sessions: List[Any],
        domains: Dict[int, List[Tuple[int, int, str]]],
        mrv: bool = True,
        degree: bool = True,
        lcv: bool = False,
        fc: bool = True,
        symmetry: bool = True,
        node_limit: int = 500_000,
        time_limit: float = 60.0,
        rng: Optional[random.Random] = None,
        data: Optional[Any] = None,
    ):
        self.sessions = sessions
        self.order = [s.sid for s in sessions]
        self.S = {s.sid: s for s in sessions}
        self.dom = {sid: set(d) for sid, d in domains.items()}
        self.mrv = mrv
        self.degree = degree
        self.lcv = lcv
        self.fc = fc
        self.sym = symmetry
        self.asg: Dict[int, Tuple[int, int, str]] = {}
        self.nodes = 0
        self.backtracks = 0
        self.node_limit = node_limit
        self.deadline = time.time() + time_limit
        self.rng = rng
        self.data = data

        # Precompute neighbors sharing teacher, class, cohort, or possible room conflicts
        self.nb = {
            s.sid: {
                t.sid
                for t in sessions
                if t.sid != s.sid and (
                    t.teacher == s.teacher
                    or t.cls == s.cls
                    or (getattr(s, "parent_cls", None) and getattr(s, "parent_cls", None) == t.cls)
                    or (getattr(t, "parent_cls", None) and getattr(t, "parent_cls", None) == s.cls)
                )
            }
            for s in sessions
        }

    def bad(self, s: Any, a: Tuple[int, int, str], t: Any, b: Tuple[int, int, str]) -> bool:
        """Check clash constraint and symmetry breaking."""
        return clash(s, a, t, b, data=self.data) or (self.sym and order_clash(s, a, t, b))

    def select(self) -> Any:
        """Variable ordering heuristic (MRV with Degree tie-breaking)."""
        free = [self.S[i] for i in self.order if i not in self.asg]
        if not self.mrv:
            return free[0]

        def key(s: Any):
            deg = (
                sum(1 for n in self.nb[s.sid] if n not in self.asg)
                if self.degree
                else 0
            )
            return (len(self.dom[s.sid]), -deg)

        return min(free, key=key)

    def values(self, s: Any) -> List[Tuple[int, int, str]]:
        """Value ordering heuristic (optional LCV and seed shuffle)."""
        vals = sorted(self.dom[s.sid])
        if self.rng:
            self.rng.shuffle(vals)
        if self.lcv:
            # Sort values by fewest pruned domain options in unassigned neighbors
            vals.sort(
                key=lambda v: sum(
                    1
                    for tid in self.nb[s.sid]
                    if tid not in self.asg
                    for b in self.dom[tid]
                    if self.bad(s, v, self.S[tid], b)
                )
            )
        return vals

    def prune(self, s: Any, v: Tuple[int, int, str]) -> Optional[List[Tuple[int, Tuple[int, int, str]]]]:
        """Forward checking: prune conflicting values from unassigned variables' domains."""
        removed = []
        for tid in self.order:
            if tid in self.asg:
                continue
            t = self.S[tid]
            dead = [b for b in self.dom[tid] if self.bad(s, v, t, b)]
            for b in dead:
                self.dom[tid].discard(b)
                removed.append((tid, b))
            if not self.dom[tid]:
                # Domain wipeout detected: dead end
                self.restore(removed)
                return None
        return removed

    def restore(self, removed: List[Tuple[int, Tuple[int, int, str]]]):
        """Restore pruned values back into domains during backtracking."""
        for tid, b in removed:
            self.dom[tid].add(b)

    def search(self) -> bool:
        """Recursive backtracking search loop."""
        if len(self.asg) == len(self.S):
            return True

        s = self.select()
        for v in self.values(s):
            self.nodes += 1
            if self.nodes >= self.node_limit or time.time() >= self.deadline:
                raise Timeout()

            if not self.fc:
                # Without Forward Checking, test against already assigned variables
                if any(self.bad(s, v, self.S[t], b) for t, b in self.asg.items()):
                    continue

            self.asg[s.sid] = v
            removed = []
            if self.fc:
                removed = self.prune(s, v)
                if removed is None:
                    del self.asg[s.sid]
                    self.backtracks += 1
                    continue

            if self.search():
                return True

            if self.fc:
                self.restore(removed)
            del self.asg[s.sid]
            self.backtracks += 1

        return False

    def solve(self) -> Optional[Dict[int, Tuple[int, int, str]]]:
        """Execute search, catching Timeout exceptions gracefully."""
        try:
            return dict(self.asg) if self.search() else None
        except Timeout:
            return None


def ac3(
    S: Dict[int, Any],
    dom: Dict[int, Set[Tuple[int, int, str]]],
    nb: Dict[int, Set[int]],
) -> Tuple[bool, int]:
    """AC-3 preprocessing that enforces arc consistency between pairs of variables.
    
    Returns:
        (is_feasible, values_pruned_count)
    """
    q = deque((x, y) for x in nb for y in nb[x])
    pruned_count = 0
    while q:
        x, y = q.popleft()
        gone = [
            a
            for a in dom[x]
            if all(clash(S[x], a, S[y], b) for b in dom[y])
        ]
        if gone:
            for a in gone:
                dom[x].discard(a)
                pruned_count += 1
            if not dom[x]:
                return False, pruned_count
            for z in nb[x]:
                if z != y:
                    q.append((z, x))
    return True, pruned_count
