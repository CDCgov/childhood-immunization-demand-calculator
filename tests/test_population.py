import pytest

from drugdemand import PopulationManager, CharacteristicProportions


def test_char_prop_validate():
    """Check that the validation of CharacteristicProportions works"""
    # should fail on non-string keys
    with pytest.raises(Exception):
        CharacteristicProportions({1: {"baseline": 1.0}})

    # should fail on non-dict values
    with pytest.raises(Exception):
        CharacteristicProportions({"baseline": 1})

    # should fail on proportions that don't sum to 1
    with pytest.raises(Exception):
        CharacteristicProportions({"risk_level": {"low": 0.1, "high": 0.1}})

    # should pass
    CharacteristicProportions({"risk_level": {"low": 0.5, "high": 0.5}})

    # two characteristics should pass
    CharacteristicProportions(
        {
            "risk_level": {"low": 0.5, "high": 0.5},
            "age_group": {"infant": 0.1, "child": 0.1, "adult": 0.8},
        }
    )


def test_pm_init():
    # should get initial population with all None ID
    pm = PopulationManager(
        100,
        CharacteristicProportions(
            {
                "risk_level": {"low": 0.5, "high": 0.5},
                "age_group": {"infant": 0.1, "child": 0.1, "adult": 0.8},
            }
        ),
    )

    assert pm.data == {(None, None): 100}


def test_update_tuple():
    x = (1, 2, 3)
    assert PopulationManager.update_tuple(x, 1, "foo") == (1, "foo", 3)

    with pytest.raises(Exception):
        PopulationManager.update_tuple(x, 3, "foo")

    with pytest.raises(Exception):
        PopulationManager.update_tuple(x, -1, "foo")


def test_pm_divide1():
    pm = PopulationManager(
        100,
        CharacteristicProportions(
            {
                "risk_level": {"low": 0.5, "high": 0.5},
                "age_group": {"infant": 0.1, "child": 0.1, "adult": 0.8},
            }
        ),
    )

    def f(pop_dict, size):
        if pop_dict["risk_level"] is None:
            return {"characteristic": "risk_level", "value": None}
        elif pop_dict["risk_level"] == "low":
            return {"characteristic": None, "value": 0.1 * size}
        elif pop_dict["risk_level"] == "high":
            return {"characteristic": None, "value": 2.0 * size}

    results = list(pm.map(f))

    assert len(results) == 2

    assert ({"risk_level": "low", "age_group": None}, 100 * 0.5 * 0.1) in results
    assert ({"risk_level": "high", "age_group": None}, 100 * 0.5 * 2.0) in results

    assert pm.get_size({"risk_level": "low", "age_group": None}) == 100 * 0.5
    assert pm.get_size({"risk_level": "high", "age_group": None}) == 100 * 0.5


def test_pm_divide_twice():
    pm = PopulationManager(
        100,
        CharacteristicProportions(
            {
                "risk_level": {"low": 0.5, "high": 0.5},
                "age_group": {"infant": 0.1, "child": 0.1, "adult": 0.8},
            }
        ),
    )

    def f_risk(pop_dict, size):
        if size == 0:
            return {"characteristic": None, "value": 0}

        if pop_dict["risk_level"] is None:
            return {"characteristic": "risk_level", "value": None}
        elif pop_dict["risk_level"] == "low":
            return {"characteristic": None, "value": 0.1 * size}
        elif pop_dict["risk_level"] == "high":
            return {"characteristic": None, "value": 2.0 * size}

        raise RuntimeError

    print(pm.data)
    print(list(pm.map(f_risk)))
    print(pm.data)

    def f_age(pop_dict, size):
        if pop_dict["age_group"] is None:
            return {"characteristic": "age_group", "value": None}
        elif pop_dict["age_group"] == "infant":
            return {"characteristic": None, "value": 0}
        elif pop_dict["age_group"] == "child":
            return {"characteristic": None, "value": 0}
        elif pop_dict["age_group"] == "adult":
            return {"characteristic": None, "value": size}

    results = list(pm.map(f_age))

    assert len(results) == 6
    assert (
        {"risk_level": "low", "age_group": "adult"},
        100 * 0.5 * 0.8,
    ) in results
    assert (
        {"risk_level": "high", "age_group": "adult"},
        100 * 0.5 * 0.8,
    ) in results


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
