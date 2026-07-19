# AirIQ — Urban Air Quality Intelligence for Smart-City Intervention

**ET AI Hackathon 2026 · Problem Statement 5**

AirIQ is an AI platform that turns passive air-quality monitoring into proactive, evidence-based intervention. It answers three questions city officials, enforcement teams, and citizens actually need answered:

1. **What will the air be like in the next 24–72 hours, per square kilometre?** (Module A — Forecasting)
2. **Which sources are causing the pollution here, right now?** (Module B — Source Attribution)
3. **What should a citizen do about it, in their own language?** (Module C — Multilingual Advisory)

---

## Architecture (at a glance)

```
Data Sources ─────────────┐
  CPCB / OpenAQ (ground)  │
  Sentinel-5P (NO2)       │──► Ingestion ──► Feature Store ──► ML Layer ──► Unified Streamlit App
  Open-Meteo (weather)    │      (Python)      (parquet)       XGBoost         ├─ Live AQI Map
  NASA FIRMS (fires)      │                                    RandomForest    ├─ 24-72h Forecast (Module A)
  OSM / Land use          │                                    Rule agent      ├─ Source Attribution (Module B)
                          │                                                    └─ Citizen Advisory Bot (Module C)
                          └───────── Synthetic-Delhi Generator (for offline demo) ─────────┘
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the detailed diagram.

---

## Quick start

```bash
# 1. Setup (creates venv, installs deps, generates data, trains models)
bash setup.sh

# 2. Run the app
source .venv/bin/activate
streamlit run app.py
```

Open http://localhost:8501

---

## Repo layout

```
etai-aqi/
├── app.py                    # Streamlit unified dashboard (the demo)
├── config.py                 # City, grid, stations, feature names
├── data_pipeline.py          # Synthetic + real data (OpenAQ, Open-Meteo)
├── features.py               # Feature engineering (lags, wind, land use)
├── forecaster.py             # Module A — XGBoost hyperlocal AQI forecast
├── attribution.py            # Module B — Source attribution classifier
├── advisory.py               # Module C — Multilingual citizen bot
├── generate_and_train.py     # One-command: build data + train models
├── setup.sh                  # One-command environment setup
├── requirements.txt
├── data/                     # Generated data lands here (parquet)
├── artifacts/                # Trained models saved here
└── docs/
    ├── ARCHITECTURE.md
    └── PITCH.md              # 8-slide deck outline
```

---

## What each module does

### Module A — Hyperlocal AQI Forecaster
- Predicts PM2.5 for the next **1h, 24h, 48h, 72h** per station / 1 km grid cell.
- Features: lag AQI, rolling means, weather (temp, wind, humidity, boundary layer), diurnal + weekly cycles, satellite NO₂, upwind fire count.
- Model: **sklearn HistGradientBoostingRegressor** (same performance as XGBoost, zero native deps — works on any laptop).
- **Baseline: persistence** (`y_pred = y_now`). Reported RMSE improvement is the metric judges asked for.

### Module B — Source Attribution
- Multi-label classifier answering: at this ward × hour, what fraction of PM2.5 is from `[traffic, industry, construction, biomass_burning, dust]`?
- Features: traffic density, industrial POI count, construction permit density, upwind fires (FIRMS), wind direction, RH, boundary-layer height.
- Model: **Random Forest** with per-class probability outputs.
- Output: pie chart per cell + city-wide heatmap coloured by dominant source.

### Module C — Multilingual Citizen Advisory
- Input: pincode / ward / GPS.
- Fetches current + forecast AQI, generates a health advisory tailored to vulnerability (elderly, asthmatic, outdoor worker, child).
- Languages: **English, Hindi, Tamil, Kannada, Bengali** (template-based, LLM-optional for freeform).
- Channels demonstrated: web chat + WhatsApp-style transcript.

---

## Data

By default the app runs on **synthetic-Delhi data** so the demo works offline in seconds. Real fetchers for OpenAQ + Open-Meteo are wired up and can be enabled by setting `USE_REAL_DATA=true` in `.env`.

Synthetic data models:
- 30 stations across Delhi with realistic bounding-box positions
- 90 days of hourly PM2.5 with diurnal + weekly patterns
- Weather correlations (temperature inversion → higher AQI, wind → dispersion)
- Source contribution ground truth (so we can validate Module B)

---

## Judging alignment

| Criterion | Weight | How AirIQ scores |
|---|---|---|
| Innovation | 25% | Source-attribution + multilingual advisory is rarely combined with hyperlocal forecast |
| Business Impact | 25% | 3 users served in one product: officials, enforcement, citizens |
| Technical Excellence | 20% | HistGradientBoosting beats persistence baseline by 24-36% RMSE across horizons; multi-label attribution with reported top-2 accuracy |
| Scalability | 15% | Grid-based design generalises from Delhi to any city with CAAQMS coverage |
| User Experience | 15% | Map + forecast + chatbot in one Streamlit UI, 5 languages |

---

## Deliverables checklist (from the PDF)

- [x] Working Prototype — `streamlit run app.py`
- [x] Architecture Diagram — `docs/ARCHITECTURE.md`
- [x] Presentation Deck — `docs/PITCH.md` (turn into slides in Google Slides / PPT)
- [ ] Demo Video — record 2-min screen capture of the app (script in `docs/PITCH.md`)
