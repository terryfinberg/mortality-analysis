"""Programmatic retrieval of the mortality inputs, replacing hand transcription.

Why this module exists
----------------------
Every value in ``data/raw/`` was, until now, meant to be typed in by a person
reading a published PDF. That is the analysis's weakest link: a transcription
error carries a citation and therefore looks verified. This module fetches the
same series over documented APIs so the provenance is a URL and an access date
rather than an act of typing.

It is built to avoid replacing one credibility problem with a worse one:

* **No identifier is hardcoded from memory.** ``SERIES`` below is empty until a
  human confirms identifiers that were read out of a live catalog response.
  Fetching an unconfirmed series raises :class:`UnconfirmedSeriesError`.
* **Nothing is written to ``data/raw/*.csv`` as a side effect.** Parsed output
  goes to ``data/raw/fetched/`` only. Copying into the raw CSVs is a separate,
  explicit, default-dry-run :func:`promote` step.
* **Partial results are never returned.** A parse failure logs the raw response
  body to ``data/raw/fetched/_debug/`` and raises.
* **Every response is cached** to ``data/raw/fetched/<series>_<date>.<ext>``
  before parsing, so a rerun on the same day is reproducible offline and the
  bytes the parse was based on remain on disk for audit.

Usage
-----
    python -m src.fetch --discover     # search the catalog, print candidates, stop
    python -m src.fetch --reconcile    # compare fetched vs. data/raw/*.csv
    python -m src.fetch --check        # as --reconcile, exit 1 on >0.5% drift
    python -m src.fetch --reconcile --refresh   # bypass today's cache
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from .loader import AGE_GROUPS

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
FETCH_DIR = RAW_DIR / "fetched"
DEBUG_DIR = FETCH_DIR / "_debug"
PROCESSED_DIR = ROOT / "data" / "processed"

CATALOG_URL = "https://data.cdc.gov/api/catalog/v1"
RESOURCE_URL = "https://data.cdc.gov/resource/{dataset_id}.json"

# CDC WONDER fallback, used only if Socrata cannot supply a series.
#
# Two properties of WONDER shape the client below, both documented at
# https://wonder.cdc.gov/wonder/help/WONDER-API.html:
#
#   1. The API refuses queries that would return sub-national (state, county)
#      detail on confidentiality grounds. National-level requests of the kind
#      this analysis needs are generally permitted, but the terms are checked
#      at request time rather than assumed.
#   2. The response schema has changed without announcement in the past. So a
#      parse failure here logs the raw XML and raises; it never degrades to a
#      partial frame.
WONDER_ENDPOINT = "https://wonder.cdc.gov/controller/datarequest/D{database}"

# Requests are attributed so CDC can identify the client if it misbehaves.
USER_AGENT = (
    "mortality-analysis/0.1 (research; +https://github.com/) "
    "python-requests"
)

DEFAULT_TIMEOUT = 60
SOCRATA_PAGE_LIMIT = 50_000

# Reconciliation tolerance for --check, in percent.
CHECK_TOLERANCE_PCT = 0.5

# Threshold above which unattributed-age deaths are called out, in percent.
NOT_STATED_WARN_PCT = 0.1


class FetchError(RuntimeError):
    """Base class for every failure raised by this module."""


class ParseError(FetchError):
    """A response could not be parsed into the expected shape.

    Always raised *after* the offending body has been written to
    ``data/raw/fetched/_debug/``. Never raised alongside a partial result.
    """


class UnconfirmedSeriesError(FetchError):
    """A series was requested whose dataset identifier is not yet confirmed.

    Guards the rule that no identifier may enter this file unless a human read
    it out of a live catalog response. See the note on ``SERIES``.
    """


# ---------------------------------------------------------------------------
# Age bands
# ---------------------------------------------------------------------------

# Collapse table transcribed from data/queries/cdc_wonder_queries.md, Query 1.
# Target group -> source bands to sum.
AGE_BAND_COLLAPSE: dict[str, tuple[str, ...]] = {
    "0-24": ("< 1 year", "1-4", "5-14", "15-24"),
    "25-44": ("25-34", "35-44"),
    "45-64": ("45-54", "55-64"),
    "65-74": ("65-74",),
    "75-84": ("75-84",),
    "85+": ("85+",),
}

# NCHS spells the same band several ways across databases and releases
# ("< 1 year", "<1 year", "Under 1 year", "85+ years", "85 years and over").
# Canonicalising to the collapse table's spelling keeps the table itself a
# faithful copy of the query doc while tolerating the wire format.
_BAND_ALIASES: dict[str, str] = {
    "<1year": "< 1 year",
    "under1year": "< 1 year",
    "under1": "< 1 year",
    "lessthan1year": "< 1 year",
    "1-4years": "1-4",
    "5-14years": "5-14",
    "15-24years": "15-24",
    "25-34years": "25-34",
    "35-44years": "35-44",
    "45-54years": "45-54",
    "55-64years": "55-64",
    "65-74years": "65-74",
    "75-84years": "75-84",
    "85+years": "85+",
    "85yearsandover": "85+",
    "85andover": "85+",
    "85plus": "85+",
}

# Sentinel for an age the certificate did not record.
NOT_STATED = "__not_stated__"

# Age values that mean "the certificate did not record an age". These are
# summed into a separate reported total, never dropped and never folded into
# a real age group.
_NOT_STATED_TOKENS = frozenset(
    {"notstated", "unknown", "unk", "missing", "notavailable", "na", "blank"}
)


def _norm_band(value: object) -> str:
    """Lowercase and strip a band label down to a comparable key."""
    return "".join(str(value).lower().split()).replace("_", "")


def canonical_band(value: object) -> str:
    """Map a wire-format age label onto the collapse table's spelling.

    Returns the canonical band name, the literal ``"__not_stated__"`` sentinel
    for unattributed ages, or raises for anything unrecognised. Unrecognised
    bands raise rather than being dropped: a band this module does not
    understand is deaths that would silently vanish from the totals.
    """
    key = _norm_band(value)
    if key in _NOT_STATED_TOKENS:
        return NOT_STATED
    if key in _BAND_ALIASES:
        return _BAND_ALIASES[key]
    for target, sources in AGE_BAND_COLLAPSE.items():
        for source in sources:
            if _norm_band(source) == key:
                return source
        if _norm_band(target) == key:
            # Already collapsed upstream.
            return target
    raise ParseError(
        f"Unrecognised age band {value!r}. Add it to AGE_BAND_COLLAPSE or "
        f"_BAND_ALIASES in src/fetch.py after confirming which target group it "
        f"belongs to. Refusing to guess, and refusing to drop the row."
    )


# Reverse index: source band -> target group.
_BAND_TO_TARGET: dict[str, str] = {
    source: target
    for target, sources in AGE_BAND_COLLAPSE.items()
    for source in sources
}


@dataclass
class CollapseResult:
    """Outcome of collapsing source age bands onto the analysis's six groups.

    ``frame`` carries only real age groups. ``not_stated`` carries the
    unattributed-age total per year, reported separately so it can be cited in
    the manuscript's limitations section rather than quietly absorbed.
    """

    frame: pd.DataFrame
    not_stated: pd.DataFrame
    warnings: list[str] = field(default_factory=list)

    def not_stated_pct(self) -> pd.DataFrame:
        """Unattributed share per year, as a percentage of all deaths."""
        return self.not_stated.copy()


def collapse_age_bands(
    df: pd.DataFrame,
    value_cols: Sequence[str],
    band_col: str = "age_band",
    year_col: str = "year",
    warn_pct: float = NOT_STATED_WARN_PCT,
) -> CollapseResult:
    """Sum source age bands into the six analysis groups.

    Rows whose age is "Not Stated" (or an equivalent) are summed into a
    separate per-year total rather than dropped or redistributed. If that total
    exceeds ``warn_pct`` of deaths in any year, a warning naming the year and
    the percentage is emitted and recorded on the result.

    Raises :class:`ParseError` for any band the collapse table does not cover.
    """
    for col in (band_col, year_col, *value_cols):
        if col not in df.columns:
            raise ParseError(
                f"collapse_age_bands: column {col!r} missing from frame with "
                f"columns {list(df.columns)}"
            )

    work = df.copy()
    work["_canonical"] = work[band_col].map(canonical_band)

    unattributed = work[work["_canonical"] == NOT_STATED]
    attributed = work[work["_canonical"] != NOT_STATED].copy()
    attributed["age_group"] = attributed["_canonical"].map(
        lambda b: _BAND_TO_TARGET.get(b, b)
    )

    value_cols = list(value_cols)
    frame = (
        attributed.groupby([year_col, "age_group"], as_index=False)[value_cols]
        .sum()
        .sort_values([year_col, "age_group"])
        .reset_index(drop=True)
    )

    # Every year present must end up with all six groups, or a band went
    # missing upstream and the totals are wrong in a way that is easy to miss.
    for year, group in frame.groupby(year_col):
        got = set(group["age_group"])
        if got != set(AGE_GROUPS):
            raise ParseError(
                f"Year {year}: collapsed to age groups {sorted(got)}, expected "
                f"{AGE_GROUPS}. Missing: {sorted(set(AGE_GROUPS) - got)}."
            )

    count_col = value_cols[0]
    if unattributed.empty:
        not_stated = pd.DataFrame(
            {year_col: pd.Series(dtype=frame[year_col].dtype),
             count_col: pd.Series(dtype="int64"),
             "pct_of_deaths": pd.Series(dtype="float64")}
        )
        return CollapseResult(frame=frame, not_stated=not_stated)

    ns = (
        unattributed.groupby(year_col, as_index=False)[[count_col]]
        .sum()
        .rename(columns={count_col: count_col})
    )
    attributed_totals = frame.groupby(year_col)[count_col].sum()
    ns["pct_of_deaths"] = ns.apply(
        lambda r: 100.0 * r[count_col]
        / (attributed_totals.get(r[year_col], 0) + r[count_col]),
        axis=1,
    )

    messages: list[str] = []
    for _, row in ns.iterrows():
        if row["pct_of_deaths"] > warn_pct:
            msg = (
                f"Age not stated for {int(row[count_col]):,} deaths in "
                f"{int(row[year_col])} ({row['pct_of_deaths']:.3f}% of deaths), "
                f"above the {warn_pct}% threshold. Note this in the "
                f"manuscript's limitations section."
            )
            messages.append(msg)
            warnings.warn(msg, stacklevel=2)

    return CollapseResult(frame=frame, not_stated=ns, warnings=messages)


# ---------------------------------------------------------------------------
# HTTP + cache
# ---------------------------------------------------------------------------


def _session():
    """Build a requests session. Imported lazily so tests never need requests."""
    import requests

    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return s


def _today() -> str:
    return dt.date.today().isoformat()


def cache_path(series: str, ext: str = "json", date: str | None = None) -> Path:
    return FETCH_DIR / f"{series}_{date or _today()}.{ext}"


def log_debug_body(series: str, body: str, suffix: str = "txt") -> Path:
    """Persist an unparseable response so the failure can be diagnosed."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    path = DEBUG_DIR / f"{series}_{stamp}.{suffix}"
    path.write_text(body, encoding="utf-8")
    return path


@dataclass
class FetchedPayload:
    """A raw response body plus where it came from and whether it was cached."""

    series: str
    body: str
    path: Path
    from_cache: bool
    url: str | None = None
    accessed: str = field(default_factory=_today)


def fetch_raw(
    series: str,
    url: str,
    params: dict[str, Any] | None = None,
    ext: str = "json",
    refresh: bool = False,
    session: Any = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> FetchedPayload:
    """Return the raw body for ``series``, from today's cache when possible.

    The body is written to ``data/raw/fetched/<series>_<date>.<ext>`` *before*
    any parsing, so the bytes a parse was based on always survive on disk. A
    rerun on the same date reads that file instead of re-hitting the API unless
    ``refresh`` is set.
    """
    path = cache_path(series, ext)
    if path.exists() and not refresh:
        return FetchedPayload(
            series=series,
            body=path.read_text(encoding="utf-8"),
            path=path,
            from_cache=True,
            url=url,
        )

    sess = session if session is not None else _session()
    response = sess.get(url, params=params or {}, timeout=timeout)
    response.raise_for_status()
    body = response.text

    FETCH_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return FetchedPayload(
        series=series, body=body, path=path, from_cache=False, url=url
    )


def parse_socrata_rows(
    payload: FetchedPayload, required: Sequence[str]
) -> pd.DataFrame:
    """Parse a Socrata JSON body into a frame, or raise having logged it.

    Refuses to return a frame missing any required column, because a silently
    absent column becomes a silently absent value downstream.
    """
    try:
        rows = json.loads(payload.body)
    except json.JSONDecodeError as exc:
        debug = log_debug_body(payload.series, payload.body, "json")
        raise ParseError(
            f"{payload.series}: response was not valid JSON ({exc}). "
            f"Raw body written to {debug}."
        ) from exc

    if not isinstance(rows, list):
        debug = log_debug_body(payload.series, payload.body, "json")
        raise ParseError(
            f"{payload.series}: expected a JSON array of rows, got "
            f"{type(rows).__name__}. Socrata returns an object for errors. "
            f"Raw body written to {debug}."
        )
    if not rows:
        debug = log_debug_body(payload.series, payload.body, "json")
        raise ParseError(
            f"{payload.series}: response contained zero rows. Treating an "
            f"empty extract as a failure rather than as 'no deaths'. "
            f"Raw body written to {debug}."
        )

    df = pd.DataFrame(rows)
    missing = [c for c in required if c not in df.columns]
    if missing:
        debug = log_debug_body(payload.series, payload.body, "json")
        raise ParseError(
            f"{payload.series}: response is missing required column(s) "
            f"{missing}. Present: {sorted(df.columns)}. The dataset schema may "
            f"have changed. Raw body written to {debug}."
        )
    return df


# ---------------------------------------------------------------------------
# WONDER export files -- the primary path
# ---------------------------------------------------------------------------
#
# WONDER is retrieved by hand and parsed from the saved export, not called over
# HTTP. That is a deliberate choice, not a workaround for the fact that the API
# is unreachable from some networks.
#
# The series is frozen history: final data for 2010-2023 will not change. A
# WONDER export carries its complete query parameters in the file footer, so
# the export file *is* the reproducibility artifact -- a reviewer replays the
# footer's query and gets the same file back. That is stronger provenance than
# an XML client pointed at an endpoint whose schema has changed without notice,
# and a TSV parser is far more testable than an XML client.
#
# Consequence enforced below: an export whose footer is missing is rejected. A
# bare table of numbers with no query parameters is not a citable artifact, and
# accepting one would quietly discard the whole reason for taking this route.

WONDER_EXPORT_DIR = RAW_DIR / "wonder_exports"

# Cells WONDER writes where a count is withheld or undefined. None of these may
# ever be coerced to zero: a suppressed cell is unknown, and zero is a claim.
_SUPPRESSION_TOKENS = frozenset(
    {"suppressed", "unreliable", "not applicable", "missing", "n/a", ""}
)


def file_sha256(path: Path) -> str:
    """Content hash of an export file. The cache key for the export path."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class WonderExport:
    """A parsed WONDER export plus the footer that makes it reproducible."""

    path: Path
    sha256: str
    frame: pd.DataFrame
    footer: str
    query_parameters: dict[str, str]

    @property
    def short_hash(self) -> str:
        return self.sha256[:12]

    def provenance(self) -> str:
        """The ``fetched_from`` value for rows promoted out of this export."""
        return f"wonder-export:{self.path.name}@sha256:{self.short_hash}"


def parse_wonder_export(path: Path) -> WonderExport:
    """Parse a saved WONDER TSV export. Raises rather than returning partial data.

    Rejects an export with no ``---`` footer, because the footer carries the
    query parameters that make the file citable.
    """
    path = Path(path)
    if not path.exists():
        raise FetchError(f"WONDER export not found: {path}")

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()

    footer_idx = None
    for i, line in enumerate(lines):
        if line.strip().strip('"') == "---":
            footer_idx = i
            break
    if footer_idx is None:
        debug = log_debug_body(path.stem, text, "txt")
        raise ParseError(
            f"{path.name}: no '---' footer found. A WONDER export without its "
            f"query-parameter footer is not a citable artifact -- it is just a "
            f"table of numbers. Re-export using 'Export' rather than copying "
            f"the results table. Raw body written to {debug}."
        )

    data_lines = [ln for ln in lines[:footer_idx] if ln.strip()]
    footer = "\n".join(lines[footer_idx:])
    if not data_lines:
        raise ParseError(f"{path.name}: footer found but no data rows above it.")

    reader = csv.reader(data_lines, delimiter="\t", quotechar='"')
    rows = list(reader)
    header = [h.strip().strip('"') for h in rows[0]]
    body = [r for r in rows[1:] if any(cell.strip() for cell in r)]
    frame = pd.DataFrame(
        [
            {
                header[i]: (cell.strip().strip('"') if i < len(header) else cell)
                for i, cell in enumerate(r[: len(header)])
            }
            for r in body
        ]
    )

    params: dict[str, str] = {}
    for line in footer.splitlines():
        clean = line.strip().strip('"').lstrip("# ").strip()
        m = re.match(r"^([A-Za-z][A-Za-z0-9 /_-]{2,60}):\s*(.*)$", clean)
        if m:
            params[m.group(1).strip()] = m.group(2).strip()

    return WonderExport(
        path=path,
        sha256=file_sha256(path),
        frame=frame,
        footer=footer,
        query_parameters=params,
    )


def _coerce_count(value: object, context: str) -> int:
    """Turn a WONDER cell into an int, or raise. Never silently yields zero."""
    text = str(value).strip().strip('"').replace(",", "")
    if text.lower() in _SUPPRESSION_TOKENS:
        raise ParseError(
            f"{context}: value is {value!r}. A suppressed or unavailable count "
            f"is unknown, not zero, and this analysis has no way to represent "
            f"unknown. Re-run the query at a coarser grouping where the cell is "
            f"not suppressed."
        )
    try:
        return int(float(text))
    except ValueError as exc:
        raise ParseError(f"{context}: could not read {value!r} as a count.") from exc


def _find_column(cols: Sequence[str], pattern: str) -> str | None:
    for c in cols:
        if c.strip().lower().endswith("code"):
            continue
        if re.search(pattern, c, re.I):
            return c
    return None


def wonder_export_totals(export: WonderExport) -> pd.DataFrame:
    """WONDER's own per-year Total rows: year, deaths, population, crude_rate.

    These are the figures WONDER itself published for this query, so they are
    an external check on our arithmetic rather than a restatement of it. The
    grand-total row (no year) is excluded.
    """
    cols = list(export.frame.columns)
    if "Notes" not in cols:
        raise ParseError(
            f"{export.path.name}: no Notes column, so per-year Total rows "
            f"cannot be identified. Re-export with 'Show Totals' enabled."
        )

    year_col = _find_column(cols, r"^year$")
    deaths_col = _find_column(cols, r"^deaths$")
    pop_col = _find_column(cols, r"^population$")
    rate_col = _find_column(cols, r"crude rate")
    if year_col is None or deaths_col is None:
        raise ParseError(f"{export.path.name}: Total rows lack Year or Deaths.")

    rows = export.frame[
        export.frame["Notes"].astype(str).str.strip().str.lower() == "total"
    ]
    out = []
    for _, r in rows.iterrows():
        year_text = str(r[year_col]).strip()
        if not year_text.isdigit():
            continue  # the grand total across all years
        entry = {
            "year": int(year_text),
            "deaths": _coerce_count(r[deaths_col], f"{export.path.name} total deaths"),
        }
        if pop_col is not None:
            entry["population"] = _coerce_count(
                r[pop_col], f"{export.path.name} total population"
            )
        if rate_col is not None:
            text = str(r[rate_col]).strip().strip('"').replace(",", "")
            entry["crude_rate"] = float(text) if text else float("nan")
        out.append(entry)

    if not out:
        raise ParseError(
            f"{export.path.name}: no per-year Total rows found. Re-export with "
            f"'Show Totals' enabled -- they are the external check on our "
            f"own arithmetic."
        )
    return pd.DataFrame(out).sort_values("year").reset_index(drop=True)


def wonder_export_to_grid(
    export: WonderExport, require_population: bool = True
) -> pd.DataFrame:
    """Reduce a parsed export to columns: year, age_band, deaths[, population].

    Drops WONDER's per-year "Total" rows from the band grid -- they are sums of
    rows already present, and keeping them would double every total.
    """
    cols = list(export.frame.columns)

    def find(pattern: str, exclude_code: bool = True) -> str | None:
        for c in cols:
            if exclude_code and c.strip().lower().endswith("code"):
                continue
            if re.search(pattern, c, re.I):
                return c
        return None

    year_col = find(r"^year$")
    age_col = find(r"age group")
    deaths_col = find(r"^deaths$")
    pop_col = find(r"^population$")

    missing = [
        name
        for name, col in [
            ("Year", year_col), ("Age Groups", age_col), ("Deaths", deaths_col)
        ]
        if col is None
    ]
    if require_population and pop_col is None:
        missing.append("Population")
    if missing:
        raise ParseError(
            f"{export.path.name}: export is missing column(s) {missing}. "
            f"Present: {cols}. Re-export with those fields selected under "
            f"'Show'."
        )

    work = export.frame
    if "Notes" in work.columns:
        work = work[~work["Notes"].astype(str).str.strip().str.lower().eq("total")]
    work = work[work[age_col].astype(str).str.strip() != ""]

    out = pd.DataFrame({
        "year": work[year_col].map(
            lambda v: _coerce_count(v, f"{export.path.name} year")
        ),
        "age_band": work[age_col].astype(str).str.strip(),
    })
    out["deaths"] = [
        _coerce_count(v, f"{export.path.name} deaths @ {b}")
        for v, b in zip(work[deaths_col], out["age_band"])
    ]
    if pop_col is not None:
        pops = []
        for value, band in zip(work[pop_col], out["age_band"]):
            token = str(value).strip().strip('"').lower()
            if canonical_band(band) == NOT_STATED and token in _SUPPRESSION_TOKENS:
                # WONDER gives no denominator for an unattributed age, which is
                # correct: there is no population of people whose age was not
                # recorded. Only this row's death count is ever used, and it is
                # reported separately by collapse_age_bands.
                pops.append(0)
            else:
                pops.append(
                    _coerce_count(value, f"{export.path.name} population @ {band}")
                )
        out["population"] = pops
    return out.reset_index(drop=True)


@dataclass
class ExportSpec:
    """One expected WONDER export file. See data/queries/cdc_wonder_queries.md."""

    filename: str
    series: str
    years: tuple[int, ...]
    database: str
    require_population: bool = True
    in_analysis_grid: bool = True

    # WONDER's Save button stores a query and returns a link that re-runs it.
    # That is better provenance than documented parameters, because a reviewer
    # clicks rather than reconstructs.
    #
    # It is a SUPPLEMENT, never a replacement. A saved query works only while
    # CDC keeps hosting it; the footer inside the export file works forever and
    # travels with the repository. Nothing in this module reads this field --
    # no parse, no cache key, no validation depends on it -- specifically so it
    # cannot quietly become load-bearing and tempt someone into dropping the
    # written parameters because the link looks sufficient.
    saved_query_url: str = ""


# Analysis grid: 2010-2017 from the bridged-race database, 2018-2024 from the
# single-race one. Non-overlapping, so no year is assembled from two databases.
# 2024 is final in the single-race database and carries population, so no
# provisional data enters the analysis at all.
#
# The SEAM export is deliberately NOT part of the grid. Its only job is to
# measure how much of the 2017/2018 discontinuity is an artifact of the change
# in race-bridging methodology rather than real mortality change. It overlaps
# the single-race export on 2018-2020, so the same years can be read under both
# population vintages and differenced. That seam sits inside the 2010-2019
# pre-pandemic baseline window, which means an unmeasured step there would bias
# the excess-mortality baseline fit without any visible symptom.
# saved_query_url is filled in by hand as each export is run. Blank is fine
# and always will be; see the note on the field.
WONDER_EXPORTS: tuple[ExportSpec, ...] = (
    ExportSpec("allcause_by_age_2010-2017_ucd-bridged.txt", "deaths_by_age",
               tuple(range(2010, 2018)),
               "Underlying Cause of Death, 1999-2020 (bridged-race)",
               saved_query_url=""),
    ExportSpec("allcause_by_age_2018-2024_ucd-singlerace.txt", "deaths_by_age",
               tuple(range(2018, 2025)),
               "Underlying Cause of Death, 2018-2024, Single Race",
               saved_query_url=""),
    ExportSpec("covid_u071_by_age_2020-2024_ucd-singlerace.txt", "covid_deaths_by_age",
               tuple(range(2020, 2025)),
               "Underlying Cause of Death, 2018-2024, Single Race",
               require_population=False,
               saved_query_url=""),
    ExportSpec("wonder_ucd_allcause_2018-2020_bridged_SEAM.txt", "seam_bridged",
               (2018, 2019, 2020),
               "Underlying Cause of Death, 1999-2020 (bridged-race)",
               in_analysis_grid=False,
               saved_query_url=""),
)

SEAM_EXPORT = WONDER_EXPORTS[-1]
GRID_EXPORTS = tuple(s for s in WONDER_EXPORTS if s.in_analysis_grid)


def missing_exports(export_dir: Path | None = None) -> list[ExportSpec]:
    """Which expected export files are not yet on disk."""
    export_dir = export_dir or WONDER_EXPORT_DIR
    return [s for s in WONDER_EXPORTS if not (export_dir / s.filename).exists()]


def export_cache_path(series: str, sha256: str, ext: str = "csv") -> Path:
    """Cache path for a parsed export, keyed on file content, not on a date.

    An export is immutable, so its hash is the honest cache key: the same file
    always resolves to the same parse, and a re-exported file with so much as a
    different footer timestamp gets a fresh entry.
    """
    return FETCH_DIR / f"{series}_{sha256[:12]}.{ext}"


def load_export_cached(
    series: str, path: Path, refresh: bool = False, require_population: bool = True
) -> tuple[pd.DataFrame, WonderExport, bool]:
    """Parse an export, or reuse the cached parse of that exact file.

    Returns ``(grid, export, from_cache)``.
    """
    path = Path(path)
    sha = file_sha256(path)
    cache = export_cache_path(series, sha)

    export = parse_wonder_export(path)
    if cache.exists() and not refresh:
        return pd.read_csv(cache), export, True

    grid = wonder_export_to_grid(export, require_population=require_population)
    FETCH_DIR.mkdir(parents=True, exist_ok=True)
    grid.to_csv(cache, index=False)
    (FETCH_DIR / f"{series}_{sha[:12]}.footer.txt").write_text(
        export.footer, encoding="utf-8"
    )
    return grid, export, False


# ---------------------------------------------------------------------------
# Catalog discovery
# ---------------------------------------------------------------------------

# Search terms per target series. Deliberately broad: the point of discovery is
# to surface candidates for a human to choose between, not to auto-select one.
DISCOVERY_QUERIES: dict[str, list[str]] = {
    "deaths_by_age": [
        "deaths by age group and year",
        "NCHS deaths population age group",
        "age-adjusted death rates United States",
    ],
    "annual_deaths": [
        "provisional death counts United States",
        "monthly provisional counts of deaths",
        "NCHS deaths final annual",
    ],
    "covid_deaths_by_age": [
        "provisional COVID-19 deaths by age",
        "COVID-19 deaths underlying cause age group",
        "deaths involving COVID-19 age",
    ],
}


@dataclass
class Candidate:
    """A catalog hit, carrying only fields read from the live response."""

    dataset_id: str
    name: str
    updated_at: str
    attribution: str
    description: str
    columns: list[tuple[str, str, str]]  # (field_name, display name, datatype)
    matched_query: str

    @property
    def landing_url(self) -> str:
        return f"https://data.cdc.gov/d/{self.dataset_id}"

    @property
    def api_url(self) -> str:
        return RESOURCE_URL.format(dataset_id=self.dataset_id)


def search_catalog(
    query: str, limit: int = 8, session: Any = None, timeout: int = DEFAULT_TIMEOUT
) -> list[Candidate]:
    """Query the CDC Socrata catalog and return candidates with their schemas.

    The catalog embeds each dataset's column schema in the search result, so no
    follow-up request per dataset is needed.
    """
    sess = session if session is not None else _session()
    response = sess.get(
        CATALOG_URL,
        params={
            "q": query,
            "only": "dataset",
            "limit": limit,
            "search_context": "data.cdc.gov",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    try:
        body = response.json()
    except ValueError as exc:
        debug = log_debug_body("catalog", response.text, "json")
        raise ParseError(
            f"Catalog search for {query!r} returned unparseable JSON. "
            f"Raw body written to {debug}."
        ) from exc

    out: list[Candidate] = []
    for item in body.get("results", []):
        resource = item.get("resource", {})
        field_names = resource.get("columns_field_name") or []
        display = resource.get("columns_name") or []
        datatypes = resource.get("columns_datatype") or []
        columns = [
            (
                field_names[i] if i < len(field_names) else "?",
                display[i] if i < len(display) else "?",
                datatypes[i] if i < len(datatypes) else "?",
            )
            for i in range(max(len(field_names), len(display), len(datatypes)))
        ]
        out.append(
            Candidate(
                dataset_id=resource.get("id", "?"),
                name=resource.get("name", "?"),
                updated_at=(resource.get("updatedAt") or "?")[:10],
                attribution=resource.get("attribution") or "?",
                description=" ".join(
                    (resource.get("description") or "").split()
                )[:300],
                columns=columns,
                matched_query=query,
            )
        )
    return out


def discover(session: Any = None, limit: int = 8) -> dict[str, list[Candidate]]:
    """Search the catalog for every target series. Returns candidates by series."""
    sess = session if session is not None else _session()
    found: dict[str, list[Candidate]] = {}
    for series, queries in DISCOVERY_QUERIES.items():
        seen: dict[str, Candidate] = {}
        for query in queries:
            for cand in search_catalog(query, limit=limit, session=sess):
                seen.setdefault(cand.dataset_id, cand)
        found[series] = list(seen.values())
    return found


def print_discovery(found: dict[str, list[Candidate]]) -> None:
    for series, candidates in found.items():
        print("=" * 78)
        print(f"SERIES: {series}   ({len(candidates)} candidates)")
        print("=" * 78)
        for cand in candidates:
            print(f"\n  id          {cand.dataset_id}")
            print(f"  title       {cand.name}")
            print(f"  updated     {cand.updated_at}")
            print(f"  attribution {cand.attribution}")
            print(f"  api         {cand.api_url}")
            if cand.description:
                print(f"  description {cand.description}")
            print(f"  columns ({len(cand.columns)}):")
            for fname, disp, dtype in cand.columns:
                print(f"      {fname:<38} {dtype:<12} {disp}")
        print()


# ---------------------------------------------------------------------------
# Series registry
# ---------------------------------------------------------------------------


@dataclass
class SeriesSpec:
    """A confirmed data source for one target series.

    ``dataset_id`` must be an identifier a human read out of a live
    ``--discover`` response and approved. Nothing in this file may populate it
    from recollection.
    """

    name: str
    dataset_id: str
    target_csv: str
    value_cols: tuple[str, ...]
    select: dict[str, str]
    confirmed_on: str
    notes: str = ""


# EMPTY BY DESIGN.
#
# Populating this dict is a human decision made against the output of
# `python -m src.fetch --discover`. It is left empty rather than pre-filled
# with plausible-looking identifiers, because an identifier that is wrong but
# well-formed produces a clean run against the wrong data, which is precisely
# the failure mode this whole module exists to remove.
SERIES: dict[str, SeriesSpec] = {}


def get_series(name: str) -> SeriesSpec:
    if name not in SERIES:
        raise UnconfirmedSeriesError(
            f"Series {name!r} has no confirmed dataset identifier. Run\n"
            f"    python -m src.fetch --discover\n"
            f"and add the approved identifier to SERIES in src/fetch.py. "
            f"Do not fill it in from memory."
        )
    return SERIES[name]


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

# Which raw CSV each series reconciles against, and on what keys.
RAW_TARGETS: dict[str, dict[str, Any]] = {
    "deaths_by_age": {
        "csv": "deaths_by_age.csv",
        "keys": ["year", "age_group"],
        "values": ["deaths", "population"],
    },
    "annual_deaths": {
        "csv": "us_annual_deaths.csv",
        "keys": ["year"],
        "values": ["deaths", "not_stated"],
    },
    "population": {
        "csv": "us_population.csv",
        "keys": ["year"],
        "values": ["population"],
    },
    "covid_deaths_by_age": {
        "csv": "covid_deaths_by_age.csv",
        "keys": ["year", "age_group"],
        "values": ["covid_deaths"],
    },
}


def reconcile_series(
    series: str, fetched: pd.DataFrame | None, raw_dir: Path | None = None
) -> pd.DataFrame:
    """Compare a fetched frame against the corresponding raw CSV, cell by cell.

    Returns one row per (key, value column) with the current value, the fetched
    value, and both differences. A blank cell in the raw CSV is reported as
    ``unpopulated`` rather than as a zero-to-N difference, because the CSVs ship
    empty and calling that a 100% discrepancy would bury real drift in noise.
    """
    spec = RAW_TARGETS[series]
    raw_dir = raw_dir or RAW_DIR
    current = pd.read_csv(raw_dir / spec["csv"])
    keys: list[str] = spec["keys"]
    values: list[str] = spec["values"]

    rows: list[dict[str, Any]] = []
    indexed = None
    if fetched is not None and not fetched.empty:
        indexed = fetched.set_index(keys)

    for _, row in current.iterrows():
        key = tuple(row[k] for k in keys)
        for col in values:
            cur = row.get(col)
            cur_missing = pd.isna(cur)

            new = None
            if indexed is not None and col in indexed.columns:
                lookup = key[0] if len(key) == 1 else key
                if lookup in indexed.index:
                    new = indexed.loc[lookup, col]

            entry: dict[str, Any] = {
                "series": series,
                **{k: row[k] for k in keys},
                "column": col,
                "current_value": "unpopulated" if cur_missing else cur,
                "fetched_value": "not fetched" if new is None else new,
                "abs_diff": None,
                "pct_diff": None,
                "status": "",
            }

            if new is None:
                entry["status"] = (
                    "unpopulated / not fetched" if cur_missing else "not fetched"
                )
            elif cur_missing:
                entry["status"] = "unpopulated"
            else:
                abs_diff = float(new) - float(cur)
                entry["abs_diff"] = abs_diff
                entry["pct_diff"] = (
                    100.0 * abs_diff / float(cur) if float(cur) != 0 else float("inf")
                )
                entry["status"] = (
                    "match" if abs(entry["pct_diff"]) <= 1e-9 else "differs"
                )
            rows.append(entry)

    return pd.DataFrame(rows)


def reconcile_all(
    fetched: dict[str, pd.DataFrame] | None = None, raw_dir: Path | None = None
) -> pd.DataFrame:
    fetched = fetched or {}
    frames = [
        reconcile_series(series, fetched.get(series), raw_dir=raw_dir)
        for series in RAW_TARGETS
    ]
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Vintage seam
# ---------------------------------------------------------------------------
#
# The analysis grid changes population vintage at 2017/2018: bridged-race
# estimates before, single-race after. Deaths are the same certificates either
# way, so a deaths delta between the two vintages should be ~0 and anything
# larger means the two exports are not actually the same query. Population is
# where a real difference lives, and it propagates straight into every
# age-specific rate.
#
# This matters because the seam sits inside the 2010-2019 pre-pandemic baseline
# window. A step in the population series puts a step in the baseline trend fit,
# which shifts every excess-mortality estimate that fit produces -- silently,
# because a fitted line through stepped data still looks like a line.

# Above this, the seam is called material and belongs in the methods section.
# A convention matched to the --check tolerance, not a statistical test.
SEAM_MATERIAL_PCT = 0.5

# Deaths should barely move between vintages. If they move more than this, the
# two exports differ in something other than race bridging.
SEAM_DEATHS_SUSPICIOUS_PCT = 0.1


def seam_comparison(
    bridged: pd.DataFrame, single_race: pd.DataFrame
) -> pd.DataFrame:
    """Per-year, per-band deltas between the two population vintages.

    Both frames are collapsed six-band grids with columns year, age_group,
    deaths and population. Compared on their overlapping years only.
    """
    keys = ["year", "age_group"]
    merged = bridged.merge(
        single_race, on=keys, suffixes=("_bridged", "_single"), how="inner"
    )
    if merged.empty:
        raise FetchError(
            "Seam comparison found no overlapping year/age cells. The seam "
            "export must cover years that the single-race export also covers, "
            "or it measures nothing."
        )

    for measure in ("deaths", "population"):
        b, s = f"{measure}_bridged", f"{measure}_single"
        if b not in merged.columns or s not in merged.columns:
            continue
        merged[f"{measure}_abs_diff"] = merged[s] - merged[b]
        merged[f"{measure}_pct_diff"] = 100.0 * merged[f"{measure}_abs_diff"] / merged[b]

    return merged.sort_values(keys).reset_index(drop=True)


def seam_verdict(seam: pd.DataFrame) -> dict[str, Any]:
    """Summarise whether the seam is material enough to disclose."""
    pop = seam["population_pct_diff"].abs() if "population_pct_diff" in seam else None
    deaths = seam["deaths_pct_diff"].abs() if "deaths_pct_diff" in seam else None

    worst_pop = float(pop.max()) if pop is not None and len(pop) else 0.0
    worst_deaths = float(deaths.max()) if deaths is not None and len(deaths) else 0.0

    material = worst_pop > SEAM_MATERIAL_PCT
    suspicious = worst_deaths > SEAM_DEATHS_SUSPICIOUS_PCT

    row = None
    if pop is not None and len(pop):
        row = seam.loc[pop.idxmax()]

    return {
        "worst_population_pct": worst_pop,
        "worst_deaths_pct": worst_deaths,
        "material": material,
        "deaths_suspicious": suspicious,
        "worst_cell": None if row is None else f"{int(row['year'])} {row['age_group']}",
    }


@dataclass
class LoadedExport:
    """One export, collapsed to the six bands, plus WONDER's own Total rows."""

    spec: ExportSpec
    collapsed: CollapseResult
    totals: pd.DataFrame
    export: WonderExport


def load_export_bundle(
    spec: ExportSpec, export_dir: Path | None = None, refresh: bool = False
) -> LoadedExport | None:
    """Parse and collapse one export, keeping WONDER's published totals."""
    export_dir = export_dir or WONDER_EXPORT_DIR
    path = export_dir / spec.filename
    if not path.exists():
        return None
    grid, export, _cached = load_export_cached(
        spec.series, path, refresh=refresh, require_population=spec.require_population
    )
    value_cols = ["deaths"] + (["population"] if spec.require_population else [])
    return LoadedExport(
        spec=spec,
        collapsed=collapse_age_bands(grid, value_cols),
        totals=wonder_export_totals(export),
        export=export,
    )


def load_grid_for(
    spec: ExportSpec, export_dir: Path | None = None, refresh: bool = False
) -> CollapseResult | None:
    """Parse one export and collapse it to the six bands. None if absent.

    Returns the whole CollapseResult, not just the frame, because the
    Not Stated total is needed to reconstruct the published annual figure.
    """
    bundle = load_export_bundle(spec, export_dir, refresh)
    return None if bundle is None else bundle.collapsed


def derive_annual_deaths(results: Sequence[CollapseResult]) -> pd.DataFrame:
    """Annual total deaths on the NVSR definition, with Not Stated made explicit.

    WONDER does not distribute Not Stated deaths among age groups, so the sum
    of the six bands falls short of the published annual total by exactly the
    Not Stated count -- around 130 deaths a year, roughly 0.005%. The published
    figure, which is what a reviewer checks, includes them.

    A percentage tolerance cannot police this: 0.005% sits far inside any
    sensible drift threshold, so a systematic shortfall would reconcile clean
    forever. The relationship is exact, so it is asserted as an identity:

        deaths == sum(six age bands) + not_stated

    ``not_stated`` is returned as its own column so the identity is auditable
    in the CSV rather than implied by a number that happens to add up.
    """
    frames = []
    for result in results:
        banded = result.frame.groupby("year", as_index=False)["deaths"].sum()
        ns = result.not_stated
        if ns is not None and not ns.empty:
            banded = banded.merge(
                ns[["year", "deaths"]].rename(columns={"deaths": "not_stated"}),
                on="year", how="left",
            )
        else:
            banded["not_stated"] = 0
        banded["not_stated"] = banded["not_stated"].fillna(0).astype(int)
        banded["deaths"] = banded["deaths"] + banded["not_stated"]
        frames.append(banded)

    if not frames:
        return pd.DataFrame(columns=["year", "deaths", "not_stated"])
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values("year").reset_index(drop=True)[
        ["year", "deaths", "not_stated"]
    ]


def derive_population(results: Sequence[CollapseResult]) -> pd.DataFrame:
    """Resident population by year, summed from the six age bands.

    July 1 resident population estimates, except 2010, which is the April 1
    decennial count as carried by WONDER. Verified band by band against Census
    CENSUS2010POP: WONDER's 2010 figures are the decennial counts exactly, not
    July 1 estimates, so "mid-year" is wrong for that one year.

    Sourced from the WONDER export rather than fetched from Census separately,
    which makes sum(bands) == annual population an exact identity instead of a
    cross-source comparison needing a tolerance.

    The deciding reason is external validation, not tidiness. WONDER publishes
    a Crude Rate column. If our denominator is WONDER's denominator, then our
    computed crude rate must reproduce WONDER's published rate for every year,
    which checks the whole rate pipeline against an outside authority for free.
    With a Census denominator it would not match, and the discrepancy would
    have to be explained while buying nothing.

    WONDER's population figures are themselves NCHS-processed Census estimates,
    so this is a choice of vintage, not a change of underlying source.
    """
    frames = [r.frame.groupby("year", as_index=False)["population"].sum()
              for r in results if "population" in r.frame.columns]
    if not frames:
        return pd.DataFrame(columns=["year", "population"])
    return pd.concat(frames, ignore_index=True).sort_values("year").reset_index(drop=True)


def assert_population_identity(population: pd.DataFrame, by_age: pd.DataFrame) -> None:
    """sum(age bands) == annual population, exactly. No tolerance.

    Exact because both sides come from the same export. Were the denominator
    taken from Census instead, this could only ever be a tolerance.
    """
    banded = by_age.groupby("year")["population"].sum()
    for _, row in population.iterrows():
        year = row["year"]
        expected = int(banded.get(year, 0))
        if int(row["population"]) != expected:
            raise FetchError(
                f"Population identity violated for {year}: bands sum to "
                f"{expected:,} but annual population is {int(row['population']):,}."
            )


# WONDER prints its Crude Rate to one decimal, so that is the precision at
# which our own computation has to reproduce it.
CRUDE_RATE_DECIMALS = 1


def crude_rate_check(
    annual: pd.DataFrame, population: pd.DataFrame, totals: pd.DataFrame
) -> pd.DataFrame:
    """Compare our computed crude rate against WONDER's published column.

    An end-to-end check of deaths, population and the rate arithmetic against
    an external authority: WONDER computed its rate independently of us, from
    the same underlying counts.
    """
    merged = (
        annual[["year", "deaths"]]
        .merge(population[["year", "population"]], on="year")
        .merge(totals[["year", "crude_rate"]], on="year", how="left")
        .rename(columns={"crude_rate": "wonder_crude_rate"})
    )
    merged["computed_crude_rate"] = (
        merged["deaths"] / merged["population"] * 100_000
    ).round(CRUDE_RATE_DECIMALS)
    merged["matches"] = (
        merged["computed_crude_rate"] - merged["wonder_crude_rate"]
    ).abs() < 10 ** -CRUDE_RATE_DECIMALS / 2
    return merged


def assert_crude_rate_matches_wonder(check: pd.DataFrame) -> None:
    bad = check[~check["matches"] & check["wonder_crude_rate"].notna()]
    if not bad.empty:
        rows = "\n".join(
            f"  {int(r['year'])}: computed {r['computed_crude_rate']}, "
            f"WONDER published {r['wonder_crude_rate']}"
            for _, r in bad.iterrows()
        )
        raise FetchError(
            f"Computed crude rate disagrees with WONDER's published Crude Rate "
            f"in {len(bad)} year(s):\n{rows}\n"
            f"Deaths, population and the rate arithmetic all feed this, so the "
            f"defect is in one of the three."
        )


def load_analysis_grids(
    export_dir: Path | None = None, refresh: bool = False
) -> dict[str, pd.DataFrame]:
    """Collapse every present grid export, concatenated per series.

    Absent exports are skipped rather than faked, so a partially exported
    repository reconciles the years it has and reports the rest as not fetched.
    """
    export_dir = export_dir or WONDER_EXPORT_DIR
    grids: dict[str, list[CollapseResult]] = {}
    totals: list[pd.DataFrame] = []
    for spec in GRID_EXPORTS:
        bundle = load_export_bundle(spec, export_dir, refresh)
        if bundle is None:
            continue
        grids.setdefault(spec.series, []).append(bundle.collapsed)
        if spec.series == "deaths_by_age":
            totals.append(bundle.totals)

    out: dict[str, pd.DataFrame] = {}
    for series, results in grids.items():
        combined = pd.concat([r.frame for r in results], ignore_index=True)
        dupes = combined.duplicated(subset=["year", "age_group"])
        if dupes.any():
            years = sorted(combined.loc[dupes, "year"].unique())
            raise FetchError(
                f"{series}: exports overlap on year(s) {years}. The grid "
                f"boundaries are meant to be non-overlapping, so a year would "
                f"be assembled from two databases."
            )
        out[series] = combined.sort_values(["year", "age_group"]).reset_index(drop=True)

    # The annual total is derived from the same exports rather than fetched
    # separately, so the identity below cannot drift apart from its own inputs.
    if "deaths_by_age" in grids:
        out["annual_deaths"] = derive_annual_deaths(grids["deaths_by_age"])
        assert_annual_identity(out["annual_deaths"], out["deaths_by_age"])

        out["population"] = derive_population(grids["deaths_by_age"])
        assert_population_identity(out["population"], out["deaths_by_age"])

        # External check: our rate arithmetic against WONDER's published one.
        if totals:
            check = crude_rate_check(
                out["annual_deaths"],
                out["population"],
                pd.concat(totals, ignore_index=True),
            )
            assert_crude_rate_matches_wonder(check)
            out["_crude_rate_check"] = check
    return out


def assert_annual_identity(annual: pd.DataFrame, by_age: pd.DataFrame) -> None:
    """sum(age bands) + not_stated == annual total, exactly. No tolerance.

    An exact relationship checked with a percentage tolerance absorbs
    systematic bias: the Not Stated shortfall is 0.005% and would pass any
    drift threshold indefinitely while being wrong every single year.
    """
    banded = by_age.groupby("year")["deaths"].sum()
    for _, row in annual.iterrows():
        year = row["year"]
        expected = int(banded.get(year, 0)) + int(row["not_stated"])
        if int(row["deaths"]) != expected:
            raise FetchError(
                f"Annual identity violated for {year}: "
                f"bands({int(banded.get(year, 0)):,}) + "
                f"not_stated({int(row['not_stated']):,}) = {expected:,}, "
                f"but annual deaths is {int(row['deaths']):,}."
            )


def load_seam(
    export_dir: Path | None = None, refresh: bool = False
) -> pd.DataFrame | None:
    """Bridged vs single-race comparison. None if either export is absent."""
    export_dir = export_dir or WONDER_EXPORT_DIR
    single_spec = next(
        s for s in GRID_EXPORTS
        if s.series == "deaths_by_age" and 2018 in s.years
    )
    bridged = load_grid_for(SEAM_EXPORT, export_dir, refresh)
    single = load_grid_for(single_spec, export_dir, refresh)
    if bridged is None or single is None:
        return None
    return seam_comparison(bridged.frame, single.frame)


def render_seam_section(seam: pd.DataFrame | None) -> list[str]:
    lines = ["## Vintage seam (bridged-race vs single-race)", ""]
    if seam is None or seam.empty:
        lines += [
            "Seam export not present, so the 2017/2018 vintage discontinuity is "
            f"**unmeasured**. Export `{SEAM_EXPORT.filename}` to measure it. "
            "The analysis grid changes population vintage at 2017/2018 and that "
            "seam sits inside the 2010-2019 baseline window, so leaving this "
            "unmeasured means the baseline trend fit may contain a step that "
            "nothing in the pipeline will reveal.",
            "",
        ]
        return lines

    verdict = seam_verdict(seam)
    lines += [
        "Same years read under both population vintages. Deaths are the same "
        "certificates either way, so only population is expected to move.",
        "",
        f"- Largest population difference: **{verdict['worst_population_pct']:.3f}%** "
        f"({verdict['worst_cell']})",
        f"- Largest deaths difference: **{verdict['worst_deaths_pct']:.3f}%**",
        "",
    ]

    if verdict["deaths_suspicious"]:
        lines += [
            f"> **Deaths differ by more than {SEAM_DEATHS_SUSPICIOUS_PCT}%.** The "
            "two exports should contain the same death certificates. A "
            "difference this large means they are not the same query -- check "
            "the year range, cause selection and location on both before "
            "reading anything else here.",
            "",
        ]

    if verdict["material"]:
        lines += [
            f"> **Material.** Population differs by more than "
            f"{SEAM_MATERIAL_PCT}% in at least one band. The 2017/2018 boundary "
            "puts a step in the population series inside the pre-pandemic "
            "baseline window, so the baseline trend fit has a step in it. State "
            "this in methods and report how much the excess-mortality headline "
            "moves when the baseline is fit on single-race years only.",
            "",
        ]
    else:
        lines += [
            f"> Not material at the {SEAM_MATERIAL_PCT}% convention. Worth one "
            "sentence in methods recording that it was measured and bounded, "
            "rather than silence.",
            "",
        ]

    header = ["year", "age group", "deaths bridged", "deaths single", "deaths %",
              "pop bridged", "pop single", "pop abs diff", "pop %"]
    lines += ["| " + " | ".join(header) + " |",
              "|" + "|".join(["---"] * len(header)) + "|"]
    for _, r in seam.iterrows():
        lines.append("| " + " | ".join([
            str(int(r["year"])),
            str(r["age_group"]),
            f"{r.get('deaths_bridged', float('nan')):,.0f}",
            f"{r.get('deaths_single', float('nan')):,.0f}",
            f"{r.get('deaths_pct_diff', float('nan')):.3f}%",
            f"{r.get('population_bridged', float('nan')):,.0f}",
            f"{r.get('population_single', float('nan')):,.0f}",
            f"{r.get('population_abs_diff', float('nan')):,.0f}",
            f"{r.get('population_pct_diff', float('nan')):.3f}%",
        ]) + " |")
    lines += [""]
    return lines


def render_crude_rate_section(check: pd.DataFrame | None) -> list[str]:
    """Our computed crude rate against WONDER's published Crude Rate column."""
    lines = ["## Crude rate check against WONDER", ""]
    if check is None or check.empty:
        lines += [
            "No exports present, so the rate pipeline has not been checked "
            "against WONDER's published Crude Rate column.",
            "",
        ]
        return lines

    n_ok = int(check["matches"].sum())
    lines += [
        "WONDER publishes a Crude Rate for each year. Because the denominator "
        "here is WONDER's own population, our computed rate must reproduce it "
        f"to {CRUDE_RATE_DECIMALS} decimal place. This checks deaths, "
        "population and the rate arithmetic end to end against an external "
        "authority, not against ourselves.",
        "",
        f"- **{n_ok} of {len(check)} year(s) match.**",
        "",
        "| year | deaths | population | computed | WONDER | match |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in check.iterrows():
        lines.append(
            f"| {int(r['year'])} | {int(r['deaths']):,} | "
            f"{int(r['population']):,} | {r['computed_crude_rate']} | "
            f"{r['wonder_crude_rate']} | {'yes' if r['matches'] else '**NO**'} |"
        )
    lines += [""]
    return lines


def render_report(
    report: pd.DataFrame,
    accessed: str | None = None,
    seam: pd.DataFrame | None = None,
    crude_check: pd.DataFrame | None = None,
) -> str:
    """Render the reconciliation table as Markdown."""
    accessed = accessed or _today()
    lines = [
        f"# Reconciliation report {accessed}",
        "",
        "Generated by `python -m src.fetch --reconcile`. Compares the values "
        "currently in `data/raw/*.csv` against values parsed from the CDC "
        "WONDER exports in `data/raw/wonder_exports/`. Nothing in this report "
        "has been written into the raw CSVs; promotion is a separate explicit "
        "step, and it does not fill in `verified_by`.",
        "",
    ]

    counts = report["status"].value_counts().to_dict()
    lines += ["## Summary", ""]
    lines += [f"- **{status}**: {n} cell(s)" for status, n in sorted(counts.items())]
    lines += [""]

    absent = missing_exports()
    if absent:
        lines += [
            "> **Not all exports are present.** Cells shown as `not fetched` "
            "have no source yet, not a source that disagrees. Missing: "
            + ", ".join(f"`{s.filename}`" for s in absent)
            + ".",
            "",
        ]

    for series, group in report.groupby("series", sort=False):
        lines += [f"## {series}", ""]
        has_age = "age_group" in group.columns and group["age_group"].notna().any()
        header = ["year"] + (["age_group"] if has_age else []) + [
            "column", "current", "fetched", "abs diff", "pct diff", "status"
        ]
        lines += ["| " + " | ".join(header) + " |",
                  "|" + "|".join(["---"] * len(header)) + "|"]
        for _, row in group.iterrows():
            cells = [str(row["year"])]
            if has_age:
                cells.append(str(row.get("age_group", "")))
            cells += [
                str(row["column"]),
                str(row["current_value"]),
                str(row["fetched_value"]),
                "" if row["abs_diff"] is None else f"{row['abs_diff']:,.2f}",
                "" if row["pct_diff"] is None else f"{row['pct_diff']:.4f}%",
                str(row["status"]),
            ]
            lines.append("| " + " | ".join(cells) + " |")
        lines += [""]

    lines += render_crude_rate_section(crude_check)
    lines += render_seam_section(seam)

    return "\n".join(lines)


def write_report(
    report: pd.DataFrame,
    accessed: str | None = None,
    seam: pd.DataFrame | None = None,
    crude_check: pd.DataFrame | None = None,
) -> Path:
    accessed = accessed or _today()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / f"reconciliation_{accessed}.md"
    path.write_text(
        render_report(report, accessed, seam=seam, crude_check=crude_check),
        encoding="utf-8",
    )
    return path


def check_drift(report: pd.DataFrame, tolerance: float = CHECK_TOLERANCE_PCT):
    """Return rows where a populated cell drifts beyond ``tolerance`` percent."""
    comparable = report[report["pct_diff"].notna()]
    return comparable[comparable["pct_diff"].abs() > tolerance]


# ---------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------
#
# Provenance and attestation are different claims, and this repository's
# integrity argument depends on not conflating them.
#
#   fetched_from  PROVENANCE. "These bytes came from this dataset on this
#                 date." A machine can assert this truthfully. It says nothing
#                 about whether the number is the *right* number for the
#                 analysis: a run that fetched the wrong dataset, or the right
#                 dataset with a wrong filter, produces a perfectly valid
#                 provenance string attached to a wrong value.
#
#   verified_by   ATTESTATION. "A person opened the cited source and confirmed
#                 this value belongs here." Only a human can assert this.
#
# The README's argument for shipping the repository empty is that a number
# carrying a citation looks verified whether or not anyone verified it. Writing
# a machine string into verified_by would recreate that exact failure in a new
# costume: an automated run against the wrong series would look signed off, and
# would look signed off *more* convincingly than a hand transcription because
# the provenance string is precise.
#
# So promote() populates source_type and fetched_from, and deliberately leaves
# verified_by blank. loader.UnverifiedDataError therefore keeps firing after a
# promotion until a human signs each row off. That is the intended behaviour,
# not an oversight, and it is why promote() cannot be part of an automated
# pipeline.

SOURCE_TYPE_API = "api"
SOURCE_TYPE_MANUAL = "manual"

PROVENANCE_COLS = ("source_type", "fetched_from")


def provenance_string(dataset_id: str, accessed: str | None = None) -> str:
    """Build a ``fetched_from`` value: ``fetch:<dataset_id>@<access_date>``."""
    return f"fetch:{dataset_id}@{accessed or _today()}"


def promote(
    series: str,
    values: pd.DataFrame | None = None,
    dataset_id: str | None = None,
    dry_run: bool = True,
    accessed: str | None = None,
    raw_dir: Path | None = None,
) -> pd.DataFrame:
    """Copy fetched values into the raw CSV for ``series``. Dry run by default.

    Writes the value columns plus ``source_type`` and ``fetched_from``. Leaves
    ``verified_by`` blank, and *clears* any existing attestation on a row whose
    value it changes: a human signed off on the old number, and that signature
    does not transfer to a new one.

    Never called automatically from anywhere. Returns the frame of changes it
    made, or would have made when ``dry_run`` is True.
    """
    if series not in RAW_TARGETS:
        raise KeyError(f"Unknown series {series!r}. Known: {sorted(RAW_TARGETS)}")
    if values is None or values.empty:
        raise FetchError(
            f"promote({series!r}) needs a frame of fetched values. Nothing was "
            f"passed, and promote() will not go and fetch on its own."
        )
    if not dataset_id:
        raise FetchError(
            "promote() needs the dataset_id the values came from, so that "
            "fetched_from records real provenance rather than a placeholder."
        )

    spec = RAW_TARGETS[series]
    raw_dir = raw_dir or RAW_DIR
    path = raw_dir / spec["csv"]
    current = pd.read_csv(path)
    keys: list[str] = spec["keys"]
    value_cols: list[str] = spec["values"]

    # These ship empty, so pandas reads them as all-NaN float columns and then
    # refuses a string assignment. Widen them to object before writing.
    for col in (*PROVENANCE_COLS, "verified_by", "verified_date"):
        if col not in current.columns:
            current[col] = ""
        current[col] = current[col].astype("object")

    indexed = values.set_index(keys)
    provenance = provenance_string(dataset_id, accessed)
    changes: list[dict[str, Any]] = []

    for i, row in current.iterrows():
        key = tuple(row[k] for k in keys)
        lookup = key[0] if len(key) == 1 else key
        if lookup not in indexed.index:
            continue
        for col in value_cols:
            if col not in indexed.columns:
                continue
            new = indexed.loc[lookup, col]
            old = row.get(col)
            if pd.isna(new):
                continue
            if not pd.isna(old) and float(old) == float(new):
                continue

            changes.append({
                **{k: row[k] for k in keys},
                "column": col,
                "old": "unpopulated" if pd.isna(old) else old,
                "new": new,
                "cleared_attestation": bool(str(row.get("verified_by") or "").strip()),
            })
            if not dry_run:
                current.at[i, col] = new
                current.at[i, "source_type"] = SOURCE_TYPE_API
                current.at[i, "fetched_from"] = provenance
                # A prior human sign-off referred to the prior value.
                current.at[i, "verified_by"] = ""
                current.at[i, "verified_date"] = ""

    diff = pd.DataFrame(changes)
    if dry_run:
        print(
            f"DRY RUN promote({series!r}): {len(diff)} cell(s) would change. "
            f"fetched_from would be {provenance!r}. verified_by would be left "
            f"blank, so strict loading still raises UnverifiedDataError until "
            f"a human signs off. Re-run with dry_run=False to write."
        )
    else:
        current.to_csv(path, index=False)
        print(
            f"promote({series!r}): wrote {len(diff)} cell(s) to {path}. "
            f"verified_by left blank by design."
        )
    return diff


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.fetch",
        description="Fetch and reconcile mortality inputs from CDC APIs.",
    )
    parser.add_argument("--discover", action="store_true",
                        help="search the CDC Socrata catalog and print candidates")
    parser.add_argument("--reconcile", action="store_true",
                        help="compare fetched values against data/raw/*.csv")
    parser.add_argument("--check", action="store_true",
                        help="reconcile, then exit non-zero on >0.5%% drift")
    parser.add_argument("--refresh", action="store_true",
                        help="bypass today's cache and re-fetch")
    parser.add_argument("--promote-info", action="store_true",
                        help="print the open question blocking promote()")
    args = parser.parse_args(argv)

    if args.promote_info:
        print(promote.__doc__ or "")
        print(
            "promote() is unimplemented pending a decision on verified_by "
            "semantics for API-sourced values. See the module docstring."
        )
        return 0

    if args.discover:
        found = discover()
        print_discovery(found)
        FETCH_DIR.mkdir(parents=True, exist_ok=True)
        snapshot = FETCH_DIR / f"_discovery_{_today()}.json"
        snapshot.write_text(
            json.dumps(
                {
                    series: [
                        {
                            "dataset_id": c.dataset_id,
                            "name": c.name,
                            "updated_at": c.updated_at,
                            "attribution": c.attribution,
                            "api_url": c.api_url,
                            "columns": c.columns,
                            "matched_query": c.matched_query,
                        }
                        for c in cands
                    ]
                    for series, cands in found.items()
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Discovery snapshot written to {snapshot}")
        print(
            "\nSTOP. Confirm which identifier belongs to each series and add it "
            "to SERIES in src/fetch.py before building parsers against it."
        )
        return 0

    if args.reconcile or args.check:
        fetched = load_analysis_grids(refresh=args.refresh)
        absent = missing_exports()
        if absent:
            print(
                "Exports not yet present ("
                + ", ".join(s.filename for s in absent)
                + ")\n",
                file=sys.stderr,
            )
        crude_check = fetched.pop("_crude_rate_check", None)
        seam = load_seam(refresh=args.refresh)
        report = reconcile_all(fetched)
        print(render_report(report, seam=seam, crude_check=crude_check))
        path = write_report(report, seam=seam, crude_check=crude_check)
        print(f"\nReport written to {path}")

        if args.check:
            drift = check_drift(report)
            if not drift.empty:
                print(
                    f"\nFAIL: {len(drift)} cell(s) differ by more than "
                    f"{CHECK_TOLERANCE_PCT}%.",
                    file=sys.stderr,
                )
                return 1
            print(f"\nOK: no populated cell differs by more than {CHECK_TOLERANCE_PCT}%.")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
