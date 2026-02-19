"""Campaign orchestration for Maggie cold-email reactivation workflow."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from draft_engine import build_reactivation_draft
from mailer import SmtpMailer
from models import CampaignRecord, CustomerRecord
from spares_client import SparesClient
from supabase_client import SupabaseClient

log = logging.getLogger("maggie-coldemail.runner")


class CampaignRunner:
    def __init__(
        self,
        supabase_client: SupabaseClient,
        spares_client: SparesClient,
        mailer: SmtpMailer,
        reviewer_email: str,
        state_path: str,
    ) -> None:
        self.supabase_client = supabase_client
        self.spares_client = spares_client
        self.mailer = mailer
        self.reviewer_email = reviewer_email
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    async def run(self, dry_run: bool, limit: int) -> dict:
        now = datetime.now(timezone.utc)
        campaign_id = now.strftime("reactivation-%Y%m%d-%H%M%S")
        state = self._load_state()
        sent_keys: set[str] = set(state.get("sent_keys", []))

        customers = await self.supabase_client.fetch_customers(limit=limit)
        eligible = [c for c in customers if _is_eligible(c)]

        processed = 0
        skipped_seen = 0
        drafted = 0
        enriched = 0
        errors = 0

        for customer in eligible:
            dedupe_key = _dedupe_key(customer)
            if dedupe_key in sent_keys:
                skipped_seen += 1
                continue

            # Enrich via maggie-spares (real Epicor data)
            try:
                wear_parts = await self.spares_client.get_wear_part_candidates(customer)
                order_summary = await self.spares_client.get_order_summary(customer)
                if wear_parts or order_summary:
                    enriched += 1
            except Exception as exc:
                log.warning("Enrichment failed for %s: %s", customer.customer_name, exc)
                wear_parts = []
                order_summary = ""

            draft = build_reactivation_draft(
                customer,
                wear_parts,
                order_summary=order_summary,
                campaign_id=campaign_id,
            )

            if not dry_run:
                try:
                    self.mailer.send_draft(draft, reviewer_email=self.reviewer_email)
                except Exception as exc:
                    log.error("Mail send failed for %s: %s", customer.customer_name, exc)
                    errors += 1
                    continue

                # Track in Supabase
                campaign_record = CampaignRecord(
                    customer_id=customer.customer_id,
                    customer_name=customer.customer_name,
                    contact_email=customer.contact_email,
                    campaign_id=campaign_id,
                    outbound_subject=draft.subject,
                    parts_included=[
                        {"part_number": p.part_number, "description": p.description, "vendor": p.vendor}
                        for p in wear_parts
                    ],
                    order_summary=order_summary,
                    status="drafted",
                )
                await self.supabase_client.insert_campaign_record(campaign_record)

            sent_keys.add(dedupe_key)
            drafted += 1
            processed += 1

        state["sent_keys"] = sorted(sent_keys)
        state["last_run"] = now.isoformat()
        state["last_campaign_id"] = campaign_id
        self._save_state(state)

        return {
            "campaign_id": campaign_id,
            "fetched": len(customers),
            "eligible": len(eligible),
            "processed": processed,
            "drafted": drafted,
            "enriched": enriched,
            "skipped_seen": skipped_seen,
            "errors": errors,
            "dry_run": dry_run,
        }

    def _load_state(self) -> dict:
        if not self.state_path.exists():
            return {"sent_keys": []}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Failed to read state file %s: %s", self.state_path, exc)
            return {"sent_keys": []}

    def _save_state(self, data: dict) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self.state_path)


def _is_eligible(customer: CustomerRecord) -> bool:
    year = customer.last_business_year
    years_since = customer.years_since_last_work
    year_ok = year is not None and 2018 <= year <= 2022
    years_ok = years_since is None or years_since >= 4.0
    return year_ok and years_ok


def _dedupe_key(customer: CustomerRecord) -> str:
    if customer.customer_id:
        return f"id:{customer.customer_id}"
    return f"name:{customer.customer_name.lower().strip()}"
