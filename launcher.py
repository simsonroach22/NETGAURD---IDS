#!/usr/bin/env python3
# ============================================================
#  NETGUARD IDS — Desktop Launcher
#  Starts Streamlit in background, opens pywebview window
# ============================================================
import os
import sys
import time
import socket
import threading
import subprocess
import webview

# ── Resolve base path (works both in .py and frozen .exe) ────
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS          # PyInstaller temp folder
    APP_DIR  = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR  = BASE_DIR

DASHBOARD = os.path.join(BASE_DIR, "app.py")
PORT      = 8501


# ── Find a free port if 8501 is taken ────────────────────────
def find_free_port(start: int = 8501) -> int:
    for p in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start


# ── Wait until Streamlit is actually serving ─────────────────
def wait_for_server(port: int, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


# ── Start Streamlit as a subprocess ──────────────────────────
def start_streamlit(port: int) -> subprocess.Popen:
    python = sys.executable
    cmd = [
        python, "-m", "streamlit", "run", DASHBOARD,
        "--server.port", str(port),
        "--server.headless", "true",
        "--server.address", "127.0.0.1",
        "--global.developmentMode", "false",
        "--browser.gatherUsageStats", "false",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
    ]
    # Run from APP_DIR so relative paths (logs/, mode.txt) resolve correctly
    return subprocess.Popen(
        cmd,
        cwd=APP_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


# ── Custom JS injected into the webview ──────────────────────
# Hides the Streamlit "Deploy" button and hamburger menu
INJECT_JS = """
(function() {
    function hideChrome() {
        const sel = [
            '[data-testid="stToolbar"]',
            '[data-testid="stDecoration"]',
            '.viewerBadge_container__1QSob',
            '#MainMenu',
        ];
        sel.forEach(s => {
            const el = document.querySelector(s);
            if (el) el.style.display = 'none';
        });
    }
    hideChrome();
    new MutationObserver(hideChrome).observe(document.body, {childList:true, subtree:true});
})();
"""


# ── Main ──────────────────────────────────────────────────────
def main():
    global PORT
    PORT = find_free_port(8501)

    proc = start_streamlit(PORT)

    # Show a loading splash in the webview while Streamlit boots
    loading_html = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@700&family=Share+Tech+Mono&display=swap');
      * { margin:0; padding:0; box-sizing:border-box; }
      body {
        background: #060d1a;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        height: 100vh;
        font-family: 'Rajdhani', sans-serif;
        color: #00c896;
        overflow: hidden;
      }
      .grid {
        position: fixed; inset: 0;
        background-image:
          linear-gradient(rgba(0,200,150,0.06) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,200,150,0.06) 1px, transparent 1px);
        background-size: 40px 40px;
        animation: drift 20s linear infinite;
        pointer-events: none;
      }
      @keyframes drift { to { background-position: 0 40px; } }
      svg { width: 80px; height: 80px; filter: drop-shadow(0 0 12px rgba(0,200,150,0.7)); margin-bottom: 24px; animation: glow 2s ease-in-out infinite; }
      @keyframes glow { 0%,100%{filter:drop-shadow(0 0 8px rgba(0,200,150,0.5));} 50%{filter:drop-shadow(0 0 20px rgba(0,200,150,0.9));} }
      h1 { font-size: 36px; letter-spacing: 8px; color: #fff; margin-bottom: 8px; }
      p  { font-family: 'Share Tech Mono', monospace; font-size: 11px; letter-spacing: 4px; animation: blink 1.5s ease-in-out infinite; }
      @keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0.4;} }
    </style>
    </head>
    <body>
      <div class="grid"></div>
      <svg viewBox="0 0 80 90" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M40 4 L72 16 L72 44 C72 62 56 76 40 84 C24 76 8 62 8 44 L8 16 Z" fill="rgba(0,200,150,0.12)" stroke="#00c896" stroke-width="2"/>
        <path d="M40 18 L58 26 L58 44 C58 55 49 63 40 68 C31 63 22 55 22 44 L22 26 Z" fill="rgba(0,200,150,0.08)" stroke="#00c896" stroke-width="1" stroke-dasharray="3 2"/>
        <path d="M32 44 L38 50 L50 36" stroke="#00c896" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <h1>NETGUARD</h1>
      <p>INITIALIZING SYSTEM...</p>
    </body>
    </html>
    """

    # Create webview window
    window = webview.create_window(
        title="NETGUARD IDS",
        html=loading_html,
        width=1280,
        height=800,
        min_size=(900, 600),
        frameless=False,          # Set True for fully frameless (no title bar)
        easy_resize=True,
        background_color="#060d1a",
    )

    def on_loaded():
        """Switch to Streamlit URL once server is ready."""
        if wait_for_server(PORT, timeout=40):
            window.load_url(f"http://127.0.0.1:{PORT}")
            time.sleep(1.5)
            window.evaluate_js(INJECT_JS)
        else:
            window.load_html("<h2 style='color:red;font-family:monospace;padding:40px'>Failed to start server. Please restart.</h2>")

    thread = threading.Thread(target=on_loaded, daemon=True)

    def start(_):
        thread.start()

    window.events.loaded += start

    try:
        webview.start(debug=False)
    finally:
        # Kill Streamlit when window closes
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
