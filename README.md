# AirIQ — Urban Air Quality Intelligence for Smart-City Intervention

### **ET AI Hackathon 2026 | Problem Statement 5: Smart Cities**

🌐 **Live Deployment:** ([https://airiq-smartcity.app](https://ai-powered-urban-air-quality-intelligence-for-smart-cities-gcy.streamlit.app/)) 

AirIQ transitions urban air quality management from a passive, observation-only model into an active, predictive framework for public safety and administrative response. Built as a unified intelligence platform, it provides actionable insights tailored for municipal leaders, field inspectors, and community members.

![AirIQ Dashboard Command Center UI](image.png)

---

## 🏛️ System Architecture

The end-to-end framework bridges automated multi-stream ingestion layer pipelines with high-performance regression networks, exposing the analytical layer inside a responsive, live operations control console.

![AirIQ Full Architecture Diagram](architecture_diagram.png)

### Core Pipeline Structure

1. **Data Ingestion Engine:** Automated ingestion layers processing ground-truth observations (CPCB / OpenAQ), satellite gas profiles (Sentinel-5P NO₂ tracking), real-time ambient meteorology data loops (Open-Meteo API), active ignition patterns (NASA FIRMS upwind vectors), and local spatial layouts (OSM / Bhuvan POI tracking points).
2. **Feature Store:** Cleansed inputs are cataloged inside structured Parquet files using custom engineered metrics, including dynamic spatial rolling averages, temporal time-lag shifts, and localized topological metrics.
3. **Machine Learning Microservices:** Decoupled functional models trained on target patterns, outputting predictive trends, multi-label fractional source estimations, and localized community advisory copies.
4. **Presentation Engine:** A high-performance dashboard UI constructed via Streamlit integrating dynamic spatial coordinates (Folium), metric distributions (Plotly), and live multilingual modules.

---

## 🛠️ Deep-Dive Product Modules

### 📈 Module A — Hyperlocal AQI Forecasting Engine
* **Objective:** Generates granular estimations for localized $PM_{2.5}$ particles across specific 1-hour, 24-hour, 48-hour, and 72-hour forecast horizons mapped to a $1\text{ km}^2$ spatial resolution coordinate grid.
* **Feature Engineering Matrix:** Employs temporal target value offsets, spatial rolling averages, detailed atmospheric conditions (ambient temperature, wind vector components, relative humidity boundaries, boundary layer elevations), cyclical time-series variables, satellite observations, and real-time upwind thermal signatures.
* **Core Algorithm:** Leverages `HistGradientBoostingRegressor` to ensure optimal gradient-boosted training parity with complex XGBoost ensembles, while avoiding heavy architecture dependencies to guarantee frictionless local compilation.
* **Target Metric Focus:** Evaluated directly against basic temporal persistence variables ($y_{t+n} = y_t$). The configuration demonstrates a measurable $24\%\text{--}36\%$ optimization in Root Mean Squared Error ($RMSE$), ensuring highly dependable predictive trajectories across macro horizons.

### 🏭 Module B — Real-Time Source Attribution Classifier
* **Objective:** A dedicated multi-label probabilistic model determining structural source shares for any target ward or time slot across five key pillars:
  $$\text{Source Share} = [f(\text{Traffic}), f(\text{Industry}), f(\text{Construction}), f(\text{Biomass Burning}), f(\text{Dust})]$$
* **Feature Input Stream:** Correlates real-world vehicular transit loads, historical factory coordinate densities, structural construction permit records, upwind thermal events, boundary layer behaviors, and real-time wind dispersal velocities.
* **Core Algorithm:** Utilizes an optimized Random Forest architecture capable of calculating multi-output probabilities simultaneously, enabling precise tracking of mixed environmental signatures.
* **Visualization Layer:** Feeds a dynamic city-wide spatial matrix alongside responsive pie chart indicators that instantly reveal the primary local emission driver.

### 💬 Module C — Multilingual Citizen Advisory Engine
* **Objective:** Processes active geo-coordinates, pincode areas, or target municipal wards to translate broad sensor intelligence into tailored community guidance.
* **Vulnerability Adaptation:** Dynamically alters output recommendations based on specified risk tiers, including high-risk profiles for infants, outdoor labor teams, asthmatic demographics, and senior populations.
* **Language Layer Support:** Features full structural localization across five languages: English, Hindi, Tamil, Kannada, and Bengali.
* **Interface Demonstration:** Showcases production-ready implementations via integrated web-chat components alongside fully mocked instant-messaging transcript simulations.

---

## 📂 Repository Blueprint

```text
etai-aqi/
├── app.py                    # Streamlit unified dashboard (the master interface)
├── config.py                 # Core configurations (coordinates, grids, stations, features)
├── data_pipeline.py          # Unified data loaders (OpenAQ, Open-Meteo, & Synthetic)
├── features.py               # Feature engineering pipelines (lags, rolling means, wind vectors)
├── forecaster.py             # Module A — Hyperlocal regression model configuration
├── attribution.py            # Module B — Multi-label source attribution engine
├── advisory.py               # Module C — Localization rules & conversational advisory engine
├── generate_and_train.py     # End-to-end orchestration: builds feature store & trains models
├── setup.sh                  # Comprehensive environment initialization script
├── requirements.txt          # Python library dependencies
├── data/                     # Local feature store storage (Parquet footprint format)
├── artifacts/                # Serialized model binaries (.joblib format)
└── docs/                     # Comprehensive structural documentation assets
    ├── ARCHITECTURE.md       # Extended system pipeline specifications
    └── PITCH.md              # 8-slide presentation deck strategy layout
