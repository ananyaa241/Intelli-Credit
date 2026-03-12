"""
Data Ingestor Router
Handles multi-format document parsing:
  - PDF (annual reports, legal notices, bank statements)
  - Text/CSV (GST filing cross-checks)
  - Structured JSON payloads

GSTR-3B auto-extraction:
  When a PDF is uploaded and no gst_json is manually provided,
  the system automatically scans the full extracted text for GSTR-3B
  monthly tables and populates the GST JSON field accordingly.
"""
import os
import json
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import UPLOAD_DIR
from services.pdf_parser import parse_pdf
from services.gst_analyser import analyse_gst_vs_bank
from services.gst_extractor import extract_gst_from_text
from services.gemini_service import classify_document, extract_data_with_schema, detect_circular_trading

router = APIRouter()

os.makedirs(UPLOAD_DIR, exist_ok=True)


class UploadResponse(BaseModel):
    session_id: str
    files_processed: int
    documents: List[dict]
    warnings: List[str]
    auto_gst_data: Optional[dict] = None


class ExtractRequest(BaseModel):
    company_name: str
    categories: Dict[str, str]
    extraction_schema: Dict[str, Any]
    gst_json: Optional[str] = None
    bank_statement_json: Optional[str] = None


class ExtractResponse(BaseModel):
    session_id: str
    extracted_data: dict
    warnings: List[str]
    circular_trading_flags: List[str]


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
):
    session_id = str(uuid.uuid4())
    session_dir = Path(UPLOAD_DIR) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    documents = []
    warnings = []

    # Accumulate all PDF text for a single-pass GST scan at the end
    all_pdf_text_parts: list[str] = []

    # ── Process each uploaded file ──────────────────────────────────────────
    for file in files:
        file_path = session_dir / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        ext = Path(file.filename).suffix.lower()
        if ext == ".pdf":
            try:
                text = parse_pdf(str(file_path))
                # Collect for GST scan
                all_pdf_text_parts.append(text)

                # Persist parsed text so we don't have to parse it again in extraction
                with open(session_dir / f"{file.filename}.txt", "w", encoding="utf-8") as text_file:
                    text_file.write(text)

                category = await classify_document(text, file.filename)

                documents.append({
                    "filename": file.filename,
                    "type": "pdf",
                    "category": category,
                    "raw_text_length": len(text),
                })
            except Exception as e:
                warnings.append(f"Could not parse {file.filename}: {str(e)}")
        else:
            warnings.append(f"Unsupported file type for {file.filename} (only PDF is parsed)")

    # ── Auto-extract GSTR-3B from PDF text (if not manually provided) ───────
    auto_gst_data = {}
    if all_pdf_text_parts:
        combined_text = "\n\n".join(all_pdf_text_parts)
        try:
            temp_auto_gst_data = extract_gst_from_text(combined_text)
            has_gst_data = any(temp_auto_gst_data.get(k) for k in (
                "monthly_turnover", "gstr_3b_tax_paid", "gstr_2a_itc_claimed"
            ))
            if has_gst_data:
                auto_gst_data = temp_auto_gst_data
                months_found = len(auto_gst_data.get("monthly_turnover", {}))
                warnings.append(
                    f"INFO: GSTR-3B data auto-extracted from uploaded PDFs — "
                    f"{months_found} month(s) detected."
                )
        except Exception as e:
            warnings.append(f"GSTR-3B auto-extraction warning: {str(e)}")

    return UploadResponse(
        session_id=session_id,
        files_processed=len(files),
        documents=documents,
        warnings=warnings,
        auto_gst_data=auto_gst_data if auto_gst_data else None
    )


@router.post("/extract/{session_id}", response_model=ExtractResponse)
async def extract_data(session_id: str, request: ExtractRequest):
    session_dir = Path(UPLOAD_DIR) / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    extracted_data = {
        "company_name": request.company_name,
        "session_id": session_id,
        "documents": [],
        "financials": {},
        "legal_flags": [],
        "collateral_mentions": [],
        "gst_data": {},
    }
    warnings = []
    circular_flags = []

    for filename, category in request.categories.items():
        text_file_path = session_dir / f"{filename}.txt"
        if text_file_path.exists():
            with open(text_file_path, "r", encoding="utf-8") as f:
                text = f.read()

            try:
                doc_analysis = await extract_data_with_schema(
                    text=text,
                    company_name=request.company_name,
                    filename=filename,
                    category=category,
                    schema=request.extraction_schema
                )

                extracted_data["documents"].append({
                    "filename": filename,
                    "type": "pdf",
                    "category": category,
                    "pages": doc_analysis.get("pages", 0),
                    "summary": doc_analysis.get("summary", ""),
                    "key_financials": doc_analysis.get("extracted_data", {}),
                    "risk_flags": doc_analysis.get("risk_flags", []),
                    "raw_text_length": len(text),
                })
                # Merge financials
                for k, v in doc_analysis.get("extracted_data", {}).items():
                    if k not in extracted_data["financials"] or not extracted_data["financials"][k]:
                        extracted_data["financials"][k] = v
                extracted_data["legal_flags"].extend(doc_analysis.get("legal_flags", []))
                extracted_data["collateral_mentions"].extend(doc_analysis.get("collateral_mentions", []))
            except Exception as e:
                warnings.append(f"Could not extract data from {filename}: {str(e)}")

    # ── Resolve GST data: manual JSON takes precedence over auto-extracted ───
    resolved_gst_data = None

    if request.gst_json:
        try:
            resolved_gst_data = json.loads(request.gst_json)
            extracted_data["gst_data"] = resolved_gst_data
        except Exception as e:
            warnings.append(f"Could not parse provided GST JSON: {str(e)}")

    # ── GST vs Bank Statement cross-check ──────────────────────────────────
    if resolved_gst_data and request.bank_statement_json:
        try:
            bank_data = json.loads(request.bank_statement_json)
            circular_flags = await detect_circular_trading(resolved_gst_data, bank_data)
        except Exception as e:
            warnings.append(f"GST/Bank cross-check failed: {str(e)}")
    elif resolved_gst_data and not request.bank_statement_json:
        warnings.append("GST data is available. Provide Bank Statement JSON to enable circular trading cross-check.")
    elif request.bank_statement_json and not resolved_gst_data:
        warnings.append("Bank Statement JSON provided but no GST data available for cross-check.")

    # Persist extracted data to session
    with open(session_dir / "extracted_data.json", "w") as f:
        json.dump(extracted_data, f, indent=2, default=str)

    # Also persist resolved GST data separately so the recommendation engine can use it
    if resolved_gst_data:
        with open(session_dir / "gst_data.json", "w") as f:
            json.dump(resolved_gst_data, f, indent=2, default=str)

    return ExtractResponse(
        session_id=session_id,
        extracted_data=extracted_data,
        warnings=warnings,
        circular_trading_flags=circular_flags,
    )


@router.get("/session/{session_id}")
async def get_session_data(session_id: str):
    session_dir = Path(UPLOAD_DIR) / session_id
    data_file = session_dir / "extracted_data.json"
    if not data_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    with open(data_file) as f:
        return json.load(f)
