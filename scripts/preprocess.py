# - Group births by HHS region and birth month
# - Interpolate births by week
#   - Assume births in the month are spread evenly over days in the month
#   - Assign births to weeks by summing up births on each day

import datetime
from pathlib import Path

import polars as pl
import yaml
import shutil

# Get path to top level of repo
repo_dir = Path(__file__).resolve().parents[1]

# just copy over the births
shutil.copy(repo_dir / "data" / "weights.csv", repo_dir / "input" / "weights.csv")

# load HHS regions ------------------------------------------------------------

with open(repo_dir / "data" / "hhs_regions.yaml") as f:
    hhs_regions = yaml.safe_load(f)

# parse the Wonder data -------------------------------------------------------
# data by state, year, month
births_2020_2022 = (
    pl.read_csv(repo_dir / "data" / "Natality, 2016-2022 expanded.txt", separator="\t")
    .with_columns(pl.col("Year").cast(pl.Int32))
    .filter(pl.col("Births").is_not_null())
    .filter(pl.col("Notes").is_null())
    .rename(
        {
            "State of Residence": "state",
            "Year": "year",
            "Month Code": "month",
            "Births": "births",
        }
    )
    .with_columns(
        # determine which states are in HHS regions 4 or 6, vs. rest of the US
        hhs_region=pl.col("state").replace(hhs_regions, default=0)
    )
    .group_by(["hhs_region", "year", "month"])
    .agg(pl.col("births").sum().cast(pl.Float64))
    .select(["hhs_region", "year", "month", "births"])
)

# pull out the 2022 data, which we'll replicate for 2023 and 2024
births_2022 = births_2020_2022.filter(pl.col("year") == 2022)

# project monthly births into the future
births = (
    pl.concat(
        [
            births_2020_2022,
            births_2022.with_columns(year=2023),
            births_2022.with_columns(year=2024),
            births_2022.with_columns(year=2025),
        ]
    )
    .with_columns(date=pl.date(pl.col("year"), pl.col("month"), 1))
    # only include cohorts that could reasonably get nirsevimab
    .filter(pl.col("date") >= datetime.date(2022, 10, 1))
    .with_columns(interval=pl.lit("month"))
    .select(["interval", "hhs_region", "date", "births"])
)


# interpolate weekly births ---------------------------------------------------


# get average number of births per day, by month
def days_in_month(x: pl.Expr):
    """Number of days in that month"""
    n_days = (x.dt.month_end() - x.dt.month_start()) / pl.duration(days=1) + 1
    return n_days.cast(pl.Int64)


# different months hav different numbers of days, so longer months will have more
# births, just because they have more days. correct for that.
births_avg_daily = births.rename({"date": "month_start"}).with_columns(
    avg_births_per_day=pl.col("births") / days_in_month(pl.col("month_start"))
)


# aggregate into weeks
def epiweek(ex: pl.Expr) -> pl.Expr:
    """Sunday that starts a week"""
    return ex.dt.offset_by("1d").dt.truncate("1w").dt.offset_by("-1d")


# start and end dates for the monthly time series
start_date = births_avg_daily["month_start"].min()
end_date = births_avg_daily["month_start"].dt.month_end().max()

births_by_week = (
    pl.DataFrame()
    # create a data frame with every single day between the start and end dates
    .with_columns(date=pl.date_range(start_date, end_date, interval="1d"))  # type: ignore
    # assign each day to a week and a month
    .with_columns(
        week=epiweek(pl.col("date")), month_start=pl.col("date").dt.month_start()
    )
    .join(births_avg_daily, on="month_start")
    .group_by(["hhs_region", "week"])
    .agg(
        days_in_week=pl.col("week").count(),
        births=pl.col("avg_births_per_day").sum(),
    )
    # only use complete weeks
    .filter(pl.col("days_in_week") == 7)
    .with_columns(interval=pl.lit("week"))
    .rename({"week": "date"})
    .select(["interval", "hhs_region", "date", "births"])
)

(
    pl.concat([births, births_by_week], how="vertical")
    .sort(["interval", "hhs_region", "date"])
    .write_csv(repo_dir / "input" / "births.csv")
)
