"""Client for asking Magnus to identify likely replacement parts."""

from __future__ import annotations

import logging

import httpx

from models import CustomerRecord, WearPartFinding

log = logging.getLogger("maggie-coldemail.magnus")


class MagnusClient:
    def __init__(self, base_url: str, api_key: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()

    async def get_wear_part_candidates(self, customer: CustomerRecord) -> list[WearPartFinding]:
        if not self.base_url:
            return []
        prompt = self._build_prompt(customer)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        payload = {"question": prompt}
        endpoint = f"{self.base_url}/ask"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(endpoint, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            return self._parse_wear_parts(data)
        except Exception as exc:
            log.warning("Magnus enrichment failed for %s: %s", customer.customer_name, exc)
            return []

    def _build_prompt(self, customer: CustomerRecord) -> str:
        return (
            "Find likely wear/replacement components for this historical Bunting customer and order. "
            "Return likely parts such as belts, bearings, seals, filters, screens, rollers, motors, gearboxes. "
            f"Customer: {customer.customer_name}. "
            f"Last order number: {customer.last_order_number or 'unknown'}. "
            f"Last order date: {customer.last_order_date or 'unknown'}."
        )

    def _parse_wear_parts(self, response: dict) -> list[WearPartFinding]:
        answer = str(response.get("answer", "")).strip()
        if not answer:
            return []
        results: list[WearPartFinding] = []
        for raw_line in answer.splitlines():
            line = raw_line.strip().lstrip("-").strip()
            if not line:
                continue
            # Light parser: "PART123 | Description | Reason"
            pieces = [p.strip() for p in line.split("|")]
            if len(pieces) == 1:
                results.append(WearPartFinding(part_number="", description=pieces[0], reason=""))
                continue
            if len(pieces) == 2:
                results.append(WearPartFinding(part_number=pieces[0], description=pieces[1], reason=""))
                continue
            results.append(WearPartFinding(part_number=pieces[0], description=pieces[1], reason=pieces[2]))
        return results[:8]
