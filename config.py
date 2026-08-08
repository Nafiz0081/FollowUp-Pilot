import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", "").split(",")
    if e.strip()
}

GOOGLE_APPLICATION_CREDENTIALS = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", str(BASE_DIR / "firebase-service-account.json")
)

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CHECKPOINT_DB_PATH = os.environ.get("CHECKPOINT_DB_PATH", str(DATA_DIR / "checkpoints.db"))
