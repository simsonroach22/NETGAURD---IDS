#!/usr/bin/env python3
"""
NETGUARD DEBUG TOOL
Run this INSTEAD of live_detector.py while pinging from your phone.
It will print exactly what it sees so you can pinpoint the problem.

Usage:
    python debug_ids.py

Then from Termux on your phone:
    ping <your-PC-IP> -c 50
"""
import socket
import time
from collections import deque, defaultdict
from scapy.all import sniff, IP, ICMP, TCP, UDP, get_if_list, conf

# ── Step 1: show what scapy thinks about your machine ─────────
print("=" * 60)
print("STEP 1 — Network info")
print("=" * 60)

# Old (buggy) method
old_ip = socket.gethostbyname(socket.gethostname())
print(f"  gethostbyname method (OLD, likely wrong): {old_ip}")

# New (correct) method
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    real_ip = s.getsockname()[0]
    s.close()
except Exception:
    real_ip = "FAILED"
print(f"  UDP trick method     (NEW, correct):      {real_ip}")
print(f"  Scapy default iface: {conf.iface}")

print()
print("=" * 60)
print("STEP 2 — All available interfaces")
print("=" * 60)
for i, iface in enumerate(get_if_list()):
    print(f"  [{i}] {iface}")

print()
print("=" * 60)
print("STEP 3 — Sniffing ALL interfaces for 15 seconds")
print(f"         >>> NOW PING THIS PC FROM YOUR PHONE: ping {real_ip} <<<")
print("=" * 60)

seen_ips = set()
icmp_counts = defaultdict(int)
all_counts  = defaultdict(int)

def probe(pkt):
    if not pkt.haslayer(IP):
        return
    src = pkt[IP].src
    dst = pkt[IP].dst
    proto = "ICMP" if pkt.haslayer(ICMP) else \
            "TCP"  if pkt.haslayer(TCP)  else \
            "UDP"  if pkt.haslayer(UDP)  else "OTHER"

    all_counts[src] += 1

    if pkt.haslayer(ICMP):
        icmp_counts[src] += 1
        if src not in seen_ips:
            print(f"  ✅ ICMP packet from {src} → {dst}  (first seen)")
            seen_ips.add(src)
        elif icmp_counts[src] % 10 == 0:
            print(f"  📦 ICMP from {src}: {icmp_counts[src]} packets so far")
    else:
        if src not in seen_ips and src != real_ip and src != old_ip:
            print(f"  📡 {proto} from {src} → {dst}")
            seen_ips.add(src)

sniff(prn=probe, store=0, timeout=15)

print()
print("=" * 60)
print("STEP 4 — Results")
print("=" * 60)

if not icmp_counts:
    print("  ❌ NO ICMP packets captured at all!")
    print()
    print("  Possible causes:")
    print("  1. Windows Firewall is BLOCKING ICMP inbound on your PC.")
    print("     Fix: Run this in Admin PowerShell:")
    print('     netsh advfirewall firewall add rule name="Allow ICMP" protocol=icmpv4:8,any dir=in action=allow')
    print()
    print("  2. Your phone is not on the same Wi-Fi network as this PC.")
    print(f"     Your PC LAN IP: {real_ip}")
    print("     Check your phone IP — it should start with the same subnet.")
    print()
    print("  3. Scapy is not capturing on the right interface.")
    print("     Try running: python debug_ids.py --iface <name>")
    print("     with each interface name from STEP 2 above.")
else:
    print(f"  ✅ ICMP packets captured from: {list(icmp_counts.keys())}")
    for ip, count in icmp_counts.items():
        print(f"     {ip}: {count} ICMP packets")
    print()
    print("  ✅ Scapy CAN see your phone's pings.")
    print("  The problem is in live_detector.py filtering them out.")
    print()
    print("  Likely cause: local_ip is wrong.")
    print(f"     OLD local_ip (gethostbyname): {old_ip}")
    print(f"     NEW local_ip (correct):       {real_ip}")
    if old_ip != real_ip:
        print(f"  ❌ CONFIRMED — local_ip was {old_ip} instead of {real_ip}")
        print("     The 'monitored_ip' logic was picking the WRONG IP to monitor.")

print()
print("=" * 60)
print("STEP 5 — ICMP flood simulation (2 seconds)")
print("=" * 60)
print("  Checking if ICMP rate threshold would trigger...")

icmp_window = deque(maxlen=200)
flood_triggered = False

def flood_check(pkt):
    global flood_triggered
    if pkt.haslayer(ICMP) and pkt.haslayer(IP):
        now = time.time()
        icmp_window.append(now)
        rate = sum(1 for t in icmp_window if now - t < 2)
        if rate >= 10 and not flood_triggered:
            print(f"  🚨 ICMP_FLOOD would trigger! Rate={rate}/2s from {pkt[IP].src}")
            flood_triggered = True

print(f"  >>> Ping fast from phone now: ping {real_ip} -i 0.2 <<<")
sniff(prn=flood_check, store=0, timeout=10)

if not flood_triggered:
    print("  ⚠️  ICMP flood threshold NOT reached in 10 seconds.")
    print("     Either no packets arrived, or ping rate is too slow.")
    print("     From Termux try: ping <PC-IP> -i 0.01 -c 200")
