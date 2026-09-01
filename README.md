# A Fragile Equilibrium

Reproducible analysis of U.S. mortality, decomposing changes in the crude death rate into
age-specific mortality and population age-structure components.

**Repository status: populated, attested, and running. Corroboration against NCHS's published
reports is partial and deliberately labelled as such — 14 of 15 annual totals.**

See [`STATUS.md`](STATUS.md) for where the project stands, what is still open and in what
order, and the known limits stated plainly.

## Where the data came from, and what is still missing

`data/raw/*.csv` was populated by `python -m src.fetch --promote --write` from the four
committed CDC WONDER exports in `data/raw/wonder_exports/`. Every row records which export it
came from, by filename and content hash, in `fetched_from`. All 150 rows were then attested
against those exports by a person, on 2026-08-30, so `python -m src.report` runs.

**What is still open is corroboration**, which is a different claim: whether a separate
publication reports the same figure. Thirteen of the fifteen annual totals, 2010–2022, match
Table B of the corresponding NVSR *Deaths: Final Data* report exactly, and our computed crude
rate matches NVSR's published rate to one decimal in all thirteen. 2023's **count** is
corroborated against NVSR 74-11, but not its rate — that report computes rates on a different
population basis, at a precision too coarse to discriminate ours. `corroborated_measures`
records which measures each row's source actually confirmed, so the weaker claim stays
visibly weaker. 2024 has no published source at all, and blank means not corroborated rather
than failed.

**That is not independent confirmation.** NVSR and WONDER are both NCHS products over the same
mortality file and the same Census-derived denominators; the agreement shows our query
returned what NCHS published, not that NCHS is correct. See
`docs/denominator-methods.md`, "What the NVSR corroboration does and does not establish", and
`UAT_CHECKLIST.md` Section 7.

That gap is the point rather than an unfinished chore. An earlier version of this project
carried mortality figures that had been transcribed rather than fetched and were never checked
against the source documents. Numbers that carry a citation look verified whether or not
anyone verified them, and an automated fetch does not fix that — it changes the costume. A run
against the wrong export writes an impeccably precise provenance string onto a wrong number,
more convincingly than a hand transcription would. So promotion fills `source_type` and
`fetched_from` and never `verified_by`.

The repository previously shipped with the CSVs empty, for the same reason: to make the
unverified state visible instead of invisible. Emptiness has done its job and been retired.
What replaced it is a guarantee that does not expire with the data's state: no machine path
in this repository can write `verified_by`, and a test asserts it against a temporary
directory rather than against the current CSVs. See **Provenance, attestation and
corroboration are three different columns** below.

What the promoted data satisfies already:

- Both exact identities: `sum(bands) + not_stated == annual deaths`, and
  `sum(bands) == annual population`, for all 15 years, with no tolerance.
- The external check: the crude rate computed from these CSVs reproduces WONDER's own
  published Crude Rate column for **all 15 years**, 2010 through 2024.

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

### Provenance, attestation and corroboration are three different columns

They answer three different questions, and collapsing any two of them is how a repository
ends up claiming more than it checked:

| Column | The claim | Who may write it |
|---|---|---|
| `source_citation` | *What this value is a copy of.* The export's footer `Dataset`, its query parameters, access date and sha256 | derived from the footer by `export_citation()` |
| `fetched_from` | *Provenance.* `wonder-export:<filename>@sha256:<hash>` | `src.fetch.promote()` |
| `verified_by` | *Attestation.* A person confirmed this value matches the cited export | **a human, only** |
| `corroborated_against` | *Corroboration.* A separate publication reports the same figure — e.g. an NVSR volume and table. **Not independent:** see the note below | **a human, only** |

This split is the point, not bookkeeping. A number carrying a citation looks verified whether
or not anyone verified it. An automated fetch does not solve that; it changes the costume. A
run against the wrong dataset, or the right dataset with a wrong filter, writes an impeccably
precise `fetched_from` string onto a wrong number, and does so more convincingly than a hand
transcription would.

**`source_citation` names the committed export**, not a published report the value did not
come from. Every row's citation is derived from that export's own footer, so it cannot drift
from the file it describes, and attesting to it is a claim anyone can check today against
bytes in this repository.

**Corroboration is deliberately separate, and deliberately incomplete.** Attestation says our
number faithfully reproduces the source we took it from; corroboration says that source agrees
with a different publication. It is not available for every row — NVSR publishes annual
totals, not the six-band grid, and a published report may not exist yet for the most recent
years. **A blank `corroborated_against` means not corroborated. It does not mean corroboration
failed, and the loader never requires it.** Partial corroboration stated as partial is worth
more than complete attestation to a standard met on a sample.

**It is corroboration, not independent confirmation.** NVSR and WONDER are both NCHS products
drawing on the same mortality file and the same Census-derived denominators. Agreement rules
out a real class of error — a query returning the wrong slice would not reproduce the
published national total for thirteen consecutive years — and says nothing about whether the
underlying NCHS data is right. The precise statement is in
`docs/denominator-methods.md`.

So `verified_by` is never machine-written. `src.fetch.promote()` fills `source_type`,
`fetched_from` and `source_citation`, and leaves `verified_by` blank, which means
**`UnverifiedDataError` still fires after a successful fetch**. Promotion gets the numbers into
place; it does not sign them off. You do that, row by row, and the loader will not run in
strict mode until you have.

If `promote()` rewrites a row's `source_citation`, it clears `verified_by` too — a signature
was made against what the old citation claimed.

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

### Regenerated figures: when to commit them

`figures/` is tracked, not ignored. The manuscript cites each figure by filename, and a Zenodo
archive of a release should contain the images a reader sees in the preprint rather than a
promise that they could be rebuilt.

**The convention: commit a regenerated figure only when the numbers behind it changed.** If a
run was a no-op — a test run, a rebuild to check reproducibility, a docs edit — discard any
figure churn rather than committing it:

```bash
git checkout -- figures/
```

The figures in a commit should correspond to the data and code in that same commit. Churn
committed on its own breaks nothing, but it buries the commits where a figure moved because a
*result* moved, which are the ones worth finding later.

In practice there is usually nothing to discard. Re-running `python -m src.report` with
unchanged inputs currently reproduces all five PNGs **byte for byte** — verified by hashing
them across consecutive runs — because this matplotlib writes no timestamp into its output.
The only metadata it embeds is a `Software` string naming its own version.

That last detail is the thing to recognise later. **A matplotlib upgrade rewrites the bytes of
every figure while every number stays identical**, because the version string is part of each
file. So if `git status` ever shows all five figures modified at once, check
`data/processed/results.json` first: it is byte-stable across runs, and if it has not moved,
what you are looking at is a toolchain bump rather than a change in any result. Commit it as
that, in a commit of its own, and say so in the message — or discard it. Do not fold it into
a substantive change, where it would masquerade as one.

## Running the tests

```bash
python -m pytest
```

One hundred and ninety-three tests. They cover rate arithmetic, exact additivity of the Kitagawa
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

Two further classes are covered because a defect in each got past everything else. **Figure
geometry** is asserted against the values it encodes — a stacked bar once hid a negative
component entirely, and every input-side check passed while it did. **Document prose** is
checked for statistic-shaped literals that restate a value from `results.json`, because a
hardcoded number that is right today agrees with itself forever.

A third class was added after a scoped code review of the arithmetic modules: **an incomplete
age grid**. Every year must carry all six bands, exactly once. A missing band is not a missing
*value* — the surviving rows are fully populated — so it passes the completeness check, and
neither the age-adjusted rate nor the Kitagawa decomposition raises on it. Both quietly return
a partial sum instead. The Kitagawa additivity identity holds just as exactly over biased
shares as over correct ones, so the suite's strongest invariant is blind to this by
construction. It is refused at the loader, and refused again in `rates.py` and
`decomposition.py` for callers that build a frame themselves.

**Tolerance policy.** A quantity defined to be equal is asserted equal, at `1e-9` for
floating-point representation only. A quantity merely expected to be close gets a real
tolerance. Do not loosen a `1e-9` to make a failure go away — at that size it is reporting an
arithmetic defect, not fixture noise. The fixtures are synthetic values with known analytic properties, chosen
to be obviously unlike real U.S. figures so nobody mistakes a fixture for data.

No test touches the network. The HTTP layer is mocked entirely.

`test_loader.py::test_repo_ships_with_unpopulated_data` was removed when the data was
populated, as this section previously instructed. `test_populated_data_is_still_unverified`
replaces it: data being present is no longer the question, data being signed off is.

## Layout

```
data/raw/          Input CSVs with per-row citations. You fill these.
data/raw/census/   Census population vintages, committed, with PROVENANCE.md.
data/queries/      CDC WONDER query parameters for reproducing each extract.
data/processed/    results.json, generated.
docs/              Method notes: denominator sourcing, vintages, discontinuities.
src/               Analysis modules.
tests/             pytest suite.
figures/           Generated PNGs. Tracked, so a release archives what the paper shows.
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
| `treatments.py` | The three treatments of the 2010 measurement basis, and the reported range. |
| `attest.py` | Records human claims: attestation and corroboration. Never called automatically. |
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
