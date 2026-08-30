"""The three treatments of the 2010 measurement basis.

These pin the robustness range the manuscript's central claim rests on. Before
this module existed the range was half computed and half typed: treatment A
matched results.json, while B and C' appeared nowhere in src/ or tests/ and were
simply asserted in docs/denominator-methods.md.

Reads the committed WONDER exports and Census files rather than synthetic
fixtures, the same deviation from this suite's usual rule as the 2010 vintage
fixture in test_fetch.py and for the same reason: what is being pinned is that
these specific published figures produce these specific claims.
"""
import re
from pathlib import Path

import pytest

from src import census, loader, treatments

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "denominator-methods.md"

# The values that stood in the doc as assertions before anything computed them.
# Kept as a regression fixture: if a refactor moves the numbers, this is what
# says so. They are NOT the source of truth -- src/treatments.py is.
ASSERTED = {
    "A": {"slope": -1.779, "excess": 1_117_059, "ratio": 3.405},
    "B": {"slope": -1.415, "excess": 1_105_148, "ratio": 3.599},
    "C'": {"slope": -1.585, "excess": 1_110_739, "ratio": 3.872},
}


@pytest.fixture(scope="module")
def computed():
    ds = loader.load_all(strict=False)
    return treatments.compute_treatments(
        ds.by_age, ds.annual_deaths, ds.population, ds.standard_pop
    )


def test_wonder_2010_is_the_april_1_decennial_count():
    """The premise of treatment C', checked band by band.

    If WONDER's 2010 were not the decennial count, swapping in the July 1
    estimate would be an unexplained substitution rather than a correction of
    measurement basis, and the range would mean nothing.
    """
    ds = loader.load_all(strict=False)
    frame = treatments.assert_wonder_2010_is_the_decennial_count(ds.by_age)
    assert (frame["april_1"] == frame["wonder"]).all()
    assert int(frame["wonder"].sum()) == 308_745_538


def test_the_two_2010_columns_differ_as_documented():
    """April 1 to July 1 is +0.188% nationally, and non-uniform by band."""
    april = treatments.april_1_2010_by_band()
    july = treatments.july_1_2010_by_band()

    total_pct = 100 * (july.sum() / april.sum() - 1)
    assert total_pct == pytest.approx(0.188, abs=0.001)

    # The spread that made the 2010 case worth a section: 85+ moves nearly
    # thirty times as much as 0-24.
    by_band = {g: 100 * (july[g] / april[g] - 1) for g in april.index}
    assert by_band["0-24"] == pytest.approx(0.032, abs=0.001)
    assert by_band["85+"] == pytest.approx(0.912, abs=0.001)
    assert by_band["85+"] / by_band["0-24"] > 25


def test_all_three_treatments_reproduce_the_previously_asserted_values(computed):
    """The headline check. These numbers were quoted for two days uncomputed."""
    by_key = {t.key: t for t in computed}
    assert set(by_key) == set(ASSERTED)

    for key, expected in ASSERTED.items():
        t = by_key[key]
        assert t.baseline_slope == pytest.approx(expected["slope"], abs=5e-4), key
        assert t.excess_2020_2021 == pytest.approx(expected["excess"], abs=1), key
        assert t.age_to_rate_ratio == pytest.approx(expected["ratio"], abs=5e-4), key


def test_treatment_intervals_are_what_the_labels_say(computed):
    by_key = {t.key: t for t in computed}
    assert by_key["A"].interval == (2010, 2019)
    assert by_key["B"].interval == (2011, 2019), "B excludes 2010"
    assert by_key["C'"].interval == (2010, 2019), "C' keeps 2010, changes its basis"


def test_the_reported_range_is_a_and_c_prime(computed):
    """A is the lowest and C' the highest, so the primary series is the least
    favourable to the paper's own argument. That asymmetry is claimed in 5.1."""
    lo, hi = treatments.ratio_range(computed)
    by_key = {t.key: t for t in computed}
    assert lo == pytest.approx(by_key["A"].age_to_rate_ratio)
    assert hi == pytest.approx(by_key["C'"].age_to_rate_ratio)
    assert (round(lo, 2), round(hi, 2)) == (3.41, 3.87)


def test_every_treatment_keeps_the_age_effect_dominant(computed):
    """The claim being tested for robustness: age effect exceeds rate effect."""
    for t in computed:
        assert t.age_effect > 0 > t.rate_effect, t.key
        assert t.age_to_rate_ratio > 1.0, t.key


def test_c_prime_moves_the_age_effect_not_only_the_rate_effect(computed):
    """A uniform revision would leave the age effect alone. This one does not."""
    by_key = {t.key: t for t in computed}
    assert by_key["C'"].age_effect != pytest.approx(
        by_key["A"].age_effect, abs=0.5
    ), "the July 1 revision is non-uniform, so it must move the age effect"
    assert by_key["A"].age_effect == pytest.approx(99.4, abs=0.1)
    assert by_key["C'"].age_effect == pytest.approx(96.7, abs=0.1)


def test_a_wrong_2010_basis_is_rejected(monkeypatch):
    """The premise check must fire, not just exist."""
    ds = loader.load_all(strict=False)
    tampered = ds.by_age.copy()
    mask = (tampered["year"] == 2010) & (tampered["age_group"] == "85+")
    tampered.loc[mask, "population"] = 1

    with pytest.raises(treatments.TreatmentError) as excinfo:
        treatments.assert_wonder_2010_is_the_decennial_count(tampered)
    assert "not the April 1 decennial count" in str(excinfo.value)
    assert "85+" in str(excinfo.value)


def test_the_doc_table_matches_the_computed_treatments(computed):
    """docs/denominator-methods.md must carry what src/treatments.py computes."""
    doc = re.sub(r"[ \t]+", " ", DOC.read_text(encoding="utf-8").replace("**", ""))
    rows = [
        re.sub(r"[ \t]+", " ", line)
        for line in treatments.render_table(computed)
        if line.startswith("|") and not line.startswith("|---")
    ]
    assert len(rows) == 4, "header plus three treatments"
    missing = [r for r in rows if r not in doc]
    assert not missing, (
        "docs/denominator-methods.md has drifted from src/treatments.py:\n  "
        + "\n  ".join(missing)
        + "\nRegenerate with `python -m src.treatments`."
    )


def test_the_census_vintage_carrying_2010_is_registered():
    spec = census.get_vintage(treatments.CENSUS_VINTAGE_2010)
    assert spec.filename == "nc-est2020-agesex-res.csv"
    assert 2010 in spec.years
    assert spec.path.exists(), "committed analysis input"
