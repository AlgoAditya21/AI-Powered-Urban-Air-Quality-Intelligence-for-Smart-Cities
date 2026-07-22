"""AirIQ — Streamlit unified dashboard.

Four tabs:
  1. Overview        — live AQI map of Delhi + KPIs
  2. Forecast        — Module A: 24/48/72h hyperlocal forecast
  3. Source Insights — Module B: per-station attribution + city map
  4. Citizen Bot     — Module C: multilingual advisory
"""
from __future__ import annotations

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

import os

import advisory
import attribution
import forecaster
from config import CITY_CENTER, SOURCE_CLASSES, STATIONS, aqi_color, pm25_to_aqi
from data_pipeline import load_dataset


# --------------------------------------------------------------------------- #
# Small helpers                                                               #
# --------------------------------------------------------------------------- #

def _action_for(source: str) -> str:
    return {
        "traffic":         "Dispatch traffic-police squad · enforce BS-VI norms · reroute heavy vehicles",
        "industry":        "DPCC inspection of nearby industrial POIs · check stack-emission records",
        "construction":    "Verify dust-suppression compliance · issue stop-work if PM10 breach",
        "biomass_burning": "Coordinate with neighbouring-state pollution board · deploy fire-response",
        "dust":            "Trigger mechanised road-sweeping · water-sprinkling on arterial roads",
    }.get(source, "Escalate to municipal command centre for review")


def _has_docs() -> bool:
    return os.path.exists("docs/ARCHITECTURE.md")

def _has_attribution_model() -> bool:
    return attribution.MODEL_PATH.exists()

# --------------------------------------------------------------------------- #
# Page config                                                                 #
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="AirIQ — Urban Air Quality Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🌫️",
)

st.markdown("""
<style>
:root { color-scheme: dark; }
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top left, rgba(56,189,248,0.16), transparent 18%),
                radial-gradient(circle at bottom right, rgba(74,222,128,0.14), transparent 16%),
                linear-gradient(180deg, #020617 0%, #071a34 42%, #050811 100%);
}
[data-testid="stSidebar"] > div:first-child {
    background: rgba(5, 15, 37, 0.96);
    border-right: 1px solid rgba(255,255,255,0.08);
}
.main .block-container {padding-top: 1.6rem; padding-bottom: 2rem; color: #e2e8f0;}
section[data-testid="stBlock"] > div {
    background: rgba(10, 18, 40, 0.78);
    border: 1px solid rgba(96,165,250,0.14);
    border-radius: 24px;
    box-shadow: 0 26px 90px rgba(0, 0, 0, 0.24);
    backdrop-filter: blur(14px);
}
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    background: rgba(255,255,255,0.08);
    padding: 8px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.12);
}
.stTabs [data-baseweb="tab"] {
    padding: 10px 18px;
    font-weight: 700;
    color: #cbd5e1;
    border-radius: 999px;
    transition: all .24s ease;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #0ea5e9 0%, #22d3ee 100%);
    color: #020617;
    box-shadow: 0 20px 45px rgba(14,165,233,0.22);
}
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(14,165,233,0.18), rgba(6,78,170,0.14));
    border: 1px solid rgba(56,189,248,0.18);
    border-radius: 22px;
    padding: 18px 16px;
    backdrop-filter: blur(10px);
}
div[data-testid="stMetricValue"] {font-size: 1.55rem; font-weight: 800; color: #f8fafc;}
div[data-testid="stMetricLabel"] {color: #94a3b8; font-size: 0.85rem; letter-spacing: 0.02em;}
div[data-testid="stMarkdown"] h1, div[data-testid="stMarkdown"] h2, div[data-testid="stMarkdown"] h3, div[data-testid="stMarkdown"] h4 {color: #f8fafc;}
div[data-testid="stMarkdown"] p, div[data-testid="stMarkdown"] li, div[data-testid="stMarkdown"] span {color: #cbd5e1;}
.hero-card {display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:1.25rem; background: rgba(6, 16, 38, 0.92); border: 1px solid rgba(56,189,248,0.24); border-radius:32px; padding:28px 30px; box-shadow: 0 32px 100px rgba(0,0,0,0.32);}
.hero-label {text-transform: uppercase; letter-spacing:0.30em; font-size:0.72rem; color:#38bdf8; font-weight:800; margin-bottom:0.6rem;}
.hero-heading {font-size:2.5rem; color:#f8fafc; margin:0; line-height:1.02;}
.hero-copy {color:#cbd5e1; font-size:1rem; line-height:1.7; max-width:660px; margin-top:0.6rem;}
.hero-visual {position:relative; width:150px; height:150px; min-width:150px; perspective:900px;}
.orb {position:absolute; inset:0; border-radius:50%; background: radial-gradient(circle at 32% 28%, rgba(56,189,248,0.95), rgba(14,165,233,0.6) 45%, rgba(15,23,42,0.08) 62%); box-shadow: 0 0 58px rgba(56,189,248,0.32), inset 0 0 18px rgba(255,255,255,0.18); animation: float 6s ease-in-out infinite;}
.ring {position:absolute; inset:0; border-radius:50%; border: 1px solid rgba(56,189,248,0.42);}
.ring-1 {transform: rotateX(65deg) rotateY(14deg); animation: spin 10s linear infinite;}
.ring-2 {transform: rotateX(32deg) rotateY(98deg); border-color: rgba(56,189,248,0.24); animation: spin 12s linear reverse infinite;}
.pulse {position:absolute; inset:34px; border-radius:50%; background: rgba(56,189,248,0.12); box-shadow: 0 0 42px rgba(56,189,248,0.18); animation: pulse 2.6s ease-in-out infinite;}
@keyframes float {0%,100%{transform: translateY(0px) rotate(0deg);}50%{transform: translateY(-10px) rotate(2deg);}}
@keyframes spin {0%{transform: rotateX(65deg) rotateY(14deg) rotateZ(0deg);}100%{transform: rotateX(65deg) rotateY(14deg) rotateZ(360deg);}}
@keyframes pulse {0%,100%{transform: scale(1); opacity:0.72;}50%{transform: scale(1.2); opacity:0.22;}}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Data loading                                                                #
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner="Loading air-quality dataset...")
def get_dataset() -> pd.DataFrame:
    return load_dataset()


@st.cache_data(show_spinner=False)
def get_forecast_metrics() -> dict:
    return forecaster.load_metrics()


@st.cache_data(show_spinner=False)
def get_attribution_metrics() -> dict:
    return attribution.load_metrics()


@st.cache_data(show_spinner="Running source attribution for all stations...")
def get_latest_with_attribution(df: pd.DataFrame, model_mtime: float | None) -> pd.DataFrame:
    latest = df.sort_values("timestamp").groupby("station_id", as_index=False).tail(1)
    return attribution.attribute(latest)


try:
    df = get_dataset()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

latest = df.sort_values("timestamp").groupby("station_id", as_index=False).tail(1).copy()
latest["aqi"] = latest["pm25"].apply(lambda p: pm25_to_aqi(p)[0])
latest["aqi_category"] = latest["pm25"].apply(lambda p: pm25_to_aqi(p)[1])

now_ts = df["timestamp"].max()


# --------------------------------------------------------------------------- #
# Header                                                                      #
# --------------------------------------------------------------------------- #

st.markdown("""
<div class="hero-card">
  <div>
    <div class="hero-label">AirIQ Command Center</div>
    <div class="hero-heading">Air intelligence for smart cities</div>
    <div class="hero-copy">Track pollution hotspots, forecast next-day AQI, and respond with an immersive data experience built for modern civic operations.</div>
  </div>
</div>
""", unsafe_allow_html=True)
st.caption(
    f"ET AI Hackathon 2026 · Problem 5  ·  City: **Delhi**  ·  Data as of "
    f"**{pd.Timestamp(now_ts).strftime('%d %b %Y, %H:%M')} IST**  ·  "
    f"Stations: **{latest['station_id'].nunique()}**"
)

top_a, top_b, top_c, top_d = st.columns(4)
top_a.metric("Mean city AQI (now)", f"{int(latest['aqi'].mean())}")
top_b.metric("Worst station", f"{latest.loc[latest['aqi'].idxmax(),'station_name']}",
             f"AQI {int(latest['aqi'].max())}")
top_c.metric("Cleanest station", f"{latest.loc[latest['aqi'].idxmin(),'station_name']}",
             f"AQI {int(latest['aqi'].min())}")
top_d.metric("Stations in ‘Very Poor’+", int((latest["aqi"] > 300).sum()))


tab_overview, tab_forecast, tab_sources, tab_bot, tab_about = st.tabs(
    ["🗺️ Overview", "📈 Forecast (Module A)", "🎯 Source Insights (Module B)",
     "💬 Citizen Bot (Module C)", "ℹ️ About & Metrics"]
)

# --------------------------------------------------------------------------- #
# TAB 1 — Overview map                                                        #
# --------------------------------------------------------------------------- #

with tab_overview:
    left, right = st.columns([2, 1])

    with left:
        st.markdown("#### Live AQI across Delhi")
        m = folium.Map(location=CITY_CENTER, zoom_start=10, tiles="cartodbpositron")
        for _, r in latest.iterrows():
            folium.CircleMarker(
                location=(r["lat"], r["lon"]),
                radius=10,
                color=aqi_color(int(r["aqi"])),
                fill=True,
                fill_color=aqi_color(int(r["aqi"])),
                fill_opacity=0.85,
                popup=folium.Popup(
                    f"<b>{r['station_name']}</b><br>"
                    f"Ward: {r['ward']}<br>"
                    f"PM2.5: {r['pm25']:.1f} µg/m³<br>"
                    f"AQI: <b>{int(r['aqi'])}</b> ({r['aqi_category']})",
                    max_width=260,
                ),
                tooltip=f"{r['station_name']} · AQI {int(r['aqi'])}",
            ).add_to(m)
        st_folium(m, use_container_width=True, height=520)

    with right:
        st.markdown("#### AQI category distribution")
        cat_counts = latest["aqi_category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Stations"]
        cat_order = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
        color_map = {"Good":"#009966","Satisfactory":"#88c100","Moderate":"#ffde33",
                     "Poor":"#ff9933","Very Poor":"#cc0033","Severe":"#7e0023"}
        fig = px.bar(
            cat_counts.sort_values("Category", key=lambda s: s.map({c:i for i,c in enumerate(cat_order)})),
            x="Category", y="Stations",
            color="Category", color_discrete_map=color_map,
            text="Stations",
        )
        fig.update_layout(showlegend=False, height=300, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 7-day city trend")
        recent = df[df["timestamp"] >= now_ts - pd.Timedelta(days=7)].copy()
        city_ts = recent.groupby("timestamp", as_index=False)["pm25"].mean()
        city_ts["aqi"] = city_ts["pm25"].apply(lambda p: pm25_to_aqi(p)[0])
        fig = px.line(city_ts, x="timestamp", y="aqi", labels={"aqi":"City-mean AQI"})
        fig.update_layout(height=240, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------- #
# TAB 2 — Forecast                                                            #
# --------------------------------------------------------------------------- #

with tab_forecast:
    st.markdown("### Module A — Hyperlocal 24/48/72-hour PM2.5 forecast")

    station_options = latest.sort_values("station_name")[["station_id", "station_name"]]
    labels = station_options["station_name"].tolist()
    ids    = station_options["station_id"].tolist()
    default_ix = 0
    sel_label = st.selectbox("Choose a monitoring station", labels, index=default_ix)
    sel_id = ids[labels.index(sel_label)]

    st_hist = df[df["station_id"] == sel_id].sort_values("timestamp").tail(24*7).copy()
    st_hist["aqi"] = st_hist["pm25"].apply(lambda p: pm25_to_aqi(p)[0])

    fc = forecaster.forecast_station(df, sel_id)

    col_a, col_b, col_c = st.columns(3)
    if not fc.empty:
        for horizon, col in zip([24, 48, 72], [col_a, col_b, col_c]):
            row = fc[fc["horizon_h"] == horizon]
            if not row.empty:
                pm = float(row["pm25_forecast"].iloc[0])
                aqi_val, cat = pm25_to_aqi(pm)
                col.metric(f"Forecast +{horizon}h", f"AQI {aqi_val}", cat)
    else:
        st.warning("No forecast available yet — did you run `generate_and_train.py`?")

    st.markdown("#### 7-day history + forecast horizons")
    hist_fig = go.Figure()
    hist_fig.add_trace(go.Scatter(
        x=st_hist["timestamp"], y=st_hist["pm25"],
        mode="lines", name="Observed PM2.5",
        line=dict(color="#1f77b4", width=2),
    ))
    if not fc.empty:
        fc_line = fc.sort_values("forecast_timestamp")
        anchor_ts = st_hist["timestamp"].iloc[-1]
        anchor_pm = st_hist["pm25"].iloc[-1]
        hist_fig.add_trace(go.Scatter(
            x=[anchor_ts] + list(fc_line["forecast_timestamp"]),
            y=[anchor_pm] + list(fc_line["pm25_forecast"]),
            mode="lines+markers", name="AirIQ forecast",
            line=dict(color="#e45756", width=2, dash="dash"),
            marker=dict(size=10),
        ))
    hist_fig.update_layout(
        yaxis_title="PM2.5 (µg/m³)", xaxis_title="Time",
        height=430, margin=dict(l=10,r=10,t=10,b=10),
    )
    st.plotly_chart(hist_fig, use_container_width=True)

    st.markdown("#### Model quality vs. persistence baseline")
    metrics = get_forecast_metrics()
    if metrics:
        rows = []
        for h, m in metrics.items():
            rows.append({
                "Horizon": f"+{h}h",
                "Baseline RMSE": round(m["baseline_rmse"], 2),
                "AirIQ RMSE":    round(m["model_rmse"], 2),
                "Baseline MAE":  round(m["baseline_mae"], 2),
                "AirIQ MAE":     round(m["model_mae"], 2),
                "RMSE improvement": f"{m['rmse_improvement_pct']:.1f}%",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("Train models first: `python generate_and_train.py`")

# --------------------------------------------------------------------------- #
# TAB 3 — Source attribution                                                  #
# --------------------------------------------------------------------------- #

with tab_sources:
    st.markdown("### Module B — Which sources are polluting the air, right now?")

    if not _has_attribution_model():
        st.warning("Attribution model not trained yet — run `python generate_and_train.py`.")
        attributed = pd.DataFrame()
    else:
        model_mtime = attribution.MODEL_PATH.stat().st_mtime
        try:
            attributed = get_latest_with_attribution(df, model_mtime)
        except Exception as exc:
            st.warning("Attribution model exists but inference failed. Please restart the app or retrain with `python generate_and_train.py`.")
            st.write(f"Technical details: {exc}")
            attributed = pd.DataFrame()

    if not attributed.empty:
        left, right = st.columns([2, 1])

        # City map coloured by dominant source
        with left:
            st.markdown("#### City map — dominant source per station")
            source_palette = {
                "traffic":         "#e45756",
                "industry":        "#4c78a8",
                "construction":    "#f58518",
                "biomass_burning": "#54a24b",
                "dust":            "#b279a2",
            }
            m = folium.Map(location=CITY_CENTER, zoom_start=10, tiles="cartodbpositron")
            for _, r in attributed.iterrows():
                pop = "<b>{}</b><br>PM2.5: {:.1f} µg/m³<br>Dominant source: <b>{}</b> ({:.0%})<br><hr style='margin:4px 0;'>".format(
                    r["station_name"], r["pm25"], r["dominant_source"], r["dominant_confidence"]
                )
                for s in SOURCE_CLASSES:
                    pop += f"{s.replace('_', ' ').title()}: {r[f'src_pred_{s}']:.0%}<br>"
                folium.CircleMarker(
                    location=(r["lat"], r["lon"]),
                    radius=11,
                    color=source_palette[r["dominant_source"]],
                    fill=True, fill_color=source_palette[r["dominant_source"]],
                    fill_opacity=0.9,
                    popup=folium.Popup(pop, max_width=280),
                    tooltip=f"{r['station_name']} · {r['dominant_source']}",
                ).add_to(m)

            # legend
            legend_html = "<div style='position: fixed; bottom: 30px; left: 30px; z-index:9999; background: white; padding:10px 14px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,.15); font-size:13px;'><b>Dominant source</b><br>"
            for s, c in source_palette.items():
                legend_html += f"<span style='display:inline-block;width:12px;height:12px;background:{c};margin-right:6px;border-radius:50%;'></span>{s.replace('_',' ').title()}<br>"
            legend_html += "</div>"
            m.get_root().html.add_child(folium.Element(legend_html))

            st_folium(m, use_container_width=True, height=500)

        with right:
            st.markdown("#### Drill down — per station")
            sel_label = st.selectbox(
                "Station",
                attributed.sort_values("station_name")["station_name"].tolist(),
                key="attr_station",
            )
            row = attributed[attributed["station_name"] == sel_label].iloc[0]
            shares = pd.DataFrame({
                "Source": [s.replace("_", " ").title() for s in SOURCE_CLASSES],
                "Share":  [row[f"src_pred_{s}"] for s in SOURCE_CLASSES],
            })
            pie = px.pie(shares, values="Share", names="Source", hole=0.45,
                         color="Source",
                         color_discrete_map={s.replace("_"," ").title(): c for s,c in source_palette.items()})
            pie.update_layout(height=320, margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(pie, use_container_width=True)

            st.markdown(f"""
**Enforcement recommendation for {sel_label}**
- Current PM2.5: **{row['pm25']:.1f} µg/m³** (AQI {int(pm25_to_aqi(row['pm25'])[0])})
- Dominant source: **{row['dominant_source'].replace('_',' ').title()}** ({row['dominant_confidence']:.0%})
- Suggested action: **{_action_for(row['dominant_source'])}**
            """)

        # City-wide dominant source distribution
        st.markdown("#### City-wide dominant source distribution")
        dist = attributed["dominant_source"].value_counts().reset_index()
        dist.columns = ["Source", "Stations"]
        fig = px.bar(dist, x="Source", y="Stations", color="Source",
                     color_discrete_map=source_palette, text="Stations")
        fig.update_layout(showlegend=False, height=290, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------- #
# TAB 4 — Citizen bot                                                         #
# --------------------------------------------------------------------------- #

with tab_bot:
    st.markdown("### Module C — Multilingual Citizen Advisory")
    st.caption("Ward-level advisory in 5 languages, tailored to health vulnerability.")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        sel_station = st.selectbox(
            "Your nearest monitoring station",
            latest.sort_values("station_name")["station_name"].tolist(),
            key="bot_station",
        )
    with c2:
        sel_lang = st.selectbox(
            "Language",
            options=list(advisory.LANG_LABELS.keys()),
            format_func=lambda x: advisory.LANG_LABELS[x],
        )
    with c3:
        sel_vuln = st.selectbox(
            "I am…",
            options=list(advisory.VULNERABILITY_LEVELS.keys()),
            format_func=lambda x: advisory.VULNERABILITY_LABELS["en"][x].capitalize(),
        )

    row = latest[latest["station_name"] == sel_station].iloc[0]
    fc = forecaster.forecast_station(df, row["station_id"])

    adv = advisory.build_advisory(
        current_pm25=float(row["pm25"]),
        forecast_df=fc,
        lang=sel_lang,
        vulnerability=sel_vuln,
    )

    # WhatsApp-style bubble
    st.markdown(f"""
<div style='background:#dcf8c6; padding:16px 20px; border-radius:14px; max-width:720px;
             margin-top:14px; font-size:1.05rem; line-height:1.5;'>
  <div style='font-size:0.85rem; color:#075e54; font-weight:700; margin-bottom:6px;'>
    AirIQ Citizen Bot · {advisory.LANG_LABELS[sel_lang]}
  </div>
  {adv.message}
  <div style='font-size:0.75rem; color:#666; margin-top:10px;'>
    Station: {sel_station}  ·  AQI: <b>{adv.aqi}</b>  ·  {adv.category}
  </div>
</div>
    """, unsafe_allow_html=True)

    with st.expander("📤 See advisory in all 5 languages (broadcast preview)"):
        for a in advisory.all_language_advisories(float(row["pm25"]), fc, vulnerability=sel_vuln):
            st.markdown(f"**{advisory.LANG_LABELS[a.lang]}** — {a.message}")

# --------------------------------------------------------------------------- #
# TAB 5 — About / metrics                                                     #
# --------------------------------------------------------------------------- #

with tab_about:
    st.markdown("### About AirIQ")
    st.markdown("""
**Problem 5 — Urban Air Quality Intelligence for Smart-City Intervention**

AirIQ fuses ground sensors, satellite proxies, weather, land-use and fire data
into a single AI platform that (1) forecasts PM2.5 24–72h ahead, (2) attributes
each hotspot to its dominant source, and (3) advises citizens in 5 languages —
turning passive monitoring into proactive action.
    """)
    st.markdown("#### Judging-aligned metrics")

    fm = get_forecast_metrics()
    am = get_attribution_metrics()

    left, right = st.columns(2)
    with left:
        st.markdown("**Module A — Forecast quality**")
        if fm:
            rows = [{"Horizon": f"+{h}h",
                     "Baseline RMSE": round(m["baseline_rmse"], 2),
                     "AirIQ RMSE":    round(m["model_rmse"], 2),
                     "Improvement":   f"{m['rmse_improvement_pct']:.1f}%"}
                    for h, m in fm.items()]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.info("Not trained yet.")

    with right:
        st.markdown("**Module B — Attribution quality**")
        if am:
            st.metric("Dominant-source accuracy (exact)", f"{am['dominant_source_accuracy']:.1%}")
            st.metric("Top-2 dominant-source match", f"{am.get('top2_source_accuracy', 0):.1%}")
            st.metric("Macro MAE across sources", f"{am['macro_mae']:.3f}")
            per = pd.DataFrame([
                {"Source": s.replace("_"," ").title(), "MAE": round(v, 3)}
                for s, v in am["per_source_mae"].items()
            ])
            st.dataframe(per, hide_index=True, use_container_width=True)
        else:
            st.info("Not trained yet.")

    st.markdown("#### Architecture")
    st.code(open("docs/ARCHITECTURE.md").read() if _has_docs() else "See docs/ARCHITECTURE.md",
            language="markdown")
