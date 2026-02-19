"""BOM Fuzzy Search — score BOM records against description keywords.

Epicor OData doesn't support contains() or full-text search.
This module pulls all BOM records for an order/job, then scores
each record against user-provided description keywords in Python.

Supports both GPT_Bom and GPT_Bom2 field layouts:
  GPT_Bom:  JobMtl_PartNum, JobMtl_Description, JobAsmbl_Description, JobMtl_BuyIt
  GPT_Bom2: Part_PartNum, Part_PartDescription, Vendor_Name (no BuyIt field)
"""

import logging
import re

log = logging.getLogger("maggie-spares.bom-search")

# Short words to ignore when tokenizing search terms
STOP_WORDS = {"a", "an", "the", "for", "and", "or", "of", "to", "in", "on", "is", "it", "my", "i", "we", "need"}


def _tokenize(text: str) -> list[str]:
    """Split search text into meaningful tokens, lowercased, stop words removed."""
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def _get_part_num(record: dict) -> str:
    """Get part number from either BAQ layout."""
    return record.get("Part_PartNum") or record.get("JobMtl_PartNum") or ""


def _get_description(record: dict) -> str:
    """Get description from either BAQ layout."""
    return record.get("Part_PartDescription") or record.get("JobMtl_Description") or ""


def score_record(record: dict, tokens: list[str]) -> float:
    """Score a single BOM record against search tokens.

    Checks part number, description, vendor, and assembly description.
    Returns 0.0 to 1.0+ (can exceed 1.0 with bonuses).
    """
    if not tokens:
        return 0.0

    # Build searchable text from the record — works with both GPT_Bom and GPT_Bom2
    part = _get_part_num(record).lower()
    desc = _get_description(record).lower()
    vendor = str(record.get("Vendor_Name", "")).lower()
    asm = str(record.get("JobAsmbl_Description", "")).lower()
    search_text = f"{part} {desc} {vendor} {asm}"

    # Count matching tokens
    matches = sum(1 for t in tokens if t in search_text)
    score = matches / len(tokens)

    # Bonus for purchasable components (GPT_Bom has BuyIt; GPT_Bom2 has vendor)
    if score > 0:
        if record.get("JobMtl_BuyIt") is True:
            score += 0.2
        elif record.get("Vendor_Name"):
            # GPT_Bom2: having a vendor implies it's a purchased component
            score += 0.1

    return round(score, 3)


def fuzzy_filter(records: list[dict], search_terms: str) -> dict:
    """Filter and score BOM records against search description.

    Args:
        records: Raw BOM records from Epicor GPT_Bom or GPT_Bom2 query
        search_terms: User's part description (e.g., "drawer filter front")

    Returns:
        {
            "matches": [...],          # Records matching search terms, scored & sorted
            "wear_suggestions": [...],  # Purchased components (potential wear/spare parts)
            "total_bom_records": int,
            "search_tokens": [...]
        }
    """
    tokens = _tokenize(search_terms)
    log.info(f"BOM fuzzy search: '{search_terms}' → tokens={tokens}, records={len(records)}")

    scored = []
    buy_items = []

    for record in records:
        s = score_record(record, tokens)
        if s > 0:
            record["_match_score"] = s
            scored.append(record)

        # Collect purchasable components for wear suggestions
        # GPT_Bom: BuyIt=true; GPT_Bom2: has a vendor (all records have vendors due to INNER JOIN)
        is_buy = record.get("JobMtl_BuyIt") is True or bool(record.get("Vendor_Name"))
        if is_buy:
            record["_match_score"] = record.get("_match_score", 0.0)
            buy_items.append(record)

    # Sort matches by score descending
    scored.sort(key=lambda r: r["_match_score"], reverse=True)
    top_matches = scored[:10]

    # Wear suggestions: buy items that DIDN'T already match (avoid duplicates)
    matched_parts = {_get_part_num(r) for r in top_matches}
    wear = [r for r in buy_items if _get_part_num(r) not in matched_parts]
    wear_suggestions = wear[:5]

    log.info(f"BOM fuzzy results: {len(top_matches)} matches, {len(wear_suggestions)} wear suggestions")

    return {
        "matches": top_matches,
        "wear_suggestions": wear_suggestions,
        "total_bom_records": len(records),
        "search_tokens": tokens,
    }
