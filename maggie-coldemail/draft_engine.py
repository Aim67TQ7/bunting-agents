"""Drafting logic for customer reactivation emails."""

from __future__ import annotations

from datetime import datetime

from models import CustomerRecord, DraftEmail, WearPartFinding


def build_reactivation_draft(
    customer: CustomerRecord,
    wear_parts: list[WearPartFinding],
    campaign_id: str,
) -> DraftEmail:
    years = customer.years_since_last_work
    years_text = f"{years:.1f}" if years is not None else "about 4"
    subject = f"Draft: Reconnect with {customer.customer_name} - service and wear-part support"

    parts_html = _build_parts_html(wear_parts)
    parts_text = _build_parts_text(wear_parts)
    greeting_name = customer.contact_name or customer.customer_name

    html = (
        "<p>Hi Rob,</p>"
        "<p>Below is a draft customer outreach email for your review.</p>"
        "<hr>"
        f"<p>Hi {greeting_name},</p>"
        "<p>I hope you are doing well. I am reaching out from Bunting Magnetics because we noticed "
        f"your team did business with us between 2018 and 2022, and it has been roughly {years_text} years "
        "since our last project together.</p>"
        "<p>Based on your prior order history, there may be routine wear components worth checking now to help "
        "avoid unplanned downtime.</p>"
        f"{parts_html}"
        "<p>If helpful, we can schedule a Bunting service team visit in about 8 weeks, or we can support you "
        "by email with any immediate questions.</p>"
        "<p>If you would like, just reply with your current equipment model and any symptoms you are seeing, "
        "and we can suggest next steps.</p>"
        "<p>Best regards,<br>"
        "Maggie<br>"
        "Bunting Magnetics</p>"
        "<hr>"
        f"<p style='font-size:12px;color:#666;'>Campaign ID: {campaign_id} | Generated: {datetime.utcnow().isoformat()}Z</p>"
    )

    text = (
        "Hi Rob,\n\n"
        "Below is a draft customer outreach email for your review.\n\n"
        f"Hi {greeting_name},\n\n"
        "I hope you are doing well. I am reaching out from Bunting Magnetics because we noticed "
        f"your team did business with us between 2018 and 2022, and it has been roughly {years_text} years "
        "since our last project together.\n\n"
        "Based on your prior order history, there may be routine wear components worth checking now to help avoid downtime.\n\n"
        f"{parts_text}\n\n"
        "If helpful, we can schedule a Bunting service team visit in about 8 weeks, or we can support you by email.\n"
        "Reply with any questions and we can help.\n\n"
        "Best regards,\n"
        "Maggie\n"
        "Bunting Magnetics\n\n"
        f"Campaign ID: {campaign_id}\n"
    )

    return DraftEmail(
        customer_name=customer.customer_name,
        recipient_hint=customer.contact_email or customer.customer_name,
        subject=subject,
        html_body=html,
        text_body=text,
        campaign_id=campaign_id,
        supporting_parts=wear_parts,
    )


def _build_parts_html(parts: list[WearPartFinding]) -> str:
    if not parts:
        return (
            "<p><strong>Potential replacement components:</strong> "
            "No specific part list was available from the initial lookup; "
            "Maggie can pull a deeper review with Magnus on reply.</p>"
        )

    rows = []
    for p in parts:
        pn = p.part_number or "TBD"
        reason = f"<br><span style='color:#555;font-size:12px;'>{p.reason}</span>" if p.reason else ""
        rows.append(
            f"<tr><td style='padding:8px;border:1px solid #ddd;'>{pn}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;'>{p.description}{reason}</td></tr>"
        )
    table = "".join(rows)
    return (
        "<p><strong>Potential wear components to review:</strong></p>"
        "<table style='border-collapse:collapse;width:100%;font-size:14px;'>"
        "<thead><tr>"
        "<th style='text-align:left;padding:8px;border:1px solid #ddd;background:#f3f4f6;'>Part</th>"
        "<th style='text-align:left;padding:8px;border:1px solid #ddd;background:#f3f4f6;'>Description</th>"
        "</tr></thead>"
        f"<tbody>{table}</tbody></table>"
    )


def _build_parts_text(parts: list[WearPartFinding]) -> str:
    if not parts:
        return "Potential replacement components: no specific list available yet."
    lines = ["Potential wear components to review:"]
    for p in parts:
        pn = p.part_number or "TBD"
        reason = f" ({p.reason})" if p.reason else ""
        lines.append(f"- {pn}: {p.description}{reason}")
    return "\n".join(lines)
