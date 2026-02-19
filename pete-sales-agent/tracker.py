"""
Conversation tracker — Supabase backend for thread management.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client

from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger("pete.tracker")

_client = None


def get_client():
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def upsert_thread(thread_id: str, prospect_email: str, prospect_name: str,
                  subject: str, intent: str, status: str = "active",
                  last_message_body: str = "", inbound: bool = True) -> dict:
    """Create or update a conversation thread."""
    db = get_client()
    now = datetime.now(timezone.utc).isoformat()

    # Check if thread exists
    existing = db.table("pete_conversations").select("*").eq("thread_id", thread_id).execute()

    if existing.data:
        # Update existing thread
        update = {
            "last_intent": intent,
            "last_message_at": now,
            "message_count": existing.data[0]["message_count"] + 1,
            "status": status,
            "updated_at": now,
        }
        if intent == "DEMO_REQUEST":
            update["status"] = "demo_booked"
            update["demo_requested_at"] = now
        elif intent == "HUMAN_REQUEST":
            update["status"] = "escalated"
            update["escalated_at"] = now
        elif intent == "NOT_INTERESTED":
            update["status"] = "closed_lost"

        result = db.table("pete_conversations").update(update).eq("thread_id", thread_id).execute()
        return result.data[0] if result.data else {}
    else:
        # Create new thread
        record = {
            "thread_id": thread_id,
            "prospect_email": prospect_email,
            "prospect_name": prospect_name,
            "subject": subject,
            "first_intent": intent,
            "last_intent": intent,
            "status": status,
            "message_count": 1,
            "created_at": now,
            "updated_at": now,
            "last_message_at": now,
        }
        result = db.table("pete_conversations").insert(record).execute()
        return result.data[0] if result.data else {}


def log_message(thread_id: str, message_id: str, sender: str, body: str,
                intent: str, response: str = None, inbound: bool = True) -> dict:
    """Log an individual message in a thread."""
    db = get_client()
    record = {
        "thread_id": thread_id,
        "message_id": message_id,
        "sender": sender,
        "body": body[:5000],
        "intent": intent,
        "response_sent": response[:5000] if response else None,
        "inbound": inbound,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = db.table("pete_messages").insert(record).execute()
    return result.data[0] if result.data else {}


def get_thread_history(thread_id: str) -> list[dict]:
    """Get conversation history for a thread."""
    db = get_client()
    result = (db.table("pete_messages")
              .select("*")
              .eq("thread_id", thread_id)
              .order("created_at")
              .execute())
    return result.data or []


def get_active_threads() -> list[dict]:
    """Get all active conversation threads."""
    db = get_client()
    result = (db.table("pete_conversations")
              .select("*")
              .in_("status", ["active", "demo_booked", "escalated"])
              .order("last_message_at", desc=True)
              .execute())
    return result.data or []


def get_daily_stats() -> dict:
    """Get stats for today's morning report."""
    db = get_client()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    active = db.table("pete_conversations").select("*", count="exact").in_("status", ["active", "demo_booked"]).execute()
    new_today = db.table("pete_messages").select("*", count="exact").eq("inbound", True).gte("created_at", today).execute()
    sent_today = db.table("pete_messages").select("*", count="exact").eq("inbound", False).gte("created_at", today).execute()
    demos = db.table("pete_conversations").select("*", count="exact").eq("status", "demo_booked").gte("updated_at", today).execute()
    escalations = db.table("pete_conversations").select("*", count="exact").eq("status", "escalated").gte("updated_at", today).execute()

    return {
        "active_threads": active.count or 0,
        "new_inbound": new_today.count or 0,
        "responses_sent": sent_today.count or 0,
        "demos_booked": demos.count or 0,
        "escalations": escalations.count or 0,
    }


def is_thread_processed(thread_id: str, message_id: str) -> bool:
    """Check if a specific message has already been processed."""
    db = get_client()
    result = (db.table("pete_messages")
              .select("id")
              .eq("message_id", message_id)
              .execute())
    return len(result.data) > 0
