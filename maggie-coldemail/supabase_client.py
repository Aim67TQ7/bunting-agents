"""Supabase client for pulling customer campaign records."""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

import httpx

from models import CustomerRecord

log = logging.getLogger("maggie-coldemail.supabase")


class SupabaseClient:
    def __init__(self, url: str, service_key: str, table: str, csv_public_url: str = "") -> None:
        self.url = url.rstrip("/")
        self.service_key = service_key
        self.table = table
        self.csv_public_url = csv_public_url.strip()

    async def fetch_customers(self, limit: int = 1000) -> list[CustomerRecord]:
        """Fetch customers either from Supabase table or a CSV URL."""
        if self.csv_public_url:
            return await self._fetch_csv_customers()
        return await self._fetch_table_customers(limit=limit)

    async def _fetch_table_customers(self, limit: int) -> list[CustomerRecord]:
        endpoint = f"{self.url}/rest/v1/{self.table}"
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }
        params = {
            "select": "*",
            "limit": str(limit),
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(endpoint, headers=headers, params=params)
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

    def _normalize_row(self, row: dict[str, Any]) -> CustomerRecord:
        # Map common field names across table/csv variants.
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
