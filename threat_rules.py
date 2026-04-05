# ============================================================
#  NETGUARD IDS - Rule-Based Threat Detection
# ============================================================
from config import DOS_RATE, SCAN_RATE, PROBE_RATE


def threat_check(rate: int) -> str | None:
    """
    Returns a threat label if the packet rate crosses a threshold,
    otherwise returns None (clean traffic).
    """
    if rate > DOS_RATE:
        return "DoS Attack"
    if rate > SCAN_RATE:
        return "Port Scan"
    if rate > PROBE_RATE:
        return "Slow Probe"
    return None
