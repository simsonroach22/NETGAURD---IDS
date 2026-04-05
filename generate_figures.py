import pandas as pd
import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import ConfusionMatrixDisplay

# Load dataset
data = pd.read_csv("dataset/custom_ids_data.csv")

# Load encoders used during training
protocol_encoder = joblib.load("protocol_encoder.pkl")
flag_encoder = joblib.load("encoder.pkl")

# Encode categorical features
if "protocol" in data.columns:
    data["protocol"] = protocol_encoder.transform(data["protocol"])

if "flag" in data.columns:
    data["flag"] = flag_encoder.transform(data["flag"])

# Ensure label exists
y = data["label"]
X = data.drop("label", axis=1)

# Load trained model
model = joblib.load("ids_model.pkl")

# Predict
y_pred = model.predict(X)

# Confusion Matrix
ConfusionMatrixDisplay.from_predictions(y, y_pred)
plt.title("Confusion Matrix")
plt.savefig("confusion_matrix.png")
plt.clf()

# Feature importance
importances = model.feature_importances_
plt.bar(range(len(importances)), importances)
plt.title("Random Forest Feature Importance")
plt.xlabel("Feature Index")
plt.ylabel("Importance")
plt.savefig("feature_importance.png")

print("Figures generated successfully.")
