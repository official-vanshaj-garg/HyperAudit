"""
Cross-document rules: anomalies that require comparing references across pages.

Each rule accepts:
  - pages: list of page dicts from parse_documents()["pages"]

Returns a list of Finding objects.
"""
import re
from collections import defaultdict
from typing import Any

from src.models import Finding

_RE_PO_NUMBER  = re.compile(r"PO Number:\s*\n(PO-[\d-]+)", re.MULTILINE)
_RE_PO_REF     = re.compile(r"PO Reference:\s*\n(PO-[\d-]+)", re.MULTILINE)
_RE_INV_NO     = re.compile(r"Invoice No:\s*\n(INV-[\w-]+)", re.MULTILINE)
_RE_PO_VENDOR  = re.compile(r"VENDOR\s*\nName:\s*\n(.+)", re.MULTILINE)
_RE_PO_TOTAL   = re.compile(r"TOTAL:\s*\n[^\d]*([\d,]+\.\d{2})", re.MULTILINE)
_RE_INV_VENDOR = re.compile(r"VENDOR DETAILS\s*\nName:\s*\n(.+)", re.MULTILINE)
_RE_GRAND      = re.compile(r"([\d,]+\.\d{2})\nGRAND TOTAL:", re.MULTILINE)

# Invoice total must exceed PO total by this fraction to be flagged
_OVERRUN_THRESHOLD = 0.20   # 20%


def _parse_amount(raw: str) -> float:
    return float(raw.replace(",", ""))


def _finding_id_phantom(page: int, seq: list[int]) -> str:
    seq[0] += 1
    return f"PHPO-{page:04d}-{seq[0]:03d}"


def _finding_id_mismatch(page: int, seq: list[int]) -> str:
    seq[0] += 1
    return f"POIM-{page:04d}-{seq[0]:03d}"


# ---------------------------------------------------------------------------
# Rule: phantom_po_reference
# ---------------------------------------------------------------------------
def check_phantom_po_reference(pages: list[dict[str, Any]]) -> list[Finding]:
    """
    Flag invoices that reference a PO ID that does not exist anywhere in the bundle.
    """
    known_po_ids: set[str] = set()
    for page in pages:
        if page["text"].strip().startswith("PURCHASE ORDER"):
            m = _RE_PO_NUMBER.search(page["text"])
            if m:
                known_po_ids.add(m.group(1))

    findings: list[Finding] = []
    seq = [0]
    seen_phantom: set[str] = set()

    for page in pages:
        text = page["text"]
        m_po = _RE_PO_REF.search(text)
        if not m_po:
            continue

        po_id = m_po.group(1)
        if po_id in known_po_ids or po_id in seen_phantom:
            continue

        seen_phantom.add(po_id)
        inv_m = _RE_INV_NO.search(text)
        inv_ref = inv_m.group(1) if inv_m else ""

        findings.append(Finding(
            finding_id=_finding_id_phantom(page["page_number"], seq),
            category="phantom_po_reference",
            pages=[page["page_number"]],
            document_refs=[inv_ref] if inv_ref else [],
            description=(
                f"Invoice on page {page['page_number']} references '{po_id}' "
                f"but no matching Purchase Order document exists in the bundle."
            ),
            reported_value=po_id,
            correct_value="",
            confidence=0.90,
        ))

    return findings


# ---------------------------------------------------------------------------
# Rule: po_invoice_mismatch
# ---------------------------------------------------------------------------
def check_po_invoice_mismatch(pages: list[dict[str, Any]]) -> list[Finding]:
    """
    Flag invoices whose GRAND TOTAL exceeds the referenced PO TOTAL by more
    than 20%, where only one unique invoice references that PO.

    This guards against false positives from legitimate multi-invoice POs
    (where each invoice covers a portion of the PO value).
    """
    # Pass 1: build PO map
    po_map: dict[str, dict[str, Any]] = {}
    for page in pages:
        if not page["text"].strip().startswith("PURCHASE ORDER"):
            continue
        m_id = _RE_PO_NUMBER.search(page["text"])
        m_v  = _RE_PO_VENDOR.search(page["text"])
        m_t  = _RE_PO_TOTAL.search(page["text"])
        if m_id and m_t:
            po_map[m_id.group(1)] = {
                "vendor": m_v.group(1).strip() if m_v else "",
                "total":  _parse_amount(m_t.group(1)),
                "page":   page["page_number"],
            }

    # Pass 2: collect invoice totals per PO (deduplicated by invoice ID)
    # Structure: po_id -> {inv_id: (inv_total, page_number)}
    po_invoices: dict[str, dict[str, tuple[float, int]]] = defaultdict(dict)
    for page in pages:
        m_ref = _RE_PO_REF.search(page["text"])
        if not m_ref:
            continue
        po_id = m_ref.group(1)
        if po_id not in po_map:
            continue
        m_g  = _RE_GRAND.search(page["text"])
        m_in = _RE_INV_NO.search(page["text"])
        if not m_g or not m_in:
            continue
        inv_id    = m_in.group(1)
        inv_total = _parse_amount(m_g.group(1))
        # Keep first occurrence of each invoice ID
        if inv_id not in po_invoices[po_id]:
            po_invoices[po_id][inv_id] = (inv_total, page["page_number"])

    # Pass 3: flag POs with a single invoice that overruns by > threshold
    findings: list[Finding] = []
    seq = [0]

    for po_id, inv_dict in po_invoices.items():
        if len(inv_dict) != 1:
            continue   # multiple invoices against this PO — skip

        inv_id, (inv_total, pg) = next(iter(inv_dict.items()))
        po_total = po_map[po_id]["total"]

        if inv_total <= po_total * (1 + _OVERRUN_THRESHOLD):
            continue

        findings.append(Finding(
            finding_id=_finding_id_mismatch(pg, seq),
            category="po_invoice_mismatch",
            pages=[pg],
            document_refs=[inv_id, po_id],
            description=(
                f"Invoice '{inv_id}' on page {pg} has a grand total of "
                f"₹{inv_total:,.2f}, which exceeds the referenced PO '{po_id}' "
                f"total of ₹{po_total:,.2f} "
                f"(overrun: ₹{inv_total - po_total:,.2f})."
            ),
            reported_value=f"{inv_total:.2f}",
            correct_value=f"{po_total:.2f}",
            confidence=0.90,
        ))

    return findings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run_crossdoc_rules(pages: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_phantom_po_reference(pages))
    findings.extend(check_po_invoice_mismatch(pages))
    return findings
