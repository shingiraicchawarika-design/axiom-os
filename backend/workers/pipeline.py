"""
Axiom OS — Full Pipeline Orchestrator
Runs: Scrape → Score → Enrich → Urgency → Outreach → CRM Health
Hybrid mode: auto for scraping/scoring, approval gate for outreach
"""
import asyncio
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from agents.agents import (
    LeadScraperAgent, LeadIntelligenceAgent, LeadEnrichmentAgent,
    UrgencyDetectionAgent, OutreachAgent, NurtureAgent,
    BookingAgent, CRMManagerAgent, ReferralRelationshipAgent, CEOAgent
)
from scrapers.scraper import ScraperOrchestrator
from models.schemas import (
    ScraperJobConfig, Lead, LeadStage, UrgencyLevel, PipelineStatus
)
from core.config import COMPANY_LOCATIONS, SERVICE_KEYWORDS, get_redis


class PipelineOrchestrator:
    def __init__(self):
        self.scraper_orchestrator = ScraperOrchestrator()
        self.scraper_agent = LeadScraperAgent()
        self.intelligence_agent = LeadIntelligenceAgent()
        self.enrichment_agent = LeadEnrichmentAgent()
        self.urgency_agent = UrgencyDetectionAgent()
        self.outreach_agent = OutreachAgent()
        self.nurture_agent = NurtureAgent()
        self.booking_agent = BookingAgent()
        self.crm_agent = CRMManagerAgent()
        self.referral_agent = ReferralRelationshipAgent()
        self.ceo_agent = CEOAgent()

    def _update_status(self, run_id: str, update: Dict[str, Any]):
        """Push status update to Redis for real-time frontend streaming"""
        try:
            r = get_redis()
            key = f"pipeline_run:{run_id}"
            existing = r.get(key)
            status = json.loads(existing) if existing else {}
            status.update(update)
            status["updated_at"] = datetime.now().isoformat()
            r.setex(key, 3600, json.dumps(status))  # 1 hour TTL
        except Exception as e:
            print(f"[Pipeline] Redis update failed: {e}")

    def _log_event(self, run_id: str, agent: str, event: str, data: Any = None):
        try:
            r = get_redis()
            log_key = f"pipeline_log:{run_id}"
            logs = json.loads(r.get(log_key) or "[]")
            logs.append({
                "ts": datetime.now().isoformat(),
                "agent": agent,
                "event": event,
                "data": data,
            })
            r.setex(log_key, 3600, json.dumps(logs))
        except Exception as e:
            print(f"[Pipeline] Log failed: {e}")

    async def run_full_pipeline(
        self,
        run_id: str,
        config: ScraperJobConfig,
        existing_leads: List[Lead] = None
    ) -> Dict[str, Any]:
        """
        Full pipeline run:
        1. Lead Scraper Agent → configures scraper
        2. Real Playwright scraper → raw leads
        3. Lead Intelligence Agent → scores each lead
        4. Lead Enrichment Agent → enriches qualifying leads
        5. Urgency Detection Agent → flags escalations
        6. Outreach Agent → drafts outreach (approval gate)
        7. Nurture Agent → plans follow-up sequences
        8. Booking Agent → checks conversion-ready leads
        9. CRM Manager → health check
        10. CEO Agent → strategic briefing
        """
        existing_leads = existing_leads or []
        results = {
            "run_id": run_id,
            "status": "running",
            "raw_leads": [],
            "scored_leads": [],
            "enriched_leads": [],
            "escalations": [],
            "outreach_drafts": [],
            "nurture_plans": [],
            "booking_actions": [],
            "crm_health": {},
            "ceo_briefing": {},
            "logs": [],
        }

        self._update_status(run_id, {"status": "running", "stage": "scraper_config"})

        # ── Stage 1: Scraper Agent configures run ─────────────────────────────
        print(f"[Pipeline:{run_id}] Stage 1: Configuring scraper...")
        self._log_event(run_id, "lead_scraper", "Configuring scraper run")
        scraper_config = self.scraper_agent.configure_run(
            locations=config.locations or COMPANY_LOCATIONS,
            keywords=config.keywords or SERVICE_KEYWORDS
        )
        self._log_event(run_id, "lead_scraper", f"Config ready: {len(scraper_config.get('queries', []))} queries")

        # ── Stage 2: Real scraping ────────────────────────────────────────────
        print(f"[Pipeline:{run_id}] Stage 2: Scraping {len(config.sources)} sources...")
        self._update_status(run_id, {"stage": "scraping", "agents_running": ["lead_scraper"]})

        try:
            raw_leads = await self.scraper_orchestrator.run(
                sources=[s.value if hasattr(s, 'value') else str(s) for s in config.sources],
                keywords=config.keywords or SERVICE_KEYWORDS,
                locations=config.locations or COMPANY_LOCATIONS,
                max_results=config.max_results,
            )
        except Exception as e:
            print(f"[Pipeline:{run_id}] Scraping failed: {e}")
            raw_leads = []

        results["raw_leads"] = [r.model_dump() for r in raw_leads]
        self._log_event(run_id, "lead_scraper", f"Scraped {len(raw_leads)} raw leads")
        self._update_status(run_id, {"leads_found": len(raw_leads), "agents_completed": ["lead_scraper"]})

        # ── Stage 3: Intelligence — score all leads ───────────────────────────
        print(f"[Pipeline:{run_id}] Stage 3: Scoring {len(raw_leads)} leads...")
        self._update_status(run_id, {"stage": "scoring", "agents_running": ["lead_intelligence"]})

        scored_leads = []
        for raw in raw_leads:
            try:
                scored = self.intelligence_agent.score_lead(raw)
                scored_leads.append(scored)
                await asyncio.sleep(0.5)  # Rate limit Claude
            except Exception as e:
                print(f"[Intelligence] Score failed: {e}")

        qualifying = [s for s in scored_leads if s.is_qualifying]
        results["scored_leads"] = [{"score": s.lead_score, "urgency": s.urgency, "qualifying": s.is_qualifying} for s in scored_leads]
        self._log_event(run_id, "lead_intelligence", f"Scored {len(scored_leads)} leads, {len(qualifying)} qualifying")
        self._update_status(run_id, {"leads_qualified": len(qualifying), "agents_completed": ["lead_scraper", "lead_intelligence"]})

        # ── Stage 4: Enrichment ───────────────────────────────────────────────
        print(f"[Pipeline:{run_id}] Stage 4: Enriching {len(qualifying)} qualifying leads...")
        self._update_status(run_id, {"stage": "enrichment", "agents_running": ["lead_enrichment"]})

        enriched_leads = []
        for scored in qualifying[:20]:  # Cap at 20 to avoid excessive API calls
            try:
                lead = self.enrichment_agent.enrich(scored)
                enriched_leads.append(lead)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[Enrichment] Failed: {e}")

        results["enriched_leads"] = [l.model_dump() for l in enriched_leads]
        self._log_event(run_id, "lead_enrichment", f"Enriched {len(enriched_leads)} leads")

        # ── Stage 5: Urgency Detection ────────────────────────────────────────
        print(f"[Pipeline:{run_id}] Stage 5: Urgency scan...")
        self._update_status(run_id, {"stage": "urgency", "agents_running": ["urgency_detection"]})

        all_leads = existing_leads + enriched_leads
        escalations = self.urgency_agent.scan_leads(all_leads)
        urgency_summary = self.urgency_agent.assess_pipeline_urgency(all_leads)
        results["escalations"] = escalations
        self._log_event(run_id, "urgency_detection", f"{len(escalations)} escalations, risk: {urgency_summary.get('pipeline_risk')}")

        # ── Stage 6: Outreach Drafts (AUTO — approval gate in UI) ─────────────
        print(f"[Pipeline:{run_id}] Stage 6: Drafting outreach...")
        self._update_status(run_id, {"stage": "outreach", "agents_running": ["outreach"]})

        outreach_drafts = []
        high_priority = [l for l in enriched_leads if l.lead_score >= 65]
        for lead in high_priority[:8]:
            try:
                draft = self.outreach_agent.draft_outreach(lead)
                outreach_drafts.append(draft)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[Outreach] Draft failed: {e}")

        results["outreach_drafts"] = [d.model_dump() for d in outreach_drafts]
        self._log_event(run_id, "outreach", f"Drafted {len(outreach_drafts)} outreach messages awaiting approval")
        self._update_status(run_id, {"outreach_drafted": len(outreach_drafts)})

        # ── Stage 7: Nurture Plans ────────────────────────────────────────────
        print(f"[Pipeline:{run_id}] Stage 7: Planning nurture sequences...")
        stale_leads = [l for l in existing_leads
                       if l.stage in [LeadStage.CONTACTED, LeadStage.ENGAGED]
                       and l.updated_at and (datetime.now() - l.updated_at).days > 3]

        nurture_plans = []
        for lead in stale_leads[:5]:
            try:
                plan = self.nurture_agent.plan_nurture_sequence(lead)
                nurture_plans.append({"lead_id": lead.id, "lead_name": lead.name, "plan": plan})
            except Exception as e:
                print(f"[Nurture] Plan failed: {e}")

        results["nurture_plans"] = nurture_plans
        self._log_event(run_id, "nurture", f"Planned {len(nurture_plans)} nurture sequences")

        # ── Stage 8: Booking Checks ───────────────────────────────────────────
        print(f"[Pipeline:{run_id}] Stage 8: Booking agent...")
        booking_actions = self.booking_agent.check_conversions(all_leads)
        results["booking_actions"] = booking_actions
        self._log_event(run_id, "booking", f"{len(booking_actions)} leads ready to book")

        # ── Stage 9: CRM Health ───────────────────────────────────────────────
        print(f"[Pipeline:{run_id}] Stage 9: CRM health check...")
        crm_health = self.crm_agent.health_check(all_leads)
        results["crm_health"] = crm_health
        self._log_event(run_id, "crm_manager", f"CRM health score: {crm_health.get('health_score')}/100")

        # ── Stage 10: CEO Briefing ────────────────────────────────────────────
        print(f"[Pipeline:{run_id}] Stage 10: CEO briefing...")
        try:
            ceo_briefing = self.ceo_agent.run({
                "total_leads": len(all_leads),
                "new_leads_today": len(enriched_leads),
                "qualifying_rate": f"{len(qualifying)}/{len(raw_leads)}",
                "high_urgency": len(escalations),
                "outreach_pending_approval": len(outreach_drafts),
                "pipeline_health": crm_health.get("health_score"),
                "pipeline_value": crm_health.get("pipeline_value"),
                "booking_ready": len(booking_actions),
            })
        except Exception as e:
            ceo_briefing = {"briefing": "CEO briefing unavailable", "priorities": []}

        results["ceo_briefing"] = ceo_briefing
        self._log_event(run_id, "ceo", "Strategic briefing generated")

        # ── Complete ──────────────────────────────────────────────────────────
        results["status"] = "completed"
        results["completed_at"] = datetime.now().isoformat()
        self._update_status(run_id, {
            "status": "completed",
            "stage": "done",
            "agents_completed": ["lead_scraper", "lead_intelligence", "lead_enrichment",
                                  "urgency_detection", "outreach", "nurture",
                                  "booking", "crm_manager", "ceo"],
        })

        print(f"[Pipeline:{run_id}] ✓ Complete — {len(enriched_leads)} new leads, {len(outreach_drafts)} drafts pending approval")
        return results
