"""Maggie Cold Email service."""

from __future__ import annotations

import logging
import os
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from campaign_runner import CampaignRunner
from magnus_client import MagnusClient
from mailer import SmtpMailer
from supabase_client import SupabaseClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("/app/logs/maggie-coldemail.log")],
)
log = logging.getLogger("maggie-coldemail")

START_TIME = datetime.utcnow()


def _env(name: str, default: str = "", required: bool = False) -> str:
    value = os.getenv(name, default).strip()
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


SUPABASE_URL = _env("SUPABASE_URL", required=True)
SUPABASE_SERVICE_KEY = _env("SUPABASE_SERVICE_KEY", required=True)
SUPABASE_CUSTOMER_TABLE = _env("SUPABASE_CUSTOMER_TABLE", "maggie_coldemail_customers")
SUPABASE_CSV_PUBLIC_URL = _env("SUPABASE_CSV_PUBLIC_URL", "")

MAGNUS_BASE_URL = _env("MAGNUS_BASE_URL", "http://magnus:8401")
MAGNUS_API_KEY = _env("MAGNUS_API_KEY", "")

REVIEWER_EMAIL = _env("REVIEWER_EMAIL", "rclausing@buntingmagnetics.com")
STATE_FILE = _env("STATE_FILE", "/app/data/state.json")

SMTP_HOST = _env("SMTP_HOST", required=True)
SMTP_PORT = int(_env("SMTP_PORT", "587"))
SMTP_USER = _env("SMTP_USER", "")
SMTP_PASS = _env("SMTP_PASS", "")
SMTP_FROM = _env("SMTP_FROM", required=True)
SMTP_USE_TLS = _env("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

supabase_client = SupabaseClient(
    url=SUPABASE_URL,
    service_key=SUPABASE_SERVICE_KEY,
    table=SUPABASE_CUSTOMER_TABLE,
    csv_public_url=SUPABASE_CSV_PUBLIC_URL,
)
magnus_client = MagnusClient(base_url=MAGNUS_BASE_URL, api_key=MAGNUS_API_KEY)
mailer = SmtpMailer(
    host=SMTP_HOST,
    port=SMTP_PORT,
    username=SMTP_USER,
    password=SMTP_PASS,
    from_email=SMTP_FROM,
    use_tls=SMTP_USE_TLS,
)
runner = CampaignRunner(
    supabase_client=supabase_client,
    magnus_client=magnus_client,
    mailer=mailer,
    reviewer_email=REVIEWER_EMAIL,
    state_path=STATE_FILE,
)

app = FastAPI(title="Maggie Cold Email", version="1.0.0")


class RunRequest(BaseModel):
    dry_run: bool = True
    limit: int = 250


@app.get("/health")
async def health() -> dict:
    return {
        "agent": "MAGGIE_COLDEMAIL",
        "status": "ok",
        "uptime_seconds": (datetime.utcnow() - START_TIME).total_seconds(),
        "reviewer_email": REVIEWER_EMAIL,
    }


@app.post("/campaign/run")
async def run_campaign(req: RunRequest) -> dict:
    if req.limit < 1 or req.limit > 5000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 5000")
    result = await runner.run(dry_run=req.dry_run, limit=req.limit)
    log.info("Campaign run completed: %s", result)
    return result
