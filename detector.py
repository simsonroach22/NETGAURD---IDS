#!/usr/bin/env python3
# ============================================================
#  NETGUARD IDS - One-Shot Detector (Test / Debug)
#  Simulates a single packet and prints what the model decides.
#  Useful to verify the model is working before running live.
#  Usage: python detector.py
# ============================================================
import joblib
import pandas as pd
from datetime import datetime
import os

from config import MODEL_PATH, LOG_FILE
from threat_rules import threat_check

# ── Load model ────────────────────────────────────────────────
model = joblib.load(MODEL_PATH)
print(f"Model loaded from {MODEL_PATH}")
print(f"Classes: {model.classes_}")

# ── Test cases ────────────────────────────────────────────────
TEST_CASES = [
    {"packet_size": 200,  "packet_rate": 10,  "protocol": 1, "desc": "Normal TCP traffic"},
    {"packet_size": 4000, "packet_rate": 150, "protocol": 1, "desc": "DoS Attack pattern"},
    {"packet_size": 80,   "packet_rate": 80,  "protocol": 2, "desc": "Port scan pattern"},
    {"packet_size": 100,  "packet_rate": 30,  "protocol": 3, "desc": "Slow probe pattern"},
]

os.makedirs("logs", exist_ok=True)

print("\n=== Running test cases ===\n")

for tc in TEST_CASES:
    features = pd.DataFrame(
        [[tc["packet_size"], tc["packet_rate"], tc["protocol"]]],
        columns=["packet_size", "packet_rate", "protocol"]
    )

    pred  = model.predict(features)[0]
    proba = model.predict_proba(features).max()
    rule  = threat_check(tc["packet_rate"])

    # Final decision: rule takes priority
    decision = rule if rule else (pred if pred != "normal" else "NORMAL")

    status = "✅ NORMAL" if decision == "NORMAL" else f"🚨 {decision}"
    print(f"  [{tc['desc']}]")
    print(f"    ML prediction : {pred} ({proba:.0%} confidence)")
    print(f"    Rule check    : {rule or 'none triggered'}")
    print(f"    Final decision: {status}")
    print()

    # Log any detections
    if decision != "NORMAL":
        ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{ts}] ALERT: {decision} | Test case: {tc['desc']}\n"
        with open(LOG_FILE, "a") as f:
            f.write(msg)

print(f"Any detections logged to {LOG_FILE}")
