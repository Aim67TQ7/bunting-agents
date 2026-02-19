#!/usr/bin/env python3
"""
Lightweight campaign stats API — serves JSON for the dashboard.
Runs as a simple HTTP server on port 8551.
"""
import http.server
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, "/opt/pete-sales")

STATE_FILE = "/opt/pete-sales/campaigns/batch_state.json"
CSV_FILE = "/opt/pete-sales/campaigns/first_shot.csv"
LOG_FILE = "/opt/pete-sales/logs/batch_sender.log"


def count_csv_rows(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return max(0, sum(1 for _ in f) - 1)  # minus header
    except Exception:
        return 0


def get_recent_log(path, lines=50):
    try:
        with open(path, "r") as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except Exception:
        return []


def build_stats():
    # Load state
    state = {"sent_emails": [], "total_sent": 0, "total_errors": 0, "runs": []}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)

    total_prospects = count_csv_rows(CSV_FILE)
    total_sent = state.get("total_sent", 0)
    total_errors = state.get("total_errors", 0)
    remaining = total_prospects - len(state.get("sent_emails", []))
    runs = state.get("runs", [])

    # A/B split stats from runs
    # Each batch is 50/50 A/B
    half_sent = total_sent // 2
    variant_a_sent = half_sent + (total_sent % 2)
    variant_b_sent = half_sent

    # Parse recent log for activity feed
    log_lines = get_recent_log(LOG_FILE, 100)
    activity = []
    for line in reversed(log_lines):
        line = line.strip()
        if not line:
            continue
        if "| A |" in line or "| B |" in line:
            parts = line.split(" | ")
            if len(parts) >= 5:
                activity.append({
                    "time": line[:19],
                    "variant": parts[1].strip(),
                    "name": parts[2].strip(),
                    "email": parts[3].strip(),
                    "company": parts[4].strip(),
                })
        elif "BATCH COMPLETE" in line or "BATCH RUN" in line or "ALL DONE" in line:
            activity.append({"time": line[:19], "event": line[20:].strip()})
        if len(activity) >= 30:
            break

    # ETA calculation
    if runs and remaining > 0:
        avg_batch = sum(r.get("sent", 0) for r in runs) / len(runs) if runs else 100
        batches_left = remaining / max(avg_batch, 1)
        eta_hours = batches_left  # 1 batch per hour
    else:
        eta_hours = 0

    return {
        "total_prospects": total_prospects,
        "total_sent": total_sent,
        "total_errors": total_errors,
        "remaining": max(0, remaining),
        "variant_a_sent": variant_a_sent,
        "variant_b_sent": variant_b_sent,
        "pct_complete": round(len(state.get("sent_emails", [])) / max(total_prospects, 1) * 100, 1),
        "eta_hours": round(eta_hours, 1),
        "runs": runs[-10:],  # last 10 runs
        "activity": activity[:20],  # last 20 activity items
        "last_updated": datetime.utcnow().isoformat() + "Z",
    }


class StatsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/campaign/stats":
            stats = build_stats()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())
        elif self.path == "/campaign/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default logging


if __name__ == "__main__":
    port = 8551
    server = http.server.HTTPServer(("127.0.0.1", port), StatsHandler)
    print(f"Campaign stats API running on port {port}")
    server.serve_forever()
