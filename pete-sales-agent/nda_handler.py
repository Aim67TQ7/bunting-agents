#!/usr/bin/env python3
"""
NDA Pipeline Handler — triggers Stan to generate NDA pages, processes submissions.
Integrates with Pete's responder and daemon for autonomous NDA flow.
"""
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/opt/pete-sales")

from config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client
from email_handler import send_html_email
from campaign import build_html_email

logger = logging.getLogger("pete.nda")

SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV6bG1tZWdvd2dndWpwY256b2RhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE1ODUxNTYsImV4cCI6MjA2NzE2MTE1Nn0.HpQRBago6CgVyQyDfyaa47Fn9xbCzYz58xotLiWxMHM"
STAN_URL = "http://localhost:8406/ask"
NDA_TEMPLATE_PATH = "/opt/pete-sales/templates/nda_template.md"
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "robert@n0v8v.com")

db = None


def get_db():
    global db
    if db is None:
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
    return db


def slugify(name: str) -> str:
    """Convert company name to URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:50]


def has_existing_nda(email: str) -> bool:
    """Check if we've already sent an NDA to this email."""
    supa = get_db()
    result = (supa.table("companies")
              .select("id")
              .eq("signer_email", email)
              .execute())
    return len(result.data) > 0


def load_nda_template() -> str:
    """Load the NDA markdown template."""
    return Path(NDA_TEMPLATE_PATH).read_text(encoding="utf-8")


def build_stan_prompt(company_name: str, company_slug: str, nda_text: str) -> str:
    """Build the prompt for Stan to generate the NDA signing page."""
    return f"""Create a professional NDA signing page for {company_name}. This is a legal document signing page.

IMPORTANT: The app name must be "nda-{company_slug}"

The page must include:

1. HEADER: "Mutual Non-Disclosure Agreement" with n0v8v LLC branding. Subtitle: "Between n0v8v LLC and {company_name}"

2. NDA TEXT: Display the following NDA in a scrollable, readable format with proper formatting (headers, numbered sections, etc.):

{nda_text}

3. COMPANY INFORMATION FORM with these required fields:
   - Company Legal Name (pre-filled with "{company_name}")
   - Street Address
   - City
   - State
   - ZIP Code
   - Signer Full Name
   - Signer Title
   - Signer Email
   - Phone Number

4. DIGITAL SIGNATURE: A canvas element where the user draws their signature with mouse/touch. Include a "Clear Signature" button. The canvas should be 400x150 with a border.

5. SUBMIT BUTTON: "Sign and Submit Agreement"

6. ON SUBMIT: POST the form data as JSON to this exact URL:
   {SUPABASE_URL}/rest/v1/nda_submissions

   With these headers:
   - apikey: {SUPABASE_ANON_KEY}
   - Authorization: Bearer {SUPABASE_ANON_KEY}
   - Content-Type: application/json
   - Prefer: return=minimal

   The JSON body must include:
   - company_slug: "{company_slug}"
   - company_name: (from form)
   - address: (from form)
   - city: (from form)
   - state: (from form)
   - zip: (from form)
   - signer_name: (from form)
   - signer_email: (from form)
   - signer_title: (from form)
   - phone: (from form)
   - signature_data: (canvas toDataURL as base64 PNG string)

   On success: Show a green confirmation message "Your NDA has been signed and submitted. Pete from n0v8v will follow up shortly."
   On error: Show a red error message with retry option.

7. STYLING: Professional legal document look. Dark navy/gray color scheme. Clean typography. Mobile responsive. The NDA text section should have a max-height with scroll. The whole page should feel trustworthy and legitimate.

8. VALIDATION: All fields required. Email must be valid format. Signature canvas must not be blank (check that the user actually drew something).

9. Add a small footer: "n0v8v LLC | Business Velocity | Confidential"
"""


def trigger_nda_generation(company_name: str, signer_email: str, source_campaign: str = "") -> dict:
    """
    Generate an NDA page via Stan and create company record.
    Returns dict with status, url, and company_slug.
    """
    import requests

    company_slug = slugify(company_name)
    today = datetime.now().strftime("%B %d, %Y")

    # Load and fill NDA template (n0v8v side is pre-filled, company side left for form)
    nda_template = load_nda_template()
    nda_text = nda_template.replace("{effective_date}", today)
    nda_text = nda_text.replace("{company_name}", company_name)
    nda_text = nda_text.replace("{company_address}", "[To be provided by Counterparty]")

    # Create company record in Supabase
    supa = get_db()
    try:
        supa.table("companies").insert({
            "slug": company_slug,
            "company_name": company_name,
            "signer_email": signer_email,
            "nda_status": "pending",
            "source_campaign": source_campaign,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        # Might already exist — update instead
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            logger.info("Company %s already exists, updating", company_slug)
            supa.table("companies").update({
                "signer_email": signer_email,
                "nda_status": "pending",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("slug", company_slug).execute()
        else:
            logger.error("Failed to create company record: %s", e)
            return {"status": "error", "error": str(e)}

    # Build Stan prompt and generate the NDA page
    stan_prompt = build_stan_prompt(company_name, company_slug, nda_text)

    try:
        resp = requests.post(STAN_URL, json={
            "question": stan_prompt,
            "app_name": f"nda-{company_slug}",
        }, timeout=120)
        result = resp.json()

        if result.get("status") == "error":
            logger.error("Stan failed to generate NDA page: %s", result.get("error"))
            return {"status": "error", "error": result.get("error")}

        nda_url = result.get("url", f"https://nda-{company_slug}.gp3.app")
        logger.info("NDA page generated: %s", nda_url)

        # Update company record with URL
        supa.table("companies").update({
            "nda_page_url": nda_url,
            "nda_status": "sent",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("slug", company_slug).execute()

        return {
            "status": "ok",
            "url": nda_url,
            "company_slug": company_slug,
        }

    except Exception as e:
        logger.error("Failed to call Stan: %s", e)
        return {"status": "error", "error": str(e)}


def send_nda_email(to_email: str, to_name: str, company_name: str, nda_url: str):
    """Send the NDA link to the prospect."""
    subject = f"Mutual NDA — n0v8v LLC and {company_name}"

    body = f"""{to_name} —

Before we dive in, here is our mutual non-disclosure agreement. It protects both sides — your company's information stays yours, our methods stay ours, and anything we build together for you belongs to you.

Review and sign here: {nda_url}

Takes about 2 minutes. Once signed, I will get Robert on your calendar for a walkthrough.

Pete | n0v8v"""

    html = build_html_email(body, include_button=False)
    # Replace the URL in the HTML with a clickable link
    html = html.replace(
        nda_url,
        f'<a href="{nda_url}" style="color:#2563eb;text-decoration:underline;">{nda_url}</a>'
    )

    send_html_email(
        to=to_email,
        subject=subject,
        body_text=body,
        body_html=html,
    )
    logger.info("NDA email sent to %s (%s)", to_name, to_email)


def send_nda_signed_followup(to_email: str, to_name: str, company_name: str):
    """Send follow-up after NDA is signed."""
    subject = f"NDA signed — next steps for {company_name}"

    body = f"""{to_name} —

Got it — NDA is signed and filed. Appreciate you moving on that quickly.

I am getting Robert Clausing on your calendar for a 15-minute walkthrough. He will show you exactly how the automated AP follow-up works and what the first month looks like for {company_name}.

Expect his email within 24 hours with time options.

Pete | n0v8v"""

    html = build_html_email(body, include_button=False)
    send_html_email(to=to_email, subject=subject, body_text=body, body_html=html)
    logger.info("NDA signed follow-up sent to %s (%s)", to_name, to_email)


def notify_robert_nda_signed(company_name: str, signer_name: str, signer_email: str):
    """Notify Robert when an NDA is signed."""
    subject = f"NDA Signed: {company_name} — {signer_name}"
    body = f"""Robert —

{signer_name} from {company_name} just signed the mutual NDA.

Email: {signer_email}

Pete already sent them a follow-up letting them know you will reach out to schedule a walkthrough. Please send calendar options within 24 hours.

— Pete (automated)"""

    html = build_html_email(body, include_button=False)
    send_html_email(to=NOTIFICATION_EMAIL, subject=subject, body_text=body, body_html=html)
    logger.info("Robert notified about NDA from %s", company_name)


def check_nda_submissions():
    """
    Poll for new NDA submissions, process them into companies table,
    send follow-ups. Called from pete_daemon poll loop.
    """
    supa = get_db()

    # Get unprocessed submissions
    result = (supa.table("nda_submissions")
              .select("*")
              .eq("processed", False)
              .execute())

    if not result.data:
        return 0

    processed_count = 0

    for sub in result.data:
        try:
            company_slug = sub["company_slug"]
            company_name = sub["company_name"]
            signer_name = sub["signer_name"]
            signer_email = sub["signer_email"]

            logger.info("Processing NDA submission from %s (%s)", signer_name, company_name)

            # Update companies table with full info
            supa.table("companies").update({
                "company_name": company_name,
                "address": sub.get("address", ""),
                "city": sub.get("city", ""),
                "state": sub.get("state", ""),
                "zip": sub.get("zip", ""),
                "signer_name": signer_name,
                "signer_email": signer_email,
                "signer_title": sub.get("signer_title", ""),
                "phone": sub.get("phone", ""),
                "nda_status": "signed",
                "nda_signed_at": sub.get("signed_at", datetime.now(timezone.utc).isoformat()),
                "signature_data": sub.get("signature_data", ""),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("slug", company_slug).execute()

            # Send follow-up to signer
            send_nda_signed_followup(signer_email, signer_name, company_name)

            # Notify Robert
            notify_robert_nda_signed(company_name, signer_name, signer_email)

            # Mark submission as processed
            supa.table("nda_submissions").update({
                "processed": True,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", sub["id"]).execute()

            processed_count += 1
            logger.info("NDA submission processed for %s", company_name)

        except Exception as e:
            logger.error("Error processing NDA submission %s: %s", sub.get("id"), e)

    return processed_count


def lookup_company(email: str) -> dict | None:
    """Look up company info by signer email. Returns dict or None."""
    supa = get_db()
    result = (supa.table("companies")
              .select("*")
              .eq("signer_email", email)
              .limit(1)
              .execute())
    return result.data[0] if result.data else None
