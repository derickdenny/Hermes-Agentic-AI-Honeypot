import json
import os
import sys
from datetime import datetime

import streamlit as st

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from core.pipeline import PERSONAS, build_report, create_session, format_duration
from main import process_message


st.set_page_config(
    page_title="Hermes Honeypot",
    page_icon="H",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(249,115,22,0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(14,165,233,0.14), transparent 24%),
                linear-gradient(180deg, #07111a 0%, #0d1722 100%);
            color: #e5edf5;
        }
        .hero {
            padding: 1.2rem 1.4rem;
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 20px;
            background: linear-gradient(135deg, rgba(15,23,42,0.9), rgba(17,24,39,0.72));
            margin-bottom: 1rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 2.2rem;
            color: #f8fafc;
        }
        .hero p {
            margin: 0.35rem 0 0 0;
            color: #cbd5e1;
        }
        .metric-card {
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 16px;
            padding: 1rem;
            background: rgba(15, 23, 42, 0.7);
            min-height: 110px;
        }
        .metric-label {
            font-size: 0.78rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .metric-value {
            font-size: 1.85rem;
            font-weight: 700;
            margin-top: 0.4rem;
            color: #f8fafc;
        }
        .panel {
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 18px;
            padding: 1rem;
            background: rgba(15, 23, 42, 0.68);
            height: 100%;
        }
        .timeline-item {
            border-left: 3px solid #f97316;
            padding: 0.7rem 0.9rem;
            margin-bottom: 0.75rem;
            background: rgba(30, 41, 59, 0.62);
            border-radius: 10px;
        }
        .timeline-meta {
            font-size: 0.75rem;
            color: #94a3b8;
            margin-bottom: 0.35rem;
        }
        .turn-scammer {
            border-left-color: #ef4444;
        }
        .turn-ai {
            border-left-color: #22c55e;
        }
        .chip {
            display: inline-block;
            padding: 0.2rem 0.55rem;
            margin: 0.1rem 0.3rem 0.1rem 0;
            border-radius: 999px;
            background: rgba(249, 115, 22, 0.14);
            color: #fdba74;
            font-size: 0.8rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state():
    if "hermes_session" not in st.session_state:
        st.session_state.hermes_session = create_session()
    if "latest_result" not in st.session_state:
        st.session_state.latest_result = None


def reset_state(persona: str):
    st.session_state.hermes_session = create_session(persona=persona)
    st.session_state.latest_result = None


initialize_state()
session = st.session_state.hermes_session
latest_result = st.session_state.latest_result

with st.sidebar:
    st.subheader("Session Controls")
    persona = st.selectbox(
        "Active persona",
        options=list(PERSONAS.keys()),
        index=list(PERSONAS.keys()).index(session["persona"]),
        format_func=lambda key: PERSONAS[key]["label"],
    )

    if persona != session["persona"]:
        session["persona"] = persona

    st.caption(PERSONAS[session["persona"]]["description"])

    if st.button("Reset Session", use_container_width=True):
        reset_state(persona)
        st.rerun()

    st.divider()
    st.markdown("### State Snapshot")
    st.write(f"State: `{session['current_state']}`")
    st.write(f"Turns: `{session['turn_count']}`")
    st.write(f"Time wasted: `{format_duration(session['time_wasted_seconds'])}`")

st.markdown(
    """
    <div class="hero">
        <h1>Hermes Agentic Honeypot</h1>
        <p>Detect, engage, delay, and extract fraud intelligence through a shared stateful session pipeline.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(4)
risk_color = {"LOW": "#22c55e", "MEDIUM": "#f59e0b", "HIGH": "#ef4444"}

with metric_cols[0]:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Risk Score</div>
            <div class="metric-value" style="color:{risk_color.get(session['risk_level'], '#f8fafc')}">{session['risk_score']:.0%}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with metric_cols[1]:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Risk Level</div>
            <div class="metric-value" style="color:{risk_color.get(session['risk_level'], '#f8fafc')}">{session['risk_level']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with metric_cols[2]:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Agent State</div>
            <div class="metric-value">{session['current_state']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with metric_cols[3]:
    indicator_count = sum(
        len(session["all_extractions"].get(key, []))
        for key in ("upi_ids", "phone_numbers", "urls", "bank_accounts", "ifsc_codes", "aadhaar")
    )
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Time Wasted / Indicators</div>
            <div class="metric-value">{format_duration(session['time_wasted_seconds'])}</div>
            <div style="color:#94a3b8;font-size:0.85rem;">{indicator_count} indicators extracted</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

left, middle, right = st.columns([1.1, 1.4, 1.1])

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Detection Input")
    message = st.text_area(
        "Scammer message",
        placeholder="Paste the latest scam message or call transcript here...",
        height=180,
    )
    simulated_delay = st.slider("Simulated scammer time wasted per turn (seconds)", 5, 60, 18)
    if st.button("Analyze And Engage", type="primary", use_container_width=True):
        if message.strip():
            result = process_message(
                message=message.strip(),
                session=st.session_state.hermes_session,
                response_delay_seconds=simulated_delay,
            )
            st.session_state.latest_result = result
            st.rerun()

    if latest_result:
        st.markdown("### Latest Turn")
        st.write(f"Verdict: `{latest_result['detection']['verdict']}`")
        st.write(f"Scam type: `{latest_result['scam_type']}`")
        st.write(f"State score: `{latest_result['score']}`")
        if latest_result["reasons"]:
            st.write("Escalation reasons:")
            for reason in latest_result["reasons"]:
                st.write(f"- {reason}")
    st.markdown("</div>", unsafe_allow_html=True)

with middle:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Conversation Timeline")
    if session["conversation"]:
        for turn in reversed(session["conversation"][-10:]):
            css_class = "turn-ai" if turn["role"] == "ai" else "turn-scammer"
            score_text = ""
            if turn.get("score") is not None:
                score_text = f" • score {turn['score']:.0%}"
            st.markdown(
                f"""
                <div class="timeline-item {css_class}">
                    <div class="timeline-meta">{turn.get('timestamp', '')} • {turn['role'].upper()} • {turn.get('state', 'NA')}{score_text}</div>
                    <div>{turn['text']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No conversation yet. Run the first suspicious message through Hermes.")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Fraud Intelligence")
    extracted = session["all_extractions"]
    displayed_any = False
    for key in ("upi_ids", "phone_numbers", "urls", "bank_accounts", "ifsc_codes", "aadhaar"):
        values = extracted.get(key, [])
        if values:
            displayed_any = True
            st.markdown(f"**{key.replace('_', ' ').title()}**")
            st.markdown("".join(f'<span class="chip">{value}</span>' for value in values), unsafe_allow_html=True)
    if not displayed_any:
        st.caption("No indicators extracted yet.")

    st.markdown("### Scam Type History")
    if session["scam_types_seen"]:
        for scam_type in sorted(set(session["scam_types_seen"])):
            st.write(f"- {scam_type}")
    else:
        st.caption("No scam patterns classified yet.")

    report = build_report(session)
    st.download_button(
        "Download Intelligence Report",
        data=json.dumps(report, indent=2),
        file_name=f"hermes_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

if latest_result:
    st.markdown("### Live Risk Meter")
    st.progress(session["risk_score"])
    st.caption(
        f"Detection {latest_result['detection']['combined_score']:.0%} • "
        f"Session {session['session_score']:.0%} • "
        f"Time wasted {format_duration(session['time_wasted_seconds'])}"
    )
