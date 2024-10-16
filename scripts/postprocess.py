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

# demand by time type (demand date or birth date), and by scenario and dosage
demand_by_time = (
    results.group_by(["scenario", "drug_dosage", "time"])
    .agg(pl.col("n_doses").sum())
    .sort(["scenario", "drug_dosage", "time"])
    .with_columns(time_type=pl.lit("demand"))
)

demand_by_birth = (
    results.group_by(["scenario", "drug_dosage", "birth_date"])
    .agg(pl.col("n_doses").sum())
    .rename({"birth_date": "time"})
    .with_columns(time_type=pl.lit("birth"))
)

plot_demand_by_time = (
    alt.Chart(demand_by_time)
    .encode(
        alt.X("time", title="Week of demand", axis=alt.Axis(format="%b %Y")),
        alt.Y("n_doses", title="No. of doses"),
        alt.Color("drug_dosage", title="Dosage"),
        alt.Row(
            "scenario",
            sort=["lowest_100", "middle_100", "highest_100"],
            title=None,
            header=None,
        ),
    )
    .mark_bar()
)

plot_demand_by_birth = (
    alt.Chart(demand_by_birth)
    .encode(
        alt.X("time", title="Week of birth", axis=alt.Axis(format="%b %Y")),
        alt.Y("n_doses", title="No. of doses"),
        alt.Color("drug_dosage"),
        alt.Row(
            "scenario",
            sort=["lowest_100", "middle_100", "highest_100"],
            title=None,
            header=None,
        ),
    )
    .mark_bar()
)

(plot_demand_by_time | plot_demand_by_birth).save(repo_dir / "output" / "demand.png")
