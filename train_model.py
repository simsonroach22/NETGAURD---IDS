#!/usr/bin/env python3
# ============================================================
#  NETGUARD IDS - Model Trainer
#  Run this once to build ids_model.pkl from ids_dataset.csv
# ============================================================
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from config import DATASET_PATH, MODEL_PATH

# ── Load data ────────────────────────────────────────────────
df = pd.read_csv(DATASET_PATH)
print(f"Loaded {len(df)} rows from {DATASET_PATH}")

X = df[["packet_size", "packet_rate", "protocol"]]
y = df["label"]

# ── Train / test split ────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── Train model ───────────────────────────────────────────────
model = RandomForestClassifier(
    n_estimators=150,
    max_depth=None,
    min_samples_split=4,
    random_state=42,
    n_jobs=-1,
)
model.fit(X_train, y_train)

# ── Evaluate ──────────────────────────────────────────────────
y_pred = model.predict(X_test)
print("\n=== Classification Report ===")
print(classification_report(y_test, y_pred))

# ── Save ──────────────────────────────────────────────────────
joblib.dump(model, MODEL_PATH)
print(f"Model saved → {MODEL_PATH}")
