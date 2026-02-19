#!/bin/bash
# Pete Sales Agent — VPS Deployment Script
set -e

PETE_DIR="/opt/pete-sales"
echo "=== Deploying Pete Sales Agent ==="

# Create directory structure
mkdir -p $PETE_DIR/{logs,backups}

# Copy all Python files
echo "Copying agent files..."
cp /tmp/pete-sales-staging/*.py $PETE_DIR/
cp /tmp/pete-sales-staging/*.sql $PETE_DIR/

# Create .env if it doesn't exist
if [ ! -f "$PETE_DIR/.env" ]; then
    cat > $PETE_DIR/.env << 'ENVEOF'
# Pete Sales Agent Configuration
ANTHROPIC_API_KEY=REPLACE_ME
CLAUDE_MODEL=claude-sonnet-4-5-20250929
SUPABASE_URL=https://ezlmmegowggujpcnzoda.supabase.co
SUPABASE_SERVICE_KEY=REPLACE_ME
GOG_ACCOUNT=pete@by-pete.com
GOG_BIN=/usr/local/bin/gog
NOTIFICATION_EMAIL=robert@n0v8v.com
POLL_INTERVAL_SECONDS=900
POLL_QUERY=is:unread -from:me -category:promotions -category:social -category:updates
MAX_EMAILS_PER_HOUR=20
DRY_RUN=true
ENVEOF
    echo "Created .env — EDIT WITH YOUR API KEYS before starting!"
else
    echo ".env already exists, preserving."
fi

# Install systemd service
cat > /etc/systemd/system/pete-sales.service << 'SVCEOF'
[Unit]
Description=Pete Sales Agent Daemon
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pete-sales
ExecStart=/usr/bin/python3 /opt/pete-sales/pete_daemon.py
Restart=always
RestartSec=30
Environment=HOME=/root
Environment=PATH=/usr/local/bin:/usr/bin:/bin
EnvironmentFile=/opt/pete-sales/.env

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pete-sales

[Install]
WantedBy=multi-user.target
SVCEOF

# Set up cron for morning reports (7 AM ET = 12 PM UTC)
CRON_LINE="0 12 * * * /usr/bin/python3 /opt/pete-sales/pete_daemon.py report >> /opt/pete-sales/logs/report.log 2>&1"
(crontab -l 2>/dev/null | grep -v "pete_daemon.py report"; echo "$CRON_LINE") | crontab -

# Reload systemd
systemctl daemon-reload
systemctl enable pete-sales

echo ""
echo "=== Deployment complete ==="
echo ""
echo "NEXT STEPS:"
echo "1. Edit /opt/pete-sales/.env with your API keys:"
echo "   - ANTHROPIC_API_KEY"
echo "   - SUPABASE_SERVICE_KEY"
echo ""
echo "2. Run the Supabase migration:"
echo "   psql or apply via Supabase dashboard"
echo ""
echo "3. Test with dry run:"
echo "   cd /opt/pete-sales && python3 pete_daemon.py once"
echo ""
echo "4. Start the daemon:"
echo "   systemctl start pete-sales"
echo ""
echo "5. Check logs:"
echo "   journalctl -u pete-sales -f"
echo ""
echo "6. When ready, set DRY_RUN=false in .env and restart:"
echo "   systemctl restart pete-sales"
