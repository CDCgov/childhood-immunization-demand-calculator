import pytest

from drugdemand import (
    PopulationResult,
    PopulationManager,
    CharacteristicProportions,
    UnresolvedCharacteristic,
)


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

    assert pm.data == {(UnresolvedCharacteristic(), UnresolvedCharacteristic()): 100}


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
        if isinstance(pop_dict["risk_level"], UnresolvedCharacteristic):
            return PopulationResult(char_to_resolve="risk_level")
        elif pop_dict["risk_level"] == "low":
            return PopulationResult(value=0.1 * size)
        elif pop_dict["risk_level"] == "high":
            return PopulationResult(value=2.0 * size)

    results = list(pm.map(f))

    assert len(results) == 2

    assert (
        {"risk_level": "low", "age_group": UnresolvedCharacteristic()},
        100 * 0.5 * 0.1,
    ) in results
    assert (
        {"risk_level": "high", "age_group": UnresolvedCharacteristic()},
        100 * 0.5 * 2.0,
    ) in results

    assert (
        pm.get_size({"risk_level": "low", "age_group": UnresolvedCharacteristic()})
        == 100 * 0.5
    )
    assert (
        pm.get_size({"risk_level": "high", "age_group": UnresolvedCharacteristic()})
        == 100 * 0.5
    )


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
            return PopulationResult(value=0)
        elif isinstance(pop_dict["risk_level"], UnresolvedCharacteristic):
            return PopulationResult(char_to_resolve="risk_level")
        elif pop_dict["risk_level"] == "low":
            return PopulationResult(value=0.1 * size)
        elif pop_dict["risk_level"] == "high":
            return PopulationResult(value=2.0 * size)
        else:
            print(pop_dict["risk_level"])
            print(type(pop_dict["risk_level"]))
            print(isinstance(pop_dict["risk_level"], UnresolvedCharacteristic))
            raise RuntimeError

    # do the first partitions
    list(pm.map(f_risk))

    def f_age(pop_dict, size):
        if isinstance(pop_dict["age_group"], UnresolvedCharacteristic):
            return PopulationResult(char_to_resolve="age_group")
        elif pop_dict["age_group"] == "infant":
            return PopulationResult(value=0)
        elif pop_dict["age_group"] == "child":
            return PopulationResult(value=0)
        elif pop_dict["age_group"] == "adult":
            return PopulationResult(value=size)
        else:
            raise RuntimeError

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


def test_pm_takes_args():
    pm = PopulationManager(
        100, CharacteristicProportions({"risk_level": {"low": 0.5, "high": 0.5}})
    )

    def f(pop, size, multiplier):
        if isinstance(pop["risk_level"], UnresolvedCharacteristic):
            return PopulationResult(char_to_resolve="risk_level")
        elif pop["risk_level"] == "low":
            return PopulationResult(value=0.1 * size * multiplier)
        elif pop["risk_level"] == "high":
            return PopulationResult(value=2.0 * size * multiplier)
        else:
            raise RuntimeError

    multiplier = 4.0
    results = list(pm.map(f, multiplier))

    assert len(results) == 2

    assert ({"risk_level": "low"}, 100 * 0.5 * 0.1 * multiplier) in results
    assert ({"risk_level": "high"}, 100 * 0.5 * 2.0 * multiplier) in results


def test_pm_takes_kwargs():
    pm = PopulationManager(
        100, CharacteristicProportions({"risk_level": {"low": 0.5, "high": 0.5}})
    )

    def f(pop, size, multiplier):
        if isinstance(pop["risk_level"], UnresolvedCharacteristic):
            return PopulationResult(char_to_resolve="risk_level")
        elif pop["risk_level"] == "low":
            return PopulationResult(value=0.1 * size * multiplier)
        elif pop["risk_level"] == "high":
            return PopulationResult(value=2.0 * size * multiplier)
        else:
            raise RuntimeError

    multiplier = 4.0
    results = list(pm.map(f, multiplier=multiplier))

    assert len(results) == 2

    assert ({"risk_level": "low"}, 100 * 0.5 * 0.1 * multiplier) in results
    assert ({"risk_level": "high"}, 100 * 0.5 * 2.0 * multiplier) in results
