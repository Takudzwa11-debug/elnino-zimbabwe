"""Baseline model: chance of a below-normal rainy season, by province, from the ONI.

Predictor: the Aug-Oct ONI (published early November), so the model only uses
information available before the main rains start. Target: the season's rainfall
falls in the driest third of 1991-2020 seasons at that town.

Validation: leave-one-season-out. Each season is held out in turn (all ten towns
together), so the model never sees the year it is scored on.

Run:  python -m src.model        -> reports/model_report.md, reports/forecast.csv,
                                    figures/06_forecast_below_normal.png
This is a learning baseline, not an official forecast. For decisions, use the
Meteorological Services Department and SARCOF outlooks.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer

from src.analysis import save, style
from src.build_features import seasonal_oni
from src.config import COLORS, PROCESSED, REPORTS, STATIONS, season_label

FEATURES = ["oni_aso", "station"]


def make_model():
    pre = ColumnTransformer([
        ("oni", StandardScaler(), ["oni_aso"]),
        ("town", OneHotEncoder(handle_unknown="ignore"), ["station"]),
    ])
    return make_pipeline(pre, LogisticRegression(C=1.0, max_iter=1000))


def cross_validate(df):
    probs = np.zeros(len(df))
    for train, test in LeaveOneGroupOut().split(df, groups=df["season"]):
        m = make_model().fit(df.iloc[train][FEATURES], df.iloc[train]["below_normal"])
        probs[test] = m.predict_proba(df.iloc[test][FEATURES])[:, 1]
    return probs


def main():
    style()
    st = pd.read_csv(PROCESSED / "season_station.csv").dropna(subset=["oni_aso"])
    st = st.reset_index(drop=True)
    y = st["below_normal"]

    probs = cross_validate(st)
    clim = np.full(len(st), 1 / 3)  # "no skill" forecast: always 33%
    bs, bs_clim = brier_score_loss(y, probs), brier_score_loss(y, clim)
    bss = 1 - bs / bs_clim
    auc = roc_auc_score(y, probs)
    st["p_cv"] = probs

    # Reliability check: when the model says "high chance", is it right?
    st["bucket"] = pd.cut(st["p_cv"], [0, 0.25, 0.45, 1], labels=["< 25%", "25-45%", "> 45%"])
    rel = st.groupby("bucket", observed=True).agg(
        n=("below_normal", "size"), predicted=("p_cv", "mean"), observed=("below_normal", "mean"))

    # Fit on everything and forecast the newest season with an ASO value.
    model = make_model().fit(st[FEATURES], y)
    # Forecast the rainy season that starts this year. Use its Aug-Oct ONI if NOAA has
    # published it; otherwise fall back to the newest 3-month value (it changes slowly).
    oni = pd.read_csv(PROCESSED / "oni_long.csv", parse_dates=["date"])
    s_oni = seasonal_oni(oni).dropna(subset=["oni_aso"])
    latest = oni.iloc[-1]
    target = latest["date"].year if latest["date"].month >= 8 else latest["date"].year - 1
    if target in s_oni.index:
        oni_now, oni_label = float(s_oni.loc[target, "oni_aso"]), "Aug–Oct ONI"
    else:
        oni_now = float(latest["oni"])
        oni_label = f"latest ONI, {latest['seas']} {latest['yr']}"
        print(f"  Note: Aug-Oct {target} ONI not published yet; using {latest['seas']} "
              f"{latest['yr']} ({oni_now:+.2f}). Re-run with --force once NOAA updates.")
    fc = pd.DataFrame({"station": list(STATIONS), "oni_aso": oni_now})
    fc["province"] = fc["station"].map(lambda s: STATIONS[s]["province"])
    fc["p_below_normal"] = model.predict_proba(fc[FEATURES])[:, 1]
    fc = fc.sort_values("p_below_normal", ascending=False)
    fc.to_csv(REPORTS / "forecast.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh(fc["province"], 100 * fc["p_below_normal"], color=COLORS["el_nino"], height=0.6)
    ax.axvline(100 / 3, color=COLORS["text_muted"], lw=1, ls=(0, (3, 3)))
    ax.text(100 / 3, len(fc) - 0.4, " normal odds (33%)", fontsize=8, color=COLORS["text_muted"])
    for i, v in enumerate(100 * fc["p_below_normal"]):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Chance of below-normal rainfall (%)")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"{season_label(target)} outlook from this model ({oni_label} = {oni_now:+.1f}°C)")
    save(fig, "06_forecast_below_normal.png",
         "Logistic regression on NOAA ONI + ERA5 rainfall. Not an official forecast.")

    lines = [
        "# Baseline model report", "",
        f"Training data: {st.season.nunique()} seasons x {st.station.nunique()} towns "
        f"= {len(st)} town-seasons. Validation: leave-one-season-out.", "",
        "| Metric | Model | No-skill (always 33%) |", "|---|---|---|",
        f"| Brier score (lower is better) | {bs:.3f} | {bs_clim:.3f} |",
        f"| Brier skill score | {bss:+.2f} | 0 |",
        f"| ROC AUC | {auc:.2f} | 0.50 |", "",
        "## Reliability (held-out predictions)", "",
        "| Predicted chance | Town-seasons | Mean predicted | Actually below normal |",
        "|---|---|---|---|",
    ]
    for b, r in rel.iterrows():
        lines.append(f"| {b} | {r.n} | {r.predicted:.0%} | {r.observed:.0%} |")
    lines += ["", f"## Outlook for {season_label(target)} ({oni_label} = {oni_now:+.2f}°C)", "",
              "| Province | Chance of below-normal rainfall |", "|---|---|"]
    for _, r in fc.iterrows():
        lines.append(f"| {r.province} | {r.p_below_normal:.0%} |")
    lines += ["", "A single climate index explains only part of the rainfall story. "
              "Treat this as a baseline to beat, not a forecast to act on."]
    (REPORTS / "model_report.md").write_text("\n".join(lines) + "\n")
    print(f"  Brier skill score {bss:+.2f}, AUC {auc:.2f}; saved reports/model_report.md")


if __name__ == "__main__":
    main()
