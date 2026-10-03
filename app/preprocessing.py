import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd


CATEGORICAL = ["gender", "merch", "cat_id", "one_city", "us_state", "jobs"]
TIME_FEATURES = ["hour", "year", "month", "day_of_month", "day_of_week"]


def number(data, key):
    value = data.get(key)
    if value is None or str(value).strip().lower() in ("", "nan", "none", "null"):
        return math.nan
    value = float(value)
    return value if math.isfinite(value) else math.nan


def distance(data):
    coordinates = [number(data, key) for key in ("lat", "lon", "merchant_lat", "merchant_lon")]
    if not all(math.isfinite(value) for value in coordinates):
        return math.nan
    lat, lon, merchant_lat, merchant_lon = coordinates
    if not (-90 <= lat <= 90 and -90 <= merchant_lat <= 90):
        raise ValueError("Некорректная широта")
    if not (-180 <= lon <= 180 and -180 <= merchant_lon <= 180):
        raise ValueError("Некорректная долгота")
    lat, lon, merchant_lat, merchant_lon = map(math.radians, coordinates)
    a = math.sin((merchant_lat - lat) / 2) ** 2
    a += math.cos(lat) * math.cos(merchant_lat) * math.sin((merchant_lon - lon) / 2) ** 2
    return 6371.009 * 2 * math.asin(math.sqrt(min(1, max(0, a))))


class Preprocessor:
    def __init__(self, path=None):
        path = path or Path(__file__).resolve().parents[1] / "models" / "preprocessing.json"
        self.parameters = json.loads(Path(path).read_text())

    def transform(self, data):
        time = datetime.fromisoformat(str(data["transaction_time"]).replace("Z", "+00:00"))
        features = dict(zip(TIME_FEATURES, map(str, (time.hour, time.year, time.month, time.day, time.weekday()))))
        for column in CATEGORICAL:
            value = str(data.get(column, ""))
            features[column + "_cat"] = self.parameters["categories"][column].get(value, "cat_NAN")
        for column in TIME_FEATURES + [value + "_cat" for value in CATEGORICAL]:
            features[column + "_mean_enc"] = self.parameters["means"][column].get(features[column], math.nan)
        for column, value in {
            "amount": number(data, "amount"),
            "population_city": number(data, "population_city"),
            "distance": distance(data),
        }.items():
            if not math.isfinite(value):
                value = self.parameters["numeric_means"][column]
            if value < 0:
                raise ValueError("Числовые признаки должны быть неотрицательными")
            features[column + "_log"] = math.log1p(value)
        return pd.DataFrame([features], columns=self.parameters["features"])
