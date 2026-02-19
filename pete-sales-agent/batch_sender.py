#!/usr/bin/env python3
"""
Autonomous A/B batch sender — runs via cron, sends 100 emails per invocation.
Tracks sent emails in a JSON state file so it never double-sends.
"""
import csv
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/opt/pete-sales")

from dotenv import load_dotenv
load_dotenv("/opt/pete-sales/.env")

from email_handler import send_html_email
from campaign import build_html_email
from inbox_manager import get_suppression_set

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CSV_PATH = "/opt/pete-sales/campaigns/first_shot.csv"
VARIANT_A_PATH = "/opt/pete-sales/campaigns/variant_a.txt"
VARIANT_B_PATH = "/opt/pete-sales/campaigns/variant_b.txt"
STATE_FILE = "/opt/pete-sales/campaigns/batch_state.json"
LOG_FILE = "/opt/pete-sales/logs/batch_sender.log"
BATCH_SIZE = 100
STAGGER_SECONDS = 30  # 100 * 30s = 50 min, fits in 1-hour window

SUBJECT_A = "Your AP team shouldn't spend hours chasing payments"
SUBJECT_B = "Quick question about your collections process"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("batch")

# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"sent_emails": [], "total_sent": 0, "total_errors": 0, "runs": []}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Prospect loader
# ---------------------------------------------------------------------------

def load_all_prospects(csv_path: str) -> list[dict]:
    prospects = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip().lower(): v.strip() for k, v in row.items()}
            name = (clean.get("first") or clean.get("first name") or
                    clean.get("first_name") or clean.get("firstname") or
                    clean.get("contact") or "")
            prospect = {
                "first_name": name.strip().title() if name else "",
                "email": clean.get("email") or clean.get("email_address") or clean.get("e-mail", ""),
                "company": clean.get("company") or clean.get("company_name") or clean.get("organization", ""),
            }
            if prospect["email"] and "@" in prospect["email"]:
                prospects.append(prospect)
    return prospects


# ---------------------------------------------------------------------------
# Main batch send
# ---------------------------------------------------------------------------

def run_batch():
    state = load_state()
    sent_set = set(state["sent_emails"])

    # Load suppression list (bounced, unsubscribed, do-not-contact)
    suppressed = get_suppression_set()
    log.info("Suppression list: %d emails blocked", len(suppressed))

    # Load prospects and filter out already sent + suppressed
    all_prospects = load_all_prospects(CSV_PATH)
    remaining = [p for p in all_prospects
                 if p["email"] not in sent_set and p["email"].lower() not in suppressed]

    if not remaining:
        log.info("ALL DONE — no more prospects to send. %d total sent.", state["total_sent"])
        return

    # Take next batch
    batch = remaining[:BATCH_SIZE]
    log.info("=" * 60)
    log.info("BATCH RUN: %d remaining, sending %d this batch", len(remaining), len(batch))
    log.info("=" * 60)

    # Load variant templates
    variant_a_body = Path(VARIANT_A_PATH).read_text()
    variant_b_body = Path(VARIANT_B_PATH).read_text()

    # Deterministic A/B split: first half = A, second half = B
    midpoint = len(batch) // 2
    sent = 0
    errors = 0

    for i, p in enumerate(batch):
        name = p["first_name"]
        email = p["email"]
        company = p["company"]
        variant = "A" if i < midpoint else "B"

        body_template = variant_a_body if variant == "A" else variant_b_body
        subject = SUBJECT_A if variant == "A" else SUBJECT_B

        body = body_template.replace("{first_name}", name).replace("{company_name}", company)
        subject_filled = subject.replace("{first_name}", name).replace("{company_name}", company)
        html = build_html_email(body, include_button=True)
        plain = body + "\n\nPete | n0v8v\npete@by-pete.com"

        try:
            send_html_email(to=email, subject=subject_filled, body_text=plain, body_html=html)
            sent += 1
            sent_set.add(email)
            log.info("%d/%d | %s | %s | %s | %s", sent, len(batch), variant, name, email, company[:40])

            # Stagger between sends (skip after last one)
            if i < len(batch) - 1:
                time.sleep(STAGGER_SECONDS)

        except Exception as e:
            errors += 1
            log.error("ERROR | %s | %s | %s : %s", variant, name, email, str(e)[:100])
            # Still mark as "sent" to avoid retrying bad addresses forever
            sent_set.add(email)

    # Update state
    state["sent_emails"] = list(sent_set)
    state["total_sent"] += sent
    state["total_errors"] += errors
    state["runs"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "batch_size": len(batch),
        "sent": sent,
        "errors": errors,
        "remaining_after": len(remaining) - len(batch),
    })
    save_state(state)

    log.info("")
    log.info("BATCH COMPLETE: %d sent, %d errors, %d remaining",
             sent, errors, len(remaining) - len(batch))
    log.info("TOTALS: %d sent overall, %d errors overall",
             state["total_sent"], state["total_errors"])


if __name__ == "__main__":
    run_batch()
