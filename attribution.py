"""Module B — Source Attribution.

A multi-output regressor that estimates the fractional contribution of
each pollution source at every station × timestamp.

Sources: traffic, industry, construction, biomass_burning, dust.

Output shares are clipped to [0, 1] and re-normalised to sum to 1.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

from config import ARTIFACTS_DIR, SOURCE_CLASSES
from features import build_attribution_features

MODEL_PATH = ARTIFACTS_DIR / "attribution.joblib"
METRICS_PATH = ARTIFACTS_DIR / "attribution_metrics.json"


@dataclass
class AttributionMetrics:
    per_source_mae: dict
    macro_mae: float
    dominant_source_accuracy: float
    top2_source_accuracy: float


def train(df: pd.DataFrame) -> AttributionMetrics:
    X_full, Y_full = build_attribution_features(df)
    feature_cols = [c for c in X_full.columns if c not in ("timestamp", "station_id")]

    X_full = X_full.sort_values("timestamp").reset_index(drop=True)
    Y_full = Y_full.loc[X_full.index].reset_index(drop=True)
    split = int(0.8 * len(X_full))

    X_tr, X_te = X_full.iloc[:split][feature_cols], X_full.iloc[split:][feature_cols]
    Y_tr, Y_te = Y_full.iloc[:split], Y_full.iloc[split:]

    model = RandomForestRegressor(
        n_estimators=400,
        max_depth=20,
        min_samples_leaf=3,
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_tr, Y_tr)

    Y_pred = model.predict(X_te)
    Y_pred = np.clip(Y_pred, 0, 1)
    row_sum = Y_pred.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1.0
    Y_pred = Y_pred / row_sum

    per_source_mae = {}
    for i, src in enumerate(SOURCE_CLASSES):
        per_source_mae[src] = float(mean_absolute_error(Y_te.iloc[:, i], Y_pred[:, i]))

    Y_te_arr = Y_te.to_numpy()
    dominant_true = Y_te_arr.argmax(axis=1)
    dominant_pred = Y_pred.argmax(axis=1)
    dom_acc = float((dominant_true == dominant_pred).mean())

    # top-2: true dominant is in predicted top-2
    top2_pred = np.argsort(-Y_pred, axis=1)[:, :2]
    top2_acc = float(np.mean([t in row for t, row in zip(dominant_true, top2_pred)]))

    metrics = AttributionMetrics(
        per_source_mae=per_source_mae,
        macro_mae=float(np.mean(list(per_source_mae.values()))),
        dominant_source_accuracy=dom_acc,
        top2_source_accuracy=top2_acc,
    )
    joblib.dump({"model": model, "features": feature_cols}, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(asdict(metrics), indent=2))

    print(f"  attribution macro MAE = {metrics.macro_mae:.3f}")
    print(f"  dominant-source accuracy = {metrics.dominant_source_accuracy:.1%}")
    print(f"  top-2 dominant match     = {metrics.top2_source_accuracy:.1%}")
    return metrics


def load_model():
    bundle = joblib.load(MODEL_PATH)
    return bundle["model"], bundle["features"]


def load_metrics() -> dict:
    if not METRICS_PATH.exists():
        return {}
    return json.loads(METRICS_PATH.read_text())


def attribute(df: pd.DataFrame) -> pd.DataFrame:
    """Predict source shares for every row in df. Returns df + src_pred_* columns."""
    model, feature_cols = load_model()
    X = df[feature_cols].copy()
    Y = model.predict(X)
    Y = np.clip(Y, 0, 1)
    row_sum = Y.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1.0
    Y = Y / row_sum

    out = df.copy()
    for i, src in enumerate(SOURCE_CLASSES):
        out[f"src_pred_{src}"] = Y[:, i]

    dominant_idx = Y.argmax(axis=1)
    out["dominant_source"] = [SOURCE_CLASSES[i] for i in dominant_idx]
    out["dominant_confidence"] = Y.max(axis=1)
    return out


def attribute_latest(df: pd.DataFrame) -> pd.DataFrame:
    """Attribute the most recent row per station."""
    latest = df.sort_values("timestamp").groupby("station_id", as_index=False).tail(1)
    return attribute(latest)
