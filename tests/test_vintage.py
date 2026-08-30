"""Tests for the Census vintage layer and the vintage-sensitivity analysis.

No test here touches the network. They do read the **committed** Census files
under ``data/raw/census/`` and the committed WONDER exports, which deliberately
breaks this suite's usual rule that fixtures are obviously-unreal numbers -- the
same deviation, for the same reason, as the 2010 regression fixture in
``test_fetch.py``. A synthetic stand-in would prove the arithmetic but not that
these specific published figures produce the specific claims made in
``docs/denominator-methods.md``. Pinning the claims is the entire point.

**These values are inputs to a finding and a regression fixture. They are not
analysis inputs to the paper**, which draws its denominators from WONDER.
"""
import re
from pathlib import Path

import pytest

from src import census, vintage

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "denominator-methods.md"


# ---------------------------------------------------------------------------
# The Census file format, enforced rather than described
# ---------------------------------------------------------------------------


def test_age_100_is_top_coded_and_included_in_the_top_band():
    """AGE 100 means 100-and-over. Reading it as exactly 100 drops people."""
    name, lo, hi = census.BAND_EDGES[-1]
    assert name == "85+"
    assert hi == census.MAX_SINGLE_AGE == 100

    detail = census.load_vintage(2024)
    at_100 = detail[detail["AGE"] == 100]["POPESTIMATE2024"].sum()
    assert at_100 > 0, "no one at AGE 100, so this test proves nothing"

    bands = census.collapse_to_bands(2024, 2024)
    without_top_code = detail[
        (detail["AGE"] >= 85) & (detail["AGE"] <= 99)
    ]["POPESTIMATE2024"].sum()
    assert bands["85+"] - without_top_code == at_100


def test_single_year_ages_sum_to_the_published_total():
    """The AGE==999 identity, which is exact and therefore asserted exactly."""
    for vintage_year in (2024, 2025):
        for year in census.get_vintage(vintage_year).years:
            bands = census.collapse_to_bands(vintage_year, year)
            assert int(bands.sum()) == census.national_total(vintage_year, year)


def test_a_broken_band_mapping_is_caught_not_absorbed(monkeypatch):
    """Drop the top code from BAND_EDGES and the total identity must fail.

    This is what makes the mapping checkable at all: six plausible numbers that
    quietly omit the centenarians look exactly like six correct ones.
    """
    broken = tuple(
        (name, lo, 99 if name == "85+" else hi)
        for name, lo, hi in census.BAND_EDGES
    )
    monkeypatch.setattr(census, "BAND_EDGES", broken)

    with pytest.raises(census.CensusError) as excinfo:
        census.collapse_to_bands(2024, 2024)
    assert "does not cover every age exactly once" in str(excinfo.value)


def test_a_vintage_cannot_be_asked_for_a_year_it_predates():
    with pytest.raises(census.CensusError) as excinfo:
        census.get_vintage(2024).column(2025)
    assert "does not carry 2025" in str(excinfo.value)


def test_unregistered_vintage_points_at_the_directory_to_list():
    """The discovery rule, enforced: the error hands over a URL to list."""
    with pytest.raises(census.CensusError) as excinfo:
        census.get_vintage(2099)
    message = str(excinfo.value)
    assert "national/asrh" in message
    assert "Do not guess the path." in message


# ---------------------------------------------------------------------------
# Cross-source validation of the band collapse
# ---------------------------------------------------------------------------


def test_wonder_2024_equals_census_v2024_band_for_band():
    """WONDER says it carries 2024 from Vintage 2024, so this must be exact.

    Independent confirmation that single-year Census ages fold onto the six
    analysis bands correctly. Without it, a wrong BAND_EDGES would produce six
    believable numbers and every downstream figure would be wrong.
    """
    frame = vintage.assert_wonder_matches_census()
    assert (frame["difference"] == 0).all()
    assert int(frame["wonder"].sum()) == 340_110_988


# ---------------------------------------------------------------------------
# Finding 1: the restatement is non-uniform, and the 70/30 split
# ---------------------------------------------------------------------------


def test_restatement_of_2023_is_non_uniform():
    u = vintage.restatement_uniformity()

    assert u.uniform is False
    assert u.total_pct_change == pytest.approx(0.565, abs=0.001)
    assert u.spread_ratio == pytest.approx(1.83, abs=0.01)
    assert u.spread_ratio > vintage.fetch.VINTAGE_UNIFORMITY_SPREAD_MULTIPLE

    # 75-84 falls while the national total rises. The sign change is why the
    # fold ratio is undefined rather than merely large.
    band = u.frame.set_index("age_group").loc["75-84"]
    assert band["abs_change"] == -12_699
    assert u.min_pct < 0 < u.max_pct
    assert u.fold != u.fold, "fold should be nan across a sign change"


def test_restatement_splits_seventy_thirty_between_rate_and_age():
    """The headline claim in docs/denominator-methods.md, finding 1."""
    t = vintage.kitagawa_treatments()

    assert t.restatement_share_of_decline == pytest.approx(26.6, abs=0.1)
    assert t.rate_share_of_restatement == pytest.approx(70.1, abs=0.1)
    assert t.age_share_of_restatement == pytest.approx(29.9, abs=0.1)

    assert t.total_shift == pytest.approx(5.18, abs=0.01)
    assert t.rate_shift == pytest.approx(3.63, abs=0.01)
    assert t.age_shift == pytest.approx(1.55, abs=0.01)

    # The two shares are shares of one quantity and must exhaust it.
    assert t.rate_shift + t.age_shift == pytest.approx(t.total_shift, abs=1e-9)


def test_deaths_are_identical_across_both_treatments():
    """Only the denominator moves. If deaths differ, the pair means nothing."""
    t = vintage.kitagawa_treatments()
    # Same certificates, same end year, same end-year denominator.
    assert t.published.crude_end == pytest.approx(t.restated.crude_end, abs=1e-9)
    assert t.published.crude_start > t.restated.crude_start


def test_kitagawa_additivity_holds_under_both_treatments():
    """Kitagawa is exact, so this is an equality, not a tolerance."""
    t = vintage.kitagawa_treatments()
    for k in (t.published, t.restated):
        assert k.rate_effect + k.age_effect == pytest.approx(
            k.total_change, abs=1e-9
        )


# ---------------------------------------------------------------------------
# Finding 2: the ratio is basis-dependent
# ---------------------------------------------------------------------------


def test_age_to_rate_ratio_shifts_on_a_denominator_choice():
    """0.406 -> 0.510 on nothing but the 2023 population basis."""
    t = vintage.kitagawa_treatments()

    assert round(t.published.ratio, 3) == 0.406
    assert round(t.restated.ratio, 3) == 0.510

    shift = 100 * (t.restated.ratio - t.published.ratio) / t.published.ratio
    assert shift == pytest.approx(25.5, abs=0.1)

    # The point of the finding: it moves the FIRST decimal digit, so quoting
    # three digits without naming a vintage overstates the precision.
    assert round(t.published.ratio, 1) != round(t.restated.ratio, 1)


# ---------------------------------------------------------------------------
# Finding 3: no terminal vintage
# ---------------------------------------------------------------------------


def test_v2025_restates_2024_and_restates_2023_a_second_time():
    """The load-bearing claim: there is no vintage to converge on."""
    assert census.national_total(2024, 2024) == 340_110_988
    assert census.national_total(2025, 2024) == 340_003_797

    # 2023 was already restated once by V2024 (+1,891,336 over WONDER's
    # V2023 figure of 334,914,895), and V2025 moves it again.
    assert census.national_total(2024, 2023) == 336_806_231
    assert census.national_total(2025, 2023) == 336_755_052
    assert census.national_total(2025, 2023) != census.national_total(2024, 2023)


def test_every_year_moves_between_v2024_and_v2025():
    """Not one row is stable, including the estimates base."""
    frame = vintage.series_restatement(2024, 2025)

    assert (frame["change"] != 0).all(), "a stable row would weaken the finding"
    assert "base 2020" in set(frame["label"])

    # Revisions grow with recency: the years a paper most wants are least settled.
    by_label = frame.set_index("label")["change"].abs()
    assert by_label["2024"] > by_label["2023"] > by_label["2022"]
    assert by_label["2024"] == 107_191


# ---------------------------------------------------------------------------
# The doc must not drift from the code
# ---------------------------------------------------------------------------


def _normalise(text: str) -> str:
    """Strip markdown emphasis and collapse whitespace runs for comparison."""
    return re.sub(r"[ \t]+", " ", text.replace("**", ""))


def test_doc_tables_match_the_computed_values():
    """docs/denominator-methods.md must carry what src/vintage.py computes.

    The reason this test exists: the doc makes numeric claims about the most
    recent year in the paper. A claim nobody can regenerate is precisely the
    failure this repository was rebuilt to remove, and a doc that drifts from
    its code is that failure with extra steps. Change a band mapping and either
    these numbers move or this fails.
    """
    doc = _normalise(DOC.read_text(encoding="utf-8"))

    rendered = (
        vintage.render_restatement_table()
        + vintage.render_kitagawa_table()
        + vintage.render_series_restatement_table()
    )
    data_rows = [
        _normalise(line) for line in rendered
        if line.startswith("|") and not line.startswith("|---")
    ]

    # Guard against passing vacuously: an empty render would satisfy the
    # containment check below while proving nothing. Three tables, each a
    # header plus its rows: (1+6) restatement, (1+2) Kitagawa, (1+6) series.
    assert len(data_rows) == 7 + 3 + 7, f"expected 17 rows, got {len(data_rows)}"

    missing = [row for row in data_rows if row not in doc]
    assert not missing, (
        "docs/denominator-methods.md has drifted from src/vintage.py. "
        "Rows computed but not found in the doc:\n  "
        + "\n  ".join(missing)
        + "\nRegenerate with `python -m src.vintage` and update the doc."
    )


def test_doc_states_the_headline_percentages():
    """The prose claims, not just the tables."""
    t = vintage.kitagawa_treatments()
    doc = _normalise(DOC.read_text(encoding="utf-8"))

    assert f"{t.restatement_share_of_decline:.1f}%" in doc
    assert f"{t.rate_share_of_restatement:.1f}%" in doc
    assert f"{t.age_share_of_restatement:.1f}%" in doc
