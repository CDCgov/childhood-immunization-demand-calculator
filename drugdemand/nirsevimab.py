from drugdemand import Population, DrugDemand, IndependentSubpopulations

import polars as pl
from dateutil.relativedelta import relativedelta
from datetime import date
import warnings


class NirsevimabCalculator:
    """Calculate nirsevimab demand"""

    def __init__(
        self, pars: dict, births: pl.DataFrame, weights: pl.DataFrame, add_pars=False
    ):
        """Initialize and run calculator

        Results stored at .results

        Args:
            pars (dict): Parameter->value mapping
            births (pl.DataFrame): data for birth cohorts. columns are
              `date` (YYYY-MM-DD), and `births`. csv format.
            weights (pl.DataFrame): data for weights by age. columns are
              `age` (in terms of `pars["interval"]`), `p_gt_5kg` (proportion of children
              that are greater than 5kg weight by that age), `interval` (should be same
              as parameter). csv format.
            add_pars: add parameters to results?
        """
        self.pars = pars
        self.births = births
        self.weights = weights
        self.add_pars = add_pars

        # validate pars
        assert all(x in self.pars for x in ["uptake", "p_high_risk", "season_start"])

        # validate data
        assert set(["date", "births"]) <= set(self.births.columns)
        assert isinstance(self.births["date"].dtype, pl.Date)
        assert set(["age", "p_gt_5kg", "interval"]) <= set(self.weights.columns)
        assert all(self.weights["interval"] == pars["interval"])

        self.results = self.calculate(self.pars, self.births, self.weights)

        if add_pars:
            self.results = self.add_pars_to_results(self.results, self.pars)

    @staticmethod
    def age_in_mo(start: date, end: date) -> int:
        """Time between dates, in (floor) months"""
        rd = relativedelta(end, start)
        return rd.months + rd.years * 12

    @staticmethod
    def age_in_wk(start: date, end: date) -> int:
        """Time between dates, in integer (floor) weeks"""
        return (end - start).days // 7

    @classmethod
    def age_in(cls, start: date, end: date, unit: str) -> int:
        """Time between dates, in terms of `unit`"""
        if unit == "month":
            return cls.age_in_mo(start, end)
        elif unit == "week":
            return cls.age_in_wk(start, end)
        else:
            raise NotImplementedError

    @staticmethod
    def relativedelta(x: int, unit: str) -> relativedelta:
        """Interface to dateutils.relativedelta.relativedelta, with more sensible signature"""
        if unit == "month":
            return relativedelta(months=x)
        elif unit == "week":
            return relativedelta(weeks=x)
        else:
            raise NotImplementedError()

    @classmethod
    def calculate_demand(
        cls, pop: PopulationID, size: float, pars: dict
    ) -> DrugDemand | None:
        """Calculate amount and timing of demand, for a single population

        see https://downloads.aap.org/AAP/PDF/Nirsevemab-Visual-Guide.pdf

        Args:
            pop (Population): population that has the demand
            pars (dict): simulation parameters

        Returns:
            DrugDemand: amount and timing of demand, or None
        """
        # if population will not uptake, stop right away
        if not pop.attributes["will_receive"]:
            return None

        # when is the population eligible?
        if pop.attributes["birth_date"] < pars["season_start"]:
            # if born before the season, eligibility date is start of the season
            eligibility_date = pars["season_start"]
        elif pars["season_start"] <= pop.attributes["birth_date"] <= pars["season_end"]:
            # if born during season, eligibility date is birth date
            eligibility_date = pop.attributes["birth_date"]
        elif pars["season_end"] < pop.attributes["birth_date"]:
            # if born after the season, you aren't eligible for anything; return zero demand
            return None

        # compute the immunization date, which is eligibility date plus delay, if any
        if "delay" not in pop.attributes:
            immunization_date = eligibility_date
        else:
            assert "interval" in pars
            assert pop.attributes["delay"] >= 0
            immunization_date = eligibility_date + cls.relativedelta(
                pop.attributes["delay"], pars["interval"]
            )

        # if immunization would be after the season, there is no demand
        if immunization_date > pars["season_end"]:
            return None

        # get age and weight at the immunization date
        # age in months at immunization determines eligibility, even if the simulation uses weeks
        age_mo_at_immunization = cls.age_in(
            pop.attributes["birth_date"], immunization_date, "month"
        )
        # age at immunization (potentially in weeks) is used for weight-for-age calculations
        age_at_immunization = cls.age_in(
            pop.attributes["birth_date"], immunization_date, pars["interval"]
        )
        is_5kg_at_immunization = pop.attributes["age_at_5kg"] <= age_at_immunization

        # some sanity checks
        assert age_mo_at_immunization >= 0
        assert pars["season_start"] <= immunization_date <= pars["season_end"]

        # determine dosage eligibility based on age (in months), weight at time of immunization,
        # and risk level
        if 0 <= age_mo_at_immunization < 8 and not is_5kg_at_immunization:
            return DrugDemand(
                drug_dosage="50mg", n_doses=pop.size, time=immunization_date
            )
        elif 0 <= age_mo_at_immunization < 8 and is_5kg_at_immunization:
            return DrugDemand(
                drug_dosage="100mg", n_doses=pop.size, time=immunization_date
            )
        elif (
            8 <= age_mo_at_immunization < 19 and pop.attributes["risk_level"] == "high"
        ):
            # note the 2xsize here
            return DrugDemand(
                drug_dosage="100mg", n_doses=2 * pop.size, time=immunization_date
            )
        else:
            return None

    @staticmethod
    def validate_delays(delays: dict):
        """Validate delays as used in scenario parameters

        Delays should be in the in form of {delay: proportion}, and proportion
        should add up to 1. Eg, `{0: 0.8, 8: 0.2}` means 80% have 0 delay and 20% have 8 delay
        """
        assert isinstance(delays, dict)
        assert all([isinstance(key, int) for key in delays.keys()])
        assert sum(delays.values()) == 1.0
        return None

    @classmethod
    def calculate(
        cls, pars: dict, births: pl.DataFrame, weights: pl.DataFrame, add_pars=False
    ) -> pl.DataFrame:
        """Calculate demand for cohorts, divided into subpopulations

        Args:
            pars (dict): simulation parameters
            births (pl.DataFrame): births, parsed by __init__
            weights (pl.DataFrame): weights, parsed by __init__
            add_pars (bool): add parameters as columns in output?

        Returns:
            pl.DataFrame: columns include the population attributes and
              demand values (date, dosage, number of doses)
        """
        # construct birth cohorts
        birth_cohorts = [
            Population(
                size=x["births"],
                attributes={"birth_date": x["date"]},
            )
            for x in births.iter_rows(named=True)
        ]

        # parse scenario parameters into attribute levels for the subpopulations. eg, if
        # scenario parameter "uptake" is 80%, that means each population will be subdivided
        # 80/20 into `will_receive=True` and `False` subpopulations.
        subpop_attribute_levels = {
            "will_receive": {True: pars["uptake"], False: 1.0 - pars["uptake"]},
            "risk_level": {
                "high": pars["p_high_risk"],
                "baseline": 1 - pars["p_high_risk"],
            },
            "age_at_5kg": {
                x["age"]: x["p_gt_5kg"] for x in weights.iter_rows(named=True)
            },
        }

        if "delays" in pars:
            cls.validate_delays(pars["delays"])
            # need to do this renaming to avoid collisions on parameter vs. attribute name
            # all other parameters have different names from their corresponding attributes
            # eg "p_high_risk" vs. "risk_level"
            #
            # thus the scenario parameter is called plural "delays", but the population attribute
            # is singular "delay"
            subpop_attribute_levels["delay"] = pars["delays"]

        # generate demand events
        events = [
            {"population": subpop, "demand": cls.calculate_demand(subpop, pars)}
            for birth_cohort in birth_cohorts
            for subpop in iter(
                IndependentSubpopulations(
                    birth_cohort, attribute_levels=subpop_attribute_levels
                )
            )
        ]

        # "results" is a data frame. each row is a demand event, augmented with columns about the
        # population attributes and the scenarios. (this is why we need separate names for scenario
        # parameter, plural "delays" vs. population attribute, singular "delay")
        results = pl.from_dicts(
            {"size": event["population"].size}
            | event["population"].attributes
            | event["demand"].__dict__
            for event in events
            if event["demand"] is not None
        )

        return results

    @staticmethod
    def add_pars_to_results(results: pl.DataFrame, pars: dict) -> pl.DataFrame:
        # check for collisions: there shouldn't be the same column names in the population
        # attributes and the scenario parameters
        assert len(set(results.columns) & set(pars)) == 0

        # change delay into strings
        if "delays" in pars:
            pars["delays"] = str(pars["delays"])

        # convert non-uniform season starts
        for x in ["season_start", "season_end"]:
            if x in pars:
                if isinstance(pars[x], date):
                    pars[x] = str(pars[x])
                else:
                    warnings.warn(
                        f"Converting season date {pars[x]!r} to simply 'non-uniform'"
                    )
                    pars[x] = "non-uniform"

        return results.with_columns(
            [pl.lit(value).alias(key) for key, value in pars.items()]
        )
