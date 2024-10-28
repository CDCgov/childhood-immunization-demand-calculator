from dataclasses import dataclass
from typing import Any, Callable
from collections.abc import Iterator
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


class CharacteristicProportions(dict):
    """A dictionary `{characteristic: {level: proportion}}`. Characteristics are
    strings, levels are anything (hashable), and proportions are floats. Proportions
    for a characteristic should sum to 1."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validate()

    def validate(self):
        # all keys (characteristics) should be strings
        assert all(isinstance(k, str) for k in self.keys())
        # all values (proportions) should be dictionaries
        assert all(isinstance(v, dict) for v in self.values())
        # all proportions of a characteristic should sum to 1
        for char, props in self.items():
            assert np.isclose(sum(props.values()), 1.0)


class PopulationID(dict):
    """Extension of the dictionary class to represent a population ID. The keys
    are strings (characteristics) and the values are anything (levels).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validate()

    def validate(self):
        assert all(isinstance(k, str) for k in self.keys())


@dataclass
class PopulationResult:
    """Result of a calculation on a population"""

    char_to_resolve: str = None
    value: Any = None


class PopulationManager:
    def __init__(self, size: float, char_props: CharacteristicProportions):
        self.char_props = char_props

        # create a canonical ordering of the characteristics
        self.chars = list(sorted(self.char_props.keys()))

        # set up the data, with an initial population with no characteristics
        self.data = {}
        self.set_size({}, size)

    def get_size(self, pop: PopulationID) -> float:
        return self.data[self._pop_to_tuple(pop)]

    def set_size(self, pop: PopulationID, value: float) -> None:
        self.data[self._pop_to_tuple(pop)] = value

    def delete_pop(self, pop: PopulationID) -> None:
        del self.data[self._pop_to_tuple(pop)]

    def pops(self) -> Iterator[PopulationID]:
        return map(self._tuple_to_pop, self.data.keys())

    def _tuple_to_pop(self, levels: tuple[str, ...]) -> PopulationID:
        return dict(zip(self.chars, levels))

    def _pop_to_tuple(self, pop: PopulationID) -> tuple[str, ...]:
        return tuple(pop.get(char, None) for char in self.chars)

    def map(
        self, f: Callable[[PopulationID, float], PopulationResult]
    ) -> Iterator[tuple[PopulationID, Any]]:
        """Map a function over all subpopulations

        Args:
            f (Callable[dict[str, Any], PopulationResult]): The function to be
              mapped. It should take a PopulationID and the population size and return
              a PopulationResult. If `result.resolved`, then the function was able to
              compute a result based on the PopulationID. If not, then the function
              needs the characteristic `result.char_to_resolve` to be further partitioned,
              to return a value.

        Yields:
            Iterator: 2-tuples of the population (defined by its `{characteristic: level}`
              dictionary) and the output of the `f` function for that population
        """
        pop_stack = list(self.pops())

        while pop_stack:
            pop = pop_stack.pop()
            result = f(pop, self.get_size(pop))
            if result.char_to_resolve is None:
                yield pop, result.value
            else:
                new_pops = self.partition(pop, result.char_to_resolve)
                pop_stack = new_pops + pop_stack

    def partition(self, pop: PopulationID, char: str) -> [PopulationID]:
        """Partition a population on a characteristic

        Args:
            pop (tuple): the population ID, i.e., a tuple of characteristic levels
            char (str): The characteristic to partition on

        Returns:
            list: A list of new population IDs
        """
        # the characteristic we are partitioning on should not have a level
        assert pop[char] is None

        parent_size = self.get_size(pop)

        new_pops = []
        for level, prop in self.char_props[char].items():
            # new population is the parent population, but with this characteristic at this level
            new_pop = pop | {char: level}
            new_pops.append(new_pop)
            self.set_size(new_pop, prop * parent_size)

        self.delete_pop(pop)
        return new_pops
