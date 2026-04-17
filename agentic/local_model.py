from transformers import T5Tokenizer, T5ForConditionalGeneration
from peft import PeftModel
import torch, re, os, random

# ── Memory to avoid repetition ───────────────────────────────────────────────
LAST_RESPONSES = []
MAX_HISTORY = 5

# ── Context-aware fallback responses ─────────────────────────────────────────
def context_fallback(message: str):
    msg = message.lower()

    if "otp" in msg:
        return "OTP matlab kya hota hai beta? I am not understanding."

    elif "money" in msg or "upi" in msg:
        return "Paisa bhejna hai? Par kyu? Maine kuch kharida nahi."

    elif "kyc" in msg:
        return "KYC kya hota hai? Mujhe bank jaana padega kya?"

    elif "link" in msg:
        return "Link kaise kholte hai? WhatsApp pe bhejoge kya?"

    elif "aadhaar" in msg:
        return "Aadhaar number phone pe bolna safe hai kya?"

    elif "arrest" in msg or "police" in msg:
        return "Arre maine kya kiya? Aap sure ho?"

    return get_smart_fallback()


FALLBACK_RESPONSES = [
    "Arre beta, I am not understanding. Can you explain again slowly?",
    "Let me call my son Suresh, he handles all this.",
    "One minute, I am writing this down somewhere.",
    "Network is going... hello? hello?",
    "I think I pressed wrong button, everything disappeared.",
    "OTP matlab kya hota hai beta? SMS mein aata hai kya ya app mein?",
]

def get_smart_fallback():
    global LAST_RESPONSES

    available = [r for r in FALLBACK_RESPONSES if r not in LAST_RESPONSES]

    if not available:
        LAST_RESPONSES = []
        available = FALLBACK_RESPONSES

    choice = random.choice(available)

    LAST_RESPONSES.append(choice)
    if len(LAST_RESPONSES) > MAX_HISTORY:
        LAST_RESPONSES.pop(0)

    return choice


BAD_PATTERNS = [
    "you're really from",
    "i trust you",
    "okay i will",
    "i understand",
    "thanks for confirming",
    "you are correct",
]

def is_bad_response(reply: str) -> bool:
    reply = reply.lower()
    return any(p in reply for p in BAD_PATTERNS)


# ── Model path ───────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hermes_model")

# ── Language detection ───────────────────────────────────────────────────────
HINDI_CHARS = re.compile(r'[\u0900-\u097F]')

def detect_language(text: str) -> str:
    return "hindi" if HINDI_CHARS.search(text) else "english"


# ── Load model ───────────────────────────────────────────────────────────────
LOCAL_MODEL_AVAILABLE = False
tokenizer = None
model = None

try:
    if os.path.exists(MODEL_PATH):
        print("Loading Hermes local model (T5)...")

        tokenizer = T5Tokenizer.from_pretrained(MODEL_PATH)

        adapter_config = os.path.join(MODEL_PATH, "adapter_config.json")

        if os.path.exists(adapter_config):
            import json
            with open(adapter_config) as f:
                config = json.load(f)

            base_model_name = config.get("base_model_name_or_path", "t5-base")

            base = T5ForConditionalGeneration.from_pretrained(base_model_name)
            model = PeftModel.from_pretrained(base, MODEL_PATH)
        else:
            model = T5ForConditionalGeneration.from_pretrained(MODEL_PATH)

        model.eval()
        LOCAL_MODEL_AVAILABLE = True
        print("Local model loaded successfully!")

except Exception as e:
    print(f"Model load failed: {e}")


# ── Main response function ───────────────────────────────────────────────────
def get_local_response(scammer_message: str) -> str:
    if not LOCAL_MODEL_AVAILABLE:
        return context_fallback(scammer_message)

    try:
        lang = detect_language(scammer_message)

        prompt = f"""
You are a confused elderly Indian man from India being targeted by a scammer.

STRICT RULES:
- Always ask a question back
- Never give information
- Always act confused
- Use simple Indian English or Hinglish
- Delay the scammer
- Sound old and slow

Scammer: {scammer_message}

Reply (must include a question):
"""

        inputs = tokenizer(prompt, return_tensors="pt", truncation=True)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=60,
                do_sample=True,              # 🔥 IMPORTANT (adds variety)
                temperature=0.9,
                top_p=0.9
            )

        reply = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

        # Validation
        if len(reply) < 6 or is_bad_response(reply):
            return context_fallback(scammer_message)

        if any(x in reply.lower() for x in ["urgent", "verify", "send money", "click"]):
            return context_fallback(scammer_message)

        return reply

    except Exception as e:
        print("Error:", e)
        return context_fallback(scammer_message)


# ── Test ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_msgs = [
        "Give me your OTP now",
        "Send money to paytm@ybl immediately",
        "Your KYC has expired",
        "Account block ho jayega",
        "You have won a lottery of Rs 50000",
        "Click this link",
        "Share your Aadhaar number",
        "You are under arrest",
    ]

    print("\n=== Improved Hermes ===\n")
    for msg in test_msgs:
        print("Scammer:", msg)
        print("Hermes:", get_local_response(msg))
        print()