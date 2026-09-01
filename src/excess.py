"""Excess mortality against a pre-pandemic baseline.

Method: fit a linear trend in the age-adjusted rate over the baseline
window, project it forward, convert the projected rate back to a count
using observed population, and take observed minus expected.

Projecting the age-adjusted rate rather than the raw count matters. A
count-based baseline attributes the mechanical effect of population
aging to the pandemic, which inflates excess-death estimates. This
choice is defensible but not universal, so it is stated explicitly in
the manuscript and the sensitivity of results to the baseline window is
reported.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ExcessResult:
    table: pd.DataFrame
    baseline_years: tuple[int, int]
    slope_per_year: float
    intercept: float

    def total_excess(self, start: int, end: int) -> float:
        m = self.table["year"].between(start, end)
        return float(self.table.loc[m, "excess_deaths"].sum())


def fit_baseline(
    adjusted: pd.DataFrame, baseline_start: int, baseline_end: int
) -> tuple[float, float]:
    """Least-squares linear fit of age-adjusted rate on year."""
    m = adjusted["year"].between(baseline_start, baseline_end)
    sub = adjusted.loc[m]
    if len(sub) < 3:
        raise ValueError(
            f"baseline window {baseline_start}-{baseline_end} has only "
            f"{len(sub)} year(s); need at least 3 for a defensible trend"
        )
    slope, intercept = np.polyfit(sub["year"], sub["age_adjusted_rate"], 1)
    return float(slope), float(intercept)


def excess_mortality(
    adjusted: pd.DataFrame,
    observed_deaths: pd.DataFrame,
    population: pd.DataFrame,
    baseline_start: int = 2010,
    baseline_end: int = 2019,
) -> ExcessResult:
    """Observed minus expected deaths, by year.

    Takes the age-adjusted series rather than recomputing it. ``by_age`` and
    ``standard_pop`` used to sit in this signature and were never read, which
    advertised a direct-standardization step this function does not perform;
    callers had to build both to have them discarded. If you need the two to
    be guaranteed consistent, compute ``adjusted`` with
    ``rates.age_adjusted_rate`` and pass the result straight through.
    """
    slope, intercept = fit_baseline(adjusted, baseline_start, baseline_end)

    df = adjusted.merge(observed_deaths, on="year", validate="one_to_one")
    df = df.merge(population, on="year", validate="one_to_one")

    df["expected_rate"] = intercept + slope * df["year"]

    # Convert expected age-adjusted rate back to a count by scaling the
    # observed count by the ratio of expected to observed adjusted rate.
    df["expected_deaths"] = df["deaths"] * (
        df["expected_rate"] / df["age_adjusted_rate"]
    )
    df["excess_deaths"] = df["deaths"] - df["expected_deaths"]
    df["excess_pct"] = df["excess_deaths"] / df["expected_deaths"] * 100

    cols = [
        "year", "deaths", "population", "age_adjusted_rate",
        "expected_rate", "expected_deaths", "excess_deaths", "excess_pct",
    ]
    return ExcessResult(
        table=df[cols].sort_values("year").reset_index(drop=True),
        baseline_years=(baseline_start, baseline_end),
        slope_per_year=slope,
        intercept=intercept,
    )


def covid_share_by_age(covid: pd.DataFrame, years: list[int] | None = None) -> pd.DataFrame:
    """Share of COVID-19 deaths falling in each age group."""
    df = covid.copy()
    if years is not None:
        df = df[df["year"].isin(years)]
    agg = df.groupby("age_group", as_index=False)["covid_deaths"].sum()
    agg["share_pct"] = agg["covid_deaths"] / agg["covid_deaths"].sum() * 100
    return agg.sort_values("share_pct", ascending=False).reset_index(drop=True)
