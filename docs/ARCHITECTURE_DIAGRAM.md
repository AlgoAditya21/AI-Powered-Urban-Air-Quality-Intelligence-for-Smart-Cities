# AirIQ — Architecture Diagram

Below is a compact architecture diagram for the AirIQ project.

```mermaid
flowchart TD
  subgraph DATA[Data Sources]
    A1[Ground stations (CPCB / OpenAQ)]
    A2[Satellite (Sentinel-5P / NASA FIRMS)]
    A3[Weather APIs (Open-Meteo)]
    A4[Land-use / POIs (OSM / Bhuvan)]
  end

  subgraph INGEST[Ingestion & Feature Store]
    B1[data_pipeline.py - ingest & write parquet]
    B2[features.py - build lags / rolling / context]
    B3[Parquet feature store (data/)]
  end

  subgraph ML[ML Layer]
    C1[Module A: forecaster (Gradient Boosting)]
    C2[Module B: attribution (RandomForest)]
    C3[Module C: advisory (template-based)]
    C4[Model artifacts (.joblib) in `artifacts/`]
  end

  subgraph PRES[Presentation]
    D1[Streamlit app (`app.py`)]
    D2[Folium map / Plotly charts / KPIs / Bot UI]
  end

  subgraph OPS[Ops & Repo]
    E1[GitHub repo]
    E2[Git LFS for `artifacts/` & `data/`]
    E3[CI / Deploy: Docker, Cloud Run or VM]
    E4[Monitoring & Logs]
  end

  %% flow
  A1 --> B1
  A2 --> B1
  A3 --> B1
  A4 --> B1
  B1 --> B3
  B2 --> B3
  B3 --> C1
  B3 --> C2
  C1 --> C4
  C2 --> C4
  C1 --> D1
  C2 --> D1
  C3 --> D1
  C4 --> D1
  D1 --> D2
  C4 --> E2
  B3 --> E2
  E2 --> E1
  E1 --> E3
  E3 --> D1
  E3 --> C1
  E3 --> C2
  E3 --> C3
  E4 --> E3
```

Saved to `docs/ARCHITECTURE_DIAGRAM.md`.
