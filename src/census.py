"""Census Bureau population vintages, for measuring denominator restatements.

Why this module exists
----------------------
WONDER carries each year at the vintage current when that year was first
estimated (see ``docs/denominator-methods.md``). To measure what a later vintage
did to an earlier year, the later vintage has to come from Census directly --
WONDER does not carry it, and will not until it refreshes.

That makes these files analysis inputs to a published finding, not a scratch
lookup, so they are committed under ``data/raw/census/`` exactly as the WONDER
exports are. A Census CSV carries no query footer the way a WONDER export does,
so the provenance that the footer would have supplied is recorded out of band in
``data/raw/census/PROVENANCE.md``: URL, access date and SHA-256 per file.

Discovery discipline
--------------------
Same rule as the WONDER work: **paths are discovered by listing, never guessed.**
The layout is genuinely counterintuitive and cost an hour once already --
national totals live under ``state/totals/``, and ``national/`` contains only
``asrh/``. ``2020-2025/national/totals/`` returns 404 while
``2020-2025/national/asrh/`` serves. The constants below record what listing
actually returned on the dates in PROVENANCE.md; :func:`vintage_index_url` exists
so the next person lists rather than guesses too.

Two file details are enforced here rather than described:

* ``AGE`` tops out at ``100``, which is a **100-and-over** code, not exactly 100.
  So the top band takes ``85 <= AGE <= 100``. Reading it as "exactly 100" would
  silently drop everyone older.
* ``AGE == 999`` is the all-ages total row. The single-year rows sum to it
  exactly, which is free arithmetic validation of any band collapse -- so
  :func:`collapse_to_bands` checks it and raises rather than trusting it.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .loader import AGE_GROUPS

ROOT = Path(__file__).resolve().parent.parent
CENSUS_DIR = ROOT / "data" / "raw" / "census"

# Discovered by listing, not guessed. See the module docstring.
CENSUS_BASE = "https://www2.census.gov/programs-surveys/popest/datasets"

# The all-ages total row, and the top-coded age. Both are properties of the
# file format, and both are checked rather than assumed.
TOTAL_AGE_CODE = 999
MAX_SINGLE_AGE = 100

# SEX == 0 is both sexes combined.
BOTH_SEXES = 0

# Not a POPESTIMATE year, but it is revised between vintages like everything
# else, which is evidence for the no-terminal-state argument in the docs.
ESTIMATES_BASE_COLUMN = "ESTIMATESBASE2020"

# Band edges for the six analysis groups, as single-year Census ages.
# The top band ends at MAX_SINGLE_AGE because 100 is "100 and over".
BAND_EDGES: tuple[tuple[str, int, int], ...] = (
    ("0-24", 0, 24),
    ("25-44", 25, 44),
    ("45-64", 45, 64),
    ("65-74", 65, 74),
    ("75-84", 75, 84),
    ("85+", 85, MAX_SINGLE_AGE),
)


class CensusError(RuntimeError):
    """A Census file was missing, malformed, or failed one of its identities."""


@dataclass(frozen=True)
class CensusVintage:
    """One Census population vintage, as published in a national asrh file."""

    vintage: int
    filename: str
    directory: str          # the listed directory, relative to CENSUS_BASE
    years: tuple[int, ...]  # reference years the file carries POPESTIMATE for

    @property
    def url(self) -> str:
        return f"{CENSUS_BASE}/{self.directory}/{self.filename}"

    @property
    def path(self) -> Path:
        return CENSUS_DIR / self.filename

    def column(self, year: int) -> str:
        """The POPESTIMATE column for a reference year, checked against years."""
        if year not in self.years:
            raise CensusError(
                f"Vintage {self.vintage} does not carry {year}. It carries "
                f"{self.years[0]}-{self.years[-1]}. A vintage cannot be asked "
                f"for a year it was published before."
            )
        return f"POPESTIMATE{year}"


# Both files were located by listing their directory, then downloaded. The
# `years` tuples are what the header actually contained, not what the vintage
# name implies -- a vintage carries every year from 2020 up to its own.
CENSUS_VINTAGES: dict[int, CensusVintage] = {
    # Carries CENSUS2010POP (the April 1 decennial count WONDER uses for 2010)
    # alongside POPESTIMATE2010 (the July 1 estimate). Both are needed to
    # measure the 2010 measurement-basis effect. Note the 2010-2019 vintage
    # directory has no agesex-res file at all -- only alldata-* -- so this is
    # where the July 1 2010 age detail actually lives. Found by listing.
    2020: CensusVintage(
        vintage=2020,
        filename="nc-est2020-agesex-res.csv",
        directory="2010-2020/national/asrh",
        years=tuple(range(2010, 2021)),
    ),
    2024: CensusVintage(
        vintage=2024,
        filename="nc-est2024-agesex-res.csv",
        directory="2020-2024/national/asrh",
        years=tuple(range(2020, 2025)),
    ),
    2025: CensusVintage(
        vintage=2025,
        filename="nc-est2025-agesex-res.csv",
        directory="2020-2025/national/asrh",
        years=tuple(range(2020, 2026)),
    ),
}


def vintage_index_url(vintage: int) -> str:
    """The directory to LIST when adding a vintage. Do not guess the filename.

    The layout has already cost an hour once. List this, read the filename out
    of the response, and add a :class:`CensusVintage` for it -- the same rule
    that governs dataset identifiers in :mod:`src.fetch`.
    """
    spec = CENSUS_VINTAGES.get(vintage)
    if spec is not None:
        return f"{CENSUS_BASE}/{spec.directory}/"
    return f"{CENSUS_BASE}/2020-{vintage}/national/asrh/"


def get_vintage(vintage: int) -> CensusVintage:
    if vintage not in CENSUS_VINTAGES:
        raise CensusError(
            f"No registered Census vintage {vintage}. List\n"
            f"    {vintage_index_url(vintage)}\n"
            f"read the filename out of the response, and add a CensusVintage "
            f"for it. Do not guess the path."
        )
    return CENSUS_VINTAGES[vintage]


def download_vintage(
    vintage: int, dest_dir: Path | None = None, session=None, timeout: int = 90
) -> Path:
    """Download one vintage file. Explicit only -- never called automatically.

    The committed files under ``data/raw/census/`` are the analysis inputs, so
    this exists to document and repeat how they were obtained, not as a step any
    analysis run performs. Nothing imports it.
    """
    spec = get_vintage(vintage)
    dest_dir = dest_dir or CENSUS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / spec.filename

    if session is None:
        import requests

        session = requests.Session()
    response = session.get(spec.url, timeout=timeout)
    response.raise_for_status()
    path.write_bytes(response.content)
    print(
        f"Downloaded {spec.url}\n  -> {path}\n"
        f"  Record the SHA-256 and access date in "
        f"{CENSUS_DIR / 'PROVENANCE.md'} -- a Census CSV carries no footer, so "
        f"that file is the only provenance it has."
    )
    return path


def load_vintage(vintage: int, census_dir: Path | None = None) -> pd.DataFrame:
    """Read one vintage's national age/sex file, both sexes, single-year ages.

    Returns the detail rows only (``AGE <= 100``); the ``AGE == 999`` total row
    is dropped here and used by :func:`collapse_to_bands` as a check.
    """
    spec = get_vintage(vintage)
    path = (census_dir / spec.filename) if census_dir else spec.path
    if not path.exists():
        raise CensusError(
            f"Census vintage {vintage} not found at {path}. It is a committed "
            f"analysis input; restore it from git rather than re-downloading, "
            f"or run download_vintage({vintage}) and update PROVENANCE.md."
        )

    frame = pd.read_csv(path)
    for col in ("SEX", "AGE"):
        if col not in frame.columns:
            raise CensusError(
                f"{path.name}: missing column {col!r}. Present: "
                f"{sorted(frame.columns)}. The Census file layout may have "
                f"changed; re-list the directory and check the schema."
            )
    return frame[(frame["SEX"] == BOTH_SEXES) & (frame["AGE"] <= MAX_SINGLE_AGE)]


def national_total_for(
    vintage: int, column: str, census_dir: Path | None = None
) -> int:
    """The ``AGE == 999`` all-ages total a vintage publishes in one column.

    Takes a column rather than a year so the ``ESTIMATESBASE2020`` column is
    reachable: it is not a ``POPESTIMATE`` year, but it does get revised between
    vintages, which is part of the point.
    """
    spec = get_vintage(vintage)
    path = (census_dir / spec.filename) if census_dir else spec.path
    frame = pd.read_csv(path)
    rows = frame[(frame["SEX"] == BOTH_SEXES) & (frame["AGE"] == TOTAL_AGE_CODE)]
    if len(rows) != 1:
        raise CensusError(
            f"{path.name}: expected exactly one SEX=0, AGE={TOTAL_AGE_CODE} "
            f"total row, found {len(rows)}."
        )
    if column not in rows.columns:
        raise CensusError(
            f"{path.name}: no column {column!r}. Present: "
            f"{sorted(c for c in rows.columns if c not in ('SEX', 'AGE'))}."
        )
    return int(rows.iloc[0][column])


def national_total(vintage: int, year: int, census_dir: Path | None = None) -> int:
    """The ``AGE == 999`` all-ages total a vintage publishes for a year."""
    return national_total_for(vintage, get_vintage(vintage).column(year), census_dir)


DECENNIAL_2010_COLUMN = "CENSUS2010POP"


def collapse_to_bands(
    vintage: int, year: int, census_dir: Path | None = None,
    column: str | None = None,
) -> pd.Series:
    """Single-year Census ages summed onto the six analysis bands.

    Enforces the two identities the file format gives for free:

    1. the single-year rows sum exactly to the ``AGE == 999`` total row, and
    2. the six bands sum exactly to that same total.

    Both are exact, so both are asserted as identities rather than checked with
    a tolerance -- the same reasoning as ``assert_population_identity`` in
    :mod:`src.fetch`. A band mapping that drops or double-counts an age is
    invisible in the six numbers and obvious against the total.
    """
    spec = get_vintage(vintage)
    # `column` overrides the POPESTIMATE lookup, for the columns that are not a
    # year's estimate -- CENSUS2010POP above all, which is what WONDER carries
    # for 2010 and therefore what any check against WONDER must use.
    column = column or spec.column(year)
    detail = load_vintage(vintage, census_dir)

    if column not in detail.columns:
        raise CensusError(
            f"{spec.filename}: no column {column!r}. Present: "
            f"{sorted(c for c in detail.columns if c not in ('SEX', 'AGE'))}."
        )

    published = national_total_for(vintage, column, census_dir)
    summed = int(detail[column].sum())
    if summed != published:
        raise CensusError(
            f"{spec.filename} {column}: single-year ages sum to {summed:,} but "
            f"the AGE={TOTAL_AGE_CODE} total row says {published:,} "
            f"(difference {summed - published:+,}). The age detail and the "
            f"published total disagree; do not compute bands from this."
        )

    bands = {
        name: int(detail[(detail["AGE"] >= lo) & (detail["AGE"] <= hi)][column].sum())
        for name, lo, hi in BAND_EDGES
    }
    if sum(bands.values()) != published:
        raise CensusError(
            f"{spec.filename} {column}: the six bands sum to "
            f"{sum(bands.values()):,} but the published total is "
            f"{published:,}. BAND_EDGES does not cover every age exactly once."
        )
    return pd.Series(bands).reindex(AGE_GROUPS)


def restatement(
    year: int, from_vintage: int, to_vintage: int, census_dir: Path | None = None
) -> pd.DataFrame:
    """What a later vintage did to one reference year, per band and in total."""
    a = collapse_to_bands(from_vintage, year, census_dir)
    b = collapse_to_bands(to_vintage, year, census_dir)
    frame = pd.DataFrame({
        "age_group": AGE_GROUPS,
        f"v{from_vintage}": [int(a[g]) for g in AGE_GROUPS],
        f"v{to_vintage}": [int(b[g]) for g in AGE_GROUPS],
    })
    frame["abs_change"] = frame[f"v{to_vintage}"] - frame[f"v{from_vintage}"]
    frame["pct_change"] = 100.0 * frame["abs_change"] / frame[f"v{from_vintage}"]
    return frame


def accessed_on() -> str:
    """Today, ISO. Used only when recording a fresh download."""
    return dt.date.today().isoformat()


# ---------------------------------------------------------------------------
# Integrity
# ---------------------------------------------------------------------------

PROVENANCE_FILE = "PROVENANCE.md"

# Matches a table row in PROVENANCE.md: | `file.csv` | `<64 hex>` | ...
_PROVENANCE_ROW = re.compile(
    r"^\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|", re.MULTILINE
)


def recorded_hashes(census_dir: Path | None = None) -> dict[str, str]:
    """The SHA-256 each file is declared to have, read out of PROVENANCE.md.

    A Census CSV carries no query footer the way a WONDER export does, so that
    document is the only provenance these files have. Parsing it here is what
    lets a test recompute the hashes rather than leaving them as numbers a human
    might compare.
    """
    census_dir = census_dir or CENSUS_DIR
    path = census_dir / PROVENANCE_FILE
    if not path.exists():
        raise CensusError(
            f"No {PROVENANCE_FILE} in {census_dir}. These files have no "
            f"embedded provenance, so without it there is nothing to verify "
            f"them against."
        )
    found = dict(_PROVENANCE_ROW.findall(path.read_text(encoding="utf-8")))
    if not found:
        raise CensusError(
            f"{path}: no file/hash rows parsed. The table must have rows of the "
            f"form | `name.csv` | `<64 hex digits>` | ... -- if the format "
            f"changed, this check silently verifies nothing, so it raises."
        )
    return found


def verify_census_files(census_dir: Path | None = None) -> dict[str, str]:
    """Recompute every committed Census file's hash against PROVENANCE.md.

    Checked both ways. A file with no recorded hash is as much a hole as a
    mismatch: it is a CSV in the input directory that nothing vouches for, and
    it would be used by the analysis exactly as if it had been verified.
    """
    from .fetch import file_sha256  # local: keeps import order one-directional

    census_dir = census_dir or CENSUS_DIR
    declared = recorded_hashes(census_dir)
    on_disk = sorted(p.name for p in census_dir.glob("*.csv"))

    unrecorded = [name for name in on_disk if name not in declared]
    if unrecorded:
        raise CensusError(
            f"CSV(s) in {census_dir} with no row in {PROVENANCE_FILE}: "
            + ", ".join(unrecorded)
            + ".\nAdd the file's URL, retrieval date and SHA-256 in the same "
            "commit that adds the file. An unrecorded CSV is indistinguishable "
            "from one somebody edited."
        )

    missing = [name for name in declared if name not in on_disk]
    if missing:
        raise CensusError(
            f"{PROVENANCE_FILE} records file(s) that are not in {census_dir}: "
            + ", ".join(sorted(missing))
            + ". Either restore them or remove the rows."
        )

    verified: dict[str, str] = {}
    mismatched: list[str] = []
    for name in on_disk:
        actual = file_sha256(census_dir / name)
        if actual != declared[name]:
            mismatched.append(
                f"  {name}\n"
                f"    {PROVENANCE_FILE}: {declared[name]}\n"
                f"    on disk:        {actual}"
            )
        else:
            verified[name] = actual

    if mismatched:
        raise CensusError(
            "Committed Census bytes do not match the recorded hash:\n"
            + "\n".join(mismatched)
            + f"\nThese hashes are of the files as the Census Bureau served "
            f"them, so a mismatch means the bytes moved after retrieval. Check "
            f"for a line-ending rule (.gitattributes marks this directory "
            f"-text for exactly that reason) before assuming the source "
            f"changed. Do not update {PROVENANCE_FILE} to match the new bytes "
            f"without establishing why they moved."
        )
    return verified
