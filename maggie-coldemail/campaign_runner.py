"""Campaign orchestration for Maggie cold-email workflow."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from draft_engine import build_reactivation_draft
from magnus_client import MagnusClient
from mailer import SmtpMailer
from models import CustomerRecord
from supabase_client import SupabaseClient

log = logging.getLogger("maggie-coldemail.runner")


class CampaignRunner:
    def __init__(
        self,
        supabase_client: SupabaseClient,
        magnus_client: MagnusClient,
        mailer: SmtpMailer,
        reviewer_email: str,
        state_path: str,
    ) -> None:
        self.supabase_client = supabase_client
        self.magnus_client = magnus_client
        self.mailer = mailer
        self.reviewer_email = reviewer_email
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    async def run(self, dry_run: bool, limit: int) -> dict:
        now = datetime.now(timezone.utc)
        campaign_id = now.strftime("maggie-coldemail-%Y%m%d-%H%M%S")
        state = self._load_state()
        sent_keys: set[str] = set(state.get("sent_keys", []))

        customers = await self.supabase_client.fetch_customers(limit=limit)
        eligible = [c for c in customers if _is_eligible(c)]

        processed = 0
        skipped_seen = 0
        drafted = 0
        for customer in eligible:
            dedupe_key = _dedupe_key(customer)
            if dedupe_key in sent_keys:
                skipped_seen += 1
                continue

            wear_parts = await self.magnus_client.get_wear_part_candidates(customer)
            draft = build_reactivation_draft(customer, wear_parts, campaign_id=campaign_id)
            if not dry_run:
                self.mailer.send_draft(draft, reviewer_email=self.reviewer_email)
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
            "skipped_seen": skipped_seen,
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
