from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch, re, os

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_MODEL = "microsoft/DialoGPT-small"
ADAPTER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hermes_model")

# ── Language detection ────────────────────────────────────────────────────────
HINDI_CHARS = re.compile(r'[\u0900-\u097F]')
HINDI_WORDS = ["kya","hai","karo","bata","mera","tera","otp",
               "paisa","jaldi","bhejo","batao","band","block"]

def detect_language(text):
    if HINDI_CHARS.search(text):
        return "hindi"
    return "hindi" if sum(1 for w in HINDI_WORDS if w in text.lower().split()) >= 2 else "english"

# ── Load model ────────────────────────────────────────────────────────────────
LOCAL_MODEL_AVAILABLE = False

try:
    if os.path.exists(ADAPTER_PATH):
        print("Loading Hermes local model...")

        tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH)
        tokenizer.pad_token = tokenizer.eos_token

        base = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            torch_dtype=torch.float32,  # float32 for CPU — safe on 4GB RAM
            low_cpu_mem_usage=True
        )

        model = PeftModel.from_pretrained(base, ADAPTER_PATH)
        model.eval()

        LOCAL_MODEL_AVAILABLE = True
        print("Local model loaded successfully!")
    else:
        print(f"hermes_model folder not found at: {ADAPTER_PATH}")
        print("Skipping local model — will use rule-based + Gemini fallback.")

except Exception as e:
    print(f"Could not load local model: {e}")
    print("Falling back to rule-based + Gemini.")

# ── Inference ─────────────────────────────────────────────────────────────────
def get_local_response(scammer_message: str) -> str:
    if not LOCAL_MODEL_AVAILABLE:
        return None

    try:
        prompt = f"Scammer: {scammer_message}\nHermes:"

        inputs = tokenizer.encode(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=100
        )

        # Create attention mask to fix the warning
        attention_mask = torch.ones(inputs.shape, dtype=torch.long)

        with torch.no_grad():
            outputs = model.generate(
                inputs,
                attention_mask=attention_mask,
                max_new_tokens=25,        # Very short — cut off before hallucination
                do_sample=True,
                temperature=0.7,          # Lower = more focused
                top_p=0.85,
                top_k=40,
                pad_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.5,
                # Stop generating at sentence end
                eos_token_id=[
                    tokenizer.eos_token_id,
                    tokenizer.encode(".")[0],
                    tokenizer.encode("!")[0],
                    tokenizer.encode("?")[0],
                ],
            )

        new_tokens = outputs[0][inputs.shape[1]:]
        reply = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        # Clean up — take only first sentence
        for punct in [".", "!", "?"]:
            if punct in reply:
                reply = reply.split(punct)[0] + punct
                break

        # Quality checks
        if len(reply) < 8:
            return None
        if "grandson" in reply.lower() and "grandson" in prompt.lower():
            return None
        # Reject if it sounds nothing like Hermes
        scam_words = ["otp","upi","bank","account","kyc","link","aadhaar","money","transfer"]
        hermes_words = ["beta","app","phone","wait","sorry","spectacles","son","please"]
        has_context = any(w in reply.lower() for w in scam_words + hermes_words)
        if not has_context and len(reply) > 60:
            return None

        return reply

    except Exception as e:
        print(f"Local model inference error: {e}")
        return None


# ── Test ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_messages = [
        "Give me your OTP now",
        "Send money to paytm@ybl immediately",
        "Your KYC has expired",
        "Account block ho jayega",
        "You have won a lottery of Rs 50000",
        "Click this link to verify your account",
        "Share your Aadhaar number",
    ]

    print("\n=== Testing Hermes Local Model ===\n")
    for msg in test_messages:
        reply = get_local_response(msg)
        print(f"Scammer: {msg}")
        print(f"Hermes:  {reply if reply else '(no response — fallback will handle)'}")
        print()