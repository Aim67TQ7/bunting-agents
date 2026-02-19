"""Configuration for Pete Sales Agent."""
import os
from dotenv import load_dotenv

load_dotenv("/opt/pete-sales/.env")

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ezlmmegowggujpcnzoda.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Email
GOG_ACCOUNT = os.getenv("GOG_ACCOUNT", "pete@by-pete.com")
GOG_BIN = os.getenv("GOG_BIN", "/usr/local/bin/gog")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "robert@n0v8v.com")

# Polling
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "900"))  # 15 min
POLL_QUERY = os.getenv("POLL_QUERY", "is:unread -from:me -category:promotions -category:social -category:updates")

# Paths
LOG_DIR = "/opt/pete-sales/logs"
STATE_FILE = "/opt/pete-sales/state.json"

# Safety
MAX_EMAILS_PER_HOUR = int(os.getenv("MAX_EMAILS_PER_HOUR", "20"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
