#!/usr/bin/env python3
"""Send first 20 prospects from the CSV — live A/B campaign."""
import sys
import csv
import random
import time
sys.path.insert(0, "/opt/pete-sales")

from dotenv import load_dotenv
load_dotenv("/opt/pete-sales/.env")

from campaign import load_prospects, build_html_email
from email_handler import send_html_email

# Load first 20
prospects = load_prospects("/opt/pete-sales/campaigns/first_shot.csv", limit=20)
print(f"Loaded {len(prospects)} prospects")

# Two variants
variant_a_body = open("/opt/pete-sales/campaigns/variant_a.txt").read()
variant_b_body = open("/opt/pete-sales/campaigns/variant_b.txt").read()

subject_a = "You don't have to wait on AI anymore"
subject_b = "Quick question about outsourcing AI"

random.seed(42)
random.shuffle(prospects)

sent = 0
errors = 0

for i, p in enumerate(prospects):
    name = p["first_name"]
    email = p["email"]
    company = p["company"]
    variant = "A" if i < 10 else "B"

    body_template = variant_a_body if variant == "A" else variant_b_body
    subject = subject_a if variant == "A" else subject_b

    body = body_template.replace("{first_name}", name).replace("{company_name}", company)
    subject_filled = subject.replace("{first_name}", name).replace("{company_name}", company)
    html = build_html_email(body, include_button=True)
    plain = body + "\n\nPete | n0v8v\npete@by-pete.com"

    try:
        result = send_html_email(to=email, subject=subject_filled, body_text=plain, body_html=html)
        sent += 1
        print(f"{sent}/{len(prospects)} | {variant} | {name} | {email} | {company[:30]}")
        if i < len(prospects) - 1:
            time.sleep(30)
    except Exception as e:
        errors += 1
        print(f"ERROR | {variant} | {name} | {email} : {str(e)[:80]}")

print()
print(f"Done: {sent} sent, {errors} errors")
