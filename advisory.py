"""Module C — Multilingual Citizen Advisory Bot.

Deterministic template-based advisory in English, Hindi, Tamil, Kannada, Bengali.
No LLM required for the demo (LLM optional via GOOGLE_API_KEY).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config import pm25_to_aqi

# --------------------------------------------------------------------------- #
# Vulnerability profiles                                                      #
# --------------------------------------------------------------------------- #

VULNERABILITY_LEVELS = {
    "general":         1.0,
    "elderly":         1.6,
    "child":           1.5,
    "asthmatic":       2.0,
    "pregnant":        1.6,
    "outdoor_worker":  1.8,
    "heart_disease":   1.9,
}


# --------------------------------------------------------------------------- #
# Advisory templates                                                          #
# --------------------------------------------------------------------------- #

# Each key: (category, vulnerability_class), value: template
# {aqi}, {category}, {station}, {peak_hour} placeholders supported.

_TEMPLATES = {
    "en": {
        "Good":         "Air is good (AQI {aqi}). All outdoor activities are safe.",
        "Satisfactory": "Air is satisfactory (AQI {aqi}). Sensitive individuals should watch for mild symptoms.",
        "Moderate":     "Air is moderate (AQI {aqi}). Limit prolonged outdoor exertion; keep windows closed 5–10 PM.",
        "Poor":         "Air is poor (AQI {aqi}). Wear an N95 mask outdoors and avoid outdoor exercise.",
        "Very Poor":    "Air is very poor (AQI {aqi}). Stay indoors, run an air purifier, mask outdoors, cancel outdoor sports.",
        "Severe":       "Air is severe (AQI {aqi}). Emergency: stay indoors, use N95, seek medical help if breathless.",
        "vuln_suffix":  " Extra caution for you as {vuln} — reduce exposure now, forecast peaks around {peak_hour}:00.",
    },
    "hi": {
        "Good":         "हवा अच्छी है (AQI {aqi})। सभी बाहरी गतिविधियाँ सुरक्षित हैं।",
        "Satisfactory": "हवा संतोषजनक है (AQI {aqi})। संवेदनशील लोगों को हल्के लक्षणों पर ध्यान देना चाहिए।",
        "Moderate":     "हवा मध्यम है (AQI {aqi})। लंबे समय तक बाहर व्यायाम न करें; शाम 5–10 बजे खिड़कियाँ बंद रखें।",
        "Poor":         "हवा खराब है (AQI {aqi})। बाहर N95 मास्क पहनें और बाहर व्यायाम न करें।",
        "Very Poor":    "हवा बहुत खराब है (AQI {aqi})। घर के अंदर रहें, एयर प्यूरीफायर चलाएँ, बाहर मास्क पहनें, बाहरी खेल रद्द करें।",
        "Severe":       "हवा गंभीर है (AQI {aqi})। आपातकाल: घर पर रहें, N95 उपयोग करें, साँस लेने में दिक्कत हो तो डॉक्टर से मिलें।",
        "vuln_suffix":  " {vuln} होने के कारण विशेष सावधानी बरतें — पूर्वानुमान के अनुसार {peak_hour}:00 बजे प्रदूषण चरम पर होगा।",
    },
    "ta": {
        "Good":         "காற்று நல்லது (AQI {aqi}). அனைத்து வெளிப்புற செயல்பாடுகளும் பாதுகாப்பானவை.",
        "Satisfactory": "காற்று திருப்திகரமானது (AQI {aqi}). உணர்திறன் உள்ளவர்கள் லேசான அறிகுறிகளைக் கவனிக்கவும்.",
        "Moderate":     "காற்று மிதமானது (AQI {aqi}). நீண்ட நேர வெளிப்புற உடற்பயிற்சியைக் குறைக்கவும்; மாலை 5–10 மணிக்கு ஜன்னல்களை மூடவும்.",
        "Poor":         "காற்று மோசம் (AQI {aqi}). வெளியில் N95 முகக்கவசம் அணியுங்கள்; வெளிப்புற உடற்பயிற்சியைத் தவிர்க்கவும்.",
        "Very Poor":    "காற்று மிக மோசம் (AQI {aqi}). வீட்டிற்குள் இருங்கள், காற்றுத்தூய்மையாக்கியை இயக்குங்கள், வெளியில் முகக்கவசம், வெளிப்புற விளையாட்டுகளை ரத்து செய்யவும்.",
        "Severe":       "காற்று கடுமையானது (AQI {aqi}). அவசரம்: வீட்டில் இருங்கள், N95 அணியுங்கள், மூச்சுத்திணறல் இருந்தால் மருத்துவரை அணுகவும்.",
        "vuln_suffix":  " {vuln} என்பதால் கூடுதல் கவனம் தேவை — {peak_hour}:00 மணியில் மாசு உச்சம் அடையும்.",
    },
    "kn": {
        "Good":         "ಗಾಳಿ ಚೆನ್ನಾಗಿದೆ (AQI {aqi}). ಎಲ್ಲಾ ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳು ಸುರಕ್ಷಿತ.",
        "Satisfactory": "ಗಾಳಿ ತೃಪ್ತಿಕರವಾಗಿದೆ (AQI {aqi}). ಸೂಕ್ಷ್ಮ ವ್ಯಕ್ತಿಗಳು ಸಣ್ಣ ಲಕ್ಷಣಗಳ ಬಗ್ಗೆ ಎಚ್ಚರವಿರಲಿ.",
        "Moderate":     "ಗಾಳಿ ಮಧ್ಯಮ (AQI {aqi}). ದೀರ್ಘಕಾಲದ ಹೊರಾಂಗಣ ವ್ಯಾಯಾಮ ಸೀಮಿತಗೊಳಿಸಿ; ಸಂಜೆ 5–10 ಗಂಟೆಗೆ ಕಿಟಕಿಗಳನ್ನು ಮುಚ್ಚಿ.",
        "Poor":         "ಗಾಳಿ ಕಳಪೆ (AQI {aqi}). ಹೊರಗಡೆ N95 ಮಾಸ್ಕ್ ಧರಿಸಿ; ಹೊರಾಂಗಣ ವ್ಯಾಯಾಮ ತಪ್ಪಿಸಿ.",
        "Very Poor":    "ಗಾಳಿ ಬಹಳ ಕಳಪೆ (AQI {aqi}). ಒಳಗಡೆ ಇರಿ, ಏರ್ ಪ್ಯೂರಿಫೈಯರ್ ಚಲಾಯಿಸಿ, ಹೊರಗಡೆ ಮಾಸ್ಕ್ ಧರಿಸಿ.",
        "Severe":       "ಗಾಳಿ ಗಂಭೀರ (AQI {aqi}). ತುರ್ತು: ಮನೆಯಲ್ಲಿ ಇರಿ, N95 ಬಳಸಿ, ಉಸಿರಾಟ ಕಷ್ಟ ಆದರೆ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "vuln_suffix":  " {vuln} ಆಗಿರುವುದರಿಂದ ಹೆಚ್ಚಿನ ಜಾಗರೂಕತೆ ಇರಲಿ — {peak_hour}:00 ರ ಸಮಯಕ್ಕೆ ಮಾಲಿನ್ಯ ಗರಿಷ್ಠ.",
    },
    "bn": {
        "Good":         "বাতাস ভালো (AQI {aqi})। সব বাইরের কাজ নিরাপদ।",
        "Satisfactory": "বাতাস সন্তোষজনক (AQI {aqi})। সংবেদনশীল ব্যক্তিরা হালকা লক্ষণে সতর্ক থাকুন।",
        "Moderate":     "বাতাস মাঝারি (AQI {aqi})। দীর্ঘসময় বাইরে ব্যায়াম কমান; সন্ধ্যা ৫–১০টায় জানালা বন্ধ রাখুন।",
        "Poor":         "বাতাস খারাপ (AQI {aqi})। বাইরে N95 মাস্ক পরুন; বাইরের ব্যায়াম এড়িয়ে চলুন।",
        "Very Poor":    "বাতাস অতি খারাপ (AQI {aqi})। ঘরে থাকুন, এয়ার পিউরিফায়ার চালান, বাইরে মাস্ক পরুন।",
        "Severe":       "বাতাস মারাত্মক (AQI {aqi})। জরুরি: ঘরে থাকুন, N95 ব্যবহার করুন, শ্বাসকষ্ট হলে চিকিৎসকের পরামর্শ নিন।",
        "vuln_suffix":  " {vuln} হওয়ায় অতিরিক্ত সতর্ক থাকুন — {peak_hour}:00-এ দূষণ সর্বোচ্চ পৌঁছাবে।",
    },
}

VULNERABILITY_LABELS = {
    "en": {"general": "a general adult", "elderly": "an elderly person", "child": "a child",
           "asthmatic": "an asthmatic", "pregnant": "pregnant", "outdoor_worker": "an outdoor worker",
           "heart_disease": "someone with heart disease"},
    "hi": {"general": "एक सामान्य वयस्क", "elderly": "एक बुज़ुर्ग", "child": "एक बच्चा",
           "asthmatic": "अस्थमा रोगी", "pregnant": "गर्भवती", "outdoor_worker": "बाहरी कामगार",
           "heart_disease": "हृदय रोगी"},
    "ta": {"general": "பொது வயதுவந்தவர்", "elderly": "வயதானவர்", "child": "குழந்தை",
           "asthmatic": "ஆஸ்துமா நோயாளி", "pregnant": "கர்ப்பிணி", "outdoor_worker": "வெளிப்புற தொழிலாளி",
           "heart_disease": "இதய நோயாளி"},
    "kn": {"general": "ಸಾಮಾನ್ಯ ವಯಸ್ಕ", "elderly": "ವೃದ್ಧ", "child": "ಮಗು",
           "asthmatic": "ಆಸ್ತಮಾ ರೋಗಿ", "pregnant": "ಗರ್ಭಿಣಿ", "outdoor_worker": "ಹೊರಾಂಗಣ ಕಾರ್ಮಿಕ",
           "heart_disease": "ಹೃದಯ ರೋಗಿ"},
    "bn": {"general": "সাধারণ প্রাপ্তবয়স্ক", "elderly": "প্রবীণ", "child": "শিশু",
           "asthmatic": "অ্যাজমা রোগী", "pregnant": "গর্ভবতী", "outdoor_worker": "বাইরের শ্রমিক",
           "heart_disease": "হৃদরোগী"},
}

LANG_LABELS = {
    "en": "English",
    "hi": "हिन्दी (Hindi)",
    "ta": "தமிழ் (Tamil)",
    "kn": "ಕನ್ನಡ (Kannada)",
    "bn": "বাংলা (Bengali)",
}


@dataclass
class Advisory:
    lang: str
    category: str
    aqi: int
    message: str


def _bumped_category(aqi: int, vuln_multiplier: float) -> tuple[int, str]:
    """Effectively raise the perceived AQI for vulnerable groups."""
    effective_aqi = int(min(500, aqi * vuln_multiplier))
    # convert back to a category using thresholds
    if effective_aqi <= 50:   return effective_aqi, "Good"
    if effective_aqi <= 100:  return effective_aqi, "Satisfactory"
    if effective_aqi <= 200:  return effective_aqi, "Moderate"
    if effective_aqi <= 300:  return effective_aqi, "Poor"
    if effective_aqi <= 400:  return effective_aqi, "Very Poor"
    return effective_aqi, "Severe"


def build_advisory(
    current_pm25: float,
    forecast_df: pd.DataFrame | None,
    lang: str = "en",
    vulnerability: str = "general",
) -> Advisory:
    """Produce a language-appropriate advisory.

    forecast_df: output of forecaster.forecast_station() — used to pick peak hour.
    """
    lang = lang if lang in _TEMPLATES else "en"
    vulnerability = vulnerability if vulnerability in VULNERABILITY_LEVELS else "general"

    base_aqi, _ = pm25_to_aqi(current_pm25)
    vuln_mult = VULNERABILITY_LEVELS[vulnerability]
    effective_aqi, category = _bumped_category(base_aqi, vuln_mult)

    peak_hour = 20  # default evening peak
    if forecast_df is not None and not forecast_df.empty:
        peak_row = forecast_df.loc[forecast_df["pm25_forecast"].idxmax()]
        peak_hour = int(pd.Timestamp(peak_row["forecast_timestamp"]).hour)

    tmpl = _TEMPLATES[lang][category]
    msg = tmpl.format(aqi=base_aqi, category=category)

    if vulnerability != "general":
        vuln_word = VULNERABILITY_LABELS[lang][vulnerability]
        msg += _TEMPLATES[lang]["vuln_suffix"].format(vuln=vuln_word, peak_hour=peak_hour)

    return Advisory(lang=lang, category=category, aqi=base_aqi, message=msg)


def all_language_advisories(
    current_pm25: float,
    forecast_df: pd.DataFrame | None,
    vulnerability: str = "general",
) -> list[Advisory]:
    return [
        build_advisory(current_pm25, forecast_df, lang=code, vulnerability=vulnerability)
        for code in _TEMPLATES.keys()
    ]
