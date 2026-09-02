"""Reusable lead-scoring pipeline matching the Part 3 notebook."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


CSV_PATH = Path(__file__).parent / "leads.csv"
CATEGORICAL_FEATURES = ["source", "city", "area", "property_type"]
NUMERIC_FEATURES = [
    "budget_pkr_lac",
    "bedrooms",
    "agent_experience_years",
    "is_overseas",
    "referred_by_existing_client",
    "has_financing_approved",
    "created_month",
    "created_dayofweek",
    "created_hour",
]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES


def normalize_city(value: str) -> str:
    aliases = {"isb": "islamabad", "rwp": "rawalpindi", "khi": "karachi"}
    normalized = value.strip().lower()
    return aliases.get(normalized, normalized).title()


@lru_cache(maxsize=1)
def train_model() -> Pipeline:
    """Train once per web process, then reuse the fitted baseline."""
    data = pd.read_csv(CSV_PATH, parse_dates=["created_at"])
    data["city"] = data["city"].map(normalize_city)
    data = (
        data.sort_values("created_at")
        .drop_duplicates("crm_record_hash", keep="first")
        .copy()
    )
    data["created_month"] = data["created_at"].dt.month
    data["created_dayofweek"] = data["created_at"].dt.dayofweek
    data["created_hour"] = data["created_at"].dt.hour

    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    preprocessing = ColumnTransformer(
        [
            ("categorical", categorical, CATEGORICAL_FEATURES),
            ("numeric", numeric, NUMERIC_FEATURES),
        ]
    )
    model = Pipeline(
        [
            ("preprocessor", preprocessing),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000, class_weight="balanced", random_state=42
                ),
            ),
        ]
    )
    # Match the notebook: train on the oldest 80%; the newest 20% remains the
    # honest evaluation set and is not used to fit the web scorer.
    training_rows = data.iloc[: int(len(data) * 0.80)]
    model.fit(training_rows[FEATURES], training_rows["converted"])
    return model


def score_lead(values: dict[str, object]) -> float:
    row = dict(values)
    row["city"] = normalize_city(str(row["city"]))
    now = pd.Timestamp.now()
    row.update(
        created_month=now.month,
        created_dayofweek=now.dayofweek,
        created_hour=now.hour,
    )
    frame = pd.DataFrame([row], columns=FEATURES)
    return float(train_model().predict_proba(frame)[0, 1])

