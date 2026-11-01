"""Interactive dashboard:  streamlit run app.py
Reads the tables in data/processed/ (refresh them with `python run_all.py`)."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config import COLORS
from src import dashboard_data as dd

REPO_URL = "https://github.com/Takudzwa-debug/elnino-zimbabwe"

PHASE_COLOR = {"La Niña": COLORS["la_nina"], "Neutral": COLORS["neutral"],
               "El Niño": "#ee8d8b", "Strong El Niño": COLORS["el_nino"]}
PHASES = list(PHASE_COLOR)
# Diverging: dry (red) <- grey -> wet (blue). Sequential: one hue, light -> dark.
DIVERGING = [[0, "#b52f2f"], [0.25, "#ee8d8b"], [0.5, "#f0efec"], [0.75, "#86b6ef"], [1, "#1c5aa6"]]
SEQ_RED = [[0, "#fbe3e2"], [0.5, "#ee8d8b"], [1, "#b52f2f"]]

st.set_page_config(page_title="El Niño & Drought Risk · Zimbabwe", page_icon="🌦️",
                   layout="wide")


def style(fig, height=380):
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=10, r=10, t=40, b=10),
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color=COLORS["text"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    fig.update_xaxes(showgrid=False, linecolor=COLORS["grid"])
    fig.update_yaxes(gridcolor=COLORS["grid"], zerolinecolor=COLORS["text_muted"])
    return fig


@st.cache_data
def get_data():
    return dd.load_all()


@st.cache_resource
def get_model():
    _, station, _ = get_data()
    return dd.train_model(station)


oni, station, nat = get_data()
model = get_model()
latest = dd.latest_oni(oni)
phases = dd.phase_summary(station)
season_name = f"{latest['target']}/{str(latest['target'] + 1)[-2:]}"

# ------------------------------------------------------------------ header
st.title("El Niño and Drought Risk in Zimbabwe")
st.markdown(
    f"How strongly does El Niño shape Zimbabwe's rains and harvests, and what does that "
    f"mean for **{season_name}**? Built from {station['season'].nunique()} rainy seasons "
    f"(1981–2025) at 10 provincial towns.")

k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Latest El Niño index ({latest['label']})", f"{latest['value']:+.2f} °C",
          help="Oceanic Niño Index. Above +0.5 °C is El Niño, above +1.5 °C is strong.")
k2.metric("Rainfall in strong El Niño years", f"{phases.loc['Strong El Niño', 'mean_anom']:+.0f}%",
          help="Average Oct–Mar rainfall vs the 1991–2020 normal, across all 10 towns.")
k3.metric("Strong El Niño seasons in driest third",
          f"{phases.loc['Strong El Niño', 'share_below']:.0%}",
          help="Share of town-seasons in the driest third of years. Chance alone: 33%.")
k4.metric("Model skill (ROC AUC)", "0.78",
          help="Leave-one-season-out validation. 0.5 = no skill, 1.0 = perfect.")

# ------------------------------------------------------------------ sidebar
st.sidebar.header("What-if: El Niño strength")
oni_value = st.sidebar.slider(
    "Aug–Oct ONI (°C)", min_value=-2.0, max_value=3.0,
    value=float(round(latest["value"], 1)), step=0.1,
    help="Move this to see how the model's outlook changes with El Niño strength.")
st.sidebar.caption(
    f"Default is the latest value ({latest['label']}: {latest['value']:+.2f} °C)."
    + ("" if latest["official"] else " The official Aug–Oct value is published by NOAA "
       "in early November."))
st.sidebar.markdown("**Reading the ONI**\n\n"
                    "- below −0.5: La Niña (usually wet)\n"
                    "- −0.5 to +0.5: neutral\n"
                    "- above +0.5: El Niño (usually dry)\n"
                    "- above +1.5: strong El Niño")
st.sidebar.markdown(f"[Code and method on GitHub]({REPO_URL})")

tab_out, tab_hist, tab_town, tab_harvest, tab_about = st.tabs(
    ["Outlook", "History", "Province explorer", "Harvests", "About"])

# ------------------------------------------------------------------ outlook
with tab_out:
    fc = dd.outlook(model, oni_value)
    st.subheader(f"Chance of below-normal rainfall, {season_name}, at ONI {oni_value:+.1f} °C")
    left, right = st.columns([1.1, 1])
    with left:
        fig = px.scatter_map(
            fc, lat="lat", lon="lon", color="p_below_normal", size="p_below_normal",
            size_max=28, hover_name="province", range_color=(0, 100),
            hover_data={"p_below_normal": ":.0f", "lat": False, "lon": False},
            color_continuous_scale=SEQ_RED, zoom=5.2, center=dict(lat=-19.0, lon=29.9),
            map_style="carto-positron",
            labels={"p_below_normal": "Chance (%)"})
        fig.update_layout(height=470, margin=dict(l=0, r=0, t=0, b=0),
                          coloraxis_colorbar=dict(title="%", thickness=12))
        st.plotly_chart(fig)
    with right:
        fig = go.Figure(go.Bar(
            x=fc["p_below_normal"], y=fc["province"], orientation="h",
            marker_color=COLORS["el_nino"], text=fc["p_below_normal"].map(lambda v: f"{v:.0f}%"),
            textposition="outside", hovertemplate="%{y}: %{x:.0f}%<extra></extra>"))
        fig.add_vline(x=100 / 3, line_dash="dot", line_color=COLORS["text_muted"],
                      annotation_text="normal odds (33%)", annotation_position="bottom right")
        fig.update_layout(xaxis=dict(range=[0, 108], title="Chance of below-normal rainfall (%)"),
                          yaxis=dict(autorange="reversed", title=None), showlegend=False)
        st.plotly_chart(style(fig, 470))

    analogs = dd.analog_seasons(station, oni_value)
    c1, c2 = st.columns([1, 1.3])
    with c1:
        st.markdown("**Past seasons that started like this** (Aug–Oct ONI within ±0.4 °C)")
        if analogs.empty:
            st.write("No past season started with an El Niño index this close, "
                     "so the model is extrapolating here.")
        else:
            st.dataframe(analogs, hide_index=True)
    with c2:
        st.warning(
            f"**Read with care.** Only {len(analogs)} past season(s) started this close to "
            f"{oni_value:+.1f} °C, and the model uses one climate index. The Meteorological "
            "Services Department, which combines many more drivers, puts the chance of "
            "below-normal rainfall for 2026/27 at about 65%. Both point the same way; "
            "use the official outlook for decisions.")

# ------------------------------------------------------------------ history
with tab_hist:
    recent = oni[oni["date"] >= "1980-01-01"].copy()
    recent["state"] = np.select([recent["oni"] >= 0.5, recent["oni"] <= -0.5],
                                ["El Niño", "La Niña"], "Neutral")
    fig = px.bar(recent, x="date", y="oni", color="state",
                 color_discrete_map={"El Niño": COLORS["el_nino"], "La Niña": COLORS["la_nina"],
                                     "Neutral": COLORS["neutral"]},
                 hover_data={"seas": True, "yr": True, "date": False, "state": False},
                 labels={"oni": "ONI (°C)", "date": "", "seas": "Months", "yr": "Year"},
                 title="The El Niño cycle since 1980 (Oceanic Niño Index)")
    fig.update_traces(marker_line_width=0)
    fig.update_layout(bargap=0)
    for y in (0.5, -0.5):
        fig.add_hline(y=y, line_dash="dot", line_color=COLORS["text_muted"], line_width=1)
    st.plotly_chart(style(fig, 330))

    fig = px.bar(nat.dropna(subset=["anom_pct"]), x="season", y="anom_pct", color="phase_label",
                 category_orders={"phase_label": PHASES}, color_discrete_map=PHASE_COLOR,
                 hover_data={"season_label": True, "season": False, "phase_label": True,
                             "anom_pct": ":.0f"},
                 labels={"anom_pct": "% vs 1991–2020 normal", "season": "Season (start year)",
                         "phase_label": "Phase", "season_label": "Season"},
                 title="Rainy-season rainfall vs normal (average of 10 towns)")
    st.plotly_chart(style(fig, 360))

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("**Average by phase**")
        tbl = phases.reset_index().rename(columns={"index": "Phase"})
        st.dataframe(pd.DataFrame({
            "Phase": tbl["Phase"],
            "Rainfall vs normal": tbl["mean_anom"].map(lambda v: f"{v:+.0f}%"),
            "Oct–Dec": tbl["ond"].map(lambda v: f"{v:+.0f}%"),
            "Jan–Mar": tbl["jfm"].map(lambda v: f"{v:+.0f}%"),
            "In driest third": tbl["share_below"].map(lambda v: f"{v:.0%}"),
        }), hide_index=True)
    with c2:
        labels = station.drop_duplicates("season").sort_values("season")["season_label"].tolist()
        pick = st.select_slider("Pick a season to map", options=labels,
                                value="2023/24" if "2023/24" in labels else labels[-1])
        one = station[station["season_label"] == pick]
        st.caption(f"{pick}: ENSO phase **{one['phase_label'].iloc[0]}**, "
                   f"average {one['anom_pct'].mean():+.0f}% vs normal")
        fig = px.scatter_map(
            one, lat="lat", lon="lon", color="anom_pct", hover_name="province",
            hover_data={"anom_pct": ":.0f", "rain_mm": ":.0f", "lat": False, "lon": False},
            range_color=(-60, 60), color_continuous_scale=DIVERGING, zoom=4.9,
            center=dict(lat=-19.0, lon=29.9), map_style="carto-positron",
            labels={"anom_pct": "% vs normal", "rain_mm": "Rain (mm)"})
        fig.update_traces(marker=dict(size=18))
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=0, b=0),
                          coloraxis_colorbar=dict(title="%", thickness=12))
        st.plotly_chart(fig)

# ------------------------------------------------------------------ province explorer
with tab_town:
    corr = dd.town_correlations(station)
    options = corr["station"].tolist()
    name = st.selectbox(
        "Province", options,
        format_func=lambda s: f"{dd.STATIONS[s]['province']} ({s})"
        if s != dd.STATIONS[s]["province"] else s)
    ts = dd.town_stats(station, name)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Normal season rainfall", f"{ts['normal_mm']:.0f} mm")
    m2.metric("Strong El Niño years", f"{ts['strong_anom']:+.0f}%")
    m3.metric("El Niño years below normal", f"{ts['el_share_below']:.0%}")
    m4.metric("Worst season", f"{ts['worst'][0]}", f"{ts['worst'][1]:+.0f}%",
              delta_color="off")

    one = station[station["station"] == name].dropna(subset=["phase"])
    fig = px.bar(one, x="season", y="anom_pct", color="phase_label",
                 category_orders={"phase_label": PHASES}, color_discrete_map=PHASE_COLOR,
                 hover_data={"season_label": True, "season": False, "rain_mm": ":.0f",
                             "anom_pct": ":.0f"},
                 labels={"anom_pct": "% vs normal", "season": "Season (start year)",
                         "phase_label": "Phase", "season_label": "Season",
                         "rain_mm": "Rain (mm)"},
                 title=f"{name}: every rainy season since 1981")
    st.plotly_chart(style(fig, 340))

    c1, c2 = st.columns(2)
    with c1:
        by = one.groupby("phase_label")[["anom_ond_pct", "anom_jfm_pct"]].mean().reindex(PHASES)
        fig = go.Figure([
            go.Bar(name="Oct–Dec", x=by.index, y=by["anom_ond_pct"], marker_color="#86b6ef"),
            go.Bar(name="Jan–Mar", x=by.index, y=by["anom_jfm_pct"], marker_color="#1c5aa6"),
        ])
        fig.update_layout(barmode="group", title="Early vs late season, by phase",
                          yaxis_title="% vs normal")
        st.plotly_chart(style(fig, 340))
    with c2:
        fig = go.Figure(go.Bar(
            x=corr["r_season"], y=corr["province"], orientation="h",
            marker_color=[COLORS["el_nino"] if s == name else COLORS["neutral"]
                          for s in corr["station"]],
            hovertemplate="%{y}: r = %{x:.2f}<extra></extra>"))
        fig.update_layout(title="How closely each province follows El Niño",
                          xaxis_title="Correlation with ONI (more negative = more sensitive)",
                          yaxis=dict(autorange="reversed"), showlegend=False)
        st.plotly_chart(style(fig, 340))
    st.caption("Sensitivity (correlation) and damage (rainfall loss) differ: the south follows "
               "El Niño less tightly but starts from less rain, so a strong event can hit it "
               "hardest in percentage terms.")

# ------------------------------------------------------------------ harvests
with tab_harvest:
    d, res = dd.harvest_fit(nat)
    fig = px.scatter(d, x="oni_djf", y="yield_vs_prev5_pct", color="phase_label",
                     category_orders={"phase_label": PHASES}, color_discrete_map=PHASE_COLOR,
                     hover_data={"season_label": True, "harvest_year": True,
                                 "cereal_yield_kg_per_ha": ":.0f", "phase_label": False},
                     labels={"oni_djf": "ONI at the peak of the season (Dec–Feb, °C)",
                             "yield_vs_prev5_pct": "Cereal yield vs previous 5 harvests (%)",
                             "season_label": "Season", "harvest_year": "Harvest",
                             "cereal_yield_kg_per_ha": "Yield (kg/ha)", "phase_label": "Phase"},
                     title=f"Hotter Pacific, smaller harvest (r = {res.rvalue:.2f}, "
                           f"{len(d)} harvests)")
    xs = np.linspace(d["oni_djf"].min(), d["oni_djf"].max(), 50)
    fig.add_trace(go.Scatter(x=xs, y=res.intercept + res.slope * xs, mode="lines",
                             line=dict(color=COLORS["text_muted"], dash="dash"),
                             name="Trend", hoverinfo="skip"))
    fig.update_traces(marker=dict(size=11, line=dict(width=1.5, color="white")),
                      selector=dict(mode="markers"))
    fig.add_hline(y=0, line_color=COLORS["text_muted"], line_width=1)
    st.plotly_chart(style(fig, 460))
    st.markdown(
        f"Each +1 °C on the El Niño index goes with roughly **{res.slope:+.0f}%** cereal yield "
        "against the previous five harvests. The worst losses followed El Niño droughts "
        "(1992, 1995, 1983, 2016).")
    st.info("**Data caveat:** the FAO/World Bank yield for 2024 is identical to 2023, which "
            "looks like an estimate rather than a measured harvest, so the 2023/24 drought's "
            "impact is probably understated.")

# ------------------------------------------------------------------ about
with tab_about:
    st.markdown(f"""
### The problem
Zimbabwe's Meteorological Services Department puts the chance of El Niño in 2026/27 at
88–94%. National forecasts say "drier than normal", but planners need to know **how much**
drier, **where**, **when** in the season, and **what it does to harvests**.

### Data
- **Oceanic Niño Index**: NOAA Climate Prediction Center
- **Daily rainfall, 10 provincial towns, 1981–2026**: Open-Meteo (ERA5 reanalysis)
- **Cereal yield and production**: World Bank Open Data (from FAO)

### Method
Seasons run October–March and are compared with the 1991–2020 average at each town.
Each season is classed by its Dec–Feb ONI. The outlook model is a logistic regression that
predicts the chance of a below-normal season (driest third) from the Aug–Oct ONI, which is
known before the main rains. It was validated leave-one-season-out
(Brier skill score +0.20, ROC AUC 0.78).

### Limitations
Point reanalysis rainfall rather than gauges; a small number of El Niño events; one
climate driver only. **This is a portfolio project, not an official forecast.**

[Full code and README on GitHub]({REPO_URL})
""")
