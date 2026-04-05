#!/usr/bin/env python3
# ============================================================
#  NETGUARD IDS - Streamlit Dashboard (FINAL VERSION)
#  - Uses sys.executable so python version never mismatches
#  - Shows blocked IPs with Unblock button
#  - Threat breakdown, live log, PDF report
# ============================================================
import os
import sys
import time
import subprocess
from datetime import datetime
from collections import Counter

import psutil
import streamlit as st

LOG_FILE  = "logs/ids.log"
BLOCK_LOG = "logs/blocked_ips.log"

st.set_page_config(page_title="NETGUARD IDS", page_icon="🛡", layout="wide")
st.title("🛡 NETGUARD — AI Intrusion Detection System")
st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")


# ── Helpers ───────────────────────────────────────────────────
def read_log() -> list:
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE) as f:
        return [l.strip() for l in f if l.strip()]


def read_blocked_ips() -> list:
    if not os.path.exists(BLOCK_LOG):
        return []
    with open(BLOCK_LOG) as f:
        ips = list(set(l.strip() for l in f if l.strip()))
    return ips


def read_mode() -> str:
    try:
        return open("mode.txt").read().strip()
    except FileNotFoundError:
        return "system"


def write_mode(mode: str) -> None:
    with open("mode.txt", "w") as f:
        f.write(mode)


def ids_running():
    return os.path.exists("ids.pid")



def unblock_ip_action(ip: str) -> bool:
    """Remove Windows Firewall block rules (_IN and _OUT) and remove from block log."""
    rule_base = f"NETGUARD_BLOCK_{ip.replace('.', '_')}"
    # Delete all variants — _IN, _OUT, and legacy rules without suffix
    for rule_name in [f"{rule_base}_IN", f"{rule_base}_OUT", rule_base]:
        try:
            subprocess.run(
                ["netsh", "advfirewall", "firewall",
                 "delete", "rule", f"name={rule_name}"],
                capture_output=True, text=True
            )
        except Exception as e:
            st.warning(f"Firewall unblock warning: {e}")

    # Remove from BLOCK_LOG
    if os.path.exists(BLOCK_LOG):
        try:
            lines = open(BLOCK_LOG).readlines()
            with open(BLOCK_LOG, "w") as f:
                for l in lines:
                    if l.strip() != ip:
                        f.write(l)
        except Exception:
            pass

    # Write unblock event to main log
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{ts}] UNBLOCKED: {ip} | Firewall rule removed by user\n")
    except Exception:
        pass

    return True


# ── Data ──────────────────────────────────────────────────────
logs        = read_log()
alert_lines = [l for l in logs if "ALERT" in l]
blocked_ips = read_blocked_ips()
running     = ids_running()
mode        = read_mode()

# Build threat counter
threat_counts: Counter = Counter()
for line in alert_lines:
    ul = line.upper()
    if "DOS" in ul or "FLOOD" in ul:
        threat_counts["DoS Attack"] += 1
    elif "SCAN" in ul:
        threat_counts["Scan Attack"] += 1
    elif "PROBE" in ul:
        threat_counts["Slow Probe"] += 1

# Per-IP alert count (for blocked panel)
ip_alert_counts: Counter = Counter()
for line in alert_lines:
    for ip in blocked_ips:
        if ip in line:
            ip_alert_counts[ip] += 1


# ── Section 1: System Status ──────────────────────────────────
st.subheader("System Status")
c1, c2, c3, c4 = st.columns(4)

with c1:
    if running:
        st.success("🟢 IDS Status: RUNNING")
    else:
        st.error("🔴 IDS Status: STOPPED")

with c2:
    label = "🖥 PC Traffic" if mode == "system" else "📱 External Devices"
    st.info(f"Monitoring: {label}")

with c3:
    st.metric("Total Alerts", len(alert_lines))

with c4:
    if blocked_ips:
        st.error(f"🚫 Blocked IPs: {len(blocked_ips)}")
    else:
        st.metric("Blocked IPs", 0)

st.divider()


# ── Section 2: IDS Control ────────────────────────────────────
st.subheader("IDS Control")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶ Start IDS", use_container_width=True):
        if not running:
            proc = subprocess.Popen(
                [sys.executable, "live_detector.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            with open("ids.pid", "w") as f:
                f.write(str(proc.pid))
            st.success(f"IDS started (PID {proc.pid})")
            time.sleep(0.5)
            st.rerun()
        else:
            st.warning("IDS is already running")

with col2:
    if st.button("⏹ Stop IDS", use_container_width=True):
        if running:
            try:
                pid = int(open("ids.pid").read())
                psutil.Process(pid).kill()
            except Exception:
                pass
            finally:
                if os.path.exists("ids.pid"):
                    os.remove("ids.pid")
            st.success("IDS stopped")
            time.sleep(0.5)
            st.rerun()
        else:
            st.warning("IDS is not running")

with col3:
    if st.button("🧹 Clear Logs", use_container_width=True):
        if os.path.exists(LOG_FILE):
            open(LOG_FILE, "w").close()
        st.success("Logs cleared")
        time.sleep(0.3)
        st.rerun()

st.divider()


# ── Section 3: Traffic Mode ───────────────────────────────────
st.subheader("Traffic Monitoring Mode")
col4, col5 = st.columns(2)

with col4:
    if st.button("🖥 Monitor System (PC) Traffic", use_container_width=True):
        write_mode("system")
        st.success("Switched to System traffic monitoring")
        time.sleep(0.3)
        st.rerun()

with col5:
    if st.button("📱 Monitor External Devices (LAN)", use_container_width=True):
        write_mode("external")
        st.success("Switched to External device monitoring")
        time.sleep(0.3)
        st.rerun()

st.divider()


# ── Section 4: Threat Breakdown ───────────────────────────────
if threat_counts:
    st.subheader("⚡ Threat Breakdown")
    tcols = st.columns(len(threat_counts))
    for i, (threat, count) in enumerate(threat_counts.most_common()):
        with tcols[i]:
            st.metric(threat, count)
    st.divider()


# ── Section 5: Auto-Blocked Attackers ────────────────────────
st.subheader("🚫 Auto-Blocked Attackers")

if not blocked_ips:
    st.info(
        f"No IPs blocked yet. Any IP that triggers "
        f"200+ alerts will be automatically blocked via Windows Firewall."
    )
else:
    st.error(f"⛔ {len(blocked_ips)} IP(s) currently blocked by Windows Firewall!")

    for ip in blocked_ips:
        col_ip, col_count, col_btn = st.columns([3, 2, 1])

        with col_ip:
            st.markdown(f"🔴 **{ip}**")

        with col_count:
            count = ip_alert_counts.get(ip, 0)
            st.markdown(f"**{count}** alerts triggered")

        with col_btn:
            if st.button(f"✅ Unblock", key=f"unblock_{ip}"):
                if unblock_ip_action(ip):
                    st.success(f"✅ {ip} unblocked!")
                    time.sleep(0.5)
                    st.rerun()

    st.caption(
        "💡 Click Unblock to remove the firewall rule and allow "
        "the device back on the network."
    )

st.divider()


# ── Section 6: Live Alert Log ─────────────────────────────────
st.subheader("🚨 Live Threat Alerts")

if not logs:
    st.info("No alerts yet. Start the IDS — detections will appear here.")
else:
    display = logs[-200:][::-1]
    st.text_area("IDS Logs (newest first)", "\n".join(display), height=400)
    if alert_lines:
        st.warning(f"⚠ Last alert: {alert_lines[-1]}")

st.divider()


# ── Section 7: PDF Report ─────────────────────────────────────
st.subheader("📄 Report")

if st.button("Generate PDF Report"):
    with st.spinner("Building report…"):
        result = subprocess.run(
            [sys.executable, "report_generator.py"],
            capture_output=True, text=True
        )
    if result.returncode == 0:
        st.success("Report saved → ids_report.pdf")
    else:
        st.error(f"Report generation failed:\n{result.stderr}")


# ── Auto-refresh while IDS is running ────────────────────────
if running:
    time.sleep(3)
    st.rerun()
