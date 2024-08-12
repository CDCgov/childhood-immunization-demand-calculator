import pytest

from drugdemand import DrugDosage, DrugQuantity


def test_drug_equal():
    """Objects are equal but not identical"""
    dd1 = DrugDosage("nirsevimab", "50mg")
    dd2 = DrugDosage("nirsevimab", "50mg")
    assert dd1 is not dd2
    assert dd1 == dd2


def test_drug_init_nonnegative():
    """Drug quantities must be nonnegative"""
    with pytest.raises(Exception):
        DrugQuantity(DrugDosage("nirsevimab", "50mg"), -5)


def test_drug_dosage_as_dict():
    """DrugDosage object can be translated into a dictionary"""
    assert DrugDosage("penicillin", "50mg").__dict__ == {
        "drug": "penicillin",
        "dosage": "50mg",
    }
