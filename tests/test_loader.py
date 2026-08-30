"""The loader's job is to refuse bad data. These tests prove it does."""
import pandas as pd
import pytest

from src import loader


# NOTE: test_repo_ships_with_unpopulated_data was removed when the CSVs were
# populated from the committed WONDER exports. It asserted that
# load_annual_deaths raised IncompleteDataError because the shipped data was
# empty, and the README said to delete it at exactly this point. It had done
# its job: it guarded the window between the repository being published and the
# data being sourced, which is when invented numbers would have been easiest to
# introduce unnoticed.
#
# The guarantee that replaces it is test_populated_data_is_still_unverified
# below. Data being present is no longer the question; data being *signed off*
# is. Promotion writes provenance and deliberately does not write attestation,
# so strict loading must still refuse.


def test_populated_data_is_still_unverified():
    """Promotion fills fetched_from. It must not fill verified_by.

    This is the live form of the repository's central claim: knowing where a
    number came from is not the same as knowing it is the right number. The
    values are in place and machine-provenanced, and strict mode still refuses
    them until a human signs each row off.
    """
    with pytest.raises(loader.UnverifiedDataError):
        loader.load_annual_deaths(strict=True)
    with pytest.raises(loader.UnverifiedDataError):
        loader.load_population(strict=True)
    with pytest.raises(loader.UnverifiedDataError):
        loader.load_deaths_by_age(strict=True)


def test_non_strict_loading_now_succeeds():
    """The counterpart: the data really is populated, so non-strict works."""
    annual = loader.load_annual_deaths(strict=False)
    population = loader.load_population(strict=False)

    assert len(annual) == 15
    assert list(annual["year"]) == list(range(2010, 2025))
    assert annual["deaths"].notna().all()
    assert len(population) == 15
    assert population["population"].notna().all()


def test_standard_population_sums_to_one_million():
    s = loader.load_standard_population()
    assert int(s.sum()) == 1_000_000
    assert list(s.index) == loader.AGE_GROUPS


def test_incomplete_data_error_names_the_file():
    """A missing value must raise, and the message must say which file.

    Exercises the check directly rather than relying on the repository's own
    CSVs being empty, which they no longer are. The previous version of this
    test called load_population() and depended on that emptiness, so it broke
    on promotion for a reason unrelated to what it was testing.
    """
    frame = pd.DataFrame({
        "year": [2010, 2011],
        "population": [309_327_143, None],
    })

    with pytest.raises(loader.IncompleteDataError) as excinfo:
        loader._require_complete(frame, ["population"], "us_population.csv")

    message = str(excinfo.value)
    assert "us_population.csv" in message
    assert "1 row(s) have missing values" in message
    assert "2011" in message, "the message should show the offending row"


def test_complete_data_passes_the_check():
    """The check must not fire on the case it exists to permit."""
    frame = pd.DataFrame({
        "year": [2010, 2011],
        "population": [309_327_143, 311_583_481],
    })
    loader._require_complete(frame, ["population"], "us_population.csv")


def test_unverified_error_names_the_file_and_counts_rows():
    frame = pd.DataFrame({
        "year": [2010, 2011, 2012],
        "deaths": [1, 2, 3],
        "verified_by": ["TF", "", None],
    })

    with pytest.raises(loader.UnverifiedDataError) as excinfo:
        loader._require_verified(frame, "us_annual_deaths.csv")

    message = str(excinfo.value)
    assert "us_annual_deaths.csv" in message
    assert "2 row(s)" in message, "blank and NaN both count as unattested"
