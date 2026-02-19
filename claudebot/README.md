# ClaudeBot - Enhanced Claude API with Tools

Flask API service providing Claude with tool-use capabilities: web search, Supabase CRUD, and document generation (PPTX, DOCX, XLSX, PDF).

## Deployment to VPS

### 1. Upload files

```bash
scp -P 40546 bot.py requirements.txt .env.example root@89.116.157.23:/opt/claudebot/
```

### 2. Set up on VPS

```bash
ssh -p 40546 root@89.116.157.23

cd /opt/claudebot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env  # Fill in real values
```

### 3. Create systemd service

```bash
cat > /etc/systemd/system/claudebot.service << 'EOF'
[Unit]
Description=ClaudeBot API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/claudebot
Environment=PATH=/opt/claudebot/venv/bin:/usr/bin:/bin
ExecStart=/opt/claudebot/venv/bin/gunicorn -b 127.0.0.1:8020 -w 2 --timeout 120 bot:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

```bash
systemctl daemon-reload
systemctl enable claudebot
systemctl start claudebot
systemctl status claudebot
```

### 4. Caddy reverse proxy (optional)

Add to `/etc/caddy/Caddyfile`:

```
claudebot.yourdomain.com {
    reverse_proxy 127.0.0.1:8020
}
```

```bash
systemctl reload caddy
```

## API Usage

### Health check (no auth)

```bash
curl http://127.0.0.1:8020/health
```

### Chat (HMAC authenticated)

```python
import hmac, hashlib, time, uuid, requests, json

secret = "your-shared-secret"
body = json.dumps({"message": "Search for recent AI news"})
ts = str(int(time.time()))
nonce = uuid.uuid4().hex
sig = hmac.new(secret.encode(), f"{ts}:{nonce}:{body}".encode(), hashlib.sha256).hexdigest()

r = requests.post(
    "http://127.0.0.1:8020/chat",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-Api-Signature": sig,
        "X-Request-Timestamp": ts,
        "X-Request-Nonce": nonce,
    },
)
print(r.json())
```

## Logs

```bash
journalctl -u claudebot -f
```

## Available Tools

| Tool | Description |
|------|-------------|
| `web_search` | DuckDuckGo search |
| `supabase_query` | Supabase table CRUD (select/insert/update/delete) |
| `supabase_storage_read` | Download from Supabase Storage |
| `supabase_storage_write` | Upload to Supabase Storage |
| `create_presentation` | Generate PPTX |
| `create_document` | Generate DOCX |
| `create_spreadsheet` | Generate XLSX |
| `create_pdf` | Generate PDF |
