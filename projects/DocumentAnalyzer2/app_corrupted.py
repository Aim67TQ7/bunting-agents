import os
import logging
import re
import json
import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import tempfile
import traceback

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

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Add iframe-friendly headers
@app.after_request
def add_iframe_headers(response):
    # Allow iframe embedding from any domain
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    # Add CSP to allow iframe embedding
    response.headers['Content-Security-Policy'] = "frame-ancestors *;"
    return response

# Configuration
UPLOAD_FOLDER = 'uploads'
REPORTS_FOLDER = 'reports'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'md', 'png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['REPORTS_FOLDER'] = REPORTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# ----------------------------
# Utilities
# ----------------------------

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_image_ext(ext: str) -> bool:
    return ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}

def normalize_whitespace(text: str) -> str:
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def try_pdf_text(path: str) -> str:
    try:
        reader = PdfReader(path)
        raw = []
        for page in reader.pages:
            t = page.extract_text() or ""
            raw.append(t)
        return "\n\n".join(raw)
    except Exception:
        pass
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
    images = convert_from_path(path, dpi=300)
    parts = []
    for im in images:
        parts.append(ocr_image(im))
    return "\n\n".join(parts)

def extract_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text = try_pdf_text(path)
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
        with open(path, 'rb') as f:
            return normalize_whitespace(f.read().decode("utf-8", errors="ignore"))
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

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    if not HAS_TIKTOKEN:
        return max(1, math.ceil(len(text) / 4))
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, math.ceil(len(text) / 4))

def split_by_tokens(text: str, max_tokens: int = 1200, overlap_tokens: int = 150) -> List[str]:
    if not HAS_TIKTOKEN:
        approx_chars = max_tokens * 4
        olap_chars = overlap_tokens * 4
        chunks = []
        i = 0
        while i < len(text):
            chunk = text[i:i+approx_chars]
            chunks.append(chunk)
            i += max(1, approx_chars - olap_chars)
        return chunks
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    i = 0
    while i < len(tokens):
        chunk_tokens = tokens[i:i+max_tokens]
        chunks.append(enc.decode(chunk_tokens))
        i += max(1, max_tokens - overlap_tokens)
    return chunks

# ----------------------------
# LLM Client
# ----------------------------

class LLMClient:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 1.0):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=30.0)
        self.model = model
        self.temperature = temperature

    def json_response(self, system_msg: str, user_msg: str, max_output_tokens: int = 2000) -> Dict[str, Any]:
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
            try:
                chat = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ]
                )
                txt = chat.choices[0].message.content
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
    seller_baseline: str = ""
    variance_summary: str = ""
    risk_level: str = Field(description="LOW/MEDIUM/HIGH")
    score_delta: float = Field(description="Negative numbers reduce compliance")
    recommendation: str = ""

class AnalysisResult(BaseModel):
    document_type: Optional[str] = "CONTRACT"
    risk_summary: Optional[str] = None
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

SYSTEM_PROMPT = """You are an in-house legal counsel for a manufacturing company analyzing buyer documents to protect the seller from litigation and financial risk.

Analyze from SELLER'S PROTECTIVE PERSPECTIVE:
- Identify terms that expose seller to liability, financial risk, or litigation
- Flag buyer terms that deviate from seller's established baseline protections
- Focus on risk mitigation and business protection for the seller
- Score compliance from 0-100, where 100 = buyer document fully accepts seller's protective terms

Return STRICT JSON format only.
"""

USER_TEMPLATE = """You are an in-house attorney analyzing buyer documents to identify legal risks and litigation exposure. 

FIRST: Determine the document type:
- CONTRACT: Full agreement with terms and conditions
- PURCHASE ORDER (PO): Order document that may incorporate terms by reference
- QUOTE/RFQ: Pricing document that may contain binding terms

Analyze from IN-HOUSE ATTORNEY PERSPECTIVE focused on:
- Risk avoidance and litigation prevention
- Unfavorable terms that expose the seller to liability
- Missing protective clauses that should be negotiated
- Terms that deviate from seller's standard baseline

Task:
- Extract key metadata (party info, contact data, dates)
- Extract line items with proper currency parsing:
  * USD8051.00 → currency: "USD", unit_price: 8051.00
  * $500.00 → currency: "USD", unit_price: 500.00
  * Calculate extended_price = unit_price * quantity
- Identify LEGAL RISKS in buyer's terms vs. seller baseline
- Flag HIGH RISK clauses that could lead to litigation
- Provide attorney recommendations for risk mitigation

Risk Assessment Priorities:
1. LIABILITY EXPOSURE: Unlimited liability, consequential damages
2. INDEMNITY OBLIGATIONS: Broad indemnification requirements
3. PAYMENT RISKS: Extended terms, disputed payment clauses
4. IP RISKS: Work-for-hire, broad IP assignments
5. COMPLIANCE GAPS: Missing force majeure, limitation clauses

Return JSON with this shape:
{{
  "document_type": "CONTRACT/PO/QUOTE",
  "risk_summary": "Overall legal risk assessment",
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
  "line_items": [{{
    "part_number": "string or null",
    "description": "string or null", 
    "quantity": "number or null",
    "unit_price": "number (without currency symbol)",
    "currency": "USD/EUR/GBP etc (extracted from price)",
    "extended_price": "unit_price * quantity when both available"
  }}],
  "clause_diffs": [{{
    "clause": "Clause name",
    "buyer_position": "What buyer document states",
    "seller_baseline": "What seller prefers",
    "variance_summary": "Key differences",
    "risk_level": "LOW/MEDIUM/HIGH",
    "score_delta": -10,
    "recommendation": "Attorney recommendation for risk mitigation"
  }}],
  "compliance_score": 0,
  "brief_summary": "Legal risk assessment from in-house attorney perspective"
}}

SELLER BASELINE TERMS (markdown):
---
{seller_terms}
---

BUYER DOCUMENT TEXT:
---
{contract_text}
---
"""

# ----------------------------
# Pipeline
# ----------------------------

def analyze_bunting_document(contract_text: str, model: str = \"gpt-4o-mini\") -> AnalysisResult:\n    \"\"\"Analyze Bunting seller document to extract customer info and line items.\"\"\"\n    llm = LLMClient(model=model, temperature=0.3)\n    \n    bunting_prompt = \"\"\"Extract customer information and line items from this Bunting seller document (quote/acknowledgement/invoice).\n    \nReturn JSON with this exact structure:\n    {\n      \"document_type\": \"SELLER_DOCUMENT\", \n      \"parties\": {\n        \"customer_name\": \"string or null\",\n        \"address_line\": \"string or null\",\n        \"city\": \"string or null\", \n        \"state\": \"string or null\",\n        \"phone\": \"string or null\",\n        \"email\": \"string or null\"\n      },\n      \"line_items\": [{\n        \"part_number\": \"string or null\",\n        \"description\": \"string or null\",\n        \"quantity\": \"number or null\",\n        \"unit_price\": \"number or null\",\n        \"currency\": \"USD\",\n        \"extended_price\": \"number or null\"\n      }],\n      \"compliance_score\": 100.0,\n      \"brief_summary\": \"Bunting seller document processed - customer info and line items extracted.\"\n    }\"\"\"\n    \n    fit_text = contract_text[:4000] if len(contract_text) > 4000 else contract_text\n    js = llm.json_response(bunting_prompt, f\"Document text:\\n{fit_text}\", max_output_tokens=1500)\n    \n    # Ensure required fields\n    js.setdefault(\"document_type\", \"SELLER_DOCUMENT\")\n    js.setdefault(\"parties\", {})\n    js.setdefault(\"line_items\", [])\n    js.setdefault(\"clause_diffs\", [])\n    js.setdefault(\"compliance_score\", 100.0)\n    js.setdefault(\"brief_summary\", \"Bunting seller document processed - customer info and line items extracted.\")\n    \n    try:\n        result = AnalysisResult(**js)\n    except ValidationError:\n        # Fallback with defaults\n        result = AnalysisResult(\n            document_type=\"SELLER_DOCUMENT\",\n            parties=PartyInfo(),\n            compliance_score=100.0,\n            brief_summary=\"Bunting seller document detected - parsing completed.\"\n        )\n    \n    return result\n\n\ndef is_bunting_document(text: str) -> bool:
    """Detect if the document is a Bunting seller document (quote, acknowledgement, etc.)"""
    bunting_indicators = [
        "bunting magnetics",
        "bunting magnetic", 
        "bunting® magnetics",
        "newton, ks",
        "newton, kansas",
        "buntingmagnetics.com",
        "800-835-2526",
        "316-284-2020",
        "quote number:",
        "acknowledgment",
        "acknowledgement",
        "pro-forma invoice",
        "proforma invoice",
        "terms and conditions of sale",
        "www.buntingmagnetics.com"
    ]
    
    text_lower = text.lower()
    # Check for multiple indicators to confirm it's a Bunting document
    matches = sum(1 for indicator in bunting_indicators if indicator in text_lower)
    return matches >= 2


def analyze_contract(contract_text: str, seller_terms_md: str, model: str = "gpt-4o-mini") -> AnalysisResult:
    llm = LLMClient(model=model, temperature=1.0)

    # Check if this is a Bunting seller document
    if is_bunting_document(contract_text):
        # This is a seller document - parse customer info and line items but no risk analysis
        return analyze_bunting_document(contract_text, model)
    
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

    # Validate + coerce to schema with defaults for missing fields
    try:
        result = AnalysisResult(**js)
    except ValidationError as e:
        app.logger.warning(f"Validation error: {e}")
        # Best-effort coercion with proper defaults
        js.setdefault("parties", {})
        js.setdefault("line_items", [])
        
        # Fix clause_diffs to have all required fields
        clause_diffs = js.get("clause_diffs", [])
        for diff in clause_diffs:
            if isinstance(diff, dict):
                diff.setdefault("buyer_position", "Position extracted from document")
                diff.setdefault("seller_baseline", "Not specified in seller terms")
                diff.setdefault("variance_summary", "Variance detected")
                diff.setdefault("recommendation", "Review clause alignment with seller baseline")
        
        js["clause_diffs"] = clause_diffs
        js.setdefault("brief_summary", js.get("brief_summary", "Analysis completed")[:1000])
        js["compliance_score"] = float(js.get("compliance_score", 0))
        
        result = AnalysisResult(**js)

    return result

def write_report(out_dir: str, result: AnalysisResult, contract_path: str, seller_path: str) -> Tuple[str, str, str]:
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(out_dir, f"t3rms_report_{ts}.json")
    md_path = os.path.join(out_dir, f"t3rms_report_{ts}.md")
    xml_path = os.path.join(out_dir, f"t3rms_report_{ts}.xml")

    # Write JSON report
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result.dict(), f, indent=2, default=str)

    # Write Markdown report
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {result.document_type or 'CONTRACT'} Analysis Report\n\n")
        f.write(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
        f.write(f"**Document Type:** {result.document_type or 'CONTRACT'}\n")
        f.write(f"**Document File:** {os.path.basename(contract_path)}\n")
        f.write(f"**Seller Baseline:** {os.path.basename(seller_path)}\n\n")
        
        f.write(f"## Compliance Score: {result.compliance_score:.1f}/100\n\n")
        
        if result.risk_summary:
            f.write(f"## Legal Risk Assessment\n\n{result.risk_summary}\n\n")
        
        f.write(f"## Analysis Summary\n\n{result.brief_summary}\n\n")
        
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
                    f.write(f" @ ${item.unit_price}")
                f.write("\n")

    # Write XML report
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<analysis_report>\n')
        f.write(f'  <metadata>\n')
        f.write(f'    <generated>{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</generated>\n')
        f.write(f'    <document_type>{result.document_type or "CONTRACT"}</document_type>\n')
        f.write(f'    <document_file>{os.path.basename(contract_path)}</document_file>\n')
        f.write(f'    <seller_baseline>{os.path.basename(seller_path)}</seller_baseline>\n')
        f.write(f'  </metadata>\n')
        f.write(f'  <compliance_score>{result.compliance_score:.1f}</compliance_score>\n')
        if result.risk_summary:
            f.write(f'  <risk_summary><![CDATA[{result.risk_summary}]]></risk_summary>\n')
        f.write(f'  <brief_summary><![CDATA[{result.brief_summary}]]></brief_summary>\n')
        
        if result.parties.customer_name:
            f.write('  <parties>\n')
            f.write(f'    <customer_name><![CDATA[{result.parties.customer_name}]]></customer_name>\n')
            if result.parties.address_line:
                f.write(f'    <address_line><![CDATA[{result.parties.address_line}]]></address_line>\n')
            if result.parties.city:
                f.write(f'    <city><![CDATA[{result.parties.city}]]></city>\n')
            if result.parties.email:
                f.write(f'    <email><![CDATA[{result.parties.email}]]></email>\n')
            f.write('  </parties>\n')
        
        if result.clause_diffs:
            f.write('  <clause_differences>\n')
            for diff in result.clause_diffs:
                f.write('    <clause_diff>\n')
                f.write(f'      <clause><![CDATA[{diff.clause}]]></clause>\n')
                f.write(f'      <risk_level>{diff.risk_level}</risk_level>\n')
                f.write(f'      <score_delta>{diff.score_delta}</score_delta>\n')
                f.write(f'      <buyer_position><![CDATA[{diff.buyer_position}]]></buyer_position>\n')
                f.write(f'      <seller_baseline><![CDATA[{diff.seller_baseline}]]></seller_baseline>\n')
                f.write(f'      <variance_summary><![CDATA[{diff.variance_summary}]]></variance_summary>\n')
                f.write(f'      <recommendation><![CDATA[{diff.recommendation}]]></recommendation>\n')
                f.write('    </clause_diff>\n')
            f.write('  </clause_differences>\n')
        
        if result.line_items:
            f.write('  <line_items>\n')
            for item in result.line_items:
                f.write('    <line_item>\n')
                f.write(f'      <part_number><![CDATA[{item.part_number or ""}]]></part_number>\n')
                f.write(f'      <description><![CDATA[{item.description or ""}]]></description>\n')
                if item.quantity:
                    f.write(f'      <quantity>{item.quantity}</quantity>\n')
                if item.unit_price:
                    f.write(f'      <unit_price>{item.unit_price}</unit_price>\n')
                if item.extended_price:
                    f.write(f'      <extended_price>{item.extended_price}</extended_price>\n')
                f.write('    </line_item>\n')
            f.write('  </line_items>\n')
        
        f.write('</analysis_report>\n')

    return json_path, md_path, xml_path

def load_seller_baseline():
    """Load seller baseline terms from markdown file"""
    try:
        with open('seller.md', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        app.logger.warning("seller.md not found, using default terms")
        return """# Default Seller Baseline Terms

## Payment Terms
- Net 30 days from invoice date
- 2% discount for payment within 10 days

## Warranty
- 12 months limited warranty on all products
- Warranty covers manufacturing defects only

## Liability
- Liability limited to product purchase price
- No liability for consequential or indirect damages

## Intellectual Property
- Customer acknowledges seller's IP rights
- No reverse engineering permitted

## Governing Law
- Governed by laws of Delaware, USA
- Disputes resolved through binding arbitration
"""

# ----------------------------
# Flask Routes
# ----------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if text was pasted instead of file upload
    contract_text = request.form.get('contract_text', '').strip()
    
    if contract_text:
        # Handle text input
        try:
            app.logger.info(f"Text input received: {len(contract_text)} characters")
            
            if len(contract_text) < 50:
                flash('Please paste more contract text for analysis (minimum 50 characters)', 'error')
                return redirect(url_for('index'))
            
            # Process text directly
            return process_contract_text(contract_text)
            
        except Exception as e:
            app.logger.error(f"Text processing error: {str(e)}")
            app.logger.error(traceback.format_exc())
            flash(f'Text analysis failed: {str(e)}', 'error')
            return redirect(url_for('index'))
    
    # Handle file upload (existing logic)
    if 'file' not in request.files:
        flash('Please select a file or paste contract text', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Please select a file or paste contract text', 'error')
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash(f'File type not supported. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}', 'error')
        return redirect(url_for('index'))
    
    try:
        if not file.filename:
            flash('Invalid filename', 'error')
            return redirect(url_for('index'))
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        app.logger.info(f"File uploaded: {filepath}")
        
        # Process the file
        return process_contract(filepath, filename)
        
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        app.logger.error(traceback.format_exc())
        flash(f'Upload failed: {str(e)}', 'error')
        return redirect(url_for('index'))

def process_contract_text(contract_text):
    """Process contract text directly without file upload"""
    try:
        app.logger.info(f"Starting contract analysis for pasted text")
        
        # Load seller baseline terms
        seller_terms = load_seller_baseline()
        
        # Analyze contract using OpenAI
        analysis_result = analyze_contract(contract_text, seller_terms, model="gpt-4o-mini")
        
        app.logger.info(f"Analysis completed with compliance score: {analysis_result.compliance_score}")
        
        # Generate reports
        json_path, md_path, xml_path = write_report(
            app.config['REPORTS_FOLDER'], 
            analysis_result, 
            "pasted_text.txt", 
            'seller.md'
        )
        
        return render_template('results.html', 
                             result=analysis_result,
                             filename="Pasted Contract Text",
                             json_report=os.path.basename(json_path),
                             md_report=os.path.basename(md_path),
                             xml_report=os.path.basename(xml_path))
        
    except Exception as e:
        app.logger.error(f"Processing error: {str(e)}")
        app.logger.error(traceback.format_exc())
        
        flash(f'Analysis failed: {str(e)}', 'error')
        return redirect(url_for('index'))

def process_contract(filepath, filename):
    try:
        app.logger.info(f"Starting contract analysis for: {filepath}")
        
        # Extract text from uploaded file
        contract_text = extract_text_from_file(filepath)
        app.logger.info(f"Extracted {len(contract_text)} characters from contract")
        
        if not contract_text.strip():
            flash('No text could be extracted from the uploaded file. Please check if the file is valid.', 'error')
            return redirect(url_for('index'))
        
        # Load seller baseline terms
        seller_terms = load_seller_baseline()
        
        # Analyze contract using OpenAI
        analysis_result = analyze_contract(contract_text, seller_terms, model="gpt-4o-mini")
        
        app.logger.info(f"Analysis completed with compliance score: {analysis_result.compliance_score}")
        
        # Generate reports
        json_path, md_path, xml_path = write_report(
            app.config['REPORTS_FOLDER'], 
            analysis_result, 
            filepath, 
            'seller.md'
        )
        
        # Clean up uploaded file
        try:
            os.remove(filepath)
        except Exception as e:
            app.logger.warning(f"Could not remove uploaded file: {e}")
        
        return render_template('results.html', 
                             result=analysis_result,
                             filename=filename,
                             json_report=os.path.basename(json_path),
                             md_report=os.path.basename(md_path),
                             xml_report=os.path.basename(xml_path))
        
    except Exception as e:
        app.logger.error(f"Processing error: {str(e)}")
        app.logger.error(traceback.format_exc())
        
        # Clean up uploaded file on error
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass
            
        flash(f'Analysis failed: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_report(filename):
    try:
        return send_file(
            os.path.join(app.config['REPORTS_FOLDER'], filename),
            as_attachment=True,
            download_name=filename
        )
    except FileNotFoundError:
        flash('Report file not found', 'error')
        return redirect(url_for('index'))

@app.route('/api/upload-progress')
def upload_progress():
    return jsonify({'status': 'processing'})

@app.errorhandler(413)
def too_large(e):
    flash(f'File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB', 'error')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(e):
    app.logger.error(f"Internal error: {str(e)}")
    flash('An internal error occurred. Please try again.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)