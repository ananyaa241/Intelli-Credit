"""
Recommendation Engine Router
Produces:
  1. Five-Cs scoring model
  2. Loan amount + interest rate recommendation
  3. Credit Appraisal Memo (CAM) as PDF
"""
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from config import UPLOAD_DIR
from services.scoring_engine import compute_credit_score
from services.cam_generator import generate_cam_pdf
from services.gemini_service import generate_final_recommendation

logger = logging.getLogger(__name__)
router = APIRouter()


class RecommendationRequest(BaseModel):
    session_id: str
    company_name: str
    loan_amount_requested: Optional[float] = None   # INR Crores
    loan_purpose: Optional[str] = ""
    tenure_months: Optional[int] = 60
    collateral_value: Optional[float] = None        # INR Crores


class FiveCScore(BaseModel):
    character: float
    capacity: float
    capital: float
    collateral: float
    conditions: float
    total: float
    grade: str


class RecommendationResponse(BaseModel):
    session_id: str
    decision: str                    # APPROVE / CONDITIONAL_APPROVE / REJECT
    recommended_loan_amount: Optional[float]
    recommended_interest_rate: Optional[float]
    risk_premium_bps: int
    five_c_scores: FiveCScore
    decision_rationale: str
    key_risks: list
    mitigants: list
    cam_available: bool


@router.post("/generate", response_model=RecommendationResponse)
async def generate_recommendation(req: RecommendationRequest):
    session_dir = Path(UPLOAD_DIR) / req.session_id
    # Always ensure the session directory exists
    session_dir.mkdir(parents=True, exist_ok=True)

    # ── Load upstream data ──────────────────────────────────────────────────
    extracted_data = {}
    research_data = {}

    extracted_file = session_dir / "extracted_data.json"
    research_file = session_dir / "research_output.json"

    if extracted_file.exists():
        with open(extracted_file) as f:
            extracted_data = json.load(f)
    else:
        # Seed with company name so scoring/CAM have context
        extracted_data = {
            "company_name": req.company_name,
            "session_id": req.session_id,
            "documents": [],
            "financials": {},
            "legal_flags": [],
            "collateral_mentions": [],
        }

    if research_file.exists():
        with open(research_file) as f:
            research_data = json.load(f)

    # ── Scoring ─────────────────────────────────────────────────────────────
    scores = compute_credit_score(
        extracted_data=extracted_data,
        research_data=research_data,
        loan_amount_requested=req.loan_amount_requested,
        collateral_value=req.collateral_value,
    )

    # ── Gemini final recommendation ─────────────────────────────────────────
    rec = await generate_final_recommendation(
        company_name=req.company_name,
        scores=scores,
        extracted_data=extracted_data,
        research_data=research_data,
        loan_amount_requested=req.loan_amount_requested,
        loan_purpose=req.loan_purpose,
        tenure_months=req.tenure_months,
    )

    result = {
        "session_id": req.session_id,
        "decision": rec["decision"],
        "recommended_loan_amount": rec.get("recommended_loan_amount"),
        "recommended_interest_rate": rec.get("recommended_interest_rate"),
        "risk_premium_bps": rec.get("risk_premium_bps", 0),
        "five_c_scores": scores["five_c"],
        "decision_rationale": rec["rationale"],
        "key_risks": rec.get("key_risks", []),
        "mitigants": rec.get("mitigants", []),
        "cam_available": False,
    }

    # ── Generate CAM PDF ────────────────────────────────────────────────────
    try:
        cam_path = session_dir / "cam_report.pdf"
        generate_cam_pdf(
            output_path=str(cam_path),
            company_name=req.company_name,
            recommendation=rec,
            scores=scores,
            extracted_data=extracted_data,
            research_data=research_data,
            loan_request=req.dict(),
        )
        result["cam_available"] = cam_path.exists() and cam_path.stat().st_size > 0
        logger.info(f"CAM generated at {cam_path} ({cam_path.stat().st_size} bytes)")
    except Exception as e:
        logger.error(f"CAM generation failed for session {req.session_id}: {e}", exc_info=True)
        # Don't fail the API — recommendation data is still valid

    # ── Persist recommendation ───────────────────────────────────────────────
    try:
        with open(session_dir / "recommendation.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Could not save recommendation.json: {e}")

    return RecommendationResponse(**result)


@router.get("/cam/{session_id}")
async def download_cam(session_id: str):
    cam_path = Path(UPLOAD_DIR) / session_id / "cam_report.pdf"
    if not cam_path.exists():
        raise HTTPException(
            status_code=404,
            detail="CAM report not found. Please run /generate first to create it."
        )
    with open(cam_path, "rb") as f:
        content = f.read()
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=CAM_{session_id[:8]}.pdf"},
    )


@router.get("/session/{session_id}")
async def get_recommendation(session_id: str):
    rec_file = Path(UPLOAD_DIR) / session_id / "recommendation.json"
    if not rec_file.exists():
        raise HTTPException(status_code=404, detail="No recommendation found for this session.")
    with open(rec_file) as f:
        return json.load(f)
