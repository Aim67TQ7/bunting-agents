"""Client for enriching customers via maggie-spares (Epicor BAQ data)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from models import CustomerRecord, WearPartFinding

log = logging.getLogger("maggie-coldemail.spares")


class SparesClient:
    """Calls maggie-spares /ask to get real Epicor BOM/order data."""

    def __init__(self, base_url: str, api_key: str = "", timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.timeout = timeout

    async def get_wear_part_candidates(self, customer: CustomerRecord) -> list[WearPartFinding]:
        """Ask maggie-spares to look up real BOM wear components from Epicor."""
        if not self.base_url:
            return []

        prompt = self._build_prompt(customer)
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        endpoint = f"{self.base_url}/ask"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, headers=headers, json={"question": prompt})
                resp.raise_for_status()
                data = resp.json()
            return self._parse_response(data)
        except Exception as exc:
            log.warning("Spares enrichment failed for %s: %s", customer.customer_name, exc)
            return []

    async def get_order_summary(self, customer: CustomerRecord) -> str:
        """Get a brief order history summary for the customer."""
        if not self.base_url:
            return ""

        prompt = (
            f"Look up the most recent orders for customer '{customer.customer_name}'. "
            f"Customer ID: {customer.customer_id or 'unknown'}. "
            "Summarize what equipment or products they ordered. Keep it brief — just the key items."
        )
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/ask",
                    headers=headers,
                    json={"question": prompt},
                )
                resp.raise_for_status()
                data = resp.json()
            return str(data.get("answer", "")).strip()
        except Exception as exc:
            log.warning("Order summary failed for %s: %s", customer.customer_name, exc)
            return ""

    def _build_prompt(self, customer: CustomerRecord) -> str:
        parts = [
            "Look up the BOM for the most recent order from this Bunting customer.",
            "List the wear and replacement components — belts, bearings, seals, filters, "
            "screens, rollers, motors, gearboxes, magnets, springs, liners.",
            "Format each part on its own line as: PART_NUMBER | DESCRIPTION | VENDOR",
            "If no vendor, leave that field blank.",
            f"Customer: {customer.customer_name}.",
        ]
        if customer.customer_id:
            parts.append(f"Customer ID: {customer.customer_id}.")
        if customer.last_order_number:
            parts.append(f"Order number: {customer.last_order_number}.")
        if customer.last_order_date:
            parts.append(f"Order date: {customer.last_order_date}.")
        return " ".join(parts)

    def _parse_response(self, response: dict[str, Any]) -> list[WearPartFinding]:
        answer = str(response.get("answer", "")).strip()
        if not answer:
            return []

        results: list[WearPartFinding] = []
        for raw_line in answer.splitlines():
            line = raw_line.strip().lstrip("-•*").strip()
            if not line or len(line) < 3:
                continue

            # Try pipe-delimited format first: "PART123 | Description | Vendor"
            if "|" in line:
                pieces = [p.strip() for p in line.split("|")]
                if len(pieces) >= 2:
                    results.append(WearPartFinding(
                        part_number=pieces[0],
                        description=pieces[1],
                        vendor=pieces[2] if len(pieces) > 2 else "",
                        reason="From Epicor BOM",
                    ))
                    continue

            # Fallback: treat as description only
            if any(kw in line.lower() for kw in (
                "belt", "bearing", "seal", "filter", "screen", "roller",
                "motor", "gearbox", "magnet", "spring", "liner", "bushing",
                "gasket", "blade", "wear", "replacement",
            )):
                results.append(WearPartFinding(
                    part_number="",
                    description=line,
                    vendor="",
                    reason="From Epicor BOM",
                ))

        return results[:12]
