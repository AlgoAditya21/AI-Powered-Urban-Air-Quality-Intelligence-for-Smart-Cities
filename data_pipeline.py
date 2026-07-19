"""Data pipeline: synthetic-Delhi generator + optional real fetchers.

The synthetic generator produces 90 days of hourly PM2.5 for 30 stations with:
  - realistic diurnal + weekly patterns
  - weather-linked variation (inversion boosts, wind disperses)
  - explicit source-contribution ground truth so Module B can be validated

Real fetchers (Open-Meteo weather, OpenAQ ground stations) are wired but
disabled by default so the demo works offline.
"""
from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests

from config import (
    BBOX,
    CONTEXT_FEATURES,
    DATA_DIR,
    SATELLITE_FEATURES,
    SOURCE_CLASSES,
    STATIONS,
    TARGET,
    WEATHER_FEATURES,
    pm25_to_aqi,
)

RNG = np.random.default_rng(seed=42)


# --------------------------------------------------------------------------- #
# Synthetic generator                                                         #
# --------------------------------------------------------------------------- #

def _diurnal(hour: np.ndarray) -> np.ndarray:
    """Two-peak diurnal PM2.5 signature (morning + evening rush + night stagnation)."""
    return (
        18 * np.exp(-((hour - 8) ** 2) / 6)      # morning rush
        + 22 * np.exp(-((hour - 20) ** 2) / 8)   # evening rush
        + 15 * np.exp(-((hour - 3) ** 2) / 10)   # nighttime stagnation
    )


def _seasonal(day_of_year: np.ndarray) -> np.ndarray:
    """Winter (Oct-Feb) peak; summer trough (monsoon wash-out)."""
    return 40 * np.cos(2 * np.pi * (day_of_year - 15) / 365)


def _station_bias(station_ward: str) -> float:
    """Ward-specific baseline offset (industrial NW / east tends to be worse)."""
    biases = {
        "East Delhi":            35,
        "North East Delhi":      30,
        "North West Delhi":      40,
        "North Delhi":           20,
        "Central Delhi":         25,
        "West Delhi":            30,
        "New Delhi":             10,
        "South Delhi":           5,
        "South East Delhi":      15,
        "South West Delhi":      10,
    }
    return biases.get(station_ward, 20)


def _generate_weather(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Simple weather model for Delhi with seasonality."""
    doy = timestamps.dayofyear.to_numpy()
    hour = timestamps.hour.to_numpy()

    # temperature: annual + diurnal cycle
    temp_c = (
        25 + 10 * np.cos(2 * np.pi * (doy - 200) / 365)     # annual (peak mid-Jul)
        - 5 * np.cos(2 * np.pi * hour / 24)                 # diurnal
        + RNG.normal(0, 1.5, size=len(timestamps))
    )
    humidity_pct = np.clip(
        70 - 0.8 * (temp_c - 25) + RNG.normal(0, 8, size=len(timestamps)), 15, 95
    )
    # wind lighter at night → inversion → higher PM
    wind_speed_ms = np.clip(
        2.5 + 1.5 * np.sin(2 * np.pi * (hour - 8) / 24)
        + RNG.normal(0, 0.8, size=len(timestamps)),
        0.1, 12,
    )
    wind_dir_deg = (
        180 + 90 * np.sin(2 * np.pi * doy / 365)
        + RNG.normal(0, 30, size=len(timestamps))
    ) % 360
    # boundary layer: deep during day, shallow at night (esp. winter)
    boundary_layer_m = np.clip(
        1200 - 800 * np.cos(2 * np.pi * hour / 24)
        - 300 * np.cos(2 * np.pi * (doy - 15) / 365)
        + RNG.normal(0, 100, size=len(timestamps)),
        150, 2500,
    )
    precip_mm = np.where(
        (doy > 175) & (doy < 260),  # monsoon
        np.clip(RNG.exponential(1.5, size=len(timestamps)) - 1, 0, None),
        np.clip(RNG.exponential(0.2, size=len(timestamps)) - 0.15, 0, None),
    )

    return pd.DataFrame({
        "timestamp": timestamps,
        "temp_c": temp_c,
        "humidity_pct": humidity_pct,
        "wind_speed_ms": wind_speed_ms,
        "wind_dir_deg": wind_dir_deg,
        "boundary_layer_m": boundary_layer_m,
        "precip_mm": precip_mm,
    })


def _generate_context(timestamps: pd.DatetimeIndex, station) -> pd.DataFrame:
    """Contextual features per station × time: traffic, POIs, fires, calendar."""
    hour = timestamps.hour.to_numpy()
    dow = timestamps.dayofweek.to_numpy()
    doy = timestamps.dayofyear.to_numpy()

    # traffic: bimodal rush-hour peaks, lower on weekend
    weekend_factor = np.where(dow >= 5, 0.6, 1.0)
    traffic_density = (
        weekend_factor
        * (
            80 * np.exp(-((hour - 9) ** 2) / 4)
            + 90 * np.exp(-((hour - 19) ** 2) / 4)
            + 20
        )
        + RNG.normal(0, 6, size=len(timestamps))
    )

    # industrial POI count (static per station, ward-based)
    industrial_high_wards = {"North West Delhi", "East Delhi", "West Delhi"}
    industrial_poi_count = np.full(
        len(timestamps),
        18 if station.ward in industrial_high_wards else 4,
    )

    # construction permits (mildly time-varying)
    construction_base = 12 if station.ward in {"South West Delhi", "North West Delhi"} else 5
    construction_permits = construction_base + (RNG.random(len(timestamps)) < 0.02).cumsum() % 10

    # upwind fires: winter crop-burning season Oct-Nov strong
    fire_season = np.where((doy > 275) & (doy < 335), 1.0, 0.05)
    upwind_fire_count = np.clip(
        fire_season * RNG.poisson(30, size=len(timestamps))
        + RNG.poisson(1, size=len(timestamps)),
        0, None,
    )

    return pd.DataFrame({
        "timestamp": timestamps,
        "traffic_density": traffic_density,
        "industrial_poi_count": industrial_poi_count,
        "construction_permits": construction_permits,
        "upwind_fire_count_50km": upwind_fire_count,
        "hour_of_day": hour,
        "day_of_week": dow,
        "is_weekend": (dow >= 5).astype(int),
        "month": timestamps.month.to_numpy(),
    })


def _generate_satellite(timestamps: pd.DatetimeIndex, weather: pd.DataFrame) -> pd.DataFrame:
    """Mock Sentinel-5P NO2 column + AOD 550nm."""
    # NO2 anti-correlates with wind + boundary-layer height; peaks in evening
    no2_column = np.clip(
        150
        - 6 * weather["wind_speed_ms"].to_numpy()
        - 0.03 * weather["boundary_layer_m"].to_numpy()
        + 20 * np.sin(2 * np.pi * (timestamps.hour - 18) / 24)
        + RNG.normal(0, 15, size=len(timestamps)),
        20, 400,
    )
    aod_550 = np.clip(
        0.6
        - 0.02 * weather["wind_speed_ms"].to_numpy()
        + 0.0002 * (weather["humidity_pct"].to_numpy() - 40)
        + RNG.normal(0, 0.08, size=len(timestamps)),
        0.05, 2.5,
    )
    return pd.DataFrame({
        "timestamp": timestamps,
        "no2_column": no2_column,
        "aod_550": aod_550,
    })


def _generate_pm25_with_sources(
    weather: pd.DataFrame,
    context: pd.DataFrame,
    satellite: pd.DataFrame,
    station,
) -> pd.DataFrame:
    """Physics-motivated PM2.5 with explicit source contributions (ground truth for Module B)."""
    n = len(weather)
    hour = weather["timestamp"].dt.hour.to_numpy()
    doy = weather["timestamp"].dt.dayofyear.to_numpy()

    # Meteorology multiplier: bad weather amplifies everything
    met_mult = np.clip(
        1.0
        + 0.9 * np.exp(-weather["wind_speed_ms"].to_numpy() / 2.0)   # low wind → high PM
        + 0.6 * np.exp(-weather["boundary_layer_m"].to_numpy() / 500)  # shallow BL → high PM
        - 0.4 * np.clip(weather["precip_mm"].to_numpy(), 0, 3) / 3    # rain → washout
        + _seasonal(doy) / 60,
        0.3, 3.0,
    )

    # --- source-specific contributions (µg/m³) before met multiplier ---
    traffic     = 0.25 * context["traffic_density"].to_numpy()
    industry    = 1.4 * context["industrial_poi_count"].to_numpy() * (1 + 0.3 * np.sin(2*np.pi*hour/24))
    construction = 0.8 * context["construction_permits"].to_numpy() * (1 - context["is_weekend"].to_numpy() * 0.5)
    biomass     = 0.9 * context["upwind_fire_count_50km"].to_numpy()
    dust        = np.clip(6 + 0.4 * (weather["wind_speed_ms"].to_numpy() - 3), 0, None) * (1 + 0.5 * (weather["humidity_pct"].to_numpy() < 30))

    # Apply meteorology to all sources
    traffic      = traffic * met_mult
    industry     = industry * met_mult
    construction = construction * met_mult
    biomass      = biomass * met_mult
    dust         = dust * met_mult

    # Station bias + noise
    bias = _station_bias(station.ward)
    noise = RNG.normal(0, 4, size=n)

    pm25 = traffic + industry + construction + biomass + dust + bias + _diurnal(hour) * met_mult / 2 + noise
    pm25 = np.clip(pm25, 3, 900)

    df = pd.DataFrame({
        "timestamp": weather["timestamp"],
        "station_id": station.station_id,
        "station_name": station.name,
        "ward": station.ward,
        "lat": station.lat,
        "lon": station.lon,
        "pm25": pm25,
        # ground-truth source shares (fraction of total)
        "src_traffic":      traffic      / (pm25 + 1e-6),
        "src_industry":     industry     / (pm25 + 1e-6),
        "src_construction": construction / (pm25 + 1e-6),
        "src_biomass_burning": biomass   / (pm25 + 1e-6),
        "src_dust":         dust         / (pm25 + 1e-6),
    })
    # Normalise so shares sum to 1 (any residual = "other/background" folded into dust)
    src_cols = [f"src_{c}" for c in SOURCE_CLASSES]
    df[src_cols] = df[src_cols].div(df[src_cols].sum(axis=1), axis=0).fillna(0)
    return df


def generate_synthetic_dataset(days: int = 90) -> pd.DataFrame:
    """Generate full dataset: hourly rows, one per (station, timestamp)."""
    end = datetime(2026, 1, 5, 23, 0, 0)
    start = end - timedelta(days=days)
    timestamps = pd.date_range(start=start, end=end, freq="h")

    rows = []
    for st in STATIONS:
        weather = _generate_weather(timestamps)
        context = _generate_context(timestamps, st)
        satellite = _generate_satellite(timestamps, weather)
        pm = _generate_pm25_with_sources(weather, context, satellite, st)

        merged = (
            pm.merge(weather, on="timestamp")
              .merge(context, on="timestamp")
              .merge(satellite, on="timestamp")
        )
        rows.append(merged)

    df = pd.concat(rows, ignore_index=True)
    df["aqi"] = df["pm25"].apply(lambda x: pm25_to_aqi(x)[0])
    df["aqi_category"] = df["pm25"].apply(lambda x: pm25_to_aqi(x)[1])
    return df


# --------------------------------------------------------------------------- #
# Real data fetchers (optional)                                               #
# --------------------------------------------------------------------------- #

def fetch_open_meteo(lat: float, lon: float, hours_back: int = 72) -> pd.DataFrame:
    """Fetch recent hourly weather from Open-Meteo (no API key)."""
    end = datetime.utcnow()
    start = end - timedelta(hours=hours_back)
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,"
        "wind_direction_10m,precipitation,boundary_layer_height"
        f"&start_date={start.strftime('%Y-%m-%d')}"
        f"&end_date={end.strftime('%Y-%m-%d')}"
        "&timezone=Asia%2FKolkata"
    )
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    j = r.json()["hourly"]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(j["time"]),
        "temp_c": j["temperature_2m"],
        "humidity_pct": j["relative_humidity_2m"],
        "wind_speed_ms": j["wind_speed_10m"],
        "wind_dir_deg": j["wind_direction_10m"],
        "precip_mm": j["precipitation"],
        "boundary_layer_m": j["boundary_layer_height"],
    })


def fetch_openaq(city: str = "Delhi", limit: int = 1000) -> pd.DataFrame:
    """Fetch recent PM2.5 measurements from OpenAQ v3 (needs OPENAQ_API_KEY)."""
    key = os.getenv("OPENAQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAQ_API_KEY not set — cannot fetch real OpenAQ data.")
    url = "https://api.openaq.org/v3/measurements"
    r = requests.get(
        url,
        headers={"X-API-Key": key},
        params={"city": city, "parameter": "pm25", "limit": limit},
        timeout=20,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        return pd.DataFrame()
    rows = [{
        "timestamp": pd.to_datetime(x["date"]["utc"]),
        "pm25": x["value"],
        "lat": x["coordinates"]["latitude"],
        "lon": x["coordinates"]["longitude"],
        "station_name": x["location"],
    } for x in results]
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Persistence                                                                 #
# --------------------------------------------------------------------------- #

DATASET_PATH = DATA_DIR / "aqi_dataset.parquet"
STATIONS_PATH = DATA_DIR / "stations.parquet"


def save_dataset(df: pd.DataFrame) -> None:
    df.to_parquet(DATASET_PATH, index=False)
    stations_df = pd.DataFrame([asdict(s) for s in STATIONS])
    stations_df.to_parquet(STATIONS_PATH, index=False)


def load_dataset() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATASET_PATH}. Run `python generate_and_train.py` first."
        )
    return pd.read_parquet(DATASET_PATH)


def load_stations() -> pd.DataFrame:
    if not STATIONS_PATH.exists():
        return pd.DataFrame([asdict(s) for s in STATIONS])
    return pd.read_parquet(STATIONS_PATH)


if __name__ == "__main__":
    print("Generating synthetic Delhi dataset...")
    df = generate_synthetic_dataset(days=90)
    save_dataset(df)
    print(f"Saved {len(df):,} rows across {df['station_id'].nunique()} stations "
          f"→ {DATASET_PATH}")
