import re
from transformers import pipeline

# ── Layer 1: Keyword-based fast detection ──────────────────────────────────
SCAM_KEYWORDS = [
    "your account has been blocked", "send money immediately", "otp",
    "upi", "bank details", "kyc update", "prize money", "lottery",
    "arrest warrant", "aadhaar", "verify now", "limited time offer",
    "click this link", "transfer funds", "gift card", "wire transfer",
    "you have won", "confirm your details", "act now", "urgent"
]

def keyword_score(text: str) -> float:
    """Returns a score 0.0–1.0 based on how many scam keywords are found."""
    text_lower = text.lower()
    hits = sum(1 for kw in SCAM_KEYWORDS if kw in text_lower)
    return min(hits / 3.0, 1.0)  # Caps at 1.0 after 3+ hits


# ── Layer 2: BERT-based sentiment / intent classifier ──────────────────────
# We use a zero-shot classifier — no training data needed!
classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli"
)

SCAM_LABELS = ["financial scam", "phishing attempt", "normal conversation"]

def bert_score(text: str) -> float:
    """Returns probability that the text is a scam (0.0–1.0)."""
    result = classifier(text, candidate_labels=SCAM_LABELS)
    scores = dict(zip(result["labels"], result["scores"]))
    # Combine both scam-related labels
    return scores.get("financial scam", 0) + scores.get("phishing attempt", 0)


# ── Combined Detection ──────────────────────────────────────────────────────
def detect_scam(text: str) -> dict:
    """
    Main detection function.
    Returns a dictionary with confidence score and verdict.
    """
    kw = keyword_score(text)
    ml = bert_score(text)

    # Weighted average: keywords 40%, ML model 60%
    combined = (kw * 0.4) + (ml * 0.6)

    return {
        "text": text,
        "keyword_score": round(kw, 2),
        "ml_score": round(ml, 2),
        "combined_score": round(combined, 2),
        "is_scam": combined > 0.45,   # Threshold: adjust as needed
        "verdict": "SCAM DETECTED" if combined > 0.45 else "Looks safe"
    }


# ── Quick test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_messages = [
        "Your KYC is expired. Send your Aadhaar and OTP immediately to avoid account block.",
        "Hey, are you free for lunch tomorrow?",
        "Congratulations! You have won a lottery of Rs 50,000. Share your UPI ID now."
    ]
    for msg in test_messages:
        result = detect_scam(msg)
        print(f"\nText: {msg[:60]}...")
        print(f"  Score: {result['combined_score']}  →  {result['verdict']}")