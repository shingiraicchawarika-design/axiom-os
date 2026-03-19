"""
Axiom OS — FastAPI Backend
All routes for: leads, agents, scraper, pipeline, outreach, relationships
"""
import asyncio
import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.config import (
    get_supabase, get_redis, COMPANY_LOCATIONS, SERVICE_KEYWORDS,
    INTENT_PHRASES, LAMORA_SYSTEM_PROMPT
)
from models.schemas import (
    Lead, LeadStage, UrgencyLevel, ScraperJobConfig, ScraperSource,
    AgentRunRequest, AgentName, OutreachDraft, OutreachApproval,
    PipelineRunRequest
)
from agents.agents import AGENT_REGISTRY
from workers.pipeline import PipelineOrchestrator

app = FastAPI(
    title="Axiom OS API",
    description="Lamora Healthcare — AI-powered lead generation platform",
    version="2.0.0"
)

from fastapi import Request
from fastapi.responses import JSONResponse

@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response
)

# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "Axiom OS", "version": "2.0.0"}


# ── Pipeline ───────────────────────────────────────────────────────────────────
@app.post("/api/pipeline/run")
async def run_pipeline(request: PipelineRunRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())[:8]
    config = request.scraper_config or ScraperJobConfig(
        sources=list(ScraperSource),
        keywords=SERVICE_KEYWORDS[:8],
        locations=COMPANY_LOCATIONS[:4],
        max_results=25,
    )

    # Store initial status
    try:
        r = get_redis()
        r.setex(f"pipeline_run:{run_id}", 3600, json.dumps({
            "run_id": run_id,
            "status": "queued",
            "started_at": datetime.now().isoformat(),
        }))
    except Exception as e:
        print(f"Redis unavailable: {e}")

    # Run pipeline in background
    background_tasks.add_task(
        _run_pipeline_task, run_id, config
    )

    return {"run_id": run_id, "status": "started", "message": "Pipeline running in background"}


async def _run_pipeline_task(run_id: str, config: ScraperJobConfig):
    try:
        # Get existing leads from Supabase
        existing_leads = []
        try:
            sb = get_supabase()
            res = sb.table("leads").select("*").execute()
            existing_leads = [Lead(**row) for row in (res.data or [])]
        except Exception as e:
            print(f"Could not fetch existing leads: {e}")

        results = await pipeline.run_full_pipeline(run_id, config, existing_leads)

        # Save new leads to Supabase
        try:
            sb = get_supabase()
            for lead_data in results.get("enriched_leads", []):
                lead_data.pop("id", None)
                lead_data["created_at"] = datetime.now().isoformat()
                lead_data["updated_at"] = datetime.now().isoformat()
                sb.table("leads").insert(lead_data).execute()

            # Save outreach drafts
            for draft_data in results.get("outreach_drafts", []):
                draft_data.pop("id", None)
                draft_data["created_at"] = datetime.now().isoformat()
                sb.table("email_outreach").insert(draft_data).execute()

            # Log agent run
            sb.table("agent_logs").insert({
                "agent_name": "pipeline",
                "status": "completed",
                "output": {
                    "leads_found": len(results.get("raw_leads", [])),
                    "leads_qualified": len(results.get("enriched_leads", [])),
                    "outreach_drafted": len(results.get("outreach_drafts", [])),
                },
                "created_at": datetime.now().isoformat(),
            }).execute()
        except Exception as e:
            print(f"Supabase save failed: {e}")

    except Exception as e:
        print(f"[Pipeline:{run_id}] FAILED: {e}")
        try:
            r = get_redis()
            r.setex(f"pipeline_run:{run_id}", 3600, json.dumps({
                "run_id": run_id, "status": "failed", "error": str(e)
            }))
        except:
            pass


@app.get("/api/pipeline/status/{run_id}")
def get_pipeline_status(run_id: str):
    try:
        r = get_redis()
        data = r.get(f"pipeline_run:{run_id}")
        if not data:
            raise HTTPException(status_code=404, detail="Run not found")
        return json.loads(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pipeline/logs/{run_id}")
def get_pipeline_logs(run_id: str):
    try:
        r = get_redis()
        data = r.get(f"pipeline_log:{run_id}")
        return json.loads(data or "[]")
    except:
        return []


@app.get("/api/pipeline/stream/{run_id}")
async def stream_pipeline_status(run_id: str):
    """SSE stream for real-time pipeline updates"""
    async def event_stream():
        for _ in range(120):  # 2 min max
            try:
                r = get_redis()
                data = r.get(f"pipeline_run:{run_id}")
                if data:
                    status = json.loads(data)
                    yield f"data: {json.dumps(status)}\n\n"
                    if status.get("status") in ["completed", "failed"]:
                        break
            except:
                pass
            await asyncio.sleep(2)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Leads ──────────────────────────────────────────────────────────────────────
@app.get("/api/leads")
def get_leads(stage: Optional[str] = None, urgency: Optional[str] = None, limit: int = 100):
    try:
        sb = get_supabase()
        query = sb.table("leads").select("*").order("created_at", desc=True).limit(limit)
        if stage:
            query = query.eq("stage", stage)
        if urgency:
            query = query.eq("urgency", urgency)
        res = query.execute()
        return {"leads": res.data or [], "total": len(res.data or [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/leads")
def create_lead(lead: Lead):
    try:
        sb = get_supabase()
        data = lead.model_dump(exclude={"id"})
        data["created_at"] = datetime.now().isoformat()
        data["updated_at"] = datetime.now().isoformat()
        res = sb.table("leads").insert(data).execute()
        return res.data[0] if res.data else {"error": "Insert failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: str, updates: Dict[str, Any]):
    try:
        sb = get_supabase()
        updates["updated_at"] = datetime.now().isoformat()
        res = sb.table("leads").update(updates).eq("id", lead_id).execute()
        return res.data[0] if res.data else {"error": "Update failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: str):
    try:
        sb = get_supabase()
        sb.table("leads").delete().eq("id", lead_id).execute()
        return {"deleted": lead_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Scraper ────────────────────────────────────────────────────────────────────
class ScraperRunRequest(BaseModel):
    sources: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    max_results: int = 20
    min_score_threshold: int = 50


@app.post("/api/scraper/run")
async def run_scraper(request: ScraperRunRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())[:8]
    config = ScraperJobConfig(
        sources=[ScraperSource(s) for s in (request.sources or ["google", "forums", "care_directories"])],
        keywords=request.keywords or SERVICE_KEYWORDS[:6],
        locations=request.locations or COMPANY_LOCATIONS[:4],
        max_results=request.max_results,
        min_score_threshold=request.min_score_threshold,
    )
    background_tasks.add_task(_run_pipeline_task, run_id, config)
    return {"run_id": run_id, "status": "started"}


@app.get("/api/scraper/results")
def get_scraper_results(status: Optional[str] = None, limit: int = 50):
    try:
        sb = get_supabase()
        query = sb.table("scraper_results").select("*").order("created_at", desc=True).limit(limit)
        if status:
            query = query.eq("status", status)
        res = query.execute()
        return {"results": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/scraper/results/{result_id}/approve")
def approve_scraper_result(result_id: str):
    try:
        sb = get_supabase()
        sb.table("scraper_results").update({"status": "approved"}).eq("id", result_id).execute()
        return {"approved": result_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/scraper/results/{result_id}/reject")
def reject_scraper_result(result_id: str):
    try:
        sb = get_supabase()
        sb.table("scraper_results").update({"status": "rejected"}).eq("id", result_id).execute()
        return {"rejected": result_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Agents ─────────────────────────────────────────────────────────────────────
@app.post("/api/agents/run")
async def run_agent(request: AgentRunRequest):
    agent_name = request.agent_name.value
    agent = AGENT_REGISTRY.get(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

    start = datetime.now()
    try:
        if agent_name == "ceo":
            result = AGENT_REGISTRY["ceo"].run(request.context or {})
        elif agent_name == "crm_manager":
            leads_data = request.context.get("leads", [])
            leads = [Lead(**l) for l in leads_data]
            result = AGENT_REGISTRY["crm_manager"].health_check(leads)
        elif agent_name == "urgency_detection":
            leads_data = request.context.get("leads", [])
            leads = [Lead(**l) for l in leads_data]
            result = {
                "escalations": AGENT_REGISTRY["urgency_detection"].scan_leads(leads),
                "summary": AGENT_REGISTRY["urgency_detection"].assess_pipeline_urgency(leads)
            }
        elif agent_name == "referral_agent":
            rel = request.context.get("relationship", {})
            result = AGENT_REGISTRY["referral_agent"].generate_recommendation(rel)
        else:
            result = {"message": f"{agent_name} run cycle completed", "timestamp": datetime.now().isoformat()}

        duration_ms = int((datetime.now() - start).total_seconds() * 1000)

        # Log to Supabase
        try:
            sb = get_supabase()
            sb.table("agent_logs").insert({
                "agent_name": agent_name,
                "status": "completed",
                "input": request.context,
                "output": result,
                "duration_ms": duration_ms,
                "created_at": datetime.now().isoformat(),
            }).execute()
        except:
            pass

        return {"agent": agent_name, "status": "completed", "result": result, "duration_ms": duration_ms}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/logs")
def get_agent_logs(agent_name: Optional[str] = None, limit: int = 50):
    try:
        sb = get_supabase()
        query = sb.table("agent_logs").select("*").order("created_at", desc=True).limit(limit)
        if agent_name:
            query = query.eq("agent_name", agent_name)
        res = query.execute()
        return {"logs": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/definitions")
def get_agent_definitions():
    return {
        "agents": [
            {"id": "ceo", "name": "CEO Agent", "role": "Strategic Controller", "category": "control", "color": "#6366f1"},
            {"id": "lead_scraper", "name": "Lead Scraper", "role": "Prospect Discovery", "category": "acquisition", "color": "#0ea5e9"},
            {"id": "lead_intelligence", "name": "Lead Intelligence", "role": "Lead Qualification", "category": "acquisition", "color": "#10b981"},
            {"id": "lead_enrichment", "name": "Lead Enrichment", "role": "Data Enhancement", "category": "acquisition", "color": "#34d399"},
            {"id": "urgency_detection", "name": "Urgency Detection", "role": "Priority Triage", "category": "intelligence", "color": "#f43f5e"},
            {"id": "outreach", "name": "Outreach Agent", "role": "First Contact (Approval Gate)", "category": "engagement", "color": "#f59e0b"},
            {"id": "nurture", "name": "Nurture Agent", "role": "Relationship Warmth", "category": "engagement", "color": "#8b5cf6"},
            {"id": "booking", "name": "Booking Agent", "role": "Assessment Conversion", "category": "conversion", "color": "#f97316"},
            {"id": "crm_manager", "name": "CRM Manager", "role": "Pipeline Integrity", "category": "intelligence", "color": "#06b6d4"},
            {"id": "referral_agent", "name": "Referral Agent", "role": "Relationship Intelligence", "category": "intelligence", "color": "#a78bfa"},
        ]
    }


# ── Outreach ───────────────────────────────────────────────────────────────────
@app.get("/api/outreach")
def get_outreach(status: Optional[str] = None):
    try:
        sb = get_supabase()
        query = sb.table("email_outreach").select("*").order("created_at", desc=True)
        if status:
            query = query.eq("status", status)
        res = query.execute()
        return {"outreach": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/outreach/{outreach_id}/approve")
def approve_outreach(outreach_id: str):
    """APPROVAL GATE: Human approves AI-drafted outreach"""
    try:
        sb = get_supabase()
        sb.table("email_outreach").update({
            "status": "approved",
            "approved_at": datetime.now().isoformat(),
        }).eq("id", outreach_id).execute()
        return {"approved": outreach_id, "status": "approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/outreach/{outreach_id}/send")
async def send_outreach(outreach_id: str):
    """Send approved outreach via Resend"""
    try:
        sb = get_supabase()
        res = sb.table("email_outreach").select("*").eq("id", outreach_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Outreach not found")

        outreach = res.data[0]
        if outreach.get("status") != "approved":
            raise HTTPException(status_code=400, detail="Outreach must be approved before sending")

        # Send via Resend
        from core.config import RESEND_API_KEY, FROM_EMAIL, FROM_NAME
        import resend
        resend.api_key = RESEND_API_KEY

        if RESEND_API_KEY:
            params = resend.Emails.SendParams(
                from_=f"{FROM_NAME} <{FROM_EMAIL}>",
                to=[outreach["to_email"]],
                subject=outreach["subject"],
                html=outreach["body"].replace("\n", "<br>"),
            )
            resend.Emails.send(params)

        sb.table("email_outreach").update({
            "status": "sent",
            "sent_at": datetime.now().isoformat(),
        }).eq("id", outreach_id).execute()

        return {"sent": outreach_id, "to": outreach["to_email"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Dashboard Stats ────────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    try:
        sb = get_supabase()
        leads_res = sb.table("leads").select("stage,urgency,pipeline_value,lead_score").execute()
        leads = leads_res.data or []

        total = len(leads)
        converted = sum(1 for l in leads if l.get("stage") == "Converted")
        pipeline_value = sum(l.get("pipeline_value", 0) for l in leads)
        high_urgency = sum(1 for l in leads if l.get("urgency") == "high")
        avg_score = sum(l.get("lead_score", 0) for l in leads) / total if total > 0 else 0

        stage_counts = {}
        for stage in ["New Lead", "Contacted", "Engaged", "Assessment Booked", "Care Package Designed", "Converted"]:
            stage_counts[stage] = sum(1 for l in leads if l.get("stage") == stage)

        outreach_res = sb.table("email_outreach").select("status").execute()
        outreach = outreach_res.data or []

        return {
            "total_leads": total,
            "converted": converted,
            "conversion_rate": round((converted / total * 100), 1) if total > 0 else 0,
            "pipeline_value": pipeline_value,
            "high_urgency": high_urgency,
            "avg_lead_score": round(avg_score, 1),
            "stage_counts": stage_counts,
            "outreach_pending": sum(1 for o in outreach if o.get("status") == "draft"),
            "outreach_sent": sum(1 for o in outreach if o.get("status") in ["sent", "opened", "replied"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Relationships ──────────────────────────────────────────────────────────────
@app.get("/api/relationships")
def get_relationships():
    try:
        sb = get_supabase()
        res = sb.table("relationships").select("*").execute()
        return {"relationships": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/relationships/{rel_id}/recommendation")
def get_relationship_recommendation(rel_id: str):
    try:
        sb = get_supabase()
        res = sb.table("relationships").select("*").eq("id", rel_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Relationship not found")

        rel = res.data[0]
        rec = AGENT_REGISTRY["referral_agent"].generate_recommendation(rel)
        return {"relationship_id": rel_id, "recommendation": rec}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
