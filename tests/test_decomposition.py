"""Kitagawa decomposition.

Tolerance policy, applied throughout this suite: a quantity **defined** to be
equal is asserted equal, at 1e-9 for floating-point representation only; a
quantity merely **expected to be close** gets a real tolerance. Do not loosen a
1e-9 here to make a failure go away -- at this size it is reporting a genuine
arithmetic defect, not fixture noise.

The 0.5 tolerances that used to sit on the pure-aging test were measured and
found to be masking residuals of exactly 0.0 and 2.8e-14. They protected
against nothing (the fixture's deaths are already integral, so its
`int(round(...))` never rounds) while hiding regressions up to half a death per
100,000.
"""
from src import decomposition


def test_stationary_population_has_zero_effects(by_age_stationary):
    r = decomposition.kitagawa(by_age_stationary, 2000, 2001)
    assert abs(r.rate_effect) < 1e-9
    assert abs(r.age_effect) < 1e-9
    assert abs(r.total_change) < 1e-9


def test_pure_aging_attributes_all_change_to_age_effect(by_age_aging_only):
    r = decomposition.kitagawa(by_age_aging_only, 2000, 2001)
    # Defined to be exactly zero: the fixture holds age-specific rates fixed.
    assert abs(r.rate_effect) < 1e-9, "rates were held fixed; rate effect must vanish"
    assert r.age_effect > 0, "population shifted older; age effect must be positive"
    # With the rate effect zero, the age effect is the entire change, exactly.
    assert abs(r.age_effect - r.total_change) < 1e-9


def test_additivity_is_exact(by_age_aging_only):
    """Kitagawa is an exact decomposition, not an approximation."""
    r = decomposition.kitagawa(by_age_aging_only, 2000, 2001)
    assert abs((r.rate_effect + r.age_effect) - r.total_change) < 1e-9


def test_reversing_years_flips_signs(by_age_aging_only):
    fwd = decomposition.kitagawa(by_age_aging_only, 2000, 2001)
    rev = decomposition.kitagawa(by_age_aging_only, 2001, 2000)
    assert abs(fwd.rate_effect + rev.rate_effect) < 1e-9
    assert abs(fwd.age_effect + rev.age_effect) < 1e-9


def test_missing_year_raises(by_age_stationary):
    import pytest
    with pytest.raises(ValueError, match="not present"):
        decomposition.kitagawa(by_age_stationary, 2000, 1999)
