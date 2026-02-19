"""
Email handler — uses gog CLI for all Gmail operations.
"""
import json
import os
import subprocess
import logging
from typing import Optional

from config import GOG_BIN, GOG_ACCOUNT

logger = logging.getLogger("pete.email")

# Environment for gog subprocess
GOG_ENV = {
    "HOME": "/root",
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "GOG_KEYRING_PASSWORD": "PeteAgent2026",
    "GOG_ACCOUNT": GOG_ACCOUNT,
}


def _run_gog(args: list[str], timeout: int = 30, results_only: bool = False) -> dict | list | str:
    """Run a gog command and return parsed JSON output."""
    cmd = [GOG_BIN, "-a", GOG_ACCOUNT, "-j", "--no-input"]
    if results_only:
        cmd.append("--results-only")
    cmd.extend(args)
    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=GOG_ENV)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        logger.error("gog error: %s", stderr)
        raise RuntimeError("gog failed: " + stderr[:500])
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.strip()


def search_emails(query: str, max_results: int = 10) -> list[dict]:
    """Search Gmail threads matching query. Returns list of thread summaries."""
    try:
        data = _run_gog(["gmail", "search", query, "--max=" + str(max_results)])
        # Full JSON wraps in {"threads": [...], "nextPageToken": ...}
        if isinstance(data, dict) and "threads" in data:
            return data["threads"]
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        logger.error("Search failed: %s", e)
        return []


def get_thread(thread_id: str) -> dict:
    """Get full thread with all messages."""
    data = _run_gog(["gmail", "thread", "get", thread_id])
    # Full JSON wraps in {"thread": {...}, "downloaded": ...}
    if isinstance(data, dict) and "thread" in data:
        return data["thread"]
    return data


def send_email(to: str, subject: str, body: str,
               reply_to_message_id: Optional[str] = None,
               thread_id: Optional[str] = None) -> dict:
    """Send or reply to an email (plain text)."""
    args = ["send", "--to", to, "--subject", subject, "--body", body]
    if reply_to_message_id:
        args.extend(["--reply-to-message-id", reply_to_message_id])
    elif thread_id:
        args.extend(["--thread-id", thread_id])
    args.append("-y")  # Skip confirmation
    return _run_gog(args, timeout=60)


def send_html_email(to: str, subject: str, body_text: str, body_html: str,
                    reply_to_message_id: Optional[str] = None,
                    thread_id: Optional[str] = None) -> dict:
    """Send an HTML email with plain text fallback."""
    import tempfile
    # Write HTML to temp file since gog --body-html takes a string
    args = ["send", "--to", to, "--subject", subject,
            "--body", body_text, "--body-html", body_html]
    if reply_to_message_id:
        args.extend(["--reply-to-message-id", reply_to_message_id])
    elif thread_id:
        args.extend(["--thread-id", thread_id])
    args.append("-y")
    return _run_gog(args, timeout=60)


def mark_as_read(thread_id: str) -> None:
    """Mark a thread as read by removing UNREAD label."""
    try:
        _run_gog(["gmail", "thread", "modify", thread_id, "--remove=UNREAD", "--force"], timeout=15)
    except Exception as e:
        logger.warning("Failed to mark %s as read: %s", thread_id, e)


def trash_thread(thread_id: str) -> None:
    """Move a thread to trash."""
    try:
        _run_gog(["gmail", "thread", "modify", thread_id, "--add=TRASH", "--force"], timeout=15)
    except Exception as e:
        logger.warning("Failed to trash %s: %s", thread_id, e)


def get_unread_threads(query: str = None, max_results: int = 10) -> list[dict]:
    """Get unread threads matching the query."""
    if query is None:
        query = "is:unread -from:me -category:promotions -category:social"
    return search_emails(query, max_results)
