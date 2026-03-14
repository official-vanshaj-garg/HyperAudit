from pathlib import Path
from typing import Any

from hyperapi import HyperAPIClient

from src.config import HYPERAPI_KEY, HYPERAPI_URL


class HyperAPIClientWrapper:
    def __init__(self) -> None:
        if not HYPERAPI_KEY:
            raise ValueError("HYPERAPI_KEY is not set. Add it to your .env file.")
        if not HYPERAPI_URL:
            raise ValueError("HYPERAPI_URL is not set. Add it to your .env file.")

        self.client = HyperAPIClient(api_key=HYPERAPI_KEY, base_url=HYPERAPI_URL)

    def parse(self, file_path: str | Path) -> dict[str, Any]:
        """Call HyperAPI parse() on a local PDF file and return the response dict."""
        try:
            return self.client.parse(file_path)
        except Exception as exc:
            raise RuntimeError(f"HyperAPI parse() failed: {exc}") from exc
