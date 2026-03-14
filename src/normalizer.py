import re
from typing import Any

from src.models import Vendor

# Tokens that appear in the vendor table header/footer — skip these
_SKIP_TOKENS = {
    "vendor master", "vendor master (continued)",
    "#", "vendor name", "gstin", "state", "bank", "ifsc",
    "vendor-master",
}

# Matches a row index like "1", "19", "100"
_ROW_INDEX_RE = re.compile(r"^\d+$")

# Matches a GSTIN: 15-char alphanumeric
_GSTIN_RE = re.compile(r"^[0-9A-Z]{15}$")

# Matches an IFSC code as used in this dataset: 4 letters + 8 alphanumeric chars
_IFSC_RE = re.compile(r"^[A-Z]{4}[0-9A-Z]{8}$")


def _clean_tokens(text: str) -> list[str]:
    """Split page text into non-empty tokens, dropping header/footer noise."""
    tokens = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Drop page-number lines like "Page 3"
        if re.match(r"^Page \d+$", stripped):
            continue
        if stripped.lower() in _SKIP_TOKENS:
            continue
        tokens.append(stripped)
    return tokens


def extract_vendor_master(parsed: dict[str, Any]) -> list[Vendor]:
    """
    Extract vendor records from pages 3 and 4 of the parsed PDF output.

    Expects parsed output from parse_documents():
    {
        "pages": [{"page_number": int, "text": str, ...}, ...]
    }

    Returns a list of Vendor objects.
    """
    source_pages = [3, 4]
    combined_tokens: list[str] = []

    pages_by_number = {p["page_number"]: p for p in parsed["pages"]}

    for page_num in source_pages:
        page = pages_by_number.get(page_num)
        if page:
            combined_tokens.extend(_clean_tokens(page["text"]))

    vendors: list[Vendor] = []
    i = 0

    while i < len(combined_tokens):
        # Expect a row index to start a vendor record
        if not _ROW_INDEX_RE.match(combined_tokens[i]):
            i += 1
            continue

        # Need at least 5 more tokens: name, gstin, state, bank, ifsc
        if i + 5 >= len(combined_tokens):
            break

        row_num = combined_tokens[i]
        name    = combined_tokens[i + 1]
        gstin   = combined_tokens[i + 2]
        state   = combined_tokens[i + 3]
        bank    = combined_tokens[i + 4]
        ifsc    = combined_tokens[i + 5]

        # Validate GSTIN and IFSC to confirm we have a real row
        if _GSTIN_RE.match(gstin) and _IFSC_RE.match(ifsc):
            vendors.append(
                Vendor(
                    vendor_id=row_num,
                    name=name,
                    gstin=gstin,
                    state=state,
                    bank=bank,
                    ifsc=ifsc,
                    source_pages=source_pages,
                )
            )
            i += 6
        else:
            i += 1

    return vendors
