"""
Basic deterministic rules: invalid_date and arithmetic_error.

Each rule accepts:
  - pages: list of page dicts from parse_documents()["pages"]

Returns a list of Finding objects.
"""
import re
from datetime import datetime
from typing import Any

from src.models import Finding

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_RE_DATE   = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
_RE_INV_NO = re.compile(r"(?:Invoice No|DN No|DEBIT NOTE No)[:\s]*\n([\w-]+)", re.MULTILINE)

# Full tax block: line_items_total → Subtotal(=CGST) → CGST(=SGST) → SGST(=GRAND) → GRAND TOTAL
# Layout: ■ITEMS\nSubtotal:\n■CGST\nCGST:\n■SGST\nSGST:\n■GRAND\nGRAND TOTAL:
_RE_TAX_BLOCK = re.compile(
    r"■([\d,]+\.\d{2})\nSubtotal:\n■([\d,]+\.\d{2})\nCGST:\n■([\d,]+\.\d{2})\nSGST:\n■([\d,]+\.\d{2})\nGRAND TOTAL:",
    re.MULTILINE,
)

_TOLERANCE = 1.0   # rupees — differences within this are floating-point rounding


def _parse_amount(raw: str) -> float:
    return float(raw.replace(",", ""))


def _doc_ref(text: str) -> str:
    m = _RE_INV_NO.search(text)
    return m.group(1).strip() if m else ""


def _finding_id(category: str, page: int, seq: list[int]) -> str:
    seq[0] += 1
    return f"{category[:4].upper()}-{page:04d}-{seq[0]:03d}"


# ---------------------------------------------------------------------------
# Rule 1: invalid_date
# ---------------------------------------------------------------------------
def check_invalid_date(pages: list[dict[str, Any]]) -> list[Finding]:
    """
    Flag dates in DD/MM/YYYY format that are impossible calendar dates.
    Examples: 30/02/2025, 32/01/2025, 15/13/2025.
    """
    findings: list[Finding] = []
    seq = [0]

    for page in pages:
        text = page["text"]
        doc_ref = _doc_ref(text)

        for match in _RE_DATE.finditer(text):
            raw_date = match.group(1)
            try:
                datetime.strptime(raw_date, "%d/%m/%Y")
            except ValueError:
                findings.append(Finding(
                    finding_id=_finding_id("invalid_date", page["page_number"], seq),
                    category="invalid_date",
                    pages=[page["page_number"]],
                    document_refs=[doc_ref],
                    description=(
                        f"Date '{raw_date}' on page {page['page_number']} "
                        f"is not a valid calendar date."
                    ),
                    reported_value=raw_date,
                    correct_value=None,
                    confidence=0.99,
                ))

    return findings


# ---------------------------------------------------------------------------
# Rule 2: arithmetic_error
# ---------------------------------------------------------------------------
def check_arithmetic_error(pages: list[dict[str, Any]]) -> list[Finding]:
    """
    Flag invoice pages where: line_items_total + CGST + SGST ≠ GRAND TOTAL.

    Invoice tax block layout (on continued pages):
        ■<line_items_total>
        Subtotal:
        ■<CGST>
        CGST:
        ■<SGST>
        SGST:
        ■<GRAND_TOTAL>
        GRAND TOTAL:

    Flags only when the difference exceeds ₹1 (rounding tolerance).
    """
    findings: list[Finding] = []
    seq = [0]

    for page in pages:
        text = page["text"]
        doc_ref = _doc_ref(text)

        for m in _RE_TAX_BLOCK.finditer(text):
            items = _parse_amount(m.group(1))
            cgst  = _parse_amount(m.group(2))
            sgst  = _parse_amount(m.group(3))
            grand = _parse_amount(m.group(4))

            expected = round(items + cgst + sgst, 2)
            diff = abs(expected - grand)

            if diff > _TOLERANCE:
                findings.append(Finding(
                    finding_id=_finding_id("arithmetic_error", page["page_number"], seq),
                    category="arithmetic_error",
                    pages=[page["page_number"]],
                    document_refs=[doc_ref],
                    description=(
                        f"Grand total ₹{grand:,.2f} on page {page['page_number']} "
                        f"does not match line items + taxes "
                        f"(₹{items:,.2f} + ₹{cgst:,.2f} + ₹{sgst:,.2f} = ₹{expected:,.2f}). "
                        f"Difference: ₹{diff:,.2f}."
                    ),
                    reported_value=f"{grand:.2f}",
                    correct_value=f"{expected:.2f}",
                    confidence=0.95,
                ))

    return findings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run_basic_rules(pages: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_invalid_date(pages))
    findings.extend(check_arithmetic_error(pages))
    return findings
