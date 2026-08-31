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


def test_promotion_cannot_write_an_attestation(tmp_path):
    """The durable invariant: a machine fills provenance, never attestation.

    This replaces test_populated_data_is_still_unverified, which asserted that
    strict loading raised because nothing had been signed yet. That was true
    until the rows were signed, and then it was just a statement about the
    calendar. The guarantee worth keeping is the one that does not expire:
    ``promote()`` is constructionally unable to vouch for a value, whatever the
    current state of the repository's own CSVs.
    """
    from src import fetch

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "us_population.csv").write_text(
        "year,population,source_citation,source_type,fetched_from,"
        "verified_by,verified_date\n2010,,cited,,,,\n",
        encoding="utf-8",
    )
    values = pd.DataFrame([{"year": 2010, "population": 308_745_538}])

    fetch.promote("population", values, provenance="wonder-export:x@sha256:abc",
                  citation="a citation", dry_run=False, raw_dir=raw)

    written = pd.read_csv(raw / "us_population.csv")
    assert int(written.loc[0, "population"]) == 308_745_538
    assert written.loc[0, "fetched_from"] == "wonder-export:x@sha256:abc"
    assert written.loc[0, "source_type"] == "api"
    assert pd.isna(written.loc[0, "verified_by"]) or not str(
        written.loc[0, "verified_by"]
    ).strip()
    assert pd.isna(written.loc[0, "verified_date"]) or not str(
        written.loc[0, "verified_date"]
    ).strip()


def test_the_committed_data_is_signed_and_loads_strictly():
    """Current state: a person attested these rows, so strict mode works."""
    annual = loader.load_annual_deaths(strict=True)
    population = loader.load_population(strict=True)
    by_age = loader.load_deaths_by_age(strict=True)

    assert len(annual) == 15
    assert list(annual["year"]) == list(range(2010, 2025))
    assert len(population) == 15
    assert len(by_age) == 90

    signed = pd.read_csv(loader.DATA_DIR / "us_annual_deaths.csv")
    assert signed["verified_by"].notna().all()
    assert signed["verified_date"].notna().all()
    # A person, not a machine string. promote() writes fetched_from; nothing
    # in src/fetch.py can write this column at all.
    assert not signed["verified_by"].astype(str).str.contains("wonder-export").any()


def test_corroboration_columns_are_never_required():
    """Blank corroboration means "not corroborated", never "failed".

    Corroboration is a separate claim from attestation: attestation says the
    value faithfully reproduces the export it was taken from, corroboration says
    a separate publication reports the same figure. The second is not
    available for every row -- NVSR publishes annual totals, not the six-band
    grid -- so requiring it would force a choice between claiming more than was
    checked and checking less than was possible.
    """
    import pandas as pd

    for name in ("us_annual_deaths.csv", "us_population.csv",
                 "deaths_by_age.csv", "covid_deaths_by_age.csv"):
        frame = pd.read_csv(loader.DATA_DIR / name)
        for col in ("corroborated_against", "corroborated_date"):
            assert col in frame.columns, f"{name} is missing {col}"

    # Entirely blank, and non-strict loading is unaffected by that.
    loader.load_annual_deaths(strict=False)
    loader.load_population(strict=False)

    # And a populated corroboration must not substitute for attestation.
    frame = pd.DataFrame({
        "year": [2010],
        "deaths": [1],
        "verified_by": [""],
        "corroborated_against": ["NVSR vol 71 no 5, Table B"],
    })
    with pytest.raises(loader.UnverifiedDataError):
        loader._require_verified(frame, "us_annual_deaths.csv")


def test_corroboration_is_partial_and_that_is_the_point():
    """2010 is corroborated; the other years are blank, and must stay loadable.

    Blank means not corroborated. If a blank ever blocked loading, the column
    would have become a second attestation requirement and the incentive would
    be to fill it with whatever was to hand.
    """
    import pandas as pd

    annual = pd.read_csv(loader.DATA_DIR / "us_annual_deaths.csv")
    done = annual[annual["corroborated_against"].notna()]
    assert list(done["year"]) == list(range(2010, 2023))
    assert (done["corroborated_date"] == "2026-08-30").all()

    # 2023 and 2024 blank -- no published report exists for either -- and
    # strict loading is indifferent to that.
    blank = annual[annual["corroborated_against"].isna()]
    assert list(blank["year"]) == [2023, 2024]
    loader.load_annual_deaths(strict=True)


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
