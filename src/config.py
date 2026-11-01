"""Project-wide settings: locations, season definition, file paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures"
REPORTS = ROOT / "reports"

# One representative town per province (provincial capital or main town).
# Point rainfall is a first pass; phase 2 moves to gridded CHIRPS by district.
STATIONS = {
    "Harare":     {"lat": -17.83, "lon": 31.05, "province": "Harare"},
    "Bulawayo":   {"lat": -20.15, "lon": 28.58, "province": "Bulawayo"},
    "Mutare":     {"lat": -18.97, "lon": 32.67, "province": "Manicaland"},
    "Marondera":  {"lat": -18.19, "lon": 31.55, "province": "Mashonaland East"},
    "Bindura":    {"lat": -17.30, "lon": 31.33, "province": "Mashonaland Central"},
    "Chinhoyi":   {"lat": -17.36, "lon": 30.20, "province": "Mashonaland West"},
    "Gweru":      {"lat": -19.45, "lon": 29.82, "province": "Midlands"},
    "Masvingo":   {"lat": -20.07, "lon": 30.83, "province": "Masvingo"},
    "Lupane":     {"lat": -18.93, "lon": 27.80, "province": "Matabeleland North"},
    "Gwanda":     {"lat": -20.94, "lon": 29.01, "province": "Matabeleland South"},
}

# Zimbabwe's main rainy season runs October to March.
# A season is labelled by the year it starts: 2015 means the 2015/16 season.
SEASON_MONTHS = [10, 11, 12, 1, 2, 3]
EARLY_MONTHS = [10, 11, 12]   # Oct-Dec
LATE_MONTHS = [1, 2, 3]       # Jan-Mar (the part SARCOF flags as driest in 2026/27)

FIRST_SEASON = 1981           # start of the satellite era
BASELINE = (1991, 2020)       # WMO standard climate normal, by season start year

# ENSO thresholds on the Oceanic Nino Index (ONI, degrees C)
EL_NINO = 0.5
LA_NINA = -0.5
STRONG = 1.5

# Labels used in charts and reports
KEY_EL_NINO_SEASONS = {1991: "1991/92", 2015: "2015/16", 2023: "2023/24"}

COLORS = {
    "el_nino": "#e34948",   # warm pole (dry for Zimbabwe)
    "la_nina": "#2a78d6",   # cool pole (wet for Zimbabwe)
    "neutral": "#a3a29c",
    "surface": "#fcfcfb",
    "text": "#0b0b0b",
    "text_muted": "#52514e",
    "grid": "#e4e3df",
}


def season_label(start_year: int) -> str:
    return f"{start_year}/{str(start_year + 1)[-2:]}"
