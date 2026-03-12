"""
GSTR-3B Extractor
Scans raw text extracted from a PDF (all pages) and detects GST monthly tables.
Returns structured JSON matching:
  {
    "monthly_turnover":   {"YYYY-MM": amount, ...},
    "gstr_3b_tax_paid":   {"YYYY-MM": amount, ...},
    "gstr_2a_itc_claimed": {"YYYY-MM": amount, ...}
  }

Detection strategy:
  1. First look for keyword "GSTR-3B" / "GST MONTHLY" / "Taxable Turnover" near month names.
  2. Parse rows that contain a month label (e.g. "Jan 2024" or "January 2024" or "01/2024")
     followed by numeric values.
  3. Map column positions to turnover / tax paid / ITC heuristically.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Month name → zero-padded month number
_MONTH_MAP = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}

# Keywords that indicate a GST/GSTR-3B section
_GST_SECTION_KEYWORDS = [
    r"gstr[\s\-]?3b",
    r"gst\s+monthly",
    r"taxable\s+turnover",
    r"gst\s+turnover",
    r"igst",
    r"cgst",
    r"sgst",
    r"input\s+tax\s+credit",
    r"itc\s+claimed",
    r"gstr[\s\-]?2a",
]

# Regex to detect a month row like "Jan 2024", "january 2024", "01/2024", "2024-01"
_MONTH_ROW_RE = re.compile(
    r"(?:"
    r"(?P<named>(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[\s\-,\.]*(?P<year1>\d{4}))"
    r"|"
    r"(?P<yymm>(?P<year2>\d{4})[\-/](?P<month2>\d{1,2}))"
    r"|"
    r"(?P<mmyy>(?P<month3>\d{1,2})[/\-](?P<year3>\d{4}))"
    r")",
    re.IGNORECASE,
)

# Numbers: Indian-formatted amounts like 1,00,000 or 100000 or 10.50
_NUMBER_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")


def _parse_indian_number(s: str) -> Optional[float]:
    """Convert Indian-formatted numeric string to float."""
    try:
        cleaned = s.replace(",", "").strip()
        if not cleaned:
            return None
        return float(cleaned)
    except ValueError:
        return None


def _month_label_to_key(match: re.Match) -> Optional[str]:
    """Convert a regex month match to YYYY-MM key."""
    try:
        if match.group("named"):
            # e.g. "Jan 2024"
            raw = match.group("named")
            year = match.group("year1")
            # Extract first word as month name
            month_name = re.split(r"[\s\-,\.]", raw.strip())[0].lower()
            mm = _MONTH_MAP.get(month_name)
            if mm and year:
                return f"{year}-{mm}"
        elif match.group("yymm"):
            year = match.group("year2")
            mm = match.group("month2").zfill(2)
            return f"{year}-{mm}"
        elif match.group("mmyy"):
            year = match.group("year3")
            mm = match.group("month3").zfill(2)
            return f"{year}-{mm}"
    except Exception:
        pass
    return None


def _is_gst_section(text_chunk: str) -> bool:
    """Return True if the given text chunk contains GST-related keywords."""
    lower = text_chunk.lower()
    for kw in _GST_SECTION_KEYWORDS:
        if re.search(kw, lower):
            return True
    return False


def extract_gst_from_text(full_text: str) -> dict:
    """
    Primary entry point.
    Scans full_text for GSTR-3B monthly data and returns structured dict.
    Returns empty dicts if nothing found.
    """
    result = {
        "monthly_turnover": {},
        "gstr_3b_tax_paid": {},
        "gstr_2a_itc_claimed": {},
    }

    if not full_text or not full_text.strip():
        return result

    lines = full_text.splitlines()

    # ── Step 1: Find which lines are in a GST section ─────────────────────────
    # We look for a window of up to 80 lines after a GST keyword match
    gst_windows = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_gst_section(line):
            # Collect a window: from i to i+80 (or end)
            end = min(i + 80, len(lines))
            gst_windows.append((i, end))
            i = end  # skip ahead to avoid overlap
        else:
            i += 1

    # If no window detected, scan the ENTIRE text (the table might exist standalone)
    if not gst_windows:
        # Try whole document but only if it contains at least some month patterns
        sample = " ".join(lines)
        month_hits = _MONTH_ROW_RE.findall(sample)
        if len(month_hits) >= 3:
            gst_windows = [(0, len(lines))]
        else:
            return result

    # ── Step 2: For each window, parse month rows ────────────────────────────
    # We accumulate per-month lists of numbers, then assign columns
    month_rows: dict[str, list[list[float]]] = {}

    for start, end in gst_windows:
        window_lines = lines[start:end]
        for line in window_lines:
            month_match = _MONTH_ROW_RE.search(line)
            if not month_match:
                continue
            ym_key = _month_label_to_key(month_match)
            if not ym_key:
                continue

            # Extract all numbers from this line (excluding the year/month itself)
            # Remove the matched month portion first
            line_without_month = line[month_match.end():]
            numbers_raw = _NUMBER_RE.findall(line_without_month)
            numbers = []
            for nr in numbers_raw:
                val = _parse_indian_number(nr)
                if val is not None and val > 0:
                    numbers.append(val)

            if numbers:
                if ym_key not in month_rows:
                    month_rows[ym_key] = []
                month_rows[ym_key].append(numbers)

    if not month_rows:
        return result

    # ── Step 3: Determine column assignment heuristically ───────────────────
    # We look at the header lines in the windows to figure out column order.
    # Common patterns:
    #   Col 0: Taxable Turnover
    #   Col 1: IGST / Total tax paid
    #   Col 2: CGST paid
    #   Col 3: SGST paid
    #   Col 4: ITC claimed
    # Fallback: col0=turnover, col1=tax, col2=itc

    # Try to detect column headers
    col_order = _detect_column_order(lines, gst_windows)

    for ym_key, rows_list in month_rows.items():
        # Use the row with the most numbers (most likely the data row)
        best_row = max(rows_list, key=len) if rows_list else []

        if not best_row:
            continue

        turnover = None
        tax_paid = None
        itc = None

        if col_order:
            for col_idx, col_type in enumerate(col_order):
                if col_idx >= len(best_row):
                    break
                val = best_row[col_idx]
                if col_type == "turnover" and turnover is None:
                    turnover = val
                elif col_type == "tax" and tax_paid is None:
                    tax_paid = val
                elif col_type == "itc" and itc is None:
                    itc = val
        else:
            # Generic fallback
            if len(best_row) >= 1:
                turnover = best_row[0]
            if len(best_row) >= 2:
                # If we have 4+ cols, col 1,2,3 are usually IGST/CGST/SGST
                # and last col is ITC. Sum IGST+CGST+SGST for tax_paid.
                if len(best_row) >= 4:
                    tax_paid = sum(best_row[1:4])
                    if len(best_row) >= 5:
                        itc = best_row[4]
                else:
                    tax_paid = best_row[1]
                    if len(best_row) >= 3:
                        itc = best_row[2]

        if turnover:
            result["monthly_turnover"][ym_key] = turnover
        if tax_paid:
            result["gstr_3b_tax_paid"][ym_key] = tax_paid
        if itc:
            result["gstr_2a_itc_claimed"][ym_key] = itc

    logger.info(
        f"GST extraction: {len(result['monthly_turnover'])} months detected. "
        f"Keys: {sorted(result['monthly_turnover'].keys())}"
    )
    return result


def _detect_column_order(lines: list, gst_windows: list) -> list:
    """
    Scan header lines in GST windows to infer column order.
    Returns a list like ["turnover", "tax", "tax", "tax", "itc"] or []
    """
    header_keywords = {
        "taxable": "turnover",
        "turnover": "turnover",
        "igst": "tax",
        "cgst": "tax",
        "sgst": "tax",
        "tax paid": "tax",
        "total tax": "tax",
        "itc": "itc",
        "input tax credit": "itc",
        "credit claimed": "itc",
        "2a": "itc",
    }

    for start, end in gst_windows:
        # Look at the first 10 lines of each window for headers
        for line in lines[start: min(start + 10, end)]:
            lower = line.lower()
            # Skip if this line contains month patterns (it's a data row)
            if _MONTH_ROW_RE.search(line):
                continue
            # Check if line has multiple keyword hits
            cols = []
            # Split by pipes or multiple spaces as column separators
            parts = re.split(r"\|{1,}|\s{2,}", lower)
            col_found = False
            for part in parts:
                part = part.strip()
                matched = False
                for kw, col_type in header_keywords.items():
                    if kw in part:
                        cols.append(col_type)
                        matched = True
                        col_found = True
                        break
                if not matched and col_found:
                    # A column with no keyword = might be a numeric/date col, skip
                    pass
            if len(cols) >= 2:
                return cols

    return []
