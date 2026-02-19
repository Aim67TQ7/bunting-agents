#!/usr/bin/env python3
"""
Pete Sales Agent Daemon — polls Gmail, classifies intent, responds, tracks everything.
Now with NDA pipeline: auto-triggers NDA generation for interested prospects.
"""
import json
import logging
import os
import sys
import time
import signal
from datetime import datetime, timezone
from pathlib import Path

# Ensure our directory is in path
sys.path.insert(0, "/opt/pete-sales")

from config import (
    POLL_INTERVAL_SECONDS, POLL_QUERY, LOG_DIR, STATE_FILE,
    MAX_EMAILS_PER_HOUR, DRY_RUN, NOTIFICATION_EMAIL, GOG_ACCOUNT
)
from email_handler import get_unread_threads, get_thread, send_email, mark_as_read
from classifier import classify_intent
from responder import generate_response, generate_morning_report
from tracker import (
    upsert_thread, log_message, get_thread_history,
    is_thread_processed, get_daily_stats, get_active_threads
)
from nda_handler import (
    has_existing_nda, trigger_nda_generation, send_nda_email,
    check_nda_submissions, lookup_company
)

# Logging setup
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/pete.log"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("pete.daemon")

# Rate limiting
_emails_sent_this_hour = 0
_hour_start = datetime.now()
_running = True


def signal_handler(sig, frame):
    global _running
    logger.info("Shutdown signal received, stopping gracefully...")
    _running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def check_rate_limit() -> bool:
    """Check if we're within rate limits."""
    global _emails_sent_this_hour, _hour_start
    now = datetime.now()
    if (now - _hour_start).total_seconds() > 3600:
        _emails_sent_this_hour = 0
        _hour_start = now
    return _emails_sent_this_hour < MAX_EMAILS_PER_HOUR


def increment_rate_counter():
    global _emails_sent_this_hour
    _emails_sent_this_hour += 1


def extract_sender_info(thread_data: dict) -> tuple[str, str, str, str, str]:
    """Extract sender email, name, subject, body, and message_id from thread data."""
    messages = thread_data.get("messages", [])
    if not messages:
        return "", "", "", "", ""

    # Get the latest message that isn't from Pete
    latest = None
    for msg in reversed(messages):
        headers = {h["name"].lower(): h.get("value", "") for h in msg.get("payload", {}).get("headers", [])}
        from_addr = headers.get("from", "")
        if GOG_ACCOUNT not in from_addr.lower():
            latest = msg
            break

    if not latest:
        latest = messages[-1]

    headers = {h["name"].lower(): h["value"] for h in latest.get("payload", {}).get("headers", [])}
    from_header = headers.get("from", "")
    subject = headers.get("subject", "")
    message_id = latest.get("id", "")

    # Parse "Name <email>" format
    if "<" in from_header:
        name = from_header.split("<")[0].strip().strip('"')
        email = from_header.split("<")[1].rstrip(">").strip()
    else:
        name = from_header.split("@")[0]
        email = from_header.strip()

    # Extract body
    body = extract_body(latest)

    return email, name, subject, body, message_id


def extract_body(message: dict) -> str:
    """Extract plain text body from a Gmail message."""
    import base64

    payload = message.get("payload", {})

    # Check for direct body
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    # Check parts
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

    # Fallback: snippet
    return message.get("snippet", "")


def try_nda_trigger(sender_email: str, sender_name: str, intent: str) -> None:
    """Attempt to trigger NDA generation for interested prospects."""
    if intent not in ("INTERESTED", "DEMO_REQUEST"):
        return

    if has_existing_nda(sender_email):
        logger.info("NDA already exists for %s, skipping trigger", sender_email)
        return

    # Infer company name from sender domain
    domain = sender_email.split("@")[1] if "@" in sender_email else ""
    if domain and domain not in ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"):
        company_name = domain.split(".")[0].replace("-", " ").title()
    else:
        company_name = f"{sender_name}'s Company"

    logger.info("Triggering NDA generation for %s (%s)", sender_name, company_name)

    result = trigger_nda_generation(company_name, sender_email, source_campaign="inbound_reply")

    if result.get("status") == "ok":
        nda_url = result["url"]
        try:
            send_nda_email(sender_email, sender_name, company_name, nda_url)
            increment_rate_counter()
            logger.info("NDA page + email sent to %s: %s", sender_email, nda_url)
        except Exception as e:
            logger.error("Failed to send NDA email to %s: %s", sender_email, e)
    else:
        logger.error("NDA generation failed for %s: %s", sender_email, result.get("error"))


def process_thread(thread_summary: dict) -> None:
    """Process a single email thread."""
    thread_id = thread_summary.get("id", "")
    if not thread_id:
        return

    try:
        # Get full thread
        thread_data = get_thread(thread_id)
        sender_email, sender_name, subject, body, message_id = extract_sender_info(thread_data)

        if not sender_email or not body:
            logger.warning(f"Empty sender/body for thread {thread_id}, skipping")
            return

        # Skip if already processed
        if is_thread_processed(thread_id, message_id):
            logger.debug(f"Thread {thread_id} message {message_id} already processed")
            return

        logger.info(f"Processing: {sender_name} <{sender_email}> — {subject}")

        # Classify intent
        intent = classify_intent(sender_email, subject, body)
        logger.info(f"Intent: {intent}")

        # Skip spam
        if intent == "SPAM":
            log_message(thread_id, message_id, sender_email, body, intent, inbound=True)
            logger.info(f"Spam detected, skipping: {subject}")
            return

        # Get conversation history
        history = get_thread_history(thread_id)

        # Generate response
        response_text = None
        should_respond = intent not in ("SPAM",)
        should_escalate = intent in ("HUMAN_REQUEST", "DEMO_REQUEST")

        if should_respond:
            response_text = generate_response(intent, sender_email, subject, body, history)

        if response_text and not DRY_RUN:
            if check_rate_limit():
                # Send response
                send_email(
                    to=sender_email,
                    subject=f"Re: {subject}" if not subject.startswith("Re:") else subject,
                    body=response_text,
                    thread_id=thread_id,
                    reply_to_message_id=message_id,
                )
                increment_rate_counter()
                logger.info(f"Response sent to {sender_email}")

                # Trigger NDA for interested/demo prospects (after response)
                try_nda_trigger(sender_email, sender_name, intent)
            else:
                logger.warning("Rate limit reached, deferring response")
                return
        elif DRY_RUN and response_text:
            logger.info(f"[DRY RUN] Would send to {sender_email}:\n{response_text}")

        # Track in Supabase
        status = "active"
        if intent == "DEMO_REQUEST":
            status = "demo_booked"
        elif intent == "HUMAN_REQUEST":
            status = "escalated"
        elif intent == "NOT_INTERESTED":
            status = "closed_lost"

        upsert_thread(thread_id, sender_email, sender_name, subject, intent, status, body)
        log_message(thread_id, message_id, sender_email, body, intent, response_text, inbound=True)

        # Escalate if needed
        if should_escalate and not DRY_RUN:
            escalation_subject = f"[PETE ESCALATION] {intent}: {sender_name} — {subject}"
            escalation_body = f"""Pete escalation — {intent}

Prospect: {sender_name} <{sender_email}>
Subject: {subject}
Intent: {intent}

Their message:
{body[:1000]}

Pete's response:
{response_text or 'No response sent'}

Thread ID: {thread_id}
"""
            send_email(to=NOTIFICATION_EMAIL, subject=escalation_subject, body=escalation_body)
            increment_rate_counter()
            logger.info(f"Escalated to {NOTIFICATION_EMAIL}: {intent}")

    except Exception as e:
        logger.error(f"Error processing thread {thread_id}: {e}", exc_info=True)


def poll_cycle():
    """Run one polling cycle."""
    logger.info("Starting poll cycle...")
    try:
        threads = get_unread_threads(POLL_QUERY)
        logger.info(f"Found {len(threads)} unread threads")
        for thread in threads:
            process_thread(thread)

        # Check for NDA submissions
        nda_count = check_nda_submissions()
        if nda_count > 0:
            logger.info(f"Processed {nda_count} NDA submissions")
    except Exception as e:
        logger.error(f"Poll cycle failed: {e}", exc_info=True)


def send_morning_report():
    """Send daily report to Robert."""
    try:
        stats = get_daily_stats()
        threads = get_active_threads()

        # Annotate threads for report
        for t in threads:
            t["needs_attention"] = t.get("status") in ("escalated", "demo_booked")
            t["attention_reason"] = t.get("status", "").replace("_", " ").title()

        report = generate_morning_report(stats, threads)

        if not DRY_RUN:
            send_email(
                to=NOTIFICATION_EMAIL,
                subject=f"Pete's Daily Report — {datetime.now().strftime('%Y-%m-%d')}",
                body=report,
            )
            logger.info("Morning report sent")
        else:
            logger.info(f"[DRY RUN] Morning report:\n{report}")
    except Exception as e:
        logger.error(f"Morning report failed: {e}", exc_info=True)


def main():
    """Main daemon loop."""
    logger.info("=" * 60)
    logger.info("Pete Sales Agent starting up")
    logger.info(f"Poll interval: {POLL_INTERVAL_SECONDS}s")
    logger.info(f"Dry run: {DRY_RUN}")
    logger.info(f"Max emails/hour: {MAX_EMAILS_PER_HOUR}")
    logger.info("=" * 60)

    while _running:
        poll_cycle()
        logger.info(f"Sleeping {POLL_INTERVAL_SECONDS}s until next poll...")
        # Sleep in small chunks so we can respond to signals
        for _ in range(POLL_INTERVAL_SECONDS):
            if not _running:
                break
            time.sleep(1)

    logger.info("Pete Sales Agent shut down cleanly")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        send_morning_report()
    elif len(sys.argv) > 1 and sys.argv[1] == "once":
        poll_cycle()
    else:
        main()
