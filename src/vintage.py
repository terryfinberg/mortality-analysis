"""Vintage sensitivity: what a denominator restatement does to the results.

This module computes every number in section 2 of ``docs/denominator-methods.md``
("Vintage 2024 methodology restatement"). It exists so those numbers are derived
rather than quoted -- the doc makes claims about the most recent year in the
paper, and a claim nobody can regenerate is exactly the failure this repository
was rebuilt to remove. ``tests/test_vintage.py`` asserts that the tables in the
doc still match what this module computes, so a change to a band mapping either
moves the doc or fails the suite.

Three questions, in order:

1. **Is the restatement uniform across age bands?** A uniform revision leaves
   the population shares untouched, so Kitagawa books the whole thing as a rate
   effect and it reads as a mortality change that never happened. A non-uniform
   one moves shares and part lands in the age effect. The national total cannot
   distinguish these -- see ``assess_vintage_uniformity`` in :mod:`src.fetch`.

2. **How much of the published 2023->2024 change is restatement?** Answered by
   running the decomposition twice, identically except for the 2023 denominator.

3. **Is there a stable vintage to rebase onto?** No. Question 3 is why this
   analysis reports a range instead of rebasing the series.

Run ``python -m src.vintage`` to print all three tables.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import census, fetch
from .decomposition import KitagawaResult, kitagawa
from .loader import AGE_GROUPS

# The reference year WONDER carries at Vintage 2023 and Census V2024 restates.
RESTATED_YEAR = 2023
# The year the restated one is compared against. WONDER carries it at V2024.
COMPARISON_YEAR = 2024

# WONDER's own vintage for RESTATED_YEAR, per export 2's footer.
WONDER_VINTAGE = 2023
RESTATING_VINTAGE = 2024
# The vintage that restates again, which is the point of finding 3.
LATEST_VINTAGE = 2025


class VintageError(RuntimeError):
    """A vintage comparison could not be made from the inputs on disk."""


# ---------------------------------------------------------------------------
# Formatting -- matches the doc, so rendered rows can be checked against it
# ---------------------------------------------------------------------------

MINUS = "−"  # U+2212, the minus sign the docs use, not a hyphen


def signed(value: float, decimals: int = 0, comma: bool = True) -> str:
    """Format with an explicit sign, using the docs' Unicode minus."""
    fmt = f",.{decimals}f" if comma else f".{decimals}f"
    text = format(abs(value), fmt)
    return f"{MINUS}{text}" if value < 0 else f"+{text}"


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _rule(n: int) -> str:
    return "|" + "|".join(["---"] * n) + "|"


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def wonder_by_age(export_dir=None) -> pd.DataFrame:
    """The single-race grid: year, age_group, deaths, population.

    Population here is WONDER's, which means each year at its own vintage --
    2023 at Vintage 2023 and 2024 at Vintage 2024.
    """
    spec = next(
        s for s in fetch.GRID_EXPORTS
        if s.series == "deaths_by_age" and RESTATED_YEAR in s.years
    )
    collapsed = fetch.load_grid_for(spec, export_dir)
    if collapsed is None:
        raise VintageError(
            f"{spec.filename} is not present, so no vintage comparison can be "
            f"made. It is a committed export; restore it from git."
        )
    return collapsed.frame


def assert_wonder_matches_census(export_dir=None, census_dir=None) -> pd.DataFrame:
    """WONDER's 2024 must equal Census V2024's 2024, band for band.

    WONDER's footer states it carries 2024 from Vintage 2024, so this has to
    hold exactly. It is the check that validates the age->band collapse in
    :mod:`src.census` against an independent source **before** anything is
    computed from it: if single-year Census ages were being folded onto the six
    bands incorrectly, the error would be invisible in six plausible-looking
    numbers and obvious here.

    Returns the per-band comparison. Raises on any disagreement.
    """
    wonder = wonder_by_age(export_dir)
    w = wonder[wonder["year"] == COMPARISON_YEAR].set_index("age_group")
    c = census.collapse_to_bands(RESTATING_VINTAGE, COMPARISON_YEAR, census_dir)

    frame = pd.DataFrame({
        "age_group": AGE_GROUPS,
        "wonder": [int(w.loc[g, "population"]) for g in AGE_GROUPS],
        "census": [int(c[g]) for g in AGE_GROUPS],
    })
    frame["difference"] = frame["census"] - frame["wonder"]

    bad = frame[frame["difference"] != 0]
    if not bad.empty:
        rows = "\n".join(
            f"  {r['age_group']}: WONDER {r['wonder']:,}, Census "
            f"{r['census']:,} ({r['difference']:+,})"
            for _, r in bad.iterrows()
        )
        raise VintageError(
            f"WONDER's {COMPARISON_YEAR} population disagrees with Census "
            f"Vintage {RESTATING_VINTAGE} in {len(bad)} band(s):\n{rows}\n"
            f"WONDER's footer says it carries {COMPARISON_YEAR} from Vintage "
            f"{RESTATING_VINTAGE}, so these must be equal. Either the age->band "
            f"collapse in src/census.py (BAND_EDGES) is wrong, or the two "
            f"sources are no longer the same vintage. Nothing downstream of "
            f"this is trustworthy until it is resolved."
        )
    return frame


# ---------------------------------------------------------------------------
# 1. Uniformity of the restatement
# ---------------------------------------------------------------------------


def restatement_uniformity(export_dir=None, census_dir=None):
    """Is the V2023 -> V2024 restatement of 2023 even across the age bands?

    Builds the frame ``assess_vintage_uniformity`` expects, labelling the two
    populations by **vintage** rather than by calendar year: both are the
    population of ``RESTATED_YEAR``, read off two different vintages.
    """
    wonder = wonder_by_age(export_dir)
    w = wonder[wonder["year"] == RESTATED_YEAR].set_index("age_group")
    restated = census.collapse_to_bands(RESTATING_VINTAGE, RESTATED_YEAR, census_dir)

    frame = pd.concat([
        pd.DataFrame({
            "year": WONDER_VINTAGE,
            "age_group": AGE_GROUPS,
            "population": [int(w.loc[g, "population"]) for g in AGE_GROUPS],
        }),
        pd.DataFrame({
            "year": RESTATING_VINTAGE,
            "age_group": AGE_GROUPS,
            "population": [int(restated[g]) for g in AGE_GROUPS],
        }),
    ], ignore_index=True)

    return fetch.assess_vintage_uniformity(frame, WONDER_VINTAGE, RESTATING_VINTAGE)


def render_restatement_table(export_dir=None, census_dir=None) -> list[str]:
    u = restatement_uniformity(export_dir, census_dir)
    lines = [
        _row(["band", f"V{WONDER_VINTAGE} (WONDER)", f"V{RESTATING_VINTAGE}",
              "change", ""]),
        _rule(5),
    ]
    for _, r in u.frame.iterrows():
        lines.append(_row([
            str(r["age_group"]),
            f"{int(r['pop_a']):,}",
            f"{int(r['pop_b']):,}",
            signed(int(r["abs_change"])),
            signed(r["pct_change"], 3) + "%",
        ]))
    return lines


# ---------------------------------------------------------------------------
# 2. The two-treatment Kitagawa
# ---------------------------------------------------------------------------


@dataclass
class Treatments:
    """The same decomposition under two denominator bases for the earlier year."""

    published: KitagawaResult
    restated: KitagawaResult

    @property
    def total_shift(self) -> float:
        return self.restated.total_change - self.published.total_change

    @property
    def rate_shift(self) -> float:
        return self.restated.rate_effect - self.published.rate_effect

    @property
    def age_shift(self) -> float:
        return self.restated.age_effect - self.published.age_effect

    @property
    def restatement_share_of_decline(self) -> float:
        """Restatement as a percentage of the published change."""
        return 100.0 * self.total_shift / -self.published.total_change

    @property
    def rate_share_of_restatement(self) -> float:
        return 100.0 * self.rate_shift / self.total_shift

    @property
    def age_share_of_restatement(self) -> float:
        return 100.0 * self.age_shift / self.total_shift


def kitagawa_treatments(export_dir=None, census_dir=None) -> Treatments:
    """Decompose 2023->2024 twice, differing only in the 2023 denominator.

    A. **as published** -- 2023 at Vintage 2023 as WONDER carries it.
    B. **consistent**   -- 2023 restated to Vintage 2024.

    Deaths are identical in both. They are the same certificates; only the
    denominator moved. Any difference between A and B is therefore entirely an
    artifact of the population revision, which is what makes the pair
    interpretable at all.
    """
    assert_wonder_matches_census(export_dir, census_dir)

    wonder = wonder_by_age(export_dir)
    published = wonder[
        wonder["year"].isin((RESTATED_YEAR, COMPARISON_YEAR))
    ][["year", "age_group", "deaths", "population"]].copy()

    restated_pop = census.collapse_to_bands(
        RESTATING_VINTAGE, RESTATED_YEAR, census_dir
    )
    restated = published.copy()
    mask = restated["year"] == RESTATED_YEAR
    restated.loc[mask, "population"] = (
        restated.loc[mask, "age_group"].map(restated_pop).astype(int).values
    )

    return Treatments(
        published=kitagawa(published, RESTATED_YEAR, COMPARISON_YEAR),
        restated=kitagawa(restated, RESTATED_YEAR, COMPARISON_YEAR),
    )


def render_kitagawa_table(export_dir=None, census_dir=None) -> list[str]:
    t = kitagawa_treatments(export_dir, census_dir)
    lines = [
        _row(["", f"crude {RESTATED_YEAR}", f"crude {COMPARISON_YEAR}", "change",
              "rate effect", "age effect", "age/rate"]),
        _rule(7),
    ]
    for label, k in (
        ("A as published", t.published),
        (f"B {RESTATED_YEAR} at V{RESTATING_VINTAGE}", t.restated),
    ):
        lines.append(_row([
            label,
            f"{k.crude_start:.1f}",
            f"{k.crude_end:.1f}",
            signed(k.total_change, 2),
            signed(k.rate_effect, 2),
            signed(k.age_effect, 2),
            f"{k.ratio:.3f}",
        ]))
    return lines


# ---------------------------------------------------------------------------
# 3. No terminal vintage
# ---------------------------------------------------------------------------


def series_restatement(
    from_vintage: int = RESTATING_VINTAGE,
    to_vintage: int = LATEST_VINTAGE,
    census_dir=None,
) -> pd.DataFrame:
    """Every year one vintage carries, as the next vintage restates it.

    Includes the estimates base, which is revised too. The point of this table
    is not any single row: it is that **no row is stable**, so "rebase onto the
    consistent vintage" names a target that moves annually.
    """
    older = census.get_vintage(from_vintage)
    rows = []

    base = census.ESTIMATES_BASE_COLUMN
    rows.append({
        "label": "base 2020",
        "from": census.national_total_for(from_vintage, base, census_dir),
        "to": census.national_total_for(to_vintage, base, census_dir),
    })
    for year in older.years:
        rows.append({
            "label": str(year),
            "from": census.national_total(from_vintage, year, census_dir),
            "to": census.national_total(to_vintage, year, census_dir),
        })

    frame = pd.DataFrame(rows)
    frame["change"] = frame["to"] - frame["from"]
    frame["pct_change"] = 100.0 * frame["change"] / frame["from"]
    return frame


def render_series_restatement_table(
    from_vintage: int = RESTATING_VINTAGE,
    to_vintage: int = LATEST_VINTAGE,
    census_dir=None,
) -> list[str]:
    frame = series_restatement(from_vintage, to_vintage, census_dir)
    lines = [
        _row(["reference year", f"V{from_vintage}", f"V{to_vintage}", "change"]),
        _rule(4),
    ]
    for _, r in frame.iterrows():
        lines.append(_row([
            str(r["label"]),
            f"{int(r['from']):,}",
            f"{int(r['to']):,}",
            signed(int(r["change"])),
        ]))
    return lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def render_all(export_dir=None, census_dir=None) -> str:
    u = restatement_uniformity(export_dir, census_dir)
    t = kitagawa_treatments(export_dir, census_dir)

    lines = [
        f"# Vintage sensitivity, V{WONDER_VINTAGE} -> V{RESTATING_VINTAGE}",
        "",
        "Regenerates the tables in docs/denominator-methods.md section 2.",
        "",
        f"## 1. Restatement of {RESTATED_YEAR}, band level",
        "",
    ]
    lines += render_restatement_table(export_dir, census_dir)
    lines += [
        "",
        f"Total {signed(u.total_pct_change, 3)}%, spread {u.spread_pp:.3f} points, "
        f"{u.spread_ratio:.2f}x the total "
        f"(threshold {fetch.VINTAGE_UNIFORMITY_SPREAD_MULTIPLE}).",
        f"**{'UNIFORM' if u.uniform else 'NON-UNIFORM'}**",
        "",
        f"## 2. Kitagawa {RESTATED_YEAR}->{COMPARISON_YEAR}, both treatments",
        "",
    ]
    lines += render_kitagawa_table(export_dir, census_dir)
    lines += [
        "",
        f"Restatement moves the total by {signed(t.total_shift, 2)} points, "
        f"{t.restatement_share_of_decline:.1f}% of the published decline.",
        f"Of that, {t.rate_share_of_restatement:.1f}% goes to the rate effect "
        f"({signed(t.rate_shift, 2)}) and {t.age_share_of_restatement:.1f}% to "
        f"the age effect ({signed(t.age_shift, 2)}).",
        f"Age/rate ratio {t.published.ratio:.3f} -> {t.restated.ratio:.3f} "
        f"({signed(100 * (t.restated.ratio - t.published.ratio) / t.published.ratio, 1)}%).",
        "",
        f"## 3. V{RESTATING_VINTAGE} -> V{LATEST_VINTAGE}: no terminal vintage",
        "",
    ]
    lines += render_series_restatement_table(census_dir=census_dir)
    lines += [
        "",
        "Every row moves. A consistent-vintage rebasing has no fixed target.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    print(render_all())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
