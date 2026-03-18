import os
from dotenv import load_dotenv
from supabase import create_client, Client
import redis
import anthropic

load_dotenv()

# ── Supabase ─────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

def get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

def get_anthropic() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── App config ────────────────────────────────────────────────────────────────
COMPANY_NAME = os.getenv("COMPANY_NAME", "Lamora Healthcare Ltd")
COMPANY_LOCATIONS = os.getenv(
    "COMPANY_LOCATIONS",
    "Aylesbury,Buckinghamshire,Bedfordshire,Luton,Milton Keynes,Northampton"
).split(",")

SCRAPING_CONCURRENCY = int(os.getenv("SCRAPING_CONCURRENCY", "3"))
SCRAPING_DELAY_MS = int(os.getenv("SCRAPING_DELAY_MS", "2000"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@lamorahealthcare.co.uk")
FROM_NAME = os.getenv("FROM_NAME", "Lamora Healthcare")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ── Lamora service catalogue ──────────────────────────────────────────────────
SERVICE_KEYWORDS = [
    "homecare", "home care", "domiciliary care", "live-in care",
    "overnight care", "respite care", "dementia care", "complex care",
    "care at home", "private carers", "elderly care", "waking night care",
    "mental health support at home", "post-discharge care", "palliative care",
    "autism support at home", "physical disability support",
]

INTENT_PHRASES = [
    "need home care for my mum",
    "live-in care for elderly parent",
    "urgent care at home after hospital",
    "dementia care near me",
    "respite care for elderly parent",
    "night care for elderly at home",
    "private carers near me",
    "looking for care for my dad",
    "mum discharged from hospital",
    "carer has let us down",
    "struggling to cope caring for parent",
    "need overnight carer",
    "care for elderly husband",
    "24 hour care at home",
    "complex care at home",
]

URGENCY_SIGNALS = [
    "urgent", "asap", "immediately", "this week", "discharged",
    "emergency", "struggling", "breakdown", "cannot cope", "help now",
    "falling", "unsafe", "crisis", "desperate", "today",
]

LAMORA_SYSTEM_PROMPT = f"""You are an AI agent in the Axiom OS system for {COMPANY_NAME}, 
a CQC-registered nurse-led domiciliary and complex care provider.
Operating areas: {', '.join(COMPANY_LOCATIONS)}.
Services: complex care, live-in care, dementia care, nurse-led oversight, 
CHC placements, supported living, mental health support at home, 
post-discharge care, palliative care, overnight care, respite care.
Always respond in professional British English."""
