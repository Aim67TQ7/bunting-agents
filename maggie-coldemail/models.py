"""Shared data models for Maggie cold email workflows."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CustomerRecord(BaseModel):
    """Normalized customer data used by the campaign pipeline."""

    customer_id: str = ""
    customer_name: str
    contact_name: str = ""
    contact_email: str = ""
    last_order_number: str = ""
    last_order_date: str = ""
    last_business_year: int | None = None
    years_since_last_work: float | None = None
    notes: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class WearPartFinding(BaseModel):
    part_number: str
    description: str
    reason: str = ""


class DraftEmail(BaseModel):
    customer_name: str
    recipient_hint: str
    subject: str
    html_body: str
    text_body: str
    campaign_id: str
    supporting_parts: list[WearPartFinding] = Field(default_factory=list)
