"""The three treatments of the 2010 measurement basis, computed.

Why this module exists
----------------------
WONDER carries the **April 1 decennial count** for 2010 and a **July 1 estimate**
for every other year. That one-year difference in measurement basis sits at the
left end of the pre-pandemic baseline window, where it has the most leverage on
a fitted slope. The paper therefore reports a range across three treatments
rather than a point estimate:

    A   as published     2010-2019, WONDER exactly as published
    B   2010 excluded    2011-2019, dropping the year with the odd basis
    C'  published July 1 2010-2019, 2010's denominator replaced with the
                         Census Bureau's published July 1 2010 estimate

These figures existed in ``docs/denominator-methods.md`` as a table of asserted
numbers that nothing in the repository produced. Rows B and C' appeared nowhere
in ``src/`` or ``tests/``, which meant the robustness range the manuscript rests
on -- "the age-to-rate ratio falls between 3.41 and 3.87" -- was half computed
and half typed. This module computes all three.

**When first computed, all three reproduced the asserted values exactly.** That
is recorded because it is the outcome that makes the previous state forgivable,
not because it was assumed: had they differed, the difference would have been
the finding.

The denominators
----------------
Both 2010 columns come from one Census file, ``nc-est2020-agesex-res.csv``,
which carries ``CENSUS2010POP`` (April 1) beside ``POPESTIMATE2010`` (July 1).
:func:`assert_wonder_2010_is_the_decennial_count` checks the April 1 column
against WONDER band by band before anything is computed from the July 1 one --
if they disagreed, the premise of treatment C' would be wrong and its result
meaningless.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import census, decomposition, excess, rates
from .loader import AGE_GROUPS

# The vintage carrying both 2010 columns. See the note in census.CENSUS_VINTAGES:
# the 2010-2019 directory has no age/sex file at all.
CENSUS_VINTAGE_2010 = 2020

BASE_YEAR = 2010
PRE_PANDEMIC_END = 2019
# Excess is summed over the two pandemic peak years, which is the window the
# manuscript quotes and the one the treatments are compared on.
EXCESS_WINDOW = (2020, 2021)


class TreatmentError(RuntimeError):
    """A treatment could not be computed from the inputs on disk."""


@dataclass
class Treatment:
    """One treatment of the 2010 basis, and what it does to the results."""

    key: str
    label: str
    interval: tuple[int, int]
    baseline_slope: float
    excess_2020_2021: float
    age_effect: float
    rate_effect: float
    age_to_rate_ratio: float

    @property
    def interval_label(self) -> str:
        return f"{self.interval[0]}-{self.interval[1]}"


def july_1_2010_by_band(census_dir=None) -> pd.Series:
    """Census's published July 1 2010 resident population, on the six bands."""
    return census.collapse_to_bands(CENSUS_VINTAGE_2010, BASE_YEAR, census_dir)


def april_1_2010_by_band(census_dir=None) -> pd.Series:
    """The April 1 2010 decennial count, on the six bands."""
    return census.collapse_to_bands(
        CENSUS_VINTAGE_2010, BASE_YEAR, census_dir,
        column=census.DECENNIAL_2010_COLUMN,
    )


def assert_wonder_2010_is_the_decennial_count(by_age: pd.DataFrame, census_dir=None):
    """WONDER's 2010 population must equal the April 1 decennial count exactly.

    The whole premise of treatment C' is that WONDER's 2010 is an April 1 count
    while its neighbours are July 1 estimates. If that is not true band for
    band, replacing 2010 with the July 1 figure is not a measurement-basis
    correction, it is an unexplained substitution, and the range it produces
    means nothing. Checked before C' is computed, not after.
    """
    april = april_1_2010_by_band(census_dir)
    wonder = by_age[by_age["year"] == BASE_YEAR].set_index("age_group")["population"]

    bad = []
    for group in AGE_GROUPS:
        a, w = int(april[group]), int(wonder[group])
        if a != w:
            bad.append(f"  {group}: Census April 1 {a:,}, WONDER {w:,} ({w - a:+,})")
    if bad:
        raise TreatmentError(
            "WONDER's 2010 population is not the April 1 decennial count:\n"
            + "\n".join(bad)
            + "\nTreatment C' assumes it is. Resolve this before using the "
            "robustness range."
        )
    return pd.DataFrame({
        "age_group": AGE_GROUPS,
        "april_1": [int(april[g]) for g in AGE_GROUPS],
        "wonder": [int(wonder[g]) for g in AGE_GROUPS],
    })


def _measure(key, label, by_age, annual, population, standard_pop,
             baseline, interval) -> Treatment:
    adjusted = rates.age_adjusted_rate(by_age, standard_pop)
    ex = excess.excess_mortality(
        adjusted, annual, population,
        baseline_start=baseline[0], baseline_end=baseline[1],
    )
    kit = decomposition.kitagawa(by_age, interval[0], interval[1])
    return Treatment(
        key=key,
        label=label,
        interval=interval,
        baseline_slope=ex.slope_per_year,
        excess_2020_2021=ex.total_excess(*EXCESS_WINDOW),
        age_effect=kit.age_effect,
        rate_effect=kit.rate_effect,
        age_to_rate_ratio=kit.ratio,
    )


def compute_treatments(
    by_age: pd.DataFrame,
    annual_deaths: pd.DataFrame,
    population: pd.DataFrame,
    standard_pop: pd.Series,
    census_dir=None,
) -> list[Treatment]:
    """A, B and C', in the order the manuscript reports them."""
    annual = annual_deaths[["year", "deaths"]]
    assert_wonder_2010_is_the_decennial_count(by_age, census_dir)

    out = [
        _measure("A", "as published", by_age, annual, population, standard_pop,
                 baseline=(BASE_YEAR, PRE_PANDEMIC_END),
                 interval=(BASE_YEAR, PRE_PANDEMIC_END)),
    ]

    # B: drop 2010 entirely, from every input, so nothing about it can leak in.
    keep = lambda f: f[f["year"] != BASE_YEAR]  # noqa: E731
    out.append(_measure(
        "B", "2010 excluded", keep(by_age), keep(annual), keep(population),
        standard_pop, baseline=(BASE_YEAR + 1, PRE_PANDEMIC_END),
        interval=(BASE_YEAR + 1, PRE_PANDEMIC_END),
    ))

    # C': same years as A, but 2010's denominator is the July 1 estimate.
    july = july_1_2010_by_band(census_dir)
    c_by_age = by_age.copy()
    mask = c_by_age["year"] == BASE_YEAR
    c_by_age.loc[mask, "population"] = (
        c_by_age.loc[mask, "age_group"].map(july).astype("int64").values
    )
    c_population = population.copy()
    c_population.loc[c_population["year"] == BASE_YEAR, "population"] = int(july.sum())
    out.append(_measure(
        "C'", "published July 1", c_by_age, annual, c_population, standard_pop,
        baseline=(BASE_YEAR, PRE_PANDEMIC_END),
        interval=(BASE_YEAR, PRE_PANDEMIC_END),
    ))
    return out


def ratio_range(treatments: list[Treatment]) -> tuple[float, float]:
    """The reported robustness range: lowest and highest age-to-rate ratio."""
    ratios = [t.age_to_rate_ratio for t in treatments]
    return min(ratios), max(ratios)


def render_table(treatments: list[Treatment]) -> list[str]:
    """The markdown table in docs/denominator-methods.md, generated."""
    header = ["treatment", "interval", "slope", "excess 2020-21",
              "age-to-rate ratio"]
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] * len(header)) + "|"]
    for t in treatments:
        lines.append("| " + " | ".join([
            f"{t.key} {t.label}",
            t.interval_label,
            f"{t.baseline_slope:.3f}".replace("-", "−"),
            f"{t.excess_2020_2021:,.0f}",
            f"{t.age_to_rate_ratio:.3f}",
        ]) + " |")
    return lines


def main(argv: list[str] | None = None) -> int:
    """Print the table, for pasting into docs/denominator-methods.md."""
    from . import loader

    ds = loader.load_all(strict=False)
    ts = compute_treatments(
        ds.by_age, ds.annual_deaths, ds.population, ds.standard_pop
    )
    print("\n".join(render_table(ts)))
    lo, hi = ratio_range(ts)
    print(f"\nage-to-rate range: {lo:.3f} to {hi:.3f} "
          f"(reported as {round(lo, 2):.2f}-{round(hi, 2):.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
