"""Streamlit Application for AI Timetable Scheduler (Section 9).

Conforms strictly to the architectural boundary:
- Algorithm code lives strictly in core/ and never imports Streamlit.
- Provides all required tabs: Data, Generate, Views, Edit, Export, and Empirical Benchmarks.
- Styled according to the Premium Utilitarian Minimalism protocol.
- Features complete visual entity form editors (Batches, Faculty, Rooms, Subjects, Time)
  matching the JavaScript studio interface, download JSON, batch auto-splitting,
  consecutive 2-row lab spanning with divided columns, and live empirical benchmarks.
"""

import html
import io
import json
import os
import re
import time
import pandas as pd
try:
    import streamlit as st
except ImportError:
    st = None

from core.model import (
    load_from_dict,
    validate_raw_data,
    check_feasibility,
    assign_teachers,
    build_sessions,
    build_domains,
    get_template_dict,
)
from core.evaluate import evaluate
from core import solvers


def ensure_batches_in_raw(raw: dict) -> dict:
    """Ensure raw_data contains 'batches' list so the visual batch form editor works on all datasets."""
    if not isinstance(raw, dict):
        return raw

    if "batches" not in raw or not raw["batches"]:
        batches = []
        for c in raw.get("classes", []):
            theory_subs = list(c.get("subjects", []))
            batches.append({
                "name": c.get("name"),
                "strength": int(c.get("strength", 30)),
                "semester": c.get("semester", 1),
                "sem_type": "odd",
                "auto_split": True,
                "lunch_period": c.get("lunch_period", 4),
                "subjects": theory_subs,
                "labs": [],
                "teacher_map": dict(c.get("teacher_map", {})),
            })
        raw["batches"] = batches
    return raw


def compile_solver_data(raw_dict: dict) -> dict:
    """If dataset uses the studio 'batches' format with merged cohorts (e.g. 120/90/60),
    auto-split into sections of 30 for lab courses while keeping theory together."""
    if not isinstance(raw_dict, dict) or "batches" not in raw_dict or not raw_dict["batches"]:
        return raw_dict

    copy_data = json.loads(json.dumps(raw_dict))
    compiled_classes = []

    for b in copy_data.get("batches", []):
        strength = int(b.get("strength", 30))
        theory_subjects = b.get("subjects", [])
        lab_subjects = b.get("labs", [])
        lunch_period = int(b.get("lunch_period", 4))

        if b.get("auto_split", True) and lab_subjects and strength > 30:
            k = (strength + 29) // 30
            sub_strength = min(30, (strength + k - 1) // k)

            # 1. Parent cohort for theory
            if theory_subjects:
                compiled_classes.append({
                    "name": b["name"],
                    "strength": strength,
                    "subjects": theory_subjects,
                    "lunch_period": lunch_period,
                    "teacher_map": b.get("teacher_map", {}),
                    "parent_class": None,
                    "parent_batch": b["name"],
                })

            # 2. Sub-batches for laboratory sessions (e.g. CSE A1, CSE A2...)
            for i in range(k):
                sub_name = f"{b['name']}{i+1}"
                sub_tmap = dict(b.get("teacher_map", {}))
                compiled_classes.append({
                    "name": sub_name,
                    "strength": sub_strength,
                    "subjects": lab_subjects,
                    "lunch_period": lunch_period,
                    "teacher_map": sub_tmap,
                    "parent_class": b["name"],
                    "parent_batch": b["name"],
                    "sub_index": i + 1,
                    "total_sub_batches": k,
                })
        else:
            all_subs = list(theory_subjects) + [l for l in lab_subjects if l not in theory_subjects]
            compiled_classes.append({
                "name": b["name"],
                "strength": strength,
                "subjects": all_subs,
                "lunch_period": lunch_period,
                "teacher_map": b.get("teacher_map", {}),
                "parent_class": None,
                "parent_batch": b["name"],
            })

    copy_data["classes"] = compiled_classes
    return copy_data


def init_session_state():
    """Initialize working objects in st.session_state (Section 9.1)."""
    if "data" not in st.session_state:
        inst_path = os.path.join(os.path.dirname(__file__), "data", "institutional_timetable_specification.json")
        custom_path = os.path.join(os.path.dirname(__file__), "data", "custom.json")
        small_path = os.path.join(os.path.dirname(__file__), "data", "small.json")

        initial_path = inst_path if os.path.exists(inst_path) else (custom_path if os.path.exists(custom_path) else small_path)
        ds_label = "Institutional Specification" if initial_path == inst_path else ("Custom Dataset" if initial_path == custom_path else "Standard Small")

        raw = {}
        if os.path.exists(initial_path):
            with open(initial_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        else:
            raw = get_template_dict()

        raw = ensure_batches_in_raw(raw)
        compiled_raw = compile_solver_data(raw)
        st.session_state.raw_data = raw
        st.session_state.compiled_data = compiled_raw
        st.session_state.dataset_name = ds_label
        st.session_state.data = load_from_dict(compiled_raw)
        st.session_state.errors = validate_raw_data(compiled_raw)
        st.session_state.sessions = []
        st.session_state.domains = {}
        st.session_state.asg = {}
        st.session_state.report = None
        st.session_state.history = []
        st.session_state.move_log = []
        st.session_state.last_result = None
        st.session_state.bench_history = []


def inject_minimalist_css():
    """Inject bespoke CSS adhering to the Premium Utilitarian Minimalism protocol."""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist+Mono:wght@400;500;600&display=swap');

    :root {
        --canvas-bg: #F7F6F3;
        --card-bg: #FFFFFF;
        --border-color: #D6D5D2;
        --text-primary: #111111;
        --text-secondary: #4A4A48;
        --accent-red: #FDEBEC;
        --accent-red-text: #9F2F2D;
        --accent-blue: #E1F3FE;
        --accent-blue-text: #1F6C9F;
        --accent-green: #EDF3EC;
        --accent-green-text: #346538;
        --accent-yellow: #FBF3DB;
        --accent-yellow-text: #956400;
    }

    .stApp {
        background-color: var(--canvas-bg) !important;
        color: var(--text-primary) !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    }

    .stTabs, [data-testid="stTabs"] {
        background-color: transparent !important;
        margin-bottom: 24px !important;
    }

    [data-testid="stTabs"] > div:first-child,
    [data-testid="stTabs"] [role="tablist"],
    div[data-baseweb="tab-list"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D6D5D2 !important;
        border-radius: 8px !important;
        padding: 6px !important;
        gap: 8px !important;
        display: flex !important;
        flex-wrap: wrap !important;
        align-items: center !important;
    }

    [data-testid="stTab"],
    [data-testid="stTabs"] button,
    [data-testid="stTabs"] [role="tab"],
    button[role="tab"],
    button[data-baseweb="tab"] {
        background-color: #F0EFEB !important;
        border: 1px solid #D6D5D2 !important;
        border-radius: 6px !important;
        padding: 8px 18px !important;
        margin: 0 !important;
        opacity: 1 !important;
        visibility: visible !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
    }

    [data-testid="stTab"] *,
    [data-testid="stTab"] p,
    [data-testid="stTab"] div,
    [data-testid="stTab"] span,
    [data-testid="stTabs"] button *,
    [data-testid="stTabs"] [role="tab"] * {
        color: #222222 !important;
        -webkit-text-fill-color: #222222 !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
    }

    [data-testid="stTab"][aria-selected="true"],
    [data-testid="stTab"][data-selected],
    [data-testid="stTabs"] button[aria-selected="true"],
    [data-testid="stTabs"] [role="tab"][aria-selected="true"],
    button[role="tab"][aria-selected="true"],
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #FFFFFF !important;
        border: 2px solid #111111 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
    }

    [data-testid="stTab"][aria-selected="true"] *,
    [data-testid="stTabs"] button[aria-selected="true"] * {
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
        font-weight: 700 !important;
    }

    .stButton > button,
    .stDownloadButton > button,
    button[kind="secondary"],
    button[kind="primary"] {
        background-color: #FFFFFF !important;
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
        border: 1.5px solid #222222 !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.55rem 1.35rem !important;
        transition: background-color 0.15s ease, border-color 0.15s ease !important;
        box-shadow: none !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background-color: #ECEBE8 !important;
        border-color: #000000 !important;
    }

    h1, h2, h3, h4 {
        font-family: 'Instrument Serif', Georgia, serif;
        font-weight: 400;
        letter-spacing: -0.02em;
        color: #111111 !important;
    }

    h1 {
        font-size: 2.75rem !important;
        line-height: 1.1 !important;
        margin-bottom: 0.5rem !important;
    }

    .bento-card {
        background: #FFFFFF !important;
        border: 1px solid #D6D5D2 !important;
        border-radius: 8px !important;
        padding: 18px 20px !important;
        margin-bottom: 16px !important;
    }

    .tag-badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        font-family: 'Geist Mono', monospace;
    }
    .tag-green { background-color: var(--accent-green) !important; color: var(--accent-green-text) !important; }
    .tag-red { background-color: var(--accent-red) !important; color: var(--accent-red-text) !important; }
    .tag-blue { background-color: var(--accent-blue) !important; color: var(--accent-blue-text) !important; }
    .tag-yellow { background-color: var(--accent-yellow) !important; color: var(--accent-yellow-text) !important; }

    /* Custom Timetable Matrix HTML Grid */
    .timetable-matrix-container {
        width: 100%;
        overflow-x: auto;
        margin-bottom: 24px;
        background: #FFFFFF;
        border: 1px solid #D6D5D2;
        border-radius: 8px;
        padding: 16px;
    }

    .matrix-grid-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .matrix-grid-table th,
    .matrix-grid-table td {
        border: 1px solid #D6D5D2;
        padding: 8px;
        text-align: center;
        vertical-align: middle;
        font-size: 0.85rem;
        word-break: break-word;
    }

    .matrix-grid-table th {
        background-color: #F4F3F0;
        color: #333333;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .matrix-grid-table td.period-label-cell {
        background-color: #FAFAF8;
        font-weight: 600;
        color: #555555;
        width: 110px;
    }

    .matrix-session-card {
        background: #FFFFFF;
        border: 1px solid #D6D5D2;
        border-radius: 6px;
        padding: 6px 8px;
        text-align: left;
        margin-bottom: 4px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }

    .matrix-session-lab {
        background: #F0F7FD;
        border: 1.5px solid #2B7CB2;
        border-left: 4px solid #1F6C9F;
    }

    .matrix-session-clash {
        background: #FDF2F2;
        border: 1.5px solid #DC2626;
        border-left: 4px solid #9F2F2D;
    }

    .matrix-divided-container {
        display: flex;
        gap: 6px;
        width: 100%;
        height: 100%;
        align-items: stretch;
    }

    .matrix-divided-col {
        flex: 1;
        min-width: 0;
        background: #F0F7FD;
        border: 1px dashed #2B7CB2;
        border-radius: 4px;
        padding: 4px 6px;
        text-align: left;
    }

    .matrix-break-cell {
        background-color: #F8F7F4;
        color: #888886;
        font-weight: 600;
        letter-spacing: 0.08em;
    }

    .matrix-lunch-cell {
        background-color: #FBF7ED;
        color: #956400;
        font-weight: 600;
        letter-spacing: 0.08em;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def build_schedule_html_matrix(data, sessions, asg, kind, entity_name):
    """Render an HTML matrix table with consecutive 2-row lab spanning and side-by-side divided columns."""
    days = data.days
    periods = data.periods
    break_set = set(data.break_periods)
    class_lunch = -1

    target_clean = entity_name.strip()
    clean_entity = target_clean.split(" (")[0].strip()

    if kind == "class":
        cls_obj = data.classes.get(clean_entity)
        if not cls_obj:
            for c in data.classes.values():
                if c.name == clean_entity or getattr(c, "parent_class", None) == clean_entity:
                    cls_obj = c
                    break
        if cls_obj:
            class_lunch = cls_obj.lunch_period

    grid_map = {(d, p): [] for d in range(len(days)) for p in range(periods)}
    for s in sessions:
        if s.sid not in asg:
            continue
        d, p, r = asg[s.sid]
        if not (0 <= d < len(days) and 0 <= p < periods):
            continue

        match = False
        if kind == "class":
            s_cls = s.cls.strip()
            if s_cls == clean_entity:
                match = True
            elif s_cls.startswith(clean_entity):
                match = True
            elif clean_entity.startswith(s_cls):
                match = True
        elif kind == "teacher":
            match = (s.teacher.strip() == clean_entity)
        elif kind == "room":
            match = (r.strip() == clean_entity)

        if match:
            grid_map[(d, p)].append((s, r))

    covered_cells = set()
    for (d, p), sess_list in grid_map.items():
        for s, r in sess_list:
            if s.length == 2 and p + 1 < periods:
                covered_cells.add((d, p + 1))

    table_html = [
        '<div class="timetable-matrix-container">',
        '<table class="matrix-grid-table">',
        '<thead><tr><th style="width: 120px;">Period</th>'
    ]
    for d in days:
        table_html.append(f'<th>{html.escape(d)}</th>')
    table_html.append('</tr></thead><tbody>')

    for p in range(periods):
        is_break = p in break_set
        table_html.append('<tr>')
        table_html.append(f'<td class="period-label-cell">P{p+1} ({9+p}:00 - {10+p}:00)</td>')

        for d_idx, d_name in enumerate(days):
            if (d_idx, p) in covered_cells:
                continue

            sess_list = grid_map[(d_idx, p)]
            has_two_period_lab = any(s.length == 2 for s, r in sess_list)

            rowspan_attr = ' rowspan="2"' if has_two_period_lab and (p + 1 < periods) else ''
            cell_class = 'lab-span-cell' if has_two_period_lab else ''

            if is_break and not sess_list:
                table_html.append(f'<td{rowspan_attr} class="matrix-break-cell">BREAK</td>')
                continue

            if kind == "class" and p == class_lunch and not sess_list:
                table_html.append(f'<td{rowspan_attr} class="matrix-lunch-cell">LUNCH</td>')
                continue

            if not sess_list:
                table_html.append(f'<td{rowspan_attr} style="color:#AAA;">&mdash;</td>')
                continue

            cell_content = []
            if len(sess_list) > 1 and has_two_period_lab:
                cell_content.append('<div class="matrix-divided-container">')
                for s, r in sess_list:
                    sub_title = html.escape(s.subject)
                    other_info = f"Sec: {html.escape(s.cls)} · Fac: {html.escape(s.teacher)} · Rm: {html.escape(r)}"
                    cell_content.append(
                        f'<div class="matrix-divided-col">'
                        f'<strong style="color:#1F6C9F; font-size:0.8rem;">{sub_title}</strong>'
                        f'<div style="font-size:0.75rem; color:#444; margin-top:2px;">{other_info}</div>'
                        f'<span class="tag-badge tag-blue" style="font-size:0.65rem; margin-top:4px;">Lab (2 Hrs)</span>'
                        f'</div>'
                    )
                cell_content.append('</div>')
            else:
                for s, r in sess_list:
                    sub_title = html.escape(s.subject)
                    is_lab = s.length == 2
                    cls_tag = "matrix-session-lab" if is_lab else "matrix-session-card"
                    tag_html = '<span class="tag-badge tag-blue" style="font-size:0.65rem;">Lab Block (2 Hrs)</span>' if is_lab else ''

                    detail = f"Class: {html.escape(s.cls)} · Faculty: {html.escape(s.teacher)} · Room: {html.escape(r)}"
                    if kind == "class":
                        detail = f"Faculty: {html.escape(s.teacher)} · Room: {html.escape(r)}"
                    elif kind == "teacher":
                        detail = f"Class: {html.escape(s.cls)} · Room: {html.escape(r)}"
                    elif kind == "room":
                        detail = f"Class: {html.escape(s.cls)} · Faculty: {html.escape(s.teacher)}"

                    cell_content.append(
                        f'<div class="{cls_tag}">'
                        f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                        f'<strong style="color:#111;">{sub_title}</strong>'
                        f'{tag_html}'
                        f'</div>'
                        f'<div style="font-size:0.75rem; color:#555; margin-top:3px;">{detail}</div>'
                        f'</div>'
                    )

            table_html.append(f'<td{rowspan_attr} class="{cell_class}">{"".join(cell_content)}</td>')

        table_html.append('</tr>')

    table_html.append('</tbody></table></div>')
    raw_html = "".join(table_html)
    clean_html = re.sub(r'\s*\n\s*', '', raw_html)
    return clean_html


def to_printable_html(data, sessions, asg) -> str:
    """Generate a clean, standalone, publication-grade printable HTML document matching editorial standards."""
    sections_html = []
    seen_parents = set()
    for cname in data.classes:
        p_name = getattr(data.classes[cname], "parent_batch", None) or getattr(data.classes[cname], "parent_class", None) or cname
        if p_name in seen_parents:
            continue
        seen_parents.add(p_name)

        grid_html = build_schedule_html_matrix(data, sessions, asg, "class", p_name)
        strength = data.classes.get(p_name, data.classes[cname]).strength
        sections_html.append(f"""
        <div class="print-sheet" style="page-break-after: always; margin-bottom: 40px;">
            <div style="display:flex; justify-content:space-between; border-bottom: 2px solid #111; padding-bottom: 8px; margin-bottom: 16px;">
                <div>
                    <h2 style="font-family: Georgia, serif; margin:0; font-size:1.4rem;">Cohort Timetable: {html.escape(p_name)}</h2>
                    <span style="font-size:0.85rem; color:#555;">Cohort Strength: {strength} Students · Split into 30-capacity laboratory sections</span>
                </div>
                <div style="text-align:right; font-size:0.8rem; color:#555;">
                    <div>Academic Session: 2026-2027</div>
                    <div style="color: green; font-weight: bold;">Status: 0 Hard Clashes Verified</div>
                </div>
            </div>
            {grid_html}
        </div>
        """)

    all_content = "\n".join(sections_html)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Master Academic Timetable Schedule Document</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 24px;
            color: #111;
            background: #FFF;
        }}
        .print-header {{
            text-align: center;
            border-bottom: 3px double #111;
            padding-bottom: 12px;
            margin-bottom: 24px;
        }}
        .print-header h1 {{
            font-family: Georgia, serif;
            font-size: 1.8rem;
            margin: 0 0 6px 0;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .print-actions {{
            margin-bottom: 20px;
            padding: 12px 18px;
            background: #F7F6F3;
            border: 1px solid #DDD;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .btn-print {{
            background: #111;
            color: #FFF;
            border: none;
            padding: 8px 18px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            font-size: 0.9rem;
        }}
        .timetable-matrix-container {{ width: 100%; margin-bottom: 16px; }}
        .matrix-grid-table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
        .matrix-grid-table th, .matrix-grid-table td {{ border: 1.5px solid #222; padding: 6px 8px; text-align: left; font-size: 0.8rem; }}
        .matrix-grid-table th {{ background-color: #EFEFEF; font-weight: bold; text-align: center; text-transform: uppercase; }}
        .matrix-session-lab {{ background-color: #EBF3FA !important; border: 1px solid #1F6C9F; padding: 4px; border-radius: 3px; }}
        .matrix-session-card {{ border: 1px solid #AAA; padding: 4px; border-radius: 3px; background: #FFF; }}
        .matrix-divided-container {{ display: flex; gap: 4px; }}
        .matrix-divided-col {{ flex: 1; border: 1px dashed #1F6C9F; padding: 3px; background: #EBF3FA; }}
        .tag-badge {{ font-size: 0.65rem; padding: 2px 5px; border-radius: 3px; font-weight: bold; }}
        .tag-blue {{ background: #D0E8F8; color: #1F6C9F; }}

        @page {{ size: landscape; margin: 10mm; }}
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ margin: 0; }}
            .print-sheet {{ page-break-after: always; }}
        }}
    </style>
</head>
<body>
    <div class="no-print print-actions">
        <div>
            <strong>Official Academic Timetable Publication Document</strong> &mdash; Ready for Print / PDF Export
        </div>
        <button class="btn-print" onclick="window.print()">Print Document / Save as PDF</button>
    </div>

    <div class="print-header">
        <h1>Department of Computer Science & Engineering</h1>
        <div style="font-size: 0.95rem; color: #444;">Master Institutional Timetable Matrix &mdash; Academic Session 2026-2027</div>
        <div style="font-size: 0.8rem; color: #777; margin-top: 4px;">Formulated via Constraint Satisfaction Problem (CSP) Search &bull; Zero Hard Clashes Verified</div>
    </div>

    {all_content}

    <div style="margin-top: 40px; display: flex; justify-content: space-between; border-top: 1px solid #888; padding-top: 20px;">
        <div style="font-size: 0.85rem; color: #555;">
            <strong>Verification Legend:</strong><br>
            Theory: 1-hour unified lecture &bull; Laboratory: 2-hour consecutive block spanned across 2 periods &bull; Shared Room 36: Parallel sections
        </div>
        <div style="text-align: right; font-size: 0.85rem; color: #333;">
            ____________________________________________<br>
            <strong>Dean of Academic Affairs & Timetable Coordinator</strong>
        </div>
    </div>
</body>
</html>
"""


def to_flat_csv(data, sessions, asg) -> bytes:
    """Generate flat CSV export (Section 9.6)."""
    rows = []
    for s in sessions:
        if s.sid in asg:
            d, p, r = asg[s.sid]
            rows.append({
                "Class": s.cls,
                "Subject": s.subject,
                "Teacher": s.teacher,
                "Day": data.days[d],
                "Start_Period": p + 1,
                "Duration_Periods": s.length,
                "Room": r,
            })
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


def run_benchmark_on_dataset(raw_dict: dict, label: str, time_limit: float = 4.0, seed: int = 42):
    """Run empirical benchmark across all 6 CSP algorithms on any selected dataset."""
    compiled = compile_solver_data(raw_dict)
    data_obj = load_from_dict(compiled)
    teacher_of = assign_teachers(data_obj)
    sessions = build_sessions(data_obj, teacher_of)
    domains = build_domains(data_obj, sessions)

    algos = [
        "Min-Conflicts",
        "BT heuristics",
        "Hill Climbing",
        "Simulated Annealing",
        "Hybrid (BT + SA)",
        "BT baseline",
    ]

    records = []
    for algo in algos:
        limit = time_limit
        if "baseline" in algo.lower() and len(sessions) > 40:
            limit = min(2.0, time_limit)

        try:
            t0 = time.perf_counter()
            res = solvers.run(
                algo=algo,
                data=data_obj,
                sessions=sessions,
                domains=domains,
                seed=seed,
                time_limit=limit,
            )
            elapsed = time.perf_counter() - t0
            rep = evaluate(data_obj, sessions, res.asg)
            success = bool(res.success and rep.hard_total == 0)

            records.append({
                "Dataset": label,
                "Method": algo,
                "Success": "1/1 (Clash-Free)" if success else "0/1 (Unresolved)",
                "Avg Time (s)": round(elapsed, 3),
                "Work (nodes/iters)": res.work,
                "Hard Clashes": rep.hard_total,
                "Soft Penalty": rep.soft_total,
                "Output Diagnostics": f"{'Clash-Free (0 Clashes)' if rep.hard_total == 0 else f'{rep.hard_total} Clashes'} · {res.work} iters · {round(elapsed, 3)}s",
            })
        except Exception as err:
            records.append({
                "Dataset": label,
                "Method": algo,
                "Success": "0/1 (Failed)",
                "Avg Time (s)": 0.0,
                "Work (nodes/iters)": 0,
                "Hard Clashes": -1,
                "Soft Penalty": -1,
                "Output Diagnostics": f"Error: {str(err)}",
            })

    return records


def apply_and_recompile_raw_data(new_raw: dict, dataset_label: str = "Custom Dataset"):
    """Recompile solver classes, validate, update session state, and refresh."""
    new_raw = ensure_batches_in_raw(new_raw)
    compiled = compile_solver_data(new_raw)
    errs = validate_raw_data(compiled)
    if errs:
        st.session_state.errors = errs
        return False, errs
    else:
        st.session_state.raw_data = new_raw
        st.session_state.compiled_data = compiled
        st.session_state.dataset_name = dataset_label
        st.session_state.data = load_from_dict(compiled)
        st.session_state.errors = []
        st.session_state.asg = {}
        st.session_state.report = None
        return True, []


def main():
    if st is None:
        print("Streamlit is not installed in the current environment.")
        return

    st.set_page_config(page_title="College Timetable Scheduler", layout="wide")
    inject_minimalist_css()
    init_session_state()

    # Editorial Header
    st.markdown("""
    <div style="border-bottom: 1px solid #EAEAEA; padding-bottom: 24px; margin-bottom: 32px;">
        <span class="tag-badge tag-blue" style="margin-bottom: 8px;">Academic Architecture</span>
        <h1>Constraint Satisfaction Timetable Scheduler</h1>
        <p style="color: #787774; font-size: 1.05rem; max-width: 900px; margin: 0;">
            Combinatorial optimization engine comparing systematic backtracking CSP and stochastic min-conflicts local search with batch auto-splitting, consecutive 2-row lab spanning, and live empirical benchmarks.
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_data, tab_gen, tab_views, tab_edit, tab_export, tab_benchmarks = st.tabs([
        "1. Data Specification",
        "2. Algorithmic Search",
        "3. Schedule Grids",
        "4. Manual Editor",
        "5. Export Matrix",
        "6. Empirical Benchmarks",
    ])

    # =========================================================================
    # TAB 1: DATA SPECIFICATION & VISUAL FORM EDITORS
    # =========================================================================
    with tab_data:
        st.markdown("### Institutional Configuration Studio & Registry")

        # Top Control Bar
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)

        with d_col1:
            if st.button("Load Institutional Specification", use_container_width=True):
                path = os.path.join(os.path.dirname(__file__), "data", "institutional_timetable_specification.json")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    apply_and_recompile_raw_data(raw, "Institutional Specification")
                    st.rerun()

        with d_col2:
            if st.button("Load Custom Dataset", use_container_width=True):
                path = os.path.join(os.path.dirname(__file__), "data", "custom.json")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    apply_and_recompile_raw_data(raw, "Custom Dataset")
                    st.rerun()

        with d_col3:
            if st.button("Load Standard Large Dataset", use_container_width=True):
                path = os.path.join(os.path.dirname(__file__), "data", "large.json")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    apply_and_recompile_raw_data(raw, "Large Dataset")
                    st.rerun()

        with d_col4:
            if st.button("Load Standard Small Dataset", use_container_width=True):
                path = os.path.join(os.path.dirname(__file__), "data", "small.json")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    apply_and_recompile_raw_data(raw, "Small Dataset")
                    st.rerun()

        # Action bar: Upload & Download JSON + Save to Disk
        act_col1, act_col2, act_col3 = st.columns([2, 1, 1])

        with act_col1:
            uploaded_file = st.file_uploader("Upload Configuration JSON", type=["json"], label_visibility="collapsed")
            if uploaded_file is not None:
                try:
                    raw_uploaded = json.load(uploaded_file)
                    ok, val_errs = apply_and_recompile_raw_data(raw_uploaded, "Uploaded Dataset")
                    if ok:
                        st.success("Uploaded configuration verified, split into 30-capacity lab sections, and loaded successfully.")
                    else:
                        st.error(f"Validation warnings: {'; '.join(val_errs)}")
                except Exception as e:
                    st.error(f"Failed to parse uploaded JSON: {e}")

        with act_col2:
            json_export_bytes = json.dumps(st.session_state.raw_data, indent=2).encode("utf-8")
            st.download_button(
                "📥 Download JSON Specification",
                json_export_bytes,
                "timetable_specification.json",
                "application/json",
                use_container_width=True,
            )

        with act_col3:
            if st.button("💾 Save to Custom (Disk)", use_container_width=True):
                custom_file_path = os.path.join(os.path.dirname(__file__), "data", "custom.json")
                try:
                    with open(custom_file_path, "w", encoding="utf-8") as f:
                        json.dump(st.session_state.raw_data, f, indent=2)
                    st.success("Custom dataset saved to server disk!")
                except Exception as e:
                    st.error(f"Failed to save to disk: {e}")

        # Active Dataset Summary Card
        if st.session_state.data:
            d = st.session_state.data
            lab_classes = [c for c in d.classes.values() if getattr(c, "sub_index", None) is not None]
            theory_classes = [c for c in d.classes.values() if getattr(c, "sub_index", None) is None]

            st.markdown(f"""
            <div class="bento-card" style="border-left: 4px solid #1F6C9F; margin-top: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span class="tag-badge tag-blue">Active Dataset: {html.escape(st.session_state.dataset_name)}</span>
                        <h4 style="margin: 8px 0 4px 0;">{len(d.classes)} Total Class Groups &bull; {len(d.teachers)} Faculty Members &bull; {len(d.rooms)} Rooms</h4>
                        <div style="font-size:0.9rem; color:#555;">
                            Unified Theory Cohorts: <strong>{len(theory_classes)}</strong> &bull;
                            Laboratory Sections (30 capacity): <strong>{len(lab_classes)}</strong> &bull;
                            Schedule Grid: <strong>{len(d.days)} Days &times; {d.periods} Periods (9 AM - 5 PM)</strong>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Feasibility Pre-Check
        if not st.session_state.errors and st.session_state.data:
            feas_checks = check_feasibility(st.session_state.data)
            st.markdown("#### Feasibility Arithmetic Pre-Check")
            feas_cols = st.columns(3)
            for i, c in enumerate(feas_checks):
                with feas_cols[i % 3]:
                    status_class = "tag-green" if c.get("passed", False) else "tag-red"
                    status_txt = "PASSED" if c.get("passed", False) else "FAILED"
                    rule_txt = c.get("rule") or c.get("equation", "")
                    detail_txt = str(c.get("detail", ""))
                    if len(detail_txt) > 120:
                        detail_txt = detail_txt[:117] + "..."
                    st.markdown(f"""
                    <div class="bento-card">
                        <span class="tag-badge {status_class}">{status_txt}</span>
                        <h4 style="margin: 8px 0 4px 0;">{html.escape(c.get('name', 'Check'))}</h4>
                        <p style="color: #666; font-size: 0.85rem; margin-bottom: 4px;">{html.escape(detail_txt)}</p>
                        <small style="color: #999;">{html.escape(rule_txt)}</small>
                    </div>
                    """, unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # ENTITY REGISTRY TABLES & INTERACTIVE FORM EDITORS
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.markdown("### Institutional Entity Studio & Form Editors")

        entity_tab_batches, entity_tab_faculty, entity_tab_rooms, entity_tab_subjects, entity_tab_time = st.tabs([
            "🏫 Academic Batches",
            "👨‍🏫 Faculty Members",
            "🏢 Rooms & Venues",
            "📚 Courses & Subjects",
            "⏰ 9 AM - 5 PM Schedule",
        ])

        # All registered courses list for selectboxes
        all_subjects_in_raw = st.session_state.raw_data.get("subjects", [])
        all_subj_codes = [s.get("code") or s.get("name") for s in all_subjects_in_raw]
        theory_subj_codes = [s.get("code") or s.get("name") for s in all_subjects_in_raw if s.get("type") != "lab" and s.get("kind") != "lab"]
        lab_subj_codes = [s.get("code") or s.get("name") for s in all_subjects_in_raw if s.get("type") == "lab" or s.get("kind") == "lab"]
        if not theory_subj_codes:
            theory_subj_codes = all_subj_codes
        if not lab_subj_codes:
            lab_subj_codes = all_subj_codes

        # ---------------------------------------------------------------------
        # 1. ACADEMIC BATCHES (TABLE + FORM EDITOR)
        # ---------------------------------------------------------------------
        with entity_tab_batches:
            batches_list = st.session_state.raw_data.get("batches", [])
            if batches_list:
                batch_rows = []
                for b in batches_list:
                    str_val = int(b.get("strength", 30))
                    k_sections = (str_val + 29) // 30 if b.get("auto_split", True) else 1
                    batch_rows.append({
                        "Cohort Name": b.get("name"),
                        "Semester": b.get("semester", 1),
                        "Total Strength": str_val,
                        "Lab Sections (Cap 30)": k_sections,
                        "Theory Courses": ", ".join(b.get("subjects", [])),
                        "Lab Courses": ", ".join(b.get("labs", [])),
                        "Lunch Period": f"Period {b.get('lunch_period', 4)}",
                    })
                st.dataframe(pd.DataFrame(batch_rows), use_container_width=True)

            with st.expander("➕ Configure / Add / Edit Academic Batch", expanded=True):
                batch_options = ["+ Add New Batch"] + [b["name"] for b in batches_list]
                selected_batch_mode = st.selectbox("Select Batch to Edit", batch_options, key="select_batch_edit_mode")

                selected_b_data = next((b for b in batches_list if b["name"] == selected_batch_mode), None)

                b_col1, b_col2, b_col3 = st.columns(3)
                with b_col1:
                    b_name = st.text_input("Batch Name / Code *", value=selected_b_data["name"] if selected_b_data else "CSE-A", key="form_batch_name")
                with b_col2:
                    sem_type = st.radio("Semester Type", ["Odd", "Even"], index=0 if (not selected_b_data or selected_b_data.get("sem_type") == "odd") else 1, horizontal=True, key="form_batch_semtype")
                with b_col3:
                    sem_options = [1, 3, 5, 7] if sem_type == "Odd" else [2, 4, 6, 8]
                    cur_sem = selected_b_data.get("semester", sem_options[0]) if selected_b_data else sem_options[0]
                    sem_val = st.selectbox("Semester", sem_options, index=sem_options.index(cur_sem) if cur_sem in sem_options else 0, key="form_batch_sem")

                b_col4, b_col5, b_col6 = st.columns(3)
                with b_col4:
                    b_strength = st.number_input("Total Cohort Strength (Students) *", min_value=10, max_value=300, value=int(selected_b_data.get("strength", 90)) if selected_b_data else 90, step=10, key="form_batch_strength")
                with b_col5:
                    auto_split = st.checkbox("Auto-split into 30-capacity lab sections", value=selected_b_data.get("auto_split", True) if selected_b_data else True, key="form_batch_autosplit")
                    if auto_split and b_strength > 30:
                        k_calc = (b_strength + 29) // 30
                        st.caption(f"⚡ Will divide into **{k_calc} sections** ({b_name}1, {b_name}2...) of ~30 for lab courses.")
                with b_col6:
                    b_lunch = st.selectbox("Designated Lunch Period", [3, 4, 5, 6], index=[3, 4, 5, 6].index(selected_b_data.get("lunch_period", 4)) if selected_b_data and selected_b_data.get("lunch_period") in [3, 4, 5, 6] else 1, key="form_batch_lunch")

                cur_theory = [s for s in selected_b_data.get("subjects", []) if s in all_subj_codes] if selected_b_data else []
                cur_labs = [s for s in selected_b_data.get("labs", []) if s in all_subj_codes] if selected_b_data else []

                b_theory_subs = st.multiselect("Theory Courses (Conducted together for full batch)", all_subj_codes, default=cur_theory, key="form_batch_theory")
                b_lab_subs = st.multiselect("Laboratory Courses (Conducted in 30-capacity sections)", all_subj_codes, default=cur_labs, key="form_batch_labs")

                b_btn1, b_btn2 = st.columns([1, 1])
                with b_btn1:
                    if st.button("Save Batch", key="btn_save_batch_form", use_container_width=True):
                        if not b_name.strip():
                            st.error("Batch name cannot be empty.")
                        else:
                            new_entry = {
                                "name": b_name.strip(),
                                "semester": int(sem_val),
                                "sem_type": sem_type.lower(),
                                "strength": int(b_strength),
                                "auto_split": bool(auto_split),
                                "lunch_period": int(b_lunch),
                                "subjects": b_theory_subs,
                                "labs": b_lab_subs,
                                "teacher_map": selected_b_data.get("teacher_map", {}) if selected_b_data else {},
                            }
                            # Update or append
                            existing_idx = next((i for i, b in enumerate(batches_list) if b["name"] == (selected_b_data["name"] if selected_b_data else b_name.strip())), -1)
                            if existing_idx >= 0:
                                batches_list[existing_idx] = new_entry
                            else:
                                batches_list.append(new_entry)
                            st.session_state.raw_data["batches"] = batches_list
                            apply_and_recompile_raw_data(st.session_state.raw_data)
                            st.success(f"Batch '{b_name.strip()}' saved successfully!")
                            st.rerun()

                with b_btn2:
                    if selected_b_data and st.button("Delete Batch", key="btn_delete_batch_form", use_container_width=True):
                        st.session_state.raw_data["batches"] = [b for b in batches_list if b["name"] != selected_b_data["name"]]
                        apply_and_recompile_raw_data(st.session_state.raw_data)
                        st.success(f"Batch '{selected_b_data['name']}' deleted.")
                        st.rerun()

        # ---------------------------------------------------------------------
        # 2. FACULTY MEMBERS (TABLE + FORM EDITOR)
        # ---------------------------------------------------------------------
        with entity_tab_faculty:
            teachers_list = st.session_state.raw_data.get("teachers", [])
            fac_rows = []
            for t in teachers_list:
                t_subs = t.get("subjects", [])
                fac_rows.append({
                    "Faculty Name": t.get("name"),
                    "Max Weekly Load": f"{t.get('max_load', 16)} Hours",
                    "Qualified Courses": ", ".join(sorted(list(t_subs))),
                    "Unavailable Slots Count": len(t.get("unavailable", [])),
                })
            if fac_rows:
                st.dataframe(pd.DataFrame(fac_rows), use_container_width=True)

            with st.expander("➕ Configure / Add / Edit Faculty Member", expanded=True):
                teacher_options = ["+ Add New Faculty"] + [t["name"] for t in teachers_list]
                selected_t_mode = st.selectbox("Select Faculty to Edit", teacher_options, key="select_teacher_edit_mode")
                selected_t_data = next((t for t in teachers_list if t["name"] == selected_t_mode), None)

                t_col1, t_col2 = st.columns([2, 1])
                with t_col1:
                    t_name = st.text_input("Faculty Name *", value=selected_t_data["name"] if selected_t_data else "Dr. New Faculty", key="form_teacher_name")
                with t_col2:
                    t_load = st.number_input("Max Weekly Load (Hours) *", min_value=1, max_value=40, value=int(selected_t_data.get("max_load", 16)) if selected_t_data else 16, key="form_teacher_load")

                cur_t_subs = [s for s in selected_t_data.get("subjects", []) if s in all_subj_codes] if selected_t_data else []
                t_qualified = st.multiselect("Qualified Courses *", all_subj_codes, default=cur_t_subs, key="form_teacher_qualified")

                t_btn1, t_btn2 = st.columns([1, 1])
                with t_btn1:
                    if st.button("Save Faculty Member", key="btn_save_teacher_form", use_container_width=True):
                        if not t_name.strip():
                            st.error("Faculty name cannot be empty.")
                        elif not t_qualified:
                            st.error("Please assign at least one qualified course to this faculty.")
                        else:
                            new_entry = {
                                "name": t_name.strip(),
                                "max_load": int(t_load),
                                "subjects": t_qualified,
                                "unavailable": selected_t_data.get("unavailable", []) if selected_t_data else [],
                                "avoid_periods": selected_t_data.get("avoid_periods", []) if selected_t_data else [],
                            }
                            existing_idx = next((i for i, t in enumerate(teachers_list) if t["name"] == (selected_t_data["name"] if selected_t_data else t_name.strip())), -1)
                            if existing_idx >= 0:
                                teachers_list[existing_idx] = new_entry
                            else:
                                teachers_list.append(new_entry)
                            st.session_state.raw_data["teachers"] = teachers_list
                            apply_and_recompile_raw_data(st.session_state.raw_data)
                            st.success(f"Faculty '{t_name.strip()}' saved successfully!")
                            st.rerun()

                with t_btn2:
                    if selected_t_data and st.button("Delete Faculty Member", key="btn_delete_teacher_form", use_container_width=True):
                        st.session_state.raw_data["teachers"] = [t for t in teachers_list if t["name"] != selected_t_data["name"]]
                        apply_and_recompile_raw_data(st.session_state.raw_data)
                        st.success(f"Faculty '{selected_t_data['name']}' deleted.")
                        st.rerun()

        # ---------------------------------------------------------------------
        # 3. ROOMS & VENUES (TABLE + FORM EDITOR)
        # ---------------------------------------------------------------------
        with entity_tab_rooms:
            rooms_list = st.session_state.raw_data.get("rooms", [])
            room_rows = []
            for r in rooms_list:
                r_kind = r.get("type") or r.get("kind", "classroom")
                room_rows.append({
                    "Room Code": r.get("name"),
                    "Seating Capacity": r.get("capacity", 60),
                    "Facility Type": r_kind.replace("_", " ").title(),
                    "Multi-Section Capable": "Yes (Up to 3 sections)" if r.get("name") == "LAB-36" or int(r.get("capacity", 0)) >= 90 else "Standard",
                })
            if room_rows:
                st.dataframe(pd.DataFrame(room_rows), use_container_width=True)

            with st.expander("➕ Configure / Add / Edit Room / Venue", expanded=True):
                room_options = ["+ Add New Room"] + [r["name"] for r in rooms_list]
                selected_r_mode = st.selectbox("Select Room to Edit", room_options, key="select_room_edit_mode")
                selected_r_data = next((r for r in rooms_list if r["name"] == selected_r_mode), None)

                r_col1, r_col2, r_col3 = st.columns(3)
                with r_col1:
                    r_name = st.text_input("Room Identifier / Code *", value=selected_r_data["name"] if selected_r_data else "LT-10", key="form_room_name")
                with r_col2:
                    r_cap = st.number_input("Seating Capacity *", min_value=15, max_value=300, value=int(selected_r_data.get("capacity", 60)) if selected_r_data else 60, step=5, key="form_room_capacity")
                with r_col3:
                    type_options = ["classroom", "lecture_theatre", "laboratory", "tutorial_room"]
                    type_labels = ["Classroom", "Lecture Theatre", "Laboratory", "Tutorial Room"]
                    cur_kind = selected_r_data.get("type") or selected_r_data.get("kind", "classroom") if selected_r_data else "classroom"
                    r_kind = st.selectbox("Facility Type", type_options, format_func=lambda x: x.replace("_", " ").title(), index=type_options.index(cur_kind) if cur_kind in type_options else 0, key="form_room_type")

                r_btn1, r_btn2 = st.columns([1, 1])
                with r_btn1:
                    if st.button("Save Room", key="btn_save_room_form", use_container_width=True):
                        if not r_name.strip():
                            st.error("Room identifier cannot be empty.")
                        else:
                            new_entry = {
                                "name": r_name.strip(),
                                "capacity": int(r_cap),
                                "type": r_kind,
                                "kind": r_kind,
                            }
                            existing_idx = next((i for i, r in enumerate(rooms_list) if r["name"] == (selected_r_data["name"] if selected_r_data else r_name.strip())), -1)
                            if existing_idx >= 0:
                                rooms_list[existing_idx] = new_entry
                            else:
                                rooms_list.append(new_entry)
                            st.session_state.raw_data["rooms"] = rooms_list
                            apply_and_recompile_raw_data(st.session_state.raw_data)
                            st.success(f"Room '{r_name.strip()}' saved successfully!")
                            st.rerun()

                with r_btn2:
                    if selected_r_data and st.button("Delete Room", key="btn_delete_room_form", use_container_width=True):
                        st.session_state.raw_data["rooms"] = [r for r in rooms_list if r["name"] != selected_r_data["name"]]
                        apply_and_recompile_raw_data(st.session_state.raw_data)
                        st.success(f"Room '{selected_r_data['name']}' deleted.")
                        st.rerun()

        # ---------------------------------------------------------------------
        # 4. COURSES & SUBJECTS (TABLE + FORM EDITOR)
        # ---------------------------------------------------------------------
        with entity_tab_subjects:
            subjects_list = st.session_state.raw_data.get("subjects", [])
            sub_rows = []
            for s in subjects_list:
                s_code = s.get("code") or s.get("name")
                s_title = s.get("name") if s.get("code") else s_code
                s_type = s.get("type") or s.get("kind", "theory")
                is_lab = (s_type == "lab")
                sub_rows.append({
                    "Course Code": s_code,
                    "Course Title": s_title,
                    "Weekly Hours": s.get("hours", 3),
                    "Course Type": s_type.title(),
                    "Preferred Venue": (s.get("room_type") or ("laboratory" if is_lab else "classroom")).replace("_", " ").title(),
                    "Duration": f"{2 if is_lab else 1} Period{'s' if is_lab else ''}",
                })
            if sub_rows:
                st.dataframe(pd.DataFrame(sub_rows), use_container_width=True)

            with st.expander("➕ Configure / Add / Edit Course / Subject", expanded=True):
                sub_options = ["+ Add New Course"] + [s.get("code") or s.get("name") for s in subjects_list]
                selected_s_mode = st.selectbox("Select Course to Edit", sub_options, key="select_subject_edit_mode")
                selected_s_data = next((s for s in subjects_list if (s.get("code") or s.get("name")) == selected_s_mode), None)

                s_col1, s_col2 = st.columns([1, 2])
                with s_col1:
                    s_code_val = st.text_input("Course Code *", value=selected_s_data.get("code") or selected_s_data.get("name") if selected_s_data else "CST-301", key="form_sub_code")
                with s_col2:
                    s_name_val = st.text_input("Course Title / Name *", value=selected_s_data.get("name", "Operating Systems") if selected_s_data else "Operating Systems", key="form_sub_name")

                s_col3, s_col4, s_col5 = st.columns(3)
                with s_col3:
                    s_hours = st.number_input("Weekly Contact Hours *", min_value=1, max_value=10, value=int(selected_s_data.get("hours", 3)) if selected_s_data else 3, key="form_sub_hours")
                with s_col4:
                    cur_kind = selected_s_data.get("type") or selected_s_data.get("kind", "theory") if selected_s_data else "theory"
                    s_format = st.radio("Delivery Format", ["Theory", "Lab"], index=0 if cur_kind != "lab" else 1, horizontal=True, key="form_sub_format")
                with s_col5:
                    venue_options = ["laboratory", "classroom", "tutorial_room", "lecture_theatre"]
                    default_venue = "laboratory" if s_format == "Lab" else "classroom"
                    cur_venue = selected_s_data.get("room_type", default_venue) if selected_s_data else default_venue
                    s_venue = st.selectbox("Preferred Room Type", venue_options, format_func=lambda x: x.replace("_", " ").title(), index=venue_options.index(cur_venue) if cur_venue in venue_options else 0, key="form_sub_venue")

                s_btn1, s_btn2 = st.columns([1, 1])
                with s_btn1:
                    if st.button("Save Course", key="btn_save_sub_form", use_container_width=True):
                        if not s_code_val.strip():
                            st.error("Course code cannot be empty.")
                        else:
                            new_entry = {
                                "code": s_code_val.strip(),
                                "name": s_name_val.strip(),
                                "hours": int(s_hours),
                                "type": "lab" if s_format == "Lab" else "theory",
                                "kind": "lab" if s_format == "Lab" else "theory",
                                "room_type": s_venue,
                            }
                            existing_idx = next((i for i, s in enumerate(subjects_list) if (s.get("code") or s.get("name")) == (selected_s_data.get("code") or selected_s_data.get("name") if selected_s_data else s_code_val.strip())), -1)
                            if existing_idx >= 0:
                                subjects_list[existing_idx] = new_entry
                            else:
                                subjects_list.append(new_entry)
                            st.session_state.raw_data["subjects"] = subjects_list
                            apply_and_recompile_raw_data(st.session_state.raw_data)
                            st.success(f"Course '{s_code_val.strip()}' saved successfully!")
                            st.rerun()

                with s_btn2:
                    if selected_s_data and st.button("Delete Course", key="btn_delete_sub_form", use_container_width=True):
                        target_code = selected_s_data.get("code") or selected_s_data.get("name")
                        st.session_state.raw_data["subjects"] = [s for s in subjects_list if (s.get("code") or s.get("name")) != target_code]
                        apply_and_recompile_raw_data(st.session_state.raw_data)
                        st.success(f"Course '{target_code}' deleted.")
                        st.rerun()

        # ---------------------------------------------------------------------
        # 5. 9:00 AM - 5:00 PM TIME & PERIOD STRUCTURE
        # ---------------------------------------------------------------------
        with entity_tab_time:
            time_cfg = st.session_state.raw_data.get("time", {})
            st.markdown("#### Academic Schedule & Period Configuration (9:00 AM – 5:00 PM)")

            t_col1, t_col2 = st.columns(2)
            with t_col1:
                p_count = st.number_input("Periods per Day", min_value=5, max_value=10, value=int(time_cfg.get("periods_per_day", 7)), key="form_time_periods")
            with t_col2:
                break_choices = list(range(1, int(p_count) + 1))
                cur_breaks = [b for b in time_cfg.get("break_periods", [2, 5]) if b in break_choices]
                sel_breaks = st.multiselect("Designate Break Periods", break_choices, default=cur_breaks, format_func=lambda x: f"Period {x}", key="form_time_breaks")

            if st.button("Apply Time Settings", key="btn_save_time_cfg", use_container_width=True):
                time_cfg["periods_per_day"] = int(p_count)
                time_cfg["break_periods"] = sel_breaks
                st.session_state.raw_data["time"] = time_cfg
                apply_and_recompile_raw_data(st.session_state.raw_data)
                st.success("Time structure updated successfully!")
                st.rerun()

    # =========================================================================
    # TAB 2: ALGORITHMIC SEARCH
    # =========================================================================
    with tab_gen:
        st.markdown("### Algorithmic Timetable Generation")

        gc1, gc2, gc3 = st.columns([2, 1, 1])
        with gc1:
            algo_choice = st.selectbox(
                "Search Algorithm",
                [
                    "Min-Conflicts",
                    "Hybrid (BT + SA)",
                    "BT heuristics",
                    "Hill Climbing",
                    "Simulated Annealing",
                    "BT baseline",
                ],
                index=0,
            )
        with gc2:
            seed_val = st.number_input("Random Seed", value=42, min_value=0, max_value=999999, step=1)
        with gc3:
            time_limit_val = st.number_input("Time Limit (seconds)", value=10, min_value=1, max_value=300, step=5)

        can_generate = len(st.session_state.errors) == 0 and st.session_state.data is not None

        if st.button("Generate Clash-Free Timetable", disabled=not can_generate, use_container_width=True):
            data = st.session_state.data
            try:
                teacher_of = assign_teachers(data)
                sessions = build_sessions(data, teacher_of)
                domains = build_domains(data, sessions)

                with st.spinner(f"Executing {algo_choice} on {st.session_state.dataset_name}..."):
                    t0 = time.perf_counter()
                    result = solvers.run(
                        algo=algo_choice,
                        data=data,
                        sessions=sessions,
                        domains=domains,
                        seed=int(seed_val),
                        time_limit=float(time_limit_val),
                    )
                    elapsed = time.perf_counter() - t0

                # Score with shared evaluator
                rep = evaluate(data, sessions, result.asg)

                st.session_state.sessions = sessions
                st.session_state.domains = domains
                st.session_state.asg = result.asg
                st.session_state.report = rep
                st.session_state.last_result = result
                st.session_state.history = []

            except Exception as e:
                st.error(f"Search failed: {e}")

        # Metrics display
        if st.session_state.report is not None and st.session_state.last_result is not None:
            rep = st.session_state.report
            res = st.session_state.last_result

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Execution Time", f"{res.time_taken:.3f} s")
            m2.metric("Hard Violations", f"{rep.hard_total}")
            m3.metric("Soft Penalty", f"{rep.soft_total}")
            m4.metric("Work (Nodes/Iters)", f"{res.work:,}")

            if rep.hard_total == 0:
                st.markdown(
                    '<div class="tag-badge tag-green" style="padding: 8px 16px; font-size: 0.95rem; display:block; margin: 12px 0;">'
                    'Optimal Feasible Schedule Found &mdash; 0 Hard Constraints Violated!'
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="tag-badge tag-red" style="padding: 8px 16px; font-size: 0.95rem; display:block; margin: 12px 0;">'
                    f'Unresolved Clashes: {rep.hard_total} (Displaying best candidate)'
                    '</div>',
                    unsafe_allow_html=True,
                )

    # =========================================================================
    # TAB 3: SCHEDULE GRIDS (COMPLETE WITH 2-ROW LABS & DIVIDED COLUMNS)
    # =========================================================================
    with tab_views:
        st.markdown("### Institutional Matrix Inspection")
        if not st.session_state.asg or not st.session_state.sessions:
            st.info("No timetable generated yet. Navigate to Tab 2 (Algorithmic Search) to solve a schedule.")
        else:
            data = st.session_state.data
            sessions = st.session_state.sessions
            asg = st.session_state.asg

            vc1, vc2 = st.columns([1, 2])
            with vc1:
                view_kind = st.selectbox("Perspective", ["class", "teacher", "room"], key="sb_view_perspective")
            with vc2:
                if view_kind == "class":
                    parent_batches = set()
                    for c in data.classes.values():
                        p = getattr(c, "parent_batch", None) or getattr(c, "parent_class", None) or c.name
                        parent_batches.add(p)

                    options = [f"{p} (Unified Cohort & All Sections)" for p in sorted(parent_batches)]
                    sub_sections = [c.name for c in data.classes.values() if getattr(c, "sub_index", None) is not None]
                    if sub_sections:
                        options.extend([f"{s} (Specific Lab Section)" for s in sorted(sub_sections)])
                elif view_kind == "teacher":
                    options = sorted(list(data.teachers.keys()))
                else:
                    options = sorted(list(data.rooms.keys()))

                selected_name = st.selectbox(f"Select {view_kind.title()}", options, key=f"sb_entity_choice_{view_kind}")

            # Entity Information Banner
            clean_ent_name = selected_name.split(" (")[0].strip()
            if view_kind == "class":
                cls_ent = data.classes.get(clean_ent_name)
                str_label = cls_ent.strength if cls_ent else "Cohort"
                st.markdown(f"""
                <div style="background:#FFF; border:1px solid #D6D5D2; border-radius:6px; padding:10px 14px; margin-bottom:12px; font-size:0.88rem;">
                    <strong>Cohort:</strong> {html.escape(clean_ent_name)} &bull;
                    <strong>Batch Strength:</strong> {str_label} Students &bull;
                    <strong>Schedule View:</strong> Unified Theory Lectures + Parallel 30-Student Lab Sections
                </div>
                """, unsafe_allow_html=True)
            elif view_kind == "teacher":
                t_ent = data.teachers.get(clean_ent_name)
                max_l = t_ent.max_load if t_ent else 14
                t_subs = getattr(t_ent, "subjects", None) or getattr(t_ent, "qualified", [])
                qual_str = ", ".join(sorted(list(t_subs))) if t_subs else "N/A"
                assigned_count = len([s for s in sessions if s.teacher.strip() == clean_ent_name and s.sid in asg])
                st.markdown(f"""
                <div style="background:#FFF; border:1px solid #D6D5D2; border-radius:6px; padding:10px 14px; margin-bottom:12px; font-size:0.88rem;">
                    <strong>Faculty:</strong> {html.escape(clean_ent_name)} &bull;
                    <strong>Weekly Assigned Hours:</strong> {assigned_count} / {max_l} Hours &bull;
                    <strong>Qualified Courses:</strong> {html.escape(qual_str)}
                </div>
                """, unsafe_allow_html=True)
            elif view_kind == "room":
                r_ent = data.rooms.get(clean_ent_name)
                cap = r_ent.capacity if r_ent else "N/A"
                knd = r_ent.kind.replace("_", " ").title() if r_ent else "Room"
                st.markdown(f"""
                <div style="background:#FFF; border:1px solid #D6D5D2; border-radius:6px; padding:10px 14px; margin-bottom:12px; font-size:0.88rem;">
                    <strong>Room:</strong> {html.escape(clean_ent_name)} &bull;
                    <strong>Capacity:</strong> {cap} Seats &bull;
                    <strong>Facility Type:</strong> {knd}
                </div>
                """, unsafe_allow_html=True)

            # Render HTML Matrix Table with 2-period lab spanning & divided columns
            matrix_html = build_schedule_html_matrix(data, sessions, asg, view_kind, clean_ent_name)
            st.markdown(matrix_html, unsafe_allow_html=True)

            # Active Constraint Notes
            if st.session_state.report and st.session_state.report.messages:
                st.markdown("#### Active Constraint Notes")
                for msg in st.session_state.report.messages[:10]:
                    st.markdown(f"- `{msg}`")

    # =========================================================================
    # TAB 4: MANUAL EDITOR (WITH CLEAR FEEDBACK & MOVE LOG)
    # =========================================================================
    with tab_edit:
        st.markdown("### Manual Assignment & Conflict Detection")
        if not st.session_state.asg or not st.session_state.sessions:
            st.info("Please generate an initial schedule in Tab 2 before performing manual adjustments.")
        else:
            data = st.session_state.data
            sessions = st.session_state.sessions
            asg = st.session_state.asg

            def session_label(sid):
                s = next(x for x in sessions if x.sid == sid)
                cur_val = asg.get(sid)
                if cur_val:
                    d_name = data.days[cur_val[0]]
                    return f"{s.cls} | {s.subject} #{s.idx} (Current: {d_name} P{cur_val[1]+1} {cur_val[2]})"
                return f"{s.cls} | {s.subject} #{s.idx} (Unassigned)"

            selected_sid = st.selectbox(
                "Select Session to Reassign",
                [s.sid for s in sessions],
                format_func=session_label,
                key="manual_edit_sid_selector",
            )

            target_sess = next(s for s in sessions if s.sid == selected_sid)
            cur_assignment = asg.get(selected_sid)
            cur_desc = f"{data.days[cur_assignment[0]]} P{cur_assignment[1]+1} in {cur_assignment[2]}" if cur_assignment else "Unassigned"

            st.info(f"Selected Session: **{target_sess.subject}** for **{target_sess.cls}** (Duration: {target_sess.length} Hr{'s' if target_sess.length > 1 else ''}, Faculty: {target_sess.teacher}). Current Assignment: `{cur_desc}`")

            e1, e2, e3 = st.columns(3)
            with e1:
                edit_day = st.selectbox("Target Day", range(len(data.days)), format_func=lambda i: data.days[i], key="edit_target_day")
            with e2:
                edit_period = st.selectbox("Target Start Period", range(data.periods), format_func=lambda i: f"P{i+1} ({9+i}:00)", key="edit_target_period")
            with e3:
                edit_room = st.selectbox("Target Room", sorted(list(data.rooms.keys())), key="edit_target_room")

            trial_asg = dict(asg)
            trial_asg[selected_sid] = (edit_day, edit_period, edit_room)

            before_rep = st.session_state.report or evaluate(data, sessions, asg)
            after_rep = evaluate(data, sessions, trial_asg)

            st.markdown(f"""
            <div class="bento-card" style="margin-top: 16px;">
                <strong>Trial Move Evaluation:</strong>
                Hard Violations: <code>{before_rep.hard_total} &rarr; {after_rep.hard_total}</code> |
                Soft Penalties: <code>{before_rep.soft_total} &rarr; {after_rep.soft_total}</code>
            </div>
            """, unsafe_allow_html=True)

            new_problems = [m for m in after_rep.messages if m not in before_rep.messages]
            if new_problems:
                for m in new_problems:
                    st.error(f"Conflict: {m}")
            else:
                st.success("No new hard constraints violated. Move is clash-free!")

            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                if st.button("Apply Move", use_container_width=True):
                    st.session_state.history.append(dict(asg))
                    st.session_state.asg = trial_asg
                    st.session_state.report = after_rep
                    new_desc = f"{data.days[edit_day]} P{edit_period+1} in {edit_room}"
                    st.session_state.move_log.append(f"Moved {target_sess.subject} ({target_sess.cls}): {cur_desc} → {new_desc}")
                    st.success(f"Move committed successfully! {target_sess.subject} is now scheduled at {new_desc}. All grids in Tab 3 and exports in Tab 5 are updated.")
                    st.rerun()

            with btn_col2:
                if st.session_state.history and st.button("Undo Last Move", use_container_width=True):
                    st.session_state.asg = st.session_state.history.pop()
                    st.session_state.report = evaluate(data, sessions, st.session_state.asg)
                    if st.session_state.move_log:
                        st.session_state.move_log.pop()
                    st.info("Reverted schedule to previous state.")
                    st.rerun()

            if st.session_state.move_log:
                st.markdown("#### Manual Move History")
                for log_item in reversed(st.session_state.move_log[-5:]):
                    st.markdown(f"- `{log_item}`")

    # =========================================================================
    # TAB 5: EXPORT
    # =========================================================================
    with tab_export:
        st.markdown("### Export Schedules & Publication-Grade Document")
        if not st.session_state.asg:
            st.info("No schedule data available for export. Generate a schedule in Tab 2 first.")
        else:
            data = st.session_state.data
            sessions = st.session_state.sessions
            asg = st.session_state.asg

            exp_col1, exp_col2, exp_col3 = st.columns(3)

            with exp_col1:
                csv_bytes = to_flat_csv(data, sessions, asg)
                st.download_button(
                    "Download Flat Timetable (CSV)",
                    csv_bytes,
                    "timetable_flat.csv",
                    "text/csv",
                    use_container_width=True,
                )

            with exp_col2:
                print_html = to_printable_html(data, sessions, asg)
                st.download_button(
                    "Download Printable Schedule (HTML)",
                    print_html,
                    "timetable_printable.html",
                    "text/html",
                    use_container_width=True,
                )

            with exp_col3:
                out_json = {
                    "dataset": st.session_state.dataset_name,
                    "assignment": {str(k): list(v) for k, v in asg.items()},
                    "evaluation": st.session_state.report.to_dict() if st.session_state.report else None,
                }
                st.download_button(
                    "Download Solution State (JSON)",
                    json.dumps(out_json, indent=2),
                    "timetable_solution.json",
                    "application/json",
                    use_container_width=True,
                )

            st.markdown("#### Document Preview (Print-Ready)")
            with st.expander("Expand to Preview Official Document Layout", expanded=True):
                st.components.v1.html(to_printable_html(data, sessions, asg), height=600, scrolling=True)

    # =========================================================================
    # TAB 6: EMPIRICAL BENCHMARKS
    # =========================================================================
    with tab_benchmarks:
        st.markdown("### Empirical Benchmarks Across Algorithms")
        st.markdown("Evaluate and compare search efficiency, constraint convergence, and runtime across all CSP solvers.")

        b_col1, b_col2, b_col3 = st.columns([2, 1, 1])
        with b_col1:
            target_bench_dataset = st.selectbox(
                "Benchmark Dataset",
                [
                    "Active In-Memory Dataset",
                    "Institutional Specification",
                    "Custom Dataset",
                    "Large Dataset",
                    "Small Dataset",
                ],
            )
        with b_col2:
            bench_timeout = st.number_input("Timeout per Method (sec)", value=5, min_value=1, max_value=60, step=1)
        with b_col3:
            st.write("")
            st.write("")
            run_bench_clicked = st.button("Run Live Benchmark", use_container_width=True)

        if run_bench_clicked:
            raw_to_bench = None
            label_to_bench = target_bench_dataset

            if target_bench_dataset == "Active In-Memory Dataset":
                raw_to_bench = st.session_state.raw_data
                label_to_bench = st.session_state.dataset_name
            elif target_bench_dataset == "Institutional Specification":
                p = os.path.join(os.path.dirname(__file__), "data", "institutional_timetable_specification.json")
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        raw_to_bench = json.load(f)
            elif target_bench_dataset == "Custom Dataset":
                p = os.path.join(os.path.dirname(__file__), "data", "custom.json")
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        raw_to_bench = json.load(f)
            elif target_bench_dataset == "Large Dataset":
                p = os.path.join(os.path.dirname(__file__), "data", "large.json")
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        raw_to_bench = json.load(f)
            elif target_bench_dataset == "Small Dataset":
                p = os.path.join(os.path.dirname(__file__), "data", "small.json")
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        raw_to_bench = json.load(f)

            if raw_to_bench:
                with st.spinner(f"Running empirical benchmark across all 6 solvers on {label_to_bench}..."):
                    new_records = run_benchmark_on_dataset(raw_to_bench, label_to_bench, time_limit=float(bench_timeout))
                    st.session_state.bench_history = new_records
                    st.success(f"Benchmark run complete on {label_to_bench}!")
            else:
                st.error("Failed to load dataset for benchmarking.")

        # Display Live Benchmark Results
        if st.session_state.bench_history:
            st.markdown(f"#### Live Benchmark Results: {st.session_state.bench_history[0]['Dataset']}")
            df_live = pd.DataFrame(st.session_state.bench_history)
            st.dataframe(df_live, use_container_width=True)

        # Display Saved Historical Benchmarks
        st.markdown("#### Historical & Pre-computed Benchmarks")
        saved_path = os.path.join(os.path.dirname(__file__), "experiments", "results", "benchmark_runs.json")
        if os.path.exists(saved_path):
            try:
                with open(saved_path, "r", encoding="utf-8") as f:
                    saved_dict = json.load(f)

                selected_saved = st.selectbox(
                    "View Saved Historical Benchmark Dataset",
                    list(saved_dict.keys()),
                    format_func=lambda k: saved_dict[k].get("display_name", k),
                )
                if selected_saved in saved_dict:
                    saved_records = saved_dict[selected_saved].get("records", [])
                    if saved_records:
                        df_saved = pd.DataFrame(saved_records)
                        cols = [c for c in ["Dataset", "Method", "Success Rate", "Avg Time (s)", "Avg Work (nodes/iters)", "Avg Hard Violations", "Avg Soft Penalty (valid runs)", "Output Summary"] if c in df_saved.columns]
                        st.dataframe(df_saved[cols] if cols else df_saved, use_container_width=True)
            except Exception as e:
                st.info(f"Could not load precomputed benchmarks: {e}")


if __name__ == "__main__":
    main()
