# AirIQ — Architecture

## High-level system diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                  │
│                                                                            │
│   CPCB / OpenAQ v3        Sentinel-5P (NO2)      Open-Meteo (weather)      │
│   (30 ground stations)    Copernicus / GEE       Free API, no key          │
│                                                                            │
│   NASA FIRMS (fires)      OSM + Bhuvan          Synthetic-Delhi generator  │
│   Crop-burning detection  land-use / POIs        (offline demo mode)       │
└──────────────────────────────────────┬─────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                          INGESTION & FEATURE STORE                         │
│                                                                            │
│   data_pipeline.py                                                         │
│   - hourly pulls per station         - parquet feature store (data/)       │
│   - synthetic fallback               - reproducible RNG seed               │
│                                                                            │
│   features.py                                                              │
│   - lag features (1/3/6/24h)         - weather + satellite + context       │
│   - rolling means (3/24h)            - persistence baseline column         │
└──────────────────────────────────────┬─────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                                ML LAYER                                    │
│                                                                            │
│   Module A — forecaster.py            Module B — attribution.py            │
│   HistGradientBoosting regressors     RandomForest multi-output            │
│   Horizons: 1/24/48/72h               5 source classes                     │
│   Metric: RMSE vs persistence         Metric: dominant + top-2 accuracy    │
│                                                                            │
│   Module C — advisory.py                                                   │
│   Template-based multilingual advisory (EN/HI/TA/KN/BN)                    │
│   Vulnerability-aware AQI bumping (elderly/child/asthmatic/…)              │
└──────────────────────────────────────┬─────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                            PRESENTATION LAYER                              │
│                                                                            │
│   app.py — Streamlit dashboard (5 tabs)                                    │
│     ├─ Overview        (folium map + KPIs + 7-day trend)                   │
│     ├─ Forecast        (per-station 24/48/72h + RMSE table)                │
│     ├─ Source Insights (attribution map + per-station pie)                 │
│     ├─ Citizen Bot     (5-language WhatsApp-style advisory)                │
│     └─ About/Metrics   (judging-aligned evidence)                          │
└────────────────────────────────────────────────────────────────────────────┘
```

## Data flow (one row)

1. **Every hour**, `data_pipeline.py` writes one row per station to the parquet feature store.
2. **Feature builder** creates lags, rolling means, weather, satellite and context columns.
3. **Module A** predicts PM2.5 at `t + {1, 24, 48, 72}h`.
4. **Module B** predicts a length-5 vector of source shares.
5. **Streamlit app** loads latest rows, calls both modules, renders maps + advisories.

## Scalability

- **New city**: change `config.CITY_NAME`, `BBOX`, `STATIONS`. No code changes to models.
- **Real-time**: swap `generate_synthetic_dataset()` for a cron job hitting OpenAQ + Open-Meteo every 15 min.
- **1 km grid resolution**: `features.py` already supports grid rows in addition to station rows.
- **Multi-tenant**: the parquet store and joblib artifacts partition trivially by city.

## Security & privacy

- No PII stored anywhere; only public sensor readings and satellite products.
- API keys read from `.env` via `python-dotenv`; never logged.
- Citizen bot returns advisory without recording user input (stateless).

## Failure modes

- **Missing sensor data** → NaN lags → row dropped by feature builder; other stations unaffected.
- **API outage** → app falls back to last cached parquet automatically.
- **Model missing** → app displays a clear "run generate_and_train.py" hint (no silent failure).
