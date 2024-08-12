import itertools
from dataclasses import dataclass
from typing import Any
import numpy as np


@dataclass
class DrugDosage:
    """Drug dosage (e.g., nirsevimab 50mg)"""

    drug: str
    dosage: str

    def __eq__(self, other):
        return self.drug == other.drug and self.dosage == other.dosage

    def __str__(self):
        return f"{self.drug} {self.dosage}"


@dataclass
class DrugQuantity:
    """Quantity of a drug-dosage"""

    drug_dosage: DrugDosage
    n_doses: int

    def __post_init__(self):
        assert self.n_doses >= 0

    def __add__(self, other):
        assert self.drug_dosage == other.drug_dosage
        DrugQuantity(self.drug_dosage, self.n_doses + other.n_doses)


@dataclass
class DrugDemand:
    """Quantity of a drug-dosage, at a time"""

    drug_dosage: DrugDosage
    n_doses: int
    time: Any


@dataclass
class Population:
    """Group of person identical for purposes of the calculation"""

    size: float
    attributes: dict = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


@dataclass
class IndependentSubpopulations:
    """Statistically independent populations

    There are multiple attributes (eg "risk_level", "state"). Each attribute has a proportion
    associated to each level (eg 1% of population is high risk, 10% live in California). Assume
    that attributes are statistically independent, ie, the size of a population is equal to the
    product of the prevalences of each of its attributes.

    Args:
        size (float): Size of the population
        attribute_levels (dict[str, dict[Any, float]]): Mapping from attribute to
            a second mapping. Second mapping is from levels to proportions. E.g.,
            `{"risk_level": {"high": 0.1, "low": 0.9}}`.
    """

    population: Population
    attribute_levels: dict[str, dict[Any, float]]

    def __post_init__(self):
        self.validate_attribute_levels()

    def validate_attribute_levels(self, eps=1e-6):
        for attribute, levels in self.attribute_levels.items():
            assert attribute not in self.population.attributes
            assert np.isclose(
                sum(levels.values()), 1.0
            ), f"proportions for attribute {attribute} sum to {sum(levels.values())}, not 1"

    def __iter__(self):
        """Iterate over subpopulations

        Yields:
            dict: keys are "size" (a float) and "attributes" (a dictionary mapping from attributes
              to levels, eg `{"risk_level": "high"}`)
        """
        # create a list, one item per attribute
        # each is a list of lists, each sublist is one level & prop
        attribute_level_iters = [
            [(attribute, level, prop) for level, prop in levels_props.items()]
            for attribute, levels_props in self.attribute_levels.items()
        ]

        # "subpop" is a list of attribute, level, proportion
        for subpop in itertools.product(*attribute_level_iters):
            subpop_prop = np.prod([x for _, _, x in subpop])

            if subpop_prop > 0:
                subpop_attributes = {attribute: level for attribute, level, _ in subpop}

                yield Population(
                    size=self.population.size * subpop_prop,
                    attributes=self.population.attributes | subpop_attributes,
                )
