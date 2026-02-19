"""AI Engine — Gemini 2.0 Flash for intent classification and response generation."""

import os
import json
import logging
import httpx

from baq_reference import get_baq_summary, BAQ_CATALOG

log = logging.getLogger("maggie-spares.ai")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# Shared httpx client for Gemini API calls
_gemini_client: httpx.AsyncClient | None = None


def _get_gemini_client() -> httpx.AsyncClient:
    global _gemini_client
    if _gemini_client is None or _gemini_client.is_closed:
        _gemini_client = httpx.AsyncClient(
            timeout=45.0,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=3),
        )
    return _gemini_client


def _fuzzy_match_baq_id(wrong_id: str, valid_ids: set[str]) -> str | None:
    """Try to correct a wrong BAQ ID by normalizing hyphens/underscores/case.

    Returns the corrected ID or None if no close match found.
    """
    # Normalize: lowercase, replace hyphens with underscores
    normalized = wrong_id.lower().replace("-", "_")
    for valid in valid_ids:
        if valid.lower().replace("-", "_") == normalized:
            return valid
    # Try without any separators
    stripped = wrong_id.lower().replace("-", "").replace("_", "")
    for valid in valid_ids:
        if valid.lower().replace("-", "").replace("_", "") == stripped:
            return valid
    return None


CLASSIFIER_SYSTEM_PROMPT = """You are MAGGIE SPARES, an AI assistant for Bunting Magnetics.
Your job is to analyze a customer or internal email and determine what Epicor ERP data to query.

You have access to these BAQ (Business Activity Query) endpoints via OData:

{baq_summary}

## VALID BAQ IDs — Use ONLY These Exact Strings
{baq_id_list}

CRITICAL: Copy-paste the baq_id exactly from the list above. Do NOT change hyphens to underscores or vice versa. Do NOT invent BAQ IDs.

## OData Filter Syntax — EPICOR SPECIFIC
**IMPORTANT: Epicor does NOT support contains() or substringof(). Use startswith() for text searches.**

- Text search (fuzzy): startswith(FieldName, 'value')
- String equals (exact): FieldName eq 'value'
- Numeric: FieldName gt 100, FieldName eq 42
- Boolean: FieldName eq true
- Date: FieldName ge 2025-01-01T00:00:00Z
- Combine: filter1 and filter2, filter1 or filter2
- NOT: not startswith(FieldName, 'value')

## Rules
1. Return ONLY valid JSON. No markdown, no explanation outside JSON.
2. Pick the best BAQ(s) for the question — usually 1-2, max 3.
3. Build OData $filter strings using actual field names from the schema.
4. **For customer names, part numbers, descriptions, and vendor names: ALWAYS use startswith().** Customer names in Epicor are often longer than what users type (e.g., "Weima" is stored as "Weima America Inc.", "Tesla" might be "Tesla Motors Inc"). Use startswith(Customer_Name, 'Weima') — NOT eq, NOT contains (contains is not supported by Epicor).
5. Default company is BMC unless the email mentions BME or MAI.
6. Default $top is 25. Only increase if the question explicitly needs more data. For GPT_Bom, use $top=100 (many components per job).
7. ALWAYS use $select — only request fields relevant to the question. This is critical for performance. NO SPACES after commas in $select (e.g., "Field1,Field2,Field3" not "Field1, Field2, Field3").
8. Include a brief explanation of what you're querying and why.
9. Results may be truncated. The response will include total_available count. If truncated, tighten your filters rather than increasing $top.
10. When searching by name, use the shortest distinctive substring. For "Weima America", filter on just startswith(Customer_Name, 'Weima'). For "John Deere", use startswith(Customer_Name, 'Deere'). Shorter = more likely to match.
11. NEVER use contains(), substringof(), or indexof() — Epicor does not support them. ONLY use startswith() for text matching.

## Spare Parts / BOM Query Flow
When a customer asks about **spare parts, replacement parts, BOM, wear items, or components**:
1. **Identify the customer first.** The customer may provide: a PO number, order number, part number, job number, serial number, or just a part description.
2. **Trace to the job.** Use the appropriate BAQ to find the job number:
   - PO number → GPT_Open_Orders (filter on OrderHed_PONum)
   - Order number → GPT_Open_Orders (filter on OrderRel_OrderNum)
   - Serial number → GPT_serialnumbers (filter on SerialNo_SerialNumber) → get JobNum
   - Part number → GPT_Open_Orders (filter on OrderRel_PartNum) or GPT_Production3
3. **Query the BOM using GPT_Bom2** (preferred) or GPT_Bom:
   - GPT_Bom2 fields: JobProd_OrderNum (integer), JobProd_JobNum (string), Customer_Name, Part_PartNum, Part_PartDescription, Vendor_Name, OrderHed_PONum
   - Filter by JobProd_OrderNum eq ORDER_NUMBER or startswith(JobProd_JobNum, 'ORDER_PREFIX') or startswith(Customer_Name, 'NAME')
   - Select: Part_PartNum,Part_PartDescription,JobMtl_QtyPer,JobMtl_RequiredQty,JobProd_JobNum,Vendor_Name,Part_ClassID,Part_TypeCode,JobMtl_TotalCost
   - Use $top=200 (jobs can have many components)
4. **ALWAYS include both steps** — a lookup query AND the GPT_Bom2 query — so the customer gets the full picture.
5. **NEVER query GPT_Bom2 without a filter.** It will timeout. Always filter by customer name, order number, or job number.

## Response Format
```json
{{
  "queries": [
    {{
      "baq_id": "GPT-Backlog",
      "company": "BMC",
      "filter": "startswith(Customer_Name, 'Acme')",
      "select": "OrderHed_OrderNum,Customer_Name,OrderDtl_LineDesc,Calculated_OpenValue",
      "top": 25,
      "orderby": "OrderRel_ReqDate desc"
    }}
  ],
  "explanation": "Looking up open backlog orders for Acme to check status.",
  "bom_search_terms": ""
}}
```
**bom_search_terms**: When the user mentions a specific part description for a BOM search (e.g., "drawer filter front", "magnet assembly", "conveyor belt"), extract those description keywords here. Leave empty ("") for non-BOM queries. This enables server-side fuzzy matching against BOM part descriptions since Epicor doesn't support text search. For BOM queries, set $top=200 to pull all components — the fuzzy filter will narrow results server-side.
"""

RESPONDER_SYSTEM_PROMPT = """You are MAGGIE SPARES, Bunting Magnetics' spare parts and order assistant.
You received a customer inquiry and have queried the Epicor ERP system for relevant data.

Your job is to write a professional, customer-ready email response. A Bunting team member will review
and forward this directly to the customer, so write AS IF you are addressing the customer. The tone
should be helpful, knowledgeable, and ready to send with minimal editing.

## Email Structure

### 1. Opening
- Address the customer by name (extract from the "From" field or email body).
- Thank them for reaching out.
- Briefly acknowledge what they asked about.

### 2. Direct Answer
- Answer their specific question first. If they asked about a belt, lead with the belt.
- Present the matching part(s) in a clean table:
  | Part Number | Description | Vendor | Job Reference |
- Include the order number and PO number for reference.

### 3. Proactive Wear Part Suggestions (BOM queries only)
- If BOM data is available, identify other purchased/wear components on the same order.
- Introduce with something like: "While reviewing your equipment's bill of materials, we identified
  additional wear and replacement components that you may want to consider having on hand to
  minimize downtime:"
- Present as a secondary table with the same format.
- Only include parts that are clearly wear/consumable items (belts, bearings, seals, filters,
  gaskets, screens, magnets, brushes, rollers, pulleys, motors, gearboxes, etc.).
- Do NOT include structural steel, weldments, paint, or fabricated assemblies.

### 4. Closing
- Offer to provide quotes, lead times, or additional information.
- Include a line like: "Please reply to this email or contact your Bunting sales representative
  to place an order or request a quote."
- Sign off with:

  Best regards,
  Bunting Magnetics Spare Parts Team
  maggie@buntingmagnetics.com

## Formatting Rules
1. Format currency as USD with commas (e.g., $12,345.67).
2. Always include Part Number AND Description — never one without the other.
3. Use HTML tables for parts lists (the email is sent as HTML).
4. Keep it concise — no more than 2-3 short paragraphs outside of tables.
5. **GROUNDING IS MANDATORY.** ONLY cite data that appears in the ERP query results below.
   NEVER invent, guess, or hallucinate part numbers, quantities, prices, dates, tracking numbers,
   or any other data. If a field is missing from the results, say "available upon request" — do NOT
   fill in a plausible value.
6. When referencing parts, always cite the exact Part Number and Description from the ERP data.
7. Do NOT include internal job numbers or Epicor-specific terminology the customer wouldn't recognize.
   Use "your order" or "your equipment" instead of "job 9432687-1-1".
8. Include the customer's PO number if available — customers recognize their own PO numbers.
9. If fuzzy match scores are in the data (_match_score), do NOT show them to the customer.
10. If Vendor_Name is present, you may mention the manufacturer/supplier for purchased parts
    (e.g., "Belt by Beltservice Corporation") as this adds credibility.
"""


async def _call_gemini(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """Call Gemini API and return text response."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 4096},
    }
    try:
        client = _get_gemini_client()
        resp = await client.post(url, json=payload)
        result = resp.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        log.error(f"Gemini error: {e}")
        return f"Error calling Gemini: {e}"


async def classify_intent(email_subject: str, email_body: str, sender: str) -> dict:
    """Classify an email into BAQ queries to execute.

    Returns: {"queries": [...], "explanation": str}
    """
    baq_id_list = "\n".join(f"- {baq_id}" for baq_id in BAQ_CATALOG.keys())
    system = CLASSIFIER_SYSTEM_PROMPT.format(baq_summary=get_baq_summary(), baq_id_list=baq_id_list)
    user_prompt = (
        f"From: {sender}\n"
        f"Subject: {email_subject}\n\n"
        f"{email_body}\n\n"
        f"Analyze this email and return the JSON query plan."
    )

    raw = await _call_gemini(system, user_prompt, temperature=0.1)
    log.info(f"Classifier raw response: {raw[:300]}")

    # Extract JSON from response (handle markdown code blocks)
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(text)
        # Validate structure
        if "queries" not in result:
            result = {"queries": [], "explanation": "Failed to parse query plan"}
            return result

        # Validate BAQ IDs — reject any that don't exist in the catalog
        valid_ids = set(BAQ_CATALOG.keys())
        validated_queries = []
        for q in result["queries"]:
            baq_id = q.get("baq_id", "")
            if baq_id in valid_ids:
                validated_queries.append(q)
            else:
                # Try fuzzy correction: find closest match
                corrected = _fuzzy_match_baq_id(baq_id, valid_ids)
                if corrected:
                    log.warning(f"BAQ ID corrected: '{baq_id}' → '{corrected}'")
                    q["baq_id"] = corrected
                    validated_queries.append(q)
                else:
                    log.error(f"Invalid BAQ ID from AI: '{baq_id}' — skipping query")

        result["queries"] = validated_queries
        return result
    except json.JSONDecodeError as e:
        log.error(f"JSON parse error: {e} | Raw: {text[:200]}")
        return {"queries": [], "explanation": f"Failed to parse AI response: {e}"}


def _filter_record_fields(record: dict, select_fields: str) -> dict:
    """Strip record down to only the $select fields requested.

    If $select was used in the query, only pass those fields to the LLM.
    This is the primary token cost control — prevents full Epicor records
    (30+ fields) from bloating the context when only 5-6 are relevant.
    """
    if not select_fields:
        return record
    allowed = {f.strip() for f in select_fields.split(",")}
    return {k: v for k, v in record.items() if k in allowed}


async def generate_response(
    email_subject: str,
    email_body: str,
    sender: str,
    query_results: list[dict],
    explanation: str,
    query_selects: list[str] | None = None,
) -> str:
    """Generate a formatted response email from query results.

    query_selects: parallel list of $select strings from the original queries,
    used to filter records before injecting into the LLM context.
    """
    if query_selects is None:
        query_selects = [""] * len(query_results)

    # Build results context
    results_text = f"## Query Explanation\n{explanation}\n\n"
    for i, qr in enumerate(query_results):
        baq = qr.get("baq_id", "Unknown")
        count = qr.get("count", 0)
        total = qr.get("total_available", count)
        truncated = qr.get("truncated", False)
        trunc_note = f" (showing {count} of {total} — results truncated)" if truncated else ""
        results_text += f"### {baq} — {count} records{trunc_note}\n"
        if qr.get("error"):
            results_text += f"**Error:** {qr['error']}\n\n"
            continue
        data = qr.get("data", [])
        select_str = query_selects[i] if i < len(query_selects) else ""
        if data:
            for j, row in enumerate(data[:20]):
                # Filter to only $select fields before serializing — token savings
                filtered = _filter_record_fields(row, select_str)
                results_text += f"Record {j+1}: {json.dumps(filtered, default=str)}\n"
            if count > 20:
                results_text += f"... and {count - 20} more records\n"
        else:
            results_text += "No records returned.\n"
        results_text += "\n"

    user_prompt = (
        f"## Customer Inquiry\n"
        f"**From:** {sender}\n"
        f"**Subject:** {email_subject}\n\n"
        f"{email_body}\n\n"
        f"## ERP Query Results\n"
        f"{results_text}\n\n"
        f"Write a professional, customer-ready response email. "
        f"A Bunting team member will review and forward this to the customer."
    )

    return await _call_gemini(RESPONDER_SYSTEM_PROMPT, user_prompt, temperature=0.3)


async def direct_query(question: str) -> dict:
    """Handle a direct /ask query (not email-based). Returns classification."""
    return await classify_intent(
        email_subject="Direct Query",
        email_body=question,
        sender="api-user",
    )
