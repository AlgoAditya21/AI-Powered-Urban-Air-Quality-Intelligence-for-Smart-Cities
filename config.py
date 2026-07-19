"""Central configuration: city bounding box, stations, source classes, feature names.

Kept small and importable everywhere. No side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# ---------- Paths ----------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
ARTIFACTS_DIR = ROOT / "artifacts"
DATA_DIR.mkdir(exist_ok=True)
ARTIFACTS_DIR.mkdir(exist_ok=True)

# ---------- City ----------
CITY_NAME = "Delhi"
# Bounding box roughly covering NCT of Delhi
BBOX = {
    "lat_min": 28.40,
    "lat_max": 28.90,
    "lon_min": 76.85,
    "lon_max": 77.35,
}
CITY_CENTER = (28.6139, 77.2090)

# ---------- Grid ----------
# 1 km grid (approx). 0.009 deg ~= 1 km in lat.
GRID_STEP_DEG = 0.02  # ~2 km cells to keep the demo snappy


# ---------- Stations (approximate real CAAQMS locations) ----------
@dataclass(frozen=True)
class Station:
    station_id: str
    name: str
    lat: float
    lon: float
    ward: str


STATIONS: list[Station] = [
    Station("DL001", "Anand Vihar", 28.6469, 77.3159, "East Delhi"),
    Station("DL002", "ITO", 28.6289, 77.2426, "Central Delhi"),
    Station("DL003", "R K Puram", 28.5628, 77.1855, "South West Delhi"),
    Station("DL004", "Punjabi Bagh", 28.6743, 77.1315, "West Delhi"),
    Station("DL005", "Mandir Marg", 28.6362, 77.2010, "New Delhi"),
    Station("DL006", "Shadipur", 28.6516, 77.1470, "West Delhi"),
    Station("DL007", "Dwarka Sector 8", 28.5710, 77.0710, "South West Delhi"),
    Station("DL008", "Rohini", 28.7325, 77.1195, "North West Delhi"),
    Station("DL009", "Wazirpur", 28.6996, 77.1652, "North West Delhi"),
    Station("DL010", "Bawana", 28.7761, 77.0341, "North West Delhi"),
    Station("DL011", "Narela", 28.8229, 77.1015, "North West Delhi"),
    Station("DL012", "Ashok Vihar", 28.6959, 77.1817, "North Delhi"),
    Station("DL013", "Sonia Vihar", 28.7108, 77.2493, "North East Delhi"),
    Station("DL014", "Jahangirpuri", 28.7328, 77.1707, "North West Delhi"),
    Station("DL015", "Vivek Vihar", 28.6716, 77.3155, "East Delhi"),
    Station("DL016", "Nehru Nagar", 28.5679, 77.2506, "South East Delhi"),
    Station("DL017", "Sirifort", 28.5504, 77.2159, "South Delhi"),
    Station("DL018", "Okhla Phase 2", 28.5305, 77.2723, "South East Delhi"),
    Station("DL019", "Alipur", 28.8158, 77.1500, "North Delhi"),
    Station("DL020", "IHBAS Dilshad Garden", 28.6811, 77.3025, "East Delhi"),
    Station("DL021", "Pusa", 28.6386, 77.1571, "West Delhi"),
    Station("DL022", "Lodhi Road", 28.5918, 77.2273, "New Delhi"),
    Station("DL023", "North Campus DU", 28.6867, 77.2100, "North Delhi"),
    Station("DL024", "Aya Nagar", 28.4703, 77.1099, "South Delhi"),
    Station("DL025", "Patparganj", 28.6371, 77.2879, "East Delhi"),
    Station("DL026", "Dr. Karni Singh Shooting Range", 28.4989, 77.2647, "South Delhi"),
    Station("DL027", "Mundka", 28.6845, 77.0328, "West Delhi"),
    Station("DL028", "Najafgarh", 28.5701, 76.9339, "South West Delhi"),
    Station("DL029", "Sri Aurobindo Marg", 28.5314, 77.1899, "South Delhi"),
    Station("DL030", "Chandni Chowk", 28.6564, 77.2299, "Central Delhi"),
]

# ---------- Source classes for Module B ----------
SOURCE_CLASSES: list[str] = [
    "traffic",
    "industry",
    "construction",
    "biomass_burning",
    "dust",
]

# ---------- Feature schema ----------
LAG_HOURS = [1, 3, 6, 24]
ROLLING_HOURS = [3, 24]

WEATHER_FEATURES = [
    "temp_c",
    "humidity_pct",
    "wind_speed_ms",
    "wind_dir_deg",
    "boundary_layer_m",
    "precip_mm",
]

SATELLITE_FEATURES = [
    "no2_column",       # Sentinel-5P tropospheric NO2 (mock in synthetic)
    "aod_550",          # aerosol optical depth (mock)
]

CONTEXT_FEATURES = [
    "traffic_density",
    "industrial_poi_count",
    "construction_permits",
    "upwind_fire_count_50km",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "month",
]

TARGET = "pm25"

# ---------- AQI breakpoints (Indian NAAQS PM2.5) ----------
# (low_conc, high_conc, low_aqi, high_aqi, category)
AQI_BREAKPOINTS_PM25 = [
    (0,   30,  0,   50,  "Good"),
    (31,  60,  51,  100, "Satisfactory"),
    (61,  90,  101, 200, "Moderate"),
    (91,  120, 201, 300, "Poor"),
    (121, 250, 301, 400, "Very Poor"),
    (251, 500, 401, 500, "Severe"),
]


def pm25_to_aqi(pm25: float) -> tuple[int, str]:
    """Convert PM2.5 concentration (µg/m³) to Indian AQI and category."""
    if pm25 is None or pm25 < 0:
        return 0, "Unknown"
    pm25 = float(pm25)
    for c_lo, c_hi, aqi_lo, aqi_hi, cat in AQI_BREAKPOINTS_PM25:
        if pm25 <= c_hi:
            aqi = (aqi_hi - aqi_lo) / (c_hi - c_lo) * (pm25 - c_lo) + aqi_lo
            return int(round(aqi)), cat
    return 500, "Severe"


def aqi_color(aqi: int) -> str:
    if aqi <= 50:   return "#009966"
    if aqi <= 100:  return "#88c100"
    if aqi <= 200:  return "#ffde33"
    if aqi <= 300:  return "#ff9933"
    if aqi <= 400:  return "#cc0033"
    return "#7e0023"
