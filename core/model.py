"""Data structures, validation, feasibility checking, and CSP session/domain building.

Implements all entities as clean Python dataclasses, separated from algorithms and UI.
Handles 1-based indexing in external representations and 0-based indexing internally.
"""

from dataclasses import dataclass, field
import json
from typing import Dict, List, Set, Tuple, Any, Optional


@dataclass
class Subject:
    code: str
    name: str
    hours: int
    kind: str  # 'theory' | 'lab'
    room_type: Optional[str] = None  # 'lab' | 'tutorial_room' | 'classroom' | 'lecture_theatre'


@dataclass
class Teacher:
    name: str
    subjects: Set[str]  # subject codes this teacher can teach
    unavailable: Set[Tuple[int, int]]  # {(day_idx, period_idx), ...}
    max_load: int  # max hours per week
    avoid_periods: Set[int] = field(default_factory=set)  # soft preference (period indices)


@dataclass
class SchoolClass:
    name: str
    strength: int
    subjects: List[str]  # subject codes
    lunch_period: int  # period index, free on every day
    teacher_map: Dict[str, str] = field(default_factory=dict)  # optional {subject_code: teacher_name}
    parent_class: Optional[str] = None  # parent batch if this is a sub-batch


@dataclass
class Room:
    name: str
    capacity: int
    kind: str  # 'classroom' | 'lab' | 'tutorial_room' | 'lecture_theatre'


@dataclass
class Data:
    days: List[str]  # e.g. ["Mon", "Tue", "Wed", "Thu", "Fri"]
    periods: int  # periods per day
    break_periods: Set[int]  # period indices that are breaks
    lab_block: int  # consecutive periods for a lab session (default 2)
    subjects: Dict[str, Subject]  # keyed by subject code
    teachers: Dict[str, Teacher]  # keyed by teacher name
    classes: Dict[str, SchoolClass]  # keyed by class name
    rooms: Dict[str, Room]  # keyed by room name
    period_slots: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class Session:
    sid: int
    cls: str
    subject: str
    teacher: str
    kind: str  # 'theory' | 'lab'
    length: int  # periods occupied: 1 for theory, lab_block for lab
    idx: int  # k-th session of this subject for this class
    parent_cls: Optional[str] = None


def validate_raw_data(raw: Dict[str, Any]) -> List[str]:
    """Validate raw JSON / dictionary data before constructing the Data model.
    
    Returns a list of readable error messages instead of raising uncaught exceptions.
    """
    errors: List[str] = []

    # 1. Check time structure
    time_info = raw.get("time")
    if not isinstance(time_info, dict):
        errors.append("Missing or invalid 'time' specification.")
        return errors

    days = time_info.get("days", [])
    if not isinstance(days, list) or len(days) == 0:
        errors.append("Time structure must have at least one day in 'days'.")
    elif len(days) != len(set(days)):
        errors.append("Duplicate day names found in 'days'.")

    periods = time_info.get("periods_per_day")
    if not isinstance(periods, int) or periods <= 0:
        errors.append("'periods_per_day' must be a positive integer.")
        periods = 6

    breaks = time_info.get("break_periods", [])
    if not isinstance(breaks, list):
        errors.append("'break_periods' must be a list of period numbers.")
    else:
        for b in breaks:
            if not isinstance(b, int) or b < 1 or b > periods:
                errors.append(f"Break period {b} must be an integer between 1 and {periods}.")

    lab_block = time_info.get("lab_block", 2)
    if not isinstance(lab_block, int) or lab_block <= 0:
        errors.append("'lab_block' must be a positive integer.")
        lab_block = 2

    # 2. Check subjects
    raw_subjects = raw.get("subjects", [])
    if not isinstance(raw_subjects, list) or len(raw_subjects) == 0:
        errors.append("At least one subject must be defined.")
    
    subject_codes = set()
    for s in (raw_subjects if isinstance(raw_subjects, list) else []):
        if not isinstance(s, dict):
            errors.append(f"Invalid subject item: {s}")
            continue
        code = s.get("code")
        name = s.get("name")
        hours = s.get("hours")
        kind = s.get("type")

        if not code or not isinstance(code, str):
            errors.append("Subject code must be a non-empty string.")
        elif code in subject_codes:
            errors.append(f"Duplicate subject code: '{code}'.")
        else:
            subject_codes.add(code)

        if not name or not isinstance(name, str):
            errors.append(f"Subject '{code}' has an invalid or missing name.")

        if not isinstance(hours, int) or hours <= 0:
            errors.append(f"Subject '{code}' weekly hours must be a positive integer.")
        elif kind == "lab" and hours % lab_block != 0:
            errors.append(
                f"Lab subject '{code}' weekly hours ({hours}) must be a multiple of lab_block ({lab_block})."
            )

        if kind not in ("theory", "lab"):
            errors.append(f"Subject '{code}' type must be 'theory' or 'lab', got '{kind}'.")

        rtype_req = s.get("room_type")
        if rtype_req and rtype_req not in ("lab", "tutorial_room", "classroom", "lecture_theatre"):
            errors.append(f"Subject '{code}' room_type must be 'lab', 'tutorial_room', 'classroom', or 'lecture_theatre', got '{rtype_req}'.")

    # 3. Check rooms
    raw_rooms = raw.get("rooms", [])
    if not isinstance(raw_rooms, list) or len(raw_rooms) == 0:
        errors.append("At least one room must be defined.")
    
    room_names = set()
    for r in (raw_rooms if isinstance(raw_rooms, list) else []):
        if not isinstance(r, dict):
            errors.append(f"Invalid room item: {r}")
            continue
        rname = r.get("name")
        cap = r.get("capacity")
        rtype = r.get("type")

        if not rname or not isinstance(rname, str):
            errors.append("Room name must be a non-empty string.")
        elif rname in room_names:
            errors.append(f"Duplicate room name: '{rname}'.")
        else:
            room_names.add(rname)

        if not isinstance(cap, int) or cap <= 0:
            errors.append(f"Room '{rname}' capacity must be a positive integer.")

        r_type_raw = str(rtype).strip().lower().replace(" ", "_") if rtype else ""
        if r_type_raw not in ("classroom", "lecture_theatre", "tutorial_room", "lab"):
            errors.append(
                f"Room '{rname}' type must be 'classroom', 'lecture_theatre', 'tutorial_room', or 'lab', got '{rtype}'."
            )

    # 4. Check teachers
    raw_teachers = raw.get("teachers", [])
    if not isinstance(raw_teachers, list) or len(raw_teachers) == 0:
        errors.append("At least one teacher must be defined.")

    teacher_names = set()
    for t in (raw_teachers if isinstance(raw_teachers, list) else []):
        if not isinstance(t, dict):
            errors.append(f"Invalid teacher item: {t}")
            continue
        tname = t.get("name")
        tsubjects = t.get("subjects", [])
        unavail = t.get("unavailable", [])
        max_load = t.get("max_load")
        avoid = t.get("avoid_periods", [])

        if not tname or not isinstance(tname, str):
            errors.append("Teacher name must be a non-empty string.")
        elif tname in teacher_names:
            errors.append(f"Duplicate teacher name: '{tname}'.")
        else:
            teacher_names.add(tname)

        if not isinstance(max_load, int) or max_load <= 0:
            errors.append(f"Teacher '{tname}' max_load must be a positive integer.")

        if not isinstance(tsubjects, list) or len(tsubjects) == 0:
            errors.append(f"Teacher '{tname}' must be qualified for at least one subject.")
        else:
            for sc in tsubjects:
                if sc not in subject_codes:
                    errors.append(f"Teacher '{tname}' teaches unknown subject code '{sc}'.")

        if isinstance(unavail, list):
            for item in unavail:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    d_val, p_val = item
                    if d_val not in days:
                        errors.append(f"Teacher '{tname}' unavailable day '{d_val}' not in days {days}.")
                    if not isinstance(p_val, int) or p_val < 1 or p_val > periods:
                        errors.append(f"Teacher '{tname}' unavailable period {p_val} must be 1..{periods}.")
                else:
                    errors.append(f"Teacher '{tname}' has invalid unavailable format {item}.")

        if isinstance(avoid, list):
            for ap in avoid:
                if not isinstance(ap, int) or ap < 1 or ap > periods:
                    errors.append(f"Teacher '{tname}' avoided period {ap} must be 1..{periods}.")

    # 5. Check classes
    raw_classes = raw.get("classes", [])
    if not isinstance(raw_classes, list) or len(raw_classes) == 0:
        errors.append("At least one class must be defined.")

    class_names = set()
    for c in (raw_classes if isinstance(raw_classes, list) else []):
        if not isinstance(c, dict):
            errors.append(f"Invalid class item: {c}")
            continue
        cname = c.get("name")
        strength = c.get("strength")
        csubjects = c.get("subjects", [])
        lunch = c.get("lunch_period")
        tmap = c.get("teacher_map", {})

        if not cname or not isinstance(cname, str):
            errors.append("Class name must be a non-empty string.")
        elif cname in class_names:
            errors.append(f"Duplicate class name: '{cname}'.")
        else:
            class_names.add(cname)

        if not isinstance(strength, int) or strength <= 0:
            errors.append(f"Class '{cname}' strength must be a positive integer.")

        if not isinstance(lunch, int) or lunch < 1 or lunch > periods:
            errors.append(f"Class '{cname}' lunch period ({lunch}) must be 1..{periods}.")
        elif lunch in breaks:
            errors.append(f"Class '{cname}' lunch period {lunch} conflicts with a designated break period.")

        if not isinstance(csubjects, list) or len(csubjects) == 0:
            errors.append(f"Class '{cname}' must have at least one subject.")
        else:
            for sc in csubjects:
                if sc not in subject_codes:
                    errors.append(f"Class '{cname}' takes unknown subject code '{sc}'.")

        if isinstance(tmap, dict):
            for sc, tn in tmap.items():
                if sc not in subject_codes:
                    errors.append(f"Class '{cname}' teacher_map has unknown subject '{sc}'.")
                if tn not in teacher_names:
                    errors.append(f"Class '{cname}' teacher_map assigns unknown teacher '{tn}'.")

    # 6. Relational checks
    # Every subject taken by a class has at least one teacher who can teach it
    for c in (raw_classes if isinstance(raw_classes, list) else []):
        cname = c.get("name")
        strength = c.get("strength", 0)
        csubjects = c.get("subjects", [])
        for sc in csubjects:
            qualified = [
                t.get("name") for t in raw_teachers
                if sc in t.get("subjects", [])
            ]
            if not qualified:
                errors.append(f"No teacher available who can teach subject '{sc}' taken by class '{cname}'.")

        # Every class has at least one room of the right type whose capacity is >= class strength
        has_classroom = any(
            str(r.get("type", "")).strip().lower().replace(" ", "_") in ("classroom", "lecture_theatre", "tutorial_room")
            and r.get("capacity", 0) >= strength
            for r in raw_rooms
        )
        has_lab = any(
            str(r.get("type", "")).strip().lower().replace(" ", "_") == "lab"
            and r.get("capacity", 0) >= strength
            for r in raw_rooms
        )
        has_tutorial = any(
            str(r.get("type", "")).strip().lower().replace(" ", "_") in ("tutorial_room", "classroom", "lecture_theatre")
            and r.get("capacity", 0) >= strength
            for r in raw_rooms
        )

        # Check if class takes theory and lab
        needs_theory = any(
            s.get("type") == "theory" for s in raw_subjects if s.get("code") in csubjects
        )
        # Dedicated lab needed only if subject requires 'lab' room type (default)
        needs_lab = any(
            s.get("type") == "lab" and s.get("room_type", "lab") == "lab"
            for s in raw_subjects if s.get("code") in csubjects
        )
        needs_tutorial_lab = any(
            s.get("type") == "lab" and s.get("room_type") in ("tutorial_room", "classroom")
            for s in raw_subjects if s.get("code") in csubjects
        )

        if needs_theory and not has_classroom:
            errors.append(f"Class '{cname}' (strength {strength}) has no classroom large enough.")
        if needs_lab and not has_lab:
            errors.append(f"Class '{cname}' (strength {strength}) has no lab large enough.")
        if needs_tutorial_lab and not has_tutorial:
            errors.append(f"Class '{cname}' (strength {strength}) has no tutorial room or classroom large enough for practical sessions.")

    return errors


def load_from_dict(raw: Dict[str, Any]) -> Data:
    """Construct a typed Data object from a dictionary.
    
    Converts 1-based period numbers into 0-based indices internally.
    """
    time_info = raw["time"]
    days = list(time_info["days"])
    day_to_idx = {d: i for i, d in enumerate(days)}
    periods = int(time_info["periods_per_day"])
    break_periods = {b - 1 for b in time_info.get("break_periods", [])}
    lab_block = int(time_info.get("lab_block", 2))

    subjects = {}
    for s in raw["subjects"]:
        subjects[s["code"]] = Subject(
            code=s["code"],
            name=s["name"],
            hours=int(s["hours"]),
            kind=s.get("type", "theory"),
            room_type=s.get("room_type"),
        )

    rooms = {}
    for r in raw["rooms"]:
        rtype = str(r.get("type", "classroom")).strip().lower().replace(" ", "_")
        rooms[r["name"]] = Room(
            name=r["name"],
            capacity=int(r["capacity"]),
            kind=rtype,
        )

    teachers = {}
    for t in raw["teachers"]:
        unavail = set()
        for item in t.get("unavailable", []):
            d_name, p_val = item[0], item[1]
            if d_name in day_to_idx and 1 <= p_val <= periods:
                unavail.add((day_to_idx[d_name], p_val - 1))
        
        avoid = {p - 1 for p in t.get("avoid_periods", []) if 1 <= p <= periods}

        teachers[t["name"]] = Teacher(
            name=t["name"],
            subjects=set(t.get("subjects", [])),
            unavailable=unavail,
            max_load=int(t["max_load"]),
            avoid_periods=avoid,
        )

    classes = {}
    for c in raw["classes"]:
        p_cls = c.get("parent_class")
        if not p_cls and c.get("parent_batch") and c.get("parent_batch") != c.get("name"):
            p_cls = c.get("parent_batch")

        classes[c["name"]] = SchoolClass(
            name=c["name"],
            strength=int(c["strength"]),
            subjects=list(c["subjects"]),
            lunch_period=int(c["lunch_period"]) - 1,
            teacher_map=dict(c.get("teacher_map", {})),
            parent_class=p_cls,
        )

    period_slots = list(time_info.get("period_slots", []))

    return Data(
        days=days,
        periods=periods,
        break_periods=break_periods,
        lab_block=lab_block,
        subjects=subjects,
        teachers=teachers,
        classes=classes,
        rooms=rooms,
        period_slots=period_slots,
    )


def load_json(file_path: str) -> Data:
    """Load and parse JSON file into a Data object."""
    with open(file_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    errors = validate_raw_data(raw)
    if errors:
        raise ValueError("Data validation failed:\n" + "\n".join(errors))
    return load_from_dict(raw)


def check_feasibility(data: Data) -> List[Dict[str, Any]]:
    """Run arithmetic tests to verify necessary conditions for a valid schedule.
    
    Returns a list of check records with:
    { "name": ..., "rule": ..., "passed": bool, "detail": ... }
    """
    results = []
    num_days = len(data.days)
    usable_slots_per_day = data.periods - len(data.break_periods) - 1  # 1 lunch period per class
    usable_slots_per_week = num_days * usable_slots_per_day

    # 1. Class capacity
    class_cap_pass = True
    class_cap_details = []
    for c in data.classes.values():
        total_hrs = sum(data.subjects[s].hours for s in c.subjects)
        limit = num_days * (data.periods - len(data.break_periods) - 1)
        if total_hrs > limit:
            class_cap_pass = False
            class_cap_details.append(f"Class '{c.name}' requires {total_hrs} hrs > max {limit} usable slots.")
        else:
            class_cap_details.append(f"Class '{c.name}': {total_hrs}/{limit} hrs ({total_hrs/limit:.0%})")
    results.append({
        "name": "Class capacity",
        "rule": "Total class weekly hours <= days x (periods - breaks - 1 lunch)",
        "passed": class_cap_pass,
        "detail": "; ".join(class_cap_details) if class_cap_pass else "; ".join(class_cap_details),
    })

    # 2. Teacher capacity
    # Calculate demand per teacher if assigned, or total demand vs total max load
    t_assigned_hours = {t: 0 for t in data.teachers}
    # Pre-estimate demand
    for c in data.classes.values():
        for s in c.subjects:
            hrs = data.subjects[s].hours
            fixed = c.teacher_map.get(s)
            if fixed and fixed in t_assigned_hours:
                t_assigned_hours[fixed] += hrs

    teacher_cap_pass = True
    teacher_cap_details = []
    total_slots_grid = num_days * data.periods
    for t in data.teachers.values():
        avail_slots = total_slots_grid - len(t.unavailable)
        limit = min(t.max_load, avail_slots)
        assigned = t_assigned_hours[t.name]
        if assigned > limit:
            teacher_cap_pass = False
            teacher_cap_details.append(f"Teacher '{t.name}' assigned {assigned} hrs exceeds limit {limit}.")
    results.append({
        "name": "Teacher capacity",
        "rule": "Teacher assigned hours <= max load and <= available slots",
        "passed": teacher_cap_pass,
        "detail": "All teachers have adequate capacity" if teacher_cap_pass else "; ".join(teacher_cap_details),
    })

    # 3. Classroom slots (any theory room: classroom, lecture_theatre, tutorial_room)
    classrooms = [
        r for r in data.rooms.values()
        if r.kind in ("classroom", "lecture_theatre", "tutorial_room")
    ]
    total_theory_hours = sum(
        data.subjects[s].hours
        for c in data.classes.values()
        for s in c.subjects
        if data.subjects[s].kind == "theory"
    )
    total_cr_slots = len(classrooms) * usable_slots_per_week
    cr_pass = total_theory_hours <= total_cr_slots
    cr_util = (total_theory_hours / total_cr_slots * 100) if total_cr_slots > 0 else 0
    results.append({
        "name": "Classroom slots",
        "rule": "Total theory hours <= usable classrooms x usable slots per week",
        "passed": cr_pass,
        "detail": f"{total_theory_hours} theory hrs vs {total_cr_slots} room slots ({cr_util:.1f}% utilisation)",
    })

    # 4. Lab slots & room capacity matching
    labs = [r for r in data.rooms.values() if r.kind == "lab"]
    total_lab_hours = sum(
        data.subjects[s].hours
        for c in data.classes.values()
        for s in c.subjects
        if data.subjects[s].kind == "lab"
    )
    total_lab_slots = len(labs) * usable_slots_per_week
    lab_pass = total_lab_hours <= total_lab_slots

    bottleneck_issues = []
    strengths_with_labs = sorted({
        c.strength for c in data.classes.values()
        if any(data.subjects[s].kind == "lab" for s in c.subjects)
    })
    for st in strengths_with_labs:
        st_demand = sum(
            data.subjects[s].hours
            for c in data.classes.values()
            if c.strength >= st
            for s in c.subjects
            if data.subjects[s].kind == "lab"
        )
        st_labs = [r for r in labs if r.capacity >= st]
        st_slots = len(st_labs) * usable_slots_per_week
        if len(st_labs) == 0:
            lab_pass = False
            bottleneck_issues.append(f"No lab has capacity >= {st} for classes of strength {st}")
        elif st_demand > st_slots:
            lab_pass = False
            bottleneck_issues.append(f"{st_demand} lab hrs needed for classes >= {st} students, but only {len(st_labs)} lab(s) fit them ({st_slots} slots)")

    lab_util = (total_lab_hours / total_lab_slots * 100) if total_lab_slots > 0 else 0
    if bottleneck_issues:
        lab_detail = "; ".join(bottleneck_issues)
    else:
        lab_detail = f"{total_lab_hours} lab hrs vs {total_lab_slots} lab slots ({lab_util:.1f}% utilisation)"

    results.append({
        "name": "Lab slots & room capacity",
        "rule": "Total lab hours <= usable labs, and labs must fit class strength",
        "passed": lab_pass,
        "detail": lab_detail,
    })

    # 5. Teacher coverage
    coverage_pass = True
    missing_coverage = []
    for sc, sub in data.subjects.items():
        qualified = [t.name for t in data.teachers.values() if sc in t.subjects]
        if not qualified:
            coverage_pass = False
            missing_coverage.append(sc)
    results.append({
        "name": "Teacher coverage",
        "rule": "Each subject has at least one qualified teacher",
        "passed": coverage_pass,
        "detail": "All subjects covered" if coverage_pass else f"No teacher for: {', '.join(missing_coverage)}",
    })

    # 6. Lab shape
    # Each lab block must fit in a day without crossing breaks or lunch
    lab_shape_pass = True
    lab_shape_details = []
    for c in data.classes.values():
        c_lab_subs = [data.subjects[s] for s in c.subjects if data.subjects[s].kind == "lab"]
        if not c_lab_subs:
            continue
        # Check if there is any start period p where p..p+lab_block-1 does not cross breaks or c.lunch_period
        valid_starts = 0
        for p in range(data.periods - data.lab_block + 1):
            slots = range(p, p + data.lab_block)
            if not any(q in data.break_periods or q == c.lunch_period for q in slots):
                valid_starts += 1
        if valid_starts == 0:
            lab_shape_pass = False
            lab_shape_details.append(f"Class '{c.name}' has no slot fitting {data.lab_block}-period lab blocks.")
    results.append({
        "name": "Lab shape",
        "rule": "Each lab block fits in a day without crossing a break or class lunch",
        "passed": lab_shape_pass,
        "detail": "Lab blocks fit cleanly" if lab_shape_pass else "; ".join(lab_shape_details),
    })

    return results


def assign_teachers(data: Data) -> Dict[Tuple[str, str], str]:
    """Assign teachers to each (class, subject) pair.
    
    Greedy assignment with load balancing. Guarantees constraint H8
    (maximum load) by construction.
    """
    load = {t: 0 for t in data.teachers}
    result: Dict[Tuple[str, str], str] = {}
    qualified = {s: [t for t in data.teachers.values() if s in t.subjects] for s in data.subjects}
    pairs = [(c.name, s) for c in data.classes.values() for s in c.subjects]
    # Sort pairs by fewest qualified teachers first (MRV on teachers)
    pairs.sort(key=lambda p: len(qualified[p[1]]))

    for c, s in pairs:
        hrs = data.subjects[s].hours
        fixed = data.classes[c].teacher_map.get(s)
        if fixed:
            t = data.teachers[fixed]
        else:
            ok = [t for t in qualified[s] if load[t.name] + hrs <= t.max_load]
            if not ok:
                raise ValueError(f"No teacher with spare load for {c}/{s}")
            # Balance load by ratio of assigned load to max_load
            t = min(ok, key=lambda t: load[t.name] / t.max_load)
        load[t.name] += hrs
        result[(c, s)] = t.name

    return result


def build_sessions(data: Data, teacher_of: Dict[Tuple[str, str], str]) -> List[Session]:
    """Build CSP variables: one variable is one session to be placed on the timetable."""
    sessions: List[Session] = []
    for c in data.classes.values():
        for code in c.subjects:
            sub = data.subjects[code]
            length = data.lab_block if sub.kind == "lab" else 1
            num_sessions = sub.hours // length
            for k in range(num_sessions):
                sessions.append(
                    Session(
                        sid=len(sessions),
                        cls=c.name,
                        subject=code,
                        teacher=teacher_of[(c.name, code)],
                        kind=sub.kind,
                        length=length,
                        idx=k,
                        parent_cls=c.parent_class,
                    )
                )
    return sessions


def build_domains(data: Data, sessions: List[Session]) -> Dict[int, List[Tuple[int, int, str]]]:
    """Build domain values for each session variable.
    
    A value is a triple (day, start_period, room).
    Filters unary constraints:
    - H4: Room capacity >= class strength
    - H5: Labs in lab rooms (or tutorial rooms/classrooms if configured), theory in classrooms
    - H6: Teacher only in available slots
    - H9: Breaks and class lunch periods free
    """
    domains: Dict[int, List[Tuple[int, int, str]]] = {}
    for s in sessions:
        c = data.classes[s.cls]
        t = data.teachers[s.teacher]
        sub = data.subjects[s.subject]
        
        target_room_type = sub.room_type if sub.room_type else ("lab" if s.kind == "lab" else "classroom")
        if target_room_type == "lab":
            allowed_room_kinds = ("lab",)
        elif target_room_type == "tutorial_room":
            allowed_room_kinds = ("tutorial_room", "classroom")
        else:
            allowed_room_kinds = ("classroom", "lecture_theatre", "tutorial_room")

        rooms = [
            r.name for r in data.rooms.values()
            if r.kind in allowed_room_kinds
            and r.capacity >= c.strength
        ]

        dom = []
        for d in range(len(data.days)):
            for p in range(data.periods - s.length + 1):
                slots = [(d, p + k) for k in range(s.length)]
                # Filter out break periods, lunch period (H9), and teacher unavailability (H6)
                if any(q[1] in data.break_periods or q[1] == c.lunch_period for q in slots):
                    continue
                if any(q in t.unavailable for q in slots):
                    continue
                for r in rooms:
                    dom.append((d, p, r))

        if not dom:
            raise ValueError(
                f"Domain for session {s.sid} ({s.cls}/{s.subject} #{s.idx}) is empty. Data is infeasible."
            )
        domains[s.sid] = dom

    return domains


def get_template_dict() -> Dict[str, Any]:
    """Return a clean template JSON dictionary for users to download."""
    return {
        "time": {
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "periods_per_day": 6,
            "break_periods": [3],
            "lab_block": 2,
        },
        "subjects": [
            {"code": "CS101", "name": "Programming Fundamentals", "hours": 4, "type": "theory"},
            {"code": "CS101L", "name": "Programming Lab", "hours": 2, "type": "lab"},
            {"code": "MA101", "name": "Calculus and Algebra", "hours": 4, "type": "theory"},
            {"code": "PH101", "name": "Physics", "hours": 3, "type": "theory"},
            {"code": "PH101L", "name": "Physics Lab", "hours": 2, "type": "lab"},
        ],
        "teachers": [
            {
                "name": "Dr. Sarah Adams",
                "subjects": ["CS101", "CS101L"],
                "unavailable": [["Mon", 1]],
                "max_load": 12,
                "avoid_periods": [1],
            },
            {
                "name": "Prof. David Miller",
                "subjects": ["MA101"],
                "unavailable": [["Fri", 6]],
                "max_load": 12,
                "avoid_periods": [6],
            },
            {
                "name": "Dr. Elena Vance",
                "subjects": ["PH101", "PH101L"],
                "unavailable": [],
                "max_load": 12,
                "avoid_periods": [],
            },
        ],
        "classes": [
            {
                "name": "CS-Year1",
                "strength": 40,
                "subjects": ["CS101", "CS101L", "MA101", "PH101", "PH101L"],
                "lunch_period": 4,
                "teacher_map": {},
            }
        ],
        "rooms": [
            {"name": "Room-101", "capacity": 50, "type": "classroom"},
            {"name": "Room-102", "capacity": 50, "type": "classroom"},
            {"name": "Lab-Alpha", "capacity": 45, "type": "lab"},
        ],
    }
