import datetime

import polars as pl
import polars.testing
import pytest
from dateutil.relativedelta import relativedelta
from datetime import date

from drugdemand import (
    DrugDemand,
    IndependentSubpopulations,
    Population,
)

from drugdemand.nirsevimab import NirsevimabCalculator


def test_all():
    """Integration test: given test birth and weight data, and some scenario
    parameters, expect some particular outcomes"""
    births = (
        pl.read_parquet("tests/data/births.parquet")
        .group_by(["date"])
        .agg(pl.col("births").sum())
    )
    weights = (
        pl.read_parquet("tests/data/weights.parquet")
        .rename({"age_mo": "age"})
        .with_columns(interval=pl.lit("month"))
    )
    expected_results = (
        pl.read_parquet("tests/data/results.parquet")
        .with_columns(interval=pl.lit("month"))
        .filter(pl.col("n_doses") > 0)
        # note that "willing" is present as a column name in the test data; this is `will_receive`
        # in the code
        .filter(pl.col("willing"))
        .rename({"willing": "will_receive"})
        # note that old data had both a uniform start and starts separated by HHS region; we have
        # jettisoned that but want to keep the same test data file
        .filter(pl.col("season_start") == pl.lit("uniform"))
        .group_by(
            [
                "season_start",
                "interval",
                "birth_date",
                "will_receive",
                "risk_level",
                "age_at_5kg",
                "drug_dosage",
                "time",
                "uptake",
                "p_high_risk",
            ]
        )
        .agg([pl.col("n_doses").sum(), pl.col("size").sum()])
    )

    scenario_pars = [
        {
            "uptake": uptake,
            "p_high_risk": p_high_risk,
            "season_start": date(2024, 10, 1),
            "season_end": date(2025, 3, 31),
            "interval": "month",
        }
        for uptake in [0.3, 0.5, 0.7]
        for p_high_risk in [0.01]
    ]

    results = (
        pl.concat(
            [
                NirsevimabCalculator(pars, births, weights, add_pars=True).results
                for pars in scenario_pars
            ]
        )
        .drop("season_end")
        .with_columns(pl.col("season_start").replace({"2024-10-01": "uniform"}))
    )

    polars.testing.assert_frame_equal(
        results, expected_results, check_row_order=False, check_column_order=False
    )


def test_in_season():
    """When a population is born in season, and they aren't 5kg at birth, they should get all
    50mg"""
    birth_date = datetime.date(2024, 11, 1)
    size = 100
    result = NirsevimabCalculator.calculate_demand(
        Population(
            size=size,
            attributes={
                "birth_date": birth_date,
                "age_at_5kg": 1,
                "will_receive": True,
            },
        ),
        pars={
            "season_start": date(2024, 10, 1),
            "season_end": date(2025, 3, 31),
            "interval": "month",
            "p_high_risk": 0,
            "uptake": 1.0,
        },
    )
    expected_result = DrugDemand("50mg", size, birth_date)

    assert result == expected_result


def test_after_season():
    """When a population is born after the season, they get nothing"""
    birth_date = datetime.date(2025, 11, 1)
    size = 100
    result = NirsevimabCalculator.calculate_demand(
        Population(
            size=size,
            attributes={
                "birth_date": birth_date,
                "age_at_5kg": 1,
                "will_receive": True,
            },
        ),
        pars={
            "season_start": date(2024, 10, 1),
            "season_end": date(2025, 3, 31),
            "interval": "month",
            "p_high_risk": 0,
            "uptake": 1.0,
        },
    )

    assert result is None


def test_before_season():
    """When a population is born before the season, and they have hit 5kg weight by the start of
    the season, they should get 100mg"""
    birth_date = datetime.date(2024, 6, 1)
    season_start = datetime.date(2024, 10, 1)
    size = 100
    result = NirsevimabCalculator.calculate_demand(
        Population(
            size=size,
            attributes={
                "birth_date": birth_date,
                "age_at_5kg": 1,
                "will_receive": True,
            },
        ),
        pars={
            "season_start": date(2024, 10, 1),
            "season_end": date(2025, 3, 31),
            "interval": "month",
            "p_high_risk": 0,
            "uptake": 1.0,
        },
    )
    expected_result = DrugDemand("100mg", size, season_start)

    assert result == expected_result


def test_feb_2024():
    """A high-risk cohort born "on" Feb 1, 2024 should get 2x100mg at season start

    This is an edge case: someone born on Feb 1 exactly 8 months old on Oct 1, so they just
    qualify
    """
    birth_date = datetime.date(2024, 2, 1)
    season_start = datetime.date(2024, 10, 1)
    size = 100
    result = NirsevimabCalculator.calculate_demand(
        Population(
            size=size,
            attributes={
                "birth_date": birth_date,
                "age_at_5kg": 1,
                "will_receive": True,
                "risk_level": "high",
            },
        ),
        pars={
            "season_start": season_start,
            "season_end": date(2025, 3, 31),
            "interval": "month",
            "uptake": 1.0,
        },
    )
    expected_result = DrugDemand("100mg", size * 2, season_start)

    assert result == expected_result


def test_parse_delay():
    # properly formatted delay should cause no error
    NirsevimabCalculator.validate_delays({0: 0.8, 8: 0.2})

    # should fail if not integer delay
    with pytest.raises(Exception):
        NirsevimabCalculator.validate_delays({0.1: 1.0})

    # should fail if props don't add to one
    with pytest.raises(Exception):
        NirsevimabCalculator.validate_delays({0: 0.1})


def test_simple_delay():
    """A population with a 1-month delay has a demand one month after a population otherwise
    identical but with no delay"""
    birth_date = datetime.date(2024, 11, 1)
    size = 100
    result1 = NirsevimabCalculator.calculate_demand(
        Population(
            size=size,
            attributes={
                "birth_date": birth_date,
                "age_at_5kg": 1,
                "will_receive": True,
            },
        ),
        pars={
            "season_start": date(2024, 10, 1),
            "season_end": date(2025, 3, 31),
            "interval": "month",
            "p_high_risk": 0,
            "uptake": 1.0,
        },
    )

    result2 = NirsevimabCalculator.calculate_demand(
        Population(
            size=size,
            attributes={
                "birth_date": birth_date,
                "age_at_5kg": 1,
                "will_receive": True,
                "delay": 1,
            },
        ),
        pars={
            "season_start": date(2024, 10, 1),
            "season_end": date(2025, 3, 31),
            "interval": "month",
            "p_high_risk": 0,
            "uptake": 1.0,
        },
    )

    assert result2.time == result1.time + relativedelta(months=1)


def test_delay_props():
    """Separate a birth cohort into two populations with different delays. Confirm that you
    end up with two demand events, in the correct proportion"""
    birth_date = datetime.date(2024, 11, 1)
    size = 100

    pop = Population(
        size=size,
        attributes={"birth_date": birth_date, "age_at_5kg": 1, "will_receive": True},
    )

    subpops = IndependentSubpopulations(
        pop, attribute_levels={"delay": {0: 0.8, 1: 0.2}}
    )

    results = [
        NirsevimabCalculator.calculate_demand(
            subpop,
            pars={
                "season_start": date(2024, 10, 1),
                "season_end": date(2025, 3, 31),
                "interval": "month",
                "p_high_risk": 0,
                "uptake": 1.0,
            },
        )
        for subpop in subpops
    ]

    dose_dates = [(x.drug_dosage, x.n_doses, x.time) for x in results]
    assert set(dose_dates) == set(
        [
            ("50mg", 80.0, birth_date),
            # note that we change dosage because weight changes are inclusive
            ("100mg", 20.0, birth_date + relativedelta(months=1)),
        ]
    )
