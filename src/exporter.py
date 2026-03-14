import json
from pathlib import Path
from typing import Any

from src.models import Finding


def export_findings(
    team_id: str,
    findings: list[Finding],
    ref_by_page: dict[int, list[str]],
    output_path: Path,
) -> int:
    """
    Export findings to the hackathon submission JSON format.

    Only the required fields are included per finding:
        finding_id, category, pages, document_refs,
        description, reported_value, correct_value

    document_refs: uses the finding's own refs if present,
    otherwise falls back to page-level doc ref lookup.

    Returns the number of findings exported.
    """
    records: list[dict[str, Any]] = []

    for f in findings:
        # Resolve document refs
        if f.document_refs and any(f.document_refs):
            doc_refs = [r for r in f.document_refs if r]
        else:
            # Fall back to page-level lookup, deduplicated
            seen: set[str] = set()
            doc_refs = []
            for pg in f.pages:
                for ref in ref_by_page.get(pg, []):
                    if ref not in seen:
                        seen.add(ref)
                        doc_refs.append(ref)

        records.append({
            "finding_id": f.finding_id,
            "category": f.category,
            "pages": f.pages,
            "document_refs": doc_refs,
            "description": f.description,
            "reported_value": f.reported_value,
            "correct_value": f.correct_value,
        })

    payload = {"team_id": team_id, "findings": records}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return len(records)
