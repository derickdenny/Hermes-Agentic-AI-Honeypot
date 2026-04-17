class StateManager:
    def __init__(self, decay: float = 0.75):
        self.state = "NEUTRAL"
        self.score = 0.0
        self.decay = decay

    def _transition(self, score: float) -> str:
        if score < 0.25:
            return "NEUTRAL"
        if score < 0.5:
            return "SUSPICIOUS"
        if score < 0.75:
            return "SCAM"
        return "EXTRACTION"

    def update(self, detection_score: float, message: str = "", extraction=None, behavior=None):
        extraction = extraction or {}
        behavior = behavior or {}

        bonus = 0.0
        reasons = []

        if behavior.get("repeat_otp_request"):
            bonus += 0.2
            reasons.append("Repeated OTP request")
        if behavior.get("repeat_payment_request"):
            bonus += 0.18
            reasons.append("Repeated payment request")
        if behavior.get("high_pressure_language"):
            bonus += 0.12
            reasons.append("High-pressure language")

        indicator_hits = 0
        for key in ("upi_ids", "phone_numbers", "urls", "bank_accounts", "ifsc_codes", "aadhaar"):
            indicator_hits += len(extraction.get(key, []))
        if indicator_hits:
            bonus += min(indicator_hits * 0.08, 0.25)
            reasons.append(f"{indicator_hits} fraud indicators extracted")

        if "otp" in message.lower():
            bonus += 0.05
            reasons.append("OTP mentioned")

        raw_score = (self.score * self.decay) + detection_score + bonus
        self.score = round(min(raw_score, 1.0), 2)
        previous_state = self.state
        self.state = self._transition(self.score)

        if self.state == "EXTRACTION" and not reasons:
            reasons.append("Session score crossed extraction threshold")

        return {
            "state": self.state,
            "score": self.score,
            "transitioned": self.state != previous_state,
            "previous_state": previous_state,
            "reasons": reasons,
        }
