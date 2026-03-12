"""
GST vs Bank Statement Analyser
Cross-references GSTR-3B/GSTR-2A data with bank statement credits
to identify potential circular trading or revenue inflation.
"""
from typing import List, Tuple


def analyse_gst_vs_bank(gst_data: dict, bank_data: dict) -> Tuple[List[str], dict]:
    """
    Compare GST turnover declared vs bank credits received.
    Returns (flags, summary_dict)

    Expected gst_data keys:
      - monthly_turnover: {YYYY-MM: amount_inr}
      - gstr_3b_tax_paid: {YYYY-MM: amount_inr}
      - gstr_2a_itc_claimed: {YYYY-MM: amount_inr}

    Expected bank_data keys:
      - monthly_credits: {YYYY-MM: amount_inr}
    """
    flags = []
    summary = {
        "gst_turnover_total": 0,
        "bank_credits_total": 0,
        "discrepancy_pct": 0,
        "suspicious_months": [],
    }

    gst_monthly = gst_data.get("monthly_turnover", {})
    bank_monthly = bank_data.get("monthly_credits", {})

    if not gst_monthly or not bank_monthly:
        return flags, summary

    common_months = set(gst_monthly.keys()) & set(bank_monthly.keys())
    if not common_months:
        flags.append("No overlapping months between GST and bank data — cannot cross-verify.")
        return flags, summary

    gst_total = sum(gst_monthly.get(m, 0) for m in common_months)
    bank_total = sum(bank_monthly.get(m, 0) for m in common_months)

    summary["gst_turnover_total"] = gst_total
    summary["bank_credits_total"] = bank_total

    if gst_total > 0:
        discrepancy_pct = abs(bank_total - gst_total) / gst_total * 100
        summary["discrepancy_pct"] = round(discrepancy_pct, 2)

        if discrepancy_pct > 30:
            flags.append(
                f"HIGH DISCREPANCY: Bank credits ({bank_total:,.0f}) vs GST turnover ({gst_total:,.0f}) — "
                f"{discrepancy_pct:.1f}% difference. Possible revenue inflation or circular trading."
            )
        elif discrepancy_pct > 15:
            flags.append(
                f"MODERATE DISCREPANCY: {discrepancy_pct:.1f}% difference between bank credits and GST turnover."
            )

    # Month-level suspicious patterns
    suspicious = []
    for month in sorted(common_months):
        g = gst_monthly.get(month, 0)
        b = bank_monthly.get(month, 0)
        if g > 0:
            month_discrepancy = abs(b - g) / g * 100
            if month_discrepancy > 40:
                suspicious.append({
                    "month": month,
                    "gst_turnover": g,
                    "bank_credits": b,
                    "discrepancy_pct": round(month_discrepancy, 1),
                })
    summary["suspicious_months"] = suspicious
    if suspicious:
        flags.append(
            f"Suspicious discrepancies in {len(suspicious)} month(s): "
            + ", ".join(s["month"] for s in suspicious)
        )

    # ITC anomaly check
    itc_claimed = gst_data.get("gstr_2a_itc_claimed", {})
    tax_paid = gst_data.get("gstr_3b_tax_paid", {})
    for month in set(itc_claimed.keys()) & set(tax_paid.keys()):
        itc = itc_claimed.get(month, 0)
        paid = tax_paid.get(month, 0)
        if paid > 0 and itc / paid > 0.95:
            flags.append(
                f"GSTR-2A vs 3B anomaly in {month}: ITC claimed ({itc:,.0f}) is ≥95% of tax paid ({paid:,.0f}). "
                "Possible inflated input credits."
            )

    return flags, summary
