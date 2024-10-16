# Make tables and plots

from pathlib import Path
import polars as pl
import altair as alt

# Get path to top level of repo
repo_dir = Path(__file__).resolve().parents[1]

results_raw = pl.read_csv(repo_dir / "output" / "results.csv", try_parse_dates=True)

# we only need to report on the weekly results, not monthly
results = results_raw.filter(pl.col("interval") == pl.lit("week"))

# summarize demand over the season, by scenario and dosage
season_demand = (
    results.group_by(["scenario", "drug_dosage"])
    .agg(pl.col("n_doses").sum().round())
    .pivot(index="scenario", columns="drug_dosage", values="n_doses")
    .with_columns(total_doses=pl.col("50mg") + pl.col("100mg"))
    .with_columns(
        (pl.col("50mg") / pl.col("total_doses")).alias("%50mg"),
        (pl.col("100mg") / pl.col("total_doses")).alias("%100mg"),
    )
    .with_columns(pl.col("%50mg", "%100mg").round(3))
    .with_columns(pl.col("50mg", "100mg", "total_doses").round_sig_figs(3))
    .sort("scenario")
    .select(["scenario", "50mg", "100mg", "total_doses", "%50mg", "%100mg"])
)

season_demand.write_csv(repo_dir / "output" / "season_demand.csv")

# demand by time of demand, and by scenario and dosage
demand_by_time = (
    results.group_by(["scenario", "drug_dosage", "time"])
    .agg(pl.col("n_doses").sum())
    .sort(["scenario", "drug_dosage", "time"])
)

date_axis = alt.Axis(format="%b %Y")

plot_demand_by_time = (
    alt.Chart(demand_by_time)
    .encode(
        x=alt.X("time", title="Week of demand", axis=date_axis),
        y="n_doses",
        color="drug_dosage",
    )
    .mark_bar()
    .properties(title="Nirsevimab demand, 2024/2025")
    .facet(row=alt.Facet("scenario", sort=["lowest_100", "middle_100", "highest_100"]))
    .resolve_scale(y="independent")
    .properties(title="Nirsevimab demand by week, 2024/2025")
)

plot_demand_by_time.save(repo_dir / "output" / "demand_by_time.png", ppi=300)

# demand by birth date, and by scenario and dosage
demand_by_birth = results.group_by(["scenario", "drug_dosage", "birth_date"]).agg(
    pl.col("n_doses").sum()
)

plot_demand_by_birth = (
    alt.Chart(demand_by_birth)
    .encode(
        x=alt.X("birth_date", title="Week of birth", axis=date_axis),
        y="n_doses",
        color="drug_dosage",
    )
    .mark_bar()
    .properties(title="Nirsevimab demand, 2024/2025")
    .facet(
        row=alt.Facet("scenario", sort=["lowest_100", "middle_100", "highest_100"]),
    )
    .resolve_scale(y="independent")
)

plot_demand_by_birth.save(repo_dir / "output" / "demand_by_birth.png", ppi=300)
