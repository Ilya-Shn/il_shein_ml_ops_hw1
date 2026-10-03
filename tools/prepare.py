import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier

from app.preprocessing import CATEGORICAL, TIME_FEATURES


parser = argparse.ArgumentParser(description="Подготовка таблиц препроцессинга без обучения модели")
parser.add_argument("train", type=Path)
args = parser.parse_args()
train = pd.read_csv(args.train)
time = pd.to_datetime(train["transaction_time"]).dt
for column, values in zip(TIME_FEATURES, (time.hour, time.year, time.month, time.day, time.dayofweek)):
    train[column] = values
categories = {}
for column in CATEGORICAL:
    counts = train.groupby(column, dropna=False)[["target"]].count().sort_values("target", ascending=False).reset_index().set_axis([column, "count"], axis=1).reset_index()
    counts["index"] = counts.apply(lambda row: np.nan if pd.isna(row[column]) else row["index"], axis=1)
    counts["code"] = ["cat_NAN" if pd.isna(value) else "cat_" + str(value) if value < 50 else "cat_50+" for value in counts["index"]]
    mapping = dict(zip(counts[column], counts["code"]))
    train[column + "_cat"] = train[column].map(mapping).fillna("cat_NAN")
    categories[column] = {str(key): value for key, value in mapping.items() if pd.notna(key)}
means = {}
for column in TIME_FEATURES + [value + "_cat" for value in CATEGORICAL]:
    means[column] = {str(key): float(value) for key, value in train.groupby(column)["target"].mean().items()}
lat, lon, merchant_lat, merchant_lon = (np.radians(train[column]) for column in ("lat", "lon", "merchant_lat", "merchant_lon"))
a = np.sin((merchant_lat - lat) / 2) ** 2 + np.cos(lat) * np.cos(merchant_lat) * np.sin((merchant_lon - lon) / 2) ** 2
train["distance"] = 6371.009 * 2 * np.arcsin(np.sqrt(a.clip(0, 1)))
model = CatBoostClassifier().load_model("models/model.cbm")
parameters = {
    "features": model.feature_names_,
    "categories": categories,
    "means": means,
    "numeric_means": {column: float(train[column].mean()) for column in ("amount", "population_city", "distance")},
    "train_rows": len(train),
}
Path("models/preprocessing.json").write_text(json.dumps(parameters, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n")
print(f"Подготовлены таблицы по {len(train)} строкам")
