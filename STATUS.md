# Status

**Last updated:** 2026-08-31 · **HEAD:** `6b535a9` · **Branch:** `main` · **No remote yet**

> The branch was renamed `master` → `main` on 2026-08-31, before any push, so it matches the
> default GitHub gives a new repository. Renaming after pushing means fixing the default
> branch in settings and re-pointing anything that already cloned it.

## Where this stands

*A Fragile Equilibrium* is a reproducible analysis of U.S. mortality, 2010–2024, decomposing
the change in the crude death rate into an age-specific mortality component and a
population age-structure component (Kitagawa), estimating pandemic-era excess mortality
against a pre-pandemic trend, and characterising the age distribution of COVID-19 deaths.
**The analysis is complete and runs end to end.** All four CDC WONDER exports are committed
and hash-verified, all 150 data rows are populated from those exports and personally
attested, 14 of the 15 annual totals are corroborated against NCHS's published NVSR reports,
and `python -m src.report` produces `results.json`, five figures and a built manuscript with
every value substituted from code. 193 tests pass. What remains is not analysis: it is
publication mechanics — a scoped review of the arithmetic, then GitHub, Zenodo, a DOI, and a
preprint. The artifact question is settled: `figures/` is tracked, so a release archives the
images the paper shows.

## Done

- **Four WONDER exports committed** (`data/raw/wonder_exports/`), each with its
  query-parameter footer, SHA-256 in `WONDER_EXPORTS`, and a test that recomputes the hash.
  Footers are asserted against the registry: dataset, ICD-10 codes (including their absence
  for all-cause queries), and access date.
- **Three Census vintage files committed** (`data/raw/census/`) with `PROVENANCE.md` carrying
  URL, retrieval date and SHA-256 per file, since a Census CSV has no embedded footer.
- **Data promoted and attested.** 150 rows across four CSVs, populated by
  `python -m src.fetch --promote --write`, each carrying the export it came from by filename
  and content hash. All attested by Terry Finberg on 2026-08-30 against the cited exports.
- **Corroboration: 14 of 15 annual totals.** 2010–2022 against NVSR *Deaths: Final Data*
  Table B on both count and crude rate; 2023 against NVSR 74-11 on the **count only**.
  `corroborated_measures` records which measures each source actually confirmed.
- **Both exact identities hold** for all 15 years with no tolerance, and the computed crude
  rate reproduces WONDER's published column for all 15.
- **The bridged/single-race seam is measured and is exactly zero** in every band.
- **The 2010 treatment range is computed**, not asserted: A/B/C′ in `src/treatments.py`,
  age-to-rate ratio 3.41–3.87.
- **Licensing done** three ways: BSD-3-Clause (`LICENSE`), a public-domain status statement
  for the federal data (`DATA.md`), CC BY 4.0 for the manuscript (`paper/LICENSE`).
- **193 tests.** (The commit count that used to sit here was removed: nothing checks it and
  it goes stale on every commit, which is the exact defect `test_docs_are_current` exists to
  catch. `git rev-list --count main` answers it on demand.)

## Open, in the order to tackle it

### 1. Review the arithmetic — scoped, not whole-repo

**Decided 2026-08-31: review the three arithmetic modules only.** Branch
`review-arithmetic` carries `src/rates.py`, `src/decomposition.py` and `src/excess.py` as a
single commit on top of `review-base`, an empty root commit sharing no history with `main`.
The diff is therefore exactly those three files added, and `/ultrareview` on that branch
reviews the arithmetic and nothing else.

The whole-repo review was tried and refused:

> This looks like a first review of the entire repository (63 files changed, 16564
> insertions(+)), which exceeds ultrareview's limit. This repo has no main branch.

The refusal named a size limit, and the three ways around it were: pass an explicit base
branch, commit a subset on a branch off an empty base, or push to GitHub and review a PR.
**None of the three fixes the real problem, which is not the limit.** A first review of 63
files is shallow whatever route delivers it — attention spread across bootstrap scripts,
licence files and prose is attention not spent on the arithmetic. Scoping is the point;
clearing the limit is a side effect.

The three modules were chosen because **a DOI makes the arithmetic permanent.** Rate
computation, the Kitagawa decomposition and the excess-mortality baseline fit are what the
manuscript's claims reduce to. A defect in `figures.py` is visible to any reader; a defect in
`decomposition.py` is not, and it would be archived under a version number that never changes.

`fetch.py`, `loader.py`, `census.py`, `vintage.py` and `treatments.py` are **not** reviewed by
this pass and remain unreviewed. They are left for future PRs whose diffs are small enough for
a review to mean something, rather than being swept into one pass that would skim all of them.
Note what this does and does not buy: the review covers the arithmetic, not the data path that
feeds it.

**Do not merge `review-arithmetic`.** It exists to be diffed. Its parent shares no history
with `main`, and the files on it are copies of files `main` already tracks.

### 2. What is tracked vs generated — decided

**Decided 2026-08-31: track `figures/`.**

| artifact | status | note |
|---|---|---|
| `figures/*.png` | **tracked** | the manuscript cites them by filename; Zenodo should archive what the paper shows |
| `data/processed/results.json` | **tracked** | every number the manuscript cites |
| `data/processed/reconciliation_*.md` | **ignored** | dated, regenerates |
| `paper/manuscript_built.md` | **tracked** | the citable output |
| `paper/public_health_policy_built.md` | **tracked** | same |

The reasoning: a Zenodo archive that omits the figures archives a promise that they can be
rebuilt rather than the images a reader saw. The cost is churn in `git status`, handled by
convention rather than by ignoring the directory — **commit a regenerated figure only when the
numbers behind it changed**, and `git checkout -- figures/` otherwise. Written up in the README
under "Regenerated figures: when to commit them" so nobody chases a phantom diff later.

One finding while implementing this, recorded because it inverts the expectation: **the figures
are currently byte-reproducible.** Two consecutive `python -m src.report` runs produced
identical SHA-256s for all five PNGs. This matplotlib embeds no timestamp — the only metadata
chunk is a `Software` string naming its own version. So the anticipated per-run noise does not
exist today.

What does exist is a version trap. That `Software` string means **a matplotlib upgrade rewrites
every figure's bytes while every number stays identical.** If all five figures ever show as
modified at once, check `results.json` before assuming a result moved: it is byte-stable across
runs, so if it has not changed, this is a toolchain bump. Commit it as its own commit and say
so, or discard it — but do not let it ride along inside a substantive change.

Making the output explicitly deterministic (pinning or stripping the PNG `Software` metadata)
would close the trap rather than document it. Not done: it would rewrite all five figures'
bytes for no change in what they show, and the trap is now written down in two places.

### 3. Create the GitHub repository and push

Public. The repo has no remote. `main` is the branch to push and the one GitHub should treat
as default — already named to match, so nothing needs fixing in settings afterwards.

**Push `main` only.** `review-base` and `review-arithmetic` are local scaffolding for step 1;
pushing them would publish a rootless branch and a duplicate copy of three source files, and
Zenodo would archive the repository with both hanging off it. Delete them once the review is
done:

```bash
git branch -D review-arithmetic review-base
```

### 4. Connect Zenodo — **BEFORE tagging**

> **Order matters and getting it wrong costs a version number.** Zenodo archives only
> Releases created *after* the repository toggle is switched on. **A pushed tag is not a
> Release.** Enable the Zenodo integration for the repository first, then create the Release
> in the GitHub UI. Tagging first and connecting after means the DOI never appears, and the
> fix is cutting a throwaway v0.1.1 purely to trigger it.

### 5. Tag `v0.1.0`, create the Release, mint the DOI

In that order, after step 4.

### 6. Put the DOI into `paper/medrxiv_submission.md`

It has a placeholder at the top and a checklist item.

### 7. Confirm the preprint license before posting

`paper/LICENSE` is CC BY 4.0. **The preprint license is effectively irreversible once
posted** — servers do not relicense a posted version, and a later version under different
terms does not retract the first. Re-confirm the target journal's preprint policy against
CC BY 4.0 *before* posting. This is repeated at the top of `paper/medrxiv_submission.md` and
as a checklist item there.

## Known limits

State these plainly; none of them is a defect to be fixed before publishing.

- **2024 has no independent published source.** Not a delayed one — none. NCHS has not
  published *Deaths: Final Data for 2024*, and the lag runs about three years. That year rests
  on the committed WONDER export alone. Do not fill it from a provisional release or a press
  figure to make the column look complete.
- **2023 is count-only corroboration.** NVSR 74-11 confirms the death count. Its rates are not
  comparable: 2020 on an April 1 basis against our July 1, 2021–2023 on a blended base rather
  than the per-year vintage chain, and published per 1,000 to one decimal — one printed digit
  is worth 100 per 100,000, so it could not discriminate our 922.9 from anything in a
  ten-point band even with matching denominators.
- **NVSR is not independent of WONDER.** Both are NCHS products over the same mortality file
  and the same Census-derived denominators. The corroboration establishes that our query
  returned what NCHS published in its report of record. It is **not** independent confirmation
  and **not** evidence that NCHS is correct. Replication wanting independence must go to a
  different data producer. See "What the NVSR corroboration does and does not establish" in
  `docs/denominator-methods.md`.
- **No full consistent-vintage reanalysis, by decision rather than omission.** The vintage
  chain has no terminal state: V2025 moved every year of V2024 including the estimates base,
  and NCHS has itself published two different crude rates for 2020 in two of its own reports.
  Vintage sensitivity is therefore reported as a range at the two points where it was
  measured — the 2010 basis and the 2023 restatement — and rebasing the series would produce
  numbers that are internally consistent, externally stale within a year, and would destroy
  the crude-rate match against WONDER.
- **Age groups are six, not the NCHS eleven.** Age-adjusted rates are therefore **not**
  comparable to NCHS's published figures. This is the trap most likely to be sprung by
  someone checking the work; it is called out in `UAT_CHECKLIST.md` Section 7.

## Where things are

| what | where |
|---|---|
| Method notes, denominators, discontinuities | `docs/denominator-methods.md` |
| Corroboration plan and status | `UAT_CHECKLIST.md` Section 7 |
| Query parameters and export registry | `data/queries/cdc_wonder_queries.md`, `src/fetch.py` |
| Data status and licensing | `README.md`, `DATA.md`, `LICENSE`, `paper/LICENSE` |
| Submission checklist | `paper/medrxiv_submission.md` |
