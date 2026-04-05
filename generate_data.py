#!/usr/bin/env python3
import random
import pandas as pd
from config import DATASET_PATH

random.seed(42)

SAMPLES_PER_CLASS = 3000

def gen_sample(label):
    if label == "normal":
        size_type = random.random()
        if size_type < 0.4:
            pkt_size = random.randint(40, 300)
            rate     = random.randint(1, 30)
        elif size_type < 0.8:
            pkt_size = random.randint(300, 1200)
            rate     = random.randint(1, 50)
        else:
            pkt_size = random.randint(1200, 5000)
            rate     = random.randint(1, 60)
        return [pkt_size, rate, random.randint(1, 3)]

    elif label == "dos":
        return [
            random.randint(1200, 5000),
            random.randint(100, 300),
            random.randint(1, 3),
        ]

    elif label == "scan":
        return [
            random.randint(40, 200),
            random.randint(40, 100),
            random.randint(1, 3),
        ]

    elif label == "icmp_flood":
        return [
            random.randint(74, 120),
            random.randint(10, 80),
            4,
        ]

    else:
        raise ValueError(f"Unknown label: {label}")


# Generate dataset
rows = []
for label in ["normal", "dos", "scan", "icmp_flood"]:
    for _ in range(SAMPLES_PER_CLASS):
        rows.append(gen_sample(label) + [label])

df = pd.DataFrame(rows, columns=["packet_size", "packet_rate", "protocol", "label"])
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

df.to_csv(DATASET_PATH, index=False)

print(f"Dataset generated → {DATASET_PATH} ({len(df)} rows)")
print(df["label"].value_counts())
