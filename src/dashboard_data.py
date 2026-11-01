"""Data and model helpers for the dashboard (pure pandas/sklearn, no Streamlit),
so they can be tested on their own."""
import numpy as np
import pandas as pd
from scipy import stats

from src.build_features import seasonal_oni
from src.config import PROCESSED, STATIONS
from src.model import FEATURES, make_model

PHASE_ORDER = ["La Nina", "Neutral", "El Nino", "Strong El Nino"]
PHASE_LABEL = {"La Nina": "La Niña", "Neutral": "Neutral",
               "El Nino": "El Niño", "Strong El Nino": "Strong El Niño"}


def load_all():
    oni = pd.read_csv(PROCESSED / "oni_long.csv", parse_dates=["date"])
    station = pd.read_csv(PROCESSED / "season_station.csv")
    station["lat"] = station["station"].map(lambda s: STATIONS[s]["lat"])
    station["lon"] = station["station"].map(lambda s: STATIONS[s]["lon"])
    station["season_label"] = station["season"].map(lambda y: f"{y}/{str(y + 1)[-2:]}")
    station["phase_label"] = station["phase"].map(PHASE_LABEL)
    nat = pd.read_csv(PROCESSED / "season_national.csv")
    nat["season_label"] = nat["season"].map(lambda y: f"{y}/{str(y + 1)[-2:]}")
    nat["phase_label"] = nat["phase"].map(PHASE_LABEL)
    return oni, station, nat


def latest_oni(oni):
    """Value to use for the coming season: official Aug-Oct if published, else newest."""
    last = oni.iloc[-1]
    target = last["date"].year if last["date"].month >= 8 else last["date"].year - 1
    s = seasonal_oni(oni).dropna(subset=["oni_aso"])
    if target in s.index:
        return {"value": float(s.loc[target, "oni_aso"]), "label": f"ASO {target}",
                "official": True, "target": int(target)}
    return {"value": float(last["oni"]), "label": f"{last['seas']} {last['yr']}",
            "official": False, "target": int(target)}


def train_model(station):
    df = station.dropna(subset=["oni_aso"])
    return make_model().fit(df[FEATURES], df["below_normal"])


def outlook(model, oni_value):
    df = pd.DataFrame({"station": list(STATIONS), "oni_aso": oni_value})
    df["province"] = df["station"].map(lambda s: STATIONS[s]["province"])
    df["lat"] = df["station"].map(lambda s: STATIONS[s]["lat"])
    df["lon"] = df["station"].map(lambda s: STATIONS[s]["lon"])
    df["p_below_normal"] = 100 * model.predict_proba(df[FEATURES])[:, 1]
    return df.sort_values("p_below_normal", ascending=False).reset_index(drop=True)


def analog_seasons(station, oni_value, window=0.4):
    """Past seasons that started with a similar Aug-Oct ONI, and what happened."""
    df = station.dropna(subset=["oni_aso"])
    near = df[(df["oni_aso"] - oni_value).abs() <= window]
    if near.empty:
        return pd.DataFrame(columns=["Season", "Aug–Oct ONI", "Rainfall vs normal",
                                     "Towns below normal"])
    g = near.groupby("season_label").agg(
        oni=("oni_aso", "first"), anom=("anom_pct", "mean"), below=("below_normal", "mean"))
    g = g.sort_values("oni", ascending=False).reset_index()
    return pd.DataFrame({
        "Season": g["season_label"],
        "Aug–Oct ONI": g["oni"].map(lambda v: f"{v:+.1f} °C"),
        "Rainfall vs normal": g["anom"].map(lambda v: f"{v:+.0f}%"),
        "Towns below normal": g["below"].map(lambda v: f"{v:.0%}"),
    })


def phase_summary(station):
    df = station.dropna(subset=["phase"])
    g = df.groupby("phase").agg(
        town_seasons=("anom_pct", "size"), mean_anom=("anom_pct", "mean"),
        share_below=("below_normal", "mean"),
        ond=("anom_ond_pct", "mean"), jfm=("anom_jfm_pct", "mean")).reindex(PHASE_ORDER)
    g.index = [PHASE_LABEL[p] for p in g.index]
    return g


def town_correlations(station):
    rows = []
    for name, g in station.dropna(subset=["oni_djf"]).groupby("station"):
        rows.append({"station": name, "province": STATIONS[name]["province"],
                     "r_season": stats.pearsonr(g["oni_djf"], g["anom_pct"])[0],
                     "r_jfm": stats.pearsonr(g["oni_djf"], g["anom_jfm_pct"])[0]})
    return pd.DataFrame(rows).sort_values("r_season")


def town_stats(station, name):
    g = station[station["station"] == name].dropna(subset=["phase"])
    strong = g[g["phase"] == "Strong El Nino"]
    el = g[g["phase"].isin(["El Nino", "Strong El Nino"])]
    return {
        "normal_mm": float(g["clim_mean"].iloc[0]),
        "r": float(stats.pearsonr(g["oni_djf"], g["anom_pct"])[0]),
        "strong_anom": float(strong["anom_pct"].mean()) if len(strong) else np.nan,
        "el_share_below": float(el["below_normal"].mean()) if len(el) else np.nan,
        "worst": g.nsmallest(1, "anom_pct")[["season_label", "anom_pct"]].iloc[0].tolist(),
    }


def harvest_fit(nat):
    d = nat.dropna(subset=["oni_djf", "yield_vs_prev5_pct"])
    res = stats.linregress(d["oni_djf"], d["yield_vs_prev5_pct"])
    return d, res
