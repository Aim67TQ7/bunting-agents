"""
Intent classifier — uses Gemini 2.5 Flash to classify inbound email intent.
"""
import logging
import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL
from knowledge import INTENT_CLASSIFIER_PROMPT

logger = logging.getLogger("pete.classifier")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

VALID_INTENTS = {
    "INTERESTED", "DEMO_REQUEST", "PRICING", "OBJECTION",
    "NOT_INTERESTED", "QUESTION", "HUMAN_REQUEST", "SPAM",
    "EXISTING_CLIENT", "REFERRAL"
}


def classify_intent(sender: str, subject: str, body: str) -> str:
    """Classify the intent of an inbound email."""
    prompt = INTENT_CLASSIFIER_PROMPT.format(
        sender=sender, subject=subject, body=body[:2000]
    )
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=50,
                temperature=0,
            )
        )
        intent = response.text.strip().upper()
        # Clean up — sometimes model returns extra text
        for valid in VALID_INTENTS:
            if valid in intent:
                return valid
        logger.warning(f"Unknown intent '{intent}', defaulting to QUESTION")
        return "QUESTION"
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return "QUESTION"  # Safe fallback
