"""
Credit Scoring Engine
Implements a transparent, explainable Five-Cs scoring model.
Weights are calibrated for Indian corporate lending context.
"""
from typing import Optional


# ── Weight configuration ────────────────────────────────────────────────────
FIVE_C_WEIGHTS = {
    "character":  0.25,  # Promoter integrity, track record, governance
    "capacity":   0.30,  # Ability to repay: DSCR, ICR, operating cash flows
    "capital":    0.20,  # Net worth, D/E ratio, leverage
    "collateral": 0.15,  # Security cover, collateral quality
    "conditions": 0.10,  # Sector outlook, macro conditions, loan purpose
}

GRADE_THRESHOLDS = [
    (85, "AAA"),
    (75, "AA"),
    (65, "A"),
    (55, "BBB"),
    (45, "BB"),
    (35, "B"),
    (0,  "C"),
]


def _grade(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "D"


def _score_character(extracted_data: dict, research_data: dict) -> float:
    """Score 0-100 for Character (promoter integrity, governance)."""
    score = 70.0  # Neutral baseline

    risk_signals = research_data.get("risk_signals", [])
    litigation = research_data.get("litigation_history", [])

    # Penalties
    fraud_keywords = ["fraud", "scam", "ED", "CBI", "SFIO", "enforcement", "arrest", "default", "wilful"]
    for signal in risk_signals:
        for kw in fraud_keywords:
            if kw.lower() in signal.lower():
                score -= 15
                break

    if len(litigation) > 5:
        score -= 10
    elif len(litigation) > 2:
        score -= 5

    legal_flags = extracted_data.get("legal_flags", [])
    score -= min(len(legal_flags) * 5, 20)

    return max(0.0, min(100.0, score))


def _score_capacity(financials: dict, qual_adjustment: dict) -> float:
    """Score 0-100 for Capacity (repayment ability)."""
    score = 60.0

    dscr = financials.get("dscr")
    icr  = financials.get("interest_coverage_ratio")
    ebitda = financials.get("ebitda_cr")
    revenue = financials.get("revenue_cr")

    if dscr is not None:
        if dscr >= 2.0:   score += 20
        elif dscr >= 1.5: score += 12
        elif dscr >= 1.2: score += 5
        elif dscr < 1.0:  score -= 20

    if icr is not None:
        if icr >= 4.0:   score += 10
        elif icr >= 2.5: score += 5
        elif icr < 1.5:  score -= 15

    if ebitda and revenue and revenue > 0:
        margin = ebitda / revenue
        if margin >= 0.20:   score += 10
        elif margin >= 0.12: score += 5
        elif margin < 0.05:  score -= 10

    # Qualitative adjustment
    qual_adj = qual_adjustment.get("score_adjustment", 0)
    score += qual_adj * 0.5  # Apply 50% of qual adjustment to capacity

    return max(0.0, min(100.0, score))


def _score_capital(financials: dict) -> float:
    """Score 0-100 for Capital (leverage, net worth)."""
    score = 60.0

    de_ratio   = financials.get("debt_equity_ratio")
    net_worth  = financials.get("net_worth_cr")
    total_debt = financials.get("total_debt_cr")

    if de_ratio is not None:
        if de_ratio <= 1.0:  score += 20
        elif de_ratio <= 2.0: score += 10
        elif de_ratio <= 3.0: score += 0
        elif de_ratio <= 4.0: score -= 10
        else:                  score -= 20

    if net_worth is not None:
        if net_worth >= 500:  score += 10
        elif net_worth >= 100: score += 5
        elif net_worth < 10:  score -= 10

    if total_debt and net_worth and net_worth > 0:
        gearing = total_debt / net_worth
        if gearing > 5: score -= 15

    return max(0.0, min(100.0, score))


def _score_collateral(extracted_data: dict, collateral_value: Optional[float], loan_amount: Optional[float]) -> float:
    """Score 0-100 for Collateral."""
    score = 50.0

    collateral_mentions = extracted_data.get("collateral_mentions", [])
    if collateral_mentions:
        score += min(len(collateral_mentions) * 8, 24)

    if collateral_value and loan_amount and loan_amount > 0:
        cover = collateral_value / loan_amount
        if cover >= 2.0:   score += 25
        elif cover >= 1.5: score += 15
        elif cover >= 1.25: score += 8
        elif cover >= 1.0: score += 0
        else:              score -= 15

    return max(0.0, min(100.0, score))


def _score_conditions(research_data: dict, financials: dict) -> float:
    """Score 0-100 for Conditions (sector, macro)."""
    score = 65.0  # Moderate baseline

    risk_signals = research_data.get("risk_signals", [])
    sector_news  = research_data.get("sector_headwinds", [])

    negative_kw = ["downturn", "headwind", "NPA", "stress", "slowdown", "crisis", "ban", "restriction"]
    positive_kw = ["growth", "opportunity", "expansion", "PLI", "infra", "export"]

    for signal in risk_signals:
        for kw in negative_kw:
            if kw.lower() in signal.lower():
                score -= 5
                break
        for kw in positive_kw:
            if kw.lower() in signal.lower():
                score += 3
                break

    roce = financials.get("roce_pct")
    if roce is not None:
        if roce >= 15:   score += 10
        elif roce >= 10: score += 5
        elif roce < 5:   score -= 8

    return max(0.0, min(100.0, score))


# ── Main scoring function ───────────────────────────────────────────────────
def compute_credit_score(
    extracted_data: dict,
    research_data: dict,
    loan_amount_requested: Optional[float] = None,
    collateral_value: Optional[float] = None,
) -> dict:
    financials    = extracted_data.get("financials", {})
    qual_adjustment = research_data.get("qualitative_adjustment", {})

    char_score  = _score_character(extracted_data, research_data)
    cap_score   = _score_capacity(financials, qual_adjustment)
    capit_score = _score_capital(financials)
    coll_score  = _score_collateral(extracted_data, collateral_value, loan_amount_requested)
    cond_score  = _score_conditions(research_data, financials)

    total = (
        char_score  * FIVE_C_WEIGHTS["character"]  +
        cap_score   * FIVE_C_WEIGHTS["capacity"]   +
        capit_score * FIVE_C_WEIGHTS["capital"]    +
        coll_score  * FIVE_C_WEIGHTS["collateral"] +
        cond_score  * FIVE_C_WEIGHTS["conditions"]
    )

    five_c = {
        "character":  round(char_score, 1),
        "capacity":   round(cap_score, 1),
        "capital":    round(capit_score, 1),
        "collateral": round(coll_score, 1),
        "conditions": round(cond_score, 1),
        "total":      round(total, 1),
        "grade":      _grade(total),
    }

    return {
        "five_c": five_c,
        "weights": FIVE_C_WEIGHTS,
    }
