#!/usr/bin/env python3
# ============================================================
#  NETGUARD IDS - Attack Simulator (for local testing only)
#  Generates realistic DoS and port-scan traffic to localhost
#  so you can verify the IDS detects it.
#  Run in a separate terminal while the IDS is running.
#  Usage: python simulator.py
# ============================================================
import socket
import threading
import random
import time

TARGET = "127.0.0.1"

print(f"[Simulator] Targeting {TARGET}")
print("[Simulator] Running DoS (15 threads) + Port Scan (5 threads)")
print("[Simulator] Press Ctrl+C to stop\n")


# ── DoS flood ─────────────────────────────────────────────────
def dos_flood():
    """Send large bursts of data on port 80 to simulate DoS."""
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((TARGET, 80))
            s.send(b"A" * random.randint(2000, 6000))
            s.close()
        except Exception:
            pass


# ── Port scanner ──────────────────────────────────────────────
def port_scan():
    """Rapidly probe random ports to simulate a port scanner."""
    while True:
        port = random.randint(1, 1024)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.05)
        try:
            s.connect((TARGET, port))
        except Exception:
            pass
        finally:
            s.close()


# ── Slow probe ────────────────────────────────────────────────
def slow_probe():
    """Low-rate probing — crosses PROBE_RATE threshold."""
    while True:
        port = random.randint(1025, 65535)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        try:
            s.connect((TARGET, port))
        except Exception:
            pass
        finally:
            s.close()
        time.sleep(random.uniform(0.02, 0.06))


# ── Launch threads ────────────────────────────────────────────
for _ in range(15):
    threading.Thread(target=dos_flood,  daemon=True).start()

for _ in range(5):
    threading.Thread(target=port_scan,  daemon=True).start()

for _ in range(2):
    threading.Thread(target=slow_probe, daemon=True).start()

print("[Simulator] All threads started. Generating traffic…")

# Keep main thread alive
while True:
    time.sleep(1)
