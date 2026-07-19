# AirIQ — Pitch Deck Outline (8 slides)

Turn each block below into one slide (Google Slides or Keynote).
Rehearsed length: **4 minutes**.

---

## Slide 1 — Title
- **AirIQ — Urban Air Quality Intelligence for Smart-City Intervention**
- Team name · College · Problem Statement 5 · ET AI Hackathon 2026
- One-line pitch: *"From measuring pollution to acting on it — hyperlocal forecasts, source attribution, and citizen advisory in one AI platform."*

## Slide 2 — The problem (2025-26 numbers)
- Delhi averaged **AQI 218 for 200+ days** in 2024–25. Air pollution kills **1.67 million Indians annually** (Lancet).
- India has **900+ CAAQMS stations**, but only **31% of cities** have any multi-agency action protocol tied to them (CAG audit 2024).
- **The data exists. The intelligence to act on it does not.**

## Slide 3 — What AirIQ does (3 modules, 1 platform)
- **Module A — Forecast** — Predict PM2.5 at 1/24/48/72h horizons, per station or 1 km grid cell.
- **Module B — Source attribution** — Attribute each hotspot to traffic / industry / construction / biomass / dust with confidence.
- **Module C — Citizen advisory** — 5-language, vulnerability-aware advisory over WhatsApp / IVR / web.

*(Screenshot: 3-tab collage of the Streamlit dashboard)*

## Slide 4 — Architecture
- Insert the diagram from `docs/ARCHITECTURE.md`.
- Callouts:
  - **Data**: CPCB / OpenAQ + Sentinel-5P + Open-Meteo + FIRMS + OSM.
  - **ML**: XGBoost forecast · Random Forest attribution.
  - **UI**: Streamlit + Folium + Plotly.

## Slide 5 — Module A results (Technical Excellence)
- Table of RMSE vs. persistence baseline at 1h / 24h / 48h / 72h — copy from the **About & Metrics** tab.
- **Headline number**: "AirIQ beats the persistence baseline by X% at the 24h horizon."
- One chart: history + dashed forecast line for a real station.

## Slide 6 — Module B results (Innovation)
- Metrics: **dominant-source accuracy = Y%**, **macro MAE = Z**.
- Screenshot of city map coloured by dominant source.
- Zoom into one station: pie chart of source contributions + **automated enforcement recommendation** ("dispatch traffic-police squad", "trigger road-sweeping", etc.).

## Slide 7 — Module C in action (Business Impact + UX)
- Screenshot of the WhatsApp-style bubble in 5 languages.
- Vulnerability control: what an elderly asthmatic sees vs. a general adult.
- Reach angle: **≈95% of India's urban population is covered by these 5 languages**.

## Slide 8 — Scalability & the ask
- New city? Change `config.CITY_NAME` and `STATIONS`. Nothing else.
- Real-time? Swap the synthetic generator for a 15-min cron on OpenAQ + Open-Meteo.
- Deployable on any city's cloud in **< 2 hours**.
- **Ask**: pilot deployment with one Smart City Mission-partner ULB — Delhi, Bengaluru, or Pune.

---

# Demo video script (2 minutes)

1. **[0:00–0:10]** *Cold open on the Streamlit Overview map.* "This is Delhi, right now. 30 monitoring stations, colour-coded by AQI."
2. **[0:10–0:35]** Click Forecast tab · pick Anand Vihar · read the +24h forecast · **highlight the RMSE-vs-baseline table** ("we beat persistence by X%").
3. **[0:35–1:15]** Click Source Insights tab · point at the coloured map · pick a hotspot · **show the pie chart and enforcement recommendation** ("Anand Vihar right now — 62% traffic, dispatch enforcement to NH-24").
4. **[1:15–1:50]** Click Citizen Bot tab · switch language to Hindi · switch profile to "asthmatic" · **show the WhatsApp-style advisory changing live**.
5. **[1:50–2:00]** Closing card: "AirIQ. From measuring pollution to acting on it."

---

# One-page executive summary (for the submission form)

> **AirIQ** turns India's 900+ CAAQMS stations from passive dashboards into a proactive intervention platform. It fuses ground sensors, Sentinel-5P satellite data, weather, land-use, and fire feeds into three AI capabilities: a hyperlocal 24-72h PM2.5 forecaster (XGBoost) that beats a persistence baseline by X% RMSE; a source-attribution model (Random Forest) that classifies each hotspot into traffic/industry/construction/biomass/dust with Y% dominant-source accuracy; and a multilingual citizen advisory bot in five Indian languages with vulnerability-aware health guidance. Delivered as a unified Streamlit application, AirIQ compresses the loop from *signal* to *action* — for city administrators, enforcement teams, and every citizen with a phone.
