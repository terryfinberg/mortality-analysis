"""Synthetic fixtures.

These are invented numbers with known analytic properties, used to prove
the math is correct. They are deliberately NOT plausible U.S. values, so
nobody can mistake a test fixture for real data.
"""
import pandas as pd
import pytest

AGES = ["0-24", "25-44", "45-64", "65-74", "75-84", "85+"]


@pytest.fixture
def standard_pop():
    return pd.Series(
        [353346, 298186, 222081, 66037, 44842, 15508],
        index=AGES,
        name="weight_per_million",
    )


@pytest.fixture
def by_age_stationary():
    """Two years, identical rates and identical age structure.

    Both Kitagawa components must be exactly zero.
    """
    rows = []
    for year in (2000, 2001):
        for age, deaths, pop in [
            ("0-24", 100, 1_000_000),
            ("25-44", 200, 1_000_000),
            ("45-64", 800, 1_000_000),
            ("65-74", 1500, 500_000),
            ("75-84", 3000, 300_000),
            ("85+", 5000, 100_000),
        ]:
            rows.append({"year": year, "age_group": age,
                         "deaths": deaths, "population": pop})
    return pd.DataFrame(rows)


@pytest.fixture
def by_age_aging_only():
    """Age-specific rates held constant; population shifts older.

    rate_effect must be 0; age_effect must equal the whole change.
    """
    rows = []
    pops = {
        2000: {"0-24": 1_000_000, "25-44": 1_000_000, "45-64": 1_000_000,
               "65-74": 500_000, "75-84": 300_000, "85+": 100_000},
        2001: {"0-24": 900_000, "25-44": 950_000, "45-64": 1_000_000,
               "65-74": 600_000, "75-84": 400_000, "85+": 150_000},
    }
    # deaths per 100k, held fixed across years
    rates = {"0-24": 10, "25-44": 20, "45-64": 80,
             "65-74": 300, "75-84": 1000, "85+": 5000}
    for year, pmap in pops.items():
        for age, pop in pmap.items():
            rows.append({
                "year": year, "age_group": age,
                "deaths": int(round(rates[age] * pop / 100_000)),
                "population": pop,
            })
    return pd.DataFrame(rows)


@pytest.fixture
def linear_adjusted():
    """Age-adjusted rate rising exactly 5.0 per year from 800.0."""
    return pd.DataFrame({
        "year": list(range(2010, 2020)),
        "age_adjusted_rate": [800.0 + 5.0 * (y - 2010) for y in range(2010, 2020)],
    })
