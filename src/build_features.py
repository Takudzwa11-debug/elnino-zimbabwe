"""Turn raw downloads into tidy seasonal tables. Run:  python -m src.build_features

Outputs (data/processed/):
  oni_long.csv        every 3-month ONI value with a date, for plotting
  season_station.csv  one row per season x town: rainfall totals, anomalies, ENSO phase
  season_national.csv one row per season: average across towns + cereal harvest that followed
"""
import pandas as pd

from src.config import (BASELINE, EARLY_MONTHS, EL_NINO, LA_NINA, LATE_MONTHS,
                        PROCESSED, RAW, SEASON_MONTHS, STATIONS, STRONG)

# CPC labels each 3-month season by its middle month; YR is that month's year.
SEASON_MID_MONTH = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
                    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


def load_oni():
    oni = pd.read_csv(RAW / "oni.ascii.txt", sep=r"\s+")
    oni.columns = [c.upper() for c in oni.columns]
    oni = oni.rename(columns={"SEAS": "seas", "YR": "yr", "ANOM": "oni"})
    oni["date"] = pd.to_datetime(dict(year=oni["yr"],
                                      month=oni["seas"].map(SEASON_MID_MONTH), day=15))
    return oni[["seas", "yr", "date", "oni"]].sort_values("date")


def seasonal_oni(oni):
    """ONI values that matter for a rainy season starting in October of year Y.

    oni_aso: Aug-Oct of Y   -> known in early November, so usable as a forecast input
    oni_djf: Dec(Y)-Feb(Y+1) -> the usual peak of an El Nino; describes the season
    """
    piv = oni.pivot(index="yr", columns="seas", values="oni")
    out = pd.DataFrame({"oni_aso": piv["ASO"]})
    out["oni_djf"] = piv["DJF"].shift(-1)   # DJF row of year Y+1
    out.index.name = "season"
    return out


def enso_phase(v):
    if pd.isna(v):
        return None
    if v >= STRONG:
        return "Strong El Nino"
    if v >= EL_NINO:
        return "El Nino"
    if v <= LA_NINA:
        return "La Nina"
    return "Neutral"


def load_rainfall():
    frames = []
    for name in STATIONS:
        f = RAW / "rainfall" / f"{name.lower()}.csv"
        df = pd.read_csv(f, parse_dates=["date"])
        df["station"] = name
        frames.append(df)
    df = pd.concat(frames)
    df = df[df["date"].dt.month.isin(SEASON_MONTHS)].copy()
    m = df["date"].dt.month
    df["season"] = df["date"].dt.year.where(m >= 10, df["date"].dt.year - 1)
    df["part"] = m.map(lambda x: "early" if x in EARLY_MONTHS else "late")
    return df


def seasonal_rainfall(df):
    g = df.groupby(["station", "season"])
    out = pd.DataFrame({
        "rain_mm": g["precip_mm"].sum(min_count=1),
        "days_with_data": g["precip_mm"].count(),
    })
    parts = df.pivot_table(index=["station", "season"], columns="part",
                           values="precip_mm", aggfunc="sum")
    out["rain_ond_mm"] = parts.get("early")
    out["rain_jfm_mm"] = parts.get("late")
    out = out.reset_index()
    # Keep complete seasons only (Oct-Mar is 182 or 183 days).
    out = out[out["days_with_data"] >= 180].drop(columns="days_with_data")
    return out


def add_anomalies(df):
    base = df[df["season"].between(*BASELINE)]
    clim = base.groupby("station").agg(
        clim_mean=("rain_mm", "mean"), clim_sd=("rain_mm", "std"),
        tercile_low=("rain_mm", lambda s: s.quantile(1 / 3)),
        tercile_high=("rain_mm", lambda s: s.quantile(2 / 3)),
        clim_jfm=("rain_jfm_mm", "mean"), clim_ond=("rain_ond_mm", "mean"))
    df = df.merge(clim, on="station")
    df["anom_pct"] = 100 * (df["rain_mm"] / df["clim_mean"] - 1)
    df["anom_z"] = (df["rain_mm"] - df["clim_mean"]) / df["clim_sd"]
    df["anom_jfm_pct"] = 100 * (df["rain_jfm_mm"] / df["clim_jfm"] - 1)
    df["anom_ond_pct"] = 100 * (df["rain_ond_mm"] / df["clim_ond"] - 1)
    df["below_normal"] = (df["rain_mm"] < df["tercile_low"]).astype(int)
    df["category"] = df.apply(
        lambda r: "Below normal" if r.rain_mm < r.tercile_low
        else ("Above normal" if r.rain_mm > r.tercile_high else "Normal"), axis=1)
    return df.drop(columns=["clim_jfm", "clim_ond"])


def load_cereal():
    c = pd.read_csv(RAW / "worldbank_cereal_zwe.csv").dropna(how="all", subset=[
        "cereal_yield_kg_per_ha", "cereal_production_t"]).sort_values("year")
    # Compare each harvest with the average of the five harvests before it,
    # which removes slow changes (land reform, input programmes) from the signal.
    for col, new in [("cereal_yield_kg_per_ha", "yield_vs_prev5_pct"),
                     ("cereal_production_t", "production_vs_prev5_pct")]:
        prev5 = c[col].shift(1).rolling(5, min_periods=3).mean()
        c[new] = 100 * (c[col] / prev5 - 1)
    # The harvest in year Y+1 comes from the rains of season Y.
    c["season"] = c["year"] - 1
    return c.rename(columns={"year": "harvest_year"})


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    oni = load_oni()
    oni.to_csv(PROCESSED / "oni_long.csv", index=False)
    s_oni = seasonal_oni(oni)
    s_oni["phase"] = s_oni["oni_djf"].map(enso_phase)

    rain = add_anomalies(seasonal_rainfall(load_rainfall()))
    station = rain.merge(s_oni, left_on="season", right_index=True, how="left")
    station["province"] = station["station"].map(lambda s: STATIONS[s]["province"])
    station = station.sort_values(["season", "station"])
    station.to_csv(PROCESSED / "season_station.csv", index=False)

    national = station.groupby("season").agg(
        rain_mm=("rain_mm", "mean"), anom_pct=("anom_pct", "mean"),
        anom_jfm_pct=("anom_jfm_pct", "mean"), anom_ond_pct=("anom_ond_pct", "mean"),
        share_towns_below_normal=("below_normal", "mean"))
    national = national.join(s_oni)
    national = national.join(load_cereal().set_index("season"), how="left")
    national.to_csv(PROCESSED / "season_national.csv")

    print(f"Seasons: {station.season.min()}-{station.season.max()} "
          f"({station.season.nunique()} complete), towns: {station.station.nunique()}")
    print(national["phase"].value_counts().to_string())


if __name__ == "__main__":
    main()
