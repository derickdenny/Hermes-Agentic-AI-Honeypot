import re

try:
    from transformers import pipeline
except Exception:  # pragma: no cover - optional dependency path
    pipeline = None


SCAM_KEYWORDS = [
    "your account has been blocked",
    "send money immediately",
    "otp",
    "upi",
    "bank details",
    "kyc update",
    "prize money",
    "lottery",
    "arrest warrant",
    "aadhaar",
    "verify now",
    "limited time offer",
    "click this link",
    "transfer funds",
    "gift card",
    "wire transfer",
    "you have won",
    "confirm your details",
    "act now",
    "urgent",
]

SCAM_LABELS = ["financial scam", "phishing attempt", "normal conversation"]
_CLASSIFIER = None
_CLASSIFIER_LOAD_FAILED = False


def keyword_score(text: str) -> float:
    """Return a fast 0-1 score based on keyword hits."""
    text_lower = text.lower()
    hits = sum(1 for keyword in SCAM_KEYWORDS if keyword in text_lower)
    return min(hits / 3.0, 1.0)


def _get_classifier():
    global _CLASSIFIER, _CLASSIFIER_LOAD_FAILED

    if _CLASSIFIER is not None or _CLASSIFIER_LOAD_FAILED or pipeline is None:
        return _CLASSIFIER

    try:
        _CLASSIFIER = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
        )
    except Exception:
        _CLASSIFIER_LOAD_FAILED = True
        _CLASSIFIER = None

    return _CLASSIFIER


def bert_score(text: str) -> float:
    """Return scam probability from the zero-shot model when available."""
    classifier = _get_classifier()
    if classifier is None:
        return 0.0

    result = classifier(text, candidate_labels=SCAM_LABELS)
    scores = dict(zip(result["labels"], result["scores"]))
    return scores.get("financial scam", 0.0) + scores.get("phishing attempt", 0.0)


def detect_scam(text: str) -> dict:
    """Return keyword, ML, and combined scam signals for a message."""
    kw = keyword_score(text)
    ml = bert_score(text)

    if _get_classifier() is None:
        combined = kw
        model_status = "keyword-only"
    else:
        combined = (kw * 0.4) + (ml * 0.6)
        model_status = "hybrid"

    combined = round(min(combined, 1.0), 2)
    threshold = 0.45

    return {
        "text": text,
        "keyword_score": round(kw, 2),
        "ml_score": round(ml, 2),
        "combined_score": combined,
        "is_scam": combined > threshold,
        "verdict": "SCAM DETECTED" if combined > threshold else "Looks safe",
        "model_status": model_status,
    }


if __name__ == "__main__":
    test_messages = [
        "Your KYC is expired. Send your Aadhaar and OTP immediately to avoid account block.",
        "Hey, are you free for lunch tomorrow?",
        "Congratulations! You have won a lottery of Rs 50,000. Share your UPI ID now.",
    ]

    for message in test_messages:
        result = detect_scam(message)
        print(f"\nText: {message[:60]}...")
        print(f"  Score: {result['combined_score']} -> {result['verdict']}")
