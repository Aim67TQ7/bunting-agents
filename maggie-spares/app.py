"""Maggie Spares — FastAPI main application with email polling background task."""

import os
import json
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from ai_engine import classify_intent, generate_response, direct_query
from epicor_client import query_baq, multi_query
from email_poller import poll_loop, get_stats
from email_responder import format_review_email
from bom_search import fuzzy_filter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/app/logs/maggie-spares.log"),
    ],
)
log = logging.getLogger("maggie-spares")

API_KEY = os.environ.get("MAGGIE_API_KEY", "")
START_TIME = datetime.utcnow()


def _apply_bom_fuzzy_filter(plan: dict, results: list[dict]) -> list[dict]:
    """If the AI plan includes bom_search_terms, apply fuzzy filtering to GPT_Bom results."""
    search_terms = plan.get("bom_search_terms", "").strip()
    if not search_terms:
        return results

    filtered = []
    for r in results:
        if r.get("baq_id") in ("GPT_Bom", "GPT_Bom2") and r.get("data"):
            bom_results = fuzzy_filter(r["data"], search_terms)
            # Replace raw data with filtered matches + wear suggestions
            combined = bom_results["matches"] + bom_results["wear_suggestions"]
            r["data"] = combined
            r["count"] = len(combined)
            r["fuzzy_search"] = {
                "terms": search_terms,
                "tokens": bom_results["search_tokens"],
                "match_count": len(bom_results["matches"]),
                "wear_count": len(bom_results["wear_suggestions"]),
                "total_scanned": bom_results["total_bom_records"],
            }
        filtered.append(r)
    return filtered


async def process_email(sender: str, subject: str, body: str) -> str:
    """Core pipeline: email → AI classify → Epicor query → AI response → HTML email."""
    log.info(f"Pipeline start: {sender} | {subject}")

    # Step 1: AI classifies intent and builds query plan
    plan = await classify_intent(subject, body, sender)
    queries = plan.get("queries", [])
    explanation = plan.get("explanation", "No explanation provided.")
    log.info(f"Query plan: {len(queries)} queries — {explanation}")

    # Step 2: Execute Epicor queries (GET only)
    if queries:
        results = await multi_query(queries)
    else:
        results = []

    # Step 2.5: Apply BOM fuzzy filter if search terms present
    results = _apply_bom_fuzzy_filter(plan, results)

    # Step 3: AI generates conversational response (pass $select for field filtering)
    query_selects = [q.get("select", "") for q in queries]
    ai_response = await generate_response(subject, body, sender, results, explanation, query_selects)

    # Step 4: Format as HTML review email
    baqs_used = [q.get("baq_id", "?") for q in queries]
    html = format_review_email(sender, subject, body, ai_response, baqs_used)

    log.info(f"Pipeline complete: {sender} | {len(queries)} queries | response {len(ai_response)} chars")
    return html


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start email poller as background task."""
    log.info("Maggie Spares starting up")
    task = asyncio.create_task(poll_loop(process_email))
    yield
    task.cancel()
    log.info("Maggie Spares shutting down")


app = FastAPI(title="Maggie Spares", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _check_auth(request: Request) -> bool:
    if not API_KEY:
        return True
    key = request.headers.get("X-API-Key", "")
    if not key:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth[7:]
    return key == API_KEY


@app.get("/health")
async def health():
    email_stats = get_stats()
    return {
        "agent": "MAGGIE_SPARES",
        "status": "ok",
        "uptime_seconds": (datetime.utcnow() - START_TIME).total_seconds(),
        "emails_processed": email_stats["emails_processed"],
        "emails_errored": email_stats["emails_errored"],
        "last_poll": email_stats["last_poll"],
        "last_email_from": email_stats["last_email_from"],
        "started_at": email_stats["started_at"],
    }


@app.get("/stats")
async def stats(request: Request):
    if not _check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    email_stats = get_stats()
    return {
        "agent": "MAGGIE_SPARES",
        "uptime_seconds": (datetime.utcnow() - START_TIME).total_seconds(),
        **email_stats,
    }


@app.post("/ask")
async def ask(request: Request):
    """Direct query endpoint (like Magnus /ask). Requires API key."""
    if not _check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized. Provide X-API-Key header.")

    body = await request.json()
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="No question provided")

    log.info(f"Direct query: {question[:100]}")

    # Classify and query
    plan = await classify_intent("Direct Query", question, "api-user")
    queries = plan.get("queries", [])
    explanation = plan.get("explanation", "")

    if queries:
        results = await multi_query(queries)
    else:
        results = []

    # Apply BOM fuzzy filter if search terms present
    results = _apply_bom_fuzzy_filter(plan, results)

    # Generate response (pass $select for field filtering)
    query_selects = [q.get("select", "") for q in queries]
    ai_response = await generate_response("Direct Query", question, "api-user", results, explanation, query_selects)

    return {
        "agent": "MAGGIE_SPARES",
        "question": question,
        "answer": ai_response,
        "queries_executed": [q.get("baq_id") for q in queries],
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# Web Form — structured BOM / spare parts lookup
# ---------------------------------------------------------------------------

FORM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Maggie Spares — BOM Lookup</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f4f8; color: #1a202c; }
  .header { background: linear-gradient(135deg, #1a365d, #2563eb); color: white; padding: 24px 32px; }
  .header h1 { font-size: 22px; margin-bottom: 4px; }
  .header p { opacity: 0.85; font-size: 13px; }
  .container { max-width: 720px; margin: 24px auto; padding: 0 16px; }
  .card { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 24px; margin-bottom: 20px; }
  label { display: block; font-weight: 600; font-size: 13px; margin-bottom: 4px; color: #4a5568; text-transform: uppercase; letter-spacing: 0.5px; }
  input, select { width: 100%; padding: 10px 12px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 15px; margin-bottom: 16px; }
  input:focus, select:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
  .row { display: flex; gap: 12px; }
  .row > div { flex: 1; }
  button { background: #2563eb; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 15px; font-weight: 600; cursor: pointer; width: 100%; }
  button:hover { background: #1d4ed8; }
  button:disabled { background: #94a3b8; cursor: not-allowed; }
  .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid white; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 8px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
  #results { margin-top: 20px; }
  .result-card { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 12px; }
  .result-card h3 { color: #1a365d; margin-bottom: 12px; font-size: 16px; }
  .match-score { display: inline-block; background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }
  .buy-tag { display: inline-block; background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; padding: 8px; background: #f7fafc; border-bottom: 2px solid #e2e8f0; font-size: 12px; text-transform: uppercase; color: #718096; }
  td { padding: 8px; border-bottom: 1px solid #edf2f7; }
  tr:hover td { background: #f7fafc; }
  .error { background: #fed7d7; color: #9b2c2c; padding: 12px; border-radius: 6px; }
  .info { background: #e2e8f0; color: #4a5568; padding: 12px; border-radius: 6px; font-size: 13px; }
</style>
</head>
<body>
<div class="header">
  <h1>Maggie Spares</h1>
  <p>BOM &amp; Spare Parts Lookup — Bunting Magnetics</p>
</div>
<div class="container">
  <div class="card">
    <form id="bomForm">
      <div class="row">
        <div>
          <label>Identifier Type</label>
          <select id="idType">
            <option value="auto" selected>Auto-detect</option>
            <option value="order">Order Number</option>
            <option value="po">PO Number</option>
            <option value="job">Job Number</option>
            <option value="serial">Serial Number</option>
          </select>
        </div>
        <div>
          <label>Number / Value</label>
          <input type="text" id="idValue" placeholder="e.g. 9433117" required>
        </div>
      </div>
      <label>Customer Name <span style="font-weight:400;color:#a0aec0">(optional — helps narrow results)</span></label>
      <input type="text" id="customer" placeholder="e.g. Weima">
      <label>Part Description <span style="font-weight:400;color:#a0aec0">(optional — fuzzy search BOM)</span></label>
      <input type="text" id="description" placeholder="e.g. drawer filter front">
      <div class="row">
        <div>
          <label>Company</label>
          <select id="company">
            <option value="BMC" selected>BMC</option>
            <option value="BME">BME</option>
            <option value="MAI">MAI</option>
          </select>
        </div>
        <div style="display:flex;align-items:flex-end;">
          <button type="submit" id="submitBtn">Search BOM</button>
        </div>
      </div>
    </form>
  </div>
  <div id="results"></div>
</div>
<script>
const form = document.getElementById('bomForm');
const btn = document.getElementById('submitBtn');
const results = document.getElementById('results');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Searching...';
  results.innerHTML = '';

  const payload = {
    id_type: document.getElementById('idType').value,
    id_value: document.getElementById('idValue').value.trim(),
    customer: document.getElementById('customer').value.trim(),
    description: document.getElementById('description').value.trim(),
    company: document.getElementById('company').value,
  };

  try {
    const resp = await fetch('/form-submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok) {
      results.innerHTML = '<div class="error">' + (data.detail || 'Query failed') + '</div>';
      return;
    }
    renderResults(data);
  } catch (err) {
    results.innerHTML = '<div class="error">Request failed: ' + err.message + '</div>';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Search BOM';
  }
});

function renderResults(data) {
  let html = '';

  if (data.fuzzy_search) {
    const fs = data.fuzzy_search;
    html += '<div class="info" style="margin-bottom:12px;">';
    html += 'Searched <strong>' + fs.total_scanned + '</strong> BOM records for tokens: <strong>' + fs.tokens.join(', ') + '</strong>';
    html += ' — found <strong>' + fs.match_count + '</strong> matches';
    if (fs.wear_count > 0) html += ' + <strong>' + fs.wear_count + '</strong> wear suggestions';
    html += '</div>';
  }

  if (data.matches && data.matches.length > 0) {
    html += '<div class="result-card"><h3>Matching Parts</h3>';
    html += buildTable(data.matches, true);
    html += '</div>';
  }

  if (data.wear_suggestions && data.wear_suggestions.length > 0) {
    html += '<div class="result-card"><h3>Wear / Spare Part Suggestions</h3>';
    html += buildTable(data.wear_suggestions, false);
    html += '</div>';
  }

  if (data.all_components && data.all_components.length > 0 && !data.matches) {
    html += '<div class="result-card"><h3>All BOM Components (' + data.total_records + ' total)</h3>';
    html += buildTable(data.all_components, false);
    html += '</div>';
  }

  if (!html) {
    html = '<div class="info">No BOM records found for this query. Check the order/job number and try again.</div>';
  }

  results.innerHTML = html;
}

function buildTable(rows, showScore) {
  let t = '<table><thead><tr>';
  if (showScore) t += '<th>Score</th>';
  t += '<th>Part Number</th><th>Description</th><th>Qty/Per</th><th>Required</th><th>Vendor</th><th>Job</th>';
  t += '</tr></thead><tbody>';
  for (const r of rows) {
    t += '<tr>';
    if (showScore) {
      const pct = Math.round((r._match_score || 0) * 100);
      t += '<td><span class="match-score">' + pct + '%</span></td>';
    }
    const partNum = r.Part_PartNum || r.JobMtl_PartNum || '';
    const partDesc = r.Part_PartDescription || r.JobMtl_Description || '';
    const jobNum = r.JobProd_JobNum || r.JobMtl_JobNum || '';
    const vendor = r.Vendor_Name || '';
    t += '<td><strong>' + partNum + '</strong></td>';
    t += '<td>' + partDesc + '</td>';
    t += '<td>' + (r.JobMtl_QtyPer || '') + '</td>';
    t += '<td>' + (r.JobMtl_RequiredQty || '') + '</td>';
    t += '<td>' + (vendor ? '<span class="buy-tag">' + vendor + '</span>' : '') + '</td>';
    t += '<td>' + jobNum + '</td>';
    t += '</tr>';
  }
  t += '</tbody></table>';
  return t;
}
</script>
</body>
</html>"""


@app.get("/form", response_class=HTMLResponse)
async def form_page():
    """Serve the BOM lookup web form."""
    return FORM_HTML


@app.post("/form-submit")
async def form_submit(request: Request):
    """Handle structured BOM form submission. No Gemini needed — direct Epicor query + fuzzy filter."""
    body = await request.json()
    id_type = body.get("id_type", "order")
    id_value = body.get("id_value", "").strip()
    customer = body.get("customer", "").strip()
    description = body.get("description", "").strip()
    company = body.get("company", "BMC")

    if not id_value and not customer:
        raise HTTPException(status_code=400, detail="Provide at least an order/PO/job number or customer name.")

    log.info(f"Form query: type={id_type} value={id_value} customer={customer} desc={description}")

    # Build the BOM filter using GPT_Bom2 field names
    # GPT_Bom2 uses: JobProd_OrderNum (int), JobProd_JobNum (string),
    #                 Customer_Name, OrderHed_PONum, Part_PartNum
    id_filter = ""
    if id_type == "auto" and id_value:
        # Auto-detect: try order number first, then job prefix, then PO
        order_filter = f"JobProd_OrderNum eq {id_value}"
        test_result = await query_baq(baq_id="GPT_Bom2", company=company, filter_str=order_filter, top=5)
        if test_result.get("data"):
            id_filter = order_filter
            log.info(f"Auto-detect: '{id_value}' matched as order number")
        else:
            # Try as job prefix (order and job share first 7 digits)
            job_filter = f"startswith(JobProd_JobNum, '{id_value}')"
            test_result = await query_baq(baq_id="GPT_Bom2", company=company, filter_str=job_filter, top=5)
            if test_result.get("data"):
                id_filter = job_filter
                log.info(f"Auto-detect: '{id_value}' matched via job prefix")
            else:
                # Try as PO number
                po_filter = f"OrderHed_PONum eq '{id_value}'"
                test_result = await query_baq(baq_id="GPT_Bom2", company=company, filter_str=po_filter, top=5)
                if test_result.get("data"):
                    id_filter = po_filter
                    log.info(f"Auto-detect: '{id_value}' matched as PO number")
        if not id_filter and not customer:
            raise HTTPException(status_code=404, detail=f"Number '{id_value}' not found as order, job, or PO number.")
    elif id_type == "order" and id_value:
        id_filter = f"JobProd_OrderNum eq {id_value}"
    elif id_type == "po" and id_value:
        id_filter = f"OrderHed_PONum eq '{id_value}'"
    elif id_type == "job" and id_value:
        if "-" in id_value:
            id_filter = f"JobProd_JobNum eq '{id_value}'"
        else:
            id_filter = f"startswith(JobProd_JobNum, '{id_value}')"
    elif id_type == "serial" and id_value:
        serial_result = await query_baq(
            baq_id="GPT_serialnumbers",
            company=company,
            filter_str=f"SerialNo_SerialNumber eq '{id_value}'",
            select="SerialNo_JobNum,SerialNo_PartNum,SerialNo_SerialNumber,Customer_Name",
            top=5,
        )
        if serial_result.get("data"):
            job_num = serial_result["data"][0].get("SerialNo_JobNum", "")
            if job_num:
                id_filter = f"JobProd_JobNum eq '{job_num}'"
            else:
                raise HTTPException(status_code=404, detail=f"Serial {id_value} found but no job number linked.")
        else:
            raise HTTPException(status_code=404, detail=f"Serial number '{id_value}' not found in Epicor.")

    # Use ID filter if available, otherwise fall back to customer name only
    if id_filter:
        filter_str = id_filter
    elif customer:
        filter_str = f"startswith(Customer_Name, '{customer}')"
    else:
        raise HTTPException(status_code=400, detail="Could not build a valid filter. Provide an order, PO, job, or customer.")

    # Query GPT_Bom2 — includes vendor info and reliable order→job linkage
    bom_result = await query_baq(
        baq_id="GPT_Bom2",
        company=company,
        filter_str=filter_str,
        top=1000,
    )

    if not bom_result.get("success"):
        raise HTTPException(status_code=502, detail=f"Epicor query failed: {bom_result.get('error', 'unknown')}")

    records = bom_result.get("data", [])
    total = bom_result.get("total_available", len(records))

    # Apply fuzzy filter if description provided
    if description and records:
        bom_filtered = fuzzy_filter(records, description)
        return {
            "matches": bom_filtered["matches"],
            "wear_suggestions": bom_filtered["wear_suggestions"],
            "total_records": total,
            "fuzzy_search": {
                "terms": description,
                "tokens": bom_filtered["search_tokens"],
                "match_count": len(bom_filtered["matches"]),
                "wear_count": len(bom_filtered["wear_suggestions"]),
                "total_scanned": bom_filtered["total_bom_records"],
            },
        }

    # No description — return all components (capped at 50 for display)
    return {
        "all_components": records[:50],
        "total_records": total,
    }
