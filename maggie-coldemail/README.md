# Maggie Cold Email

Containerized campaign service for reactivating Bunting customers from 2018-2022.

## What It Does

- Pulls customer rows from Supabase table or CSV URL.
- Filters to eligible customers:
  - `last_business_year` in `2018..2022`
  - `years_since_last_work >= 4` (if provided)
- Asks Magnus for likely wear/replacement parts based on historical order context.
- Generates a friendly draft outreach email.
- Sends draft only to internal reviewer: `rclausing@buntingmagnetics.com`.
- Never auto-sends customer-facing emails directly.

## API

- `GET /health`
- `POST /campaign/run`

Example:

```bash
curl -X POST http://127.0.0.1:8408/campaign/run \
  -H "Content-Type: application/json" \
  -d '{"dry_run":true,"limit":200}'
```

Set `dry_run:false` to route draft emails through SMTP.

## Run

```bash
cp .env.example .env
docker compose up -d --build
```

## Expected Supabase Fields

Best-effort mapping is included, but these fields are preferred:

- `customer_id`
- `customer_name`
- `contact_name`
- `contact_email`
- `last_order_number`
- `last_order_date`
- `last_business_year`
- `years_since_last_work`

## Notes

- Magnus integration is optional. If Magnus is unavailable, Maggie still drafts outreach with a fallback note.
- Campaign state is stored in `./data/state.json` to avoid duplicate outreach drafts.
