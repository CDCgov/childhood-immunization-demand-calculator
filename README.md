# Childhood immunization demand calculator

## Overview

The Python package `drugdemand` is an experimental modeling framework for developing hypothetical, forward-looking projections of demand for childhood immunizations. Currently, this approach is deterministic, data-informed calculation. In other words, the modeling framework produces models with no stochastic or dynamical elements. Once a model has been formulated, the model parameters can be adjusted to produce demand estimates for hypothetical scenarios.

The modeling framework centers around _populations_ of children. Each population has a size (i.e., number of children) and one or other more _attributes_ that uniquely determine the volume and timing of demand for an immunization among that population. A model consists of these populations and a _demand function_ that takes a population as input, examines its size and attributes, and determines if the population would have demand for an immunization, and if so, when and how much.

The code consists of these classes:

- `Population` is a data class contains a population's size (i.e., number of people) and attributes (e.g., birth date, "willing"-ness).
- `IndependentSubpopulations` is a data manager that subdivides a list of `Population`s into smaller populations based on lists of attributes.
- `DrugDosage`, `DrugQuantity`, and `DrugDemand` are data classes that account for dosages (e.g., 50mg vs. 100mg), numbers of doses, and times of demand.

## Example application to nirsevimab

Nirsevimab is a long-acting monoclonal antibody that protects infants and young children against severe respiratory syncytial virus (RSV). CDC recommends that infants aged <8 months not protected through maternal immunization receive nirsevimab just before the RSV season, or in the first week of life if born during the RSV season. Nirsevimab is also recommended for some high-risk children aged 8-19 months entering their second RSV season. In October 2023, at the start of the first RSV season with nirsevimab available, the manufacturer reported that demand for nirsevimab [had exceeded supply](https://emergency.cdc.gov/han/2023/han00499.asp).

The example code for nirsevimab demonstrates how one could use this modeling framework to generate hypothetical projections of nirsevimab demand for the 2024/2025 season.

### Getting started with the example

1. Set up a Python environment with `poetry install`.
2. Run `make`. This will:
   - Run the preprocessing script `scripts/preprocess.py`, that cleans the raw data in `data/` into ready-to-analyze data in `input/`.
   - Write the scenarios with `scripts/write_scenarios.py`, using the parameter sets in `input/scenarios.yaml`.
   - Run and analyze the scenarios with `scripts/scenarios.py`.
3. See output in `output/`.

### Population attributes

The modeled population attributes are:

- **Birth date**: Populations are grouped into weekly birth cohorts between March 2023 and March 2025.
- **"Willingness"** (yes/no): Only "willing," eligible populations demand nirsevimab. "Willing" is merely a convenience label; the real-world implication is more about which populations are willing and able to receive the immunization.
- **Risk level** (low/high): High risk children in their second season are eligible for 2x100mg dosage.
- **Weight-for-age**: Age (in weeks, or months) at which infant will reach 5 kg weight.
- **Delay from eligibility to immunization**: Some children born during the season are immunized at birth, while others are immunized at a later checkup. Some children born before the season will be immunized at the start of the season, while others will be immunized somewhat later.
- **Place of birth**: 50 states and DC, optionally grouped into HHS regions. In certain scenarios, nirsevimab may be made available at different times in different parts of the country.

In this implementation of the model, there are approximately 80,000 populations, one for each combination of birth week, willingness, risk level, weight-for-age, delay, and place of birth. Every child in the US is modeled as being part of one of these populations, and the members of each populations are treated as identical for purposes of the model.

### Demand function

> ACIP recommends 1 dose of nirsevimab for all infants aged <8 months born during or entering their first RSV season (50 mg for infants weighing <5 kg and 100 mg for infants weighing ≥5 kg ). ACIP recommends 1 dose of nirsevimab (200 mg, administered as two 100 mg injections given at the same time at different injection sites) for infants and children aged 8–19 months who are at increased risk for severe RSV disease and entering their second RSV season. ([Jones et al. _MMWR_ 2023](https://www.cdc.gov/mmwr/volumes/72/wr/mm7234a4.htm))

In this implementation, the demand function follows this logic:

1. If a population is not "willing," it does not demand nirsevimab.
2. A "first eligibility" date is computed for each population.
   - If a population is born before the start of the RSV season, their first eligibility is the start of the RSV season.
   - If a population is born during the RSV season, their first eligibility is at birth.
   - If the population is born after the RSV season, they do not demand nirsevimab.
3. A hypothetical immunization date is computed for each population. This is the first eligibility date plus the population's delay between eligibility and immunization.
4. If the hypothetical immunization date is after the RSV season, the population does not demand nirsevimab. (Some populations that delay immunization too long will "fall off" the edge of an eligibility period.)
5. The population's age and weight at the immunization date are computed.
6. The dosage is computed from the age and weight at immunization.
   - Populations aged 0-8 months and <5kg demand 50 mg.
   - Populations aged 0-8 months and >=5kg demand 100 mg.
   - High-risk populations aged 8-19 months demand 2x100mg.

The demand function is encoded in the `NirsevimabCalculator.calculate_demand()` in `drugdemand/nirsevimab.py`.

The model generates the list of populations, their attributes, whether they demand nirsevimab and, if so, the date, volume, and dosage of that demand. This list of demands can be summarized to produce aggregate demand over weeks or over the entire season.

The demand over populations can be summarized to produce aggregate demand for each dosage through time.

### Scenarios and parameter values

To illustrate a range of demand projections, the following parameters were varied across scenarios:

- Time interval used for birth cohorts: In the main analysis, weekly birth cohorts were used. Monthly birth cohorts were used to explore the effect of that model structure on projections.
- Uptake (i.e., proportion of each birth cohort that is "willing"): In the main analysis, a robust 80% uptake was assumed.
- Prevalence of "high risk" criteria: Ranged from 2% to 4% prevalence across scenarios.
- Weight-for-age tables (i.e., distribution of times after birth that a population reaches 5 kg): WHO growth charts were used in the main analysis. CDC growth charts were used in sensitivity analyses.
- Delays from eligibility to immunization: In the main analysis, 80% of eligible children had a <1 week delay and the remaining 20% had a 2-month delay.

The scenarios and parameter values are encoded in `scripts/scenarios.py`.

### Data sources and assumptions

- Births
  - Birth counts are from [WONDER](https://wonder.cdc.gov/natality-expanded-current.html).
    - Manually downloaded data are included in the repo at `data/Natality 2016-2022 expanded.txt`
    - These data are grouped by: state of residence, year, month.
    - _N.B._: WONDER provides the "final" birth data, which does not include 2023 births, but range of dates available in the [provisional data](https://data.cdc.gov/NCHS/VSRR-State-and-National-Provisional-Counts-for-Liv/hmz2-vwda/) changes over time (i.e., data is phased out of provisional and moved to WONDER).
  - Assume monthly birth counts for 2023 through 2025 are the same as for 2022.
  - Interpolate weekly birth counts from monthly counts (see `script/preprocess.py`).
    - _N.B._: NCHS does not make births by exact date available for analysis, not even to CDC employees.
- Weight by age: Use R packages `childsds` and `anthro`, via the R script `scripts/pct_heavier_by_age.R`.
- Assume population attributes are statistically independent (e.g., if 80% of children are willing, and 20% of patients delay immunization by 8 weeks after eligibility, then 64% of each cohort are immunized at birth and 16% are immunized 8 weeks later, and 20% are not immunized).
- Ignore maternal RSV vaccination.
- Do not includes territories/FASs.
- Do not model the relationship between patients' demand for treatment, providers' demand for shipments of drug, and manufacturers' shipping timelines.

## File structure

- `drugdemand/`: Python package
  - `__init__.py`: General package functionality
  - `nirsevimab.py`: Application to nirsevimab eligibility
- `tests/`: Unit tests for `drugdemand`
- `data/`: Raw data, tracked in repo
- `input/`: Preprocessed data for scenarios; untracked
- `output/`: Results
  - `demand_by_birth.(png|csv)`: Demand by scenario and birth cohort
  - `demand_by_time.csv`: Demand by scenario and date of demand
  - `results.csv`: Every subpopulation with a demand, by scenario
  - `season_demand.(png|csv)`: Summary of demand
  - `season_mix.csv`: Summary of demand, organized by "mix" of the two doses
- `scripts/`: Scripts for running nirsevimab example analyses
  - `pct_heavier_by_age.R`: Extract weight-for-age tables from R packages
  - `preprocess.py`: Interpolate weekly births
  - `run_scenarios.py`: Run the scenarios articulated in `input/scenarios.yaml`
  - `write_scenarios.py`: Write scenarios to `input/scenarios.yaml`

## Project admins

- Scott Olesen, PhD <ulp7@cdc.gov> (CDC/IOD/ORR/CFA)
- Inga Holmdahl, PhD <usn4@cdc.gov> (CDC/IOD/ORR/CFA)

## General Disclaimer

This repository was created for use by CDC programs to collaborate on public health related projects in support of the [CDC mission](https://www.cdc.gov/about/organization/mission.htm). GitHub is not hosted by the CDC, but is a third party website used by CDC and its partners to share information and collaborate on software. CDC use of GitHub does not imply an endorsement of any one particular service, product, or enterprise.

## Public Domain Standard Notice

This repository constitutes a work of the United States Government and is not subject to domestic copyright protection under 17 USC § 105. This repository is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/). All contributions to this repository will be released under the CC0 dedication. By submitting a pull request you are agreeing to comply with this waiver of copyright interest.

## License Standard Notice

This repository is licensed under ASL v2 or later.

This source code in this repository is free: you can redistribute it and/or modify it under the terms of the Apache Software License version 2, or (at your option) any later version.

This source code in this repository is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the Apache Software License for more details.

You should have received a copy of the Apache Software License along with this program. If not, see http://www.apache.org/licenses/LICENSE-2.0.html

The source code forked from other open source projects will inherit its license.

## Privacy Standard Notice

This repository contains only non-sensitive, publicly available data and information. All material and community participation is covered by the [Disclaimer](https://github.com/CDCgov/template/blob/master/DISCLAIMER.md) and [Code of Conduct](https://github.com/CDCgov/template/blob/master/code-of-conduct.md). For more information about CDC's privacy policy, please visit [http://www.cdc.gov/other/privacy.html](https://www.cdc.gov/other/privacy.html).

## Contributing Standard Notice

Anyone is encouraged to contribute to the repository by [forking](https://help.github.com/articles/fork-a-repo) and submitting a pull request. (If you are new to GitHub, you might start with a [basic tutorial](https://help.github.com/articles/set-up-git).) By contributing to this project, you grant a world-wide, royalty-free, perpetual, irrevocable, non-exclusive, transferable license to all users under the terms of the [Apache Software License v2](http://www.apache.org/licenses/LICENSE-2.0.html) or later.

All comments, messages, pull requests, and other submissions received through CDC including this GitHub page may be subject to applicable federal law, including but not limited to the Federal Records Act, and may be archived. Learn more at [http://www.cdc.gov/other/privacy.html](http://www.cdc.gov/other/privacy.html).

## Records Management Standard Notice

This repository is not a source of government records but is a copy to increase collaboration and collaborative potential. All government records will be published through the [CDC web site](http://www.cdc.gov).

## Additional Standard Notices

Please refer to [CDC's Template Repository](https://github.com/CDCgov/template) for more information about [contributing to this repository](https://github.com/CDCgov/template/blob/master/CONTRIBUTING.md), [public domain notices and disclaimers](https://github.com/CDCgov/template/blob/master/DISCLAIMER.md), and [code of conduct](https://github.com/CDCgov/template/blob/master/code-of-conduct.md).
