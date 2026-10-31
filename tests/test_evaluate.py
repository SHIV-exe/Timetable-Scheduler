"""Unit tests for the timetable evaluator (Section 5.4 in project specification).

Tests each scenario by hand with minimal Data objects to ensure the single source
of truth accurately catches each hard constraint violation and soft penalty.
"""

import pytest
from config import W
from core.model import Data, Subject, Teacher, SchoolClass, Room, Session
from core.evaluate import evaluate


@pytest.fixture
def base_data():
    """Minimal test data structure: 1 class, 2 teachers, 2 rooms (1 classroom, 1 lab), 5 days, 6 periods."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    periods = 6
    break_periods = {3}  # Period 4 (0-indexed 3) is a break
    lab_block = 2

    subjects = {
        "MATH": Subject(code="MATH", name="Mathematics", hours=4, kind="theory"),
        "PHYS": Subject(code="PHYS", name="Physics", hours=3, kind="theory"),
        "LAB1": Subject(code="LAB1", name="Lab Work", hours=2, kind="lab"),
    }

    teachers = {
        "T1": Teacher(name="T1", subjects={"MATH", "LAB1"}, unavailable=set(), max_load=20),
        "T2": Teacher(name="T2", subjects={"PHYS"}, unavailable=set(), max_load=20),
    }

    classes = {
        "C1": SchoolClass(name="C1", strength=30, subjects=["MATH", "PHYS", "LAB1"], lunch_period=4),  # Period 5 (index 4)
        "C2": SchoolClass(name="C2", strength=25, subjects=["MATH"], lunch_period=4),
    }

    rooms = {
        "R1": Room(name="R1", capacity=40, kind="classroom"),
        "R2": Room(name="R2", capacity=40, kind="classroom"),
        "L1": Room(name="L1", capacity=40, kind="lab"),
    }

    return Data(
        days=days,
        periods=periods,
        break_periods=break_periods,
        lab_block=lab_block,
        subjects=subjects,
        teachers=teachers,
        classes=classes,
        rooms=rooms,
    )


def test_h1_teacher_clash(base_data):
    """Two sessions, same teacher, same slot, different rooms and classes -> H1 = 1."""
    s0 = Session(sid=0, cls="C1", subject="MATH", teacher="T1", kind="theory", length=1, idx=0)
    s1 = Session(sid=1, cls="C2", subject="MATH", teacher="T1", kind="theory", length=1, idx=0)
    sessions = [s0, s1]

    # Both assigned to Monday (0), Period 1 (0), but different rooms (R1 and R2)
    asg = {0: (0, 0, "R1"), 1: (0, 0, "R2")}
    rep = evaluate(base_data, sessions, asg)

    assert rep.hard["H1"] == 1
    assert 0 in rep.conflicted and 1 in rep.conflicted


def test_h2_class_clash(base_data):
    """Two sessions, same class, same slot -> H2 = 1."""
    s0 = Session(sid=0, cls="C1", subject="MATH", teacher="T1", kind="theory", length=1, idx=0)
    s1 = Session(sid=1, cls="C1", subject="PHYS", teacher="T2", kind="theory", length=1, idx=0)
    sessions = [s0, s1]

    # Both assigned to Monday (0), Period 1 (0), different rooms and teachers
    asg = {0: (0, 0, "R1"), 1: (0, 0, "R2")}
    rep = evaluate(base_data, sessions, asg)

    assert rep.hard["H2"] == 1
    assert 0 in rep.conflicted and 1 in rep.conflicted


def test_h3_room_clash(base_data):
    """Two sessions, same room, same slot -> H3 = 1."""
    s0 = Session(sid=0, cls="C1", subject="MATH", teacher="T1", kind="theory", length=1, idx=0)
    s1 = Session(sid=1, cls="C2", subject="PHYS", teacher="T2", kind="theory", length=1, idx=0)
    sessions = [s0, s1]

    # Both assigned to Room R1 on Monday (0), Period 1 (0)
    asg = {0: (0, 0, "R1"), 1: (0, 0, "R1")}
    rep = evaluate(base_data, sessions, asg)

    assert rep.hard["H3"] == 1


def test_h5_wrong_room_type(base_data):
    """Theory session placed in a lab -> H5 = 1."""
    s0 = Session(sid=0, cls="C1", subject="MATH", teacher="T1", kind="theory", length=1, idx=0)
    sessions = [s0]

    # Placed in L1 (which is a lab)
    asg = {0: (0, 0, "L1")}
    rep = evaluate(base_data, sessions, asg)

    assert rep.hard["H5"] == 1
    assert 0 in rep.conflicted


def test_h9_lunch_period_violation(base_data):
    """Session in a class's lunch period -> H9 = 1."""
    s0 = Session(sid=0, cls="C1", subject="MATH", teacher="T1", kind="theory", length=1, idx=0)
    sessions = [s0]

    # C1 lunch period is 4 (Period 5)
    asg = {0: (0, 4, "R1")}
    rep = evaluate(base_data, sessions, asg)

    assert rep.hard["H9"] == 1


def test_range_violation(base_data):
    """A 2-period lab starting in the last period -> RANGE = 1."""
    s0 = Session(sid=0, cls="C1", subject="LAB1", teacher="T1", kind="lab", length=2, idx=0)
    sessions = [s0]

    # Starts at period index 5 (last period of 6 periods), runs through period 6 (out of range)
    asg = {0: (0, 5, "L1")}
    rep = evaluate(base_data, sessions, asg)

    assert rep.hard["RANGE"] == 1


def test_s1_gaps_penalty(base_data):
    """A class has sessions in periods 1 and 4 (indices 0 and 3) with 2 empty teachable periods between -> S1 = 2 * weight."""
    # Temporarily remove break and lunch to have 2 clean teachable empty periods (indices 1 and 2)
    base_data.break_periods = set()
    base_data.classes["C1"].lunch_period = 5

    s0 = Session(sid=0, cls="C1", subject="MATH", teacher="T1", kind="theory", length=1, idx=0)
    s1 = Session(sid=1, cls="C1", subject="PHYS", teacher="T2", kind="theory", length=1, idx=0)
    sessions = [s0, s1]

    # s0 at P1 (idx 0), s1 at P4 (idx 3). Gaps: indices 1 and 2 -> 2 empty periods
    asg = {0: (0, 0, "R1"), 1: (0, 3, "R1")}
    rep = evaluate(base_data, sessions, asg)

    assert rep.soft["S1"] == 2 * W["S1"]


def test_s5_consecutive_teacher_penalty(base_data):
    """Teacher with sessions in periods 1, 2, 3 -> S5 = 1 * weight."""
    s0 = Session(sid=0, cls="C1", subject="MATH", teacher="T1", kind="theory", length=1, idx=0)
    s1 = Session(sid=1, cls="C2", subject="MATH", teacher="T1", kind="theory", length=1, idx=1)
    s2 = Session(sid=2, cls="C1", subject="MATH", teacher="T1", kind="theory", length=1, idx=2)
    sessions = [s0, s1, s2]

    # Teacher T1 teaches in periods 0, 1, 2 consecutively on Monday -> 3 periods -> 1 beyond 2
    asg = {0: (0, 0, "R1"), 1: (0, 1, "R2"), 2: (0, 2, "R1")}
    rep = evaluate(base_data, sessions, asg)

    assert rep.soft["S5"] == 1 * W["S5"]


def test_h2_parent_cohort_subbatch_clash(base_data):
    """Sub-batch C1-A has a lab while parent cohort C1 has a lecture at the same time -> H2 violation."""
    base_data.classes["C1-A"] = SchoolClass(name="C1-A", strength=15, subjects=["LAB1"], lunch_period=4, parent_class="C1")
    s_parent = Session(sid=0, cls="C1", subject="MATH", teacher="T1", kind="theory", length=1, idx=0)
    s_child = Session(sid=1, cls="C1-A", subject="LAB1", teacher="T2", kind="lab", length=2, idx=0, parent_cls="C1")
    sessions = [s_parent, s_child]

    # s_child is at Monday P1-P2 (periods 0 and 1)
    # s_parent is placed at Monday P1 (period 0)
    asg = {0: (0, 0, "R1"), 1: (0, 0, "L1")}
    rep = evaluate(base_data, sessions, asg)

    assert rep.hard["H2"] >= 1
    assert any("H2: Sub-batch 'C1-A' lab conflicts with parent cohort 'C1'" in m for m in rep.messages)

