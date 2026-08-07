import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "cif"

ALLOWED_MID_PREFIX = "mp-"
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
MATERIAL_SEARCH_LIMIT = 12
MP_API_KEY = os.getenv("MP_API_KEY", "").strip()
MP_API_TIMEOUT_SECONDS = float(os.getenv("MP_API_TIMEOUT_SECONDS", "15"))
MP_API_MAX_RETRIES = int(os.getenv("MP_API_MAX_RETRIES", "2"))
MP_API_BACKOFF_SECONDS = float(os.getenv("MP_API_BACKOFF_SECONDS", "0.75"))
