# ============================================================
#  NETGUARD IDS - Flow / Connection Tracker
#  Tracks packet counts and byte totals per (src, dst) pair.
# ============================================================
from collections import defaultdict

# {(src_ip, dst_ip): {"packets": int, "bytes": int}}
_flows: dict = defaultdict(lambda: {"packets": 0, "bytes": 0})


def update_flow(src: str, dst: str, pkt_size: int) -> dict:
    """
    Record a packet and return updated stats for this flow.

    Returns
    -------
    dict with keys "packets" and "bytes"
    """
    key = (src, dst)
    _flows[key]["packets"] += 1
    _flows[key]["bytes"]   += pkt_size
    return dict(_flows[key])


def get_flow(src: str, dst: str) -> dict:
    """Return current stats for a flow without updating."""
    return dict(_flows.get((src, dst), {"packets": 0, "bytes": 0}))


def clear_flows() -> None:
    """Reset all tracked flows (called on IDS restart)."""
    _flows.clear()
