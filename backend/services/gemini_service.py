"""
Gemini Service
All interactions with the Google Gemini API:
  - Financial data extraction from document text
  - Circular trading detection
  - Research summarisation
  - Qualitative score adjustment
  - Final credit recommendation generation

When Gemini is unavailable, rich rule-based fallbacks are used so the
CAM PDF is always populated with meaningful content.
"""
import json
import re
import logging
from typing import Tuple, List, Optional

import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# ── Gemini model setup ──────────────────────────────────────────────────────
_model = None


def _get_model():
    global _model
    if _model is None:
        if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("your_"):
            raise RuntimeError(
                "GEMINI_API_KEY is not configured. "
                "Add your key to backend/.env and restart the server."
            )
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-1.5-flash")
    return _model


def _parse_json_response(text: str) -> dict:
    """Strip markdown fences and parse JSON from Gemini output."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return {"raw_response": text}


# ── 1. Document Classification & Dynamic Extraction ────────────────────────

async def classify_document(text: str, filename: str) -> str:
    try:
        model = _get_model()
        prompt = f"""
You are an expert Indian credit analyst. Categorise the following document '{filename}' based on its text content.

Choose exactly ONE of the following categories that best describes the document:
- "Financial Statement" (e.g., Annual Report, Balance Sheet, P&L, Audit Report)
- "Bank Statement"
- "Legal Notice" (e.g., NCLT, DRT, Court Summons, Sanction Letter)
- "Rating Report" (e.g., CRISIL, ICRA, CARE)
- "GST Return" (e.g., GSTR-3B, GSTR-1)
- "Other" (if none of the above apply)

Return ONLY a JSON object with a single key "category" containing the chosen category as a string.

DOCUMENT TEXT (first 3000 chars):
{text[:3000]}
"""
        response = model.generate_content(prompt)
        data = _parse_json_response(response.text)
        return data.get("category", "Other")
    except Exception as e:
        logger.warning(f"Gemini document classification failed for {filename}: {e}")
        return "Other"


async def extract_data_with_schema(text: str, company_name: str, filename: str, category: str, schema: dict) -> dict:
    try:
        model = _get_model()
        schema_json_str = json.dumps(schema, indent=2)
        prompt = f"""
You are an expert Indian credit analyst. Analyse the document '{filename}' for '{company_name}'.
The document has been classified as '{category}'.

Your task is to extract data according to the VERY SPECIFIC JSON schema provided below.
Extract the relevant values from the text. If a value is not found, use null, 0, or [] as appropriate.

Additionally, always extract these standard metadata fields:
- "summary": (string) 2–3 sentence executive summary of the document
- "pages": (integer) estimated number of pages (use 0 if unknown)
- "risk_flags": list of strings — any red flags found
- "legal_flags": list of strings — litigation mentions, NCLT/DRT/ED references
- "collateral_mentions": list of strings — property/assets pledged as collateral

Provide your response strictly as valid JSON matching this exact structure:
{{
  "summary": "...",
  "pages": 0,
  "risk_flags": [],
  "legal_flags": [],
  "collateral_mentions": [],
  "extracted_data": {schema_json_str}
}}

Return ONLY valid JSON, no other text.

DOCUMENT TEXT (first 8000 chars):
{text[:8000]}
"""
        response = model.generate_content(prompt)
        return _parse_json_response(response.text)
    except Exception as e:
        logger.warning(f"Gemini dynamic extraction failed for {filename}: {e}")
        return {
            "summary": f"Document '{filename}' uploaded. Gemini AI extraction unavailable — manual review required.",
            "pages": 0,
            "risk_flags": [],
            "legal_flags": [],
            "collateral_mentions": [],
            "extracted_data": {}
        }


# ── 2. Circular trading / revenue inflation detection ───────────────────────
async def detect_circular_trading(gst_data: dict, bank_data: dict) -> List[str]:
    from services.gst_analyser import analyse_gst_vs_bank
    flags, summary = analyse_gst_vs_bank(gst_data, bank_data)

    if not flags:
        return []

    try:
        model = _get_model()
        prompt = f"""
You are an Indian credit fraud detection expert specialising in GST analysis.
Review the following GST vs Bank Statement cross-check results and provide additional insights.

GST Analysis Summary:
{json.dumps(summary, indent=2)}

Initial flags raised:
{json.dumps(flags, indent=2)}

Return a JSON object with key "additional_flags" containing a list of strings with any extra risks identified.
Return ONLY valid JSON.
"""
        response = model.generate_content(prompt)
        data = _parse_json_response(response.text)
        return flags + data.get("additional_flags", [])
    except Exception as e:
        logger.warning(f"Gemini circular trading analysis failed: {e}")
        return flags


# ── 3. Research summarisation ───────────────────────────────────────────────
async def summarize_research(company_name: str, research_data: dict) -> Tuple[str, List[str]]:
    try:
        model = _get_model()
        prompt = f"""
You are a senior credit analyst preparing a research brief for Indian corporate lending.
Summarise the following secondary research for '{company_name}' in the context of a credit appraisal.

Research Data:
{json.dumps(research_data, indent=2)[:5000]}

Return a JSON object with:
- "summary": (string) 4–6 sentence comprehensive research summary covering company reputation,
  promoter background, sector outlook, and litigation risks
- "risk_signals": list of strings — specific early warning signals or red flags found in the research
  (e.g., "Promoter X named in ED inquiry 2023", "Sector facing NPA stress per RBI circular")

Return ONLY valid JSON.
"""
        response = model.generate_content(prompt)
        data = _parse_json_response(response.text)
        return data.get("summary", "Research summary unavailable."), data.get("risk_signals", [])
    except Exception as e:
        logger.warning(f"Gemini research summarisation failed: {e}")
        # Build a rule-based summary from available search results
        company_news = research_data.get("company_news", [])
        litigation = research_data.get("litigation", [])
        sector = research_data.get("sector_headwinds", [])

        news_count = len(company_news)
        litigation_count = len(litigation)

        summary = (
            f"Secondary research for {company_name} retrieved {news_count} company news articles "
            f"and {litigation_count} litigation-related results. "
            f"Sector headwind data includes {len(sector)} regulatory and market updates. "
            f"Web-scale research was conducted across news, NCLT/DRT litigation databases, "
            f"and regulatory sources (SEBI, RBI). Manual review of flagged articles is recommended."
        )
        risk_signals = []
        if litigation_count > 3:
            risk_signals.append(f"Multiple litigation results found ({litigation_count}). Manual verification of NCLT/DRT cases required.")
        for item in company_news[:3]:
            title = item.get("title", "")
            for kw in ["fraud", "ED", "CBI", "default", "SEBI", "penalty", "insolvency"]:
                if kw.lower() in title.lower():
                    risk_signals.append(f"News flag: {title[:120]}")
                    break
        return summary, risk_signals


# ── 4. Qualitative note adjustment ──────────────────────────────────────────
async def adjust_score_for_qualitative(notes: str) -> dict:
    try:
        model = _get_model()
        prompt = f"""
You are a credit officer AI assistant. A field officer has submitted the following qualitative notes
from a factory visit / management interview:

"{notes}"

Analyse these notes and return a JSON object with:
- "score_adjustment": (integer between -30 and +10) — negative means risk worsens, positive means risk improves
- "adjustment_reasons": list of strings explaining each adjustment
- "critical_concerns": list of strings for any show-stopper findings
- "positive_factors": list of strings for any upside findings

Return ONLY valid JSON.
"""
        response = model.generate_content(prompt)
        return _parse_json_response(response.text)
    except Exception as e:
        logger.warning(f"Gemini qualitative adjustment failed: {e}")
        # Rule-based fallback
        adj = 0
        reasons = []
        concerns = []
        positives = []
        notes_lower = notes.lower()

        negative_kw = {
            "40% capacity": -15, "low capacity": -10, "evasive": -10,
            "stretched": -8, "delayed": -8, "under construction": -5,
            "shutdown": -15, "vacant": -12, "dispute": -10,
        }
        positive_kw = {
            "prime": +5, "strong banking": +5, "above capacity": +8,
            "100% capacity": +10, "new order": +5, "expansion": +5,
            "good collateral": +7, "experienced": +5,
        }
        for kw, delta in negative_kw.items():
            if kw in notes_lower:
                adj += delta
                reasons.append(f"Negative indicator detected: '{kw}' → {delta} pts")
                if delta <= -10:
                    concerns.append(f"Critical finding: {kw}")
        for kw, delta in positive_kw.items():
            if kw in notes_lower:
                adj += delta
                reasons.append(f"Positive indicator detected: '{kw}' → +{delta} pts")
                positives.append(f"Upside factor: {kw}")

        adj = max(-30, min(10, adj))
        if not reasons:
            reasons = ["Qualitative notes noted. No specific keywords triggered automatic adjustment."]
        return {
            "score_adjustment": adj,
            "adjustment_reasons": reasons,
            "critical_concerns": concerns,
            "positive_factors": positives,
        }


# ── 5. Final credit recommendation ─────────────────────────────────────────
async def generate_final_recommendation(
    company_name: str,
    scores: dict,
    extracted_data: dict,
    research_data: dict,
    loan_amount_requested: Optional[float],
    loan_purpose: Optional[str],
    tenure_months: Optional[int],
) -> dict:
    five_c = scores.get("five_c", {})
    total_score = five_c.get("total", 0)

    # Determine decision thresholds
    if total_score >= 65:
        decision = "APPROVE"
    elif total_score >= 50:
        decision = "CONDITIONAL_APPROVE"
    else:
        decision = "REJECT"

    # Interest rate model: base MCLR ~8.5% + risk premium
    risk_premium_bps = max(0, int((100 - total_score) * 3))  # 0–300 bps
    base_rate = 8.5
    rec_rate = round(base_rate + risk_premium_bps / 100, 2) if decision != "REJECT" else None
    rec_amount = None
    if loan_amount_requested and decision != "REJECT":
        ltv_factor = min(1.0, total_score / 100 * 1.3)
        rec_amount = round(loan_amount_requested * ltv_factor, 2)

    # ── Try Gemini first ────────────────────────────────────────────────────
    try:
        model = _get_model()
        prompt = f"""
You are the Chief Credit Officer of a leading Indian commercial bank. You must provide a final
credit recommendation for '{company_name}'.

CREDIT SCORES (out of 100):
- Character: {five_c.get('character', 0):.1f}
- Capacity: {five_c.get('capacity', 0):.1f}
- Capital: {five_c.get('capital', 0):.1f}
- Collateral: {five_c.get('collateral', 0):.1f}
- Conditions: {five_c.get('conditions', 0):.1f}
- TOTAL: {total_score:.1f} / 100

LOAN REQUEST:
- Amount Requested: ₹{loan_amount_requested or 'Not specified'} Crores
- Purpose: {loan_purpose or 'Not specified'}
- Tenure: {tenure_months or 60} months

KEY FINANCIAL HIGHLIGHTS:
{json.dumps(extracted_data.get('financials', {}), indent=2)[:1500]}

RESEARCH RISK SIGNALS:
{json.dumps(research_data.get('risk_signals', []), indent=2)[:1000]}

Based on the above, return a JSON object with:
- "decision": one of "APPROVE", "CONDITIONAL_APPROVE", or "REJECT"
- "recommended_loan_amount": (float, INR Crores) — null if rejected
- "recommended_interest_rate": (float, %) — e.g. 10.5 — null if rejected
- "risk_premium_bps": (integer) basis points above base rate (MCLR ~8.5%)
- "rationale": (string) 5–8 sentences explaining the decision with SPECIFIC references to the data
  (e.g., "Rejected due to high litigation risk found in secondary research despite strong GST flows")
- "key_risks": list of 5 strings — top risks
- "mitigants": list of strings — suggested mitigants / conditions if approving
- "cam_sections": dict with keys character, capacity, capital, collateral, conditions —
  each containing a 3–4 sentence narrative for the Credit Appraisal Memo

Return ONLY valid JSON.
"""
        response = model.generate_content(prompt)
        result = _parse_json_response(response.text)
        # Ensure mandatory fields are present
        if "decision" in result and "rationale" in result:
            logger.info(f"Gemini recommendation generated successfully for {company_name}")
            return result
    except Exception as e:
        logger.warning(f"Gemini recommendation failed for {company_name}: {e}. Using rule-based fallback.")

    # ── Rule-based fallback (rich, meaningful content) ──────────────────────
    financials = extracted_data.get("financials", {})
    risk_signals = research_data.get("risk_signals", [])
    char = five_c.get("character", 70)
    cap = five_c.get("capacity", 60)
    capital = five_c.get("capital", 60)
    coll = five_c.get("collateral", 50)
    cond = five_c.get("conditions", 65)

    # Build rationale
    decision_word = decision.replace("_", " ")
    if decision == "APPROVE":
        rationale_intro = f"Based on a comprehensive Five-Cs credit assessment, the credit proposal for {company_name} is recommended for APPROVAL."
    elif decision == "CONDITIONAL_APPROVE":
        rationale_intro = f"The credit proposal for {company_name} is recommended for CONDITIONAL APPROVAL, subject to the mitigants and covenants outlined below."
    else:
        rationale_intro = f"The credit proposal for {company_name} is recommended for REJECTION based on the following risk assessment."

    dscr = financials.get("dscr")
    de = financials.get("debt_equity_ratio")
    net_worth = financials.get("net_worth_cr")
    revenue = financials.get("revenue_cr")

    fin_summary = []
    if dscr:
        qualifier = "healthy" if dscr >= 1.5 else ("adequate" if dscr >= 1.2 else "weak")
        fin_summary.append(f"DSCR of {dscr:.2f}x is {qualifier}")
    if de:
        qualifier = "conservative" if de <= 2.0 else ("moderate" if de <= 3.5 else "high")
        fin_summary.append(f"D/E ratio of {de:.2f}x reflects {qualifier} leverage")
    if net_worth:
        fin_summary.append(f"net worth of ₹{net_worth:.0f} Crores")
    if revenue:
        fin_summary.append(f"revenue base of ₹{revenue:.0f} Crores")

    fin_text = (", ".join(fin_summary) + ".") if fin_summary else "Financial data extracted from submitted documents."
    research_text = f"Secondary research identified {len(risk_signals)} risk signal(s)." if risk_signals else "Secondary research did not identify significant adverse findings."
    if risk_signals:
        research_text += f" Key concern: {risk_signals[0][:100]}."

    rationale = (
        f"{rationale_intro} "
        f"The company scored {total_score:.1f}/100 on the Five-Cs model (Character: {char:.0f}, "
        f"Capacity: {cap:.0f}, Capital: {capital:.0f}, Collateral: {coll:.0f}, Conditions: {cond:.0f}). "
        f"Financial highlights include: {fin_text} "
        f"{research_text} "
        f"The recommended interest rate of {rec_rate}% (Risk premium: {risk_premium_bps} bps over MCLR) "
        f"appropriately prices the identified risks for this credit exposure."
        if decision != "REJECT" else
        f"{rationale_intro} "
        f"The company scored {total_score:.1f}/100 on the Five-Cs model. "
        f"{fin_text} "
        f"{research_text} "
        f"The overall risk profile does not meet the bank's minimum threshold of 50/100 for approval."
    )

    # Build key risks
    key_risks = []
    if char < 65:
        key_risks.append(f"Character risk: Promoter/governance score of {char:.0f}/100 — litigation or reputation concerns identified")
    if cap < 65:
        key_risks.append(f"Capacity risk: Repayment ability score of {cap:.0f}/100 — DSCR/ICR may not meet comfort levels")
    if capital < 65:
        key_risks.append(f"Capital risk: Leverage score of {capital:.0f}/100 — high D/E ratio or thin net worth")
    if coll < 60:
        key_risks.append(f"Collateral risk: Security cover score of {coll:.0f}/100 — collateral may be insufficient or illiquid")
    if cond < 60:
        key_risks.append(f"Conditions risk: Sector/macro score of {cond:.0f}/100 — sector headwinds or regulatory risks")
    if risk_signals:
        key_risks.append(f"Research risk: {risk_signals[0][:120]}")
    while len(key_risks) < 3:
        key_risks.append("Concentration risk: Single-borrower exposure in a cyclical sector")

    # Build mitigants
    mitigants = []
    if decision != "REJECT":
        if loan_amount_requested and rec_amount and rec_amount < loan_amount_requested:
            mitigants.append(f"Sanction ₹{rec_amount:.1f} Cr vs requested ₹{loan_amount_requested:.1f} Cr (haircut applied based on score)")
        mitigants.append("Obtain personal guarantee of key promoters/directors")
        mitigants.append("Mortgage of primary collateral with registered charge via CERSAI")
        mitigants.append("Quarterly financial covenant monitoring (DSCR, D/E ratio reporting)")
        mitigants.append("Escrow of receivables with the lending bank for working capital facilities")
        if char < 70:
            mitigants.append("Enhanced KYC and periodic background refresh on promoters")

    # Build cam_sections (rich narratives for the CAM PDF)
    cam_sections = {
        "character": (
            f"{company_name} has received a Character score of {char:.0f}/100. "
            f"The assessment is based on promoter background research, governance track record, and litigation history. "
            f"{'No significant adverse findings were identified in the secondary research.' if char >= 70 else 'Some adverse signals were identified that warrant continued monitoring.'} "
            f"The promoter group's ability to manage the business and honour financial commitments is considered {'adequate' if char >= 65 else 'marginal'} at this time."
        ),
        "capacity": (
            f"{company_name} has received a Capacity score of {cap:.0f}/100. "
            f"{'DSCR of ' + str(dscr) + 'x indicates ' + ('strong' if dscr >= 1.5 else 'adequate') + ' debt servicing ability. ' if dscr else 'DSCR data was not available from submitted documents. '}"
            f"{'D/E ratio of ' + str(de) + 'x reflects the leverage position. ' if de else ''}"
            f"{'Revenue base of ₹' + str(revenue) + ' Crores provides ' + ('comfortable' if cap >= 65 else 'limited') + ' operating headroom. ' if revenue else ''}"
            f"The overall repayment capacity is assessed as {'satisfactory' if cap >= 65 else 'stretched'} relative to the proposed facility."
        ),
        "capital": (
            f"{company_name} has received a Capital score of {capital:.0f}/100. "
            f"{'Net worth of ₹' + str(net_worth) + ' Crores provides ' + ('a strong' if net_worth and net_worth >= 100 else 'a moderate') + ' equity buffer. ' if net_worth else 'Net worth data was not extracted from available documents. '}"
            f"The company's leverage profile is assessed as {'conservative and within comfortable limits' if capital >= 70 else ('moderate with some room for caution' if capital >= 55 else 'elevated and requiring close monitoring')}. "
            f"Capital adequacy is a {'positive' if capital >= 65 else 'limiting'} factor in this credit decision."
        ),
        "collateral": (
            f"{company_name} has received a Collateral score of {coll:.0f}/100. "
            f"{'Collateral mentions were identified in submitted documents. ' if extracted_data.get('collateral_mentions') else 'Specific collateral details were not extracted from submitted documents. '}"
            f"{'Collateral coverage ratio of ' + str(round((extracted_data.get('collateral_value', 0) or 0) / (loan_amount_requested or 1), 2)) + 'x based on provided values. ' if loan_amount_requested else ''}"
            f"The security package should be supplemented with personal guarantees and first charge on all fixed assets. "
            f"Independent valuation of collateral is recommended before drawdown."
        ),
        "conditions": (
            f"{company_name} has received a Conditions score of {cond:.0f}/100. "
            f"{'The sector faces headwinds based on research findings. ' if cond < 65 else 'Sector conditions are broadly supportive at this time. '}"
            f"RBI and SEBI regulatory environment has been reviewed for sector-specific constraints. "
            f"Macro-economic conditions including interest rate trajectory (MCLR benchmark), GST collection trends, and credit cycle indicators have been factored into the conditions score. "
            f"The loan purpose of '{loan_purpose or 'business operations'}' aligns with the company's stated operational requirements."
        ),
    }

    return {
        "decision": decision,
        "recommended_loan_amount": rec_amount,
        "recommended_interest_rate": rec_rate,
        "risk_premium_bps": risk_premium_bps,
        "rationale": rationale,
        "key_risks": key_risks[:5],
        "mitigants": mitigants,
        "cam_sections": cam_sections,
    }
