import streamlit as st
import json, os, sys
from datetime import datetime
from main import process_message

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detection.scam_detector import detect_scam
from extraction.extractor import extract_fraud_data
from agentic.honeypot_agent import get_honeypot_response

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hermes Honeypot",
    page_icon="🍯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stApp { background-color: #0e1117; }

    .hero-title {
        font-size: 2.4rem; font-weight: 700;
        background: linear-gradient(90deg, #f97316, #ef4444);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 0.2rem;
    }
    .hero-sub {
        text-align: center; color: #6b7280;
        font-size: 0.95rem; margin-bottom: 2rem;
    }

    .card {
        background: #1c1f26; border: 1px solid #2d3139;
        border-radius: 12px; padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .card-title {
        font-size: 0.8rem; font-weight: 600;
        color: #9ca3af; letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 0.6rem;
    }

    .scam-bubble {
        background: #2d1f1f; border-left: 3px solid #ef4444;
        border-radius: 8px; padding: 0.7rem 1rem;
        margin-bottom: 0.5rem; color: #fca5a5; font-size: 0.9rem;
    }
    .ai-bubble {
        background: #1a2a1a; border-left: 3px solid #22c55e;
        border-radius: 8px; padding: 0.7rem 1rem;
        margin-bottom: 0.5rem; color: #86efac; font-size: 0.9rem;
    }
    .system-bubble {
        background: #1e1f2e; border-left: 3px solid #6366f1;
        border-radius: 8px; padding: 0.5rem 1rem;
        margin-bottom: 0.5rem; color: #a5b4fc; font-size: 0.8rem;
    }

    .badge-red   { background:#4b1a1a; color:#f87171; border-radius:6px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
    .badge-amber { background:#3b2a0e; color:#fbbf24; border-radius:6px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
    .badge-green { background:#0f2e1a; color:#4ade80; border-radius:6px; padding:2px 10px; font-size:0.78rem; font-weight:600; }

    .metric-box {
        background: #1c1f26; border: 1px solid #2d3139;
        border-radius: 10px; padding: 0.9rem 1rem; text-align: center;
    }
    .metric-value { font-size: 1.8rem; font-weight: 700; }
    .metric-label { font-size: 0.75rem; color: #6b7280; margin-top: 2px; }

    .indicator {
        display: inline-block; width: 10px; height: 10px;
        border-radius: 50%; margin-right: 6px;
    }
    .ind-red   { background: #ef4444; }
    .ind-green { background: #22c55e; }
    .ind-gray  { background: #4b5563; }

    div[data-testid="stButton"] button {
        border-radius: 8px; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────────────
defaults = {
    "conversation": [],
    "ai_history": [],
    "all_extractions": {},
    "handover_active": False,
    "detection_result": None,
    "turn_count": 0,
    "scam_types_seen": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">🍯 Hermes — Agentic AI Honeypot</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Scam & Fraud Intelligence System · Real-time Detection · Active Deception</div>', unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ System Status")

    honeypot_status = "🟢 Active" if st.session_state.handover_active else "🔴 Standby"
    st.markdown(f"**Honeypot Agent:** {honeypot_status}")
    st.markdown(f"**Conversation Turns:** {st.session_state.turn_count}")

    ex = st.session_state.all_extractions
    indicators_found = sum(len(v) for v in ex.values() if isinstance(v, list))
    st.markdown(f"**Indicators Extracted:** {indicators_found}")

    st.divider()
    st.markdown("### 📋 Scam Types Detected")
    if st.session_state.scam_types_seen:
        for s in set(st.session_state.scam_types_seen):
            st.markdown(f"- {s}")
    else:
        st.caption("None yet")

    st.divider()
    if st.button("🔄 Reset Session", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ── Top metrics row ──────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)

score = st.session_state.detection_result["combined_score"] if st.session_state.detection_result else 0
risk  = "HIGH" if score > 0.7 else "MEDIUM" if score > 0.45 else "LOW"
risk_color = "#ef4444" if risk=="HIGH" else "#f59e0b" if risk=="MEDIUM" else "#22c55e"

with m1:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-value" style="color:{risk_color}">{score:.0%}</div>
        <div class="metric-label">Scam Confidence</div>
    </div>""", unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-value" style="color:{risk_color}">{risk}</div>
        <div class="metric-label">Risk Level</div>
    </div>""", unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-value" style="color:#6366f1">{st.session_state.turn_count}</div>
        <div class="metric-label">Turns Engaged</div>
    </div>""", unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-value" style="color:#f97316">{indicators_found}</div>
        <div class="metric-label">Indicators Found</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Main layout: 3 columns ───────────────────────────────────────────────────
col1, col2, col3 = st.columns([1.1, 1.5, 1.2])

# ══════════════════════════════════════════════════════════
# COLUMN 1 — Detection Engine
# ══════════════════════════════════════════════════════════
with col1:
    st.markdown('<div class="card-title">🔍 Detection Engine</div>', unsafe_allow_html=True)

    msg_input = st.text_area(
        "Incoming message:",
        placeholder="Paste a suspicious message here...",
        height=110, label_visibility="collapsed"
    )

    if st.button("⚡ Analyze", use_container_width=True, type="primary"):
        if msg_input.strip():
            with st.spinner("Analyzing..."):
                result = process_message(msg_input)
                st.session_state.detection_result = result

                # Classify scam type roughly
                text_lower = msg_input.lower()
                if any(w in text_lower for w in ["otp","upi","bank","account","transfer"]):
                    scam_type = "Financial Fraud"
                elif any(w in text_lower for w in ["kyc","aadhaar","verify","update"]):
                    scam_type = "Identity Phishing"
                elif any(w in text_lower for w in ["lottery","won","prize","gift"]):
                    scam_type = "Lottery Scam"
                elif any(w in text_lower for w in ["arrest","police","court","legal"]):
                    scam_type = "Legal Threat Scam"
                else:
                    scam_type = "Unknown"
                if result["is_scam"]:
                    st.session_state.scam_types_seen.append(scam_type)

                # Extract
                extraction = extract_fraud_data(msg_input)
                for k, v in extraction.items():
                    if k not in ("raw_text","named_entities") and v:
                        st.session_state.all_extractions.setdefault(k, [])
                        st.session_state.all_extractions[k] = list(
                            set(st.session_state.all_extractions[k] + v)
                        )

                st.session_state.conversation.append({
                    "role": "scammer", "text": msg_input,
                    "score": result["combined_score"]
                })
                st.session_state.turn_count += 1
                st.rerun()

    # Detection result
    if st.session_state.detection_result:
        r = st.session_state.detection_result
        s = r["combined_score"]
        badge = f'<span class="badge-red">⚠ SCAM</span>' if r["is_scam"] else '<span class="badge-green">✓ SAFE</span>'
        st.markdown(badge, unsafe_allow_html=True)
        st.progress(s)
        st.caption(f"Keyword: {r['keyword_score']}  ·  ML: {r['ml_score']}  ·  Combined: {r['combined_score']}")

        if r["is_scam"] and not st.session_state.handover_active:
            st.warning("Scam detected! Hand over to AI?")
            if st.button("🤖 Activate Honeypot Agent", type="primary", use_container_width=True):
                st.session_state.handover_active = True
                st.session_state.conversation.append({
                    "role": "system",
                    "text": "Honeypot activated. Hermes has taken over the conversation."
                })
                st.rerun()

    # Scam type
    if st.session_state.scam_types_seen:
        latest = st.session_state.scam_types_seen[-1]
        st.markdown(f"**Scam type:** `{latest}`")

# ══════════════════════════════════════════════════════════
# COLUMN 2 — Live Conversation
# ══════════════════════════════════════════════════════════
with col2:
    st.markdown('<div class="card-title">💬 Live Conversation</div>', unsafe_allow_html=True)

    if st.session_state.handover_active:
        honeypot_msg = st.text_input(
            "Scammer says:",
            placeholder="Type what the scammer says next...",
            label_visibility="collapsed"
        )
    if st.button("➤ Send to Hermes", use_container_width=True):
        if honeypot_msg.strip():
            with st.spinner("Hermes is thinking..."):
                try:
                    reply, st.session_state.ai_history = get_honeypot_response(
                        st.session_state.ai_history, honeypot_msg
                    )
                    extraction = extract_fraud_data(honeypot_msg)
                    for k, v in extraction.items():
                        if k not in ("raw_text", "named_entities") and v:
                            st.session_state.all_extractions.setdefault(k, [])
                            st.session_state.all_extractions[k] = list(
                                set(st.session_state.all_extractions[k] + v)
                            )
                    st.session_state.conversation.append({"role": "scammer", "text": honeypot_msg, "score": None})
                    st.session_state.conversation.append({"role": "ai", "text": reply, "score": None})
                    st.session_state.turn_count += 1
                    st.rerun()

                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        st.warning("⏳ API quota hit — please wait 30 seconds, then try again.")
                    else:
                        st.error(f"Something went wrong: {e}")

    # Render conversation
    chat_html = ""
    for msg in st.session_state.conversation:
        if msg["role"] == "scammer":
            score_tag = f' <span style="font-size:0.75rem;color:#9ca3af;">({msg["score"]:.0%} confidence)</span>' if msg.get("score") else ""
            chat_html += f'<div class="scam-bubble">🦹 <b>Scammer:</b> {msg["text"]}{score_tag}</div>'
        elif msg["role"] == "ai":
            chat_html += f'<div class="ai-bubble">🤖 <b>Hermes:</b> {msg["text"]}</div>'
        elif msg["role"] == "system":
            chat_html += f'<div class="system-bubble">⚙ {msg["text"]}</div>'

    if chat_html:
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.caption("No conversation yet. Analyze a message to begin.")

# ══════════════════════════════════════════════════════════
# COLUMN 3 — Intelligence Report
# ══════════════════════════════════════════════════════════
with col3:
    st.markdown('<div class="card-title">📊 Fraud Intelligence</div>', unsafe_allow_html=True)

    ex = st.session_state.all_extractions
    if ex:
        if ex.get("upi_ids"):
            st.markdown("**💸 UPI IDs**")
            for u in ex["upi_ids"]:
                st.markdown(f'<span class="badge-red">{u}</span>', unsafe_allow_html=True)
            st.markdown("")

        if ex.get("phone_numbers"):
            st.markdown("**📞 Phone Numbers**")
            for p in ex["phone_numbers"]:
                st.markdown(f'<span class="badge-amber">{p}</span>', unsafe_allow_html=True)
            st.markdown("")

        if ex.get("urls"):
            st.markdown("**🔗 Suspicious URLs**")
            for u in ex["urls"]:
                st.markdown(f'<span class="badge-red">{u}</span>', unsafe_allow_html=True)
            st.markdown("")

        if ex.get("bank_accounts"):
            st.markdown("**🏦 Account Numbers**")
            for a in ex["bank_accounts"]:
                st.markdown(f'<span class="badge-amber">{a}</span>', unsafe_allow_html=True)
            st.markdown("")

        if ex.get("aadhaar"):
            st.markdown("**🪪 Aadhaar Patterns**")
            for a in ex["aadhaar"]:
                st.markdown(f'<span class="badge-red">{a}</span>', unsafe_allow_html=True)
            st.markdown("")
    else:
        st.caption("No indicators extracted yet.")

    st.divider()

    # Generate report
    if st.session_state.conversation:
        if st.button("📄 Generate Report", use_container_width=True):
            report = {
                "report_id": f"HRP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "risk_level": risk,
                "scam_confidence": score,
                "scam_types": list(set(st.session_state.scam_types_seen)),
                "conversation_turns": st.session_state.turn_count,
                "honeypot_engaged": st.session_state.handover_active,
                "extracted_indicators": st.session_state.all_extractions,
                "conversation_log": [
                    {"role": m["role"], "text": m["text"]}
                    for m in st.session_state.conversation
                ]
            }
            st.download_button(
                label="⬇️ Download JSON Report",
                data=json.dumps(report, indent=2),
                file_name=f"hermes_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True
            )