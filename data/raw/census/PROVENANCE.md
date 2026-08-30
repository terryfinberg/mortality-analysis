# Census population vintages — provenance

These files are **analysis inputs to a published finding**, not scratch lookups,
so they are committed for the same reason the WONDER exports are: a reviewer
should get the exact bytes the numbers were computed from.

**A Census CSV carries no query footer.** A WONDER export embeds its own query
parameters, which is what makes the export file self-describing. These files have
no equivalent, so this document is the only provenance they have. If you add a
file here, add its row below in the same commit — an unrecorded CSV in this
directory is indistinguishable from one somebody edited.

## Files

| file | SHA-256 | bytes | retrieved | source URL |
|---|---|---|---|---|
| `nc-est2020-agesex-res.csv` | `03d7376535ae0e15233f40758e84f7692e2669452f7d2da71968eb4a3269e30b` | 32,782 | 2026-08-30 | https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/national/asrh/nc-est2020-agesex-res.csv |
| `nc-est2024-agesex-res.csv` | `fbb151e8ae8554283dcbf192e6b420658ea444ee7d8849988aa1d5615183edf1` | 16,171 | 2026-08-30 | https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/national/asrh/nc-est2024-agesex-res.csv |
| `nc-est2025-agesex-res.csv` | `6436d4f6972d415caf14cb20776807bc031fc9f1bfc9d6ff26055d592a2b0230` | 18,282 | 2026-08-30 | https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/national/asrh/nc-est2025-agesex-res.csv |

Verify with:

```bash
sha256sum data/raw/census/*.csv
```

## How the paths were found

**By listing the directory, not by guessing the filename.** The layout is
counterintuitive enough to have cost an hour once already:

- National totals live under `state/totals/`, **not** `national/totals/`.
  `2020-2025/national/totals/` returns HTTP 404; `2020-2025/national/asrh/`
  serves.
- `national/` contains only `asrh/`.
- Vintage directories are named by range — `2010-2020/`, `2020-2024/`,
  `2020-2025/` — so the directory name does not match the vintage number on its
  own.
- **The filename pattern is not stable across vintages.** `2010-2019/national/asrh/`
  contains only `nc-est2019-alldata-*.csv` files and **no** `agesex-res` file at
  all; the July 1 2010 age detail lives in the Vintage 2020 file instead, which
  carries both `CENSUS2010POP` and `POPESTIMATE2010`. Constructing
  `nc-est2019-agesex-res.csv` by analogy would have produced a 404, which is the
  concrete form of "list, do not guess".

`src/census.vintage_index_url(vintage)` returns the directory to list when adding
a vintage. List it, read the filename out of the response, and register a
`CensusVintage`. Do not construct the filename from a pattern.

`www2.census.gov` is reachable from this repository's tooling, unlike
`wonder.cdc.gov`, which returns HTTP 403 behind an Akamai edge block. So Census
figures can be checked directly rather than quoted from memory, and should be.

## Schema notes

`SEX,AGE,ESTIMATESBASE2020,POPESTIMATE2020,…` — one row per (sex, single-year age).
The Vintage 2020 file additionally carries `CENSUS2010POP`, the April 1 2010
decennial count, alongside `POPESTIMATE2010`, the July 1 estimate. Both are
needed: WONDER carries the April 1 figure for 2010 and the July 1 figure is the
alternative denominator in treatment C′ (see `src/treatments.py`).

- `SEX == 0` is both sexes combined.
- `AGE == 999` is the all-ages total row.
- `AGE == 100` is **100 and over**, not exactly 100. The `85+` band therefore
  takes `85 <= AGE <= 100`; reading it as exactly 100 silently drops everyone
  older.
- The single-year rows sum **exactly** to the `AGE == 999` row. That is free
  arithmetic validation of any band collapse, and `src/census.collapse_to_bands`
  asserts it rather than trusting it.

## What these are used for

Measuring what a later vintage did to an earlier year, which WONDER cannot show
because it carries each year at the vintage current when that year was first
estimated. See `docs/denominator-methods.md` section 2, and `src/vintage.py`,
which computes every number in it.

## Redistribution

Census Bureau data are in the public domain, as with the WONDER exports.
Citation is requested and is provided: the source URL and retrieval date above
identify each file precisely.
