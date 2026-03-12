"""
Research Agent Router
Performs:
  1. Web-scale secondary research (news, regulatory filings, litigation)
  2. Promoter background checks
  3. Sector-specific headwind analysis
  4. Primary insight integration (qualitative notes from Credit Officer)
"""
import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import UPLOAD_DIR
from services.web_search import search_news, search_litigation, search_regulatory
from services.gemini_service import summarize_research, adjust_score_for_qualitative

router = APIRouter()


class ResearchRequest(BaseModel):
    session_id: str
    company_name: str
    promoter_names: Optional[List[str]] = []
    sector: Optional[str] = ""
    qualitative_notes: Optional[str] = ""


class ResearchResponse(BaseModel):
    session_id: str
    company_news: List[dict]
    promoter_background: List[dict]
    sector_headwinds: List[dict]
    litigation_history: List[dict]
    regulatory_updates: List[dict]
    research_summary: str
    qualitative_adjustment: dict
    risk_signals: List[str]


@router.post("/run", response_model=ResearchResponse)
async def run_research(req: ResearchRequest):
    session_dir = Path(UPLOAD_DIR) / req.session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Company news ─────────────────────────────────────────────────────
    company_news = await search_news(f"{req.company_name} India corporate news fraud")

    # ── 2. Promoter background ──────────────────────────────────────────────
    promoter_results = []
    for promoter in (req.promoter_names or []):
        results = await search_news(f"{promoter} India director corporate fraud SEBI ED CBI")
        promoter_results.extend(results[:3])

    # ── 3. Sector headwinds ─────────────────────────────────────────────────
    sector_query = f"{req.sector} India sector RBI SEBI regulation headwinds 2024 2025" if req.sector else ""
    sector_news = await search_news(sector_query) if sector_query else []

    # ── 4. Litigation ────────────────────────────────────────────────────────
    litigation = await search_litigation(req.company_name)

    # ── 5. Regulatory updates ───────────────────────────────────────────────
    regulatory = await search_regulatory(req.sector or req.company_name)

    # ── 6. Gemini synthesis ─────────────────────────────────────────────────
    all_research = {
        "company_news": company_news,
        "promoter_background": promoter_results,
        "sector_headwinds": sector_news,
        "litigation": litigation,
        "regulatory": regulatory,
    }
    research_summary, risk_signals = await summarize_research(req.company_name, all_research)

    # ── 7. Qualitative adjustment ───────────────────────────────────────────
    qual_adjustment = {}
    if req.qualitative_notes:
        qual_adjustment = await adjust_score_for_qualitative(req.qualitative_notes)

    # Persist research output
    research_output = {
        "session_id": req.session_id,
        "company_news": company_news,
        "promoter_background": promoter_results,
        "sector_headwinds": sector_news,
        "litigation_history": litigation,
        "regulatory_updates": regulatory,
        "research_summary": research_summary,
        "qualitative_adjustment": qual_adjustment,
        "risk_signals": risk_signals,
    }
    with open(session_dir / "research_output.json", "w") as f:
        json.dump(research_output, f, indent=2, default=str)

    return ResearchResponse(**research_output)
