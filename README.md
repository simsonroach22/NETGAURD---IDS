# NETGUARD — AI Intrusion Detection System

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate training data
```bash
python generate_data.py
```

### 3. Train the model
```bash
python train_model.py
```
This prints a classification report so you can verify accuracy before running live.

### 4. Launch the dashboard
```bash
streamlit run app.py
```
Open http://localhost:8501 in your browser.

### 5. (Optional) Start the REST API in a separate terminal
```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000
```
- GET  http://localhost:8000/alerts  → JSON list of alerts
- GET  http://localhost:8000/status  → IDS health check
- DELETE http://localhost:8000/alerts → clear the log

### 6. (Optional) Test the IDS with simulated attacks
In a third terminal while the IDS is running:
```bash
python simulator.py
```

---

## File Reference

| File | Purpose |
|---|---|
| `config.py` | Central constants — thresholds, paths, trusted IPs |
| `generate_data.py` | Build `ids_dataset.csv` (run once) |
| `train_model.py` | Train + save `ids_model.pkl` (run once) |
| `live_detector.py` | Captures live packets, runs detection, writes alerts |
| `detection_engine.py` | Hybrid ML + rule engine used by `live_detector.py` |
| `threat_rules.py` | Rate-based rule checks |
| `flow_tracker.py` | Tracks per-flow packet/byte counts |
| `app.py` | Streamlit dashboard (start/stop IDS, view alerts) |
| `api_server.py` | FastAPI server exposing alerts as JSON |
| `detector.py` | One-shot test — verify model works before going live |
| `simulator.py` | Generate fake DoS + scan traffic for local testing |
| `report_generator.py` | Build a PDF report from the current log |

---

## How detection works

```
Live packet
    │
    ▼
live_detector.py   ← reads mode.txt (system / external)
    │
    ▼
detection_engine.py
    ├── threat_rules.py  (rate threshold — fires first, fastest)
    └── ids_model.pkl    (Random Forest — catches subtle patterns)
    │
    ▼
logs/ids.log  ←── app.py reads this for the dashboard
              ←── api_server.py serves this as JSON
```

Rules fire first because they're fast and reliable for obvious floods.
The ML model catches patterns that don't cross a rate threshold
(e.g. steady low-rate data exfiltration).

---

## Notes
- `live_detector.py` requires **root / administrator** privileges to capture packets (Scapy needs raw socket access).  
  - Linux/Mac: `sudo python live_detector.py`  
  - Windows: run terminal as Administrator
- The simulator targets `127.0.0.1` — set IDS mode to **System (PC) Traffic** to see those alerts.
