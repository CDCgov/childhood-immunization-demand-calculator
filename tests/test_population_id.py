import pytest
from drugdemand import (
    PopulationID,
    UnresolvedCharacteristic,
    UnresolvedCharacteristicException,
)


def test_popid_init():
    PopulationID({"age": "adult", "sex": UnresolvedCharacteristic()})


def test_popid_from_chars():
    pop = PopulationID.from_characteristics(["age", "sex"])
    assert pop.mapping == {
        "age": UnresolvedCharacteristic(),
        "sex": UnresolvedCharacteristic(),
    }


def test_popid_basic_patterns():
    pop = PopulationID({"age": "adult", "sex": UnresolvedCharacteristic()})
    # can get values
    assert pop["age"] == "adult"
    # can get values with defaults
    assert pop.get("foo", None) is None
    # can get length
    assert len(pop) == 2


def test_raise_unresolved():
    pop = PopulationID({"age": "adult", "sex": UnresolvedCharacteristic()})
    with pytest.raises(UnresolvedCharacteristicException) as exc_info:
        pop["sex"]

    # pytest gives you an ExceptionInfo objects; pull out the exception itself
    e = exc_info.value
    assert e.args[0] == "sex"
