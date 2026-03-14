import json
from pathlib import Path
from src.models import Finding


def export_findings(team_id: str, findings: list[Finding], output_path: Path) -> None:
    payload = {
        "team_id": team_id,
        "findings": [finding.model_dump() for finding in findings],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")