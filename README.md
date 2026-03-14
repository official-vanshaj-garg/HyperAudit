# HyperAudit

HyperAudit is an AI-assisted accounting anomaly detection pipeline for hackathon use.

## Planned flow

1. Parse accounting bundle
2. Normalize documents into structured records
3. Run deterministic anomaly rules
4. Optionally use LLM assistance for ambiguous cases
5. Review findings in UI
6. Export submission JSON

## Project structure

- `app.py` - Streamlit UI
- `main.py` - local runner
- `src/config.py` - configuration
- `src/models.py` - data models
- `src/hyperapi_client.py` - HyperAPI wrapper
- `src/parser.py` - raw parsing logic
- `src/normalizer.py` - normalize extracted data
- `src/exporter.py` - JSON export
- `src/rules/` - anomaly detection rules