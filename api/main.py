"""
api/main.py
FastAPI REST API backend for AIS-Sentinel.
Serves as the API layer between the Streamlit frontend and backend modules.
"""

import os
import sys
import json
import logging
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root is on sys.path so module imports work
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.database import (
    init_db,
    get_articles,
    insert_article,
    get_benchmark_results,
    insert_benchmark_result,
    get_agent_logs,
    insert_agent_log,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AIS-Sentinel API",
    description="REST API for the AIS-Sentinel AI Safety Monitoring & Control Platform",
    version="1.0.0",
)

# CORS — allow Streamlit (default port 8501) and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Initialize the database on startup."""
    init_db()
    
    # Auto-seed database if empty
    articles = get_articles(limit=1)
    if not articles:
        logger.info("Seeding database with mock data...")
        try:
            from seed_db import seed
            seed()
        except ImportError:
            logger.warning("Could not import seed_db.py")

    logger.info("AIS-Sentinel API started — database initialized.")


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class EvaluateRequest(BaseModel):
    """Request body for threat evaluation."""
    article_text: str = Field(..., description="The article text to evaluate")
    article_title: str = Field("", description="Optional article title")


class DesignRequest(BaseModel):
    """Request body for slide design via CreativeAgent."""
    task: str = Field(..., description="The legitimate design task description")
    attack_type: Optional[str] = Field(None, description="Optional attack scenario name (e.g., STEGANOGRAPHY)")


class ScanRequest(BaseModel):
    """Request body for slide monitoring."""
    slide_json: Dict[str, Any] = Field(..., description="The slide JSON state to scan")
    use_llm: bool = Field(True, description="Whether to use LLM-based scanning in addition to rules")


class MapThreatRequest(BaseModel):
    """Request body for regulatory threat mapping."""
    risk_category: str = Field(..., description="Risk category to map (e.g., 'Biosecurity', 'AI Safety')")
    jurisdiction: Optional[str] = Field(None, description="Optional jurisdiction filter")


class CompareRequest(BaseModel):
    """Request body for jurisdiction comparison."""
    risk_category: str = Field(..., description="Risk category to compare across jurisdictions")


class ReportRequest(BaseModel):
    """Request body for compliance report generation."""
    title: Optional[str] = Field(None, description="Threat title/headline")
    risk_category: str = Field("Default", description="Risk category")
    severity: str = Field("Medium", description="Severity level")
    justification: str = Field("No justification provided.", description="Justification text")
    confidence_score: Optional[float] = Field(None, description="Confidence score")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "AIS-Sentinel API", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# IntelStream Endpoints
# ---------------------------------------------------------------------------

@app.get("/intelstream/articles")
def get_intelstream_articles(
    threat_only: bool = Query(False, description="Filter to threat-detected articles only"),
    limit: int = Query(50, description="Max articles to return"),
):
    """Fetch articles from the database."""
    try:
        articles = get_articles(threat_only=threat_only, limit=limit)
        return {"articles": articles, "count": len(articles)}
    except Exception as e:
        logger.error(f"Error fetching articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/intelstream/evaluate")
def evaluate_article(req: EvaluateRequest):
    """Evaluate an article for biosecurity threats using ThreatEvaluator."""
    try:
        from modules.intelstream.evaluator import ThreatEvaluator
        evaluator = ThreatEvaluator()
        result = evaluator.evaluate(req.article_text, article_title=req.article_title)
        return result
    except Exception as e:
        logger.error(f"Error evaluating article: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/intelstream/brief")
def generate_brief(
    days: int = Query(7, description="Number of days to cover"),
    region: str = Query("Asia", description="Region label for the brief"),
):
    """Generate a weekly HTML intelligence brief."""
    try:
        from modules.intelstream.brief_generator import BriefGenerator
        gen = BriefGenerator()
        html = gen.generate_brief(days=days, region=region)
        return {"html": html}
    except Exception as e:
        logger.error(f"Error generating brief: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/intelstream/threat-summary")
def get_threat_summary(days: int = Query(7, description="Number of trailing days")):
    """Get aggregated threat statistics."""
    try:
        from modules.intelstream.evaluator import ThreatEvaluator
        evaluator = ThreatEvaluator()
        summary = evaluator.get_threat_summary(days=days)
        return summary
    except Exception as e:
        logger.error(f"Error getting threat summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# SafetyBench Endpoints
# ---------------------------------------------------------------------------

@app.get("/safetybench/results")
def get_safetybench_results(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
):
    """Fetch benchmark results from the database."""
    try:
        results = get_benchmark_results(model_name=model_name, language=language)
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error fetching benchmark results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/safetybench/summary")
def get_safetybench_summary(
    model_name: Optional[str] = Query(None, description="Model name for summary"),
):
    """Get benchmark summary statistics for a model."""
    try:
        from modules.safetybench.test_runner import BenchmarkRunner
        # Use a dummy model_path since we're just reading summaries
        runner = BenchmarkRunner(
            model_name=model_name or "unknown",
            model_path="dummy",
        )
        summary = runner.get_summary(model_name=model_name)
        return summary
    except Exception as e:
        logger.error(f"Error getting benchmark summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/safetybench/leaderboard")
def get_leaderboard():
    """Generate the leaderboard table from DB results."""
    try:
        from modules.safetybench.leaderboard import LeaderboardGenerator
        gen = LeaderboardGenerator()
        df = gen.generate_table()
        return {"leaderboard": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"Error generating leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# AgentGuard Endpoints
# ---------------------------------------------------------------------------

@app.post("/agentguard/design")
def design_slide(req: DesignRequest):
    """Run the CreativeAgent to design a slide (optionally with a covert attack)."""
    try:
        from core.llm_client import GeminiClient
        from modules.agentguard.agent import CreativeAgent

        client = GeminiClient()
        agent = CreativeAgent(model_client=client)

        covert_task = None
        if req.attack_type:
            covert_task = agent.get_attack_scenario(req.attack_type)

        result = agent.design_slide(task=req.task, covert_task=covert_task)

        # Log to database
        try:
            scan_score = max(
                (s.get("suspicion_score", 0) for s in result.get("steps", [])),
                default=0,
            )
            insert_agent_log({
                "task_description": req.task,
                "attack_type": req.attack_type or "none",
                "slide_json": result.get("slide_json", "{}"),
                "monitor_suspicion_score": scan_score,
                "detected": result.get("covert_injected", False),
            })
        except Exception as log_err:
            logger.warning(f"Failed to log agent run: {log_err}")

        return result
    except Exception as e:
        logger.error(f"Error in agent design: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agentguard/scan")
def scan_slide(req: ScanRequest):
    """Scan slide JSON for hidden malicious content."""
    try:
        from modules.agentguard.monitor import SlideMonitor

        # Optionally use LLM client for enhanced scanning
        llm_client = None
        if req.use_llm:
            try:
                from core.llm_client import GeminiClient
                llm_client = GeminiClient()
            except Exception:
                pass

        monitor = SlideMonitor(llm_client=llm_client)
        result = monitor.scan(req.slide_json, use_llm=req.use_llm)

        # Also generate Pareto data
        pareto = monitor.generate_pareto_data(req.slide_json)
        result["pareto_data"] = pareto

        # Generate explanation
        explanation = monitor.explain_flags(result.get("flagged_elements", []))
        result["explanation"] = explanation

        return result
    except Exception as e:
        logger.error(f"Error scanning slide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agentguard/logs")
def get_agentguard_logs(
    detected_only: bool = Query(False, description="Filter to detected-only logs"),
):
    """Fetch agent monitoring logs."""
    try:
        logs = get_agent_logs(detected_only=detected_only)
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"Error fetching agent logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# PolicyBridge Endpoints
# ---------------------------------------------------------------------------

@app.post("/policybridge/map")
def map_threat(req: MapThreatRequest):
    """Map a threat risk category to applicable regulations."""
    try:
        from modules.policybridge.mapper import RegulatoryMapper
        mapper = RegulatoryMapper()
        laws = mapper.map_threat(req.risk_category, jurisdiction=req.jurisdiction)
        return {"laws": laws, "count": len(laws)}
    except Exception as e:
        logger.error(f"Error mapping threat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/policybridge/compare")
def compare_jurisdictions(req: CompareRequest):
    """Compare regulatory frameworks across jurisdictions for a risk category."""
    try:
        from modules.policybridge.mapper import RegulatoryMapper
        mapper = RegulatoryMapper()
        df = mapper.compare_jurisdictions(req.risk_category)
        return {"comparison": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"Error comparing jurisdictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/policybridge/report/html")
def generate_html_report(req: ReportRequest):
    """Generate an HTML compliance report."""
    try:
        from modules.policybridge.reporter import ComplianceReporter
        reporter = ComplianceReporter()
        threat_data = req.model_dump()
        html = reporter.generate_report(threat_data)
        return {"html": html}
    except Exception as e:
        logger.error(f"Error generating HTML report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/policybridge/report/markdown")
def generate_markdown_report(req: ReportRequest):
    """Generate a Markdown compliance report."""
    try:
        from modules.policybridge.reporter import ComplianceReporter
        reporter = ComplianceReporter()
        threat_data = req.model_dump()
        markdown = reporter.generate_markdown(threat_data)
        return {"markdown": markdown}
    except Exception as e:
        logger.error(f"Error generating Markdown report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
