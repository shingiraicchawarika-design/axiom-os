from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class LeadStage(str, Enum):
    NEW = "New Lead"
    CONTACTED = "Contacted"
    ENGAGED = "Engaged"
    ASSESSMENT_BOOKED = "Assessment Booked"
    CARE_PACKAGE_DESIGNED = "Care Package Designed"
    CONVERTED = "Converted"


class UrgencyLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScraperSource(str, Enum):
    GOOGLE = "google"
    CARE_DIRECTORIES = "care_directories"
    FORUMS = "forums"
    BARK = "bark"
    LINKEDIN = "linkedin"
    NHS_LA = "nhs_la"
    FACEBOOK = "facebook"
    SOCIAL = "social"


class AgentName(str, Enum):
    CEO = "ceo"
    SCRAPER = "lead_scraper"
    INTELLIGENCE = "lead_intelligence"
    ENRICHMENT = "lead_enrichment"
    URGENCY = "urgency_detection"
    OUTREACH = "outreach"
    NURTURE = "nurture"
    BOOKING = "booking"
    CRM = "crm_manager"
    REFERRAL = "referral_agent"
    CONTENT_SEO = "content_seo"


# ── Lead models ───────────────────────────────────────────────────────────────
class RawLead(BaseModel):
    source: ScraperSource
    source_url: Optional[str] = None
    title: Optional[str] = None
    snippet: str
    location: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    scraped_at: datetime = datetime.now()
    raw_data: Dict[str, Any] = {}


class ScoredLead(BaseModel):
    raw: RawLead
    lead_score: int  # 0-100
    urgency: UrgencyLevel
    service_needed: Optional[str] = None
    buyer_type: Optional[str] = None
    situation_tags: List[str] = []
    intent_tags: List[str] = []
    ai_analysis: str = ""
    is_qualifying: bool = False  # passes threshold to enter CRM


class Lead(BaseModel):
    id: Optional[str] = None
    name: str
    organisation: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    service_type: Optional[str] = None
    service_category: Optional[str] = None
    stage: LeadStage = LeadStage.NEW
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    lead_score: int = 0
    source: Optional[str] = None
    source_url: Optional[str] = None
    location: Optional[str] = None
    buyer_type: Optional[str] = None
    snippet: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []
    pipeline_value: float = 0
    ai_analysis: Optional[str] = None
    outreach_drafted: bool = False
    outreach_approved: bool = False
    outreach_sent: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Scraper models ────────────────────────────────────────────────────────────
class ScraperJobConfig(BaseModel):
    sources: List[ScraperSource] = list(ScraperSource)
    keywords: List[str] = []
    locations: List[str] = []
    max_results: int = 30
    min_score_threshold: int = 50


class ScraperJob(BaseModel):
    id: Optional[str] = None
    config: ScraperJobConfig
    status: str = "pending"  # pending | running | completed | failed
    results_count: int = 0
    qualifying_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class ScraperResult(BaseModel):
    id: Optional[str] = None
    job_id: str
    source: str
    title: Optional[str] = None
    snippet: str
    url: Optional[str] = None
    service_needed: Optional[str] = None
    urgency: str = "medium"
    location: Optional[str] = None
    buyer_type: Optional[str] = None
    lead_score: int = 0
    ai_analysis: Optional[str] = None
    status: str = "pending"  # pending | approved | rejected | converted
    created_at: Optional[datetime] = None


# ── Agent models ──────────────────────────────────────────────────────────────
class AgentRunRequest(BaseModel):
    agent_name: AgentName
    context: Dict[str, Any] = {}
    force: bool = False


class AgentLog(BaseModel):
    id: Optional[str] = None
    agent_name: str
    status: str  # running | completed | failed
    input: Dict[str, Any] = {}
    output: Dict[str, Any] = {}
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Outreach models ───────────────────────────────────────────────────────────
class OutreachDraft(BaseModel):
    id: Optional[str] = None
    lead_id: Optional[str] = None
    relationship_id: Optional[str] = None
    to_email: str
    to_name: Optional[str] = None
    subject: str
    body: str
    channel: str = "email"  # email | call_brief
    talking_points: List[str] = []
    status: str = "draft"  # draft | approved | sent | opened | replied
    generated_by: str = "outreach_agent"
    approved_by: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class OutreachApproval(BaseModel):
    outreach_id: str
    approved: bool
    send_now: bool = False


# ── Pipeline run ──────────────────────────────────────────────────────────────
class PipelineRunRequest(BaseModel):
    agents: Optional[List[AgentName]] = None  # None = all
    scraper_config: Optional[ScraperJobConfig] = None


class PipelineStatus(BaseModel):
    run_id: str
    status: str
    agents_completed: List[str] = []
    agents_running: List[str] = []
    agents_queued: List[str] = []
    leads_found: int = 0
    leads_qualified: int = 0
    outreach_drafted: int = 0
    started_at: Optional[datetime] = None
