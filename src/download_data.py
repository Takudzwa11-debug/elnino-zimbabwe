"""Download the raw data. Run from the project root:  python -m src.download_data

Sources (all free, no account needed):
  * Oceanic Nino Index (ONI)       - NOAA Climate Prediction Center
  * Daily rainfall, 10 towns       - Open-Meteo historical API (ERA5 reanalysis)
  * Cereal yield and production    - World Bank Open Data (sourced from FAO)

Files that already exist are skipped; pass --force to download again.
"""
import argparse
import time
from datetime import date, timedelta

import pandas as pd
import requests

from src.config import FIRST_SEASON, RAW, STATIONS

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
WORLD_BANK_URL = "https://api.worldbank.org/v2/country/ZWE/indicator/{code}"
WB_INDICATORS = {
    "AG.YLD.CREL.KG": "cereal_yield_kg_per_ha",
    "AG.PRD.CREL.MT": "cereal_production_t",
}


def get(url, params=None, tries=4):
    """GET with a polite retry on rate limits and timeouts."""
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, params=params, timeout=90)
            if r.status_code == 429:
                raise requests.HTTPError("rate limited (429)")
            r.raise_for_status()
            return r
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as err:
            if attempt == tries:
                raise
            wait = 10 * attempt
            print(f"    {err}; retrying in {wait}s")
            time.sleep(wait)


def download_oni(force=False):
    out = RAW / "oni.ascii.txt"
    if out.exists() and not force:
        print(f"ONI: already have {out.name}")
        return
    print("ONI: downloading from NOAA CPC")
    out.write_text(get(ONI_URL).text)


def download_rainfall(force=False):
    folder = RAW / "rainfall"
    folder.mkdir(parents=True, exist_ok=True)
    # The archive lags real time by a few days.
    end = (date.today() - timedelta(days=7)).isoformat()
    for name, s in STATIONS.items():
        out = folder / f"{name.lower()}.csv"
        if out.exists() and not force:
            print(f"Rainfall: already have {out.name}")
            continue
        print(f"Rainfall: downloading {name} ({s['province']})")
        params = {
            "latitude": s["lat"],
            "longitude": s["lon"],
            "start_date": f"{FIRST_SEASON}-10-01",
            "end_date": end,
            "daily": "precipitation_sum",
            "timezone": "Africa/Harare",
        }
        js = get(OPEN_METEO_URL, params).json()
        df = pd.DataFrame({
            "date": js["daily"]["time"],
            "precip_mm": js["daily"]["precipitation_sum"],
        })
        df.to_csv(out, index=False)
        time.sleep(2)  # be gentle with the free API


def download_cereal(force=False):
    out = RAW / "worldbank_cereal_zwe.csv"
    if out.exists() and not force:
        print(f"Cereal: already have {out.name}")
        return
    frames = []
    for code, col in WB_INDICATORS.items():
        print(f"Cereal: downloading {code} from World Bank")
        js = get(WORLD_BANK_URL.format(code=code),
                 {"format": "json", "per_page": 200}).json()
        rows = js[1] if len(js) > 1 and js[1] else []
        frames.append(pd.DataFrame(
            [{"year": int(r["date"]), col: r["value"]} for r in rows]
        ).set_index("year"))
    pd.concat(frames, axis=1).sort_index().to_csv(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--force", action="store_true", help="re-download existing files")
    args = p.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    download_oni(args.force)
    download_rainfall(args.force)
    download_cereal(args.force)
    print("Done. Raw files are in data/raw/")


if __name__ == "__main__":
    main()
