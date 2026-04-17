from copy import deepcopy
from datetime import datetime

from agentic.honeypot_agent import get_honeypot_response
from agentic.state_manager import StateManager
from detection.scam_detector import detect_scam
from extraction.extractor import extract_fraud_data


PERSONAS = {
    "elderly_man": {
        "label": "Elderly Man",
        "description": "Slow, confused retired bank customer",
    },
    "busy_woman": {
        "label": "Busy Woman",
        "description": "Distracted professional who keeps multitasking",
    },
    "tech_newbie": {
        "label": "Tech Newbie",
        "description": "Younger user who is bad with digital payments",
    },
}


def create_session(persona: str = "elderly_man") -> dict:
    persona_key = persona if persona in PERSONAS else "elderly_man"
    return {
        "persona": persona_key,
        "created_at": datetime.utcnow().isoformat(),
        "conversation": [],
        "ai_history": [],
        "detections": [],
        "all_extractions": {},
        "state_manager": StateManager(),
        "current_state": "NEUTRAL",
        "session_score": 0.0,
        "risk_score": 0.0,
        "risk_level": "LOW",
        "turn_count": 0,
        "time_wasted_seconds": 0,
        "scam_types_seen": [],
        "behavior_flags": {
            "otp_requests": 0,
            "payment_requests": 0,
            "urgent_requests": 0,
        },
        "latest_report": None,
    }


def _merge_extractions(existing: dict, new_data: dict) -> dict:
    merged = deepcopy(existing)
    for key, value in new_data.items():
        if key in ("raw_text", "named_entities"):
            continue
        if not value:
            continue
        merged.setdefault(key, [])
        merged[key] = sorted(set(merged[key] + value))

    named_entities = merged.setdefault("named_entities", {})
    for label, values in new_data.get("named_entities", {}).items():
        named_entities.setdefault(label, [])
        named_entities[label] = sorted(set(named_entities[label] + values))

    return merged


def _classify_scam_type(message: str) -> str:
    text = message.lower()
    if any(token in text for token in ["otp", "upi", "bank", "transfer", "account"]):
        return "Financial Fraud"
    if any(token in text for token in ["kyc", "aadhaar", "verify", "update"]):
        return "Identity Phishing"
    if any(token in text for token in ["lottery", "won", "prize", "gift"]):
        return "Lottery Scam"
    if any(token in text for token in ["arrest", "police", "court", "legal"]):
        return "Legal Threat Scam"
    if any(token in text for token in ["link", "http", "website", "click"]):
        return "Malicious Link Scam"
    return "Unknown"


def _analyze_behavior(message: str, session: dict) -> dict:
    text = message.lower()
    flags = session["behavior_flags"]

    if "otp" in text:
        flags["otp_requests"] += 1
    if any(token in text for token in ["upi", "send money", "transfer", "pay", "deposit"]):
        flags["payment_requests"] += 1
    if any(token in text for token in ["urgent", "immediately", "now", "quick", "jaldi"]):
        flags["urgent_requests"] += 1

    return {
        "repeat_otp_request": flags["otp_requests"] >= 2,
        "repeat_payment_request": flags["payment_requests"] >= 2,
        "high_pressure_language": flags["urgent_requests"] >= 1,
    }


def _decide_response(state: str, session: dict, message: str) -> tuple[str, list]:
    if state == "NEUTRAL":
        return "Okay, can you explain what this is about?", session["ai_history"]

    if state == "SUSPICIOUS":
        return "I am not following. Can you explain that slowly once more?", session["ai_history"]

    return get_honeypot_response(
        session["ai_history"],
        message,
        state=state,
        persona=session["persona"],
    )


def _calculate_risk(detection: dict, session: dict) -> tuple[float, str]:
    indicator_count = sum(
        len(session["all_extractions"].get(key, []))
        for key in ("upi_ids", "phone_numbers", "urls", "bank_accounts", "ifsc_codes", "aadhaar")
    )
    indicator_bonus = min(indicator_count * 0.04, 0.2)
    combined = min(
        (detection["combined_score"] * 0.45)
        + (session["session_score"] * 0.45)
        + indicator_bonus
        + (0.05 if session["turn_count"] >= 3 else 0.0),
        1.0,
    )
    if combined >= 0.75:
        level = "HIGH"
    elif combined >= 0.45:
        level = "MEDIUM"
    else:
        level = "LOW"
    return round(combined, 2), level


def format_duration(total_seconds: int) -> str:
    minutes, seconds = divmod(max(total_seconds, 0), 60)
    return f"{minutes}m {seconds:02d}s"


def build_report(session: dict) -> dict:
    return {
        "report_id": f"HRP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "persona": session["persona"],
        "state": session["current_state"],
        "risk_level": session["risk_level"],
        "risk_score": session["risk_score"],
        "session_score": session["session_score"],
        "scam_types": sorted(set(session["scam_types_seen"])),
        "conversation_turns": session["turn_count"],
        "time_wasted_seconds": session["time_wasted_seconds"],
        "time_wasted_human": format_duration(session["time_wasted_seconds"]),
        "behavior_flags": session["behavior_flags"],
        "extracted_indicators": session["all_extractions"],
        "conversation_log": [
            {
                "role": item["role"],
                "text": item["text"],
                "state": item.get("state"),
                "score": item.get("score"),
                "timestamp": item.get("timestamp"),
            }
            for item in session["conversation"]
        ],
    }


def process_turn(message: str, session: dict | None = None, response_delay_seconds: int = 18) -> dict:
    working_session = session if session is not None else create_session()

    detection = detect_scam(message)
    extraction = extract_fraud_data(message)
    behavior = _analyze_behavior(message, working_session)
    state_info = working_session["state_manager"].update(
        detection_score=detection["combined_score"],
        message=message,
        extraction=extraction,
        behavior=behavior,
    )

    working_session["current_state"] = state_info["state"]
    working_session["session_score"] = state_info["score"]
    working_session["all_extractions"] = _merge_extractions(
        working_session["all_extractions"],
        extraction,
    )
    working_session["detections"].append(detection)

    scam_type = _classify_scam_type(message)
    if detection["is_scam"] or state_info["state"] != "NEUTRAL":
        working_session["scam_types_seen"].append(scam_type)

    reply, updated_history = _decide_response(state_info["state"], working_session, message)
    working_session["ai_history"] = updated_history
    working_session["turn_count"] += 1

    if state_info["state"] in {"SCAM", "EXTRACTION"}:
        working_session["time_wasted_seconds"] += response_delay_seconds

    timestamp = datetime.now().isoformat(timespec="seconds")
    working_session["conversation"].append(
        {
            "role": "scammer",
            "text": message,
            "score": detection["combined_score"],
            "state": state_info["state"],
            "timestamp": timestamp,
        }
    )
    working_session["conversation"].append(
        {
            "role": "ai",
            "text": reply,
            "state": state_info["state"],
            "timestamp": timestamp,
        }
    )

    working_session["risk_score"], working_session["risk_level"] = _calculate_risk(
        detection,
        working_session,
    )
    working_session["latest_report"] = build_report(working_session)

    return {
        "detection": detection,
        "state": state_info["state"],
        "score": state_info["score"],
        "response": reply,
        "extraction": extraction,
        "session": working_session,
        "risk_score": working_session["risk_score"],
        "risk_level": working_session["risk_level"],
        "scam_type": scam_type,
        "time_wasted_seconds": working_session["time_wasted_seconds"],
        "time_wasted_human": format_duration(working_session["time_wasted_seconds"]),
        "reasons": state_info["reasons"],
        "report": working_session["latest_report"],
    }
