#!/usr/bin/env python3
"""
Pete A/B Campaign Engine — batch outbound with variant tracking.
Reads prospects from CSV, splits into A/B groups, sends staggered, tracks everything.
"""
import csv
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/opt/pete-sales")

from config import SUPABASE_URL, SUPABASE_KEY, GOG_ACCOUNT
from email_handler import send_email, send_html_email
from supabase import create_client

logger = logging.getLogger("pete.campaign")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                    handlers=[logging.FileHandler("/opt/pete-sales/logs/campaign.log"), logging.StreamHandler()])

db = None

def get_db():
    global db
    if db is None:
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
    return db


# ---------------------------------------------------------------------------
# HTML email builder with "Tell me more" mailto button
# ---------------------------------------------------------------------------

BUTTON_HTML = """<div style="margin:24px 0;text-align:center;">
<a href="mailto:pete@by-pete.com?subject=Tell%20me%20more%20about%20AI%20outsourcing&body=I%27d%20like%20to%20learn%20more%20about%20what%20you%20do."
   style="background-color:#2563eb;color:#ffffff;padding:14px 28px;text-decoration:none;border-radius:6px;display:inline-block;font-family:Arial,sans-serif;font-size:16px;font-weight:600;">
Tell me more</a></div>"""

EMAIL_WRAPPER = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f5f5;padding:20px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;">
<tr><td style="padding:32px 40px;color:#1a1a1a;font-size:15px;line-height:24px;">
{body_html}
{button}
<p style="color:#1a1a1a;margin-top:24px;">Pete | n0v8v<br>
<span style="color:#666;font-size:13px;">pete@by-pete.com</span></p>
</td></tr>
</table>
<table width="600" cellpadding="0" cellspacing="0">
<tr><td style="padding:16px 40px;color:#999;font-size:12px;line-height:18px;text-align:center;">
n0v8v | Business Velocity<br>
AI operations for manufacturers
</td></tr></table>
</td></tr></table></body></html>"""


def text_to_html(text: str) -> str:
    """Convert plain text email body to simple HTML paragraphs."""
    paragraphs = text.strip().split("\n\n")
    html_parts = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # Handle bullet lines
        lines = p.split("\n")
        if any(line.strip().startswith("- ") for line in lines):
            items = []
            for line in lines:
                line = line.strip()
                if line.startswith("- "):
                    items.append("<li>" + line[2:] + "</li>")
                else:
                    items.append("<li>" + line + "</li>")
            html_parts.append('<ul style="padding-left:20px;margin:16px 0;">' + "".join(items) + "</ul>")
        else:
            html_parts.append('<p style="margin:16px 0;">' + "<br>".join(lines) + "</p>")
    return "".join(html_parts)


def build_html_email(body_text: str, include_button: bool = True) -> str:
    """Build full HTML email from plain text body."""
    body_html = text_to_html(body_text)
    button = BUTTON_HTML if include_button else ""
    return EMAIL_WRAPPER.format(body_html=body_html, button=button)


# ---------------------------------------------------------------------------
# Campaign management
# ---------------------------------------------------------------------------

def load_prospects(csv_path: str, limit: int = 0) -> list[dict]:
    """Load prospects from CSV. Handles common column name variations."""
    prospects = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize column names (strip whitespace, lowercase)
            clean = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items()}
            # Try common column name variations
            name = (clean.get("first_name") or clean.get("firstname") or
                    clean.get("first") or clean.get("name", "").split()[0] if clean.get("name") else
                    clean.get("contact", ""))
            prospect = {
                "first_name": name.strip().title() if name else "",
                "email": clean.get("email") or clean.get("email_address") or clean.get("e-mail", ""),
                "company": clean.get("company") or clean.get("company_name") or clean.get("organization", ""),
            }
            if prospect["email"] and "@" in prospect["email"]:
                prospects.append(prospect)
            else:
                logger.warning("Skipping row with no valid email: %s", clean)
            if limit and len(prospects) >= limit:
                break
    return prospects


def create_campaign(name: str, variant_a_subject: str, variant_a_body: str,
                    variant_b_subject: str, variant_b_body: str,
                    prospects: list[dict], dry_run: bool = True) -> str:
    """Create a campaign, assign variants, store in Supabase."""
    campaign_id = f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Shuffle and split A/B
    random.shuffle(prospects)
    midpoint = len(prospects) // 2

    records = []
    for i, prospect in enumerate(prospects):
        variant = "A" if i < midpoint else "B"
        records.append({
            "campaign_id": campaign_id,
            "campaign_name": name,
            "variant": variant,
            "prospect_email": prospect["email"],
            "prospect_name": prospect["first_name"],
            "company": prospect["company"],
            "subject": variant_a_subject if variant == "A" else variant_b_subject,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Store campaign in Supabase
    supa = get_db()
    supa.table("pete_campaigns").insert(records).execute()

    # Store variant bodies for reference
    supa.table("pete_campaign_variants").insert([
        {"campaign_id": campaign_id, "variant": "A", "subject": variant_a_subject, "body": variant_a_body},
        {"campaign_id": campaign_id, "variant": "B", "subject": variant_b_subject, "body": variant_b_body},
    ]).execute()

    logger.info("Campaign '%s' created: %d prospects (%d A, %d B)",
                name, len(prospects), midpoint, len(prospects) - midpoint)
    return campaign_id


def send_campaign(campaign_id: str, variant_a_body: str, variant_b_body: str,
                  stagger_seconds: int = 45, dry_run: bool = True) -> dict:
    """Send all pending emails for a campaign with staggering."""
    supa = get_db()
    pending = (supa.table("pete_campaigns")
               .select("*")
               .eq("campaign_id", campaign_id)
               .eq("status", "pending")
               .execute())

    stats = {"sent": 0, "errors": 0, "skipped": 0}

    for record in pending.data:
        prospect_email = record["prospect_email"]
        prospect_name = record["prospect_name"]
        company = record["company"]
        variant = record["variant"]
        subject = record["subject"]

        # Fill template
        body_template = variant_a_body if variant == "A" else variant_b_body
        body = body_template.replace("{first_name}", prospect_name).replace("{company_name}", company)

        # Build HTML version with button
        html_body = build_html_email(body, include_button=True)

        if dry_run:
            logger.info("[DRY RUN] Would send to %s (%s) — Variant %s — Subject: %s",
                        prospect_name, prospect_email, variant, subject)
            stats["skipped"] += 1
            continue

        try:
            send_html_email(
                to=prospect_email,
                subject=subject.replace("{first_name}", prospect_name).replace("{company_name}", company),
                body_text=body,  # Plain text fallback
                body_html=html_body,
            )
            # Update status
            supa.table("pete_campaigns").update({
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", record["id"]).execute()

            stats["sent"] += 1
            logger.info("Sent to %s (%s) — Variant %s", prospect_name, prospect_email, variant)

            # Stagger to avoid spam flags
            if stagger_seconds > 0:
                time.sleep(stagger_seconds)

        except Exception as e:
            logger.error("Failed to send to %s: %s", prospect_email, e)
            supa.table("pete_campaigns").update({
                "status": "error",
                "error_message": str(e)[:500],
            }).eq("id", record["id"]).execute()
            stats["errors"] += 1

    logger.info("Campaign %s complete: %s", campaign_id, stats)
    return stats


def campaign_report(campaign_id: str) -> str:
    """Generate A/B performance report for a campaign."""
    supa = get_db()

    records = (supa.table("pete_campaigns")
               .select("*")
               .eq("campaign_id", campaign_id)
               .execute()).data

    # Count by variant and status
    results = {"A": {"sent": 0, "replied": 0, "demo": 0}, "B": {"sent": 0, "replied": 0, "demo": 0}}
    for r in records:
        v = r["variant"]
        if r["status"] == "sent":
            results[v]["sent"] += 1
        if r.get("replied"):
            results[v]["replied"] += 1
        if r.get("demo_booked"):
            results[v]["demo"] += 1

    report = f"""A/B Campaign Report — {campaign_id}
{'='*50}

Variant A: {results['A']['sent']} sent | {results['A']['replied']} replied ({_pct(results['A']['replied'], results['A']['sent'])}%) | {results['A']['demo']} demos
Variant B: {results['B']['sent']} sent | {results['B']['replied']} replied ({_pct(results['B']['replied'], results['B']['sent'])}%) | {results['B']['demo']} demos

Winner: {'A' if results['A']['replied'] > results['B']['replied'] else 'B' if results['B']['replied'] > results['A']['replied'] else 'Tie'}
"""
    return report


def _pct(num, den):
    return round(num / den * 100, 1) if den > 0 else 0


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pete A/B Campaign Engine")
    sub = parser.add_subparsers(dest="command")

    # Create campaign
    create = sub.add_parser("create", help="Create a new campaign from CSV")
    create.add_argument("--csv", required=True, help="Path to prospect CSV")
    create.add_argument("--name", required=True, help="Campaign name")
    create.add_argument("--subject-a", required=True, help="Subject line for Variant A")
    create.add_argument("--subject-b", required=True, help="Subject line for Variant B")
    create.add_argument("--body-a", required=True, help="Path to text file for Variant A body")
    create.add_argument("--body-b", required=True, help="Path to text file for Variant B body")

    # Send campaign
    send = sub.add_parser("send", help="Send a campaign")
    send.add_argument("--id", required=True, help="Campaign ID")
    send.add_argument("--body-a", required=True, help="Path to Variant A body file")
    send.add_argument("--body-b", required=True, help="Path to Variant B body file")
    send.add_argument("--stagger", type=int, default=45, help="Seconds between sends")
    send.add_argument("--live", action="store_true", help="Actually send (default is dry run)")

    # Report
    report = sub.add_parser("report", help="Get campaign report")
    report.add_argument("--id", required=True, help="Campaign ID")

    args = parser.parse_args()

    if args.command == "create":
        prospects = load_prospects(args.csv)
        body_a = Path(args.body_a).read_text()
        body_b = Path(args.body_b).read_text()
        cid = create_campaign(args.name, args.subject_a, body_a, args.subject_b, body_b, prospects)
        print(f"Campaign created: {cid}")
        print(f"Prospects loaded: {len(prospects)}")

    elif args.command == "send":
        body_a = Path(args.body_a).read_text()
        body_b = Path(args.body_b).read_text()
        stats = send_campaign(args.id, body_a, body_b,
                              stagger_seconds=args.stagger, dry_run=not args.live)
        print(f"Results: {stats}")

    elif args.command == "report":
        print(campaign_report(args.id))

    else:
        parser.print_help()
