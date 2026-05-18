#!/usr/bin/env python3
# ============================================================
#  NETGUARD IDS - Streamlit Dashboard with Animated Splash
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

st.set_page_config(
    page_title="NETGUARD IDS",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Splash + transition CSS/HTML ──────────────────────────────
SPLASH_HTML = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Share+Tech+Mono&display=swap');

/* Hide Streamlit chrome on splash */
[data-testid="stToolbar"],
[data-testid="stSidebarNav"],
footer { visibility: hidden; }

.ng-splash-root {
    position: fixed;
    inset: 0;
    background: #060d1a;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    font-family: 'Rajdhani', sans-serif;
    overflow: hidden;
}

/* Grid background */
.ng-grid {
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(0,200,150,0.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,200,150,0.07) 1px, transparent 1px);
    background-size: 40px 40px;
    animation: gridDrift 20s linear infinite;
}
@keyframes gridDrift {
    from { transform: translateY(0); }
    to   { transform: translateY(40px); }
}

/* Scanning line */
.ng-scanline {
    position: absolute; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(0,255,160,0.5), transparent);
    animation: scan 4s linear infinite;
    pointer-events: none;
}
@keyframes scan { from { top: -2px; } to { top: 100%; } }

/* Corner brackets */
.ng-corner { position: absolute; width: 32px; height: 32px; border-color: #00c896; border-style: solid; }
.ng-tl { top: 24px; left: 24px; border-width: 2px 0 0 2px; }
.ng-tr { top: 24px; right: 24px; border-width: 2px 2px 0 0; }
.ng-bl { bottom: 24px; left: 24px; border-width: 0 0 2px 2px; }
.ng-br { bottom: 24px; right: 24px; border-width: 0 2px 2px 0; }

/* Content stack */
.ng-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0;
    position: relative;
    z-index: 2;
    animation: fadeInUp 0.8s ease both;
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(24px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Shield */
.ng-shield-wrap {
    position: relative;
    width: 140px; height: 140px;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 24px;
}
.ng-ring {
    position: absolute;
    border: 1px solid rgba(0,200,150,0.3);
    border-radius: 50%;
    animation: ringPulse 2.5s ease-in-out infinite;
}
.ng-ring-1 { inset: 0; }
.ng-ring-2 { inset: 14px; animation-delay: 0.5s; }
.ng-ring-3 { inset: 28px; animation-delay: 1s; }
@keyframes ringPulse {
    0%,100% { opacity: 0.3; transform: scale(1); }
    50%      { opacity: 1;   transform: scale(1.05); }
}
.ng-shield-svg {
    width: 80px; height: 80px;
    filter: drop-shadow(0 0 14px rgba(0,200,150,0.7));
    animation: shieldGlow 3s ease-in-out infinite;
}
@keyframes shieldGlow {
    0%,100% { filter: drop-shadow(0 0 10px rgba(0,200,150,0.5)); }
    50%      { filter: drop-shadow(0 0 22px rgba(0,200,150,0.9)); }
}

/* Logo */
.ng-wordmark {
    font-size: 44px;
    font-weight: 700;
    letter-spacing: 8px;
    color: #ffffff;
    text-shadow: 0 0 24px rgba(0,200,150,0.5);
    margin-bottom: 6px;
    line-height: 1;
}
.ng-tagline {
    font-family: 'Share Tech Mono', monospace;
    font-size: 11px;
    letter-spacing: 5px;
    color: #00c896;
    margin-bottom: 36px;
    animation: blink 3s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0.6;} }

/* Status readout */
.ng-status {
    font-family: 'Share Tech Mono', monospace;
    font-size: 11px;
    letter-spacing: 2px;
    color: rgba(0,200,150,0.65);
    margin-bottom: 32px;
    height: 18px;
}

/* CTA button */
.ng-enter-btn {
    background: transparent;
    border: 1px solid #00c896;
    color: #00c896;
    font-family: 'Rajdhani', sans-serif;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 5px;
    padding: 16px 56px;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: color 0.35s ease;
    outline: none;
}
.ng-enter-btn::before {
    content: '';
    position: absolute;
    inset: 0;
    background: #00c896;
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.35s cubic-bezier(0.4,0,0.2,1);
}
.ng-enter-btn:hover::before { transform: scaleX(1); }
.ng-enter-btn:hover { color: #060d1a; }
.ng-enter-btn span { position: relative; z-index: 1; }

/* Transition overlay */
.ng-transition-overlay {
    position: fixed;
    inset: 0;
    background: #060d1a;
    z-index: 10000;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.5s ease;
}
.ng-transition-overlay.active {
    opacity: 1;
    pointer-events: all;
}
.ng-transition-overlay .ng-flash {
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 50% 50%, rgba(0,200,150,0.3), transparent 70%);
    animation: flashPulse 0.5s ease-out forwards;
}
@keyframes flashPulse {
    from { opacity: 1; transform: scale(0.5); }
    to   { opacity: 0; transform: scale(2); }
}
</style>

<div class="ng-splash-root" id="ngSplash">
    <div class="ng-grid"></div>
    <div class="ng-scanline"></div>
    <div class="ng-corner ng-tl"></div>
    <div class="ng-corner ng-tr"></div>
    <div class="ng-corner ng-bl"></div>
    <div class="ng-corner ng-br"></div>

    <div class="ng-content">
        <div class="ng-shield-wrap">
            <div class="ng-ring ng-ring-1"></div>
            <div class="ng-ring ng-ring-2"></div>
            <div class="ng-ring ng-ring-3"></div>
            <svg class="ng-shield-svg" viewBox="0 0 80 90" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M40 4 L72 16 L72 44 C72 62 56 76 40 84 C24 76 8 62 8 44 L8 16 Z"
                    fill="rgba(0,200,150,0.12)" stroke="#00c896" stroke-width="2"/>
                <path d="M40 18 L58 26 L58 44 C58 55 49 63 40 68 C31 63 22 55 22 44 L22 26 Z"
                    fill="rgba(0,200,150,0.08)" stroke="#00c896" stroke-width="1" stroke-dasharray="3 2"/>
                <path d="M32 44 L38 50 L50 36"
                    stroke="#00c896" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>

        <div class="ng-wordmark">NETGUARD</div>
        <div class="ng-tagline">AI INTRUSION DETECTION SYSTEM</div>
        <div class="ng-status" id="ngStatusText">INITIALIZING THREAT ENGINE...</div>

        <button class="ng-enter-btn" id="ngEnterBtn">
            <span>ENTER DASHBOARD</span>
        </button>
    </div>
</div>

<div class="ng-transition-overlay" id="ngOverlay">
    <div class="ng-flash"></div>
</div>

<script>
(function() {
    /* Cycle status messages */
    const msgs = [
        "INITIALIZING THREAT ENGINE...",
        "LOADING PACKET INSPECTOR...",
        "ARMING FIREWALL HOOKS...",
        "SCANNING LOCAL INTERFACES...",
        "ALL SYSTEMS NOMINAL."
    ];
    const el = document.getElementById('ngStatusText');
    if (!el) return;
    el.style.transition = 'opacity 0.3s ease';
    let i = 0;
    const timer = setInterval(() => {
        i++;
        if (i < msgs.length) {
            el.style.opacity = 0;
            setTimeout(() => { el.textContent = msgs[i]; el.style.opacity = 1; }, 320);
        } else {
            clearInterval(timer);
        }
    }, 900);

    /* Button click → overlay flash → hide splash */
    const btn = document.getElementById('ngEnterBtn');
    const overlay = document.getElementById('ngOverlay');
    const splash = document.getElementById('ngSplash');
    if (!btn || !overlay || !splash) return;

    btn.addEventListener('click', () => {
        overlay.classList.add('active');
        setTimeout(() => {
            splash.style.transition = 'opacity 0.4s ease';
            splash.style.opacity = '0';
            splash.style.pointerEvents = 'none';
            overlay.style.transition = 'opacity 0.4s ease';
            overlay.style.opacity = '0';
            setTimeout(() => {
                splash.style.display = 'none';
                overlay.style.display = 'none';
                /* Click the hidden Streamlit button in the parent frame */
                try {
                    const stButtons = window.parent.document.querySelectorAll('button');
                    for (const b of stButtons) {
                        if (b.innerText && b.innerText.includes('ENTER DASHBOARD')) {
                            b.click();
                            break;
                        }
                    }
                } catch(e) {
                    /* fallback: reload forces Streamlit to re-evaluate state */
                    window.parent.location.reload();
                }
            }, 420);
        }, 380);
    });
})();
</script>
"""

# ── Session state ──────────────────────────────────────────────
if "splash_done" not in st.session_state:
    st.session_state.splash_done = False

# ── Splash page ────────────────────────────────────────────────
if not st.session_state.splash_done:
    st.components.v1.html(SPLASH_HTML, height=800, scrolling=False)

    # Streamlit-side "Enter" button (hidden below the HTML overlay;
    # acts as the native trigger when JS message can't reach Streamlit)
    st.markdown(
        """
        <style>
        /* Completely hide the native Streamlit button — JS will click it */
        div[data-testid="stButton"][id="splash_enter_container"],
        div[data-testid="stButton"] > button[kind="secondary"] {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            padding: 0 !important;
            margin: -1px !important;
            overflow: hidden !important;
            clip: rect(0,0,0,0) !important;
            white-space: nowrap !important;
            border: 0 !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.button("▶ ENTER DASHBOARD", key="splash_enter", use_container_width=True):
        st.session_state.splash_done = True
        st.rerun()
    st.stop()


# ══════════════════════════════════════════════════════════════
#  MAIN DASHBOARD (shown after splash)
# ══════════════════════════════════════════════════════════════

# Fade-in animation for main content
st.markdown(
    """
    <style>
    @keyframes dashFadeIn {
        from { opacity: 0; transform: translateY(16px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    section.main > div { animation: dashFadeIn 0.6s ease both; }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    rule_base = f"NETGUARD_BLOCK_{ip.replace('.', '_')}"
    for rule_name in [f"{rule_base}_IN", f"{rule_base}_OUT", rule_base]:
        try:
            subprocess.run(
                ["netsh", "advfirewall", "firewall",
                 "delete", "rule", f"name={rule_name}"],
                capture_output=True, text=True
            )
        except Exception as e:
            st.warning(f"Firewall unblock warning: {e}")

    if os.path.exists(BLOCK_LOG):
        try:
            lines = open(BLOCK_LOG).readlines()
            with open(BLOCK_LOG, "w") as f:
                for l in lines:
                    if l.strip() != ip:
                        f.write(l)
        except Exception:
            pass

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

threat_counts: Counter = Counter()
for line in alert_lines:
    ul = line.upper()
    if "DOS" in ul or "FLOOD" in ul:
        threat_counts["DoS Attack"] += 1
    elif "SCAN" in ul:
        threat_counts["Scan Attack"] += 1
    elif "PROBE" in ul:
        threat_counts["Slow Probe"] += 1

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
        "No IPs blocked yet. Any IP that triggers "
        "200+ alerts will be automatically blocked via Windows Firewall."
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
