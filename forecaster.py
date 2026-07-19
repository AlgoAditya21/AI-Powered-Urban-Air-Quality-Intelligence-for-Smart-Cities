"""Module A — Hyperlocal AQI Forecaster.

Trains gradient-boosted regressors for multiple horizons (1h, 24h, 48h, 72h).
Reports RMSE + MAE against a persistence baseline (y_pred = y_now).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from config import ARTIFACTS_DIR
from features import build_forecast_features

HORIZONS = [1, 24, 48, 72]

MODEL_PATH = ARTIFACTS_DIR / "forecaster.joblib"
METRICS_PATH = ARTIFACTS_DIR / "forecaster_metrics.json"


@dataclass
class HorizonMetrics:
    horizon_h: int
    baseline_rmse: float
    baseline_mae: float
    model_rmse: float
    model_mae: float
    rmse_improvement_pct: float


def _train_one_horizon(df: pd.DataFrame, horizon_h: int) -> tuple[HistGradientBoostingRegressor, HorizonMetrics, list[str]]:
    X, y = build_forecast_features(df, horizon_h=horizon_h)

    # chronological split: last 20% is test
    X = X.sort_values("timestamp").reset_index(drop=True)
    y = y.loc[X.index]
    split = int(0.8 * len(X))
    train_idx, test_idx = X.index[:split], X.index[split:]

    feature_cols = [c for c in X.columns if c not in ("timestamp", "station_id", "persistence")]

    model = HistGradientBoostingRegressor(
        max_iter=400,
        max_depth=8,
        learning_rate=0.05,
        min_samples_leaf=20,
        random_state=42,
    )
    model.fit(X.loc[train_idx, feature_cols], y.loc[train_idx])

    y_test = y.loc[test_idx].to_numpy()
    y_pred = model.predict(X.loc[test_idx, feature_cols])
    y_persist = X.loc[test_idx, "persistence"].to_numpy()

    b_rmse = float(np.sqrt(mean_squared_error(y_test, y_persist)))
    b_mae  = float(mean_absolute_error(y_test, y_persist))
    m_rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    m_mae  = float(mean_absolute_error(y_test, y_pred))

    metrics = HorizonMetrics(
        horizon_h=horizon_h,
        baseline_rmse=b_rmse,
        baseline_mae=b_mae,
        model_rmse=m_rmse,
        model_mae=m_mae,
        rmse_improvement_pct=100.0 * (b_rmse - m_rmse) / b_rmse if b_rmse > 0 else 0.0,
    )
    return model, metrics, feature_cols


def train_all(df: pd.DataFrame) -> dict[int, dict]:
    """Train one model per horizon. Return a metrics summary."""
    models: dict[int, HistGradientBoostingRegressor] = {}
    all_metrics: dict[int, dict] = {}
    feature_cols_map: dict[int, list[str]] = {}

    for h in HORIZONS:
        model, metrics, feat_cols = _train_one_horizon(df, h)
        models[h] = model
        all_metrics[h] = asdict(metrics)
        feature_cols_map[h] = feat_cols
        print(
            f"  horizon={h:>2}h | baseline RMSE={metrics.baseline_rmse:6.2f} "
            f"| model RMSE={metrics.model_rmse:6.2f} "
            f"| improvement={metrics.rmse_improvement_pct:5.1f}%"
        )

    joblib.dump({"models": models, "features": feature_cols_map}, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(all_metrics, indent=2))
    return all_metrics


# --------------------------------------------------------------------------- #
# Inference                                                                   #
# --------------------------------------------------------------------------- #

def load_models() -> tuple[dict[int, HistGradientBoostingRegressor], dict[int, list[str]]]:
    bundle = joblib.load(MODEL_PATH)
    return bundle["models"], bundle["features"]


def load_metrics() -> dict:
    if not METRICS_PATH.exists():
        return {}
    return json.loads(METRICS_PATH.read_text())


def forecast_station(df: pd.DataFrame, station_id: str) -> pd.DataFrame:
    """Return a small dataframe of horizon → predicted PM2.5 for the latest row of a station.

    Falls back gracefully if models aren't trained yet.
    """
    models, feat_map = load_models()
    st_df = df[df["station_id"] == station_id].sort_values("timestamp")
    if st_df.empty:
        return pd.DataFrame()

    out_rows = []
    for h, model in models.items():
        X, _ = build_forecast_features(st_df, horizon_h=h)
        if X.empty:
            continue
        last = X.iloc[[-1]]
        cols = feat_map[h]
        pred = float(model.predict(last[cols])[0])
        ts = last["timestamp"].iloc[0] + pd.Timedelta(hours=h)
        out_rows.append({"horizon_h": h, "forecast_timestamp": ts, "pm25_forecast": pred})
    return pd.DataFrame(out_rows)


def forecast_all_stations_next_24h(df: pd.DataFrame) -> pd.DataFrame:
    """Predict PM2.5 in +24h for every station's latest observation."""
    models, feat_map = load_models()
    if 24 not in models:
        return pd.DataFrame()
    model = models[24]
    cols = feat_map[24]

    X, _ = build_forecast_features(df, horizon_h=24)
    if X.empty:
        return pd.DataFrame()
    latest = (
        X.sort_values("timestamp")
         .groupby("station_id", as_index=False)
         .tail(1)
    )
    preds = model.predict(latest[cols])
    latest = latest.copy()
    latest["pm25_forecast_24h"] = preds
    return latest[["station_id", "timestamp", "pm25_forecast_24h"]]
