"""Email Poller — Microsoft Graph API inbox polling for maggie@buntingmagnetics.com."""

import os
import asyncio
import logging
from datetime import datetime

import httpx
import msal
from bs4 import BeautifulSoup

log = logging.getLogger("maggie-spares.email")

TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
MAILBOX = os.environ.get("MAILBOX_ADDRESS", "maggie@buntingmagnetics.com")
REVIEW_EMAIL = os.environ.get("REVIEW_EMAIL", "rclausing@buntingmagnetics.com")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Senders to skip — no point burning Gemini tokens on these
SKIP_SENDERS = {
    "noreply@", "no-reply@", "mailer-daemon@", "postmaster@",
    "notifications@", "donotreply@", "auto-reply@", "bounce@",
}
SKIP_SUBJECTS = [
    "out of office", "automatic reply", "auto-reply", "undeliverable",
    "delivery status notification", "read receipt",
]

# Track stats
stats = {
    "emails_processed": 0,
    "emails_errored": 0,
    "emails_skipped": 0,
    "last_poll": None,
    "last_email_from": None,
    "started_at": datetime.utcnow().isoformat(),
}

# Deduplication — track processed message IDs to prevent reprocessing on crash recovery
_processed_ids: set[str] = set()
_MAX_PROCESSED_IDS = 1000  # Rolling window

# MSAL app singleton — token caching built in
_msal_app: msal.ConfidentialClientApplication | None = None

# Shared httpx client for Graph API calls
_graph_client: httpx.AsyncClient | None = None


def get_stats() -> dict:
    return stats.copy()


def _get_msal_app() -> msal.ConfidentialClientApplication | None:
    global _msal_app
    if _msal_app is None:
        if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
            log.error("Azure credentials not configured")
            return None
        _msal_app = msal.ConfidentialClientApplication(
            CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}",
            client_credential=CLIENT_SECRET,
        )
    return _msal_app


async def _get_token() -> str | None:
    """Get OAuth2 token via client credentials flow. Async-safe via to_thread."""
    app = _get_msal_app()
    if app is None:
        return None

    # MSAL's acquire_token_for_client is synchronous and blocks the event loop.
    # Wrap in to_thread to prevent stalling the poller.
    result = await asyncio.to_thread(
        app.acquire_token_for_client,
        scopes=["https://graph.microsoft.com/.default"],
    )

    if "access_token" in result:
        return result["access_token"]
    log.error(f"Token acquisition failed: {result.get('error_description', 'unknown')}")
    return None


def _get_graph_client() -> httpx.AsyncClient:
    """Shared httpx client for all Graph API calls — connection pooling."""
    global _graph_client
    if _graph_client is None or _graph_client.is_closed:
        _graph_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _graph_client


def _should_skip(sender: str, subject: str) -> bool:
    """Filter out junk: auto-replies, noreply, bounces, newsletters."""
    sender_lower = sender.lower()
    for prefix in SKIP_SENDERS:
        if prefix in sender_lower:
            return True

    subject_lower = subject.lower()
    for pattern in SKIP_SUBJECTS:
        if pattern in subject_lower:
            return True

    return False


def _strip_html(html: str) -> str:
    """Convert HTML email body to plain text using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    # Remove style and script tags
    for tag in soup(["style", "script"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _track_processed(msg_id: str) -> bool:
    """Track processed message ID. Returns True if already processed (duplicate)."""
    if msg_id in _processed_ids:
        return True
    _processed_ids.add(msg_id)
    # Rolling window — evict oldest when we hit the cap
    if len(_processed_ids) > _MAX_PROCESSED_IDS:
        # set doesn't have order, but for a rolling window this is good enough
        # In practice, the set resets on container restart anyway
        excess = len(_processed_ids) - _MAX_PROCESSED_IDS
        for _ in range(excess):
            _processed_ids.pop()
    return False


async def fetch_unread_emails(token: str) -> list[dict]:
    """Fetch unread emails from the mailbox."""
    url = (
        f"{GRAPH_BASE}/users/{MAILBOX}/messages"
        f"?$filter=isRead eq false"
        f"&$top=10"
        f"&$orderby=receivedDateTime desc"
        f"&$select=id,subject,from,body,receivedDateTime"
    )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    client = _get_graph_client()
    resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        log.error(f"Graph API fetch error: {resp.status_code} {resp.text[:300]}")
        return []

    data = resp.json()
    return data.get("value", [])


async def mark_as_read(token: str, message_id: str):
    """Mark an email as read."""
    url = f"{GRAPH_BASE}/users/{MAILBOX}/messages/{message_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    client = _get_graph_client()
    await client.patch(url, headers=headers, json={"isRead": True})


async def send_email(token: str, to: str, subject: str, body_html: str, cc: str = ""):
    """Send an email via Microsoft Graph API. Optional cc recipient."""
    url = f"{GRAPH_BASE}/users/{MAILBOX}/sendMail"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    message = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": body_html},
        "toRecipients": [{"emailAddress": {"address": to}}],
    }
    if cc:
        message["ccRecipients"] = [{"emailAddress": {"address": cc}}]

    payload = {"message": message, "saveToSentItems": True}

    client = _get_graph_client()
    resp = await client.post(url, headers=headers, json=payload)

    if resp.status_code not in (200, 202):
        log.error(f"Send email failed: {resp.status_code} {resp.text[:300]}")
        return False
    cc_note = f" (cc: {cc})" if cc else ""
    log.info(f"Email sent to {to}{cc_note}: {subject}")
    return True


async def poll_loop(process_callback):
    """Main polling loop. Calls process_callback(sender, subject, body) for each unread email."""
    log.info(f"Email poller starting — mailbox: {MAILBOX}, interval: {POLL_INTERVAL}s")

    while True:
        try:
            stats["last_poll"] = datetime.utcnow().isoformat()
            token = await _get_token()
            if not token:
                log.warning("No token — skipping poll cycle")
                await asyncio.sleep(POLL_INTERVAL)
                continue

            emails = await fetch_unread_emails(token)
            log.info(f"Poll: {len(emails)} unread emails")

            for email in emails:
                msg_id = email["id"]
                subject = email.get("subject", "(no subject)")
                sender = email.get("from", {}).get("emailAddress", {}).get("address", "unknown")

                # Deduplication check
                if _track_processed(msg_id):
                    log.info(f"Skipping duplicate: {msg_id[:20]}...")
                    continue

                # Sender/subject filtering — don't waste Gemini tokens on junk
                if _should_skip(sender, subject):
                    log.info(f"Skipping filtered email from {sender}: {subject}")
                    stats["emails_skipped"] += 1
                    await mark_as_read(token, msg_id)
                    continue

                body_raw = email.get("body", {}).get("content", "")
                body_type = email.get("body", {}).get("contentType", "text")

                if body_type.lower() == "html":
                    body = _strip_html(body_raw)
                else:
                    body = body_raw

                log.info(f"Processing email from {sender}: {subject}")
                stats["last_email_from"] = sender

                try:
                    response_html = await process_callback(sender, subject, body)

                    # Route based on sender domain:
                    # Internal (@buntingmagnetics.com) → reply to sender, CC rclausing
                    # External → send to rclausing for review
                    is_internal = sender.lower().endswith("@buntingmagnetics.com")
                    if is_internal:
                        reply_subject = f"Re: {subject}"
                        await send_email(token, sender, reply_subject, response_html, cc=REVIEW_EMAIL)
                    else:
                        review_subject = f"[Maggie Spares] Re: {subject} (from {sender})"
                        await send_email(token, REVIEW_EMAIL, review_subject, response_html)

                    # Mark original as read
                    await mark_as_read(token, msg_id)
                    stats["emails_processed"] += 1

                except Exception as e:
                    log.error(f"Error processing email {msg_id}: {e}", exc_info=True)
                    stats["emails_errored"] += 1
                    # Still mark as read to avoid reprocessing
                    await mark_as_read(token, msg_id)

        except Exception as e:
            log.error(f"Poll loop error: {e}", exc_info=True)

        await asyncio.sleep(POLL_INTERVAL)
