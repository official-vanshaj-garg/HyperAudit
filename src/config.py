from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"
CACHE_DIR = BASE_DIR / "cache"

HYPERAPI_KEY = os.getenv("HYPERAPI_KEY", "")
HYPERAPI_URL = os.getenv("HYPERAPI_URL", "")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "")

for folder in [DATA_DIR, OUTPUTS_DIR, CACHE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)