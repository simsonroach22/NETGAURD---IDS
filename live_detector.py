#!/usr/bin/env python3
# ============================================================
#  NETGUARD IDS - Live Packet Detector
#  Auto-disconnects attacker IP via Windows Firewall (both
#  directions) after ALERT_THRESHOLD alerts from one IP.
# ============================================================
import os
import re
import ctypes
import socket
import time
import subprocess
from datetime import datetime
from collections import deque, defaultdict

import joblib
import pandas as pd
from scapy.all import sniff, IP, TCP, UDP, ICMP

# ── Config ───────────────────────────────────────────────────
LOG_FILE        = "logs/ids.log"
BLOCK_LOG       = "logs/blocked_ips.log"
ALERT_THRESHOLD = 50   # blocks after 50 alerts in one session (~5-10 seconds of ping flood)
LOG_SYNC_EVERY  = 10   # sync with log every 10 alerts
IFACE           = "\\Device\\NPF_{705D4F03-D8C0-4AA6-A54E-DB8517863C2D}"

# ICMP flood threshold — Termux ping -i 0.2 x5 threads = ~25 pings/sec
# We alert if any single IP sends more than this many ICMP packets in 2 sec
ICMP_FLOOD_RATE = 10

# Set True to print every packet's src/dst/monitored_ip — helps
# diagnose why blocking isn't triggering. Turn off once working.
DEBUG_MODE = True

TRUSTED_PREFIXES = [
    "142.251.", "172.217.",
    "52.", "13.", "34.",
    "8.8.",
]

LAN_PREFIXES = [
    "192.168.", "10.",
    "172.16.", "172.17.", "172.18.",
    "172.19.", "172.20.", "172.21.",
    "172.22.", "172.23.", "172.24.",
    "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.",
    "172.31.",
]

# ── State ────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

model    = joblib.load("ids_model.pkl")
local_ip = socket.gethostbyname(socket.gethostname())

alert_counts: dict  = defaultdict(int)
blocked_ips:  set   = set()
sync_counter: dict  = defaultdict(int)
packet_times: deque = deque(maxlen=500)

# Per-IP ICMP packet timestamps for flood detection
icmp_times: dict = defaultdict(lambda: deque(maxlen=200))

# debug counter — only print every N packets to avoid spam
_dbg_counter = 0

_IP_RE = re.compile(r"Source:\s*([\d]{1,3}(?:\.[\d]{1,3}){3})")


# ── Admin check ──────────────────────────────────────────────
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def print_admin_warning() -> None:
    if not is_admin():
        print("=" * 60)
        print("  WARNING: Not running as Administrator!")
        print("  Windows Firewall blocks WILL FAIL.")
        print("  Fix: right-click terminal -> Run as administrator")
        print("=" * 60 + "\n")
    else:
        print("[NETGUARD] Running as Administrator — firewall rules will work.\n")


# ── Load already-blocked IPs ─────────────────────────────────
def load_blocked_ips() -> set:
    if not os.path.exists(BLOCK_LOG):
        return set()
    with open(BLOCK_LOG) as f:
        return set(l.strip() for l in f if l.strip())


# ── Startup log scan ─────────────────────────────────────────
def scan_log_and_preblock() -> None:
    if not os.path.exists(LOG_FILE):
        print("[NETGUARD] No existing log — starting fresh.")
        return

    ip_counts: dict = defaultdict(int)
    try:
        with open(LOG_FILE) as f:
            for line in f:
                if "ALERT" not in line:
                    continue
                m = _IP_RE.search(line)
                if m:
                    ip_counts[m.group(1)] += 1
    except Exception as e:
        print(f"[NETGUARD] Log scan error: {e}")
        return

    if not ip_counts:
        print("[NETGUARD] Startup scan — 0 IPs found in existing alerts.")
        # Print a sample to verify log format
        try:
            with open(LOG_FILE) as f:
                for line in f:
                    if "ALERT" in line:
                        print(f"[NETGUARD] Sample line: {line.strip()}")
                        break
        except Exception:
            pass
        return

    print(f"[NETGUARD] Startup scan found {len(ip_counts)} IP(s):")
    for ip, count in sorted(ip_counts.items(), key=lambda x: -x[1]):
        alert_counts[ip] = count
        remaining = max(0, ALERT_THRESHOLD - count)
        if count >= ALERT_THRESHOLD:
            if ip not in blocked_ips:
                print(f"  {ip}: {count} alerts -> BLOCKING NOW")
                block_ip(ip, count, "STARTUP_RESCAN")
            else:
                print(f"  {ip}: {count} alerts (already blocked)")
        elif count >= ALERT_THRESHOLD * 0.8:
            # Within 80% of threshold — block immediately, they're clearly an attacker
            print(f"  {ip}: {count} alerts -> BLOCKING NOW (within 80% of threshold)")
            block_ip(ip, count, "STARTUP_RESCAN")
        else:
            print(f"  {ip}: {count} alerts ({remaining} more until block)")


def reset_ip_log(ip: str) -> None:
    """Remove all alert lines for this IP from the log so it starts fresh after unblock."""
    if not os.path.exists(LOG_FILE):
        return
    try:
        with open(LOG_FILE) as f:
            lines = f.readlines()
        # Keep lines that don't mention this IP in an ALERT
        kept = [l for l in lines if not ("ALERT" in l and ip in l)]
        with open(LOG_FILE, "w") as f:
            f.writelines(kept)
        removed = len(lines) - len(kept)
        print(f"[NETGUARD] Cleared {removed} alert lines for {ip} from log.")
    except Exception as e:
        print(f"[NETGUARD] Could not reset log for {ip}: {e}")


# ── Periodic log sync ────────────────────────────────────────
def sync_count_from_log(ip: str) -> int:
    if not os.path.exists(LOG_FILE):
        return 0
    try:
        with open(LOG_FILE) as f:
            return sum(1 for line in f if "ALERT" in line and ip in line)
    except Exception:
        return 0


# ── Helpers ──────────────────────────────────────────────────
def read_mode() -> str:
    try:
        return open("mode.txt").read().strip()
    except FileNotFoundError:
        return "system"


def get_protocol(packet) -> int:
    if packet.haslayer(TCP):  return 1
    if packet.haslayer(UDP):  return 2
    if packet.haslayer(ICMP): return 4   # 4 = ICMP (model trained on this)
    return 3


def is_trusted(ip: str) -> bool:
    return any(ip.startswith(p) for p in TRUSTED_PREFIXES)


def is_lan(ip: str) -> bool:
    return any(ip.startswith(p) for p in LAN_PREFIXES)


def is_loopback(ip: str) -> bool:
    return ip.startswith("127.")


def log_write(tag: str, msg: str) -> None:
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {tag}: {msg}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)
    icon = "🚨" if tag == "ALERT" else ("🚫" if tag == "BLOCKED" else "⚠️")
    print(f"{icon} {line.strip()}")


# ── Block / disconnect ────────────────────────────────────────
def block_ip(ip: str, count: int, threat: str) -> None:
    """Block IP both inbound and outbound via Windows Firewall."""
    if ip in blocked_ips:
        return

    # Never block loopback — would break the entire machine
    if is_loopback(ip):
        print(f"[NETGUARD] Skipping block for loopback {ip}")
        blocked_ips.add(ip)   # still stop counting it
        return

    rule_base = f"NETGUARD_BLOCK_{ip.replace('.', '_')}"
    reason    = f"{threat} — {count} alerts >= threshold {ALERT_THRESHOLD}"
    firewall_ok      = True
    firewall_skipped = False

    for direction, rule_name in [
        ("in",  f"{rule_base}_IN"),
        ("out", f"{rule_base}_OUT"),
    ]:
        cmd = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}",
            f"dir={direction}",
            "action=block",
            f"remoteip={ip}",
            "enable=yes",
            "profile=any",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                firewall_ok = False
                print(f"[NETGUARD] Firewall {direction} rule FAILED for {ip}")
                print(f"           stdout : {result.stdout.strip()}")
                print(f"           stderr : {result.stderr.strip()}")
                print(f"           -> Run as Administrator!")
        except FileNotFoundError:
            firewall_skipped = True
            firewall_ok = False
            break
        except Exception as e:
            firewall_ok = False
            print(f"[NETGUARD] Block error ({direction}): {e}")

    blocked_ips.add(ip)
    try:
        with open(BLOCK_LOG, "a") as f:
            f.write(f"{ip}\n")
    except Exception as e:
        print(f"[NETGUARD] Block log write failed: {e}")

    if firewall_ok:
        log_write("BLOCKED",
                  f"{ip} | {reason} | IN+OUT firewall rules ACTIVE — fully disconnected")
        print(f"\n{'='*56}\n  {ip}  FULLY DISCONNECTED\n  IN + OUT firewall rules added.\n{'='*56}\n")
    elif firewall_skipped:
        log_write("BLOCKED", f"{ip} | {reason} | netsh unavailable")
    else:
        log_write("BLOCKED",
                  f"{ip} | {reason} | FIREWALL FAILED — run as Administrator!")
        print(f"\n{'='*56}\n  WARNING: {ip} marked blocked but firewall DID NOT apply.\n"
              f"  Run terminal as Administrator then restart IDS.\n{'='*56}\n")


# ── Packet processor ─────────────────────────────────────────
def process(packet) -> None:
    global _dbg_counter

    if not packet.haslayer(IP):
        return

    src_ip = packet[IP].src
    dst_ip = packet[IP].dst
    mode   = read_mode()

    # ── Determine which IP to monitor based on mode ───────────
    if mode == "system":
        # System mode: watch traffic TO or FROM this PC
        # Include loopback (127.x) traffic so local simulator is detected
        is_mine = (
            src_ip == local_ip or dst_ip == local_ip
            or src_ip.startswith("127.") or dst_ip.startswith("127.")
        )
        if not is_mine:
            return
        # The "other" side of the connection is the potential attacker
        if src_ip == local_ip or src_ip.startswith("127.0.0.1"):
            other_ip = dst_ip
        else:
            other_ip = src_ip
        # Don't monitor trusted CDNs/cloud IPs
        if is_trusted(other_ip):
            return
        monitored_ip = other_ip

    else:
        # External mode: watch LAN devices (not this PC)
        if src_ip == local_ip:
            return
        if not is_lan(src_ip) and not is_loopback(src_ip):
            return
        monitored_ip = src_ip

    # ── Debug: print first 5 and then every 100 packets ───────
    if DEBUG_MODE:
        _dbg_counter += 1
        if _dbg_counter <= 5 or _dbg_counter % 100 == 0:
            print(
                f"[DBG #{_dbg_counter}] src={src_ip} dst={dst_ip} "
                f"mode={mode} monitored={monitored_ip} "
                f"alerts={alert_counts[monitored_ip]}"
            )

    # ── Skip already-blocked ──────────────────────────────────
    if monitored_ip in blocked_ips:
        return

    # ── Feature extraction ────────────────────────────────────
    now      = time.time()
    packet_times.append(now)
    rate     = sum(1 for t in packet_times if now - t < 2)
    pkt_size = len(packet)
    protocol = get_protocol(packet)

    features = pd.DataFrame(
        [[pkt_size, rate, protocol]],
        columns=["packet_size", "packet_rate", "protocol"]
    )

    # ── Detection ─────────────────────────────────────────────
    try:
        threat = None

        # Fast path: ICMP flood rule (catches Termux ping floods)
        if packet.haslayer(ICMP):
            icmp_times[monitored_ip].append(now)
            icmp_rate = sum(1 for t in icmp_times[monitored_ip] if now - t < 2)
            if icmp_rate >= ICMP_FLOOD_RATE:
                threat = "ICMP_FLOOD"
                log_write("ALERT",
                          f"{threat} ATTACK | Source: {monitored_ip} | "
                          f"ICMP rate: {icmp_rate}/2s | Mode: {mode}")

        # ML path: catches DoS, port scan, slow probe
        if threat is None:
            pred = model.predict(features)[0]
            if pred != "normal":
                threat = pred.upper()
                log_write("ALERT",
                          f"{threat} ATTACK | Source: {monitored_ip} | Mode: {mode}")

        # If neither rule nor ML flagged this packet — skip
        if threat is None:
            return

        # ── Shared alert counting + auto-block for ALL threat types ──
        alert_counts[monitored_ip] += 1
        sync_counter[monitored_ip] += 1

        # Periodic reconcile with log file
        if sync_counter[monitored_ip] >= LOG_SYNC_EVERY:
            sync_counter[monitored_ip] = 0
            log_count = sync_count_from_log(monitored_ip)
            if log_count > alert_counts[monitored_ip]:
                alert_counts[monitored_ip] = log_count

        count = alert_counts[monitored_ip]

        # Milestone prints
        if count in (50, 100, 150, 175, 190, 195, 199) or count % 200 == 0:
            print(
                f"[NETGUARD] {monitored_ip} -> {count} alerts "
                f"({'BLOCKING NOW!' if count >= ALERT_THRESHOLD else f'{ALERT_THRESHOLD - count} until block'})"
            )

        if count == 150:
            log_write("WARNING",
                      f"{monitored_ip} triggered {count} alerts "
                      f"— DISCONNECTING at {ALERT_THRESHOLD}!")

        # ── AUTO-BLOCK ────────────────────────────────────────
        if count >= ALERT_THRESHOLD and monitored_ip not in blocked_ips:
            block_ip(monitored_ip, count, threat)

    except Exception as e:
        print(f"[NETGUARD] Detection error: {e}")


# ── Entry point ───────────────────────────────────────────────
if __name__ == "__main__":
    print_admin_warning()

    print(f"[NETGUARD] Local IP             : {local_ip}")
    print(f"[NETGUARD] Interface            : {IFACE}")
    print(f"[NETGUARD] Auto-block threshold : {ALERT_THRESHOLD} alerts")
    print(f"[NETGUARD] Debug mode           : {'ON' if DEBUG_MODE else 'OFF'}")
    print("[NETGUARD] IDS running — press Ctrl+C to stop\n")

    blocked_ips = load_blocked_ips()
    if blocked_ips:
        print(f"[NETGUARD] Restored {len(blocked_ips)} blocked IP(s): {blocked_ips}\n")

    scan_log_and_preblock()
    print()

    while True:
        try:
            sniff(filter="ip", prn=process, store=0, iface=IFACE)
        except Exception as e:
            print(f"[NETGUARD] Sniff error: {e} — restarting in 2s...")
            time.sleep(2)
            continue
