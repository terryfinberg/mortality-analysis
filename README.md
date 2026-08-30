# A Fragile Equilibrium

Reproducible analysis of U.S. mortality, decomposing changes in the crude death rate into
age-specific mortality and population age-structure components.

**Repository status: the data files are intentionally empty.**

## Why the data is empty

The CSVs in `data/raw/` ship with citations and no values. You populate them from the primary
sources before anything will run.

This is deliberate. An earlier version of this project carried mortality figures that had been
transcribed rather than fetched, and were never checked against the source documents. Numbers
that carry a citation comment look verified whether or not anyone verified them. Shipping the
repository empty makes the unverified state visible instead of invisible, and the loader
enforces it: `src/loader.py` raises `IncompleteDataError` on any missing value and
`UnverifiedDataError` on any row without a sign-off.

## Setup

**Windows**
```powershell
.\bootstrap.ps1
```

**macOS / Linux / WSL**
```bash
./bootstrap.sh
```

Either script creates a virtual environment, installs dependencies, registers a Jupyter
kernel, and runs the test suite. Expect about three minutes.

## Filling in the data

1. Open `data/queries/cdc_wonder_queries.md` and follow each query.
2. Enter values into the matching CSV in `data/raw/`, or retrieve them with
   `python -m src.fetch` (see **Fetching** below).
3. Fill `verified_by` and `verified_date` for each row you personally checked against the
   cited source. Do not fill these for values you copied from somewhere else.
4. Run `python -m src.report`.

`UAT_CHECKLIST.md` walks through this with checkpoints.

### Provenance and attestation are different columns

Each raw CSV carries three provenance columns, and they do not mean the same thing:

| Column | Meaning | Who may write it |
|---|---|---|
| `source_type` | `api` if fetched, `manual` if typed in | either |
| `fetched_from` | `fetch:<dataset_id>@<access_date>` | `src.fetch.promote()` |
| `verified_by` | a person checked this value against the cited source | **a human, only** |

This split is the point, not bookkeeping. The reason this repository ships empty is that a
number carrying a citation looks verified whether or not anyone verified it. An automated
fetch does not solve that; it changes the costume. A run against the wrong dataset, or the
right dataset with a wrong filter, writes an impeccably precise `fetched_from` string onto a
wrong number, and does so more convincingly than a hand transcription would.

So `verified_by` is never machine-written. `src.fetch.promote()` fills `source_type` and
`fetched_from` and leaves `verified_by` blank, which means **`UnverifiedDataError` still fires
after a successful fetch**. Promotion gets the numbers into place; it does not sign them off.
You do that, row by row, and the loader will not run in strict mode until you have.

If `promote()` overwrites a value you had already signed off on, it clears your
`verified_by` for that row. Your attestation was about the old number.

## Fetching

```bash
python -m src.fetch --discover     # search the CDC Socrata catalog, print candidates
python -m src.fetch --reconcile    # compare fetched values against data/raw/*.csv
python -m src.fetch --check        # as --reconcile, exit non-zero on >0.5% drift
```

`--reconcile` writes `data/processed/reconciliation_<date>.md`. Nothing in the fetch path
writes to `data/raw/*.csv`; parsed output lands in `data/raw/fetched/` and only the explicit,
default-dry-run `promote()` copies it across.

## Data redistribution

The raw CDC WONDER export files in `data/raw/wonder_exports/` are **committed deliberately**,
not by accident. They are the reproducibility artifact: each carries WONDER's own
query-parameter footer, so a reviewer gets the exact bytes the results were computed from and
can replay the query rather than reconstruct it from a description.

CDC WONDER data are in the public domain. Per the [CDC WONDER
FAQ](https://wonder.cdc.gov/wonder/help/faq.html#10):

> The public web site at http://wonder.cdc.gov is in the public domain, and only provides
> access to public use data and information. You may access the information freely, and use,
> copy, distribute or publish this information without additional or explicit permission.
> Please do provide a citation to credit the authors and/or data providers.

Citation is requested rather than required, and is provided: every export's footer contains
WONDER's own suggested citation, and `data/queries/cdc_wonder_queries.md` records the database
and query behind each file.

Use is subject to the WONDER Data Use Restrictions — statistical reporting and analysis only,
and no reported count or rate based on fewer than ten deaths. This analysis is national and
its smallest cell is in the tens of thousands, so that rule is satisfied by a wide margin.

## Running the analysis

```bash
python -m src.report
```

This computes every result, writes `data/processed/results.json`, generates five figures into
`figures/`, and builds `paper/manuscript_built.md` by substituting computed values into the
template at `paper/manuscript.md`.

**Never edit numbers in `manuscript_built.md`.** It is regenerated on every run. Edit the data
or the code.

## Running the tests

```bash
python -m pytest
```

One hundred and fifteen tests. They cover rate arithmetic, exact additivity of the Kitagawa
decomposition, recovery of a known trend by the excess-mortality baseline fit, the loader's
refusal to accept incomplete data, and the fetch layer: WONDER export parsing, age-band
collapse arithmetic, "Not Stated" handling, cache behaviour, refusal to return partial data
from a malformed response, the two exact identities, agreement with WONDER's published crude
rate, rejection of an export whose years do not match the range the registry declares,
measurement of the bridged/single-race vintage seam, and the vintage-sensitivity findings —
including a test that fails if `docs/denominator-methods.md` drifts from the code that
computes its numbers.

They also verify the committed data itself. Every WONDER export is hashed against the
`sha256` recorded in `WONDER_EXPORTS`, and every Census file against
`data/raw/census/PROVENANCE.md`, with cases that mutate a single byte to prove the check
fires. A recorded hash nobody recomputes is a claim, not a check — and the one integrity
defect this repository has actually had (git rewriting line endings inside a committed data
file, moving its bytes underneath its recorded hash) was caught by reading a warning, not by
anything that could fail.

**Tolerance policy.** A quantity defined to be equal is asserted equal, at `1e-9` for
floating-point representation only. A quantity merely expected to be close gets a real
tolerance. Do not loosen a `1e-9` to make a failure go away — at that size it is reporting an
arithmetic defect, not fixture noise. The fixtures are synthetic values with known analytic properties, chosen
to be obviously unlike real U.S. figures so nobody mistakes a fixture for data.

No test touches the network. The HTTP layer is mocked entirely.

`test_loader.py::test_repo_ships_with_unpopulated_data` fails once you populate the data.
That is expected. Delete the test at that point.

## Layout

```
data/raw/          Input CSVs with per-row citations. You fill these.
data/raw/census/   Census population vintages, committed, with PROVENANCE.md.
data/queries/      CDC WONDER query parameters for reproducing each extract.
data/processed/    results.json, generated.
docs/              Method notes: denominator sourcing, vintages, discontinuities.
src/               Analysis modules.
tests/             pytest suite.
figures/           Generated PNGs.
notebooks/         Guided walkthrough.
paper/             Manuscript template, built manuscript, policy framework.
```

## Modules

| Module | Responsibility |
|---|---|
| `loader.py` | Read and validate inputs. Fails loudly on incomplete or unverified data. |
| `fetch.py` | Retrieve inputs from CDC APIs, cache, reconcile against the raw CSVs. |
| `census.py` | Census population vintages. Enforces the age top-code and total identities. |
| `vintage.py` | Vintage sensitivity: restatement uniformity, two-treatment Kitagawa. |
| `rates.py` | Crude rates, age-specific rates, direct age standardization. |
| `decomposition.py` | Kitagawa decomposition. |
| `excess.py` | Baseline fitting and excess mortality. |
| `figures.py` | Figure generation. |
| `report.py` | Orchestration, results.json, manuscript build. |

## Method notes

Age adjustment uses the 2000 U.S. Standard Population, collapsed from eleven groups to six.
The loader asserts the weights sum to 1,000,000, because an error there would bias every
adjusted rate without any visible symptom.

Excess mortality projects the **age-adjusted** rate rather than the raw count. A count-based
baseline attributes the mechanical effect of population aging to the pandemic. This choice
produces lower estimates than count-based published figures; the difference is methodological,
not an error on either side. See manuscript section 3.3.

## License and citation

Three different things live here and they are licensed separately, because one file covering
all three would have to be wrong about at least one of them.

| what | terms | file |
|---|---|---|
| Software — `src/`, `tests/`, `bootstrap.*`, `notebooks/` | BSD-3-Clause | [`LICENSE`](LICENSE) |
| Data — `data/raw/wonder_exports/`, `data/raw/census/` | **Not licensed.** U.S. federal government works, public domain under 17 U.S.C. § 105 | [`DATA.md`](DATA.md) |
| Manuscript and outputs — `paper/`, `figures/`, `results.json` | CC BY 4.0 | [`paper/LICENSE`](paper/LICENSE) |

**The data is not licensed because it is not ours to license.** Applying any license to it —
BSD, CC BY, even CC0 — would assert rights that do not exist. `DATA.md` states the status,
records the CC0 release of the thin compilation right over the *selection and arrangement*
only, and explains why that scope is kept narrow rather than simplified into a blanket CC0.

BSD-3-Clause rather than MIT for the code because of clause 3, the non-endorsement term: this
repository ships a model policy framework next to the analysis, so a fork reaching different
conclusions while carrying the author's name is foreseeable rather than hypothetical.

If this work is cited, cite the manuscript and the Zenodo DOI minted from a tagged release,
not this README.
