from dataclasses import dataclass
from typing import Any, Callable
from collections.abc import Iterator
import numpy as np
from collections.abc import Mapping


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
        self.validate(self)

    @staticmethod
    def validate(x):
        # all keys (characteristics) should be strings
        assert all(isinstance(k, str) for k in x.keys())
        # all values (proportions) should be dictionaries
        assert all(isinstance(v, dict) for v in x.values())
        # all proportions of a characteristic should sum to 1
        for char, props in x.items():
            assert np.isclose(sum(props.values()), 1.0)


class UnresolvedCharacteristic:
    """Marker for a population characteristic not yet resolved"""

    def __eq__(self, other):
        """All UnresolvedCharacteristics are equal, for ease of testing"""
        return isinstance(other, UnresolvedCharacteristic)

    def __hash__(self):
        """Identical hash, so it can go into dictionaries"""
        return hash("UnresolvedCharacteristic")

    def __str__(self):
        return "unresolved"


class UnresolvedCharacteristicException(Exception):
    pass


class PopulationID(Mapping):
    """Immutable, dictionary-like class to represent a population ID. The keys
    are strings (characteristics) and the values are anything (levels).

    If an UnresolvedCharacteristic would be returned, instead raise an
    exception, to be caught by PopulationManager.map().
    """

    def __init__(self, data=(), raise_if_unresolved: bool = False):
        self.mapping = dict(data)
        self.raise_if_unresolved = raise_if_unresolved
        self._validate_mapping(self.mapping)

    @classmethod
    def from_characteristics(cls, chars: [str]):
        return cls({char: UnresolvedCharacteristic() for char in chars})

    @staticmethod
    def _validate_mapping(x: dict) -> None:
        assert all(isinstance(k, str) for k in x.keys())

    def is_resolved(self, char: str) -> bool:
        return not isinstance(self.mapping[char], UnresolvedCharacteristic)

    def __getitem__(self, char: str):
        if self.raise_if_unresolved and not self.is_resolved(char):
            raise UnresolvedCharacteristicException(char)
        else:
            return self.mapping[char]

    def __len__(self):
        return len(self.mapping)

    def __iter__(self):
        return iter(self.mapping)

    def __str__(self):
        return str(self.mapping)

    def __repr__(self):
        return f"PopulationID({self.mapping!r})"

    def __or__(self, other: dict):
        return PopulationID(self.mapping | other)


class PopulationManager:
    def __init__(self, size: float, char_props: CharacteristicProportions):
        self.char_props = char_props

        # create a canonical ordering of the characteristics
        self.chars = list(sorted(self.char_props.keys()))

        # set up the data, with an initial population with no characteristics
        self.data = {}
        self.set_size(PopulationID({}), size)

    def get_size(self, pop: PopulationID) -> float:
        return self.data[self._pop_to_tuple(pop)]

    def set_size(self, pop: PopulationID, value: float) -> None:
        self.data[self._pop_to_tuple(pop)] = value

    def delete_pop(self, pop: PopulationID) -> None:
        del self.data[self._pop_to_tuple(pop)]

    def pops(self) -> Iterator[PopulationID]:
        return map(self._tuple_to_pop, self.data.keys())

    def _tuple_to_pop(self, levels: tuple[str, ...]) -> PopulationID:
        return PopulationID(zip(self.chars, levels))

    def _pop_to_tuple(self, pop: PopulationID) -> tuple[str, ...]:
        return tuple(pop.get(char, UnresolvedCharacteristic()) for char in self.chars)

    def map(
        self, f: Callable[[PopulationID, float], Any], *args, **kwargs
    ) -> Iterator[tuple[PopulationID, Any]]:
        """Map a function over all subpopulations

        Args:
            f (Callable[[PopulationID, float], Any]): The function to be mapped. It
              should take a PopulationID and the population size. If the function
              references a key in the PopulationID that has not been resolved, that
              characteristic will be partitioned and resolved.
            args, kwargs: further arguments passed to `f`

        Yields:
            Iterator: 2-tuples of the population (defined by its `{characteristic: level}`
              dictionary) and the output of `f` for that population
        """
        pop_stack = list(self.pops())

        while pop_stack:
            pop = pop_stack.pop()

            try:
                # get the size (need to do this *before* allowing exception raising)
                size = self.get_size(pop)
                # run the function, raising the unresolved exceptions if needed
                pop.raise_if_unresolved = True
                value = f(pop, size, *args, **kwargs)
                # revert back, so the pop ID has normal functionality
                pop.raise_if_unresolved = False
                yield pop, value
            except UnresolvedCharacteristicException as e:
                # revert back, so the pop ID has normal functionality
                pop.raise_if_unresolved = False
                char_to_resolve = e.args[0]
                new_pops = self.partition(pop, char_to_resolve)
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
        assert not pop.is_resolved(char)

        parent_size = self.get_size(pop)

        new_pops = []
        for level, prop in self.char_props[char].items():
            # new population is the parent population, but with this characteristic at this level
            new_pop = pop | {char: level}
            new_pops.append(new_pop)
            self.set_size(new_pop, prop * parent_size)

        self.delete_pop(pop)
        return new_pops
