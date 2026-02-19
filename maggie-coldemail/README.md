# Maggie Cold Email Reactivation (v2.0)

Containerized campaign service for reactivating lapsed Bunting customers (4-8 years inactive). Enriches outreach with real Epicor BOM data via maggie-spares and tracks campaign lifecycle in Supabase.

## How It Works

1. **Fetch** — Pulls lapsed customer records from Supabase table or CSV URL
2. **Filter** — Selects eligible customers (`last_business_year` 2018-2022, `years_since_last_work >= 4`)
3. **Enrich** — Calls maggie-spares `/ask` to look up real Epicor BOM wear components and order history
4. **Draft** — Generates a personalized 3-section email:
   - **Equipment Attention** — Actual wear parts from their order history with part numbers and vendors
   - **Field Service Pitch** — Promotes on-site technical support team (scheduling into late June)
   - **Reply CTA** — Invites customer to reply with equipment details or schedule a visit
5. **Route** — Sends draft to internal reviewer (`rclausing@buntingmagnetics.com`) — never directly to customers
6. **Track** — Writes campaign record to `maggie_campaigns` Supabase table

## Integration with maggie-spares

When a customer replies to the outreach email, their reply goes to `maggie@buntingmagnetics.com`. maggie-spares picks it up automatically via its existing email polling loop, classifies the request, queries Epicor BAQs, and generates a parts response — all without any code changes to maggie-spares.

```
maggie-coldemail (outbound)          maggie-spares (inbound)
       │                                    │
       │  draft email ──► Rob reviews       │
       │  Rob forwards to customer          │
       │                                    │
       │              customer replies ────►│
       │                                    │  classify → Epicor BAQ → response
       │                                    │  route to Rob for review
       │                                    │
       └──── maggie_campaigns table ◄───────┘
              (tracks full lifecycle)
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with uptime and config info |
| `/campaign/run` | POST | Execute a campaign run |
| `/campaign/stats` | GET | Campaign stats by status (optional `?campaign_id=`) |

### Run a campaign

```bash
# Dry run (no emails sent)
curl -X POST http://127.0.0.1:8408/campaign/run \
  -H "Content-Type: application/json" \
  -d '{"dry_run":true,"limit":50}'

# Live run (drafts sent to reviewer)
curl -X POST http://127.0.0.1:8408/campaign/run \
  -H "Content-Type: application/json" \
  -d '{"dry_run":false,"limit":50}'
```

### Check campaign stats

```bash
curl http://127.0.0.1:8408/campaign/stats
curl http://127.0.0.1:8408/campaign/stats?campaign_id=reactivation-20260219-140000
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | Yes | — | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | — | Supabase service role key |
| `SUPABASE_CUSTOMER_TABLE` | No | `maggie_coldemail_customers` | Table with lapsed customer records |
| `SUPABASE_CAMPAIGN_TABLE` | No | `maggie_campaigns` | Campaign tracking table |
| `SUPABASE_CSV_PUBLIC_URL` | No | — | Alternative: fetch customers from CSV URL |
| `SPARES_BASE_URL` | No | `http://maggie-spares:8402` | maggie-spares enrichment endpoint |
| `SPARES_API_KEY` | No | — | API key for maggie-spares (if required) |
| `SMTP_HOST` | Yes | — | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | No | — | SMTP username |
| `SMTP_PASS` | No | — | SMTP password |
| `SMTP_FROM` | Yes | — | From address for draft emails |
| `SMTP_USE_TLS` | No | `true` | Enable STARTTLS |
| `REVIEWER_EMAIL` | No | `rclausing@buntingmagnetics.com` | Internal reviewer for draft approval |

## Run

```bash
cp .env.example .env   # configure env vars
docker compose up -d --build
```

## Supabase Schema

### Customer input fields (CSV or table)

| Field | Description |
|-------|-------------|
| `customer_id` | ERP customer ID |
| `customer_name` | Company name |
| `contact_name` | Contact person |
| `contact_email` | Contact email |
| `last_order_number` | Most recent order number |
| `last_order_date` | Most recent order date |
| `last_business_year` | Year of last business (2018-2022) |
| `years_since_last_work` | Years since last activity |

### Campaign tracking table (`maggie_campaigns`)

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid | Primary key |
| `customer_id` | text | ERP customer ID |
| `customer_name` | text | Company name |
| `contact_email` | text | Customer contact email |
| `campaign_id` | text | Campaign run identifier |
| `outbound_subject` | text | Email subject line |
| `outbound_sent_at` | timestamptz | When draft was sent |
| `parts_included` | jsonb | Wear parts included in email |
| `order_summary` | text | Order history summary |
| `field_service_mentioned` | boolean | Whether field service was pitched |
| `reply_received_at` | timestamptz | When customer replied |
| `status` | text | `drafted → sent → replied → quoted → closed` |

## Files

| File | Purpose |
|------|---------|
| `app.py` | FastAPI application and endpoint definitions |
| `campaign_runner.py` | Campaign orchestration and eligibility logic |
| `spares_client.py` | Client for maggie-spares enrichment (Epicor BAQ data) |
| `draft_engine.py` | Email template builder (3-section reactivation format) |
| `supabase_client.py` | Customer fetch and campaign tracking |
| `mailer.py` | SMTP draft routing to reviewer |
| `models.py` | Pydantic data models |
| `magnus_client.py` | Legacy Magnus client (deprecated, kept for reference) |

## Notes

- maggie-spares enrichment is optional. If unavailable, emails still draft with a fallback note inviting the customer to reply with details.
- Campaign state is stored in `./data/state.json` to prevent duplicate outreach.
- Field service team scheduling is promoted as "into late June" — update this seasonally.
