# ============================================================
#  NETGUARD IDS - Hybrid Detection Engine
#  Combines ML model predictions with rule-based thresholds.
#  Rules fire first (fast); ML catches what rules miss.
# ============================================================
import time
import joblib
import pandas as pd
from collections import deque
from config import TIME_WINDOW, MODEL_PATH
from threat_rules import threat_check

# Shared rolling window — stores timestamps of recent packets
packet_times: deque = deque(maxlen=500)

# Load trained Random Forest model once at import time
model = joblib.load(MODEL_PATH)


def analyze(packet_size: int, protocol: int) -> str | None:
    """
    Analyse a single packet and return a threat label or None.

    Parameters
    ----------
    packet_size : raw byte length of the captured packet
    protocol    : integer-encoded protocol (1=TCP, 2=UDP, 3=Other)

    Returns
    -------
    Threat label string, or None if traffic looks normal.
    """
    now = time.time()
    packet_times.append(now)

    # Packet rate over the rolling TIME_WINDOW
    rate = sum(1 for t in packet_times if now - t < TIME_WINDOW)

    # --- Rule-based check (fast path) ---
    rule_alert = threat_check(rate)
    if rule_alert:
        return rule_alert

    # --- ML check (slower path, catches subtle patterns) ---
    features = pd.DataFrame(
        [[packet_size, rate, protocol]],
        columns=["packet_size", "packet_rate", "protocol"]
    )

    try:
        pred = model.predict(features)[0]
        proba = model.predict_proba(features).max()

        if pred != "normal" and proba >= 0.6:
            return f"ML:{pred.upper()}"   # e.g. "ML:DOS" or "ML:SCAN"
    except Exception as e:
        print(f"[DetectionEngine] ML error: {e}")

    return None
