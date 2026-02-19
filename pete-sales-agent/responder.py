"""
Response generator — uses Gemini 2.5 Flash to generate contextually appropriate sales responses.
"""
import logging
import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL
from knowledge import SYSTEM_PROMPT, RESPONSE_TEMPLATES

logger = logging.getLogger("pete.responder")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=SYSTEM_PROMPT)


def generate_response(intent: str, sender: str, subject: str, body: str,
                      conversation_history: list[dict] = None) -> str:
    """Generate a contextual email response based on intent and conversation history."""
    template = RESPONSE_TEMPLATES.get(intent, RESPONSE_TEMPLATES["QUESTION"])

    # Build conversation context
    context_block = ""
    if conversation_history:
        context_block = "\n\nPREVIOUS MESSAGES IN THIS THREAD:\n"
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            direction = "FROM PROSPECT" if msg.get("inbound") else "FROM PETE"
            context_block += f"\n--- {direction} ---\n{msg.get('body', '')[:500]}\n"

    user_prompt = f"""{template}

CURRENT EMAIL:
From: {sender}
Subject: {subject}
Body:
{body[:2000]}
{context_block}

Generate ONLY the email body. No subject line. No "Subject:" prefix. Start with the greeting."""

    try:
        response = model.generate_content(
            user_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=500,
                temperature=0.7,
            )
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return None


def generate_morning_report(stats: dict, threads: list[dict]) -> str:
    """Generate the daily morning report for Robert."""
    from knowledge import MORNING_REPORT_TEMPLATE
    from datetime import datetime

    thread_details = ""
    needs_attention = ""
    actions = ""

    for t in threads:
        status_emoji = {"active": "🟢", "demo_booked": "🎯", "escalated": "🔴"}.get(t.get("status"), "⚪")
        thread_details += f"- {status_emoji} {t.get('prospect_name', 'Unknown')} ({t.get('prospect_email', '')}): {t.get('last_intent', 'N/A')} — {t.get('message_count', 0)} messages\n"

        if t.get("needs_attention"):
            needs_attention += f"- {t.get('prospect_name')}: {t.get('attention_reason', 'Review needed')}\n"

    if not needs_attention:
        needs_attention = "None — all threads handled autonomously."

    return MORNING_REPORT_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d"),
        active_threads=stats.get("active_threads", 0),
        new_inbound=stats.get("new_inbound", 0),
        responses_sent=stats.get("responses_sent", 0),
        demos_booked=stats.get("demos_booked", 0),
        escalations=stats.get("escalations", 0),
        thread_details=thread_details or "No active threads.",
        actions=actions or "Standard operations.",
        needs_attention=needs_attention,
    )
