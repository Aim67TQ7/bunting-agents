"""Supabase client for pulling customer records and tracking campaigns."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from models import CampaignRecord, CustomerRecord

log = logging.getLogger("maggie-coldemail.supabase")


class SupabaseClient:
    def __init__(
        self,
        url: str,
        service_key: str,
        table: str,
        campaign_table: str = "maggie_campaigns",
        csv_public_url: str = "",
    ) -> None:
        self.url = url.rstrip("/")
        self.service_key = service_key
        self.table = table
        self.campaign_table = campaign_table
        self.csv_public_url = csv_public_url.strip()
        self._headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    # ------------------------------------------------------------------
    # Customer fetch
    # ------------------------------------------------------------------

    async def fetch_customers(self, limit: int = 1000) -> list[CustomerRecord]:
        if self.csv_public_url:
            return await self._fetch_csv_customers()
        return await self._fetch_table_customers(limit=limit)

    async def _fetch_table_customers(self, limit: int) -> list[CustomerRecord]:
        endpoint = f"{self.url}/rest/v1/{self.table}"
        params = {"select": "*", "limit": str(limit)}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(endpoint, headers=self._headers, params=params)
            resp.raise_for_status()
            rows = resp.json()
        return [self._normalize_row(row) for row in rows]

    async def _fetch_csv_customers(self) -> list[CustomerRecord]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.csv_public_url)
            resp.raise_for_status()
            body = resp.text
        reader = csv.DictReader(io.StringIO(body))
        return [self._normalize_row(row) for row in reader]

    # ------------------------------------------------------------------
    # Campaign tracking
    # ------------------------------------------------------------------

    async def insert_campaign_record(self, record: CampaignRecord) -> None:
        """Insert a campaign tracking row into Supabase."""
        endpoint = f"{self.url}/rest/v1/{self.campaign_table}"
        payload = {
            "customer_id": record.customer_id,
            "customer_name": record.customer_name,
            "contact_email": record.contact_email,
            "campaign_id": record.campaign_id,
            "outbound_subject": record.outbound_subject,
            "parts_included": record.parts_included,
            "order_summary": record.order_summary,
            "field_service_mentioned": record.field_service_mentioned,
            "status": record.status,
            "outbound_sent_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(endpoint, headers=self._headers, json=payload)
                resp.raise_for_status()
            log.info("Campaign record saved for %s", record.customer_name)
        except Exception as exc:
            log.warning("Failed to save campaign record for %s: %s", record.customer_name, exc)

    async def get_campaign_stats(self, campaign_id: str | None = None) -> dict[str, Any]:
        """Get campaign summary stats."""
        endpoint = f"{self.url}/rest/v1/{self.campaign_table}"
        params: dict[str, str] = {"select": "status,campaign_id"}
        if campaign_id:
            params["campaign_id"] = f"eq.{campaign_id}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(endpoint, headers=self._headers, params=params)
                resp.raise_for_status()
                rows = resp.json()
        except Exception as exc:
            log.warning("Failed to fetch campaign stats: %s", exc)
            return {"error": str(exc)}

        total = len(rows)
        by_status: dict[str, int] = {}
        for row in rows:
            s = row.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1

        return {"total": total, "by_status": by_status}

    # ------------------------------------------------------------------
    # Row normalization
    # ------------------------------------------------------------------

    def _normalize_row(self, row: dict[str, Any]) -> CustomerRecord:
        customer_name = (
            row.get("customer_name")
            or row.get("Customer_Name")
            or row.get("name")
            or ""
        ).strip()
        if not customer_name:
            customer_name = "Unknown Customer"

        last_year = _to_int(row.get("last_business_year") or row.get("LastBusinessYear"))
        years_since = _to_float(row.get("years_since_last_work") or row.get("YearsSinceLastWork"))

        return CustomerRecord(
            customer_id=str(row.get("customer_id") or row.get("Customer_ID") or row.get("id") or ""),
            customer_name=customer_name,
            contact_name=str(row.get("contact_name") or row.get("ContactName") or "").strip(),
            contact_email=str(row.get("contact_email") or row.get("ContactEmail") or "").strip(),
            last_order_number=str(
                row.get("last_order_number") or row.get("OrderNum") or row.get("order_number") or ""
            ).strip(),
            last_order_date=str(row.get("last_order_date") or row.get("OrderDate") or "").strip(),
            last_business_year=last_year,
            years_since_last_work=years_since,
            notes=str(row.get("notes") or "").strip(),
            raw=row,
        )


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
