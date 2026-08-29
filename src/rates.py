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
    """
    rates = age_specific_rates(by_age)
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
