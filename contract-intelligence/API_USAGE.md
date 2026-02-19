# Contract Intelligence API - Integration Rules

## Endpoint: `http://89.116.157.23:8002`

## Authentication
- No API key required for service calls (Claude API key is server-side)
- Rate limiting: 100 requests/minute per IP

## Integration Rules

### 1. Request Format
```json
POST /api/v1/analyze
Content-Type: application/json

{
  "document_id": "optional-tracking-id",
  "doc_type": "NDA|MSA|PO_TERMS|UNKNOWN",
  "text": "full contract text here",
  "tenant_id": "your-tenant-id",
  "policy_context": {
    "risk_tolerance": "low|medium|high",
    "must_reject": ["unlimited indemnification", "ip assignment"],
    "preferred_terms": {}
  }
}
```

### 2. Response Contract
```json
{
  "document_id": "string",
  "overall_risk": "red|yellow|green",
  "summary": "Executive summary",
  "findings": [
    {
      "id": "finding-uuid",
      "category": "payment_terms|indemnification|...",
      "severity": "red|yellow|green",
      "clause_text": "quoted text from contract",
      "explanation": "why this is risky",
      "recommendation": "accept|negotiate|reject",
      "redline_suggestion": "replacement language",
      "confidence": 0.85
    }
  ],
  "redlines": [
    {"original": "...", "suggested": "...", "priority": "high|medium|low"}
  ],
  "category_scores": {...},
  "confidence": 0.87,
  "processing_time_ms": 3500
}
```

### 3. Error Handling
| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Invalid request (text too short, malformed JSON) |
| 500 | Server error (API key issue, Claude timeout) |

### 4. Best Practices

**DO:**
- Extract text from PDF before sending (server expects plain text)
- Include `doc_type` for better analysis accuracy
- Use `document_id` for traceability
- Submit corrections via `/api/v1/correct` to improve accuracy

**DON'T:**
- Send raw PDF binary (text only)
- Send more than 15,000 characters (truncated)
- Expect real-time response (avg 3-8 seconds)

### 5. Feedback Loop
```json
POST /api/v1/correct
{
  "clause_id": "finding-id",
  "detection_text": "the flagged text",
  "original_severity": "red",
  "is_correct": false,
  "corrected_severity": "yellow"
}
```

### 6. Monitoring
- `GET /health` - Service status
- `GET /api/v1/metrics` - Performance stats
- `GET /api/v1/patterns` - Current risk patterns

## CORS
All origins allowed. Safe to call from any frontend.

## Legal Disclaimer
This service provides contract risk analysis suggestions, not legal advice.
All recommendations should be reviewed by qualified legal counsel.
