import re
import spacy

nlp = spacy.load("en_core_web_sm")

# ── Regex patterns for Indian fraud context ────────────────────────────────
PATTERNS = {
    "upi_ids":      r'[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}',
    "phone_numbers": r'\b[6-9]\d{9}\b',                      # Indian mobile numbers
    "urls":         r'https?://[^\s]+|www\.[^\s]+',
    "bank_accounts": r'\b\d{9,18}\b',
    "ifsc_codes":   r'\b[A-Z]{4}0[A-Z0-9]{6}\b',
    "aadhaar":      r'\b\d{4}\s?\d{4}\s?\d{4}\b',
}

def extract_fraud_data(text: str) -> dict:
    """Extract all fraud indicators from a piece of text."""
    findings = {}

    for label, pattern in PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            findings[label] = list(set(matches))  # Remove duplicates

    # Use spaCy to extract named entities (people, orgs, locations)
    doc = nlp(text)
    entities = {}
    for ent in doc.ents:
        if ent.label_ not in entities:
            entities[ent.label_] = []
        entities[ent.label_].append(ent.text)

    findings["named_entities"] = entities
    findings["raw_text"] = text
    return findings


def summarize_extraction(findings: dict) -> str:
    """Create a human-readable summary of what was found."""
    lines = ["=== Fraud Intelligence Report ==="]
    for key, value in findings.items():
        if key not in ("raw_text", "named_entities") and value:
            lines.append(f"  {key.replace('_', ' ').title()}: {value}")
    if findings.get("named_entities"):
        lines.append(f"  Entities: {findings['named_entities']}")
    return "\n".join(lines)


if __name__ == "__main__":
    sample = """
    Send Rs 5000 to paytm@ybl or call 9876543210.
    Visit http://fake-bank-kyc.com for verification.
    Your account 123456789012 will be blocked.
    """
    result = extract_fraud_data(sample)
    print(summarize_extraction(result))