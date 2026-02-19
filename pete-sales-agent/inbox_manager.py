#!/usr/bin/env python3
"""
Inbox Manager — processes bounces, auto-replies, unsubscribes.
Logs everything to local Postgres, cleans Pete's inbox, maintains suppression list.
"""
import csv
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/opt/pete-sales")

import psycopg2
import psycopg2.extras
from config import GOG_ACCOUNT
from email_handler import get_unread_threads, get_thread, mark_as_read, trash_thread

logger = logging.getLogger("pete.inbox")

DB_CONN = "host=127.0.0.1 port=5432 dbname=pete_sales user=pete password=PeteSalesDB2026"

# ---------------------------------------------------------------------------
# Bounce / auto-reply detection patterns
# ---------------------------------------------------------------------------

DEFINITE_BOUNCE_SENDERS = {
    "mailer-daemon", "postmaster", "bounce", "mailerdaemon",
}

# These senders are only bounces if the subject also matches bounce patterns
MAYBE_BOUNCE_SENDERS = {
    "noreply", "no-reply", "donotreply", "do-not-reply",
}

BOUNCE_SUBJECT_PATTERNS = [
    r"(?i)undeliverable",
    r"(?i)delivery.*fail",
    r"(?i)returned mail",
    r"(?i)mail delivery",
    r"(?i)delivery status",
    r"(?i)auto.?reply",
    r"(?i)automatic reply",
    r"(?i)out of office",
]

HARD_BOUNCE_PATTERNS = [
    r"(?i)user unknown",
    r"(?i)mailbox not found",
    r"(?i)does not exist",
    r"(?i)no such user",
    r"(?i)invalid recipient",
    r"(?i)address rejected",
    r"(?i)account disabled",
    r"(?i)account has been disabled",
    r"(?i)delivery to .+ not allowed",
    r"(?i)550[- ]",
    r"(?i)553[- ]",
    r"(?i)user .+ not found",
]

SOFT_BOUNCE_PATTERNS = [
    r"(?i)mailbox full",
    r"(?i)over quota",
    r"(?i)temporarily rejected",
    r"(?i)try again later",
    r"(?i)service unavailable",
    r"(?i)451[- ]",
    r"(?i)452[- ]",
]

REDIRECT_PATTERNS = [
    r"(?i)has moved to\s+(\S+@\S+)",
    r"(?i)new email.{0,20}?(\S+@\S+)",
    r"(?i)please.{0,30}?contact\s+(\S+@\S+)",
    r"(?i)reach me at\s+(\S+@\S+)",
    r"(?i)forward.{0,20}?to\s+(\S+@\S+)",
    r"(?i)redirect.{0,20}?(\S+@\S+)",
]

UNSUBSCRIBE_PATTERNS = [
    r"(?i)remove me",
    r"(?i)unsubscribe",
    r"(?i)stop (emailing|contacting|sending)",
    r"(?i)do not (contact|email|send)",
    r"(?i)take me off",
    r"(?i)opt.?out",
    r"(?i)no longer interested",
    r"(?i)please don.?t (contact|email)",
    r"(?i)cease (and desist|contact)",
    r"(?i)remove .+ from .+ list",
    r"(?i)not interested",
]

AUTO_REPLY_PATTERNS = [
    r"(?i)automatic reply",
    r"(?i)auto[- ]?reply",
    r"(?i)out of (the )?office",
    r"(?i)away from (the )?office",
    r"(?i)on (annual |sick )?leave",
    r"(?i)i.?m (currently )?(away|out|on leave|on vacation)",
]


def get_db():
    """Get a database connection."""
    return psycopg2.connect(DB_CONN)


def is_bounce_sender(email: str, subject: str = "") -> bool:
    """Check if sender is a bounce/delivery system. For noreply senders, requires bounce subject."""
    local = email.lower().split("@")[0] if "@" in email else email.lower()
    if any(s in local for s in DEFINITE_BOUNCE_SENDERS):
        return True
    if any(s in local for s in MAYBE_BOUNCE_SENDERS):
        return any(re.search(pat, subject) for pat in BOUNCE_SUBJECT_PATTERNS)
    return False


def classify_bounce(subject: str, body: str) -> tuple[str, str | None]:
    """
    Returns (bounce_type, redirect_email).
    bounce_type: 'hard', 'soft', 'redirect', 'auto_reply', 'out_of_office'
    """
    text = f"{subject} {body}"

    # Check for redirect first
    for pat in REDIRECT_PATTERNS:
        m = re.search(pat, text)
        if m:
            redirect = m.group(1).strip().rstrip(".")
            if "@" in redirect:
                return "redirect", redirect

    # Hard bounce
    for pat in HARD_BOUNCE_PATTERNS:
        if re.search(pat, text):
            return "hard", None

    # Soft bounce
    for pat in SOFT_BOUNCE_PATTERNS:
        if re.search(pat, text):
            return "soft", None

    # Auto-reply / OOO
    for pat in AUTO_REPLY_PATTERNS:
        if re.search(pat, text):
            return "auto_reply", None

    # Default: hard bounce for MAILER-DAEMON, auto_reply for others
    return "hard", None


def classify_unsubscribe(body: str) -> bool:
    """Check if the email body contains an unsubscribe request."""
    return any(re.search(pat, body) for pat in UNSUBSCRIBE_PATTERNS)


def extract_original_recipient(subject: str, body: str) -> str | None:
    """Try to extract the original recipient email from a bounce message."""
    # Common patterns in bounce messages
    patterns = [
        r"(?i)was not delivered to\s+(\S+@\S+)",
        r"(?i)delivery.+?(?:to|for)\s+(\S+@\S+)",
        r"(?i)failed.+?(?:to|for)\s+(\S+@\S+)",
        r"(?i)(?:recipient|address|mailbox)\s*:?\s*(\S+@\S+)",
        r"(?i)could not.+?deliver.+?(\S+@\S+)",
        r"(?i)undeliverable.+?(\S+@\S+)",
        r"<(\S+@\S+)>",  # Angle-bracket email in bounce body
    ]
    text = f"{subject} {body}"
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            email = m.group(1).strip().rstrip(">").rstrip(".")
            # Don't return pete's own email or the bounce sender
            if "@" in email and "pete@by-pete.com" not in email.lower() and "mailer-daemon" not in email.lower():
                return email.lower()
    return None


def ensure_prospect(conn, email: str, first_name: str = "", company: str = ""):
    """Insert prospect if not exists."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO prospects (email, first_name, company)
               VALUES (%s, %s, %s)
               ON CONFLICT (email) DO NOTHING""",
            (email.lower(), first_name, company)
        )
    conn.commit()


def update_prospect_status(conn, email: str, status: str, **kwargs):
    """Update prospect status and optional fields."""
    sets = ["status = %s", "updated_at = now()"]
    vals = [status]
    for k, v in kwargs.items():
        if v is not None:
            sets.append(f"{k} = %s")
            vals.append(v)
    vals.append(email.lower())
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE prospects SET {', '.join(sets)} WHERE email = %s",
            vals
        )
    conn.commit()


def add_to_suppression(conn, email: str, reason: str, source: str = "auto"):
    """Add email to suppression list."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO suppression_list (email, reason, source)
               VALUES (%s, %s, %s)
               ON CONFLICT (email) DO UPDATE SET reason = %s, added_at = now()""",
            (email.lower(), reason, source, reason)
        )
    conn.commit()
    logger.info("Suppressed: %s (%s)", email, reason)


def log_bounce(conn, prospect_email: str, bounce_type: str,
               raw_subject: str, raw_snippet: str,
               redirect_email: str = None, thread_id: str = None):
    """Log a bounce event."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO bounce_log
               (prospect_email, bounce_type, raw_subject, raw_snippet, redirect_email, thread_id)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (prospect_email.lower(), bounce_type, raw_subject[:500],
             raw_snippet[:1000] if raw_snippet else "", redirect_email, thread_id)
        )
    conn.commit()


def is_suppressed(conn, email: str) -> bool:
    """Check if email is on suppression list."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM suppression_list WHERE email = %s", (email.lower(),))
        return cur.fetchone() is not None


def delete_thread_from_inbox(thread_id: str):
    """Trash a processed bounce/auto-reply thread to keep inbox clean."""
    try:
        trash_thread(thread_id)
        logger.info("Trashed thread %s", thread_id)
    except Exception as e:
        logger.warning("Failed to trash thread %s: %s", thread_id, e)


def process_inbox():
    """
    Main inbox processing loop.
    Scans unread threads, classifies bounces/auto-replies/unsubscribes,
    logs to DB, suppresses as needed, cleans inbox.
    Returns dict of stats.
    """
    conn = get_db()
    stats = {"bounces_hard": 0, "bounces_soft": 0, "redirects": 0,
             "auto_replies": 0, "unsubscribes": 0, "cleaned": 0, "errors": 0}

    try:
        # Get all unread threads
        threads = get_unread_threads("is:unread -from:me", max_results=50)
        logger.info("Inbox scan: %d unread threads", len(threads))

        for thread_summary in threads:
            thread_id = thread_summary.get("id", "")
            if not thread_id:
                continue

            try:
                thread_data = get_thread(thread_id)
                messages = thread_data.get("messages", [])
                if not messages:
                    continue

                # Get latest inbound message
                latest = None
                for msg in reversed(messages):
                    headers = {h["name"].lower(): h.get("value", "")
                               for h in msg.get("payload", {}).get("headers", [])}
                    from_addr = headers.get("from", "")
                    if GOG_ACCOUNT not in from_addr.lower():
                        latest = msg
                        break

                if not latest:
                    continue

                headers = {h["name"].lower(): h.get("value", "")
                           for h in latest.get("payload", {}).get("headers", [])}
                from_header = headers.get("from", "")
                subject = headers.get("subject", "")
                snippet = latest.get("snippet", "")

                # Parse sender email
                if "<" in from_header:
                    sender_email = from_header.split("<")[1].rstrip(">").strip().lower()
                else:
                    sender_email = from_header.strip().lower()

                # --- BOUNCE HANDLING ---
                if is_bounce_sender(sender_email, subject):
                    original = extract_original_recipient(subject, snippet)
                    bounce_type, redirect = classify_bounce(subject, snippet)

                    if original:
                        ensure_prospect(conn, original)
                        log_bounce(conn, original, bounce_type, subject, snippet,
                                   redirect, thread_id)

                        if bounce_type == "hard":
                            update_prospect_status(conn, original, "bounced",
                                                   bounce_reason=snippet[:200],
                                                   bounce_type="hard")
                            add_to_suppression(conn, original, "bounced")
                            stats["bounces_hard"] += 1
                        elif bounce_type == "soft":
                            update_prospect_status(conn, original, "bounced",
                                                   bounce_reason=snippet[:200],
                                                   bounce_type="soft")
                            stats["bounces_soft"] += 1
                        elif bounce_type == "redirect" and redirect:
                            update_prospect_status(conn, original, "redirected",
                                                   redirect_email=redirect)
                            stats["redirects"] += 1
                        else:
                            stats["auto_replies"] += 1

                        logger.info("Bounce [%s]: %s → %s", bounce_type, original,
                                    redirect or "dead")
                    else:
                        logger.warning("Bounce from %s but couldn't extract recipient: %s",
                                       sender_email, subject)

                    # Clean from inbox
                    delete_thread_from_inbox(thread_id)
                    stats["cleaned"] += 1
                    continue

                # --- AUTO-REPLY HANDLING ---
                is_auto = any(re.search(pat, subject) for pat in AUTO_REPLY_PATTERNS)
                if is_auto:
                    ensure_prospect(conn, sender_email)
                    log_bounce(conn, sender_email, "auto_reply", subject, snippet,
                               thread_id=thread_id)
                    delete_thread_from_inbox(thread_id)
                    stats["auto_replies"] += 1
                    stats["cleaned"] += 1
                    logger.info("Auto-reply from %s, cleaned", sender_email)
                    continue

                # --- UNSUBSCRIBE HANDLING ---
                if classify_unsubscribe(snippet):
                    ensure_prospect(conn, sender_email)
                    update_prospect_status(conn, sender_email, "do_not_contact",
                                           unsubscribed_at=datetime.now(timezone.utc).isoformat())
                    add_to_suppression(conn, sender_email, "unsubscribed")
                    stats["unsubscribes"] += 1
                    logger.info("Unsubscribe from %s, suppressed", sender_email)
                    # Don't delete — let Pete's daemon respond respectfully
                    continue

                # Everything else is a real reply — leave in inbox for Pete daemon

            except Exception as e:
                logger.error("Error processing thread %s: %s", thread_id, e)
                stats["errors"] += 1

    finally:
        conn.close()

    logger.info("Inbox scan complete: %s", stats)
    return stats


def seed_prospects_from_csv(csv_path: str):
    """Seed the prospects table from the campaign CSV."""
    conn = get_db()
    count = 0
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                clean = {k.strip().lower(): v.strip() for k, v in row.items()}
                email = clean.get("email") or clean.get("email_address") or clean.get("e-mail", "")
                name = (clean.get("first") or clean.get("first name") or
                        clean.get("first_name") or clean.get("firstname") or
                        clean.get("contact") or "")
                company = (clean.get("company") or clean.get("company_name") or
                           clean.get("organization") or "")

                if email and "@" in email:
                    ensure_prospect(conn, email.lower(), name.strip().title(), company.strip())
                    count += 1
        logger.info("Seeded %d prospects from %s", count, csv_path)
    finally:
        conn.close()
    return count


def seed_sent_from_state(state_file: str):
    """Mark prospects as 'sent' based on batch_state.json."""
    conn = get_db()
    count = 0
    try:
        with open(state_file, "r") as f:
            state = json.load(f)
        sent_emails = state.get("sent_emails", [])
        for email in sent_emails:
            ensure_prospect(conn, email.lower())
            update_prospect_status(conn, email, "sent")
            count += 1
        logger.info("Marked %d prospects as sent from state file", count)
    finally:
        conn.close()
    return count


def get_suppression_set(conn=None) -> set[str]:
    """Return the full set of suppressed emails for batch sender checks."""
    close = False
    if conn is None:
        conn = get_db()
        close = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM suppression_list")
            return {row[0] for row in cur.fetchall()}
    finally:
        if close:
            conn.close()


def get_inbox_stats() -> dict:
    """Get stats for the dashboard."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'active') as active,
                    COUNT(*) FILTER (WHERE status = 'sent') as sent,
                    COUNT(*) FILTER (WHERE status = 'bounced') as bounced,
                    COUNT(*) FILTER (WHERE status = 'redirected') as redirected,
                    COUNT(*) FILTER (WHERE status = 'unsubscribed' OR status = 'do_not_contact') as suppressed,
                    COUNT(*) FILTER (WHERE status = 'responded') as responded,
                    COUNT(*) as total
                FROM prospects
            """)
            prospect_stats = dict(cur.fetchone())

            cur.execute("SELECT COUNT(*) as count FROM suppression_list")
            suppression_count = cur.fetchone()["count"]

            cur.execute("""
                SELECT bounce_type, COUNT(*) as count
                FROM bounce_log
                GROUP BY bounce_type
                ORDER BY count DESC
            """)
            bounce_breakdown = {row["bounce_type"]: row["count"] for row in cur.fetchall()}

        return {
            "prospects": prospect_stats,
            "suppression_count": suppression_count,
            "bounce_breakdown": bounce_breakdown,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "scan":
            stats = process_inbox()
            print(json.dumps(stats, indent=2))
        elif cmd == "seed":
            csv_path = sys.argv[2] if len(sys.argv) > 2 else "/opt/pete-sales/campaigns/first_shot.csv"
            count = seed_prospects_from_csv(csv_path)
            print(f"Seeded {count} prospects")
        elif cmd == "seed-sent":
            state_path = sys.argv[2] if len(sys.argv) > 2 else "/opt/pete-sales/campaigns/batch_state.json"
            count = seed_sent_from_state(state_path)
            print(f"Marked {count} as sent")
        elif cmd == "stats":
            stats = get_inbox_stats()
            print(json.dumps(stats, indent=2))
        elif cmd == "check":
            email = sys.argv[2]
            conn = get_db()
            print(f"Suppressed: {is_suppressed(conn, email)}")
            conn.close()
        else:
            print("Usage: inbox_manager.py [scan|seed|seed-sent|stats|check <email>]")
    else:
        print("Usage: inbox_manager.py [scan|seed|seed-sent|stats|check <email>]")
