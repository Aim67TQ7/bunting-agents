"""Email Responder — formats AI-generated responses as HTML emails."""

import logging
import re

log = logging.getLogger("maggie-spares.responder")


def markdown_to_html(md: str) -> str:
    """Simple markdown to HTML conversion for email bodies."""
    html = md

    # Headers
    html = re.sub(r"^### (.+)$", r"<h3 style='color:#1a365d;margin:16px 0 8px;'>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2 style='color:#1a365d;margin:18px 0 10px;'>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1 style='color:#1a365d;margin:20px 0 12px;'>\1</h1>", html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Bullet lists
    html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"(<li>.*</li>\n?)+", lambda m: f"<ul style='margin:8px 0;padding-left:20px;'>{m.group(0)}</ul>", html)

    # Paragraphs (double newline)
    html = re.sub(r"\n\n", "</p><p>", html)
    html = re.sub(r"\n", "<br>", html)
    html = f"<p>{html}</p>"

    # Clean up empty paragraphs
    html = re.sub(r"<p>\s*</p>", "", html)

    return html


def format_review_email(
    sender: str,
    subject: str,
    original_body: str,
    ai_response: str,
    queries_used: list[str],
) -> str:
    """Format the complete review email as HTML."""
    ai_html = markdown_to_html(ai_response)
    baqs_list = ", ".join(queries_used) if queries_used else "None"

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 700px; margin: 0 auto; color: #1a202c; line-height: 1.6;">

  <div style="background: linear-gradient(135deg, #1a365d, #2563eb); color: white; padding: 20px 24px; border-radius: 8px 8px 0 0;">
    <h1 style="margin: 0; font-size: 20px;">Maggie Spares — ERP Query Result</h1>
    <p style="margin: 4px 0 0; opacity: 0.85; font-size: 13px;">Automated Epicor data lookup for review</p>
  </div>

  <div style="border: 1px solid #e2e8f0; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">

    <div style="background: #f7fafc; border-left: 4px solid #2563eb; padding: 12px 16px; margin-bottom: 20px; border-radius: 0 4px 4px 0;">
      <p style="margin: 0; font-size: 12px; color: #718096; text-transform: uppercase; letter-spacing: 0.5px;">Original Email</p>
      <p style="margin: 4px 0 0; font-size: 14px;"><strong>From:</strong> {sender}</p>
      <p style="margin: 2px 0 0; font-size: 14px;"><strong>Subject:</strong> {subject}</p>
      <p style="margin: 8px 0 0; font-size: 13px; color: #4a5568;">{original_body[:500]}{'...' if len(original_body) > 500 else ''}</p>
    </div>

    <div style="margin-bottom: 20px;">
      {ai_html}
    </div>

    <div style="background: #edf2f7; padding: 10px 14px; border-radius: 4px; font-size: 12px; color: #718096; margin-top: 20px;">
      <strong>BAQs consulted:</strong> {baqs_list}<br>
      <strong>Action required:</strong> Review this data and respond to {sender} if appropriate.
    </div>

  </div>

  <p style="text-align: center; font-size: 11px; color: #a0aec0; margin-top: 16px;">
    Maggie Spares — Automated ERP Query Assistant | Bunting Magnetics
  </p>

</body>
</html>
"""
