"""
Axiom OS — 10 AI Agents
Each agent has a defined role, inputs, outputs, and Claude-powered logic.
"""
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from core.config import get_anthropic, LAMORA_SYSTEM_PROMPT, COMPANY_LOCATIONS, URGENCY_SIGNALS
from models.schemas import (
    RawLead, ScoredLead, Lead, LeadStage, UrgencyLevel,
    OutreachDraft, AgentLog
)


def _claude(system: str, prompt: str, max_tokens: int = 1000, json_mode: bool = False) -> str:
    client = get_anthropic()
    if json_mode:
        system += "\n\nRespond ONLY with valid JSON. No markdown, no preamble, no explanation."
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


def _timed_run(fn, *args, **kwargs):
    start = time.time()
    result = fn(*args, **kwargs)
    ms = int((time.time() - start) * 1000)
    return result, ms


# ── 1. CEO Agent ──────────────────────────────────────────────────────────────
class CEOAgent:
    """Strategic controller — reads all agent outputs, sets daily priorities"""
    name = "ceo"

    def run(self, pipeline_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
Current pipeline snapshot for Lamora Healthcare Ltd:
{json.dumps(pipeline_snapshot, indent=2, default=str)}

Generate a strategic briefing covering:
1. Top 3 priority actions today
2. Pipeline health assessment
3. Agent coordination instructions
4. Revenue/growth outlook this week

Be direct, specific, and actionable. UK English.
Respond as JSON: {{
  "briefing": "...",
  "priorities": ["...", "...", "..."],
  "agent_instructions": {{"agent_name": "instruction"}},
  "pipeline_health": "good|moderate|poor",
  "revenue_forecast": "..."
}}
"""
        result = _claude(LAMORA_SYSTEM_PROMPT + "\nYou are the CEO Agent.", prompt, json_mode=True)
        try:
            return json.loads(result)
        except:
            return {"briefing": result, "priorities": [], "agent_instructions": {}}


# ── 2. Lead Scraper Agent ─────────────────────────────────────────────────────
class LeadScraperAgent:
    """Configures and triggers the scraper, processes raw results"""
    name = "lead_scraper"

    def configure_run(self, locations: List[str], keywords: List[str]) -> Dict[str, Any]:
        prompt = f"""
Configure an optimal scraper run for finding private care clients and referral partners.
Locations: {', '.join(locations)}
Available keywords: {', '.join(keywords[:10])}

Select the best:
- Search queries (up to 8 specific intent phrases for the UK care market)
- Source priorities
- Urgency keywords to monitor

Respond as JSON: {{
  "queries": [...],
  "priority_sources": [...],
  "urgency_keywords": [...],
  "estimated_leads": number
}}
"""
        result = _claude(LAMORA_SYSTEM_PROMPT + "\nYou are the Lead Scraper Agent.", prompt, json_mode=True)
        try:
            return json.loads(result)
        except:
            return {"queries": keywords, "priority_sources": ["google", "forums"], "urgency_keywords": URGENCY_SIGNALS}


# ── 3. Lead Intelligence Agent ────────────────────────────────────────────────
class LeadIntelligenceAgent:
    """Scores and qualifies raw leads using NLP intent detection"""
    name = "lead_intelligence"

    def score_lead(self, raw: RawLead) -> ScoredLead:
        prompt = f"""
Analyse this raw lead for Lamora Healthcare Ltd and score it.

Source: {raw.source}
Title: {raw.title or 'N/A'}
Snippet: {raw.snippet}
Location: {raw.location or 'Unknown'}

Score 0-100 and classify:
- lead_score: integer 0-100
- urgency: "high"|"medium"|"low"
- service_needed: specific service type
- buyer_type: "daughter-looking-for-care"|"son-looking-for-care"|"spouse-looking-for-care"|"self-funding-family"|"deputy-or-poa"|"social-worker-enquirer"|"case-manager-enquirer"|"partnership"
- situation_tags: list of relevant tags
- intent_tags: list of intent signals
- ai_analysis: 2-sentence analysis
- is_qualifying: true if score >= 50 and has genuine care intent

Respond as JSON with these exact keys.
"""
        result = _claude(
            LAMORA_SYSTEM_PROMPT + "\nYou are the Lead Intelligence Agent. Be strict — only qualify genuine care leads.",
            prompt, json_mode=True
        )
        try:
            data = json.loads(result)
            return ScoredLead(
                raw=raw,
                lead_score=int(data.get("lead_score", 30)),
                urgency=UrgencyLevel(data.get("urgency", "medium")),
                service_needed=data.get("service_needed"),
                buyer_type=data.get("buyer_type"),
                situation_tags=data.get("situation_tags", []),
                intent_tags=data.get("intent_tags", []),
                ai_analysis=data.get("ai_analysis", ""),
                is_qualifying=data.get("is_qualifying", False),
            )
        except Exception as e:
            return ScoredLead(
                raw=raw,
                lead_score=20,
                urgency=UrgencyLevel.LOW,
                is_qualifying=False,
                ai_analysis=f"Scoring failed: {e}"
            )

    def batch_score(self, raw_leads: List[RawLead]) -> List[ScoredLead]:
        return [self.score_lead(lead) for lead in raw_leads]


# ── 4. Lead Enrichment Agent ──────────────────────────────────────────────────
class LeadEnrichmentAgent:
    """Enriches qualifying leads with additional context"""
    name = "lead_enrichment"

    def enrich(self, scored: ScoredLead) -> Lead:
        prompt = f"""
Enrich this qualifying care lead and prepare it for CRM entry.

Snippet: {scored.raw.snippet}
Title: {scored.raw.title or 'N/A'}
Source: {scored.raw.source}
Location: {scored.raw.location or 'Unknown'}
Service needed: {scored.service_needed or 'Unknown'}
Buyer type: {scored.buyer_type or 'Unknown'}
AI analysis: {scored.ai_analysis}

Determine:
- name: best name to use (person name or organisation name)
- organisation: if B2B
- service_category: which category (Core Home Care|Live-In & 24hr|Specialist Support|Independence & Wellbeing)
- pipeline_value: estimated monthly value in GBP (realistic for UK domiciliary care)
- tags: relevant CRM tags
- notes: brief context note for care coordinator

Respond as JSON with these keys.
"""
        result = _claude(LAMORA_SYSTEM_PROMPT + "\nYou are the Lead Enrichment Agent.", prompt, json_mode=True)
        try:
            data = json.loads(result)
            return Lead(
                name=data.get("name", scored.raw.title or "Unknown"),
                organisation=data.get("organisation"),
                service_type=scored.service_needed,
                service_category=data.get("service_category"),
                stage=LeadStage.NEW,
                urgency=scored.urgency,
                lead_score=scored.lead_score,
                source=scored.raw.source.value if hasattr(scored.raw.source, 'value') else str(scored.raw.source),
                source_url=scored.raw.source_url,
                location=scored.raw.location,
                buyer_type=scored.buyer_type,
                snippet=scored.raw.snippet[:500],
                notes=data.get("notes", ""),
                tags=data.get("tags", []) + scored.situation_tags,
                pipeline_value=float(data.get("pipeline_value", 1500)),
                ai_analysis=scored.ai_analysis,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        except Exception as e:
            return Lead(
                name=scored.raw.title or "Unknown Lead",
                snippet=scored.raw.snippet[:500],
                stage=LeadStage.NEW,
                urgency=scored.urgency,
                lead_score=scored.lead_score,
                source=str(scored.raw.source),
                location=scored.raw.location,
                ai_analysis=scored.ai_analysis,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )


# ── 5. Urgency Detection Agent ────────────────────────────────────────────────
class UrgencyDetectionAgent:
    """Monitors leads for urgency escalation signals"""
    name = "urgency_detection"

    def scan_leads(self, leads: List[Lead]) -> List[Dict[str, Any]]:
        escalations = []
        for lead in leads:
            snippet = (lead.snippet or "").lower()
            notes = (lead.notes or "").lower()
            text = snippet + " " + notes

            urgency_count = sum(1 for signal in URGENCY_SIGNALS if signal in text)
            if urgency_count >= 2 and lead.urgency != UrgencyLevel.HIGH:
                escalations.append({
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "reason": f"Detected {urgency_count} urgency signals",
                    "signals": [s for s in URGENCY_SIGNALS if s in text],
                    "recommended_action": "Immediate outreach within 2 hours"
                })
        return escalations

    def assess_pipeline_urgency(self, leads: List[Lead]) -> Dict[str, Any]:
        high_urgency = [l for l in leads if l.urgency == UrgencyLevel.HIGH]
        stale = [l for l in leads if l.updated_at and
                 (datetime.now() - l.updated_at).days > 3 and
                 l.stage not in [LeadStage.CONVERTED]]
        return {
            "high_urgency_count": len(high_urgency),
            "stale_leads": len(stale),
            "immediate_action_required": len(high_urgency) > 0,
            "pipeline_risk": "high" if len(stale) > 3 else "moderate" if len(stale) > 0 else "low"
        }


# ── 6. Outreach Agent ─────────────────────────────────────────────────────────
class OutreachAgent:
    """Drafts GDPR-compliant outreach for approved leads — requires human approval"""
    name = "outreach"

    def draft_outreach(self, lead: Lead) -> OutreachDraft:
        channel = "email" if lead.email else "call_brief"
        prompt = f"""
Draft a professional outreach message for this care lead.

Lead details:
- Name: {lead.name}
- Organisation: {lead.organisation or 'Private individual'}
- Service needed: {lead.service_type or 'Home care'}
- Location: {lead.location or 'Unknown'}
- Buyer type: {lead.buyer_type or 'Unknown'}
- Snippet: {lead.snippet or 'N/A'}
- Urgency: {lead.urgency}
- AI analysis: {lead.ai_analysis or 'N/A'}

Channel: {channel}

Requirements:
- Warm, supportive, professional tone
- Not salesy or pushy  
- Reference the specific situation if evident from snippet
- Mention nurse-led, CQC-registered, Lamora Healthcare
- UK English
- GDPR compliant — mention how we found them

Respond as JSON: {{
  "subject": "...",
  "body": "...",
  "talking_points": ["...", "...", "..."],
  "recommended_time": "...",
  "gdpr_basis": "legitimate interests|public source"
}}
"""
        result = _claude(
            LAMORA_SYSTEM_PROMPT + "\nYou are the Outreach Agent. Draft compliant, warm, effective outreach.",
            prompt, json_mode=True
        )
        try:
            data = json.loads(result)
            return OutreachDraft(
                lead_id=lead.id,
                to_email=lead.email or "",
                to_name=lead.name,
                subject=data.get("subject", f"Home care support for {lead.name}"),
                body=data.get("body", ""),
                talking_points=data.get("talking_points", []),
                channel=channel,
                status="draft",
                generated_by="outreach_agent",
                created_at=datetime.now(),
            )
        except Exception as e:
            return OutreachDraft(
                lead_id=lead.id,
                to_email=lead.email or "",
                to_name=lead.name,
                subject=f"Care support — Lamora Healthcare",
                body="Draft generation failed. Please write manually.",
                status="draft",
                created_at=datetime.now(),
            )

    def batch_draft(self, leads: List[Lead]) -> List[OutreachDraft]:
        qualifying = [l for l in leads if l.lead_score >= 60 and not l.outreach_drafted]
        return [self.draft_outreach(lead) for lead in qualifying[:10]]


# ── 7. Nurture Agent ──────────────────────────────────────────────────────────
class NurtureAgent:
    """Manages follow-up sequences for non-responsive leads"""
    name = "nurture"

    def plan_nurture_sequence(self, lead: Lead) -> Dict[str, Any]:
        days_since_contact = 0
        if lead.updated_at:
            days_since_contact = (datetime.now() - lead.updated_at).days

        prompt = f"""
Plan a nurture sequence for this care lead that hasn't responded.

Lead: {lead.name}
Stage: {lead.stage}
Days since last contact: {days_since_contact}
Service needed: {lead.service_type or 'Unknown'}
Urgency: {lead.urgency}

Design a 3-touch nurture sequence. For each touch:
- timing: when to send
- channel: email|phone|linkedin
- message_brief: 1-sentence description
- objective: what we want to achieve

Respond as JSON: {{
  "sequence": [
    {{"touch": 1, "timing": "...", "channel": "...", "message_brief": "...", "objective": "..."}},
    ...
  ],
  "escalate_if_no_response": "...",
  "disqualify_after": "..."
}}
"""
        result = _claude(LAMORA_SYSTEM_PROMPT + "\nYou are the Nurture Agent.", prompt, json_mode=True)
        try:
            return json.loads(result)
        except:
            return {
                "sequence": [
                    {"touch": 1, "timing": "Day 3", "channel": "email", "message_brief": "Gentle follow-up", "objective": "Re-engage"},
                    {"touch": 2, "timing": "Day 7", "channel": "phone", "message_brief": "Check-in call", "objective": "Qualify"},
                    {"touch": 3, "timing": "Day 14", "channel": "email", "message_brief": "Final touch", "objective": "Last chance"},
                ],
                "disqualify_after": "21 days no response"
            }


# ── 8. Booking Agent ──────────────────────────────────────────────────────────
class BookingAgent:
    """Converts engaged leads into assessment bookings"""
    name = "booking"

    def generate_booking_message(self, lead: Lead) -> Dict[str, Any]:
        prompt = f"""
Generate an assessment booking message for this engaged care lead.

Lead: {lead.name}
Service: {lead.service_type or 'Home care assessment'}
Location: {lead.location or 'To be confirmed'}
Urgency: {lead.urgency}

Create:
- booking_message: warm message inviting them to book a free home assessment
- booking_link_placeholder: "[CALENDLY_LINK]"
- confirmation_checklist: what coordinator needs to prepare
- assessment_brief: 3 key things to assess

Respond as JSON.
"""
        result = _claude(LAMORA_SYSTEM_PROMPT + "\nYou are the Booking Agent.", prompt, json_mode=True)
        try:
            return json.loads(result)
        except:
            return {
                "booking_message": f"Thank you for your interest. We'd love to arrange a free home assessment for {lead.name}. Please use the link below to choose a convenient time.",
                "booking_link_placeholder": "[CALENDLY_LINK]",
                "confirmation_checklist": ["Confirm address", "Check care needs", "Assign assessor"],
            }

    def check_conversions(self, leads: List[Lead]) -> List[Dict[str, Any]]:
        ready_to_book = [
            l for l in leads
            if l.stage == LeadStage.ENGAGED and l.lead_score >= 70
        ]
        return [{"lead_id": l.id, "lead_name": l.name, "action": "Send booking link"} for l in ready_to_book]


# ── 9. CRM Manager Agent ─────────────────────────────────────────────────────
class CRMManagerAgent:
    """Monitors CRM health, flags stale leads, generates pipeline reports"""
    name = "crm_manager"

    def health_check(self, leads: List[Lead]) -> Dict[str, Any]:
        total = len(leads)
        if total == 0:
            return {"health_score": 0, "issues": ["No leads in pipeline"]}

        converted = sum(1 for l in leads if l.stage == LeadStage.CONVERTED)
        stale = sum(1 for l in leads if l.updated_at and (datetime.now() - l.updated_at).days > 5)
        high_value = sum(1 for l in leads if l.pipeline_value >= 3000)
        no_contact = sum(1 for l in leads if not l.email and not l.phone)

        conversion_rate = (converted / total) * 100 if total > 0 else 0
        pipeline_value = sum(l.pipeline_value for l in leads)
        avg_score = sum(l.lead_score for l in leads) / total if total > 0 else 0

        issues = []
        if stale > 2: issues.append(f"{stale} stale leads (no activity > 5 days)")
        if no_contact > 3: issues.append(f"{no_contact} leads with no contact details")
        if conversion_rate < 10: issues.append("Conversion rate below 10%")

        health_score = max(0, 100 - (stale * 10) - (no_contact * 5) - (20 if conversion_rate < 10 else 0))

        return {
            "health_score": health_score,
            "total_leads": total,
            "converted": converted,
            "conversion_rate": round(conversion_rate, 1),
            "pipeline_value": pipeline_value,
            "avg_lead_score": round(avg_score, 1),
            "stale_leads": stale,
            "issues": issues,
            "recommendations": self._generate_recommendations(leads, issues)
        }

    def _generate_recommendations(self, leads: List[Lead], issues: List[str]) -> List[str]:
        recs = []
        high_score_new = [l for l in leads if l.lead_score >= 75 and l.stage == LeadStage.NEW]
        if high_score_new:
            recs.append(f"Move {len(high_score_new)} high-scoring leads from New to Contacted")
        engaged = [l for l in leads if l.stage == LeadStage.ENGAGED]
        if engaged:
            recs.append(f"Send booking links to {len(engaged)} engaged leads")
        return recs


# ── 10. Referral Relationship Agent ──────────────────────────────────────────
class ReferralRelationshipAgent:
    """Manages commissioner and partner relationships"""
    name = "referral_agent"

    def generate_recommendation(self, relationship: Dict[str, Any]) -> Dict[str, Any]:
        days_since_ref = relationship.get("days_since_referral", 30)
        days_since_contact = relationship.get("days_since_contact", 14)

        prompt = f"""
Generate a relationship outreach recommendation for this commissioner/partner.

Relationship data:
{json.dumps(relationship, indent=2, default=str)}

Days since last referral: {days_since_ref}
Days since last contact: {days_since_contact}

Generate:
- subject: email subject or "Call Brief"
- message: professional outreach draft (3-4 paragraphs, UK English)
- talking_points: 3 specific points for a call
- risk: one-sentence risk if no action taken
- next_step: single recommended next action

Respond as JSON.
"""
        result = _claude(
            LAMORA_SYSTEM_PROMPT + "\nYou are the Referral Relationship Agent managing commissioner relationships.",
            prompt, json_mode=True
        )
        try:
            return json.loads(result)
        except:
            return {
                "subject": f"Touching base — Lamora Healthcare",
                "message": "Draft unavailable. Please generate manually.",
                "talking_points": [],
                "risk": "Relationship may go cold without contact.",
                "next_step": "Schedule call"
            }

    def score_relationship_health(self, relationship: Dict[str, Any]) -> int:
        score = 50
        refs_90 = relationship.get("referrals_90_days", 0)
        days_since_ref = relationship.get("days_since_referral", 99)
        days_since_contact = relationship.get("days_since_contact", 99)

        score += min(30, refs_90 * 8)
        if days_since_ref < 30: score += 15
        elif days_since_ref > 90: score -= 20
        if days_since_contact < 14: score += 10
        elif days_since_contact > 60: score -= 15
        if relationship.get("contract_active"): score += 10

        return max(0, min(100, score))


# ── Agent Registry ────────────────────────────────────────────────────────────
AGENT_REGISTRY = {
    "ceo": CEOAgent(),
    "lead_scraper": LeadScraperAgent(),
    "lead_intelligence": LeadIntelligenceAgent(),
    "lead_enrichment": LeadEnrichmentAgent(),
    "urgency_detection": UrgencyDetectionAgent(),
    "outreach": OutreachAgent(),
    "nurture": NurtureAgent(),
    "booking": BookingAgent(),
    "crm_manager": CRMManagerAgent(),
    "referral_agent": ReferralRelationshipAgent(),
}
