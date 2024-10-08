# Articulate scenarios as dictionary of parameters. Write those to a file.

from pathlib import Path
import yaml
from datetime import date

# Get path to top level of repo
repo_dir = Path(__file__).resolve().parents[1]

# input parameters ------------------------------------------------------------

# parameters constant across all scenarios
fixed_pars = {
    "uptake": 0.8,
    "season_start": date(2024, 10, 1),
    "season_end": date(2025, 3, 31),
    "births_path": str(repo_dir / "input" / "births.csv"),
    "weights_path": str(repo_dir / "data" / "weights.csv"),
}

# parameters that vary between scenarios
varying_pars = [
    {
        "scenario": "highest_100",  # scenario name
        "growth_chart": "WHO",
        "p_high_risk": 0.04,
        "delays": {
            0: 0.8,
            8: 0.2,
        },  # in form delay_in_weeks: proportion_with_that_delay
        "interval": "week",  # birth cohort interval
    },
    {
        "scenario": "middle_100",
        "growth_chart": "WHO",
        "p_high_risk": 0.03,
        "delays": {0: 0.8, 4: 0.2},
        "interval": "week",
    },
    {
        "scenario": "lowest_100",
        "growth_chart": "CDC",
        "p_high_risk": 0.02,
        "delays": {0: 1.0},
        "interval": "week",
    },
    {
        "scenario": "highest_100",
        "growth_chart": "WHO",
        "p_high_risk": 0.04,
        # month delays have different delays, assuming 1mo=4wk
        "delays": {0: 0.8, 2: 0.2},
        "interval": "month",
    },
    {
        "scenario": "middle_100",
        "growth_chart": "WHO",
        "p_high_risk": 0.03,
        "delays": {0: 0.8, 1: 0.2},
        "interval": "month",
    },
    {
        "scenario": "lowest_100",
        "growth_chart": "CDC",
        "p_high_risk": 0.02,
        "delays": {0: 1.0},
        "interval": "month",
    },
]

# "scenarios" is a list of parameter dictionaries
# use same fixed parameters for each one, then add in varying parameters
scenarios = [x | fixed_pars for x in varying_pars]

with open(repo_dir / "input" / "scenarios.yaml", "w") as f:
    yaml.dump(scenarios, f)
