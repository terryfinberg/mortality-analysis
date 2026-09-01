"""Baseline fitting and excess mortality.

Tolerance policy: a quantity **defined** to be equal is asserted equal, at
1e-9 for floating-point representation only; a quantity merely **expected to be
close** gets a real tolerance. The 1e-6 on the fitted slope below is the one
genuine tolerance in this file -- a least-squares solve is not exact
arithmetic. Do not loosen the 1e-9s.
"""
import pandas as pd
import pytest

from src import excess


def test_baseline_recovers_known_slope(linear_adjusted):
    slope, intercept = excess.fit_baseline(linear_adjusted, 2010, 2019)
    assert abs(slope - 5.0) < 1e-6
    assert abs((intercept + slope * 2010) - 800.0) < 1e-6


def test_short_baseline_window_raises(linear_adjusted):
    with pytest.raises(ValueError, match="at least 3"):
        excess.fit_baseline(linear_adjusted, 2010, 2011)


def test_zero_excess_when_observed_matches_trend(linear_adjusted):
    """A year sitting exactly on the fitted trend must show zero excess."""
    adjusted = linear_adjusted.copy()
    deaths = pd.DataFrame({
        "year": adjusted["year"],
        "deaths": [1_000_000] * len(adjusted),
    })
    pop = pd.DataFrame({
        "year": adjusted["year"],
        "population": [100_000_000] * len(adjusted),
    })
    res = excess.excess_mortality(
        adjusted, deaths, pop,
        baseline_start=2010, baseline_end=2019,
    )
    # Sitting exactly on the fitted trend means excess is exactly zero, not
    # approximately zero. Measured residual is 0.0; the tolerance was 1.0.
    assert res.table["excess_deaths"].abs().max() < 1e-9


def test_covid_share_sums_to_100():
    covid = pd.DataFrame({
        "year": [2020] * 3,
        "age_group": ["0-24", "65-74", "85+"],
        "covid_deaths": [100, 400, 500],
    })
    out = excess.covid_share_by_age(covid)
    assert abs(out["share_pct"].sum() - 100.0) < 1e-9
    assert out.iloc[0]["age_group"] == "85+"
