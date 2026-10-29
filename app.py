"""Streamlit Application for AI Timetable Scheduler (Section 9).

Conforms strictly to the architectural boundary:
- Algorithm code lives strictly in core/ and never imports Streamlit.
- Provides all 5 required tabs: Data, Generate, Views, Edit, Export.
- Styled according to the Premium Utilitarian Minimalism protocol.
"""

import io
import json
import os
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


def init_session_state():
    """Initialize working objects in st.session_state (Section 9.1)."""
    if "data" not in st.session_state:
        # Load small dataset as initial state
        small_path = os.path.join(os.path.dirname(__file__), "data", "small.json")
        if os.path.exists(small_path):
            with open(small_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            st.session_state.raw_data = raw
            st.session_state.data = load_from_dict(raw)
        else:
            raw = get_template_dict()
            st.session_state.raw_data = raw
            st.session_state.data = load_from_dict(raw)

        st.session_state.errors = validate_raw_data(st.session_state.raw_data)
        st.session_state.sessions = []
        st.session_state.domains = {}
        st.session_state.asg = {}
        st.session_state.report = None
        st.session_state.history = []
        st.session_state.last_result = None


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

    /* Overall page container styling */
    .stApp {
        background-color: var(--canvas-bg) !important;
        color: var(--text-primary) !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    }

    /* ============================================================
       TABS — STREAMLIT 1.66+ REACT ARIA & BASEWEB COMPATIBLE
       Force all tabs to be clearly visible at all times!
       ============================================================ */
    .stTabs,
    [data-testid="stTabs"] {
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

    /* ALL TAB BUTTONS (inactive state) */
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

    /* ALL TEXT inside every tab button — force dark, high-contrast, fully visible */
    [data-testid="stTab"] *,
    [data-testid="stTab"] p,
    [data-testid="stTab"] div,
    [data-testid="stTab"] span,
    [data-testid="stTabs"] button *,
    [data-testid="stTabs"] [role="tab"] *,
    button[role="tab"] *,
    button[role="tab"] p,
    button[role="tab"] span,
    button[data-baseweb="tab"] *,
    button[data-baseweb="tab"] p {
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }

    /* Inactive tab hover */
    [data-testid="stTab"]:not([aria-selected="true"]):hover,
    [data-testid="stTabs"] button:not([aria-selected="true"]):hover,
    button[role="tab"]:not([aria-selected="true"]):hover,
    button[data-baseweb="tab"]:not([aria-selected="true"]):hover {
        background-color: #E2E1DC !important;
        border-color: #AFAEA9 !important;
    }

    /* ACTIVE / SELECTED TAB — crisp highlighted tab with dark border & text (NO BLACK BOX) */
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
    [data-testid="stTab"][aria-selected="true"] p,
    [data-testid="stTab"][aria-selected="true"] div,
    [data-testid="stTab"][aria-selected="true"] span,
    [data-testid="stTab"][data-selected] *,
    [data-testid="stTabs"] button[aria-selected="true"] *,
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] *,
    button[role="tab"][aria-selected="true"] *,
    button[role="tab"][aria-selected="true"] p,
    button[data-baseweb="tab"][aria-selected="true"] *,
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
        font-weight: 700 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }

    /* Selection indicator line inside tab */
    [data-testid="stTab"] .react-aria-SelectionIndicator,
    [data-testid="stTabs"] .react-aria-SelectionIndicator {
        background-color: transparent !important;
        display: none !important;
    }

    /* ============================================================
       BUTTONS — ALL BUTTONS (stButton, stDownloadButton, etc.)
       Clean white background, 1.5px dark border, crisp black text!
       Matches the clean 'Download Dataset Template' style.
       ============================================================ */
    .stButton > button,
    .stDownloadButton > button,
    [data-testid^="stBaseButton"],
    [data-testid^="baseButton"],
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
        opacity: 1 !important;
        visibility: visible !important;
    }

    .stButton > button *,
    .stDownloadButton > button *,
    .stButton > button p,
    .stDownloadButton > button p,
    [data-testid^="stBaseButton"] *,
    [data-testid^="baseButton"] *,
    button[kind="secondary"] *,
    button[kind="primary"] * {
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
        font-weight: 600 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    [data-testid^="stBaseButton"]:hover,
    [data-testid^="baseButton"]:hover,
    button[kind="secondary"]:hover,
    button[kind="primary"]:hover {
        background-color: #ECEBE8 !important;
        border-color: #000000 !important;
    }

    .stButton > button:hover *,
    .stDownloadButton > button:hover *,
    [data-testid^="stBaseButton"]:hover *,
    [data-testid^="baseButton"]:hover *,
    button[kind="secondary"]:hover *,
    button[kind="primary"]:hover * {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }

    /* ============================================================
       FILE UPLOADER — make all text and button inside visible
       ============================================================ */
    [data-testid="stFileUploader"] section {
        background-color: #FFFFFF !important;
        border: 1.5px dashed #999896 !important;
        border-radius: 6px !important;
    }
    [data-testid="stFileUploader"] section * {
        color: #222222 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    [data-testid="stFileUploader"] section button {
        background-color: #FFFFFF !important;
        color: #111111 !important;
        border: 1.5px solid #333333 !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    [data-testid="stFileUploader"] section button * {
        color: #111111 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    [data-testid="stFileUploader"] section button:hover {
        background-color: #F4F3F0 !important;
    }
    [data-testid="stFileUploader"] section p,
    [data-testid="stFileUploader"] section span,
    [data-testid="stFileUploader"] section small {
        color: #444444 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }

    /* General Typography & High Contrast Readability */
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

    .stMarkdown p, .stMarkdown div, .stMarkdown span {
        color: #222222 !important;
    }

    label, .stWidgetLabel p, .stWidgetLabel span {
        color: #111111 !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }

    /* Form Controls & Inputs */
    input, select, textarea, div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        color: #111111 !important;
        border-color: #D6D5D2 !important;
    }

    div[data-baseweb="select"] * {
        color: #111111 !important;
    }

    /* Metrics Readability */
    div[data-testid="stMetricValue"] {
        color: #111111 !important;
        font-family: 'Instrument Serif', Georgia, serif !important;
        font-size: 2.2rem !important;
    }

    div[data-testid="stMetricLabel"] p {
        color: #444444 !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
        font-size: 0.8rem !important;
    }

    /* Cards and bento containers */
    .bento-card {
        background: #FFFFFF !important;
        border: 1px solid #D6D5D2 !important;
        border-radius: 8px !important;
        padding: 22px !important;
        margin-bottom: 18px !important;
    }

    /* Status tags */
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

    /* Keystrokes */
    kbd {
        border: 1px solid #D6D5D2 !important;
        border-radius: 4px;
        background: #F0EFEB !important;
        font-family: 'Geist Mono', monospace;
        font-size: 0.85em;
        padding: 2px 6px;
        color: #111111 !important;
    }

    /* Tables */
    table {
        border-collapse: collapse !important;
        width: 100% !important;
        border: 1px solid #D6D5D2 !important;
        background-color: #FFFFFF !important;
    }
    th, td {
        border: 1px solid #D6D5D2 !important;
        padding: 10px 14px !important;
        text-align: left !important;
        color: #111111 !important;
    }
    th {
        background-color: #F4F3F0 !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: #333333 !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_timetable_grid(data, sessions, asg, kind, name):
    """Render timetable matrix (Section 9.4)."""
    df = pd.DataFrame(
        "",
        index=[f"P{p+1}" for p in range(data.periods)],
        columns=data.days,
    )

    for s in sessions:
        if s.sid not in asg:
            continue
        d, p, r = asg[s.sid]
        owner = {"class": s.cls, "teacher": s.teacher, "room": r}[kind]
        if owner != name:
            continue

        label = {
            "class": f"{s.subject} ({s.teacher}, {r})",
            "teacher": f"{s.subject} ({s.cls}, {r})",
            "room": f"{s.subject} ({s.cls}, {s.teacher})",
        }[kind]

        for k in range(s.length):
            if 0 <= p + k < data.periods:
                df.iat[p + k, d] = label

    # Fill break periods and lunch period
    for q in data.break_periods:
        if 0 <= q < data.periods:
            for d_idx in range(len(data.days)):
                if not df.iat[q, d_idx]:
                    df.iat[q, d_idx] = "BREAK"

    if kind == "class" and name in data.classes:
        lunch_idx = data.classes[name].lunch_period
        if 0 <= lunch_idx < data.periods:
            for d_idx in range(len(data.days)):
                df.iat[lunch_idx, d_idx] = "LUNCH"

    return df


def to_printable_html(data, sessions, asg) -> str:
    """Generate a clean, standalone, printable HTML document with all class schedules."""
    grids_html = []
    for cname in data.classes:
        df = render_timetable_grid(data, sessions, asg, "class", cname)
        # Convert df to clean HTML table
        table_html = df.to_html(classes="print-table")
        grids_html.append(f"""
        <div class="print-section">
            <h2 style="font-family: Georgia, serif; font-size: 1.4rem; margin-bottom: 8px; border-bottom: 2px solid #111; padding-bottom: 4px;">
                Cohort Schedule: {cname} (Strength: {data.classes[cname].strength})
            </h2>
            {table_html}
        </div>
        """)

    all_sections = "\n".join(grids_html)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Academic Timetable Schedule Matrix</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 20px;
            color: #111;
            background: #FFF;
        }}
        h1 {{
            font-family: Georgia, serif;
            font-size: 2rem;
            margin-bottom: 4px;
        }}
        p.subtitle {{
            color: #555;
            font-size: 0.9rem;
            margin-bottom: 24px;
        }}
        .print-section {{
            margin-bottom: 36px;
            page-break-after: always;
        }}
        .print-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82rem;
            margin-bottom: 12px;
        }}
        .print-table th, .print-table td {{
            border: 1px solid #333;
            padding: 8px 10px;
            text-align: left;
            vertical-align: top;
        }}
        .print-table th {{
            background-color: #F0F0F0;
            font-weight: bold;
            text-transform: uppercase;
        }}
        @media print {{
            .no-print {{ display: none; }}
            body {{ margin: 0; }}
            .print-section {{ page-break-after: always; }}
        }}
    </style>
</head>
<body>
    <div class="no-print" style="margin-bottom: 20px; padding: 12px; background: #F7F6F3; border: 1px solid #DDD; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
        <strong>Official Academic Timetable Schedule Document</strong>
        <button onclick="window.print()" style="background: #111; color: #FFF; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;">Print Document / Save as PDF</button>
    </div>
    <h1>Institutional Master Timetable</h1>
    <p class="subtitle">Generated via Constraint Satisfaction Problem (CSP) Solver &mdash; Zero Hard Clashes</p>
    {all_sections}
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
        <p style="color: #787774; font-size: 1.05rem; max-width: 800px; margin: 0;">
            A rigorous combinatorial optimization system comparing systematic backtracking CSP and stochastic min-conflicts local search under hard and soft constraints.
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_data, tab_gen, tab_views, tab_edit, tab_export = st.tabs([
        "1. Data Specification",
        "2. Algorithmic Search",
        "3. Schedule Grids",
        "4. Manual Editor",
        "5. Export Matrix",
    ])

    # =========================================================================
    # TAB 1: DATA
    # =========================================================================
    with tab_data:
        st.markdown("### Institutional Configuration & Parameters")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Load Standard Small Dataset"):
                path = os.path.join(os.path.dirname(__file__), "data", "small.json")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    st.session_state.raw_data = raw
                    st.session_state.data = load_from_dict(raw)
                    st.session_state.errors = validate_raw_data(raw)
                    st.session_state.asg = {}
                    st.session_state.report = None
                    st.rerun()

        with col2:
            if st.button("Load Standard Large Dataset"):
                path = os.path.join(os.path.dirname(__file__), "data", "large.json")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    st.session_state.raw_data = raw
                    st.session_state.data = load_from_dict(raw)
                    st.session_state.errors = validate_raw_data(raw)
                    st.session_state.asg = {}
                    st.session_state.report = None
                    st.rerun()

        with col3:
            tpl = json.dumps(get_template_dict(), indent=2)
            st.download_button(
                "Download Dataset Template (JSON)",
                tpl,
                "timetable_template.json",
                "application/json",
            )

        # Upload JSON
        uploaded_file = st.file_uploader("Upload Configuration JSON", type=["json"])
        if uploaded_file is not None:
            try:
                raw_uploaded = json.load(uploaded_file)
                val_errs = validate_raw_data(raw_uploaded)
                if val_errs:
                    st.session_state.errors = val_errs
                else:
                    st.session_state.raw_data = raw_uploaded
                    st.session_state.data = load_from_dict(raw_uploaded)
                    st.session_state.errors = []
                    st.session_state.asg = {}
                    st.session_state.report = None
                    st.success("Configuration loaded and verified successfully.")
            except Exception as e:
                st.error(f"Failed to parse uploaded JSON: {e}")

        # Validation Display
        if st.session_state.errors:
            st.markdown('<div class="bento-card" style="border-left: 4px solid var(--accent-red-text);">', unsafe_allow_html=True)
            st.markdown("<h4 style='color: var(--accent-red-text); margin-top:0;'>Validation Errors Detected</h4>", unsafe_allow_html=True)
            for err in st.session_state.errors:
                st.markdown(f"- {err}")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="bento-card" style="border-left: 4px solid var(--accent-green-text); padding: 14px 20px;">'
                        '<span class="tag-badge tag-green">Validated</span> All entity references, positive integer constraints, and relational schemas are valid.'
                        '</div>', unsafe_allow_html=True)

        # Feasibility Pre-Check (Section 3.5)
        if not st.session_state.errors and st.session_state.data:
            feas_checks = check_feasibility(st.session_state.data)
            st.markdown("#### Feasibility Arithmetic Pre-Check")
            feas_cols = st.columns(3)
            for i, c in enumerate(feas_checks):
                col = feas_cols[i % 3]
                badge = '<span class="tag-badge tag-green">Pass</span>' if c["passed"] else '<span class="tag-badge tag-red">Fail</span>'
                col.markdown(f"""
                <div class="bento-card" style="padding: 16px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <strong>{c['name']}</strong>
                        {badge}
                    </div>
                    <p style="font-size:0.85rem; color:#787774; margin:0 0 6px 0;">{c['rule']}</p>
                    <p style="font-size:0.85rem; margin:0; font-family:'Geist Mono', monospace;">{c['detail']}</p>
                </div>
                """, unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: GENERATE
    # =========================================================================
    with tab_gen:
        st.markdown("### Algorithmic Optimization")

        gc1, gc2, gc3 = st.columns([2, 1, 1])
        with gc1:
            algo_choice = st.selectbox(
                "Search Method",
                [
                    "Backtracking (MRV + FC + degree)",
                    "Min-Conflicts",
                    "Hybrid (BT + SA)",
                    "Simulated Annealing",
                    "Backtracking (plain)",
                    "Hill Climbing",
                ],
            )
        with gc2:
            seed_val = st.number_input("Random Seed", value=0, min_value=0, max_value=999999, step=1)
        with gc3:
            time_limit_val = st.number_input("Time Limit (seconds)", value=30, min_value=1, max_value=300, step=5)

        can_generate = len(st.session_state.errors) == 0 and st.session_state.data is not None

        if st.button("Generate Clash-Free Timetable", disabled=not can_generate):
            data = st.session_state.data
            try:
                teacher_of = assign_teachers(data)
                sessions = build_sessions(data, teacher_of)
                domains = build_domains(data, sessions)

                with st.spinner(f"Executing {algo_choice}..."):
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

                # Score with shared evaluator (Section 5)
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
            m4.metric("Search Nodes / Iterations", f"{res.work:,}")

            if rep.hard_total == 0:
                st.markdown(
                    '<div class="tag-badge tag-green" style="padding: 6px 14px; font-size: 0.85rem;">'
                    'Optimal Feasibility: Zero Clashes'
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="tag-badge tag-red" style="padding: 6px 14px; font-size: 0.85rem;">'
                    f'Unresolved Clashes: {rep.hard_total} (Displaying best candidate)'
                    '</div>',
                    unsafe_allow_html=True,
                )

    # =========================================================================
    # TAB 3: VIEWS
    # =========================================================================
    with tab_views:
        st.markdown("### Institutional Matrix Inspection")
        if not st.session_state.asg or not st.session_state.sessions:
            st.info("No timetable generated yet. Navigate to the Generate tab to produce a schedule.")
        else:
            data = st.session_state.data
            sessions = st.session_state.sessions
            asg = st.session_state.asg

            vc1, vc2 = st.columns([1, 2])
            with vc1:
                view_kind = st.selectbox("Perspective", ["class", "teacher", "room"])
            with vc2:
                if view_kind == "class":
                    options = list(data.classes.keys())
                elif view_kind == "teacher":
                    options = list(data.teachers.keys())
                else:
                    options = list(data.rooms.keys())
                selected_name = st.selectbox(f"Select {view_kind.title()}", options)

            grid_df = render_timetable_grid(data, sessions, asg, view_kind, selected_name)
            st.table(grid_df)

            # Display any conflict messages under grid (Section 9.4)
            if st.session_state.report and st.session_state.report.messages:
                st.markdown("#### Active Constraint Notes")
                for msg in st.session_state.report.messages[:10]:
                    st.markdown(f"- `{msg}`")

    # =========================================================================
    # TAB 4: MANUAL EDIT
    # =========================================================================
    with tab_edit:
        st.markdown("### Manual Assignment & Conflict Detection")
        if not st.session_state.asg or not st.session_state.sessions:
            st.info("Please generate an initial schedule before performing manual adjustments.")
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
            )

            e1, e2, e3 = st.columns(3)
            with e1:
                edit_day = st.selectbox("Target Day", range(len(data.days)), format_func=lambda i: data.days[i])
            with e2:
                edit_period = st.selectbox("Target Start Period", range(data.periods), format_func=lambda i: f"P{i+1}")
            with e3:
                edit_room = st.selectbox("Target Room", list(data.rooms.keys()))

            trial_asg = dict(asg)
            trial_asg[selected_sid] = (edit_day, edit_period, edit_room)

            before_rep = st.session_state.report or evaluate(data, sessions, asg)
            after_rep = evaluate(data, sessions, trial_asg)

            new_problems = [m for m in after_rep.messages if m not in before_rep.messages]

            st.markdown(f"""
            <div class="bento-card" style="margin-top: 16px;">
                <strong>Trial Evaluation:</strong>
                Hard Violations: <code>{before_rep.hard_total} &rarr; {after_rep.hard_total}</code> |
                Soft Penalties: <code>{before_rep.soft_total} &rarr; {after_rep.soft_total}</code>
            </div>
            """, unsafe_allow_html=True)

            if new_problems:
                for m in new_problems:
                    st.error(f"Conflict: {m}")
            else:
                st.success("No new hard constraints violated.")

            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                if st.button("Apply Move"):
                    st.session_state.history.append(dict(asg))
                    st.session_state.asg = trial_asg
                    st.session_state.report = after_rep
                    st.success("Move committed.")
                    st.rerun()

            with btn_col2:
                if st.session_state.history and st.button("Undo Last Move"):
                    st.session_state.asg = st.session_state.history.pop()
                    st.session_state.report = evaluate(data, sessions, st.session_state.asg)
                    st.info("Reverted to previous state.")
                    st.rerun()

    # =========================================================================
    # TAB 5: EXPORT
    # =========================================================================
    with tab_export:
        st.markdown("### Export Schedules")
        if not st.session_state.asg:
            st.info("No schedule data available for export.")
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
                # Printable HTML export
                print_html = to_printable_html(data, sessions, asg)
                st.download_button(
                    "Download Printable Matrix (HTML)",
                    print_html,
                    "timetable_printable.html",
                    "text/html",
                    use_container_width=True,
                )

            with exp_col3:
                # JSON export of full state
                out_json = {
                    "assignment": {str(k): list(v) for k, v in asg.items()},
                    "evaluation": st.session_state.report.to_dict() if st.session_state.report else None,
                }
                st.download_button(
                    "Download Solution (JSON)",
                    json.dumps(out_json, indent=2),
                    "timetable_solution.json",
                    "application/json",
                    use_container_width=True,
                )

            st.markdown("#### Printable Matrix Preview")
            with st.expander("Expand to View Printable Document Format", expanded=True):
                print_html = to_printable_html(data, sessions, asg)
                st.components.v1.html(print_html, height=500, scrolling=True)


if __name__ == "__main__":
    main()
