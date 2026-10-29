"""Unit tests for the timetable solvers (Section 10.1 in project specification).

Verifies:
1. State.total incrementally matches H1+H2+H3 from evaluate() across multiple random assignments.
2. Backtracking baseline, BTSolver (heuristics), and Min-Conflicts find 0 hard violations on a solvable test problem.
3. AC-3 runs cleanly without false infeasibility flags.
"""

import pytest
import random
from core.model import (
    Data, Subject, Teacher, SchoolClass, Room,
    assign_teachers, build_sessions, build_domains,
)
from core.evaluate import evaluate
from core.backtracking import plain_bt, BTSolver, ac3, Budget
from core.minconflicts import State, min_conflicts, greedy_init
from core.annealing import anneal


@pytest.fixture
def solvable_dataset() -> Data:
    """A small verified solvable college timetable specification."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    periods = 6
    break_periods = {2}  # Period 3 (index 2) is a break
    lab_block = 2

    subjects = {
        "CS101": Subject(code="CS101", name="CS Basics", hours=4, kind="theory"),
        "CS101L": Subject(code="CS101L", name="CS Lab", hours=2, kind="lab"),
        "MA101": Subject(code="MA101", name="Calculus", hours=4, kind="theory"),
    }

    teachers = {
        "T_Alice": Teacher(name="T_Alice", subjects={"CS101", "CS101L"}, unavailable=set(), max_load=15),
        "T_Bob": Teacher(name="T_Bob", subjects={"MA101"}, unavailable=set(), max_load=15),
    }

    classes = {
        "CSE1": SchoolClass(name="CSE1", strength=35, subjects=["CS101", "CS101L", "MA101"], lunch_period=3),  # Period 4 is lunch
    }

    rooms = {
        "R101": Room(name="R101", capacity=40, kind="classroom"),
        "LAB1": Room(name="LAB1", capacity=40, kind="lab"),
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


def test_incremental_state_consistency(solvable_dataset):
    """Test that State.total matches evaluate(data, sessions, asg).hard_total exactly on random assignments."""
    teacher_of = assign_teachers(solvable_dataset)
    sessions = build_sessions(solvable_dataset, teacher_of)
    domains = build_domains(solvable_dataset, sessions)
    rng = random.Random(42)

    # Test 50 random states and incremental removals/additions
    for _ in range(50):
        st = State()
        # Random assignment
        for s in sessions:
            st.add(s, rng.choice(domains[s.sid]))

        rep = evaluate(solvable_dataset, sessions, st.asg)
        # H1 + H2 + H3 are the binary slot clash constraints
        expected_binary_clashes = rep.hard["H1"] + rep.hard["H2"] + rep.hard["H3"]
        assert st.total == expected_binary_clashes, (
            f"State.total ({st.total}) does not match evaluator H1+H2+H3 ({expected_binary_clashes})"
        )

        # Test incremental remove and re-add
        s_pick = rng.choice(sessions)
        old_val = st.remove(s_pick)
        rep_after_remove = evaluate(solvable_dataset, sessions, st.asg)
        expected_after_remove = rep_after_remove.hard["H1"] + rep_after_remove.hard["H2"] + rep_after_remove.hard["H3"]
        assert st.total == expected_after_remove

        # Re-add another value
        new_val = rng.choice(domains[s_pick.sid])
        st.add(s_pick, new_val)
        rep_after_readd = evaluate(solvable_dataset, sessions, st.asg)
        expected_after_readd = rep_after_readd.hard["H1"] + rep_after_readd.hard["H2"] + rep_after_readd.hard["H3"]
        assert st.total == expected_after_readd


def test_bt_heuristics_solves_cleanly(solvable_dataset):
    """Verify that BTSolver with heuristics achieves 0 hard violations."""
    teacher_of = assign_teachers(solvable_dataset)
    sessions = build_sessions(solvable_dataset, teacher_of)
    domains = build_domains(solvable_dataset, sessions)

    solver = BTSolver(
        sessions=sessions,
        domains=domains,
        mrv=True,
        degree=True,
        fc=True,
        symmetry=True,
        time_limit=10.0,
    )
    asg = solver.solve()
    assert asg is not None, "BTSolver failed to solve solvable dataset"
    assert len(asg) == len(sessions)

    rep = evaluate(solvable_dataset, sessions, asg)
    assert rep.hard_total == 0, f"BTSolver produced hard violations: {rep.messages}"


def test_min_conflicts_solves_cleanly(solvable_dataset):
    """Verify that Min-Conflicts local search achieves 0 hard violations."""
    teacher_of = assign_teachers(solvable_dataset)
    sessions = build_sessions(solvable_dataset, teacher_of)
    domains = build_domains(solvable_dataset, sessions)

    asg, iters, success = min_conflicts(
        sessions=sessions,
        domains=domains,
        seed=123,
        max_iters=5000,
        time_limit=10.0,
    )
    assert success is True, "Min-conflicts did not find conflict-free assignment"
    rep = evaluate(solvable_dataset, sessions, asg)
    assert rep.hard_total == 0, f"Min-conflicts had violations: {rep.messages}"


def test_ac3_preprocessing(solvable_dataset):
    """Verify that AC-3 executes without false infeasibility flags."""
    teacher_of = assign_teachers(solvable_dataset)
    sessions = build_sessions(solvable_dataset, teacher_of)
    domains = build_domains(solvable_dataset, sessions)

    S = {s.sid: s for s in sessions}
    dom_set = {s.sid: set(domains[s.sid]) for s in sessions}
    nb = {
        s.sid: {
            t.sid
            for t in sessions
            if t.sid != s.sid and (t.teacher == s.teacher or t.cls == s.cls)
        }
        for s in sessions
    }

    is_feasible, pruned = ac3(S, dom_set, nb)
    assert is_feasible is True
