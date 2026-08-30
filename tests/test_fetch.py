"""Tests for the fetch layer. No test in this file touches the network.

Fixtures follow the same rule as conftest.py: invented numbers with known
analytic properties, deliberately unlike real U.S. figures, so nobody can
mistake a fixture for data. The age bands, however, are the real WONDER
spellings, because band handling is exactly what these tests exist to pin down.
"""
import json
from dataclasses import replace

import pandas as pd
import pytest

from src import fetch


# ---------------------------------------------------------------------------
# Synthetic sources
# ---------------------------------------------------------------------------

# Each source band carries a distinct round number so a collapse error shows up
# as an obviously wrong total rather than an off-by-a-little one.
#
#   0-24  = 10 + 20 + 30 + 40   = 100
#   25-44 = 50 + 60             = 110
#   45-64 = 70 + 80             = 150
#   65-74 = 90                  =  90
#   75-84 = 100                 = 100
#   85+   = 110                 = 110
#                          total = 660
BAND_DEATHS = [
    ("< 1 year", 10), ("1-4", 20), ("5-14", 30), ("15-24", 40),
    ("25-34", 50), ("35-44", 60),
    ("45-54", 70), ("55-64", 80),
    ("65-74", 90),
    ("75-84", 100),
    ("85+", 110),
]

EXPECTED_COLLAPSE = {
    "0-24": 100, "25-44": 110, "45-64": 150,
    "65-74": 90, "75-84": 100, "85+": 110,
}

def _footer(
    dataset: str = "Underlying Cause of Death, 1999-2020",
    icd10: str | None = None,
    query_date: str | None = "Jan 1, 2000 12:00:00 AM",
) -> str:
    """A WONDER-shaped footer.

    Dataset and Query Date are parameters because
    assert_export_footer_matches_spec checks them against the registry, and a
    fixture that could not vary them could not test the failure cases.
    """
    lines = ['"---"', f'"Dataset: {dataset}"', '"Query Parameters:"',
             '"Title: Fixture extract"']
    if icd10 is not None:
        lines.append(f'"ICD-10 Codes: {icd10}"')
    lines += ['"Group By: Year; Ten-Year Age Groups"', '"Show Totals: True"',
              '"---"']
    if query_date is not None:
        lines += [f'"Query Date: {query_date}"', '"---"']
    lines += ['"Caveats:"', '"Data are fictional."']
    return "\n".join(lines) + "\n"


WONDER_FOOTER = _footer()


def _wonder_export_text(
    not_stated: int | None = None,
    years: tuple[int, ...] = (2000,),
    population: int = 1_000_000,
    footer: str | None = None,
) -> str:
    """Build a WONDER-shaped TSV export with a footer."""
    header = (
        '"Notes"\t"Year"\t"Year Code"\t"Ten-Year Age Groups"\t'
        '"Ten-Year Age Groups Code"\t"Deaths"\t"Population"\t"Crude Rate"'
    )
    lines = [header]
    for year in years:
        for band, deaths in BAND_DEATHS:
            lines.append(
                f'\t"{year}"\t"{year}"\t"{band}"\t"x"\t"{deaths}"\t'
                f'"{population}"\t"1.0"'
            )
        if not_stated is not None:
            lines.append(
                f'\t"{year}"\t"{year}"\t"Not Stated"\t"NS"\t"{not_stated}"\t'
                f'"Not Applicable"\t"Not Applicable"'
            )
        total = sum(d for _, d in BAND_DEATHS) + (not_stated or 0)
        lines.append(
            f'"Total"\t"{year}"\t"{year}"\t\t\t"{total}"\t'
            f'"{population * len(BAND_DEATHS)}"\t"6.0"'
        )
    return "\n".join(lines) + "\n" + (footer if footer is not None else WONDER_FOOTER)


@pytest.fixture
def wonder_export(tmp_path):
    """A representative export with no unattributed-age rows."""
    path = tmp_path / "allcause_by_age_fixture.txt"
    path.write_text(_wonder_export_text(), encoding="utf-8")
    return path


@pytest.fixture
def band_frame():
    """The collapse input, as wonder_export_to_grid would hand it over."""
    return pd.DataFrame([
        {"year": 2000, "age_band": band, "deaths": deaths, "population": 1_000_000}
        for band, deaths in BAND_DEATHS
    ])


class FakeResponse:
    def __init__(self, text, status=200):
        self._text, self.status_code = text, status

    @property
    def text(self):
        return self._text

    def json(self):
        return json.loads(self._text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Records every call so a test can assert the network was not re-hit."""

    def __init__(self, response):
        self.response, self.calls = response, []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        return self.response


@pytest.fixture(autouse=True)
def isolate_dirs(tmp_path, monkeypatch):
    """Point every write at tmp_path. No test may touch data/ or the network."""
    monkeypatch.setattr(fetch, "FETCH_DIR", tmp_path / "fetched")
    monkeypatch.setattr(fetch, "DEBUG_DIR", tmp_path / "fetched" / "_debug")
    monkeypatch.setattr(fetch, "PROCESSED_DIR", tmp_path / "processed")

    def _no_network():
        raise AssertionError("a test tried to open a real HTTP session")

    monkeypatch.setattr(fetch, "_session", _no_network)


# ---------------------------------------------------------------------------
# Parsing a representative export
# ---------------------------------------------------------------------------


def test_parses_representative_export(wonder_export):
    """A well-formed export yields every band row and keeps its footer."""
    export = fetch.parse_wonder_export(wonder_export)

    assert len(export.frame) == len(BAND_DEATHS) + 1  # bands + the Total row
    assert export.query_parameters["Dataset"].startswith("Underlying Cause")
    assert export.query_parameters["Group By"] == "Year; Ten-Year Age Groups"
    assert len(export.sha256) == 64
    assert export.provenance().startswith("wonder-export:")


def test_grid_drops_the_total_row(wonder_export):
    """WONDER's per-year Total is a sum of rows already present.

    Keeping it would double every yearly figure.
    """
    grid = fetch.wonder_export_to_grid(fetch.parse_wonder_export(wonder_export))

    assert len(grid) == len(BAND_DEATHS)
    assert grid["deaths"].sum() == sum(d for _, d in BAND_DEATHS)
    assert set(grid.columns) == {
        "year", "age_band", "deaths", "population", "deaths_suppressed"
    }
    assert not grid["deaths_suppressed"].any()


def test_export_without_footer_is_rejected(tmp_path):
    """A table with no query footer is not a citable artifact."""
    path = tmp_path / "no_footer.txt"
    path.write_text('"Notes"\t"Year"\t"Deaths"\n\t"2000"\t"5"\n', encoding="utf-8")

    with pytest.raises(fetch.ParseError, match="footer"):
        fetch.parse_wonder_export(path)


def test_suppressed_count_raises_rather_than_becoming_zero(tmp_path):
    """Suppressed means unknown. Zero is a claim, and a false one."""
    text = _wonder_export_text().replace('"90"', '"Suppressed"', 1)
    path = tmp_path / "suppressed.txt"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(fetch.ParseError, match="[Ss]uppressed"):
        fetch.wonder_export_to_grid(fetch.parse_wonder_export(path))


def test_suppressed_not_stated_is_bounded_not_rejected(tmp_path):
    """WONDER suppresses below ten, so a suppressed cell is known to be <= 9.

    The Not Stated row never enters the six-band grid, so taking the bound
    there cannot put a fabricated number into any rate. Rejecting the export
    over it would block a file the user could not have produced any other way.
    """
    text = _wonder_export_text(not_stated=3).replace('"3"\t"Not Applicable"',
                                                     '"Suppressed"\t"Not Applicable"')
    path = tmp_path / "suppressed_ns.txt"
    path.write_text(text, encoding="utf-8")

    grid = fetch.wonder_export_to_grid(fetch.parse_wonder_export(path))
    ns_row = grid[grid["age_band"] == "Not Stated"].iloc[0]

    assert int(ns_row["deaths"]) == fetch.SUPPRESSION_UPPER_BOUND
    assert bool(ns_row["deaths_suppressed"]) is True
    # The six real bands are untouched and unflagged.
    assert not grid[grid["age_band"] != "Not Stated"]["deaths_suppressed"].any()


def test_suppressed_not_stated_is_marked_in_the_collapse(tmp_path):
    """A bounded figure must not be reported as though it were exact."""
    text = _wonder_export_text(not_stated=3).replace('"3"\t"Not Applicable"',
                                                     '"Suppressed"\t"Not Applicable"')
    path = tmp_path / "suppressed_ns2.txt"
    path.write_text(text, encoding="utf-8")

    grid = fetch.wonder_export_to_grid(fetch.parse_wonder_export(path))
    with pytest.warns(UserWarning, match="at most"):
        result = fetch.collapse_age_bands(grid, ["deaths", "population"])

    assert bool(result.not_stated.loc[0, "suppressed"]) is True
    assert "at most" in result.warnings[0]


def test_a_suppressed_analysis_band_still_raises(tmp_path):
    """The bound is usable only where the cell is not an analysis input."""
    text = _wonder_export_text().replace('"90"', '"Suppressed"', 1)
    path = tmp_path / "suppressed_band.txt"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(fetch.ParseError, match="[Ss]uppressed"):
        fetch.wonder_export_to_grid(fetch.parse_wonder_export(path))


def test_totals_are_optional_only_where_they_are_unused(tmp_path):
    """WONDER disables totals on suppressed queries; requiring them everywhere
    would reject an export the user could not produce another way."""
    covid = next(s for s in fetch.WONDER_EXPORTS
                 if s.series == "covid_deaths_by_age")
    allcause = next(s for s in fetch.GRID_EXPORTS
                    if s.series == "deaths_by_age")

    assert covid.require_totals is False   # crude-rate check does not use it
    assert allcause.require_totals is True  # crude-rate check does use it


def test_missing_show_column_names_what_to_re_export(tmp_path):
    text = _wonder_export_text().replace('\t"Population"', "\t\"Pop'n\"")
    path = tmp_path / "no_pop.txt"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(fetch.ParseError, match="Population"):
        fetch.wonder_export_to_grid(fetch.parse_wonder_export(path))


# ---------------------------------------------------------------------------
# Age-band collapse arithmetic
# ---------------------------------------------------------------------------


def test_collapse_sums_source_bands_into_the_six_groups(band_frame):
    """Each target group equals the sum of exactly its source bands."""
    result = fetch.collapse_age_bands(band_frame, ["deaths", "population"])
    got = dict(zip(result.frame["age_group"], result.frame["deaths"]))

    assert got == EXPECTED_COLLAPSE
    assert list(result.frame["age_group"]) == fetch.AGE_GROUPS


def test_collapse_conserves_the_total(band_frame):
    """Collapsing regroups deaths; it must not create or destroy any."""
    result = fetch.collapse_age_bands(band_frame, ["deaths"])

    assert result.frame["deaths"].sum() == band_frame["deaths"].sum()


def test_collapse_sums_population_alongside_deaths(band_frame):
    """0-24 draws on four source bands, so it carries four bands of population."""
    result = fetch.collapse_age_bands(band_frame, ["deaths", "population"])
    pops = dict(zip(result.frame["age_group"], result.frame["population"]))

    assert pops["0-24"] == 4_000_000
    assert pops["65-74"] == 1_000_000


@pytest.mark.parametrize("spelling", ["85 years and over", "85+ years", "85+"])
def test_band_spelling_variants_map_to_the_same_group(spelling):
    """NCHS spells bands several ways across databases; all must land alike."""
    assert fetch.canonical_band(spelling) == "85+"


def test_unknown_band_raises_rather_than_being_dropped():
    """An unrecognised band is deaths that would vanish from the totals."""
    frame = pd.DataFrame([
        {"year": 2000, "age_band": "40-49", "deaths": 5},
    ])

    with pytest.raises(fetch.ParseError, match="Unrecognised age band"):
        fetch.collapse_age_bands(frame, ["deaths"])


def test_missing_band_raises_so_a_year_is_never_silently_short(band_frame):
    """Dropping a source band would leave a year with five groups, not six."""
    short = band_frame[band_frame["age_band"] != "65-74"]

    with pytest.raises(fetch.ParseError, match="65-74"):
        fetch.collapse_age_bands(short, ["deaths"])


# ---------------------------------------------------------------------------
# "Not Stated" handling
# ---------------------------------------------------------------------------


def test_not_stated_is_reported_separately_never_dropped(band_frame):
    """Unattributed ages leave the grid but must survive as a reported total."""
    frame = pd.concat([
        band_frame,
        pd.DataFrame([{"year": 2000, "age_band": "Not Stated",
                       "deaths": 3, "population": 0}]),
    ], ignore_index=True)

    with pytest.warns(UserWarning):
        result = fetch.collapse_age_bands(frame, ["deaths", "population"])

    assert result.frame["deaths"].sum() == 660  # unchanged by the extra row
    assert "Not Stated" not in set(result.frame["age_group"])
    assert int(result.not_stated.loc[0, "deaths"]) == 3


def test_not_stated_above_threshold_warns_naming_year_and_percentage(band_frame):
    """3 of 663 deaths is 0.452%, over the 0.1% threshold."""
    frame = pd.concat([
        band_frame,
        pd.DataFrame([{"year": 2000, "age_band": "Not Stated",
                       "deaths": 3, "population": 0}]),
    ], ignore_index=True)

    with pytest.warns(UserWarning, match="2000"):
        result = fetch.collapse_age_bands(frame, ["deaths"])

    assert result.warnings
    assert "0.452" in result.warnings[0]
    assert result.not_stated.loc[0, "pct_of_deaths"] == pytest.approx(0.4525, abs=1e-3)


def test_not_stated_below_threshold_is_recorded_without_warning(band_frame):
    """Under 0.1% it is still reported, just not flagged."""
    big = band_frame.copy()
    big["deaths"] *= 1000  # total 660,000; one unattributed death is 0.00015%
    frame = pd.concat([
        big,
        pd.DataFrame([{"year": 2000, "age_band": "Not Stated",
                       "deaths": 1, "population": 0}]),
    ], ignore_index=True)

    with warnings_as_errors():
        result = fetch.collapse_age_bands(frame, ["deaths"])

    assert not result.warnings
    assert int(result.not_stated.loc[0, "deaths"]) == 1


@pytest.mark.parametrize("token", ["Not Stated", "Unknown", "NOT STATED", "unknown"])
def test_not_stated_spelling_variants_all_recognised(token):
    assert fetch.canonical_band(token) == fetch.NOT_STATED


def warnings_as_errors():
    import warnings as _w

    ctx = _w.catch_warnings()
    ctx.__enter__()
    _w.simplefilter("error")

    class _Ctx:
        def __enter__(self_inner):
            return None

        def __exit__(self_inner, *exc):
            ctx.__exit__(*exc)
            return False

    return _Ctx()


# ---------------------------------------------------------------------------
# Cache behaviour
# ---------------------------------------------------------------------------


def test_http_cache_miss_then_hit_does_not_re_request():
    """The second call on the same day must read the file, not the API."""
    session = FakeSession(FakeResponse('[{"year": "2000", "deaths": "5"}]'))

    first = fetch.fetch_raw("fixture", "https://example.invalid/x", session=session)
    second = fetch.fetch_raw("fixture", "https://example.invalid/x", session=session)

    assert first.from_cache is False
    assert second.from_cache is True
    assert len(session.calls) == 1
    assert first.body == second.body
    assert first.path.exists()


def test_refresh_forces_a_new_request():
    session = FakeSession(FakeResponse('[{"year": "2000", "deaths": "5"}]'))

    fetch.fetch_raw("fixture", "https://example.invalid/x", session=session)
    again = fetch.fetch_raw(
        "fixture", "https://example.invalid/x", session=session, refresh=True
    )

    assert again.from_cache is False
    assert len(session.calls) == 2


def test_raw_body_is_written_before_parsing():
    """The bytes a parse was based on must survive even when the parse fails."""
    session = FakeSession(FakeResponse("this is not json"))

    payload = fetch.fetch_raw("fixture", "https://example.invalid/x", session=session)

    assert payload.path.exists()
    assert payload.path.read_text(encoding="utf-8") == "this is not json"


def test_export_cache_is_keyed_on_content_not_date(wonder_export, tmp_path):
    """Re-parsing the same file hits the cache; a changed file does not."""
    grid1, export1, cached1 = fetch.load_export_cached("allcause", wonder_export)
    grid2, export2, cached2 = fetch.load_export_cached("allcause", wonder_export)

    assert cached1 is False
    assert cached2 is True
    assert export1.sha256 == export2.sha256
    pd.testing.assert_frame_equal(grid1, grid2)

    edited = tmp_path / "edited.txt"
    edited.write_text(_wonder_export_text(not_stated=7), encoding="utf-8")
    _, export3, cached3 = fetch.load_export_cached("allcause", edited)

    assert export3.sha256 != export1.sha256
    assert cached3 is False


def test_export_footer_is_cached_alongside_the_parse(wonder_export):
    """The footer is the provenance; it must not be lost on the way to cache."""
    _, export, _ = fetch.load_export_cached("allcause", wonder_export)
    footer_file = fetch.FETCH_DIR / f"allcause_{export.short_hash}.footer.txt"

    assert footer_file.exists()
    assert "Group By" in footer_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Malformed responses raise rather than returning partial data
# ---------------------------------------------------------------------------


def test_malformed_json_raises_and_logs_the_body():
    payload = fetch.FetchedPayload(
        series="fixture", body="<html>Access Denied</html>",
        path=fetch.FETCH_DIR / "unused", from_cache=False,
    )

    with pytest.raises(fetch.ParseError, match="not valid JSON"):
        fetch.parse_socrata_rows(payload, required=["year"])

    logged = list(fetch.DEBUG_DIR.glob("fixture_*.json"))
    assert len(logged) == 1
    assert "Access Denied" in logged[0].read_text(encoding="utf-8")


def test_missing_required_column_raises_and_does_not_return_a_partial_frame():
    """A silently absent column becomes a silently absent value downstream."""
    payload = fetch.FetchedPayload(
        series="fixture", body='[{"year": "2000"}]',
        path=fetch.FETCH_DIR / "unused", from_cache=False,
    )

    with pytest.raises(fetch.ParseError, match="missing required column"):
        fetch.parse_socrata_rows(payload, required=["year", "deaths"])


def test_empty_result_set_is_a_failure_not_an_absence_of_deaths():
    payload = fetch.FetchedPayload(
        series="fixture", body="[]",
        path=fetch.FETCH_DIR / "unused", from_cache=False,
    )

    with pytest.raises(fetch.ParseError, match="zero rows"):
        fetch.parse_socrata_rows(payload, required=["year"])


def test_socrata_error_object_is_not_mistaken_for_rows():
    """Socrata returns a JSON object, not an array, on error."""
    payload = fetch.FetchedPayload(
        series="fixture", body='{"error": true, "message": "invalid query"}',
        path=fetch.FETCH_DIR / "unused", from_cache=False,
    )

    with pytest.raises(fetch.ParseError, match="array of rows"):
        fetch.parse_socrata_rows(payload, required=["year"])


# ---------------------------------------------------------------------------
# Promotion never forges an attestation
# ---------------------------------------------------------------------------


def test_promote_dry_run_writes_nothing(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    csv_path = raw / "us_annual_deaths.csv"
    before = (
        "year,deaths,status,source_citation,source_type,fetched_from,"
        "verified_by,verified_date\n2000,,final,fixture,,,,\n"
    )
    csv_path.write_text(before, encoding="utf-8")

    diff = fetch.promote(
        "annual_deaths",
        values=pd.DataFrame([{"year": 2000, "deaths": 660}]),
        dataset_id="fixture-id",
        dry_run=True,
        raw_dir=raw,
    )

    assert len(diff) == 1
    assert csv_path.read_text(encoding="utf-8") == before


def test_promote_records_provenance_but_leaves_verified_by_blank(tmp_path):
    """Provenance is not attestation. Strict loading must still refuse."""
    raw = tmp_path / "raw"
    raw.mkdir()
    csv_path = raw / "us_annual_deaths.csv"
    csv_path.write_text(
        "year,deaths,status,source_citation,source_type,fetched_from,"
        "verified_by,verified_date\n2000,,final,fixture,,,,\n",
        encoding="utf-8",
    )

    fetch.promote(
        "annual_deaths",
        values=pd.DataFrame([{"year": 2000, "deaths": 660}]),
        dataset_id="fixture-id",
        dry_run=False,
        accessed="2000-01-01",
        raw_dir=raw,
    )
    out = pd.read_csv(csv_path)

    assert int(out.loc[0, "deaths"]) == 660
    assert out.loc[0, "source_type"] == fetch.SOURCE_TYPE_API
    assert out.loc[0, "fetched_from"] == "fetch:fixture-id@2000-01-01"
    assert pd.isna(out.loc[0, "verified_by"])


def test_promote_clears_a_stale_human_signoff(tmp_path):
    """A sign-off refers to the value that was signed, not to its replacement."""
    raw = tmp_path / "raw"
    raw.mkdir()
    csv_path = raw / "us_annual_deaths.csv"
    csv_path.write_text(
        "year,deaths,status,source_citation,source_type,fetched_from,"
        "verified_by,verified_date\n2000,999,final,fixture,manual,,TF,2000-01-01\n",
        encoding="utf-8",
    )

    diff = fetch.promote(
        "annual_deaths",
        values=pd.DataFrame([{"year": 2000, "deaths": 660}]),
        dataset_id="fixture-id",
        dry_run=False,
        raw_dir=raw,
    )
    out = pd.read_csv(csv_path)

    assert bool(diff.loc[0, "cleared_attestation"]) is True
    assert pd.isna(out.loc[0, "verified_by"])


def test_promote_refuses_without_a_dataset_id(tmp_path):
    """fetched_from must record real provenance, never a placeholder."""
    with pytest.raises(fetch.FetchError, match="dataset_id"):
        fetch.promote(
            "annual_deaths",
            values=pd.DataFrame([{"year": 2000, "deaths": 660}]),
            dataset_id=None,
        )


# ---------------------------------------------------------------------------
# Vintage seam
# ---------------------------------------------------------------------------


def _grid(populations, deaths=None):
    """A collapsed six-band grid for one year, 2018."""
    deaths = deaths or {g: 100 for g in fetch.AGE_GROUPS}
    return pd.DataFrame([
        {"year": 2018, "age_group": g, "deaths": deaths[g], "population": populations[g]}
        for g in fetch.AGE_GROUPS
    ])


def test_seam_measures_population_difference_per_band():
    """65-74 differs by 1%: 1,010,000 against 1,000,000."""
    bridged = _grid({g: 1_000_000 for g in fetch.AGE_GROUPS})
    single = _grid({**{g: 1_000_000 for g in fetch.AGE_GROUPS}, "65-74": 1_010_000})

    seam = fetch.seam_comparison(bridged, single)
    row = seam[seam["age_group"] == "65-74"].iloc[0]

    assert row["population_abs_diff"] == 10_000
    assert row["population_pct_diff"] == pytest.approx(1.0)
    assert row["deaths_pct_diff"] == pytest.approx(0.0)


def test_seam_above_threshold_is_reported_material():
    bridged = _grid({g: 1_000_000 for g in fetch.AGE_GROUPS})
    single = _grid({**{g: 1_000_000 for g in fetch.AGE_GROUPS}, "85+": 1_009_000})

    verdict = fetch.seam_verdict(fetch.seam_comparison(bridged, single))

    assert verdict["material"] is True
    assert verdict["worst_cell"] == "2018 85+"
    assert verdict["worst_population_pct"] == pytest.approx(0.9)


def test_seam_below_threshold_is_not_material():
    bridged = _grid({g: 1_000_000 for g in fetch.AGE_GROUPS})
    single = _grid({**{g: 1_000_000 for g in fetch.AGE_GROUPS}, "85+": 1_001_000})

    verdict = fetch.seam_verdict(fetch.seam_comparison(bridged, single))

    assert verdict["material"] is False
    assert verdict["worst_population_pct"] == pytest.approx(0.1)


def test_seam_flags_moving_deaths_as_a_query_mismatch():
    """The same certificates appear under both vintages. Deaths must not move."""
    bridged = _grid({g: 1_000_000 for g in fetch.AGE_GROUPS})
    single = _grid(
        {g: 1_000_000 for g in fetch.AGE_GROUPS},
        deaths={**{g: 100 for g in fetch.AGE_GROUPS}, "45-64": 140},
    )

    verdict = fetch.seam_verdict(fetch.seam_comparison(bridged, single))

    assert verdict["deaths_suspicious"] is True


def test_seam_requires_overlapping_years():
    """A seam export that shares no years with the grid measures nothing."""
    bridged = _grid({g: 1_000_000 for g in fetch.AGE_GROUPS})
    single = bridged.assign(year=2022)

    with pytest.raises(fetch.FetchError, match="overlapping"):
        fetch.seam_comparison(bridged, single)


def test_report_says_seam_is_unmeasured_when_export_absent():
    """Silence about the seam is the failure mode; say so explicitly."""
    text = "\n".join(fetch.render_seam_section(None))

    assert "unmeasured" in text
    assert fetch.SEAM_EXPORT.filename in text


def test_seam_export_is_not_part_of_the_analysis_grid():
    """It is a measurement of the grid, never a row in it."""
    assert fetch.SEAM_EXPORT.in_analysis_grid is False
    assert fetch.SEAM_EXPORT not in fetch.GRID_EXPORTS
    assert all(s.series != "seam_bridged" for s in fetch.GRID_EXPORTS)


def test_analysis_grid_covers_2010_to_2024_without_provisional_data():
    """No provisional database may enter the grid; 2024 is final single-race."""
    covered = set()
    for spec in fetch.GRID_EXPORTS:
        if spec.series == "deaths_by_age":
            covered |= set(spec.years)
        assert "Provisional" not in spec.database

    assert covered == set(range(2010, 2025))


def test_analysis_grid_years_never_overlap():
    """An overlapping year would be assembled from two databases."""
    seen = set()
    for spec in fetch.GRID_EXPORTS:
        if spec.series != "deaths_by_age":
            continue
        assert not (seen & set(spec.years)), f"{spec.filename} overlaps"
        seen |= set(spec.years)


def test_seam_end_to_end_from_export_files(tmp_path):
    """Two real export files through routing, collapse, comparison and render.

    Single-race population is 0.6% above bridged in every band, which is over
    the materiality convention, so the report must say so.
    """
    export_dir = tmp_path / "wonder_exports"
    export_dir.mkdir()
    years = (2018, 2019, 2020)

    single_spec = next(
        s for s in fetch.GRID_EXPORTS
        if s.series == "deaths_by_age" and 2018 in s.years
    )
    # Each file must carry exactly the years its spec declares, or
    # assert_export_years_match_spec rejects it. The seam is then measured on
    # the overlap: the seam export's three years against the single-race
    # export's seven.
    assert fetch.SEAM_EXPORT.years == years
    (export_dir / fetch.SEAM_EXPORT.filename).write_text(
        _wonder_export_text(years=years, population=1_000_000), encoding="utf-8"
    )
    (export_dir / single_spec.filename).write_text(
        _wonder_export_text(
            years=single_spec.years, population=1_006_000,
            footer=_footer(dataset=single_spec.footer_dataset),
        ),
        encoding="utf-8",
    )

    seam = fetch.load_seam(export_dir=export_dir)

    assert len(seam) == len(years) * len(fetch.AGE_GROUPS)
    assert seam["population_pct_diff"].round(3).eq(0.6).all()
    assert seam["deaths_pct_diff"].abs().max() == pytest.approx(0.0)

    verdict = fetch.seam_verdict(seam)
    assert verdict["material"] is True
    assert verdict["deaths_suspicious"] is False

    text = "\n".join(fetch.render_seam_section(seam))
    assert "Material" in text
    assert "0.600%" in text


def test_seam_is_none_when_only_one_side_is_present(tmp_path):
    """One export alone measures nothing, and must not half-report."""
    export_dir = tmp_path / "wonder_exports"
    export_dir.mkdir()
    (export_dir / fetch.SEAM_EXPORT.filename).write_text(
        _wonder_export_text(years=fetch.SEAM_EXPORT.years), encoding="utf-8"
    )

    assert fetch.load_seam(export_dir=export_dir) is None


# ---------------------------------------------------------------------------
# The annual identity
# ---------------------------------------------------------------------------


def _collapse_with_not_stated(not_stated: int):
    frame = pd.DataFrame([
        {"year": 2000, "age_band": band, "deaths": deaths}
        for band, deaths in BAND_DEATHS
    ] + [{"year": 2000, "age_band": "Not Stated", "deaths": not_stated}])
    with warnings_as_errors() if not_stated == 0 else _nullcontext():
        return fetch.collapse_age_bands(frame, ["deaths"], warn_pct=100.0)


def _nullcontext():
    class _C:
        def __enter__(self):
            return None

        def __exit__(self, *exc):
            return False

    return _C()


def test_annual_total_includes_not_stated():
    """The published NVSR figure counts them; the six bands do not."""
    result = _collapse_with_not_stated(3)
    annual = fetch.derive_annual_deaths([result])

    assert int(annual.loc[0, "deaths"]) == 663  # 660 banded + 3 unattributed
    assert int(annual.loc[0, "not_stated"]) == 3


def test_annual_identity_holds_exactly():
    result = _collapse_with_not_stated(3)
    annual = fetch.derive_annual_deaths([result])

    fetch.assert_annual_identity(annual, result.frame)  # must not raise


def test_annual_identity_catches_a_gap_far_below_any_percentage_tolerance():
    """A 0.005% shortfall passes every drift threshold and is still wrong.

    This is the whole reason the check is an identity: 3 deaths in 663 is
    0.45%, and the real-world case is a hundredfold smaller still.
    """
    result = _collapse_with_not_stated(3)
    annual = fetch.derive_annual_deaths([result])
    annual.loc[0, "deaths"] = 660  # the banded sum, omitting Not Stated

    with pytest.raises(fetch.FetchError, match="identity violated"):
        fetch.assert_annual_identity(annual, result.frame)


def test_annual_identity_is_not_a_tolerance():
    """Off by one death must fail. No margin at all."""
    result = _collapse_with_not_stated(3)
    annual = fetch.derive_annual_deaths([result])
    annual.loc[0, "deaths"] = 664

    with pytest.raises(fetch.FetchError, match="identity violated"):
        fetch.assert_annual_identity(annual, result.frame)


def test_annual_deaths_with_no_unattributed_rows_still_carries_the_column():
    result = _collapse_with_not_stated(0)
    annual = fetch.derive_annual_deaths([result])

    assert int(annual.loc[0, "not_stated"]) == 0
    assert int(annual.loc[0, "deaths"]) == 660
    fetch.assert_annual_identity(annual, result.frame)


# ---------------------------------------------------------------------------
# Population identity and the crude-rate check against WONDER
# ---------------------------------------------------------------------------


def test_population_identity_holds_exactly(band_frame):
    result = fetch.collapse_age_bands(band_frame, ["deaths", "population"])
    population = fetch.derive_population([result])

    assert int(population.loc[0, "population"]) == 11_000_000  # 11 bands
    fetch.assert_population_identity(population, result.frame)


def test_population_identity_is_not_a_tolerance(band_frame):
    """Both sides come from one export, so off by one person must fail."""
    result = fetch.collapse_age_bands(band_frame, ["deaths", "population"])
    population = fetch.derive_population([result])
    population.loc[0, "population"] = 11_000_001

    with pytest.raises(fetch.FetchError, match="Population identity violated"):
        fetch.assert_population_identity(population, result.frame)


def test_totals_are_read_from_wonders_own_rows(wonder_export):
    """The Total rows are WONDER's published figures, not our restatement."""
    totals = fetch.wonder_export_totals(fetch.parse_wonder_export(wonder_export))

    assert list(totals["year"]) == [2000]
    assert int(totals.loc[0, "deaths"]) == 660
    assert totals.loc[0, "crude_rate"] == 6.0


def test_export_without_total_rows_is_rejected(tmp_path):
    """Without WONDER's totals there is no external check to run."""
    text = _wonder_export_text().replace('"Total"\t', '\t')
    path = tmp_path / "no_totals.txt"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(fetch.ParseError, match="Show Totals"):
        fetch.wonder_export_totals(fetch.parse_wonder_export(path))


def test_crude_rate_matching_wonder_passes():
    """660 deaths over 11,000,000 is 6.0 per 100,000, which is what WONDER says."""
    annual = pd.DataFrame([{"year": 2000, "deaths": 660}])
    population = pd.DataFrame([{"year": 2000, "population": 11_000_000}])
    totals = pd.DataFrame([{"year": 2000, "crude_rate": 6.0}])

    check = fetch.crude_rate_check(annual, population, totals)

    assert bool(check.loc[0, "matches"]) is True
    assert check.loc[0, "computed_crude_rate"] == 6.0
    fetch.assert_crude_rate_matches_wonder(check)


def test_crude_rate_disagreeing_with_wonder_raises():
    """A denominator error shows up here even when both sides look plausible."""
    annual = pd.DataFrame([{"year": 2000, "deaths": 660}])
    population = pd.DataFrame([{"year": 2000, "population": 10_000_000}])
    totals = pd.DataFrame([{"year": 2000, "crude_rate": 6.0}])

    check = fetch.crude_rate_check(annual, population, totals)

    assert bool(check.loc[0, "matches"]) is False
    with pytest.raises(fetch.FetchError, match="disagrees with WONDER"):
        fetch.assert_crude_rate_matches_wonder(check)


def test_crude_rate_compared_at_wonders_own_precision():
    """WONDER prints one decimal, so agreement is judged at one decimal.

    661/11,000,000 is 6.00909 per 100,000, which WONDER would print as 6.0.
    Demanding more precision than WONDER publishes would fail on its rounding.
    """
    annual = pd.DataFrame([{"year": 2000, "deaths": 661}])
    population = pd.DataFrame([{"year": 2000, "population": 11_000_000}])
    totals = pd.DataFrame([{"year": 2000, "crude_rate": 6.0}])

    check = fetch.crude_rate_check(annual, population, totals)

    assert check.loc[0, "computed_crude_rate"] == 6.0
    assert bool(check.loc[0, "matches"]) is True


def test_saved_query_url_defaults_blank_and_stays_optional():
    """Exports parse with no saved query link, because the footer is the artifact.

    Asserts the property rather than the current contents of the registry: the
    field defaults blank, and blank stays valid for a real entry. File 1 was
    exported before the field existed and will never carry a link, so a
    populated URL must never become a precondition for anything.
    """
    assert fetch.ExportSpec("x.txt", "s", (2020,), "db").saved_query_url == ""
    assert any(s.saved_query_url == "" for s in fetch.WONDER_EXPORTS)


def test_saved_query_url_does_not_affect_parsing(tmp_path):
    """A dead CDC link must never change a result. It is for reviewers, not code."""
    export_dir = tmp_path / "wonder_exports"
    export_dir.mkdir()
    spec = fetch.SEAM_EXPORT
    (export_dir / spec.filename).write_text(
        _wonder_export_text(years=spec.years), encoding="utf-8"
    )

    without = fetch.load_export_bundle(spec, export_dir)
    with_url = fetch.load_export_bundle(
        replace(spec, saved_query_url="https://wonder.cdc.gov/saved/does-not-exist"),
        export_dir,
        refresh=True,
    )

    pd.testing.assert_frame_equal(without.collapsed.frame, with_url.collapsed.frame)
    pd.testing.assert_frame_equal(without.totals, with_url.totals)
    assert without.export.sha256 == with_url.export.sha256


# ---------------------------------------------------------------------------
# The footer vs. the registry
# ---------------------------------------------------------------------------
#
# Every other check verifies the export against itself or against our
# arithmetic. The crude-rate check compares WONDER's deaths over WONDER's
# population against WONDER's own rate, so it validates the pipeline, not the
# query -- an export run with the wrong filter passes all of them and simply
# reports fewer deaths than it should. The footer is the only record of what was
# actually asked.


def _export_with_footer(tmp_path, spec, footer):
    export_dir = tmp_path / "wonder_exports"
    export_dir.mkdir(exist_ok=True)
    (export_dir / spec.filename).write_text(
        _wonder_export_text(years=spec.years, footer=footer), encoding="utf-8"
    )
    return export_dir


def test_every_committed_export_footer_matches_its_spec():
    """The real files, checked rather than read once and remembered."""
    checked = 0
    for spec in fetch.WONDER_EXPORTS:
        path = fetch.WONDER_EXPORT_DIR / spec.filename
        if not path.exists():
            continue
        export = fetch.parse_wonder_export(path)
        fetch.assert_export_footer_matches_spec(spec, export)
        assert spec.footer_dataset, f"{spec.filename} has no expected Dataset"
        checked += 1
    assert checked == 4


def test_footer_naming_the_wrong_database_is_rejected(tmp_path):
    """Bridged-race and single-race are different denominators."""
    spec = fetch.SEAM_EXPORT
    export_dir = _export_with_footer(
        tmp_path, spec,
        _footer(dataset="Underlying Cause of Death, 2018-2024, Single Race"),
    )
    with pytest.raises(fetch.FetchError) as excinfo:
        fetch.load_export_bundle(spec, export_dir)
    message = str(excinfo.value)
    assert "registry expects: 'Underlying Cause of Death, 1999-2020'" in message
    assert "Single Race" in message


def test_an_all_cause_export_that_came_back_filtered_is_rejected(tmp_path):
    """The dangerous direction: nothing else would notice.

    A cause-filtered file standing in for an all-cause one parses cleanly, has
    the right years, satisfies both identities among its own rows, and simply
    understates every death count.
    """
    spec = fetch.SEAM_EXPORT
    assert spec.icd10_codes == (), "this spec must be all-cause for the test"
    export_dir = _export_with_footer(
        tmp_path, spec, _footer(icd10="U07.1 (COVID-19)")
    )
    with pytest.raises(fetch.FetchError) as excinfo:
        fetch.load_export_bundle(spec, export_dir)
    assert "expected none (all causes)" in str(excinfo.value)


def test_a_cause_specific_export_missing_its_code_is_rejected(tmp_path):
    from dataclasses import replace

    spec = replace(fetch.SEAM_EXPORT, icd10_codes=("U07.1",))
    export_dir = _export_with_footer(tmp_path, spec, _footer())
    with pytest.raises(fetch.FetchError) as excinfo:
        fetch.load_export_bundle(spec, export_dir)
    assert "all-cause where a cause-specific query was intended" in str(excinfo.value)


def test_a_footer_with_no_access_date_is_rejected(tmp_path):
    """The access date is what pins which population vintage a run used."""
    spec = fetch.SEAM_EXPORT
    export_dir = _export_with_footer(tmp_path, spec, _footer(query_date=None))
    with pytest.raises(fetch.FetchError) as excinfo:
        fetch.load_export_bundle(spec, export_dir)
    assert "Query Date" in str(excinfo.value)


def test_export_citation_is_built_from_the_footer():
    """The citation must describe the file, not be typed alongside it."""
    spec = next(s for s in fetch.WONDER_EXPORTS if s.icd10_codes)
    export = fetch.parse_wonder_export(fetch.WONDER_EXPORT_DIR / spec.filename)
    citation = fetch.export_citation(spec, export)

    assert spec.filename in citation
    assert export.short_hash in citation
    assert spec.footer_dataset in citation
    assert "U07.1" in citation
    # The database it is NOT: the old citation claimed Multiple Cause of Death,
    # which Query 3 warns differs from underlying cause by 10-15%.
    assert "MCD" not in citation


def test_citation_records_an_unpinned_year_range_as_unpinned():
    """Export 2's footer has no Year/Month line, and the citation says so."""
    spec = next(
        s for s in fetch.GRID_EXPORTS
        if s.series == "deaths_by_age" and 2024 in s.years
    )
    export = fetch.parse_wonder_export(fetch.WONDER_EXPORT_DIR / spec.filename)
    citation = fetch.export_citation(spec, export)
    assert "all years in the database at access" in citation
    assert "2018-2024 in this file" in citation


# ---------------------------------------------------------------------------
# Declared years vs. the file
# ---------------------------------------------------------------------------
#
# ExportSpec.years is otherwise used only by the tests, for grid coverage and
# non-overlap, and by load_seam() to pick the single-race spec -- so without
# the assertion below it reads like a guard while guarding nothing.
#
# The motivating case is export 2, whose footer carries no Year/Month line: its
# saved query may replay as "all dates" and pick up 2025 once WONDER adds it,
# with no change to the link. The widened file would otherwise parse cleanly,
# join the analysis grid, and extend the crude-rate check by a year.


def _seam_export_at(export_dir, years):
    (export_dir / fetch.SEAM_EXPORT.filename).write_text(
        _wonder_export_text(years=years), encoding="utf-8"
    )
    return fetch.SEAM_EXPORT


def test_export_carrying_an_undeclared_year_is_rejected(tmp_path):
    """The export-2 replay hazard: a file that came back one year wider."""
    export_dir = tmp_path / "wonder_exports"
    export_dir.mkdir()
    spec = _seam_export_at(export_dir, fetch.SEAM_EXPORT.years + (2021,))

    with pytest.raises(fetch.FetchError) as excinfo:
        fetch.load_export_bundle(spec, export_dir)

    message = str(excinfo.value)
    # Both ranges named outright, so the diagnosis needs neither file opened.
    assert "declares: 2018-2020" in message
    assert "contains:       2018-2021" in message
    assert "present in the file but not declared: 2021" in message


def test_export_missing_a_declared_year_is_rejected(tmp_path):
    """Truncation is as wrong as widening, and just as quiet."""
    export_dir = tmp_path / "wonder_exports"
    export_dir.mkdir()
    spec = _seam_export_at(export_dir, (2018, 2020))

    with pytest.raises(fetch.FetchError) as excinfo:
        fetch.load_export_bundle(spec, export_dir)

    message = str(excinfo.value)
    assert "declares: 2018-2020" in message
    assert "contains:       2018, 2020" in message
    assert "declared but absent from the file: 2019" in message


def test_matching_years_load_without_complaint(tmp_path):
    """The check must not fire on the case it exists to permit."""
    export_dir = tmp_path / "wonder_exports"
    export_dir.mkdir()
    spec = _seam_export_at(export_dir, fetch.SEAM_EXPORT.years)

    bundle = fetch.load_export_bundle(spec, export_dir)

    assert sorted(bundle.collapsed.frame["year"].unique()) == list(spec.years)


def test_year_range_formatting_collapses_contiguous_runs():
    """The message is only readable if 2018-2024 does not print as seven years."""
    assert fetch._format_year_range([2018, 2019, 2020, 2021]) == "2018-2021"
    assert fetch._format_year_range([2018, 2020, 2021]) == "2018, 2020-2021"
    assert fetch._format_year_range([2024]) == "2024"
    assert fetch._format_year_range([]) == "(none)"


# ---------------------------------------------------------------------------
# Vintage uniformity
# ---------------------------------------------------------------------------
#
# NOTE: the fixture below breaks this suite's usual rule that fixtures are
# obviously-unreal numbers. It uses REAL published Census figures, deliberately,
# because the whole point of the test is that this exact historical case is
# non-uniform in a way its national total conceals. A synthetic stand-in would
# only prove the arithmetic, not that the threshold catches the case it was
# calibrated on.
#
# These values are a REGRESSION FIXTURE, not analysis input. Nothing in
# data/raw/ should ever be populated from them -- the pipeline fetches its own.

# Census Bureau, nc-est2020-agesex-res.csv (Vintage 2020), SEX=0, national.
# CENSUS2010POP = April 1 2010 decennial count, which is what WONDER carries.
# POPESTIMATE2010 = the published July 1 2010 estimate.
CENSUS_2010_APRIL1 = {
    "0-24": 104_853_555, "25-44": 82_134_554, "45-64": 81_489_445,
    "65-74": 21_713_429, "75-84": 13_061_122, "85+": 5_493_433,
}
CENSUS_2010_JULY1 = {
    "0-24": 104_886_738, "25-44": 82_192_810, "45-64": 81_769_346,
    "65-74": 21_856_431, "75-84": 13_078_302, "85+": 5_543_516,
}


def _two_year_frame(year_a_pops, year_b_pops):
    rows = []
    for year, pops in ((2010, year_a_pops), (2011, year_b_pops)):
        for band in fetch.AGE_GROUPS:
            rows.append({"year": year, "age_group": band,
                         "deaths": 1000, "population": pops[band]})
    return pd.DataFrame(rows)


def test_real_2010_april_to_july_is_flagged_non_uniform():
    """The historical case the threshold was calibrated on.

    Nationally +0.188%, which looks like a small uniform nudge. Band by band
    it runs +0.032% to +0.912% -- a 28-fold spread that moved the age effect,
    not just the rate effect.
    """
    frame = _two_year_frame(CENSUS_2010_APRIL1, CENSUS_2010_JULY1)

    result = fetch.assess_vintage_uniformity(frame, 2010, 2011)

    assert result.uniform is False
    assert result.total_pct_change == pytest.approx(0.188, abs=0.002)
    assert result.min_pct == pytest.approx(0.032, abs=0.002)
    assert result.max_pct == pytest.approx(0.912, abs=0.002)
    assert result.fold == pytest.approx(28.5, abs=0.5)
    assert result.spread_ratio > fetch.VINTAGE_UNIFORMITY_SPREAD_MULTIPLE


def test_the_national_total_alone_would_not_have_caught_it():
    """The point of the function: the total looks benign and is not.

    0.184% is small enough to wave through, which is exactly why the check
    has to be at band level.
    """
    frame = _two_year_frame(CENSUS_2010_APRIL1, CENSUS_2010_JULY1)
    result = fetch.assess_vintage_uniformity(frame, 2010, 2011)

    assert abs(result.total_pct_change) < 0.2      # would pass any eyeball test
    assert result.spread_pp > 4 * abs(result.total_pct_change)


def test_a_proportional_revision_is_uniform():
    """Every band up by exactly 1%: shares unchanged, books as a rate effect."""
    uniform_b = {band: int(round(pop * 1.01))
                 for band, pop in CENSUS_2010_APRIL1.items()}
    frame = _two_year_frame(CENSUS_2010_APRIL1, uniform_b)

    result = fetch.assess_vintage_uniformity(frame, 2010, 2011)

    assert result.uniform is True
    assert result.total_pct_change == pytest.approx(1.0, abs=0.001)
    assert result.spread_pp < 0.01
    assert "rate effect" in result.summary()


def test_uniformity_verdict_names_the_consequence():
    """A verdict nobody can act on is not worth returning."""
    frame = _two_year_frame(CENSUS_2010_APRIL1, CENSUS_2010_JULY1)

    summary = fetch.assess_vintage_uniformity(frame, 2010, 2011).summary()

    assert "NON-UNIFORM" in summary
    assert "age effect" in summary


def test_uniformity_requires_all_six_bands():
    """A missing band would silently narrow the spread it is measuring."""
    frame = _two_year_frame(CENSUS_2010_APRIL1, CENSUS_2010_JULY1)
    frame = frame[frame["age_group"] != "85+"]  # the largest mover

    with pytest.raises(fetch.FetchError, match="expected all of"):
        fetch.assess_vintage_uniformity(frame, 2010, 2011)


def test_uniformity_raises_on_a_missing_year():
    frame = _two_year_frame(CENSUS_2010_APRIL1, CENSUS_2010_JULY1)

    with pytest.raises(fetch.FetchError, match="no rows for year"):
        fetch.assess_vintage_uniformity(frame, 2010, 1999)


def test_spread_against_a_near_zero_total_is_non_uniform():
    """Offsetting band moves can net to zero nationally and still shift shares."""
    offset = dict(CENSUS_2010_APRIL1)
    offset["0-24"] = CENSUS_2010_APRIL1["0-24"] - 1_000_000
    offset["85+"] = CENSUS_2010_APRIL1["85+"] + 1_000_000
    frame = _two_year_frame(CENSUS_2010_APRIL1, offset)

    result = fetch.assess_vintage_uniformity(frame, 2010, 2011)

    assert abs(result.total_pct_change) < 0.001   # invisible in the total
    assert result.uniform is False


def test_unconfirmed_series_cannot_be_fetched():
    """No identifier may enter SERIES except one read from a live response."""
    with pytest.raises(fetch.UnconfirmedSeriesError, match="--discover"):
        fetch.get_series("deaths_by_age")
