import pytest

from drugdemand import IndependentSubpopulations, Population


def test_independent():
    """Check that populations can be arbitrarily sub-divided, and they are broken down
    according to the correct proportions"""
    subpops = IndependentSubpopulations(
        Population(size=1.0),
        attribute_levels={
            "has_y_chromosome": {True: 0.5, False: 0.5},
            "eye_color": {"brown": 0.5, "blue": 0.25, "green": 0.20, "other": 0.05},
        },
    )

    pops = list(iter(subpops))

    some_pop = Population(
        size=1.0 * 0.5 * 0.5,
        attributes={"eye_color": "brown", "has_y_chromosome": True},
    )

    assert some_pop in pops


def test_subdivide_bad_proportions():
    """Raise an error when attribute levels don't add up to 1"""
    with pytest.raises(Exception):
        list(
            iter(
                IndependentSubpopulations(
                    Population(size=1.0), attribute_levels={"sex": {"m": 0.4, "f": 0.4}}
                )
            )
        )
