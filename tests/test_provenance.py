"""Integrity of the committed data inputs.

Every other test in this suite checks what the code computes. These check that
the bytes it computes *from* are the bytes that were recorded -- the WONDER
exports against the hashes in ``WONDER_EXPORTS``, the Census files against
``data/raw/census/PROVENANCE.md``.

Why this file exists
--------------------
The repository's argument is that a value nobody recomputes is a claim rather
than a check. That argument was applied to every number in the analysis and not
to the hashes describing the inputs, which sat in a document and a registry for
a human to compare by eye.

That gap produced a real defect: git's ``text=auto eol=lf`` rule normalised CRLF
inside a committed Census file, changing its bytes and breaking the recorded
hash on any platform whose checkout does not restore CRLF. It was caught by
reading a warning in passing. Nothing here could have failed, which means the
next one would have arrived silently. Now it fails.

Each check is proved to fire by mutating a single byte of a copy.
"""
import shutil

import pytest

from src import census, fetch


# ---------------------------------------------------------------------------
# WONDER exports, against the registry
# ---------------------------------------------------------------------------


def test_committed_exports_match_their_recorded_hashes():
    verified = fetch.verify_export_hashes()
    present = [
        s.filename for s in fetch.WONDER_EXPORTS
        if (fetch.WONDER_EXPORT_DIR / s.filename).exists()
    ]
    assert sorted(verified) == sorted(present)
    assert len(verified) == 4, "all four exports should be present and verified"


def test_every_present_export_has_a_recorded_hash():
    """Blank is honest for an unrun export, never for one on disk."""
    for spec in fetch.WONDER_EXPORTS:
        if (fetch.WONDER_EXPORT_DIR / spec.filename).exists():
            assert len(spec.sha256) == 64, (
                f"{spec.filename} is committed but has no sha256 in "
                f"WONDER_EXPORTS"
            )
            assert spec.sha256 == spec.sha256.lower()


def test_a_single_mutated_byte_fails_the_export_check(tmp_path):
    """Prove the check fires rather than trusting that it would."""
    export_dir = tmp_path / "wonder_exports"
    export_dir.mkdir()
    spec = fetch.SEAM_EXPORT
    source = fetch.WONDER_EXPORT_DIR / spec.filename
    target = export_dir / spec.filename
    shutil.copyfile(source, target)

    # Unmutated, the copy verifies.
    assert spec.filename in fetch.verify_export_hashes(export_dir)

    # Flip one byte in the middle of the data, leaving the length identical.
    data = bytearray(target.read_bytes())
    midpoint = len(data) // 2
    data[midpoint] = data[midpoint] ^ 0x01
    target.write_bytes(bytes(data))
    assert target.stat().st_size == source.stat().st_size

    with pytest.raises(fetch.IntegrityError) as excinfo:
        fetch.verify_export_hashes(export_dir)
    message = str(excinfo.value)
    assert spec.filename in message
    assert spec.sha256 in message, "the error must name the expected hash"
    assert "immutable history" in message


def test_an_export_with_no_recorded_hash_is_rejected(tmp_path, monkeypatch):
    from dataclasses import replace

    export_dir = tmp_path / "wonder_exports"
    export_dir.mkdir()
    spec = fetch.SEAM_EXPORT
    shutil.copyfile(
        fetch.WONDER_EXPORT_DIR / spec.filename, export_dir / spec.filename
    )
    monkeypatch.setattr(fetch, "WONDER_EXPORTS", (replace(spec, sha256=""),))

    with pytest.raises(fetch.IntegrityError) as excinfo:
        fetch.verify_export_hashes(export_dir)
    assert "no sha256 recorded" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Census files, against PROVENANCE.md
# ---------------------------------------------------------------------------


def test_committed_census_files_match_provenance():
    """Derived from the registry, so adding a vintage does not break this."""
    verified = census.verify_census_files()
    registered = sorted(s.filename for s in census.CENSUS_VINTAGES.values())
    assert sorted(verified) == registered
    assert len(verified) >= 2


def test_provenance_records_a_hash_for_every_registered_vintage():
    declared = census.recorded_hashes()
    for spec in census.CENSUS_VINTAGES.values():
        assert spec.filename in declared, (
            f"{spec.filename} is registered in CENSUS_VINTAGES but has no row "
            f"in PROVENANCE.md"
        )


def _census_copy(tmp_path):
    """A copy of the whole census input directory, whatever it holds."""
    census_dir = tmp_path / "census"
    census_dir.mkdir()
    for src in list(census.CENSUS_DIR.glob("*.csv")) + [
        census.CENSUS_DIR / census.PROVENANCE_FILE
    ]:
        shutil.copyfile(src, census_dir / src.name)
    return census_dir


def test_a_single_mutated_byte_fails_the_census_check(tmp_path):
    """The mutation is a digit swap inside a real population figure.

    Deliberately the most plausible corruption there is: same length, still
    valid CSV, still parses, still produces six believable band totals. Only
    the hash catches it.
    """
    census_dir = _census_copy(tmp_path)
    assert len(census.verify_census_files(census_dir)) == len(
        list(census.CENSUS_DIR.glob("*.csv"))
    )

    target = census_dir / "nc-est2024-agesex-res.csv"
    original = target.read_text(encoding="utf-8")
    mutated = original.replace("3615598", "3615599", 1)
    assert mutated != original, "the fixture value moved; pick another"
    target.write_text(mutated, encoding="utf-8", newline="")

    with pytest.raises(census.CensusError) as excinfo:
        census.verify_census_files(census_dir)
    message = str(excinfo.value)
    assert "nc-est2024-agesex-res.csv" in message
    assert "as the Census Bureau served" in message


def test_an_unrecorded_csv_in_the_input_directory_is_rejected(tmp_path):
    """A file nothing vouches for would be used as if it had been verified."""
    census_dir = _census_copy(tmp_path)
    (census_dir / "nc-est2026-agesex-res.csv").write_text(
        "SEX,AGE,POPESTIMATE2026\n0,999,1\n", encoding="utf-8"
    )

    with pytest.raises(census.CensusError) as excinfo:
        census.verify_census_files(census_dir)
    assert "no row in PROVENANCE.md" in str(excinfo.value)


def test_a_recorded_file_that_has_gone_missing_is_rejected(tmp_path):
    census_dir = _census_copy(tmp_path)
    (census_dir / "nc-est2025-agesex-res.csv").unlink()

    with pytest.raises(census.CensusError) as excinfo:
        census.verify_census_files(census_dir)
    assert "not in" in str(excinfo.value)


def test_an_unparseable_provenance_table_raises_rather_than_passing(tmp_path):
    """A format change must not silently turn this into a check of nothing."""
    census_dir = _census_copy(tmp_path)
    (census_dir / census.PROVENANCE_FILE).write_text(
        "# Census provenance\n\nNo table here any more.\n", encoding="utf-8"
    )

    with pytest.raises(census.CensusError) as excinfo:
        census.recorded_hashes(census_dir)
    assert "silently verifies nothing" in str(excinfo.value)
