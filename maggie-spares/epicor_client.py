"""Epicor OData Client — GET requests ONLY. Never POST/PUT/DELETE.

TECH DEBT: verify=False disables SSL verification. Epicor server likely uses
a self-signed or internal CA cert. For production hardening, pin the cert or
add it to the container's trust store.
"""

import os
import asyncio
import base64
import logging
import httpx

log = logging.getLogger("maggie-spares.epicor")

EPICOR_BASE_URL = os.environ.get("EPICOR_BASE_URL", "")
EPICOR_USER = os.environ.get("EPICOR_USER", "")
EPICOR_PASS = os.environ.get("EPICOR_PASS", "")
EPICOR_API_KEY = os.environ.get("EPICOR_API_KEY", "")

# Pre-compute auth header once at startup (not on every call)
_AUTH_HEADERS: dict | None = None


def _get_auth_headers() -> dict:
    global _AUTH_HEADERS
    if _AUTH_HEADERS is None:
        creds = base64.b64encode(f"{EPICOR_USER}:{EPICOR_PASS}".encode()).decode()
        _AUTH_HEADERS = {
            "Authorization": f"Basic {creds}",
            "Accept": "application/json",
        }
        if EPICOR_API_KEY:
            _AUTH_HEADERS["x-api-key"] = EPICOR_API_KEY
    return _AUTH_HEADERS


# Reusable async client — connection pooling across calls
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=60.0,  # 60s for large BAQs like GPT_Bom
            verify=False,  # TECH DEBT: self-signed cert on Epicor server
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _client


async def query_baq(
    baq_id: str,
    company: str = "BMC",
    select: str = "",
    filter_str: str = "",
    top: int = 25,
    orderby: str = "",
) -> dict:
    """Execute a GET-only OData query against an Epicor BAQ.

    Returns {"success": bool, "data": [...], "count": int, "truncated": bool, "error": str|None}
    """
    if not EPICOR_BASE_URL:
        return {"success": False, "data": [], "count": 0, "truncated": False, "error": "EPICOR_BASE_URL not configured"}

    url = f"{EPICOR_BASE_URL}/api/v2/odata/{company}/BaqSvc/{baq_id}/Data"

    params = {}
    if top:
        params["$top"] = str(top)
    if select:
        # Strip spaces from $select — Epicor OData chokes on "Field1, Field2"
        clean_select = select.replace(" ", "")
        # Validate $select fields against BAQ catalog to prevent 400 errors
        from baq_reference import BAQ_CATALOG
        if baq_id in BAQ_CATALOG:
            valid_fields = set(BAQ_CATALOG[baq_id]["fields"].keys())
            requested = [f.strip() for f in clean_select.split(",")]
            validated = [f for f in requested if f in valid_fields]
            rejected = [f for f in requested if f and f not in valid_fields]
            if rejected:
                log.warning(f"Stripped invalid $select fields for {baq_id}: {rejected}")
            clean_select = ",".join(validated) if validated else ""
        if clean_select:
            params["$select"] = clean_select
    if filter_str:
        params["$filter"] = filter_str
    if orderby:
        params["$orderby"] = orderby
    # Request count to detect truncation
    params["$count"] = "true"

    log.info(f"Epicor GET: {baq_id} company={company} filter={filter_str} top={top}")

    try:
        client = _get_client()
        # HARDCODED: Only GET. This client will NEVER issue POST/PUT/DELETE.
        resp = await client.get(url, headers=_get_auth_headers(), params=params)

        if resp.status_code == 200:
            body = resp.json()
            records = body.get("value", [])
            total_count = body.get("@odata.count", len(records))
            truncated = total_count > len(records)

            if truncated:
                log.warning(
                    f"Epicor {baq_id}: returned {len(records)}/{total_count} records "
                    f"(truncated by $top={top}). Agent may be missing data."
                )
            else:
                log.info(f"Epicor returned {len(records)} records from {baq_id}")

            return {
                "success": True,
                "data": records,
                "count": len(records),
                "total_available": total_count,
                "truncated": truncated,
                "error": None,
            }
        else:
            error_msg = f"HTTP {resp.status_code}: {resp.text[:500]}"
            log.error(f"Epicor error: {error_msg}")
            return {"success": False, "data": [], "count": 0, "truncated": False, "error": error_msg}

    except Exception as e:
        log.error(f"Epicor request failed: {e}")
        return {"success": False, "data": [], "count": 0, "truncated": False, "error": str(e)}


async def multi_query(queries: list[dict]) -> list[dict]:
    """Execute multiple BAQ queries concurrently (max 5 per cycle). All GET-only."""
    capped = queries[:5]  # Hard limit: 5 queries per cycle

    tasks = [
        query_baq(
            baq_id=q.get("baq_id", ""),
            company=q.get("company", "BMC"),
            select=q.get("select", ""),
            filter_str=q.get("filter", ""),
            top=q.get("top", 25),
            orderby=q.get("orderby", ""),
        )
        for q in capped
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    final = []
    for r, q in zip(results, capped):
        if isinstance(r, Exception):
            log.error(f"Query {q.get('baq_id')} failed: {r}")
            r = {"success": False, "data": [], "count": 0, "truncated": False, "error": str(r)}
        r["baq_id"] = q.get("baq_id", "")
        final.append(r)

    return final
