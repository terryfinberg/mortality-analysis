"""Record a human's attestation that values match their cited source.

**This module records a decision. It does not make one.** Nothing here inspects
a value, compares it to anything, or forms a view about whether it is right.
That is the whole point: attestation is a claim by a person, and a claim a
machine can generate is not an attestation, it is a formatting convention.

Kept out of :mod:`src.fetch` deliberately. ``fetch`` is the machine side --
retrieval, parsing, provenance, reconciliation -- and ``promote()`` there is
constructionally unable to write ``verified_by``. Putting the signing path in a
separate module keeps that separation legible: if signing were a flag on
``promote``, the distance between "fetched it" and "vouched for it" would be one
keystroke, which is exactly the collapse this repository exists to prevent.

**Never call this from an automated path.** Nothing imports it, and nothing
should. It is a CLI for a person who has just done the checking.

What signing means here
-----------------------
``verified_by`` asserts: *a person confirmed this value matches the source named
in ``source_citation``* -- which, since promotion, is the committed WONDER
export, identified by filename and content hash. It does not assert that an
independent publication agrees; that is ``corroborated_against``, a separate
claim recorded separately, and blank there means not corroborated rather than
failed.

Usage
-----
    python -m src.attest --name "Your Name"                  # dry run
    python -m src.attest --name "Your Name" --write
    python -m src.attest --name "Your Name" --file deaths_by_age.csv --write
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"

# The files that carry attestable values, and the value column(s) that must be
# populated before a row can be signed. Signing an empty cell would be
# attesting to nothing.
ATTESTABLE: dict[str, tuple[str, ...]] = {
    "deaths_by_age.csv": ("deaths", "population"),
    "us_annual_deaths.csv": ("deaths", "not_stated"),
    "us_population.csv": ("population",),
    "covid_deaths_by_age.csv": ("covid_deaths",),
}


class AttestationError(RuntimeError):
    """A row could not be signed, or the signature was not well formed."""


def _text(value: object) -> str:
    """A cell as trimmed text, with NaN read as blank.

    An empty CSV column arrives as float NaN, and ``nan or ""`` evaluates to
    NaN because NaN is truthy -- which silently turns an unsigned row into one
    signed by the string 'nan'.
    """
    return "" if pd.isna(value) else str(value).strip()


def attest(
    name: str,
    date: str | None = None,
    files: list[str] | None = None,
    raw_dir: Path | None = None,
    dry_run: bool = True,
) -> pd.DataFrame:
    """Write ``verified_by`` and ``verified_date`` for populated, cited rows.

    Refuses to sign a row with no value, or one with no ``source_citation`` --
    an attestation naming no source is not checkable and therefore not an
    attestation. Refuses to overwrite a different person's signature: theirs
    was a claim about what they checked, and it is not transferable.
    """
    if not name or not name.strip():
        raise AttestationError(
            "attest() needs the name of the person making the claim. A blank "
            "verified_by is what the loader is looking for the absence of."
        )
    name = name.strip()
    date = date or dt.date.today().isoformat()
    raw_dir = raw_dir or RAW_DIR
    targets = files or list(ATTESTABLE)

    signed: list[dict] = []
    for filename in targets:
        if filename not in ATTESTABLE:
            raise AttestationError(
                f"{filename!r} is not an attestable file. Known: "
                f"{sorted(ATTESTABLE)}"
            )
        path = raw_dir / filename
        frame = pd.read_csv(path)
        for col in ("verified_by", "verified_date"):
            if col not in frame.columns:
                frame[col] = ""
            frame[col] = frame[col].astype("object")

        value_cols = ATTESTABLE[filename]
        n = 0
        for i, row in frame.iterrows():
            missing = [c for c in value_cols if pd.isna(row.get(c))]
            if missing:
                continue  # nothing to attest to
            if not _text(row.get("source_citation")):
                raise AttestationError(
                    f"{filename} row {i}: no source_citation. An attestation "
                    f"that names no source cannot be checked by anyone."
                )
            existing = _text(row.get("verified_by"))
            if existing and existing != name:
                raise AttestationError(
                    f"{filename} row {i}: already signed by {existing!r}. "
                    f"Their signature is a claim about what they checked and "
                    f"does not transfer. Clear it deliberately if it is stale."
                )
            if existing == name:
                continue
            signed.append({"file": filename, "row": i,
                           "year": row.get("year"),
                           "age_group": row.get("age_group", "")})
            if not dry_run:
                frame.at[i, "verified_by"] = name
                frame.at[i, "verified_date"] = date
            n += 1

        if n and not dry_run:
            frame.to_csv(path, index=False)
        verb = "would sign" if dry_run else "signed"
        print(f"  {filename:26} {verb} {n:>3} row(s)")

    return pd.DataFrame(signed)


def corroborate(
    source: str,
    year: int,
    files: list[str],
    date: str | None = None,
    raw_dir: Path | None = None,
    dry_run: bool = True,
) -> pd.DataFrame:
    """Record that an independent publication reports the same figure.

    A different claim from :func:`attest`, and deliberately a separate call.
    Attestation says a value faithfully reproduces the export it came from;
    corroboration says a source outside this repository agrees with it. Only
    the second is external evidence, and it is available for some rows and not
    others -- so it is recorded per year, never in bulk across the file.

    ``source`` must name the publication precisely enough to be looked up: a
    volume and a table, not "NVSR". Blank stays blank and means **not
    corroborated**, never that corroboration was attempted and failed.
    """
    if not source or not source.strip():
        raise AttestationError(
            "corroborate() needs a source specific enough for a reader to "
            "find: a volume and table, not a series name."
        )
    source = source.strip()
    date = date or dt.date.today().isoformat()
    raw_dir = raw_dir or RAW_DIR

    written: list[dict] = []
    for filename in files:
        if filename not in ATTESTABLE:
            raise AttestationError(
                f"{filename!r} is not a known data file. Known: "
                f"{sorted(ATTESTABLE)}"
            )
        path = raw_dir / filename
        frame = pd.read_csv(path)
        for col in ("corroborated_against", "corroborated_date"):
            if col not in frame.columns:
                frame[col] = ""
            frame[col] = frame[col].astype("object")

        rows = frame.index[frame["year"] == year]
        if len(rows) == 0:
            raise AttestationError(f"{filename}: no rows for year {year}.")

        n = 0
        for i in rows:
            row = frame.loc[i]
            missing = [c for c in ATTESTABLE[filename] if pd.isna(row.get(c))]
            if missing:
                continue
            existing = _text(row.get("corroborated_against"))
            if existing and existing != source:
                raise AttestationError(
                    f"{filename} row {i} ({year}) is already corroborated "
                    f"against {existing!r}. Two independent sources agreeing "
                    f"is worth recording, but not by overwriting the first: "
                    f"decide which to keep, or widen the string deliberately."
                )
            if existing == source:
                continue
            written.append({"file": filename, "year": year,
                            "age_group": row.get("age_group", "")})
            if not dry_run:
                frame.at[i, "corroborated_against"] = source
                frame.at[i, "corroborated_date"] = date
            n += 1

        if n and not dry_run:
            frame.to_csv(path, index=False)
        verb = "would corroborate" if dry_run else "corroborated"
        print(f"  {filename:26} {year}  {verb} {n:>3} row(s)")

    return pd.DataFrame(written)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.attest",
        description=(
            "Record that a person confirmed these values match their cited "
            "source. Dry run by default."
        ),
    )
    parser.add_argument("--name", default=None,
                        help="the person making the attestation")
    parser.add_argument("--date", default=None, help="ISO date, default today")
    parser.add_argument("--file", action="append", dest="files",
                        help="limit to one file; repeatable")
    parser.add_argument("--write", action="store_true",
                        help="actually write (default is a dry run)")
    parser.add_argument("--corroborate", metavar="SOURCE", default=None,
                        help="record an independent source instead of signing; "
                             "needs --year and at least one --file")
    parser.add_argument("--year", type=int, default=None,
                        help="with --corroborate, the reference year")
    args = parser.parse_args(argv)

    if args.corroborate:
        if args.year is None or not args.files:
            parser.error("--corroborate needs --year and at least one --file")
        diff = corroborate(
            source=args.corroborate, year=args.year, files=args.files,
            date=args.date, dry_run=not args.write,
        )
        print()
        if args.write:
            print(
                f"Corroborated {len(diff)} row(s) for {args.year} against "
                f"{args.corroborate!r}. Every other year stays blank, which "
                f"means not corroborated -- not that it failed."
            )
        else:
            print(f"Dry run: {len(diff)} row(s). Re-run with --write.")
        return 0

    if not args.name:
        parser.error("--name is required when attesting")

    diff = attest(
        name=args.name, date=args.date, files=args.files,
        dry_run=not args.write,
    )
    print()
    if args.write:
        print(
            f"Signed {len(diff)} row(s) as {args.name!r}. Strict loading will "
            f"now succeed. corroborated_against is untouched and still blank: "
            f"that is a separate claim about an independent publication."
        )
    else:
        print(f"Dry run: {len(diff)} row(s) would be signed. Re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
