"""Attestation and corroboration: two human claims, kept apart.

src/attest.py records decisions people make. These tests pin the refusals --
the cases where it declines to record something, which is the only part of a
signing tool that carries any weight.
"""
import shutil

import pandas as pd
import pytest

from src import attest


@pytest.fixture
def raw(tmp_path):
    """A minimal raw directory with one populated, cited, unsigned row."""
    d = tmp_path / "raw"
    d.mkdir()
    (d / "us_annual_deaths.csv").write_text(
        "year,deaths,not_stated,status,source_citation,source_type,"
        "fetched_from,verified_by,verified_date,corroborated_against,"
        "corroborated_date\n"
        "2010,2468435,126,final,CDC WONDER export x,api,wonder-export:x,,,,\n"
        "2011,2515458,134,final,CDC WONDER export x,api,wonder-export:x,,,,\n",
        encoding="utf-8",
    )
    return d


def _read(raw):
    return pd.read_csv(raw / "us_annual_deaths.csv")


# ---------------------------------------------------------------------------
# Attestation
# ---------------------------------------------------------------------------


def test_attest_writes_the_signer_and_date(raw):
    attest.attest(name="A Person", date="2026-08-30",
                  files=["us_annual_deaths.csv"], raw_dir=raw, dry_run=False)
    frame = _read(raw)
    assert list(frame["verified_by"]) == ["A Person", "A Person"]
    assert list(frame["verified_date"]) == ["2026-08-30", "2026-08-30"]


def test_attest_refuses_a_blank_signer(raw):
    with pytest.raises(attest.AttestationError) as e:
        attest.attest(name="   ", files=["us_annual_deaths.csv"], raw_dir=raw)
    assert "needs the name" in str(e.value)


def test_attest_refuses_a_row_with_no_citation(raw):
    frame = _read(raw)
    frame.loc[0, "source_citation"] = ""
    frame.to_csv(raw / "us_annual_deaths.csv", index=False)

    with pytest.raises(attest.AttestationError) as e:
        attest.attest(name="A Person", files=["us_annual_deaths.csv"], raw_dir=raw)
    assert "cannot be checked by anyone" in str(e.value)


def test_attest_will_not_overwrite_someone_elses_signature(raw):
    attest.attest(name="First Person", files=["us_annual_deaths.csv"],
                  raw_dir=raw, dry_run=False)
    with pytest.raises(attest.AttestationError) as e:
        attest.attest(name="Second Person", files=["us_annual_deaths.csv"],
                      raw_dir=raw, dry_run=False)
    assert "does not transfer" in str(e.value)


def test_attest_skips_a_row_with_no_value(raw):
    """Signing an empty cell attests to nothing."""
    frame = _read(raw)
    frame.loc[1, "deaths"] = None
    frame.to_csv(raw / "us_annual_deaths.csv", index=False)

    diff = attest.attest(name="A Person", files=["us_annual_deaths.csv"],
                         raw_dir=raw, dry_run=False)
    assert len(diff) == 1
    written = _read(raw)
    assert written.loc[0, "verified_by"] == "A Person"
    assert pd.isna(written.loc[1, "verified_by"])


def test_attest_never_touches_corroboration(raw):
    """The two claims are independent; signing must not imply the other."""
    attest.attest(name="A Person", files=["us_annual_deaths.csv"],
                  raw_dir=raw, dry_run=False)
    frame = _read(raw)
    assert frame["corroborated_against"].isna().all()


# ---------------------------------------------------------------------------
# Corroboration
# ---------------------------------------------------------------------------


def test_corroborate_writes_one_year_only(raw):
    attest.corroborate(source="NVSR Vol. 61 No. 4, Table B", year=2010,
                       files=["us_annual_deaths.csv"], measures="count,rate",
                       date="2026-08-30", raw_dir=raw, dry_run=False)
    frame = _read(raw).set_index("year")
    assert frame.loc[2010, "corroborated_against"] == "NVSR Vol. 61 No. 4, Table B"
    assert frame.loc[2010, "corroborated_date"] == "2026-08-30"
    # 2011 untouched. Partial corroboration is the expected state.
    assert pd.isna(frame.loc[2011, "corroborated_against"])


def test_corroborate_refuses_a_vague_source(raw):
    with pytest.raises(attest.AttestationError) as e:
        attest.corroborate(source="  ", year=2010, measures="count",
                           files=["us_annual_deaths.csv"], raw_dir=raw)
    assert "specific enough" in str(e.value)


def test_corroborate_refuses_to_overwrite_a_different_source(raw):
    attest.corroborate(source="NVSR 61-4, Table B", year=2010, measures="count",
                       files=["us_annual_deaths.csv"], raw_dir=raw, dry_run=False)
    with pytest.raises(attest.AttestationError) as e:
        attest.corroborate(source="NVSR Vol. 70 No. 8, Table B", year=2010,
                           files=["us_annual_deaths.csv"], measures="count",
                           raw_dir=raw, dry_run=False)
    assert "already corroborated" in str(e.value)


def test_corroborate_refuses_a_source_with_no_number(raw):
    """A citation naming no volume, issue or table cannot be looked up.

    This exists because a shell loop interpolated an empty variable and wrote
    "NVSR Vol. , Table B" onto twelve rows: non-blank, plausible at a glance,
    and useless. Every other check passed it.
    """
    with pytest.raises(attest.AttestationError) as e:
        attest.corroborate(source="NVSR Vol. , Table B", year=2010, measures="count",
                           files=["us_annual_deaths.csv"], raw_dir=raw)
    assert "contains no number" in str(e.value)


def test_corroborate_rejects_a_year_that_is_not_there(raw):
    with pytest.raises(attest.AttestationError) as e:
        attest.corroborate(source="NVSR 74-4, Table B", year=1999, measures="count",
                           files=["us_annual_deaths.csv"], raw_dir=raw)
    assert "no rows for year 1999" in str(e.value)


def test_corroborate_does_not_imply_attestation(raw):
    """An external source agreeing is not a person having checked our copy."""
    attest.corroborate(source="NVSR 61-4, Table B", year=2010, measures="count",
                       files=["us_annual_deaths.csv"], raw_dir=raw, dry_run=False)
    frame = _read(raw)
    assert frame["verified_by"].isna().all()


def test_dry_run_writes_nothing(raw):
    before = (raw / "us_annual_deaths.csv").read_text(encoding="utf-8")
    attest.attest(name="A Person", files=["us_annual_deaths.csv"], raw_dir=raw)
    attest.corroborate(source="NVSR 61-4, Table B", year=2010, measures="count",
                       files=["us_annual_deaths.csv"], raw_dir=raw)
    assert (raw / "us_annual_deaths.csv").read_text(encoding="utf-8") == before


def test_corroborate_requires_measures(raw):
    """"Corroborated" without saying of what is not comparable to anything."""
    with pytest.raises(attest.AttestationError) as e:
        attest.corroborate(source="NVSR 74-11, Table", year=2010, measures="",
                           files=["us_annual_deaths.csv"], raw_dir=raw)
    assert "needs `measures`" in str(e.value)


def test_corroborate_rejects_an_unknown_measure(raw):
    with pytest.raises(attest.AttestationError) as e:
        attest.corroborate(source="NVSR 74-11, Table", year=2010,
                           measures="vibes", files=["us_annual_deaths.csv"],
                           raw_dir=raw)
    assert "unknown measure" in str(e.value)


def test_count_only_corroboration_is_distinguishable_from_count_and_rate(raw):
    """The 2023 case: a weaker claim must not read as a stronger one."""
    attest.corroborate(source="NVSR Vol. 74 No. 11, Table", year=2010,
                       measures="count", files=["us_annual_deaths.csv"],
                       raw_dir=raw, dry_run=False)
    attest.corroborate(source="NVSR Vol. 63 No. 3, Table B", year=2011,
                       measures="count,rate", files=["us_annual_deaths.csv"],
                       raw_dir=raw, dry_run=False)
    frame = _read(raw).set_index("year")
    assert frame.loc[2010, "corroborated_measures"] == "count"
    assert frame.loc[2011, "corroborated_measures"] == "count,rate"
