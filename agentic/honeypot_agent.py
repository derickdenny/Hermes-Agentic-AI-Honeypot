import os
import random
import re
import time

from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - optional dependency path
    genai = None
    types = None


load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

API_KEYS = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
]
API_KEYS = [key for key in API_KEYS if key]
current_key_index = 0

PERSONA_PROMPTS = {
    "elderly_man": (
        "You are Hermes, a 68-year-old confused retired government employee from Pune. "
        "You are slow, cautious, and keep asking for clarification."
    ),
    "busy_woman": (
        "You are Anita, a busy office worker handling chores and work calls at the same time. "
        "You are distracted, impatient, and keep asking the caller to repeat things."
    ),
    "tech_newbie": (
        "You are Rohan, a new smartphone user who understands basic apps but gets confused by banking flows. "
        "You ask simple technical questions and make small mistakes."
    ),
}


def get_client():
    if genai is None or not API_KEYS:
        return None
    return genai.Client(api_key=API_KEYS[current_key_index])


HINDI_CHARS = re.compile(r"[\u0900-\u097F]")
HINDI_WORDS = [
    "kya",
    "hai",
    "karo",
    "bata",
    "mera",
    "tera",
    "aap",
    "tum",
    "nahi",
    "haan",
    "paisa",
    "rupaye",
    "abhi",
    "bhejo",
    "batao",
    "account",
    "number",
    "jaldi",
    "band",
    "block",
]


def detect_language(text: str) -> str:
    if HINDI_CHARS.search(text):
        return "hindi"
    hits = sum(1 for word in HINDI_WORDS if word in text.lower().split())
    return "hindi" if hits >= 2 else "english"


RESPONSE_MAP_EN = {
    "otp": [
        "OTP? Which app should I open? There are too many icons on my phone.",
        "The OTP came but vanished before I could read it. Should I wait for another one?",
        "My son told me not to share OTPs. Why do you need it again?",
    ],
    "upi": [
        "Which UPI app do you want me to use, GPay or PhonePe? I always mix them up.",
        "The app is open but it wants a PIN. Should I reset it first?",
        "I can see the payment page, but there are too many buttons. Which one now?",
    ],
    "link": [
        "The link opened very slowly. Is it supposed to download something?",
        "Which browser should I use for this, Chrome or the blue one?",
        "I clicked once already and now it says retry. Should I click again?",
    ],
    "account": [
        "I have two accounts. Which one are you talking about?",
        "My passbook is here somewhere. Give me a minute to find it.",
        "The account number is written very small. Let me get my glasses.",
    ],
    "kyc": [
        "I did KYC last year. Does it expire again so quickly?",
        "Do you need Aadhaar for KYC or just the account number?",
        "Can I do this later today? I am not at home right now.",
    ],
    "block": [
        "Please do not block it. Tell me the next step slowly.",
        "If it gets blocked, my pension will stop. How much time do I have?",
        "I am trying, but I am not fast with these apps.",
    ],
    "urgent": [
        "I understand it is urgent, but I am still opening the app.",
        "Please wait, I am doing it. The network is very slow today.",
        "You are speaking fast. Can you repeat the step once more?",
    ],
    "send_money": [
        "How much do I need to send exactly, and to which account?",
        "Should I send from the app or from ATM? I do not know which is safer.",
        "If I send this, will it definitely fix the problem?",
    ],
    "aadhaar": [
        "Do you need the number or the card photo? I am confused.",
        "My Aadhaar has an old address. Will that be a problem?",
        "I found the card, but the print is faded. Give me a moment.",
    ],
}

RESPONSE_MAP_HI = {
    "otp": [
        "OTP aaya tha, par ab gayab ho gaya. Dobara bhejoge kya?",
        "OTP share karna safe hai kya? Mere ghar wale mana karte hain.",
        "Message dikha tha par number chhote the. Chashma laun kya?",
    ],
    "upi": [
        "UPI mein kaunsa app kholun, GPay ya PhonePe?",
        "App khula hai par PIN maang raha hai. Kya karun ab?",
        "Screen par bahut options aa rahe hain. Kaunsa dabana hai?",
    ],
    "block": [
        "Block mat karo please, dheere dheere samjhao mujhe.",
        "Agar block hua toh paise kaise nikalenge? Thoda time do.",
        "Main koshish kar raha hoon, bas samajhne mein time lag raha hai.",
    ],
    "account": [
        "Passbook dhoondh raha hoon, ek minute rukna.",
        "Do account hain mere, kaunsa chahiye aapko?",
        "Number chhota likha hai, chashma pehen ke dekhta hoon.",
    ],
}

GENERIC_EN = [
    "I did not understand that properly. Can you explain it once more?",
    "Please wait, I am writing this down.",
    "The phone network is poor here. Say that again slowly.",
    "Which step are we on now? I got confused in between.",
]

GENERIC_HI = [
    "Theek se samajh nahi aaya. Ek baar fir se bolo.",
    "Ruko, main likh raha hoon. Dobara batao.",
    "Network weak hai, zara dheere bolo.",
    "Kaunsa step tha ye? Main beech mein confuse ho gaya.",
]

used_responses = {}


def get_rule_based_response(message: str, lang: str) -> str:
    msg_lower = message.lower()
    intent_map = {
        "otp": ["otp", "one time", "password", "code"],
        "upi": ["upi", "gpay", "phonepe", "paytm", "transfer", "pay"],
        "link": ["link", "click", "website", "url", "http", "open"],
        "account": ["account", "number", "ac no", "acno"],
        "kyc": ["kyc", "verification", "verify"],
        "block": ["block", "suspend", "freeze", "closed", "band"],
        "urgent": ["urgent", "immediately", "now", "quick", "jaldi"],
        "send_money": ["send", "transfer", "deposit", "bhejo"],
        "aadhaar": ["aadhaar", "aadhar", "uid", "identity"],
    }

    matched_intent = None
    for intent, keywords in intent_map.items():
        if any(keyword in msg_lower for keyword in keywords):
            matched_intent = intent
            break

    if lang == "hindi":
        pool = RESPONSE_MAP_HI.get(matched_intent, GENERIC_HI)
    else:
        pool = RESPONSE_MAP_EN.get(matched_intent, GENERIC_EN)

    key = f"{lang}_{matched_intent or 'generic'}"
    used_responses.setdefault(key, [])
    available = [index for index in range(len(pool)) if index not in used_responses[key]]
    if not available:
        used_responses[key] = []
        available = list(range(len(pool)))

    chosen_index = random.choice(available)
    used_responses[key].append(chosen_index)
    return pool[chosen_index]


def build_system_prompt(lang: str, persona: str) -> str:
    lang_instruction = "Reply only in Hindi or Hinglish." if lang == "hindi" else "Reply only in English."
    persona_prompt = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS["elderly_man"])
    return (
        f"{persona_prompt} {lang_instruction} "
        "Keep replies under 2 short sentences. Never reveal you are an AI. "
        "Stall the scammer, ask questions back, and avoid giving real information."
    )


def get_honeypot_response(conversation_history: list, new_message: str, state="SCAM", persona="elderly_man"):
    global current_key_index

    lang = detect_language(new_message)

    if state == "EXTRACTION":
        if "upi" in new_message.lower():
            return "I can check the UPI details, but tell me why you need them first.", conversation_history
        return "What exact detail do you need from me? I will try to find it.", conversation_history

    rule_reply = get_rule_based_response(new_message, lang)
    final_reply = rule_reply

    try:
        from agentic.local_model import LOCAL_MODEL_AVAILABLE, get_local_response

        if LOCAL_MODEL_AVAILABLE and random.random() < 0.3:
            model_reply = get_local_response(new_message)
            if model_reply and len(model_reply) > 8:
                final_reply = model_reply
    except Exception:
        final_reply = rule_reply

    gemini_reply = None
    if types is not None and API_KEYS:
        conversation_history.append(types.Content(role="user", parts=[types.Part(text=new_message)]))
        for _ in range(len(API_KEYS)):
            try:
                client = get_client()
                if client is None:
                    break
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=build_system_prompt(lang, persona),
                        max_output_tokens=80,
                        temperature=1.0,
                    ),
                    contents=conversation_history,
                )
                gemini_reply = response.text.strip()
                if gemini_reply:
                    final_reply = gemini_reply
                break
            except Exception as exc:
                if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                    current_key_index = (current_key_index + 1) % len(API_KEYS)
                    time.sleep(1)
                    continue
                break
    elif types is not None:
        conversation_history.append(types.Content(role="user", parts=[types.Part(text=new_message)]))

    if types is not None:
        conversation_history.append(types.Content(role="model", parts=[types.Part(text=final_reply)]))

    return final_reply, conversation_history


if __name__ == "__main__":
    print("Hermes Honeypot Agent activated. Ctrl+C to stop.\n")
    history = []
    while True:
        message = input("Scammer: ")
        reply, history = get_honeypot_response(history, message)
        print(f"Hermes: {reply}\n")
