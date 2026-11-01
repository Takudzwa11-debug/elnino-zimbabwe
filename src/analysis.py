"""Exploratory analysis: how strongly does El Nino shape Zimbabwe's rains and harvests?
Run:  python -m src.analysis      -> figures/*.png and reports/summary.md
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from scipy import stats

from src.config import (COLORS, FIGURES, KEY_EL_NINO_SEASONS, PROCESSED, REPORTS,
                        season_label)

PHASE_COLOR = {"Strong El Nino": COLORS["el_nino"], "El Nino": "#ee8d8b",
               "Neutral": COLORS["neutral"], "La Nina": COLORS["la_nina"]}
PHASE_ORDER = ["La Nina", "Neutral", "El Nino", "Strong El Nino"]


def style():
    plt.rcParams.update({
        "figure.facecolor": COLORS["surface"], "axes.facecolor": COLORS["surface"],
        "savefig.facecolor": COLORS["surface"], "font.size": 10,
        "axes.edgecolor": COLORS["grid"], "axes.labelcolor": COLORS["text_muted"],
        "xtick.color": COLORS["text_muted"], "ytick.color": COLORS["text_muted"],
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": COLORS["grid"], "grid.linewidth": 0.6,
        "axes.axisbelow": True, "axes.titleweight": "bold", "axes.titlesize": 12,
        "axes.titlelocation": "left", "text.color": COLORS["text"],
    })


def save(fig, name, source):
    fig.text(0.01, 0.01, f"Source: {source}", fontsize=7.5, color=COLORS["text_muted"])
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURES / name, dpi=180)
    plt.close(fig)
    print(f"  saved figures/{name}")


def fig_oni_timeline(oni):
    oni = oni[oni["date"] >= "1980-01-01"]
    fig, ax = plt.subplots(figsize=(11, 4))
    colors = np.where(oni["oni"] >= 0.5, COLORS["el_nino"],
                      np.where(oni["oni"] <= -0.5, COLORS["la_nina"], COLORS["neutral"]))
    ax.bar(oni["date"], oni["oni"], width=31, color=colors, linewidth=0)
    for y in (0.5, -0.5):
        ax.axhline(y, color=COLORS["text_muted"], lw=0.8, ls=(0, (3, 3)))
    ax.axhline(0, color=COLORS["text_muted"], lw=0.8)
    for start, label in KEY_EL_NINO_SEASONS.items():
        row = oni[(oni["yr"] == start + 1) & (oni["seas"] == "DJF")]
        if len(row):
            ax.annotate(f"{label}\ndrought", (row["date"].iloc[0], max(row["oni"].iloc[0], 0)),
                        xytext=(0, 8), textcoords="offset points", ha="center",
                        fontsize=8, color=COLORS["text"])
    last = oni.iloc[-1]
    ax.annotate(f"Latest ({last['seas']} {last['yr']}): {last['oni']:+.1f}°C",
                (last["date"], max(last["oni"], 0)), xytext=(-6, 30), textcoords="offset points",
                ha="right", fontsize=8.5, fontweight="bold")
    ax.set_title("The El Niño cycle since 1980: Pacific temperature anomaly (ONI)")
    ax.set_ylabel("ONI (°C)")
    ax.legend(handles=[Patch(color=COLORS["el_nino"], label="El Niño (≥ +0.5)"),
                       Patch(color=COLORS["la_nina"], label="La Niña (≤ −0.5)"),
                       Patch(color=COLORS["neutral"], label="Neutral")],
              loc="lower left", frameon=False, ncol=3, fontsize=8.5)
    save(fig, "01_oni_timeline.png", "NOAA Climate Prediction Center, Oceanic Niño Index")


def fig_national_rainfall(nat):
    nat = nat.dropna(subset=["anom_pct"])
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.bar(nat.index, nat["anom_pct"], width=0.8,
           color=nat["phase"].map(PHASE_COLOR).fillna(COLORS["neutral"]), linewidth=0)
    ax.axhline(0, color=COLORS["text_muted"], lw=0.8)
    for s in KEY_EL_NINO_SEASONS:
        if s in nat.index:
            v = nat.loc[s, "anom_pct"]
            ax.annotate(season_label(s), (s, v), xytext=(0, -12 if v < 0 else 4),
                        textcoords="offset points", ha="center", fontsize=8)
    ax.set_title("Rainy-season rainfall in Zimbabwe vs normal, coloured by ENSO phase")
    ax.set_ylabel("% above / below 1991–2020 average")
    ax.set_xlabel("Season (start year)")
    ax.legend(handles=[Patch(color=PHASE_COLOR[p], label=p.replace("Nino", "Niño"))
                       for p in PHASE_ORDER], frameon=False, ncol=4, fontsize=8.5,
              loc="upper left")
    save(fig, "02_national_rainfall_by_enso.png",
         "Open-Meteo / ERA5 (mean of 10 provincial towns, Oct–Mar); NOAA CPC ONI (DJF)")


def fig_phase_boxplot(st):
    st = st.dropna(subset=["phase"])
    data = [st.loc[st["phase"] == p, "anom_pct"] for p in PHASE_ORDER]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    bp = ax.boxplot(data, patch_artist=True, widths=0.55, showfliers=False,
                    medianprops=dict(color=COLORS["text"], lw=1.5))
    for patch, p in zip(bp["boxes"], PHASE_ORDER):
        patch.set_facecolor(PHASE_COLOR[p]); patch.set_edgecolor(COLORS["surface"])
    rng = np.random.default_rng(0)
    for i, d in enumerate(data, start=1):
        ax.scatter(i + rng.uniform(-0.15, 0.15, len(d)), d, s=8,
                   color=COLORS["text"], alpha=0.25, linewidths=0)
    ax.set_xticks(range(1, 5), [f"{p.replace('Nino', 'Niño')}\n(n={len(d)})"
                                for p, d in zip(PHASE_ORDER, data)])
    ax.axhline(0, color=COLORS["text_muted"], lw=0.8)
    ax.set_title("Seasonal rainfall anomaly by ENSO phase (every town, every season)")
    ax.set_ylabel("% vs 1991–2020 average")
    save(fig, "03_rainfall_by_phase.png", "Open-Meteo / ERA5; NOAA CPC ONI (DJF)")


def fig_station_sensitivity(st):
    rows = []
    for name, g in st.dropna(subset=["oni_djf"]).groupby("station"):
        rows.append({"station": f"{name} ({g['province'].iloc[0]})" if name != g['province'].iloc[0] else name,
                     "Whole season": stats.pearsonr(g["oni_djf"], g["anom_pct"])[0],
                     "Jan–Mar only": stats.pearsonr(g["oni_djf"], g["anom_jfm_pct"])[0]})
    df = pd.DataFrame(rows).sort_values("Whole season", ascending=False)
    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.barh(y + 0.2, df["Whole season"], height=0.38, color=COLORS["el_nino"],
            label="Whole season (Oct–Mar)")
    ax.barh(y - 0.2, df["Jan–Mar only"], height=0.38, color="#9e2f2e",
            label="Late season (Jan–Mar)")
    ax.set_yticks(y, df["station"])
    ax.axvline(0, color=COLORS["text_muted"], lw=0.8)
    ax.set_xlabel("Correlation with ONI (more negative = El Niño dries it out more)")
    ax.set_title("Which parts of Zimbabwe are most sensitive to El Niño?")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=2,
              bbox_to_anchor=(0.5, -0.13))
    ax.grid(axis="y", visible=False)
    save(fig, "04_province_sensitivity.png", "Open-Meteo / ERA5; NOAA CPC ONI (DJF)")
    return df


def fig_cereal(nat):
    d = nat.dropna(subset=["oni_djf", "yield_vs_prev5_pct"])
    if d.empty:
        print("  no cereal data overlap; skipping figure 5")
        return None
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.scatter(d["oni_djf"], d["yield_vs_prev5_pct"], s=40,
               c=d["phase"].map(PHASE_COLOR), edgecolors=COLORS["surface"], linewidths=1.5)
    slope, intercept, r, p, _ = stats.linregress(d["oni_djf"], d["yield_vs_prev5_pct"])
    xs = np.linspace(d["oni_djf"].min(), d["oni_djf"].max(), 50)
    ax.plot(xs, intercept + slope * xs, color=COLORS["text_muted"], lw=1.2, ls="--")
    for s, row in d.iterrows():
        if s in KEY_EL_NINO_SEASONS or abs(row["yield_vs_prev5_pct"]) > 45:
            ax.annotate(season_label(s), (row["oni_djf"], row["yield_vs_prev5_pct"]),
                        xytext=(5, 3), textcoords="offset points", fontsize=8)
    ax.axhline(0, color=COLORS["text_muted"], lw=0.8)
    ax.set_xlabel("ONI at the peak of the rainy season (DJF, °C)")
    ax.set_ylabel("Cereal yield vs previous 5 harvests (%)")
    ax.set_title(f"Hotter Pacific, smaller harvest  (r = {r:.2f}, n = {len(d)})")
    save(fig, "05_cereal_yield_vs_oni.png", "World Bank / FAO cereal yield; NOAA CPC ONI")
    return {"r": r, "p": p, "slope": slope, "n": len(d)}


def write_summary(st, nat, sens, cereal):
    el = st[st["phase"].isin(["El Nino", "Strong El Nino"])]
    neu = st[st["phase"] == "Neutral"]
    strong = st[st["phase"] == "Strong El Nino"]
    u, p = stats.mannwhitneyu(el["anom_pct"], neu["anom_pct"], alternative="less")
    by_phase = st.groupby("phase").agg(
        town_seasons=("anom_pct", "size"), mean_anomaly_pct=("anom_pct", "mean"),
        share_below_normal=("below_normal", "mean")).reindex(PHASE_ORDER)
    worst = nat.dropna(subset=["anom_pct"]).nsmallest(5, "anom_pct")

    lines = [
        "# El Niño and Zimbabwe's rains: summary of findings", "",
        f"Seasons analysed: {season_label(int(st.season.min()))} to "
        f"{season_label(int(st.season.max()))}, 10 provincial towns.", "",
        "## Rainfall by ENSO phase", "",
        "| Phase | Town-seasons | Mean rainfall vs normal | Share below normal (driest third) |",
        "|---|---|---|---|",
    ]
    for ph, r in by_phase.iterrows():
        if pd.notna(r.town_seasons):
            lines.append(f"| {ph} | {int(r.town_seasons)} | {r.mean_anomaly_pct:+.1f}% "
                         f"| {r.share_below_normal:.0%} |")
    lines += ["",
              f"* El Niño seasons were drier than neutral seasons "
              f"(one-sided Mann-Whitney U test, p = {p:.3g}).",
              f"* In strong El Niño seasons, {strong['below_normal'].mean():.0%} of "
              f"town-seasons fell in the driest third, against 33% expected by chance."
              if len(strong) else "* No strong El Niño seasons in the data.",
              "", "## Driest seasons on record (national average)", ""]
    for s, r in worst.iterrows():
        lines.append(f"* {season_label(s)}: {r.anom_pct:+.0f}% (ENSO phase: {r.phase})")
    lines += ["", "## Most El Niño-sensitive towns (correlation with ONI)", ""]
    for _, r in sens.sort_values("Whole season").head(4).iterrows():
        lines.append(f"* {r.station}: r = {r['Whole season']:.2f} whole season, "
                     f"{r['Jan–Mar only']:.2f} Jan–Mar")
    if cereal:
        lines += ["", "## Harvests", "",
                  f"* Cereal yield vs ONI: r = {cereal['r']:.2f} (p = {cereal['p']:.3g}, "
                  f"n = {cereal['n']}). Each +1°C on the ONI goes with about "
                  f"{cereal['slope']:+.0f}% yield against the previous five harvests."]
    (REPORTS / "summary.md").write_text("\n".join(lines) + "\n")
    print("  saved reports/summary.md")


def main():
    FIGURES.mkdir(exist_ok=True); REPORTS.mkdir(exist_ok=True)
    style()
    oni = pd.read_csv(PROCESSED / "oni_long.csv", parse_dates=["date"])
    st = pd.read_csv(PROCESSED / "season_station.csv")
    nat = pd.read_csv(PROCESSED / "season_national.csv", index_col="season")
    fig_oni_timeline(oni)
    fig_national_rainfall(nat)
    fig_phase_boxplot(st)
    sens = fig_station_sensitivity(st)
    cereal = fig_cereal(nat)
    write_summary(st.dropna(subset=["phase"]), nat, sens, cereal)


if __name__ == "__main__":
    main()
