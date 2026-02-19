#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
t3rms_analyzer.py
Ingest buyer-supplied contract (PO / RFQ / T&Cs / Distributor Agreement, etc.),
extract text (OCR fallback), chunk, and compare vs. seller baseline terms.
Outputs: brief summary + compliance score to stdout, plus JSON + Markdown report on disk.

Dependencies:
  pip install pypdf pdfplumber python-docx pillow pytesseract pdf2image tiktoken openai pydantic
System deps:
  Tesseract OCR + Poppler (for pdf2image)
Environment:
  export OPENAI_API_KEY=...
"""

import os
import re
import io
import json
import math
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Text extraction
import pdfplumber
from pypdf import PdfReader
from docx import Document as DocxDocument
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

# Chunking
try:
    import tiktoken
    HAS_TIKTOKEN = True
except Exception:
    HAS_TIKTOKEN = False

# LLM
from openai import OpenAI

# Schema
from pydantic import BaseModel, Field, ValidationError


# ----------------------------
# Utilities
# ----------------------------

def read_file_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def is_image_ext(ext: str) -> bool:
    return ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def try_pdf_text(path: str) -> str:
    # First: fast text extraction
    try:
        reader = PdfReader(path)
        raw = []
        for page in reader.pages:
            t = page.extract_text() or ""
            raw.append(t)
        text = "\n\n".join(raw)
        return text
    except Exception:
        pass

    # Second: pdfplumber as a fallback
    try:
        texts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                texts.append(t)
        return "\n\n".join(texts)
    except Exception:
        return ""


def ocr_image(img: Image.Image) -> str:
    return pytesseract.image_to_string(img)


def pdf_to_ocr_text(path: str) -> str:
    # Requires poppler (pdf2image)
    images = convert_from_path(path, dpi=300)
    parts = []
    for im in images:
        parts.append(ocr_image(im))
    return "\n\n".join(parts)


def extract_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        text = try_pdf_text(path)
        # If text is empty or too sparse, OCR the PDF
        if not text or len(text.strip()) < 50:
            try:
                text = pdf_to_ocr_text(path)
            except Exception as e:
                raise RuntimeError(f"OCR for PDF failed: {e}")
        return normalize_whitespace(text)

    elif ext in {".docx"}:
        try:
            doc = DocxDocument(path)
            text = "\n".join(p.text for p in doc.paragraphs)
            return normalize_whitespace(text)
        except Exception as e:
            raise RuntimeError(f"Reading DOCX failed: {e}")

    elif ext in {".txt", ".md"}:
        return normalize_whitespace(read_file_bytes(path).decode("utf-8", errors="ignore"))

    elif is_image_ext(ext):
        try:
            img = Image.open(path)
            text = ocr_image(img)
            return normalize_whitespace(text)
        except Exception as e:
            raise RuntimeError(f"OCR for image failed: {e}")

    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ----------------------------
# Chunking
# ----------------------------

def count_tokens(text: str, model: str = "gpt-5") -> int:
    if not HAS_TIKTOKEN:
        # crude fallback: ~4 chars per token heuristic
        return max(1, math.ceil(len(text) / 4))
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, math.ceil(len(text) / 4))


def split_by_tokens(text: str, max_tokens: int = 1200, overlap_tokens: int = 150) -> List[str]:
    if not HAS_TIKTOKEN:
        # Fallback: split by characters approx.
        approx_chars = max_tokens * 4
        olap_chars = overlap_tokens * 4
        chunks = []
        i = 0
        while i < len(text):
            chunk = text[i:i+approx_chars]
            chunks.append(chunk)
            i += approx_chars - olap_chars
        return chunks

    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    i = 0
    while i < len(tokens):
        chunk_tokens = tokens[i:i+max_tokens]
        chunks.append(enc.decode(chunk_tokens))
        i += max_tokens - overlap_tokens
    return chunks


# ----------------------------
# LLM client
# ----------------------------

class LLMClient:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 1.0):
        # Use faster, more reliable model to avoid timeouts
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=30.0)
        self.model = model
        self.temperature = temperature

    def json_response(self, system_msg: str, user_msg: str, max_output_tokens: int = 2000) -> Dict[str, Any]:
        """
        Use JSON mode when available. Fallback to best-effort parse.
        """
        try:
            chat = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                max_tokens=max_output_tokens,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ]
            )
            content = chat.choices[0].message.content
            if content:
                return json.loads(content)
            else:
                return {"error": "No content received"}
        except Exception as e:
            # Fallback to regular chat completion
            try:
                chat = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ]
                )
                txt = chat.choices[0].message.content
                # Try JSON extraction
                if txt:
                    m = re.search(r"\{.*\}", txt, flags=re.S)
                    if m:
                        return json.loads(m.group(0))
                    return {"raw_text": txt}
                return {"error": "No content received"}
            except Exception as e:
                raise RuntimeError(f"LLM call failed: {e}")


# ----------------------------
# Schemas
# ----------------------------

class PartyInfo(BaseModel):
    customer_name: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class LineItem(BaseModel):
    part_number: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = None
    extended_price: Optional[float] = None


class ClauseDiff(BaseModel):
    clause: str
    buyer_position: str
    seller_baseline: str
    variance_summary: str
    risk_level: str = Field(description="LOW/MEDIUM/HIGH")
    score_delta: float = Field(description="Negative numbers reduce compliance")
    recommendation: str


class AnalysisResult(BaseModel):
    parties: PartyInfo
    buyer_reference_numbers: List[str] = []
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    incoterms: Optional[str] = None
    payment_terms: Optional[str] = None
    governing_law: Optional[str] = None
    warranty: Optional[str] = None
    liability_cap: Optional[str] = None
    ip_indemnity: Optional[str] = None
    confidentiality: Optional[str] = None
    line_items: List[LineItem] = []
    clause_diffs: List[ClauseDiff] = []
    compliance_score: float
    brief_summary: str


# ----------------------------
# Prompts
# ----------------------------

SYSTEM_PROMPT = """You are an expert contracts analyst. Return STRICT JSON.
Be precise, concise, and practical. Avoid legalese. If unknown, set null or empty.
Score compliance from 0-100, where 100 = fully conforms to seller baseline.
IMPORTANT: If buyer terms are missing or don't conflict with seller baseline, treat as NEUTRAL (score_delta = 0). Only penalize actual conflicts or unfavorable buyer terms.
"""

USER_TEMPLATE = """You are given:
1) BUYER CONTRACT TEXT (possibly partial/chunked or summarized).
2) SELLER BASELINE TERMS (markdown).

Task:
- Extract key metadata (party info, contact data, dates).
- Extract line items (part number/desc/qty/unit price/currency/extended).
- Compare buyer positions vs. seller baseline (clause-by-clause) and highlight variances.
- CRITICAL: Only flag actual conflicts. If buyer terms are missing or silent on a topic, seller's protective terms control (score_delta = 0).
- Provide risk levels (LOW/MEDIUM/HIGH) and a score_delta per variance (-10 to +0).
- Produce an overall compliance_score (0-100) and a brief_summary (<= 180 words).

Return JSON with this shape:
{{
  "parties": {{}},
  "buyer_reference_numbers": [],
  "effective_date": null,
  "expiry_date": null,
  "incoterms": null,
  "payment_terms": null,
  "governing_law": null,
  "warranty": null,
  "liability_cap": null,
  "ip_indemnity": null,
  "confidentiality": null,
  "line_items": [{{}}],
  "clause_diffs": [{{}}],
  "compliance_score": 0,
  "brief_summary": "..."
}}

SELLER BASELINE TERMS (markdown):
---
{seller_terms}
---

BUYER CONTRACT TEXT:
---
{contract_text}
---
"""


# ----------------------------
# Pipeline
# ----------------------------

def summarize_long_text_for_fit(llm: LLMClient, text: str, target_tokens: int = 8000) -> str:
    """If text too long, auto-summarize to fit."""
    if count_tokens(text) <= target_tokens:
        return text

    chunks = split_by_tokens(text, max_tokens=1200, overlap_tokens=150)
    # Map: summarize each chunk
    partial_summaries = []
    for idx, ch in enumerate(chunks, 1):
        u = f"Summarize this contract chunk (#{idx}) for later clause-level comparison. Keep facts, numbers, party names, and clause language. <= 300 words.\n\n---\n{ch}\n---"
        js = llm.json_response(
            system_msg="You are a world-class summarizer. Respond in JSON: {\"summary\": \"...\"}",
            user_msg=u,
            max_output_tokens=800
        )
        partial_summaries.append(js.get("summary", ""))

    joined = "\n\n".join(partial_summaries)
    # Reduce: one final concise summary
    final_js = llm.json_response(
        system_msg="You are a world-class summarizer. Respond in JSON: {\"summary\": \"...\"}",
        user_msg=f"Combine the following into one concise, clause-preserving summary (<=1500 words):\n\n{joined}",
        max_output_tokens=1200
    )
    return final_js.get("summary", joined)


def analyze_contract(
    contract_text: str,
    seller_terms_md: str,
    model: str = "gpt-4o-mini"
) -> AnalysisResult:
    llm = LLMClient(model=model, temperature=1.0)

    # Simplify by using first 4000 characters to avoid timeouts
    fit_text = contract_text[:4000] if len(contract_text) > 4000 else contract_text

    user_msg = USER_TEMPLATE.format(
        seller_terms=seller_terms_md,
        contract_text=fit_text
    )

    js = llm.json_response(SYSTEM_PROMPT, user_msg, max_output_tokens=2000)

    # If LLM didn't compute compliance, derive one from deltas (defensive)
    if "compliance_score" not in js or js.get("compliance_score") is None:
        deltas = [d.get("score_delta", 0) for d in js.get("clause_diffs", []) if isinstance(d, dict)]
        base = 100.0 + sum(deltas)
        js["compliance_score"] = max(0.0, min(100.0, base))

    # Validate + coerce to schema
    try:
        result = AnalysisResult(**js)
    except ValidationError:
        # Best-effort coercion
        js.setdefault("parties", {})
        js.setdefault("line_items", [])
        js.setdefault("clause_diffs", [])
        js.setdefault("brief_summary", js.get("brief_summary", "")[:1000])
        js["compliance_score"] = float(js.get("compliance_score", 0))
        result = AnalysisResult(**js)

    return result


def write_report(out_dir: str, result: AnalysisResult, contract_path: str, seller_path: str) -> Tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    json_path = os.path.join(out_dir, f"t3rms_report_{ts}.json")
    md_path = os.path.join(out_dir, f"t3rms_report_{ts}.md")

    # Write JSON report
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result.dict(), f, indent=2, default=str)

    # Write Markdown report
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Contract Analysis Report\n\n")
        f.write(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
        f.write(f"**Contract File:** {os.path.basename(contract_path)}\n")
        f.write(f"**Seller Baseline:** {os.path.basename(seller_path)}\n\n")
        
        f.write(f"## Compliance Score: {result.compliance_score:.1f}/100\n\n")
        
        f.write(f"## Summary\n\n{result.brief_summary}\n\n")
        
        if result.parties.customer_name:
            f.write(f"## Party Information\n\n")
            f.write(f"**Customer:** {result.parties.customer_name}\n")
            if result.parties.address_line:
                f.write(f"**Address:** {result.parties.address_line}\n")
            if result.parties.city:
                f.write(f"**City:** {result.parties.city}\n")
            if result.parties.email:
                f.write(f"**Email:** {result.parties.email}\n")
            f.write("\n")
        
        if result.clause_diffs:
            f.write(f"## Clause Differences\n\n")
            for diff in result.clause_diffs:
                f.write(f"### {diff.clause}\n\n")
                f.write(f"**Risk Level:** {diff.risk_level}\n")
                f.write(f"**Score Impact:** {diff.score_delta:+.1f}\n\n")
                f.write(f"**Buyer Position:** {diff.buyer_position}\n\n")
                f.write(f"**Seller Baseline:** {diff.seller_baseline}\n\n")
                f.write(f"**Variance:** {diff.variance_summary}\n\n")
                f.write(f"**Recommendation:** {diff.recommendation}\n\n")
        
        if result.line_items:
            f.write(f"## Line Items\n\n")
            for item in result.line_items:
                f.write(f"- **{item.part_number or 'N/A'}**: {item.description or 'N/A'}")
                if item.quantity:
                    f.write(f" (Qty: {item.quantity})")
                if item.unit_price:
                    f.write(f" @ {item.currency or '$'}{item.unit_price}")
                f.write("\n")

    return json_path, md_path


# Command-line interface for standalone usage
def main():
    parser = argparse.ArgumentParser(description="Analyze buyer contract vs. seller baseline terms")
    parser.add_argument("contract_file", help="Path to buyer contract file")
    parser.add_argument("--seller-terms", default="seller_baseline_terms.md",
                        help="Path to seller baseline terms (markdown)")
    parser.add_argument("--model", default="gpt-5", help="OpenAI model to use")
    parser.add_argument("--output-dir", default="reports", help="Output directory for reports")
    
    args = parser.parse_args()
    
    try:
        # Extract text
        contract_text = extract_text_from_file(args.contract_file)
        
        # Load seller terms
        with open(args.seller_terms, 'r', encoding='utf-8') as f:
            seller_terms = f.read()
        
        # Analyze
        result = analyze_contract(contract_text, seller_terms, model=args.model)
        
        # Output brief summary to stdout
        print(f"Compliance Score: {result.compliance_score:.1f}/100")
        print(f"Summary: {result.brief_summary}")
        
        # Write detailed reports
        json_path, md_path = write_report(args.output_dir, result, args.contract_file, args.seller_terms)
        print(f"Reports written to: {json_path}, {md_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
