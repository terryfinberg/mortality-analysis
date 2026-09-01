"""Crude and age-adjusted mortality rates.

Age adjustment uses direct standardization against the 2000 U.S.
Standard Population, which is the convention NCHS uses and therefore the
one that makes these numbers comparable to published figures.
"""
from __future__ import annotations

import pandas as pd

PER = 100_000


def crude_rate(deaths: pd.DataFrame, population: pd.DataFrame) -> pd.DataFrame:
    """Deaths per 100,000 resident population, by year."""
    df = deaths.merge(population, on="year", validate="one_to_one")
    df["crude_rate"] = df["deaths"] / df["population"] * PER
    return df[["year", "deaths", "population", "crude_rate"]]


def age_specific_rates(by_age: pd.DataFrame) -> pd.DataFrame:
    """Deaths per 100,000 within each age group."""
    df = by_age.copy()
    df["rate"] = df["deaths"] / df["population"] * PER
    return df


def age_adjusted_rate(by_age: pd.DataFrame, standard_pop: pd.Series) -> pd.DataFrame:
    """Directly standardized rate per 100,000, by year.

    R_adj(t) = sum_a [ m_a(t) * w_a ] where w_a is the standard
    population share and m_a(t) the age-specific rate.

    Raises if the two age-group vocabularies are not identical. The weights
    are normalized over all of ``standard_pop`` before the join below, which
    is an inner join, so a band present in one input and not the other would
    be dropped from the sum while its weight remained in the denominator that
    produced every other weight. The result is a partial sum reported as a
    directly standardized rate: biased downward, still plausible, and not
    caught by ``validate="many_to_one"``, which checks uniqueness rather than
    coverage. The loader already refuses an incomplete grid; this is the
    second line, for callers that build a frame themselves.
    """
    rates = age_specific_rates(by_age)

    have = set(rates["age_group"])
    want = set(standard_pop.index)
    if have != want:
        raise ValueError(
            "age_adjusted_rate needs the same age groups on both sides.\n"
            f"  in standard_pop, absent from by_age: {sorted(want - have) or 'none'}\n"
            f"  in by_age, absent from standard_pop: {sorted(have - want) or 'none'}\n"
            "Standardizing across a mismatched vocabulary yields a partial "
            "sum, not a standardized rate."
        )

    w = standard_pop / standard_pop.sum()
    rates = rates.merge(
        w.rename("weight").reset_index().rename(columns={"index": "age_group"}),
        on="age_group",
        validate="many_to_one",
    )
    rates["contribution"] = rates["rate"] * rates["weight"]
    out = rates.groupby("year", as_index=False)["contribution"].sum()
    return out.rename(columns={"contribution": "age_adjusted_rate"})


def population_shares(by_age: pd.DataFrame) -> pd.DataFrame:
    """Share of total population in each age group, by year."""
    df = by_age.copy()
    totals = df.groupby("year")["population"].transform("sum")
    df["share"] = df["population"] / totals
    return df[["year", "age_group", "share"]]
