"""
PDF Parser Service
Three-tier extraction cascade — in order of quality:
  1. pdfplumber  — best for structured Indian CA-certified financial statements
  2. pypdf       — pure-Python, good for searchable PDFs
  3. PyPDF2      — legacy fallback

Handles both text-native and lightly structured PDFs.
Scanned/image-only PDFs would require OCR (not included in base version).
"""
from pathlib import Path

# ── Tier 1: pdfplumber ──────────────────────────────────────────────────────
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

# ── Tier 2: pypdf ───────────────────────────────────────────────────────────
try:
    from pypdf import PdfReader as NewPdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# ── Tier 3: PyPDF2 (legacy) ─────────────────────────────────────────────────
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False


def _extract_with_pdfplumber(file_path: str) -> str:
    """
    pdfplumber extracts text page-by-page and also handles tables.
    For Indian financial statements with tabular data, this yields the
    best quality raw text for Gemini to parse.
    """
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # Extract regular text
            page_text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            text_parts.append(page_text)
            # Also extract any tables (convert to simple text grid)
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row:
                        row_text = " | ".join(str(cell) if cell else "" for cell in row)
                        if row_text.strip(" |"):
                            text_parts.append(row_text)
    return "\n".join(text_parts)


def parse_pdf(file_path: str) -> str:
    """
    Extract full text from a PDF file.
    Cascade: pdfplumber → pypdf → PyPDF2
    """
    # ── Tier 1: pdfplumber ──────────────────────────────────────────────────
    if HAS_PDFPLUMBER:
        try:
            text = _extract_with_pdfplumber(file_path)
            if text.strip():
                return text
        except Exception:
            pass  # fall through to next tier

    # ── Tier 2: pypdf ───────────────────────────────────────────────────────
    if HAS_PYPDF:
        try:
            reader = NewPdfReader(file_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            if text.strip():
                return text
        except Exception:
            pass

    # ── Tier 3: PyPDF2 ──────────────────────────────────────────────────────
    if HAS_PYPDF2:
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                return text
        except Exception as e:
            raise RuntimeError(f"All PDF parsers failed. Last error: {e}")

    raise RuntimeError(
        "No PDF parsing library is installed. "
        "Run: pip install pdfplumber pypdf PyPDF2"
    )


def count_pages(file_path: str) -> int:
    """Return the number of pages in a PDF."""
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(file_path) as pdf:
                return len(pdf.pages)
        except Exception:
            pass
    if HAS_PYPDF:
        try:
            return len(NewPdfReader(file_path).pages)
        except Exception:
            pass
    if HAS_PYPDF2:
        try:
            with open(file_path, "rb") as f:
                return len(PyPDF2.PdfReader(f).pages)
        except Exception:
            pass
    return 0
