"""The NVSR figures, pinned as constants and recompared on every run.

A corroboration recorded in a column is a claim. One that recomputes is a
check. Same reasoning as the input hash tests: a value nobody recomputes agrees
with itself indefinitely, and `corroborated_against` would otherwise be a string
asserting an agreement that nothing re-establishes.

**These figures were read out of the PDFs by a person**, each appearing twice
per report -- once in a narrative sentence and once in Table B -- with the two
agreeing. That reading is the evidence; this file is what stops it rotting.

WHAT THIS DOES NOT ESTABLISH
----------------------------
NVSR and WONDER are **not independent of each other**. Both are NCHS products
drawing on the same underlying mortality file and the same Census-derived
denominators. Agreement here establishes that our query returned what NCHS
published in its own report of record. It is not independent confirmation, and
it is not evidence that NCHS is correct. See docs/denominator-methods.md,
"What the NVSR corroboration does and does not establish".
"""
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

# year -> (total deaths, crude rate per 100,000, NVSR volume-issue)
# Table B of "Deaths: Final Data for <year>". Read 2026-08-30.
NVSR: dict[int, tuple[int, float, str]] = {
    2010: (2_468_435, 799.5, "61-4"),
    2011: (2_515_458, 807.3, "63-3"),
    2012: (2_543_279, 810.2, "63-9"),
    2013: (2_596_993, 821.5, "64-2"),
    2014: (2_626_418, 823.7, "65-4"),
    2015: (2_712_630, 844.0, "66-6"),
    2016: (2_744_248, 849.3, "67-5"),
    2017: (2_813_503, 863.8, "68-9"),
    2018: (2_839_205, 867.8, "69-13"),
    2019: (2_854_838, 869.7, "70-8"),
    2020: (3_383_729, 1027.0, "72-10"),
    2021: (3_464_231, 1043.8, "73-8"),
    2022: (3_279_857, 984.1, "74-4"),
}

# No "Deaths: Final Data" report exists for these yet; the lag runs about three
# years. Blank corroboration for them is correct, not an omission.
UNCORROBORATED_YEARS = (2023, 2024)

# NVSR prints the crude rate to one decimal, so that is the precision at which
# agreement can be judged.
RATE_DECIMALS = 1


@pytest.fixture(scope="module")
def annual():
    return pd.read_csv(RAW / "us_annual_deaths.csv").set_index("year")


@pytest.fixture(scope="module")
def population():
    return pd.read_csv(RAW / "us_population.csv").set_index("year")


def test_every_nvsr_total_matches_the_committed_deaths(annual):
    """Thirteen years, exact. NVSR totals include age-not-stated, as we do."""
    for year, (deaths, _, vol) in NVSR.items():
        assert int(annual.loc[year, "deaths"]) == deaths, f"{year} (NVSR {vol})"


def test_every_nvsr_crude_rate_matches_our_computed_rate(annual, population):
    """Recomputed from deaths and population, not read from a column."""
    for year, (_, rate, vol) in NVSR.items():
        deaths = int(annual.loc[year, "deaths"])
        pop = int(population.loc[year, "population"])
        computed = round(deaths / pop * 100_000, RATE_DECIMALS)
        assert computed == pytest.approx(rate, abs=10 ** -RATE_DECIMALS / 2), (
            f"{year} (NVSR {vol}): computed {computed}, NVSR published {rate}"
        )


def test_rate_agreement_implies_the_denominators_agree(annual, population):
    """The finding this corroboration actually produces.

    Neither publication prints the other's population beside its rate. But a
    rate is deaths over population: with the deaths matching exactly and the
    rate matching to NVSR's printed precision across all thirteen years, the
    denominators must agree to within the rounding of the rate. That is
    inference about the denominator, which is why us_population.csv is NOT
    marked corroborated -- the column records what a document states.
    """
    for year, (deaths, rate, _) in NVSR.items():
        pop = int(population.loc[year, "population"])
        # The population NVSR must have used, to reproduce its printed rate.
        implied_low = deaths / ((rate + 0.05) / 100_000)
        implied_high = deaths / ((rate - 0.05) / 100_000)
        assert implied_low <= pop <= implied_high, (
            f"{year}: our population {pop:,} is outside the range NVSR's "
            f"published rate of {rate} implies "
            f"({implied_low:,.0f} to {implied_high:,.0f})"
        )


def test_the_recorded_citations_name_the_right_volume(annual):
    """The column must agree with the constants above, volume by volume."""
    for year, (_, _, vol) in NVSR.items():
        recorded = str(annual.loc[year, "corroborated_against"])
        volume, number = vol.split("-")
        assert f"Vol. {volume} No. {number}" in recorded, (
            f"{year}: recorded {recorded!r} does not name NVSR {vol}"
        )
        assert "Table B" in recorded


def test_exactly_the_expected_years_are_corroborated(annual):
    recorded = set(annual.index[annual["corroborated_against"].notna()])
    assert recorded == set(NVSR)
    for year in UNCORROBORATED_YEARS:
        assert pd.isna(annual.loc[year, "corroborated_against"]), (
            f"{year} has no published Deaths: Final Data report; blank is "
            f"correct and must not be filled from a weaker source"
        )


def test_corroboration_did_not_reach_the_other_files():
    """Only the annual totals were checked against Table B.

    deaths_by_age carries 2010 alone, from NVSR 61-4 Table 10. The other twelve
    reports were read for Table B only, so their age distributions are not
    corroborated and must not be marked as though they were.
    """
    by_age = pd.read_csv(RAW / "deaths_by_age.csv")
    marked = by_age[by_age["corroborated_against"].notna()]
    assert set(marked["year"]) == {2010}
    assert len(marked) == 6, "the six bands of 2010"

    for name in ("us_population.csv", "covid_deaths_by_age.csv"):
        frame = pd.read_csv(RAW / name)
        assert frame["corroborated_against"].isna().all(), (
            f"{name} is not corroborated; recovering a denominator by division "
            f"is an inference, not a document stating a figure"
        )
