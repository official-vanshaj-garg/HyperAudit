"""
Cross-document rules: anomalies that require comparing references across pages.

Each rule accepts:
  - pages: list of page dicts from parse_documents()["pages"]

Returns a list of Finding objects.
"""
import re
from typing import Any

from src.models import Finding

_RE_PO_NUMBER  = re.compile(r"PO Number:\s*\n(PO-[\d-]+)", re.MULTILINE)
_RE_PO_REF     = re.compile(r"PO Reference:\s*\n(PO-[\d-]+)", re.MULTILINE)
_RE_INV_NO     = re.compile(r"Invoice No:\s*\n(INV-[\w-]+)", re.MULTILINE)


def _finding_id(page: int, seq: list[int]) -> str:
    seq[0] += 1
    return f"PHPO-{page:04d}-{seq[0]:03d}"


# ---------------------------------------------------------------------------
# Rule: phantom_po_reference
# ---------------------------------------------------------------------------
def check_phantom_po_reference(pages: list[dict[str, Any]]) -> list[Finding]:
    """
    Flag invoices that reference a PO ID that does not exist anywhere in the bundle.

    Step 1: Collect all PO IDs from actual PO documents
            (pages whose text starts with 'PURCHASE ORDER').
    Step 2: For each invoice page with a 'PO Reference:' field,
            check whether the referenced PO ID is in the known set.
    Step 3: If not found, emit a phantom_po_reference finding.

    Deduplicates by PO ID — one finding per phantom PO, on the first page
    that mentions it.
    """
    # --- Pass 1: build the set of real PO IDs in the bundle ---
    known_po_ids: set[str] = set()
    for page in pages:
        if page["text"].strip().startswith("PURCHASE ORDER"):
            m = _RE_PO_NUMBER.search(page["text"])
            if m:
                known_po_ids.add(m.group(1))

    # --- Pass 2: find invoice pages referencing unknown POs ---
    findings: list[Finding] = []
    seq = [0]
    seen_phantom: set[str] = set()   # deduplicate by PO ID

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
            finding_id=_finding_id(page["page_number"], seq),
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
# Entry point
# ---------------------------------------------------------------------------
def run_crossdoc_rules(pages: list[dict[str, Any]]) -> list[Finding]:
    return check_phantom_po_reference(pages)
