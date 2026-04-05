#!/usr/bin/env python3
# ============================================================
#  NETGUARD IDS - PDF Report Generator
#  Reads logs/ids.log and builds a formatted PDF report.
#  Run manually: python report_generator.py
# ============================================================
import os
from datetime import datetime
from collections import Counter

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from config import LOG_FILE

OUTPUT_PDF = "ids_report.pdf"


def parse_logs(log_path: str) -> list[dict]:
    """Parse each alert line into a dict."""
    entries = []
    if not os.path.exists(log_path):
        return entries
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Expected format: [YYYY-MM-DD HH:MM:SS] ALERT: <message>
            try:
                ts_part, _, rest = line.partition("] ")
                timestamp = ts_part.lstrip("[")
                level, _, message = rest.partition(": ")
                entries.append({
                    "timestamp": timestamp,
                    "level":     level.strip(),
                    "message":   message.strip(),
                })
            except Exception:
                entries.append({
                    "timestamp": "?",
                    "level":     "UNKNOWN",
                    "message":   line,
                })
    return entries


def build_report(entries: list[dict]) -> None:
    doc    = SimpleDocTemplate(OUTPUT_PDF, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    # ── Title ──────────────────────────────────────────────────
    title_style = ParagraphStyle("Title2", parent=styles["Title"],
                                 fontSize=20, spaceAfter=6)
    story.append(Paragraph("NETGUARD IDS — Security Report", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.5*cm))

    # ── Summary ────────────────────────────────────────────────
    story.append(Paragraph("Summary", styles["Heading2"]))
    total  = len(entries)
    alerts = [e for e in entries if e["level"] == "ALERT"]

    # Count threat types
    threat_counts: Counter = Counter()
    for e in alerts:
        msg = e["message"]
        for keyword in ["DoS Attack", "Port Scan", "Slow Probe",
                         "ML:DOS", "ML:SCAN"]:
            if keyword in msg:
                threat_counts[keyword] += 1
                break
        else:
            threat_counts["Other"] += 1

    summary_data = [
        ["Metric", "Value"],
        ["Total log entries", str(total)],
        ["Total ALERT entries", str(len(alerts))],
    ]
    for threat, count in threat_counts.most_common():
        summary_data.append([f"  — {threat}", str(count)])

    summary_table = Table(summary_data, colWidths=[10*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#f0f0f0"), colors.white]),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Alert log ─────────────────────────────────────────────
    story.append(Paragraph("Alert Log", styles["Heading2"]))

    if not alerts:
        story.append(Paragraph("No alerts recorded.", styles["Normal"]))
    else:
        log_data = [["Timestamp", "Level", "Message"]]
        for e in alerts[-100:]:   # last 100 alerts
            log_data.append([e["timestamp"], e["level"], e["message"]])

        col_widths = [4*cm, 2.5*cm, 10.5*cm]
        log_table  = Table(log_data, colWidths=col_widths, repeatRows=1)
        log_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1),
             [colors.HexColor("#fff3f3"), colors.white]),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.grey),  # Fixed: changed colours.grey to colors.grey
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("WORDWRAP",      (2, 1), (2, -1),  True),
        ]))
        story.append(log_table)

    doc.build(story)
    # Changed Unicode arrow to hyphen
    print(f"Report saved - {OUTPUT_PDF}")


if __name__ == "__main__":
    entries = parse_logs(LOG_FILE)
    print(f"Parsed {len(entries)} log entries")
    build_report(entries)
