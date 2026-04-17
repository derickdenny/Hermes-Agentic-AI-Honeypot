from google import genai
from google.genai import types
import os, time, re, random
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

# ── Load all API keys ────────────────────────────────────────────────────────
API_KEYS = [
    os.getenv("AIzaSyCnuqDIcHu62jDire5ex9nwCh_U7QUYMZA"),
    os.getenv("AIzaSyCNLa4A_vOOaYbD5XF1B0Lm3vSUksUSma8"),
    os.getenv("AIzaSyCvn-mYYmt407f6e5dd_BHRRMSxiN0atZQ"),
]
API_KEYS = [k for k in API_KEYS if k]
current_key_index = 0

def get_client():
    return genai.Client(api_key=API_KEYS[current_key_index])

# ── Language Detection ────────────────────────────────────────────────────────
HINDI_CHARS = re.compile(r'[\u0900-\u097F]')
HINDI_WORDS = ["kya","hai","karo","bata","mera","tera","aap","tum",
               "nahi","haan","paisa","rupaye","abhi","bhejo","batao",
               "account","number","jaldi","band","block"]

def detect_language(text: str) -> str:
    if HINDI_CHARS.search(text):
        return "hindi"
    hits = sum(1 for w in HINDI_WORDS if w in text.lower().split())
    return "hindi" if hits >= 2 else "english"

# ── Smart Rule-Based Response Engine ─────────────────────────────────────────
# Maps scammer intent → multiple varied Hermes responses
RESPONSE_MAP_EN = {
    "otp": [
        "OTP? Yes yes, but which app should I open beta? There are so many on my phone.",
        "Haan, the OTP came but it disappeared. Let me check again... my screen is very small.",
        "Beta I see some numbers but my spectacles are not with me. Can you wait one minute?",
        "OTP? My son Suresh told me never share this with anyone. Are you sure it is safe?",
        "I clicked on the message but now it is gone. Shall I restart the phone?",
    ],
    "upi": [
        "UPI? Which app beta — PhonePe, GPay or Paytm? I have all three but always get confused.",
        "I opened the app but it is asking for fingerprint and my finger is not working properly.",
        "Haan I know UPI. My grandson set it up. But I forgot the PIN, should I reset it?",
        "Wait wait, the app is loading. My internet is very slow today, BSNL connection.",
        "I can see the UPI screen but which option to press? There are too many buttons.",
    ],
    "link": [
        "I clicked the link but it is showing some error. Should I click again?",
        "The link opened but now my phone is very hot. Is that normal beta?",
        "Which browser should I use? I have Chrome and also another one, the blue one.",
        "Link opened but it is asking me to download something. Should I do it?",
        "The page is loading very slowly. BSNL is giving problem today.",
    ],
    "account": [
        "Account number? Let me find my passbook... where did I keep it. One minute.",
        "I have two accounts beta, one SBI and one post office. Which one do you need?",
        "The number is written very small in the passbook. Let me get my spectacles.",
        "Haan I will give you but first tell me — is this recorded call? Just asking.",
        "Account number I remember but let me double check from the card. Hold on.",
    ],
    "kyc": [
        "KYC? I did this last year only. Does it expire so fast beta?",
        "For KYC what documents are needed? I have Aadhaar but it is old photo.",
        "My wife did the KYC for me last time. She is not home right now, can I call back?",
        "Which branch should I come to? Shivajinagar is far for me, any closer option?",
        "Haan KYC I will do but my Aadhaar card I cannot find right now. It was here only.",
    ],
    "block": [
        "Block? Arre no no, please don't block. What should I do beta? Tell me slowly.",
        "My son will be very upset if account is blocked. Can you give me some more time?",
        "How many days do I have? I am an old man, these things take time for me.",
        "Please don't block. I am a senior citizen, I get pension in this account only.",
        "Blocked means I cannot withdraw money? My medicine money is also in there.",
    ],
    "urgent": [
        "I understand it is urgent but my phone is not cooperating today beta.",
        "Yes yes I am doing it, but these apps are very complicated for old people.",
        "Urgent I know but I accidentally called my daughter. She is asking what happened.",
        "I am trying to be fast but my arthritis makes it hard to type quickly. Sorry.",
        "Haan urgent I understand. But first confirm — you are calling from the bank right?",
    ],
    "send_money": [
        "Send money? How much exactly? And to which account, let me note it down.",
        "I need to write this down. Wait, where is my pen... Seema! Where is the pen!",
        "How do I send? Through ATM or from the app? I am not sure which is safer.",
        "My phone is showing insufficient balance screen. Is that a problem?",
        "I will send but my son said always call back on official number first to verify.",
    ],
    "aadhaar": [
        "Aadhaar I have but the card is somewhere in the drawer. Give me two minutes.",
        "Should I give the number or scan the card? I don't know how to scan.",
        "My Aadhaar has old address, will that be a problem for the verification?",
        "I found the card but the number is faded. Let me try to read it... 4... wait.",
        "Aadhaar I can give but my son specifically told me not to share it on phone.",
    ],
}

RESPONSE_MAP_HI = {
    "otp": [
        "OTP aaya hai beta, lekin mujhe nahi pata kahan dekhun. Kaunsa app kholun?",
        "Haan message aaya, par numbers bahut chote hain. Mera chashma nahi mila.",
        "OTP share karna safe hai kya? Mere bete ne mana kiya tha iske liye.",
        "Maine click kiya toh message chala gaya. Phone restart karun kya?",
        "OTP dikha tha par ab screen lock ho gayi. Kaise kholun?",
    ],
    "upi": [
        "UPI mein konsa app? PhonePe ya GPay? Dono mein confused ho jaata hoon main.",
        "App khola toh fingerprint maang raha hai, meri ungli kaam nahi kar rahi.",
        "PIN bhool gaya hoon. Reset karna padega kya? Bahut time lagega.",
        "App load ho raha hai, internet slow hai aaj. BSNL ka chakkar hai.",
        "UPI screen dikhi, par konsa button dabana hai? Bahut saare options hain.",
    ],
    "block": [
        "Block mat karo beta please! Main kya karun abhi? Dheere dheere batao.",
        "Block hua toh pension kaise aayegi? Main senior citizen hoon.",
        "Mere bete ko pata chalega toh bahut pareshaan hoga. Thoda time do.",
        "Kitne din hain mere paas? Main budhha aadmi hoon, jaldi nahi ho paata.",
        "Please block mat karo, saari savings isi account mein hain meri.",
    ],
    "account": [
        "Account number dhundh raha hoon, passbook kahin rakh di. Ek minute.",
        "Do account hain mere, SBI aur post office. Kaunsa chahiye aapko?",
        "Number bahut chota likha hai passbook mein. Chashma leke aata hoon.",
        "Haan dunga, par pehle batao — ye recorded call toh nahi hai na?",
        "Card pe number hai lekin dhundh raha hoon card ko. Thoda wait karo.",
    ],
}

# Generic fallbacks when no intent matches
GENERIC_EN = [
    "Sorry beta, can you repeat that? There is some noise here.",
    "I did not understand properly. My hearing is not so good these days.",
    "Wait, my neighbour rang the bell. One moment please.",
    "Theek hai but can you explain once more? I am writing it down.",
    "Haan haan, I am listening. My phone battery is low also, doing charging.",
    "Can you speak a little slowly? I am an old man, things take time.",
    "Sorry I missed what you said. My grandson was talking to me.",
    "Which step are we on now? I got confused in between.",
]

GENERIC_HI = [
    "Beta zara dobara boliye, sunai nahi diya acha se.",
    "Samajh nahi aaya. Meri sunne ki aadat thodi kam ho gayi hai.",
    "Ruko, padosi ne bell bajaya. Ek minute.",
    "Theek hai, ek baar aur samjhao. Main likh raha hoon.",
    "Haan sun raha hoon, bas phone charge pe lagana tha, ho gaya.",
    "Thoda dheere boliye beta, budhhe hain hum, time lagta hai.",
    "Kya bola aapne? Pota baat kar raha tha mere se.",
    "Kaun sa step tha? Beech mein bhool gaya main.",
]

# Track last used responses to avoid repeats
used_responses: dict = {}

def get_rule_based_response(message: str, lang: str) -> str:
    msg_lower = message.lower()

    # Match intent
    intent_map = {
        "otp":        ["otp", "one time", "password", "code"],
        "upi":        ["upi", "phonpe", "gpay", "paytm", "transfer", "pay"],
        "link":       ["link", "click", "website", "url", "http", "open"],
        "account":    ["account", "number", "ac no", "acno"],
        "kyc":        ["kyc", "know your customer", "verification", "verify"],
        "block":      ["block", "suspend", "freeze", "closed", "band"],
        "urgent":     ["urgent", "immediately", "now", "fast", "quick", "jaldi"],
        "send_money": ["send", "transfer", "pay", "deposit", "bhejo"],
        "aadhaar":    ["aadhaar", "aadhar", "uid", "identity"],
    }

    matched_intent = None
    for intent, keywords in intent_map.items():
        if any(kw in msg_lower for kw in keywords):
            matched_intent = intent
            break

    # Pick response pool
    if lang == "hindi":
        pool = RESPONSE_MAP_HI.get(matched_intent, GENERIC_HI)
    else:
        pool = RESPONSE_MAP_EN.get(matched_intent, GENERIC_EN)

    # Avoid repeating — track used indices per intent key
    key = f"{lang}_{matched_intent or 'generic'}"
    if key not in used_responses:
        used_responses[key] = []

    available = [i for i in range(len(pool)) if i not in used_responses[key]]
    if not available:
        used_responses[key] = []  # Reset when all used
        available = list(range(len(pool)))

    chosen_idx = random.choice(available)
    used_responses[key].append(chosen_idx)
    return pool[chosen_idx]

# ── Gemini System Prompt ──────────────────────────────────────────────────────
def build_system_prompt(lang: str) -> str:
    lang_instruction = (
        "Reply ONLY in Hindi or Hinglish." if lang == "hindi"
        else "Reply ONLY in English."
    )
    return f"""You are Hermes, a 68-year-old confused retired government employee from Pune.
{lang_instruction}
Keep ALL replies under 2 sentences. Never repeat yourself.
Stall the scammer. Act confused about technology.
Fake details: Name: Hermes Kulkarni, Bank: SBI Shivajinagar,
UPI: hermes.kulkarni1956@sbi, Son: Suresh in Bangalore.
Never reveal you are an AI. Vary every response."""


# ── Main Response Function ────────────────────────────────────────────────────
def get_honeypot_response(conversation_history: list, new_message: str, state="SCAM"):
    global current_key_index
    lang = detect_language(new_message)

    # State-based behavior
    if state == "EXTRACTION":
        # Ask for more details
        if "upi" in new_message.lower():
            return "Haan UPI hai. But first tell me, is this safe? You are from bank na?", conversation_history
        
        return "What details do you need? I will try to find them. Wait.", conversation_history

    # ── PRIORITY 1: Rule-based (instant, always works) ────────────────────────
    rule_reply = get_rule_based_response(new_message, lang)

    # ── OPTIONAL: Enhance with local model sometimes ─────────────
    try:
        from agentic.local_model import get_local_response, LOCAL_MODEL_AVAILABLE

        if LOCAL_MODEL_AVAILABLE and random.random() < 0.3:
            model_reply = get_local_response(new_message)

            if model_reply and len(model_reply) > 8:
                final_reply = model_reply
            else:
                final_reply = rule_reply
        else:
            final_reply = rule_reply

    except:
        final_reply = rule_reply

    # ── PRIORITY 3: Gemini API (cloud backup) ─────────────────────────────────
    gemini_reply = None
    if API_KEYS:
        conversation_history.append(
            types.Content(role="user", parts=[types.Part(text=new_message)])
        )
        for attempt in range(len(API_KEYS)):
            try:
                client = get_client()
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=build_system_prompt(lang),
                        max_output_tokens=80,
                        temperature=1.0,
                    ),
                    contents=conversation_history
                )
                gemini_reply = response.text.strip()
                print(f"→ Gemini: {gemini_reply[:50]}")
                break
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    current_key_index = (current_key_index + 1) % len(API_KEYS)
                    time.sleep(2)
                else:
                    break

    # final_reply = gemini_reply if gemini_reply else rule_reply

    if not gemini_reply:
        conversation_history.append(
            types.Content(role="user", parts=[types.Part(text=new_message)])
        )
    conversation_history.append(
        types.Content(role="model", parts=[types.Part(text=final_reply)])
    )

    source = "Gemini" if gemini_reply else "Rule-based"
    print(f"→ {source}: {final_reply[:50]}")
    return final_reply, conversation_history


if __name__ == "__main__":
    print("Hermes Honeypot Agent activated. Ctrl+C to stop.\n")
    history = []
    while True:
        msg = input("Scammer: ")
        reply, history = get_honeypot_response(history, msg)
        print(f"Hermes: {reply}\n")