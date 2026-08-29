"""Kitagawa decomposition of a change in the crude death rate.

The crude rate can move because age-specific mortality changed, because
the age structure of the population changed, or both. Kitagawa (1955)
splits the difference between two periods into exactly those two
components plus nothing else -- the decomposition is exact, not
approximate, which is why the additivity check in the tests is an
equality rather than a tolerance.

Reference: Kitagawa EM. Components of a difference between two rates.
Journal of the American Statistical Association 1955;50(272):1168-1194.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .rates import PER, age_specific_rates, population_shares


@dataclass
class KitagawaResult:
    year_start: int
    year_end: int
    crude_start: float
    crude_end: float
    total_change: float
    rate_effect: float
    age_effect: float

    @property
    def ratio(self) -> float:
        """Magnitude of age effect relative to rate effect.

        Reported as a ratio in the paper. Returns inf when the rate
        effect is zero rather than raising, since that is a meaningful
        (if degenerate) result.
        """
        if self.rate_effect == 0:
            return float("inf")
        return abs(self.age_effect / self.rate_effect)

    def summary(self) -> str:
        return (
            f"{self.year_start}->{self.year_end}: crude rate "
            f"{self.crude_start:.1f} -> {self.crude_end:.1f} per 100k "
            f"(change {self.total_change:+.1f}); "
            f"rate effect {self.rate_effect:+.1f}, "
            f"age effect {self.age_effect:+.1f}"
        )


def kitagawa(by_age: pd.DataFrame, year_start: int, year_end: int) -> KitagawaResult:
    """Decompose the crude-rate change between two years.

    rate_effect = sum_a [ (m_a1 - m_a0) * (w_a0 + w_a1)/2 ]
    age_effect  = sum_a [ (w_a1 - w_a0) * (m_a0 + m_a1)/2 ]

    These sum exactly to the change in the crude rate.
    """
    for y in (year_start, year_end):
        if y not in set(by_age["year"]):
            raise ValueError(f"year {y} not present in dataset")

    rates = age_specific_rates(by_age)
    shares = population_shares(by_age)
    df = rates.merge(shares, on=["year", "age_group"], validate="one_to_one")

    a = df[df["year"] == year_start].set_index("age_group")
    b = df[df["year"] == year_end].set_index("age_group")
    idx = a.index.intersection(b.index)
    a, b = a.loc[idx], b.loc[idx]

    rate_effect = ((b["rate"] - a["rate"]) * (a["share"] + b["share"]) / 2).sum()
    age_effect = ((b["share"] - a["share"]) * (a["rate"] + b["rate"]) / 2).sum()

    crude_start = (a["rate"] * a["share"]).sum()
    crude_end = (b["rate"] * b["share"]).sum()

    return KitagawaResult(
        year_start=year_start,
        year_end=year_end,
        crude_start=float(crude_start),
        crude_end=float(crude_end),
        total_change=float(crude_end - crude_start),
        rate_effect=float(rate_effect),
        age_effect=float(age_effect),
    )
