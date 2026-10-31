"""Central evaluation module for AI Timetable Scheduler.

Implements the single source of truth for timetable quality, counting all hard
constraint violations (H1 to H9, RANGE) and soft constraint penalties (S1, S2, S4, S5).
Used by Backtracking, Min-Conflicts, Simulated Annealing, the manual editor, and experiments.
"""

from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any
from config import HARD_W, W
from core.model import Data, Session


class Report:
    """Stores hard violations, soft penalties, conflicted sessions, and error messages."""

    def __init__(self):
        self.hard: Dict[str, int] = defaultdict(int)
        self.soft: Dict[str, int] = defaultdict(int)
        self.conflicted: Set[int] = set()
        self.messages: List[str] = []

    @property
    def hard_total(self) -> int:
        return sum(self.hard.values())

    @property
    def soft_total(self) -> int:
        return sum(self.soft.values())

    @property
    def cost(self) -> int:
        return HARD_W * self.hard_total + self.soft_total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hard_total": self.hard_total,
            "soft_total": self.soft_total,
            "cost": self.cost,
            "hard_breakdown": dict(self.hard),
            "soft_breakdown": dict(self.soft),
            "conflicted_count": len(self.conflicted),
            "conflicted_sids": list(self.conflicted),
            "messages": list(self.messages),
        }


def evaluate(data: Data, sessions: List[Session], asg: Dict[int, Tuple[int, int, str]]) -> Report:
    """Evaluate a timetable assignment against all hard and soft constraints.
    
    Args:
        data: The institutional schedule data.
        sessions: The list of Session variables.
        asg: Assignment mapping session id -> (day_idx, start_period_idx, room_name).

    Returns:
        Report containing violation counts, soft penalties, conflicted session IDs, and messages.
    """
    R = Report()
    t_at = defaultdict(list)
    c_at = defaultdict(list)
    r_at = defaultdict(list)
    occ_c = defaultdict(set)  # (class_name, day_idx) -> set of occupied period indices
    occ_t = defaultdict(set)  # (teacher_name, day_idx) -> set of occupied period indices
    subj_day = defaultdict(int)  # (class_name, subject_code, day_idx) -> count
    load = defaultdict(int)  # teacher_name -> total hours

    for s in sessions:
        load[s.teacher] += s.length

        if s.sid not in asg:
            # H7: session is unassigned
            R.hard["H7"] += 1
            R.conflicted.add(s.sid)
            R.messages.append(f"H7: {s.cls}/{s.subject} #{s.idx} is not placed")
            continue

        d, p, rn = asg[s.sid]
        c = data.classes[s.cls]
        t = data.teachers[s.teacher]
        room = data.rooms.get(rn)

        bad = False

        # Range check: start must be >= 0 and end <= periods per day
        if p < 0 or p + s.length > data.periods:
            R.hard["RANGE"] += 1
            bad = True
            R.messages.append(f"RANGE: {s.cls}/{s.subject} starts at P{p+1} with length {s.length}")

        # H4: Room capacity
        if room is None or room.capacity < c.strength:
            R.hard["H4"] += 1
            bad = True
            R.messages.append(f"H4: Room '{rn}' is too small for class '{c.name}' ({c.strength} students)")

        # H5: Room type
        sub = data.subjects.get(s.subject)
        target_room_type = sub.room_type if (sub and sub.room_type) else ("lab" if s.kind == "lab" else "classroom")
        if target_room_type == "lab":
            is_valid_room = (room is not None and room.kind == "lab")
            expected_kind = "lab"
        elif target_room_type == "tutorial_room":
            is_valid_room = (room is not None and room.kind in ("tutorial_room", "classroom"))
            expected_kind = "tutorial_room/classroom"
        else:
            is_valid_room = (room is not None and room.kind in ("classroom", "lecture_theatre", "tutorial_room"))
            expected_kind = "classroom/lecture_theatre/tutorial_room"

        if not is_valid_room:
            R.hard["H5"] += 1
            bad = True
            R.messages.append(f"H5: Room '{rn}' is {room.kind if room else 'unknown'}, expected {expected_kind} for {s.subject}")

        # Period-by-period checks
        for k in range(s.length):
            q = p + k
            slot = (d, q)

            t_at[(t.name, slot)].append(s.sid)
            c_at[(c.name, slot)].append(s.sid)
            r_at[(rn, slot)].append(s.sid)

            occ_c[(c.name, d)].add(q)
            occ_t[(t.name, d)].add(q)

            # H9: Break periods or class lunch period
            if q in data.break_periods or q == c.lunch_period:
                R.hard["H9"] += 1
                bad = True
                period_type = "lunch" if q == c.lunch_period else "break"
                R.messages.append(f"H9: {c.name} has session during {period_type} period P{q+1} on {data.days[d]}")

            # H6: Teacher unavailable slot
            if slot in t.unavailable:
                R.hard["H6"] += 1
                bad = True
                R.messages.append(f"H6: {t.name} is unavailable on {data.days[d]} P{q+1}")

            # S4: Teacher avoided periods
            if q in t.avoid_periods:
                R.soft["S4"] += W["S4"]

        if bad:
            R.conflicted.add(s.sid)

        if s.kind == "theory":
            subj_day[(c.name, s.subject, d)] += 1

    # Binary constraints H1, H2, H3
    sess_by_id = {s.sid: s for s in sessions}

    # H1: Teacher clashing
    for (name, (d, q)), sids in t_at.items():
        if len(sids) > 1:
            R.hard["H1"] += len(sids) - 1
            R.conflicted.update(sids)
            day_name = data.days[d] if 0 <= d < len(data.days) else f"Day {d}"
            R.messages.append(f"H1: Teacher '{name}' has {len(sids)} sessions on {day_name} P{q+1}")

    # H2: Class / Cohort clashing
    for (name, (d, q)), sids in c_at.items():
        if len(sids) > 1:
            R.hard["H2"] += len(sids) - 1
            R.conflicted.update(sids)
            day_name = data.days[d] if 0 <= d < len(data.days) else f"Day {d}"
            R.messages.append(f"H2: Class '{name}' has {len(sids)} sessions on {day_name} P{q+1}")

    # H2 part 2: Parent cohort vs sub-section conflict
    checked_parent_child = set()
    for s1 in sessions:
        if s1.parent_cls and s1.parent_cls != s1.cls and s1.sid in asg:
            p_cls = s1.parent_cls
            d1, p1, _ = asg[s1.sid]
            for k1 in range(s1.length):
                slot1 = (d1, p1 + k1)
                for s2_sid in c_at.get((p_cls, slot1), []):
                    if s2_sid != s1.sid:
                        pair = tuple(sorted([s1.sid, s2_sid]))
                        if pair not in checked_parent_child:
                            checked_parent_child.add(pair)
                            R.hard["H2"] += 1
                            R.conflicted.add(s1.sid)
                            R.conflicted.add(s2_sid)
                            day_name = data.days[d1] if 0 <= d1 < len(data.days) else f"Day {d1}"
                            R.messages.append(
                                f"H2: Sub-batch '{s1.cls}' lab conflicts with parent cohort '{p_cls}' on {day_name} P{slot1[1]+1}"
                            )

    # H3: Room clashing / capacity
    for (rn, (d, q)), sids in r_at.items():
        if len(sids) > 1:
            day_name = data.days[d] if 0 <= d < len(data.days) else f"Day {d}"
            room = data.rooms.get(rn)
            if room and room.kind == "lab":
                # Multiple lab sections can share a lab room as long as total strength <= room.capacity
                total_students = sum(data.classes[sess_by_id[sid].cls].strength for sid in sids if sess_by_id[sid].cls in data.classes)
                if total_students > room.capacity:
                    R.hard["H3"] += len(sids) - 1
                    R.conflicted.update(sids)
                    R.messages.append(f"H3: Lab '{rn}' overloaded with {total_students} students (capacity {room.capacity}) on {day_name} P{q+1}")
            else:
                R.hard["H3"] += len(sids) - 1
                R.conflicted.update(sids)
                R.messages.append(f"H3: Room '{rn}' has {len(sids)} sessions on {day_name} P{q+1}")

    # H8: Teacher maximum weekly load
    for tname, hrs in load.items():
        if tname in data.teachers:
            over = hrs - data.teachers[tname].max_load
            if over > 0:
                R.hard["H8"] += over
                R.messages.append(f"H8: Teacher '{tname}' is overloaded by {over} hours")

    # S1: Gaps (free periods) inside a class's day
    # Count teachable periods between first and last session that are unoccupied
    for (cname, d), ps in occ_c.items():
        if not ps:
            continue
        c = data.classes[cname]
        min_p, max_p = min(ps), max(ps)
        teachable = [
            q for q in range(min_p, max_p + 1)
            if q not in data.break_periods and q != c.lunch_period
        ]
        gaps = sum(1 for q in teachable if q not in ps)
        if gaps > 0:
            R.soft["S1"] += W["S1"] * gaps

    # S2: Spread a subject over different days (avoid repeating theory subject in one day)
    for (cname, sub_code, d), n in subj_day.items():
        if n > 1:
            R.soft["S2"] += W["S2"] * (n - 1)

    # S5: Teacher consecutive lectures (penalty for back-to-back runs > 2 periods)
    for (tname, d), ps in occ_t.items():
        run = 0
        for q in sorted(ps):
            run = (run + 1) if ((q - 1) in ps) else 1
            if run > 2:
                R.soft["S5"] += W["S5"]

    return R
