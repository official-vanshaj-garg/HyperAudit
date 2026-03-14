"""
Vendor-based anomaly rules.

Each rule accepts:
  - pages: list of page dicts from parse_documents()["pages"]
  - vendors: list of Vendor objects from extract_vendor_master()

Returns a list of Finding objects.
"""
import re
from typing import Any

from rapidfuzz import fuzz

from src.models import Finding, Vendor

# ---------------------------------------------------------------------------
# GSTIN state code → state name (first 2 digits)
# ---------------------------------------------------------------------------
_GSTIN_STATE: dict[str, str] = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "25": "Daman & Diu", "26": "Dadra & Nagar Haveli", "27": "Maharashtra",
    "28": "Andhra Pradesh", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman & Nicobar", "36": "Telangana",
    "37": "Andhra Pradesh (New)",
}

# Regex patterns for extracting fields from invoice page text
_RE_VENDOR_NAME = re.compile(r"Name:\s*\n(.+)", re.MULTILINE)
_RE_GSTIN       = re.compile(r"GSTIN:\s*\n([0-9A-Z]{15})", re.MULTILINE)
_RE_IFSC        = re.compile(r"IFSC:\s*\n([A-Z]{4}[0-9A-Z]{8})", re.MULTILINE)
_RE_INV_NO      = re.compile(r"Invoice No:\s*\n(INV-[\w-]+)", re.MULTILINE)

# Similarity thresholds
_TYPO_LOW  = 70   # below this → unrelated / fake vendor
_TYPO_HIGH = 99   # at or above this → exact match (no typo)


def _best_match(name: str, vendors: list[Vendor]) -> tuple[Vendor | None, float]:
    """Return the vendor with the highest fuzzy name similarity and its score."""
    best_vendor: Vendor | None = None
    best_score = 0.0
    for v in vendors:
        score = fuzz.ratio(name.lower(), v.name.lower())
        if score > best_score:
            best_score = score
            best_vendor = v
    return best_vendor, best_score


def _extract_vendor_block(text: str) -> dict[str, str]:
    """Pull vendor name, GSTIN, and IFSC from a single page's text."""
    result: dict[str, str] = {}
    m = _RE_VENDOR_NAME.search(text)
    if m:
        result["name"] = m.group(1).strip()
    m = _RE_GSTIN.search(text)
    if m:
        result["gstin"] = m.group(1).strip()
    m = _RE_IFSC.search(text)
    if m:
        result["ifsc"] = m.group(1).strip()
    m = _RE_INV_NO.search(text)
    if m:
        result["invoice_no"] = m.group(1).strip()
    return result


def _finding_id(category: str, page: int, seq: list[int]) -> str:
    seq[0] += 1
    return f"{category.upper()[:4]}-{page:04d}-{seq[0]:03d}"


# ---------------------------------------------------------------------------
# Rule 1: vendor_name_typo
# ---------------------------------------------------------------------------
def check_vendor_name_typo(
    pages: list[dict[str, Any]],
    vendors: list[Vendor],
) -> list[Finding]:
    """Flag vendor names in documents that are close but not exact matches to the master."""
    findings: list[Finding] = []
    seq = [0]

    for page in pages:
        block = _extract_vendor_block(page["text"])
        name = block.get("name")
        if not name:
            continue

        best, score = _best_match(name, vendors)
        if best is None:
            continue

        if _TYPO_LOW <= score < _TYPO_HIGH:
            findings.append(Finding(
                finding_id=_finding_id("vendor_name_typo", page["page_number"], seq),
                category="vendor_name_typo",
                pages=[page["page_number"]],
                document_refs=[block.get("invoice_no", "")],
                description=(
                    f"Vendor name '{name}' on page {page['page_number']} "
                    f"closely matches master entry '{best.name}' "
                    f"(similarity {score:.0f}%) but is not identical."
                ),
                reported_value=name,
                correct_value=best.name,
                confidence=round(score / 100, 2),
            ))

    return findings


# ---------------------------------------------------------------------------
# Rule 2: ifsc_mismatch
# ---------------------------------------------------------------------------
def check_ifsc_mismatch(
    pages: list[dict[str, Any]],
    vendors: list[Vendor],
) -> list[Finding]:
    """Flag documents where the IFSC differs from the vendor master for the same vendor."""
    # Build lookup: gstin → vendor
    gstin_map: dict[str, Vendor] = {v.gstin: v for v in vendors if v.gstin}
    findings: list[Finding] = []
    seq = [0]

    for page in pages:
        block = _extract_vendor_block(page["text"])
        gstin = block.get("gstin")
        ifsc  = block.get("ifsc")
        if not gstin or not ifsc:
            continue

        master = gstin_map.get(gstin)
        if master is None:
            continue  # unknown vendor — handled by fake_vendor rule

        if master.ifsc and ifsc != master.ifsc:
            findings.append(Finding(
                finding_id=_finding_id("ifsc_mismatch", page["page_number"], seq),
                category="ifsc_mismatch",
                pages=[page["page_number"]],
                document_refs=[block.get("invoice_no", "")],
                description=(
                    f"IFSC on page {page['page_number']} is '{ifsc}' "
                    f"but vendor master for '{master.name}' lists '{master.ifsc}'."
                ),
                reported_value=ifsc,
                correct_value=master.ifsc,
                confidence=0.95,
            ))

    return findings


# ---------------------------------------------------------------------------
# Rule 3: gstin_state_mismatch
# ---------------------------------------------------------------------------
def check_gstin_state_mismatch(
    pages: list[dict[str, Any]],
    vendors: list[Vendor],
) -> list[Finding]:
    """Flag documents where the GSTIN state code contradicts the vendor master state."""
    gstin_map: dict[str, Vendor] = {v.gstin: v for v in vendors if v.gstin}
    findings: list[Finding] = []
    seq = [0]

    for page in pages:
        block = _extract_vendor_block(page["text"])
        gstin = block.get("gstin")
        if not gstin or len(gstin) < 2:
            continue

        state_code = gstin[:2]
        gstin_state = _GSTIN_STATE.get(state_code)
        if not gstin_state:
            continue

        master = gstin_map.get(gstin)
        if master is None or not master.state:
            continue

        # Normalise for comparison (lowercase, strip)
        if gstin_state.lower() not in master.state.lower() and \
           master.state.lower() not in gstin_state.lower():
            findings.append(Finding(
                finding_id=_finding_id("gstin_state_mismatch", page["page_number"], seq),
                category="gstin_state_mismatch",
                pages=[page["page_number"]],
                document_refs=[block.get("invoice_no", "")],
                description=(
                    f"GSTIN '{gstin}' on page {page['page_number']} encodes state "
                    f"'{gstin_state}' but vendor master lists '{master.state}' "
                    f"for vendor '{master.name}'."
                ),
                reported_value=gstin_state,
                correct_value=master.state,
                confidence=0.90,
            ))

    return findings


# ---------------------------------------------------------------------------
# Rule 4: fake_vendor
# ---------------------------------------------------------------------------
def check_fake_vendor(
    pages: list[dict[str, Any]],
    vendors: list[Vendor],
) -> list[Finding]:
    """Flag vendor names in documents that have no close match in the vendor master."""
    findings: list[Finding] = []
    seq = [0]
    seen: set[str] = set()  # deduplicate by name

    for page in pages:
        block = _extract_vendor_block(page["text"])
        name = block.get("name")
        if not name or name in seen:
            continue

        _, score = _best_match(name, vendors)
        if score < _TYPO_LOW:
            seen.add(name)
            findings.append(Finding(
                finding_id=_finding_id("fake_vendor", page["page_number"], seq),
                category="fake_vendor",
                pages=[page["page_number"]],
                document_refs=[block.get("invoice_no", "")],
                description=(
                    f"Vendor '{name}' on page {page['page_number']} "
                    f"has no match in the vendor master (best similarity {score:.0f}%)."
                ),
                reported_value=name,
                correct_value=None,
                confidence=round((100 - score) / 100, 2),
            ))

    return findings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run_vendor_rules(
    pages: list[dict[str, Any]],
    vendors: list[Vendor],
) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_vendor_name_typo(pages, vendors))
    findings.extend(check_ifsc_mismatch(pages, vendors))
    findings.extend(check_gstin_state_mismatch(pages, vendors))
    findings.extend(check_fake_vendor(pages, vendors))
    return findings
