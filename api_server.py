#!/usr/bin/env python3
# ============================================================
#  NETGUARD IDS - FastAPI Alert Server
#  Start: uvicorn api_server:app --host 0.0.0.0 --port 8000
# ============================================================
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import LOG_FILE

app = FastAPI(title="NETGUARD IDS API", version="1.0")

# Allow Streamlit (same machine, different port) to call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def parse_line(line: str) -> dict:
    """Turn a log line into a structured dict."""
    line = line.strip()
    if not line:
        return {}
    try:
        ts_part, _, rest = line.partition("] ")
        timestamp = ts_part.lstrip("[")
        level, _, message = rest.partition(": ")
        return {
            "timestamp": timestamp,
            "level":     level.strip(),
            "message":   message.strip(),
        }
    except Exception:
        return {"timestamp": "", "level": "RAW", "message": line}


@app.get("/alerts")
def get_alerts(limit: int = 100):
    """Return the last `limit` alert lines as structured JSON."""
    if not os.path.exists(LOG_FILE):
        return {"alerts": [], "total": 0}

    with open(LOG_FILE) as f:
        lines = [l for l in f.readlines() if l.strip()]

    parsed  = [parse_line(l) for l in lines[-limit:]]
    alerts  = [p for p in parsed if p]

    return {
        "alerts": alerts,
        "total":  len(lines),
        "shown":  len(alerts),
    }


@app.get("/status")
def status():
    """Quick health-check — is the IDS log file present?"""
    running = os.path.exists("ids.pid")
    return {
        "ids_running": running,
        "log_exists":  os.path.exists(LOG_FILE),
        "log_lines":   sum(1 for _ in open(LOG_FILE)) if os.path.exists(LOG_FILE) else 0,
    }


@app.delete("/alerts")
def clear_alerts():
    """Wipe the log file."""
    if os.path.exists(LOG_FILE):
        open(LOG_FILE, "w").close()
    return {"cleared": True}
