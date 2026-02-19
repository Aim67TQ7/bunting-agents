"""Drafting logic for customer reactivation emails."""

from __future__ import annotations

from datetime import datetime, timezone

from models import CustomerRecord, DraftEmail, WearPartFinding


def build_reactivation_draft(
    customer: CustomerRecord,
    wear_parts: list[WearPartFinding],
    order_summary: str = "",
    campaign_id: str = "",
) -> DraftEmail:
    years = customer.years_since_last_work
    years_text = f"{years:.0f}" if years is not None else "several"
    greeting_name = customer.contact_name or customer.customer_name
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    subject = f"Draft: Reconnect with {customer.customer_name} — parts & service support"

    # --- Build HTML email ---
    parts_html = _build_parts_html(wear_parts)
    order_html = _build_order_html(order_summary)

    html = (
        "<p>Hi Rob,</p>"
        "<p>Below is a draft reactivation email for your review. "
        "Edit as needed, then forward to the customer.</p>"
        "<hr style='border:1px solid #ccc;'>"
        f"<p>Hi {greeting_name},</p>"
        "<p>I hope this finds you well. I'm reaching out from Bunting Magnetics — we noticed "
        f"it's been about {years_text} years since we last worked together, and wanted to check in.</p>"

        # Section 1: Equipment & Parts
        "<h3 style='color:#1a5276;margin-top:24px;'>Your Equipment May Need Attention</h3>"
        "<p>Based on your previous order history with us, there are likely routine wear "
        "components that are due for inspection or replacement. Catching these early helps "
        "avoid unplanned downtime.</p>"
        f"{order_html}"
        f"{parts_html}"

        # Section 2: Field Technical Support
        "<h3 style='color:#1a5276;margin-top:24px;'>On-Site Technical Support</h3>"
        "<p>Our field service team provides on-site equipment reviews, maintenance, and "
        "optimization. They're currently scheduling into <strong>late June</strong>, but if "
        "you're interested in having our engineers visit your facility for a full equipment "
        "assessment, we'd love to get you on the calendar.</p>"
        "<p>A typical visit includes:</p>"
        "<ul>"
        "<li>Complete equipment inspection and performance evaluation</li>"
        "<li>Wear component assessment with replacement recommendations</li>"
        "<li>Process optimization suggestions</li>"
        "</ul>"

        # Section 3: CTA
        "<h3 style='color:#1a5276;margin-top:24px;'>How Can We Help?</h3>"
        "<p>If any of this is useful, just reply to this email with:</p>"
        "<ul>"
        "<li>Your current equipment model and any symptoms you're seeing, and I'll pull up your complete parts list</li>"
        "<li>Or let me know if you'd like to schedule a field service visit</li>"
        "</ul>"
        "<p>Either way, we're here to help keep your equipment running.</p>"

        "<p>Best regards,<br>"
        "Maggie<br>"
        "<span style='color:#666;'>Bunting Magnetics</span></p>"
        "<hr style='border:1px solid #ccc;'>"
        f"<p style='font-size:11px;color:#999;'>Campaign: {campaign_id} | Generated: {now_iso}</p>"
    )

    # --- Build plain text version ---
    parts_text = _build_parts_text(wear_parts)
    order_text = _build_order_text(order_summary)

    text = (
        "Hi Rob,\n\n"
        "Below is a draft reactivation email for your review.\n"
        "Edit as needed, then forward to the customer.\n\n"
        "---\n\n"
        f"Hi {greeting_name},\n\n"
        "I hope this finds you well. I'm reaching out from Bunting Magnetics — we noticed "
        f"it's been about {years_text} years since we last worked together, and wanted to check in.\n\n"

        "YOUR EQUIPMENT MAY NEED ATTENTION\n\n"
        "Based on your previous order history with us, there are likely routine wear "
        "components that are due for inspection or replacement.\n\n"
        f"{order_text}"
        f"{parts_text}\n\n"

        "ON-SITE TECHNICAL SUPPORT\n\n"
        "Our field service team provides on-site equipment reviews, maintenance, and "
        "optimization. They're currently scheduling into late June, but if you're interested "
        "in having our engineers visit your facility, we'd love to get you on the calendar.\n\n"
        "A typical visit includes:\n"
        "- Complete equipment inspection and performance evaluation\n"
        "- Wear component assessment with replacement recommendations\n"
        "- Process optimization suggestions\n\n"

        "HOW CAN WE HELP?\n\n"
        "Just reply with your current equipment model and any symptoms, "
        "and I'll pull up your complete parts list. Or let me know if you'd "
        "like to schedule a field service visit.\n\n"
        "Best regards,\n"
        "Maggie\n"
        "Bunting Magnetics\n\n"
        f"---\nCampaign: {campaign_id}\n"
    )

    return DraftEmail(
        customer_name=customer.customer_name,
        recipient_hint=customer.contact_email or customer.customer_name,
        subject=subject,
        html_body=html,
        text_body=text,
        campaign_id=campaign_id,
        supporting_parts=wear_parts,
        order_summary=order_summary,
    )


# ---------------------------------------------------------------------------
# Parts table builders
# ---------------------------------------------------------------------------

def _build_parts_html(parts: list[WearPartFinding]) -> str:
    if not parts:
        return (
            "<p><em>We weren't able to pull specific part numbers from your last order "
            "automatically, but reply with your equipment details and I can dig deeper.</em></p>"
        )

    rows = []
    for p in parts:
        pn = p.part_number or "—"
        vendor = f"<td style='padding:6px 10px;border:1px solid #ddd;'>{p.vendor}</td>" if p.vendor else ""
        rows.append(
            f"<tr>"
            f"<td style='padding:6px 10px;border:1px solid #ddd;font-family:monospace;'>{pn}</td>"
            f"<td style='padding:6px 10px;border:1px solid #ddd;'>{p.description}</td>"
            f"{vendor}"
            f"</tr>"
        )

    has_vendor = any(p.vendor for p in parts)
    vendor_header = "<th style='text-align:left;padding:6px 10px;border:1px solid #ddd;background:#f3f4f6;'>Vendor</th>" if has_vendor else ""

    return (
        "<p><strong>Potential wear components to review:</strong></p>"
        "<table style='border-collapse:collapse;width:100%;font-size:13px;margin-bottom:16px;'>"
        "<thead><tr>"
        "<th style='text-align:left;padding:6px 10px;border:1px solid #ddd;background:#f3f4f6;'>Part #</th>"
        "<th style='text-align:left;padding:6px 10px;border:1px solid #ddd;background:#f3f4f6;'>Description</th>"
        f"{vendor_header}"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _build_parts_text(parts: list[WearPartFinding]) -> str:
    if not parts:
        return "Specific part numbers were not available from the initial lookup."
    lines = ["Potential wear components to review:"]
    for p in parts:
        pn = p.part_number or "TBD"
        vendor = f" (vendor: {p.vendor})" if p.vendor else ""
        lines.append(f"  - {pn}: {p.description}{vendor}")
    return "\n".join(lines)


def _build_order_html(order_summary: str) -> str:
    if not order_summary:
        return ""
    return (
        "<p style='background:#f8f9fa;padding:10px 14px;border-left:3px solid #1a5276;margin:12px 0;'>"
        f"<strong>From your records:</strong> {order_summary}</p>"
    )


def _build_order_text(order_summary: str) -> str:
    if not order_summary:
        return ""
    return f"From your records: {order_summary}\n\n"
