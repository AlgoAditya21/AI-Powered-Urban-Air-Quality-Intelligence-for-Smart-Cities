"""Feature engineering for forecasting and source attribution."""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import (
    CONTEXT_FEATURES,
    LAG_HOURS,
    ROLLING_HOURS,
    SATELLITE_FEATURES,
    SOURCE_CLASSES,
    TARGET,
    WEATHER_FEATURES,
)


def build_forecast_features(df: pd.DataFrame, horizon_h: int = 24) -> tuple[pd.DataFrame, pd.Series]:
    """Create X, y for the forecaster.

    Target: PM2.5 at t + horizon_h, per station.
    Features: lag PM2.5, rolling means, weather at t, satellite at t, context at t.
    """
    df = df.sort_values(["station_id", "timestamp"]).copy()

    grp = df.groupby("station_id", group_keys=False)

    # lag features
    for lag in LAG_HOURS:
        df[f"pm25_lag_{lag}h"] = grp[TARGET].shift(lag)

    # rolling means (past)
    for w in ROLLING_HOURS:
        df[f"pm25_roll_{w}h"] = grp[TARGET].transform(
            lambda s: s.shift(1).rolling(w, min_periods=1).mean()
        )

    # target = pm25 shifted forward
    df["target"] = grp[TARGET].shift(-horizon_h)

    # persistence baseline column (y_pred = current pm25)
    df["persistence"] = df[TARGET]

    feature_cols = (
        [f"pm25_lag_{lag}h" for lag in LAG_HOURS]
        + [f"pm25_roll_{w}h" for w in ROLLING_HOURS]
        + WEATHER_FEATURES
        + SATELLITE_FEATURES
        + CONTEXT_FEATURES
    )

    df = df.dropna(subset=feature_cols + ["target"]).reset_index(drop=True)

    X = df[feature_cols + ["timestamp", "station_id", "persistence"]].copy()
    y = df["target"].copy()
    return X, y


def build_attribution_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create X, Y for the multi-output source-attribution classifier.

    X: context + weather + satellite + station lat/lon at time t
    Y: ground-truth source shares (5 continuous outputs summing to ~1)
    """
    feature_cols = WEATHER_FEATURES + SATELLITE_FEATURES + CONTEXT_FEATURES + ["lat", "lon"]
    target_cols = [f"src_{c}" for c in SOURCE_CLASSES]

    keep = df.dropna(subset=feature_cols + target_cols).reset_index(drop=True)
    X = keep[feature_cols + ["timestamp", "station_id"]].copy()
    Y = keep[target_cols].copy()
    return X, Y


def latest_row_per_station(df: pd.DataFrame) -> pd.DataFrame:
    """Return the most recent row for each station."""
    return (
        df.sort_values("timestamp")
          .groupby("station_id", as_index=False)
          .tail(1)
          .reset_index(drop=True)
    )
