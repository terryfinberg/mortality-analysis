"""Tests that inspect what the figures actually DRAW, not what they were given.

Why this file exists
--------------------
``fig_decomposition`` once stacked the age effect on the rate effect with
``bottom=rate``. That is correct only while both components share a sign. Over
2010-2019 the rate effect is negative and the age effect positive, so the second
bar was drawn from the negative base straight back over the first and hid it
completely -- the chart showed the whole crude-rate change as population aging,
which is the opposite of the finding.

**Every input-side check passed.** The identities held, the crude rate matched
WONDER for all fifteen years, results.json was correct to the decimal. The
defect existed only in rendered geometry, and nothing in the suite looked there.
So these tests read patch extents off the Axes and compare them to the values
they are supposed to encode.

The fixtures are deliberately unreal numbers, per the rest of the suite. The
sign combinations are what matter, not the magnitudes.
"""
from pathlib import Path

import pandas as pd
import pytest
from matplotlib.colors import to_rgba

from src import figures
from src.decomposition import KitagawaResult


@pytest.fixture
def drawn(monkeypatch):
    """Capture the Axes instead of saving and closing the figure.

    Patches ``_save`` so the production drawing code runs untouched and the
    figure survives for inspection.
    """
    box = {}

    def capture(fig, name):
        box["fig"] = fig
        box["name"] = name
        box["ax"] = fig.axes[0]
        return Path(f"{name}.png")

    monkeypatch.setattr(figures, "_save", capture)
    return box


def bars(ax):
    """The drawn rectangles, in creation order."""
    return list(ax.patches)


def extent(patch):
    """(low, high) vertical extent of a bar, sign-normalised."""
    y0 = patch.get_y()
    y1 = y0 + patch.get_height()
    return (min(y0, y1), max(y0, y1))


def overlap(a, b):
    """Length of the shared span. Zero when they merely touch."""
    return min(a[1], b[1]) - max(a[0], b[0])


def _result(start, end, rate, age):
    return KitagawaResult(
        year_start=start, year_end=end,
        crude_start=100.0, crude_end=100.0 + rate + age,
        total_change=rate + age, rate_effect=rate, age_effect=age,
    )


# Every sign combination. The first is the case that was silently wrong.
MIXED = _result(2001, 2002, rate=-7.0, age=25.0)    # opposite signs
BOTH_POS = _result(2002, 2003, rate=4.0, age=6.0)   # same sign, positive
BOTH_NEG = _result(2003, 2004, rate=-5.0, age=-3.0)  # same sign, negative
DECOMP = [MIXED, BOTH_POS, BOTH_NEG]


# ---------------------------------------------------------------------------
# fig5: the decomposition
# ---------------------------------------------------------------------------


def test_decomposition_bar_heights_equal_the_effects_they_encode(drawn):
    figures.fig_decomposition(DECOMP)
    patches = bars(drawn["ax"])
    assert len(patches) == 6, "three intervals x two effects"

    rate_bars, age_bars = patches[:3], patches[3:]
    for bar, result in zip(rate_bars, DECOMP):
        assert bar.get_height() == pytest.approx(result.rate_effect, abs=1e-9)
    for bar, result in zip(age_bars, DECOMP):
        assert bar.get_height() == pytest.approx(result.age_effect, abs=1e-9)


def test_opposite_signed_effects_are_both_visible(drawn):
    """The regression. Neither bar may be drawn over the other.

    With the old `bottom=rate` stack the age bar spanned (-7, 18) while the
    rate bar spanned (-7, 0), so the rate bar was entirely inside it and
    invisible. Here they must share at most an endpoint.
    """
    figures.fig_decomposition([MIXED])
    patches = bars(drawn["ax"])
    assert len(patches) == 2

    rate_extent, age_extent = extent(patches[0]), extent(patches[1])
    assert overlap(rate_extent, age_extent) <= 1e-9, (
        f"bars overlap: rate {rate_extent}, age {age_extent}. One is drawn "
        f"over the other and the reader cannot see it."
    )
    # And each is on its own side of zero, which is what makes them legible.
    assert rate_extent == pytest.approx((-7.0, 0.0))
    assert age_extent == pytest.approx((0.0, 25.0))


def test_no_two_bars_at_the_same_x_ever_overlap(drawn):
    """Holds for every sign combination, not just the mixed one."""
    figures.fig_decomposition(DECOMP)
    patches = bars(drawn["ax"])
    rate_bars, age_bars = patches[:3], patches[3:]

    for i, (r, a) in enumerate(zip(rate_bars, age_bars)):
        assert r.get_x() == pytest.approx(a.get_x()), "same interval, same x"
        assert overlap(extent(r), extent(a)) <= 1e-9, (
            f"interval {DECOMP[i].year_start}-{DECOMP[i].year_end}: "
            f"rate {extent(r)} overlaps age {extent(a)}"
        )


def test_same_signed_effects_stack_end_to_end(drawn):
    """Where signs agree, stacking is correct and must be preserved."""
    figures.fig_decomposition([BOTH_POS])
    rate_bar, age_bar = bars(drawn["ax"])
    assert extent(rate_bar) == pytest.approx((0.0, 4.0))
    assert extent(age_bar) == pytest.approx((4.0, 10.0))
    # Touching, not overlapping.
    assert overlap(extent(rate_bar), extent(age_bar)) == pytest.approx(0.0)

    figures.fig_decomposition([BOTH_NEG])
    rate_bar, age_bar = bars(drawn["ax"])
    assert extent(rate_bar) == pytest.approx((-5.0, 0.0))
    assert extent(age_bar) == pytest.approx((-8.0, -5.0))


def test_drawn_extents_span_the_net_change(drawn):
    """The two bars together must reach exactly the total, on every case."""
    figures.fig_decomposition(DECOMP)
    patches = bars(drawn["ax"])
    for r, a, result in zip(patches[:3], patches[3:], DECOMP):
        assert r.get_height() + a.get_height() == pytest.approx(
            result.total_change, abs=1e-9
        )


def test_net_change_marker_sits_at_the_total(drawn):
    """The diamond is the reader's check that the parts sum. It must be right."""
    figures.fig_decomposition(DECOMP)
    ax = drawn["ax"]
    scatters = [c for c in ax.collections if len(c.get_offsets())]
    assert scatters, "the net-change marker is missing"
    ys = [float(y) for _, y in scatters[0].get_offsets()]
    assert ys == pytest.approx([r.total_change for r in DECOMP])


def test_the_overlap_check_would_have_caught_the_old_bug():
    """Prove the assertion has teeth by reproducing the defect directly.

    Draws the mixed-sign case the old way -- age stacked on rate with
    `bottom=rate` -- and confirms the same helper reports a real overlap.
    Without this, a bug in the checker would look like a passing suite.
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    rate, age = MIXED.rate_effect, MIXED.age_effect
    ax.bar([0], [rate])
    ax.bar([0], [age], bottom=[rate])          # the old, wrong idiom
    rate_bar, age_bar = bars(ax)
    plt.close(fig)

    assert extent(rate_bar) == pytest.approx((-7.0, 0.0))
    assert extent(age_bar) == pytest.approx((-7.0, 18.0))
    assert overlap(extent(rate_bar), extent(age_bar)) == pytest.approx(7.0), (
        "the old rendering hid the whole rate bar; the checker must see that"
    )


# ---------------------------------------------------------------------------
# fig3: excess mortality -- height encodes the count, colour encodes the sign
# ---------------------------------------------------------------------------

EXCESS = pd.DataFrame([
    {"year": 2001, "excess_deaths": 500},
    {"year": 2002, "excess_deaths": -200},
    {"year": 2003, "excess_deaths": 900},
])


def test_excess_bar_heights_equal_the_counts(drawn):
    figures.fig_excess(EXCESS)
    patches = bars(drawn["ax"])
    assert len(patches) == len(EXCESS)
    for bar, value in zip(patches, EXCESS["excess_deaths"]):
        assert bar.get_height() == pytest.approx(value)
        # Bars grow from the zero line, so the axis reads as a real baseline.
        assert bar.get_y() == pytest.approx(0.0)


def test_excess_bar_colour_matches_the_sign(drawn):
    """A deficit drawn in the surplus colour would invert the reading."""
    figures.fig_excess(EXCESS)
    surplus, deficit = to_rgba("#c0392b"), to_rgba("#2980b9")
    for bar, value in zip(bars(drawn["ax"]), EXCESS["excess_deaths"]):
        expected = surplus if value > 0 else deficit
        assert bar.get_facecolor() == pytest.approx(expected)


# ---------------------------------------------------------------------------
# fig4: COVID share -- width encodes the percentage
# ---------------------------------------------------------------------------

SHARES = pd.DataFrame([
    {"age_group": "0-24", "share_pct": 1.5},
    {"age_group": "25-44", "share_pct": 8.0},
    {"age_group": "85+", "share_pct": 40.5},
])


def test_covid_bar_widths_equal_the_shares(drawn):
    figures.fig_covid_by_age(SHARES)
    patches = bars(drawn["ax"])
    assert len(patches) == len(SHARES)
    for bar, value in zip(patches, SHARES["share_pct"]):
        assert bar.get_width() == pytest.approx(value)
        assert bar.get_x() == pytest.approx(0.0), "bars must start at zero"


# ---------------------------------------------------------------------------
# fig1 and fig2: position carries the value, so check the plotted series
# ---------------------------------------------------------------------------


def test_crude_and_adjusted_lines_carry_their_own_series(drawn):
    """Guards against the two series being swapped or one column reused."""
    crude = pd.DataFrame({"year": [2001, 2002], "crude_rate": [10.0, 12.0],
                          "deaths": [1, 2], "population": [3, 4]})
    adjusted = pd.DataFrame({"year": [2001, 2002],
                             "age_adjusted_rate": [20.0, 19.0]})

    figures.fig_crude_vs_adjusted(crude, adjusted)
    lines = drawn["ax"].get_lines()
    assert len(lines) == 2
    assert list(lines[0].get_ydata()) == [10.0, 12.0]
    assert list(lines[1].get_ydata()) == [20.0, 19.0]
    assert list(lines[0].get_xdata()) == [2001, 2002]


def test_every_age_group_is_drawn_as_its_own_line(drawn):
    """A dropped group would leave the chart looking complete."""
    rates = pd.DataFrame([
        {"year": y, "age_group": g, "rate": r}
        for g, r in (("0-24", 5.0), ("85+", 500.0))
        for y, r in ((2001, r), (2002, r * 2))
    ])

    figures.fig_age_specific_rates(rates)
    lines = drawn["ax"].get_lines()
    assert len(lines) == rates["age_group"].nunique()
    drawn_values = sorted(tuple(line.get_ydata()) for line in lines)
    expected = sorted(
        tuple(sub.sort_values("year")["rate"])
        for _, sub in rates.groupby("age_group")
    )
    assert drawn_values == expected


def test_age_specific_legend_is_outside_the_plot_area(drawn):
    """It used to sit on top of the 85+ and 75-84 lines' final points."""
    rates = pd.DataFrame([
        {"year": 2001, "age_group": "0-24", "rate": 5.0},
        {"year": 2002, "age_group": "0-24", "rate": 6.0},
    ])
    figures.fig_age_specific_rates(rates)
    legend = drawn["ax"].get_legend()
    assert legend is not None
    # Anchored past the right edge of the axes in axes coordinates.
    x0 = legend.get_bbox_to_anchor().transformed(
        drawn["ax"].transAxes.inverted()
    ).x0
    assert x0 >= 1.0, "legend still overlaps the data area"
