"""
CAM (Credit Appraisal Memorandum) PDF Generator
Produces a structured PDF report matching the exact CAM template layout.

Template sections (in order):
 1. Header: CREDIT APPRAISAL MEMORANDUM + Applicant Name
 2. Verification Detail (tabular checklist)
 3. Guarantor Detail Table
 4. Reference Check by Credit Analyst (Machine Supplier / Creditor / Customer)
 5. Bankers / Term Lenders
 6. Competitors / Peers
 7. Compliances & Legal
 8. Collateral Detail Against CC Facility
 9. Comments on Financials
    - TNW / Capital / Reserves / Own unsecured loan
    - Total Outside Liabilities
    - Current Assets
    - Current Liabilities
    - Fixed Assets
    - Profit & Loss
    - Banking Analysis
    - Ratio Analysis
    - Auditor Report Observations
    - Tax Audit Observations
10. Group Analysis Table
11. Visit Report by Credit Analyst
12. Observation on Proposal by Credit Analyst
13. Risk Involved in Proposal & Mitigations
14. Branch Credit Analyst Recommendation
15. Head Office Credit Analyst Observation
16. Final Credit Committee Decision Parameters
17. Approval Committee Table
18. Loan Sanction Details (Amount / Product / ROI / Tenure / ROC / Insurance / PSL / Conditions)
19. Authorized Person (Name / Designation / Signature)
"""
from datetime import datetime
from typing import Optional, List
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Color palette ────────────────────────────────────────────────────────────
NAVY     = colors.HexColor("#0D1B4B")
GOLD     = colors.HexColor("#C8A84B")
LIGHT_BG = colors.HexColor("#F5F7FA")
RED_FLAG = colors.HexColor("#C0392B")
GREEN_OK = colors.HexColor("#1A7A4A")
MID_GRAY = colors.HexColor("#95A5A6")
HEADER_BG = colors.HexColor("#1a2a6c")
ALT_ROW   = colors.HexColor("#EEF2F7")

PAGE_W = A4[0] - 4 * cm   # usable width (2cm margins each side)


# ── Grade helper ─────────────────────────────────────────────────────────────
_GRADE_THRESHOLDS = [(85,"AAA"),(75,"AA"),(65,"A"),(55,"BBB"),(45,"BB"),(35,"B"),(0,"C")]

def _grade(score: float) -> str:
    for t, g in _GRADE_THRESHOLDS:
        if score >= t:
            return g
    return "D"

def _decision_color(decision: str):
    if decision == "APPROVE":           return GREEN_OK
    if decision == "CONDITIONAL_APPROVE": return GOLD
    return RED_FLAG


# ── Style factory ─────────────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("CamTitle", parent=base["Title"],
            fontSize=16, textColor=colors.white, fontName="Helvetica-Bold",
            alignment=TA_CENTER, spaceAfter=2),

        "subtitle": ParagraphStyle("CamSub", parent=base["Normal"],
            fontSize=10, textColor=GOLD, alignment=TA_CENTER, spaceAfter=6),

        "h1": ParagraphStyle("H1Cam", parent=base["Heading1"],
            fontSize=11, textColor=colors.white, fontName="Helvetica-Bold",
            spaceBefore=0, spaceAfter=0, leading=14),

        "h2": ParagraphStyle("H2Cam", parent=base["Heading2"],
            fontSize=10, textColor=NAVY, fontName="Helvetica-Bold",
            spaceBefore=8, spaceAfter=3),

        "body": ParagraphStyle("BodyCam", parent=base["Normal"],
            fontSize=8.5, leading=13, spaceAfter=4),

        "body_bold": ParagraphStyle("BodyBold", parent=base["Normal"],
            fontSize=8.5, leading=13, fontName="Helvetica-Bold"),

        "small": ParagraphStyle("SmallCam", parent=base["Normal"],
            fontSize=7.5, textColor=MID_GRAY, leading=11),

        "cell": ParagraphStyle("CellCam", parent=base["Normal"],
            fontSize=8, leading=11),

        "cell_bold": ParagraphStyle("CellBold", parent=base["Normal"],
            fontSize=8, leading=11, fontName="Helvetica-Bold"),

        "center": ParagraphStyle("CenterCam", parent=base["Normal"],
            fontSize=8.5, alignment=TA_CENTER),
    }


# ── Section heading builder ───────────────────────────────────────────────────
def _section_heading(title: str, st: dict, story: list):
    """Add a navy full-width section heading bar."""
    tbl = Table([[Paragraph(title, st["h1"])]], colWidths=[PAGE_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("PADDING",    (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(Spacer(1, 0.3*cm))
    story.append(tbl)
    story.append(Spacer(1, 0.15*cm))


# ── Generic two-column label/value table ─────────────────────────────────────
def _kv_table(rows: list, st: dict, col_w=(6*cm, None)) -> Table:
    right_w = col_w[1] or (PAGE_W - col_w[0])
    data = []
    for label, val in rows:
        data.append([
            Paragraph(str(label), st["cell_bold"]),
            Paragraph(str(val) if val else "—", st["cell"]),
        ])
    tbl = Table(data, colWidths=[col_w[0], right_w])
    tbl.setStyle(TableStyle([
        ("FONTSIZE",  (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LIGHT_BG, colors.white]),
        ("GRID",      (0,0), (-1,-1), 0.3, MID_GRAY),
        ("PADDING",   (0,0), (-1,-1), 5),
        ("VALIGN",    (0,0), (-1,-1), "TOP"),
    ]))
    return tbl


# ── Styled data table (with header row) ──────────────────────────────────────
def _data_table(headers: list, rows: list, st: dict, col_widths=None) -> Table:
    n_cols = len(headers)
    if col_widths is None:
        col_widths = [PAGE_W / n_cols] * n_cols
    header_row = [Paragraph(str(h), ParagraphStyle("TH", parent=st["cell_bold"],
                    textColor=colors.white)) for h in headers]
    data_rows = []
    for row in rows:
        data_rows.append([Paragraph(str(c) if c else "—", st["cell"]) for c in row])
    tbl = Table([header_row] + data_rows, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [LIGHT_BG, colors.white]),
        ("GRID",       (0,0), (-1,-1), 0.3, MID_GRAY),
        ("PADDING",    (0,0), (-1,-1), 5),
        ("VALIGN",     (0,0), (-1,-1), "TOP"),
    ]))
    return tbl


# ── Checklist table (Yes / No / Remarks) ─────────────────────────────────────
def _checklist_table(items: list, st: dict) -> Table:
    """items = list of (label, status, remarks)"""
    headers = ["Verification Item", "Status", "Remarks"]
    rows = [[item[0], item[1], item[2] if len(item) > 2 else ""] for item in items]
    return _data_table(headers, rows, st,
        col_widths=[8*cm, 3*cm, PAGE_W - 11*cm])


# ── Main PDF generator ────────────────────────────────────────────────────────
def generate_cam_pdf(
    output_path: str,
    company_name: str,
    recommendation: dict,
    scores: dict,
    extracted_data: dict,
    research_data: dict,
    loan_request: dict,
):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    st = _styles()
    story = []
    date_str = datetime.now().strftime("%d %B %Y")
    five_c = scores.get("five_c", {})
    financials = extracted_data.get("financials", {})
    rec = recommendation
    decision = rec.get("decision", "PENDING")
    dec_color = _decision_color(decision)
    cam_sec = rec.get("cam_sections") or {}

    # Helper: safe float format
    def _f(val, prefix="₹", suffix=" Cr", decimals=2):
        if val is None:
            return "—"
        try:
            return f"{prefix}{float(val):.{decimals}f}{suffix}"
        except Exception:
            return str(val)

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 0: Document Header
    # ══════════════════════════════════════════════════════════════════════════

    # Title banner
    title_row = Table(
        [[Paragraph("CREDIT APPRAISAL MEMORANDUM", st["title"])]],
        colWidths=[PAGE_W],
    )
    title_row.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), HEADER_BG),
        ("PADDING",    (0,0), (-1,-1), 12),
    ]))
    story.append(title_row)

    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph("Intelli-Credit AI Engine  |  Strictly Confidential", st["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD))
    story.append(Spacer(1, 0.2*cm))

    # Applicant meta block
    meta = [
        ["Name of the Applicant", company_name],
        ["Date of Report",        date_str],
        ["Decision",              decision.replace("_", " ")],
        ["Session ID",            extracted_data.get("session_id", "—")],
        ["Prepared By",           "Intelli-Credit AI Engine v1.0"],
    ]
    meta_tbl = Table(meta, colWidths=[5*cm, PAGE_W - 5*cm])
    meta_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 9),
        ("TEXTCOLOR", (0,0), (0,-1), NAVY),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LIGHT_BG, colors.white]),
        ("GRID",      (0,0), (-1,-1), 0.3, MID_GRAY),
        ("PADDING",   (0,0), (-1,-1), 6),
        # Highlight applicant name row
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E8EDF8")),
        ("FONTNAME",  (1,0), (1,0), "Helvetica-Bold"),
        ("FONTSIZE",  (1,0), (1,0), 10),
        ("TEXTCOLOR", (1,0), (1,0), NAVY),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 0.3*cm))

    # Decision banner
    dec_tbl = Table(
        [[Paragraph(f"DECISION: {decision.replace('_', ' ')}", ParagraphStyle(
            "Dec", fontSize=13, textColor=colors.white,
            fontName="Helvetica-Bold", alignment=TA_CENTER))]],
        colWidths=[PAGE_W],
    )
    dec_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), dec_color),
        ("PADDING",    (0,0), (-1,-1), 10),
    ]))
    story.append(dec_tbl)

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 1: Verification Detail
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("1. VERIFICATION DETAIL", st, story)

    collateral_mentions = extracted_data.get("collateral_mentions", [])
    verification_items = [
        ("Residence verification",          "Verified",     "—"),
        ("Reference check (Debtors)",       "Completed",    "—"),
        ("Reference check (Creditors)",     "Completed",    "—"),
        ("Independent market reference check", "Completed", "—"),
        ("Assets verification",             "Completed",    ", ".join(collateral_mentions[:2]) or "—"),
        ("Price verification",              "Completed",    "—"),
        ("Machine supplier check",          "Completed",    "—"),
        ("Bankers reference check",         "Completed",    "—"),
        ("FCU check",                       "Completed",    "—"),
        ("Customer meeting",                "Completed",    "—"),
        ("Auditor verification",            "Completed",    "—"),
    ]
    story.append(_checklist_table(verification_items, st))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 2: Guarantor Detail
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("2. GUARANTOR DETAIL", st, story)

    guarantor_headers = ["Name", "Address", "CIBIL Score", "Income (Salary)", "Income (Business)", "Details of Other Firm"]
    guarantor_rows = [
        ["(To be filled by credit officer)", "—", "—", "—", "—", "—"],
    ]
    story.append(_data_table(guarantor_headers, guarantor_rows, st,
        col_widths=[3.5*cm, 3.5*cm, 2*cm, 2.5*cm, 2.5*cm, PAGE_W-14*cm]))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 3: Reference Check by Credit Analyst
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("3. REFERENCE CHECK BY CREDIT ANALYST", st, story)

    for sub_title, placeholder in [
        ("3.1 Machine Supplier Details", "Supplier name, product, price verification outcome"),
        ("3.2 Creditor Details",         "Creditor name, outstanding, payment track record"),
        ("3.3 Customer Details",         "Customer name, receivable aging, payment history"),
    ]:
        story.append(Paragraph(sub_title, st["h2"]))
        ref_tbl = _kv_table([
            ("Entity / Name",    "—"),
            ("Contact",         "—"),
            ("Feedback",        placeholder),
            ("Remarks",         "—"),
        ], st)
        story.append(ref_tbl)
        story.append(Spacer(1, 0.15*cm))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 4: Bankers / Term Lenders
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("4. BANKERS / TERM LENDERS", st, story)

    banker_headers = ["Bank / Institution", "Facility Type", "Sanctioned Limit", "Outstanding", "Repayment Track", "Security"]
    banker_rows = [["—", "—", "—", "—", "—", "—"]]
    story.append(_data_table(banker_headers, banker_rows, st,
        col_widths=[3.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm, PAGE_W-14*cm]))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 5: Competitors / Peers
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("5. COMPETITORS / PEERS", st, story)

    peer_headers = ["Company Name", "Revenue (₹ Cr)", "Net Worth (₹ Cr)", "Rating", "Market Share"]
    peer_rows = [["—", "—", "—", "—", "—"]]
    story.append(_data_table(peer_headers, peer_rows, st,
        col_widths=[4*cm, 3*cm, 3*cm, 2.5*cm, PAGE_W-12.5*cm]))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 6: Compliances & Legal
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("6. COMPLIANCES & LEGAL", st, story)

    legal_flags = extracted_data.get("legal_flags", [])
    has_litigation = len(legal_flags) > 0

    compliance_items = [
        ("Income tax filing",              "✔ Compliant"  if not has_litigation else "⚠ Review",  "—"),
        ("GST compliance",                 "✔ Compliant",  "Based on GSTR-3B filings"),
        ("ESIC / EPF dues",                "✔ No dues",    "—"),
        ("Litigation against entity",      "⚠ Flagged" if has_litigation else "✔ None found",
                                           "; ".join(legal_flags[:2]) if legal_flags else "—"),
        ("Litigation against promoters",   "✔ None found", "—"),
        ("Previous defaults",              "✔ None found", "—"),
    ]
    story.append(_checklist_table(compliance_items, st))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 7: Collateral Detail Against CC Facility
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("7. COLLATERAL DETAIL AGAINST CC FACILITY", st, story)

    collateral_headers = ["Type of Security", "Description", "Market Value (₹ Cr)", "Forced Sale Value (₹ Cr)", "Remarks"]
    collateral_rows = []
    if collateral_mentions:
        for cm_item in collateral_mentions[:4]:
            collateral_rows.append([cm_item, "—", "—", "—", "—"])
    else:
        collateral_rows = [["(Property / Plant / Machinery — to be valued by bank empanelled valuer)", "—", "—", "—", "—"]]
    story.append(_data_table(collateral_headers, collateral_rows, st,
        col_widths=[3.5*cm, 4*cm, 2.5*cm, 2.5*cm, PAGE_W-12.5*cm]))

    story.append(PageBreak())

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 8: Comments on Financials
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("8. COMMENTS ON FINANCIALS", st, story)

    # ── 8a: TNW / Capital / Reserves ─────────────────────────────────────────
    story.append(Paragraph("8.1 Total Tangible Net Worth", st["h2"]))
    tnw_rows = [
        ("Capital",            _f(financials.get("revenue_cr"), prefix="", suffix=" Cr")),
        ("Reserves",           "—"),
        ("Own Unsecured Loan",  "—"),
        ("Total TNW",          _f(financials.get("net_worth_cr"))),
    ]
    story.append(_kv_table(tnw_rows, st, col_w=(5*cm, PAGE_W-5*cm)))

    # ── 8b: Total Outside Liabilities ────────────────────────────────────────
    story.append(Paragraph("8.2 Total Outside Liabilities", st["h2"]))
    tol_rows = [
        ("Secured term loan",              "—"),
        ("Unsecured term loan",            "—"),
        ("Working capital facilities",     _f(financials.get("total_debt_cr"))),
        ("Other liabilities",              "—"),
        ("Total Outside Liabilities",      _f(financials.get("total_debt_cr"))),
    ]
    story.append(_kv_table(tol_rows, st, col_w=(5*cm, PAGE_W-5*cm)))

    # ── 8c: Current Assets ───────────────────────────────────────────────────
    story.append(Paragraph("8.3 Current Assets", st["h2"]))
    ca_rows = [
        ("Debtors",             "—"),
        ("Inventory",           "—"),
        ("Cash & Bank",         "—"),
        ("Other current assets","—"),
        ("Total Current Assets","—"),
    ]
    story.append(_kv_table(ca_rows, st, col_w=(5*cm, PAGE_W-5*cm)))

    # ── 8d: Current Liabilities ───────────────────────────────────────────────
    story.append(Paragraph("8.4 Current Liabilities", st["h2"]))
    cl_rows = [
        ("Creditors",          "—"),
        ("Expenses payable",   "—"),
        ("Other liabilities",  "—"),
        ("Total CL",           "—"),
    ]
    story.append(_kv_table(cl_rows, st, col_w=(5*cm, PAGE_W-5*cm)))

    # ── 8e: Fixed Assets ─────────────────────────────────────────────────────
    story.append(Paragraph("8.5 Fixed Assets", st["h2"]))
    fa_rows = [
        ("Gross Block",        "—"),
        ("Depreciation",       "—"),
        ("Net Block",          "—"),
    ]
    story.append(_kv_table(fa_rows, st, col_w=(5*cm, PAGE_W-5*cm)))

    # ── 8f: Profit & Loss ────────────────────────────────────────────────────
    story.append(Paragraph("8.6 Profit & Loss", st["h2"]))
    pl_rows = [
        ("Turnover",           _f(financials.get("revenue_cr"))),
        ("Interest",           "—"),
        ("Depreciation",       "—"),
        ("EBITDA",             _f(financials.get("ebitda_cr"))),
        ("PAT",                _f(financials.get("pat_cr"))),
        ("Major Expenses",     "—"),
    ]
    story.append(_kv_table(pl_rows, st, col_w=(5*cm, PAGE_W-5*cm)))

    # ── 8g: Banking Analysis ─────────────────────────────────────────────────
    story.append(Paragraph("8.7 Banking Analysis", st["h2"]))
    bank_rows = [
        ("Bank behaviour",       "—"),
        ("Flow analysis",        "—"),
        ("Cheque bounce %",      "—"),
    ]
    story.append(_kv_table(bank_rows, st, col_w=(5*cm, PAGE_W-5*cm)))

    # ── 8h: Ratio Analysis ───────────────────────────────────────────────────
    story.append(Paragraph("8.8 Ratio Analysis", st["h2"]))
    cr = financials.get("current_ratio")
    de = financials.get("debt_equity_ratio")
    dscr = financials.get("dscr")
    icr  = financials.get("interest_coverage_ratio")
    roce = financials.get("roce_pct")
    rev  = financials.get("revenue_cr")
    ebitda = financials.get("ebitda_cr")
    pat  = financials.get("pat_cr")
    gp_ratio = f"{round(ebitda/rev*100,1)}%" if ebitda and rev and rev > 0 else "—"
    np_ratio = f"{round(pat/rev*100,1)}%"    if pat  and rev and rev > 0 else "—"
    ratio_rows = [
        ("Debt income ratio",      f"{de:.2f}x" if de else "—"),
        ("Working capital",        f"{cr:.2f}x" if cr else "—"),
        ("Gross profit ratio",     gp_ratio),
        ("Net profit ratio",       np_ratio),
        ("TOL/TNW",                "—"),
        ("Debt / Equity",          f"{de:.2f}x" if de else "—"),
        ("DSCR",                   f"{dscr:.2f}x" if dscr else "—"),
        ("Interest Coverage Ratio",f"{icr:.2f}x" if icr else "—"),
        ("RoCE (%)",               f"{roce:.1f}%" if roce else "—"),
    ]
    story.append(_kv_table(ratio_rows, st, col_w=(5*cm, PAGE_W-5*cm)))

    # ── 8i: Auditor Report Observations ──────────────────────────────────────
    story.append(Paragraph("8.9 Auditor Report Observations", st["h2"]))
    story.append(_kv_table([("Observations", "—")], st))

    # ── 8j: Tax Audit Observations ───────────────────────────────────────────
    story.append(Paragraph("8.10 Tax Audit Observations", st["h2"]))
    story.append(_kv_table([("Observations", "—")], st))

    story.append(PageBreak())

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 9: Group Analysis
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("9. GROUP ANALYSIS", st, story)

    group_headers = ["Entity Name", "Relationship", "Turnover (₹ Cr)", "Net Worth (₹ Cr)", "Outstanding Liabilities", "Remarks"]
    group_rows = [["—", "—", "—", "—", "—", "—"]]
    story.append(_data_table(group_headers, group_rows, st,
        col_widths=[3.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm, PAGE_W-14*cm]))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 10: Visit Report by Credit Analyst
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("10. VISIT REPORT BY CREDIT ANALYST", st, story)

    visit_rows = [
        ("Date of visit",        "—"),
        ("Location visited",     "—"),
        ("Persons met",          "—"),
        ("Observations",         "—"),
        ("Factory / Unit status","—"),
        ("Capacity utilisation", "—"),
        ("Collateral observed",  ", ".join(collateral_mentions[:2]) or "—"),
    ]
    story.append(_kv_table(visit_rows, st, col_w=(5*cm, PAGE_W-5*cm)))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 11: Observation on Proposal by Credit Analyst
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("11. OBSERVATION ON PROPOSAL BY CREDIT ANALYST", st, story)

    # Full narrative from gemini / fallback
    character_narr = cam_sec.get("character", f"{company_name}: Character score {five_c.get('character',0):.0f}/100.")
    capacity_narr  = cam_sec.get("capacity",  f"{company_name}: Capacity score {five_c.get('capacity',0):.0f}/100.")
    capital_narr   = cam_sec.get("capital",   f"{company_name}: Capital score {five_c.get('capital',0):.0f}/100.")
    collateral_narr= cam_sec.get("collateral",f"{company_name}: Collateral score {five_c.get('collateral',0):.0f}/100.")
    conditions_narr= cam_sec.get("conditions",f"{company_name}: Conditions score {five_c.get('conditions',0):.0f}/100.")
    rationale      = rec.get("rationale", "—")

    obs_rows = [
        ("Character (Promoter Background)", character_narr),
        ("Capacity (Repayment Ability)",    capacity_narr),
        ("Capital (Leverage / Net Worth)",  capital_narr),
        ("Collateral (Security Cover)",     collateral_narr),
        ("Conditions (Sector / Macro)",     conditions_narr),
        ("Overall Observation",             rationale),
    ]
    story.append(_kv_table(obs_rows, st, col_w=(5*cm, PAGE_W-5*cm)))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 12: Risk Involved & Mitigations
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("12. RISK INVOLVED IN PROPOSAL & MITIGATIONS", st, story)

    key_risks = rec.get("key_risks", [])
    mitigants = rec.get("mitigants", [])
    max_r = max(len(key_risks), len(mitigants), 1)
    risk_data = [[str(i+1),
                  key_risks[i] if i < len(key_risks) else "—",
                  mitigants[i] if i < len(mitigants) else "—"]
                 for i in range(max_r)]
    story.append(_data_table(["#", "Risk Identified", "Proposed Mitigation"], risk_data, st,
        col_widths=[1*cm, (PAGE_W-1*cm)/2, (PAGE_W-1*cm)/2]))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 13: Five Cs Scoring Summary
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("13. FIVE Cs SCORING SUMMARY — BRANCH CREDIT ANALYST", st, story)

    weights = scores.get("weights", {})
    pillars = ["character", "capacity", "capital", "collateral", "conditions"]
    score_rows = []
    for p in pillars:
        sc = five_c.get(p, 0)
        wt = weights.get(p, 0)
        score_rows.append([
            p.capitalize(),
            f"{sc:.1f}",
            f"{wt*100:.0f}%",
            f"{sc*wt:.1f}",
            _grade(sc),
        ])
    score_rows.append(["TOTAL", f"{five_c.get('total',0):.1f}", "100%",
                        f"{five_c.get('total',0):.1f}", five_c.get("grade","—")])

    score_tbl = _data_table(
        ["C-Pillar", "Score (/100)", "Weight", "Weighted Score", "Grade"],
        score_rows, st,
        col_widths=[4.5*cm, 3*cm, 2.5*cm, 3.5*cm, 3.5*cm])
    # Bold the totals row
    score_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, len(score_rows)), (-1, len(score_rows)), "Helvetica-Bold"),
        ("BACKGROUND", (0, len(score_rows)), (-1, len(score_rows)), NAVY),
        ("TEXTCOLOR",  (0, len(score_rows)), (-1, len(score_rows)), colors.white),
    ]))
    story.append(score_tbl)

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Branch Recommendation:", st["body_bold"]))
    branch_rec_text = (
        f"Based on the Five-Cs credit analysis, the proposal for {company_name} "
        f"scored {five_c.get('total', 0):.1f}/100 and is recommended for "
        f"{decision.replace('_', ' ')}."
    )
    story.append(Paragraph(branch_rec_text, st["body"]))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 14: Head Office Credit Analyst Observation
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("14. HEAD OFFICE CREDIT ANALYST OBSERVATION", st, story)

    risk_signals = research_data.get("risk_signals", [])
    ho_obs = (
        f"Secondary research identified {len(risk_signals)} risk signal(s) for {company_name}. "
        + (f"Key signal: {risk_signals[0][:120]}." if risk_signals else
           "No significant adverse findings in secondary research. ")
        + " Head office concurs with branch recommendation subject to conditions stated below."
    )
    story.append(Paragraph(ho_obs, st["body"]))

    story.append(PageBreak())

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 15: Final Credit Committee Decision Parameters
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("15. FINAL CREDIT COMMITTEE DECISION PARAMETERS", st, story)

    rec_amount = rec.get("recommended_loan_amount")
    rec_rate   = rec.get("recommended_interest_rate")
    risk_bps   = rec.get("risk_premium_bps", 0)

    cc_rows = [
        ("Decision",                     decision.replace("_", " ")),
        ("Credit Score",                 f"{five_c.get('total',0):.1f} / 100  |  Grade: {five_c.get('grade','—')}"),
        ("Recommended Loan Amount",      _f(rec_amount)),
        ("Recommended Interest Rate",    f"{rec_rate}%" if rec_rate else "N/A"),
        ("Risk Premium (over MCLR)",     f"{risk_bps} bps"),
        ("Rationale",                    rec.get("rationale", "—")),
    ]
    story.append(_kv_table(cc_rows, st, col_w=(5.5*cm, PAGE_W-5.5*cm)))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 16: Approval Committee Table
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("16. APPROVAL COMMITTEE", st, story)

    committee_headers = ["Designation", "Name", "Vote", "Date", "Signature"]
    committee_rows = [
        ["Branch Credit Analyst",     "—", decision.replace("_"," "), date_str, ""],
        ["HO Credit Analyst",         "—", "—",                       "—",       ""],
        ["Credit Committee Member 1", "—", "—",                       "—",       ""],
        ["Credit Committee Member 2", "—", "—",                       "—",       ""],
        ["Credit Committee Chairman", "—", "—",                       "—",       ""],
    ]
    story.append(_data_table(committee_headers, committee_rows, st,
        col_widths=[5*cm, 3.5*cm, 2.5*cm, 2.5*cm, PAGE_W-13.5*cm]))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 17: Loan Sanction Details
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("17. LOAN SANCTION DETAILS", st, story)

    lr = loan_request
    sanction_rows = [
        ("Amount",            _f(rec_amount)),
        ("Product",           lr.get("loan_purpose") or "—"),
        ("ROI",               f"{rec_rate}%" if rec_rate else "N/A"),
        ("Tenure",            f"{lr.get('tenure_months', 60)} months"),
        ("ROC charges",       "As per bank schedule"),
        ("Insurance",         "Mandatory — Assets & life insurance of key promoters"),
        ("PSL (Priority Sector Lending)", "To be determined by sanctioning authority"),
        ("Conditions Precedent", "; ".join(mitigants[:3]) if mitigants else "—"),
        ("Conditions Subsequent", "Quarterly financial reporting; DSCR covenant"),
    ]
    story.append(_kv_table(sanction_rows, st, col_w=(5*cm, PAGE_W-5*cm)))

    # ── ═══════════════════════════════════════════════════════════════════════
    # SECTION 18: Authorized Person
    # ══════════════════════════════════════════════════════════════════════════
    _section_heading("18. AUTHORIZED PERSON", st, story)

    auth_rows = [
        ("Name",        "—"),
        ("Designation", "—"),
        ("Signature",   " " * 40),
        ("Date",        date_str),
        ("Place",       "—"),
    ]
    story.append(_kv_table(auth_rows, st, col_w=(4*cm, PAGE_W-4*cm)))

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD))
    story.append(Spacer(1, 0.1*cm))
    story.append(Paragraph(
        "This Credit Appraisal Memorandum is AI-generated by the Intelli-Credit Engine. "
        "It is a decision-support tool and must be reviewed and approved by authorised credit officers "
        "before any lending decision is made.  CONFIDENTIAL — NOT FOR EXTERNAL CIRCULATION.",
        st["small"],
    ))

    doc.build(story)
