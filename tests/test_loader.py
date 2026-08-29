"""The loader's job is to refuse bad data. These tests prove it does."""
import pytest

from src import loader


def test_repo_ships_with_unpopulated_data():
    """Guard against someone committing invented numbers.

    The shipped CSVs are intentionally empty. If this test starts
    failing, either the data was legitimately populated (in which case
    delete this test) or placeholder values leaked into the repo.
    """
    with pytest.raises(loader.IncompleteDataError):
        loader.load_annual_deaths(strict=False)


def test_standard_population_sums_to_one_million():
    s = loader.load_standard_population()
    assert int(s.sum()) == 1_000_000
    assert list(s.index) == loader.AGE_GROUPS


def test_incomplete_data_error_names_the_file():
    try:
        loader.load_population(strict=False)
    except loader.IncompleteDataError as e:
        assert "us_population.csv" in str(e)
    else:
        pytest.fail("expected IncompleteDataError")
