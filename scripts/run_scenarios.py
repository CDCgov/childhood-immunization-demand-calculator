# - Articulate scenarios as dictionary of parameters
# - Run each scenario
# - Generate output tables and figures

from pathlib import Path
import yaml
import polars as pl

from drugdemand.nirsevimab import NirsevimabCalculator

# Get path to top level of repo
repo_dir = Path(__file__).resolve().parents[1]

# input parameters ------------------------------------------------------------

with open(repo_dir / "input" / "scenarios.yaml") as f:
    scenarios = yaml.safe_load(f)

# run the scenarios -----------------------------------------------------------

# - "results" is a list of demand events
# - each "scenario" is a dict of parameters
# - births and weights are dealt with somewhat different from other parameters,
#   getting filtered here in scenarios.py rather than in NirsevimabCalculator
results = pl.concat(
    [
        NirsevimabCalculator(
            pars,
            pl.read_csv(pars["births_path"], try_parse_dates=True).filter(
                pl.col("interval") == pl.lit(pars["interval"])
            ),
            pl.read_csv(pars["weights_path"]).filter(
                (pl.col("source") == pl.lit(pars["growth_chart"]))
                & (pl.col("interval") == pl.lit(pars["interval"]))
            ),
            add_pars=True,
        ).results
        for pars in scenarios
    ]
)

# write list of demand events, across all scenarios
results.write_csv(repo_dir / "output" / "results.csv")
