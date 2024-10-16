# Make tables and plots

from pathlib import Path
import polars as pl
import altair as alt

# Get path to top level of repo
repo_dir = Path(__file__).resolve().parents[1]

results = pl.read_csv(repo_dir / "output" / "results.csv", try_parse_dates=True)

# summarize demand over the season, by scenario and dosage
season_demand = (
    results.group_by(["scenario", "interval", "drug_dosage"])
    .agg(pl.col("n_doses").sum().round())
    .sort(["scenario", "interval", "drug_dosage"])
)

season_demand.write_csv(repo_dir / "output" / "season_demand.csv")

(
    alt.Chart(
        # show demand from weekly scenarios
        season_demand.filter(pl.col("interval") == pl.lit("week")).to_pandas(),
        title="Season 2024/2025 demand, by scenario, weekly",
    )
    .encode(
        alt.X("drug_dosage", sort=["50mg", "100mg"]).axis(title=None),
        alt.Y("n_doses").axis(title="No. of doses"),
        alt.Column(
            "scenario", sort=["lowest_100", "middle_100", "highest_100"], title=None
        ),
        alt.Color("drug_dosage").legend(None),
    )
    .mark_bar()
    .save(repo_dir / "output" / "season_demand.png", ppi=300)
)


# summarize mix
def summarize_mix(df: pl.DataFrame) -> pl.DataFrame:
    return (
        df.pivot(
            index=["scenario", "interval"],
            columns="drug_dosage",
            values="n_doses",
            aggregate_function="sum",
        )
        .with_columns(total_doses=pl.col("50mg") + pl.col("100mg"))
        .with_columns(
            (pl.col("50mg") / pl.col("total_doses")).alias("%50mg"),
            (pl.col("100mg") / pl.col("total_doses")).alias("%100mg"),
        )
        .with_columns(pl.col("%50mg", "%100mg").round(3))
        .with_columns(pl.col("50mg", "100mg", "total_doses").round_sig_figs(3))
        .sort(["scenario", "interval"])
        .select(
            ["scenario", "interval", "50mg", "100mg", "total_doses", "%50mg", "%100mg"]
        )
    )


# summarize mix over the whole season for each scenario
(summarize_mix(season_demand).write_csv(repo_dir / "output" / "season_mix.csv"))

# summarize mix for the first 3 months
# compute values like "%50mg" = percent of all doses that are 50mg
(
    results.filter(pl.col("time") < pl.date(2025, 1, 1))
    .group_by(["scenario", "interval", "drug_dosage"])
    .agg(pl.col("n_doses").sum().round())
    .pipe(summarize_mix)
    .write_csv(repo_dir / "output" / "season_mix_q4.csv")
)

# demand by time of demand, and by scenario and dosage
demand_by_time = (
    results.group_by(["scenario", "interval", "drug_dosage", "time"])
    .agg(pl.col("n_doses").sum())
    .sort(["interval", "drug_dosage", "time", "scenario"])
)

demand_by_time.write_csv(repo_dir / "output" / "demand_by_time.csv")

(
    alt.Chart(demand_by_time.to_pandas())
    .encode(x="time", y="n_doses", color="drug_dosage")
    .mark_bar()
    .properties(title="Nirsevimab demand, 2024/2025")
    .facet(
        row=alt.Facet("scenario", sort=["lowest_100", "middle_100", "highest_100"]),
        column=alt.Facet("interval", sort=["week", "month"]),
    )
    .resolve_scale(y="independent")
    .save(repo_dir / "output" / "demand_by_time.png", ppi=300)
)

# demand by week
(
    alt.Chart(demand_by_time.filter(pl.col("interval") == pl.lit("week")).to_pandas())
    .encode(
        alt.X("time").axis(title=None),
        alt.Y("n_doses").axis(title="Weekly no. doses"),
        color="drug_dosage",
    )
    .mark_bar()
    .facet(
        column=alt.Facet(
            "scenario", sort=["lowest_100", "middle_100", "highest_100"], title=None
        ),
    )
    .properties(title="Nirsevimab demand by week, 2024/2025")
    .save(repo_dir / "output" / "demand_by_week.png", ppi=300)
)

# demand by week
(
    alt.Chart(demand_by_time.filter(pl.col("interval") == pl.lit("week")).to_pandas())
    .encode(
        alt.X("time").axis(title=None),
        alt.Y("n_doses").axis(title="Weekly no. doses"),
        color="drug_dosage",
    )
    .mark_bar()
    .facet(
        column=alt.Facet(
            "scenario", sort=["lowest_100", "middle_100", "highest_100"], title=None
        ),
    )
    .properties(title="Nirsevimab demand by week, 2024/2025")
    .save(repo_dir / "output" / "demand_by_week.png", ppi=300)
)

# demand by birth date, and by scenario and dosage
(
    alt.Chart(
        results.group_by(["scenario", "interval", "drug_dosage", "birth_date"])
        .agg(pl.col("n_doses").sum())
        .to_pandas()
    )
    .encode(x="birth_date", y="n_doses", color="drug_dosage")
    .mark_bar()
    .properties(title="Nirsevimab demand, 2024/2025")
    .facet(
        row=alt.Facet("scenario", sort=["lowest_100", "middle_100", "highest_100"]),
        column=alt.Facet("interval", sort=["week", "month"]),
    )
    .resolve_scale(y="independent")
    .save(repo_dir / "output" / "demand_by_birth.png", ppi=300)
)
