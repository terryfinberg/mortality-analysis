# Status

**Last updated:** 2026-09-04 · **Branch:** `main` ·
**Remote:** `origin` → `github.com/terryfinberg/mortality-analysis` · **`v0.1.2` tagged;
it is the release the preprint cites, pending its version DOI**

> ## ✅ `v0.1.2` is tagged. It is the release to post.
>
> **`v0.1.1` renders a typographic error the source never contained.** Its PDF sets
> `2023's` as `2023′s`, with a prime where the apostrophe belongs, in the abstract, in
> §4.4 and in §4.5. `paper/manuscript.md` held an ordinary ASCII apostrophe the whole
> time; the build manufactured the prime. See step 9. `v0.1.2` also removes the em dash
> from the manuscript, which is house style and now enforced by a test.
>
> **`v0.1.0` is archived and permanent, and its manuscript is defective.** That is why
> `v0.1.1` exists. Everything that
> makes the paper citable landed *after* that tag: the deposited Declarations section
> contains the AI disclosure and nothing else — no data availability, funding, competing
> interests, ethics, author contributions or ORCID. The deposited abstract still says
> "mortality risk at a given age fell", which reads as a per-band claim and is false for
> two of six bands. Its §4.1 has no band-level discussion at all, its figures are named as
> prose filenames rather than embedded, they run 1, 5, 3, 4, and `fig2` is archived uncited.
>
> Those are defects in the deposited record, not cosmetics. `v0.1.1` corrects all of them;
> the submission artifacts in `dist/` were built from the tagged tree and verified
> identical to it, so the posted preprint and the deposit are the same document.
>
> ### The DOI rule this release established
>
> **Nothing inside the archive names its own release's version DOI.** A version DOI is
> minted when Zenodo archives the release, which is *after* the commit that release is cut
> from, so a file inside the deposit cannot carry the identifier of the deposit containing
> it. Writing one there yields either an identifier that does not exist yet or — the way
> `CITATION.cff` read before this release — the *previous* release's DOI attached to a new
> version number, which is the same class of error as a `date-released` describing a
> release that never happened.
>
> | | DOI | where it may be written |
> |---|---|---|
> | **Concept** | [10.5281/zenodo.22263667](https://doi.org/10.5281/zenodo.22263667) | anywhere, including inside the archive. Always exists, always resolves |
> | **Version `v0.1.0`** | [10.5281/zenodo.22263668](https://doi.org/10.5281/zenodo.22263668) | the Zenodo record, and `CITATION.cff`'s `identifiers:` in a **post-tag** commit |
> | **Version `v0.1.1`** | [10.5281/zenodo.22267191](https://doi.org/10.5281/zenodo.22267191) | same |
| **Version `v0.1.2`** | not yet minted | same, once the Release is created |
>
> **The allocation is not sequential, and this release proved it.** `v0.1.0`'s version DOI
> was the concept DOI plus one, which made `22263669` look like a safe guess for the next
> one. `v0.1.1` landed at `22267191`, some three and a half thousand away. Zenodo assigns
> at deposit time. A version DOI is only ever copied from the record it was minted on.
>
> The manuscript, `README.md` and `paper/medrxiv_submission.md` all cite the concept DOI
> and say why. The manuscript names its own release from `{{RELEASE_VERSION}}`, which
> `report.py` reads out of `CITATION.cff`, so the paper cannot name a version the citation
> record disagrees with. **Do not guess a version DOI**; the table above records what
> happened when that pattern looked predictable.
>
> **Every medRxiv declaration is now written.** Funding, competing interests, ethics,
> author contributions, data availability and ORCID (`0009-0006-1598-4200`) are all in the
> manuscript's Declarations. The iD went into `CITATION.cff` and `.zenodo.json` in the same
> commit, because an identifier in one place and not the others is the two-places-disagree
> failure step 6 was written about.
>
> What remains is the preprint, not the archive: step 7's licence confirmation, the UAT
> pass, and the format items in `paper/medrxiv_submission.md`.
>
> **`.zenodo.json` describes the *next* deposit, not the one that exists.** Zenodo read that
> file when it archived `v0.1.0`, and it had no ORCID then, so the live record's creator is
> still bare. Add the iD to the existing record in the Zenodo UI, or it will not appear
> until a future release.

> The branch was renamed `master` → `main` on 2026-08-31, before any push, so it matches the
> default GitHub gives a new repository. Renaming after pushing means fixing the default
> branch in settings and re-pointing anything that already cloned it.

## Where this stands

*Decomposing U.S. Crude Death Rates, 2010-2024: Population Aging Dominates, and the
Denominator Is Not Stable* is a reproducible analysis of U.S. mortality making two
stated contributions. **The decomposition:** the change in the crude death rate splits into an
age-specific mortality component and a population age-structure component (Kitagawa), with
pandemic-era excess mortality estimated against a pre-pandemic trend and the age distribution
of COVID-19 deaths characterised. **The denominator:** four vintage boundaries inside a single
fifteen-year series, each measured against source data rather than assumed, one of them at
exactly zero.

**The analysis is complete and runs end to end.** All four CDC WONDER exports are committed
and hash-verified, all 150 data rows are populated from those exports and personally
attested, 14 of the 15 annual totals are corroborated against NCHS's published NVSR reports,
and `python -m src.report` produces `results.json`, five figures and a built manuscript with
every value substituted from code. 219 tests pass. The arithmetic has been reviewed and its
findings fixed, `figures/` is tracked so a release archives the images the paper shows, and
`main` is pushed to GitHub.

**The restructure is executed, `v0.1.0` is archived, and nothing analytical remains.**
`v0.1.2` is the release to post: `v0.1.0` predates the Declarations, the abstract
correction and the embedded figures, and `v0.1.1` renders a prime where the abstract
wants an apostrophe. Neither is analytical and both reach the reader. See the banner
above and steps 4 through 9 below.

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
- **219 tests.** (The commit count that used to sit here was removed: nothing checks it and
  it goes stale on every commit, which is the exact defect `test_docs_are_current` exists to
  catch. `git rev-list --count main` answers it on demand.)

## The restructure, executed

**Decided 2026-08-31. Executed 2026-09-01.**

### What was wrong

The paper's strongest contribution was filed as a limitation, in §6.2 "Denominator vintage",
and the abstract did not mention it at all. The introduction conceded, correctly, that the
Kitagawa decomposition is not novel — "demographers have applied it routinely since" — which
left the demographic half of the paper contributing a careful application of a 1955 method to
a recent series. Useful; not new. The denominator work was the new part, and it sat in the
section reserved for the analysis's own shortcomings. If the strongest contribution is absent
from the abstract and present only in the limitations, the paper is framed wrongly — not
incompletely, wrongly.

### What changed

One paper, two stated contributions. Not two papers: the findings are causally linked — the
denominator work is what licenses the decomposition's interpretation, and the decomposition is
what makes the denominator work matter to anyone who is not a methodologist.

1. **Denominator findings moved into Results as §4.4, "The population denominator is not
   stable."** They are results; they were measured, not conceded. The section states the four
   boundaries, carries the three-treatment table, and closes on the NCHS instance.
2. **§6 keeps only limitations of this work** — data provenance, baseline sensitivity, age
   group coarseness, no cause-of-death modelling. Renumbered 6.2–6.4 after the move.
3. **A genuine limitation was added as §6.5, "No consistent-vintage reanalysis."** The
   distinction that resolves the old muddle: *measuring* the vintage boundaries is a result;
   *declining to rebase the series onto one vintage* is a limitation. The first moved to §4.4,
   the second was written fresh.
4. **The abstract states both contributions**, and its closing paragraph no longer opens
   "The equilibrium of the title" — that phrase was anchored to a title that no longer exists.
   The equilibrium argument survives in §5.1, introduced by the text rather than by the title.
5. **The introduction names what is new**, pointing at §4.4 explicitly instead of claiming
   novelty for the pipeline.
6. **The title changed in all six files that carried it** (see below).
7. **The boundary count is now stated one way: four, one of which is exactly zero.**
   `docs/denominator-methods.md` said "three known discontinuities" and then discussed the
   bridged/single-race seam separately, which made the seam invisible in the count precisely
   because its measurement came back zero. Its heading is now "The four measured boundaries,
   one of which is exactly zero", the seam has its own numbered entry, and the doc records why
   the count changed.

### Three defects found while doing it, all predating the restructure

Recorded because none was caused by this work and all three would have survived it:

| defect | fix |
|---|---|
| The manuscript cross-referenced "Section 6.2" for baseline-window sensitivity; §6.2 was Denominator vintage and baseline sensitivity was §6.3 | the renumbering makes the existing reference correct; verified rather than assumed |
| The manuscript twice cited "the table appears in section 6" for the three 2010 treatments. **No such table existed anywhere in the paper** — the built manuscript contained exactly one table, the decomposition — though `results.json` had carried every value for one all along | the table now exists, in §4.4, bound to new `TREAT_*` tokens in `report._flatten()` |
| This document listed three files as carrying the title. **Six did**: also `README.md`, `src/__init__.py`, `notebooks/01_walkthrough.ipynb` and `paper/public_health_policy.md`, where it served as the project's short name | all six updated; see below |

### What the title change dragged with it

**Decided 2026-09-01: retire "A Fragile Equilibrium" everywhere**, rather than keeping it as a
project codename. The objection that retired it from the paper — it names the demographic half
only — applies to the project as much as to the manuscript, and a README whose title disagrees
with `CITATION.cff` is the same two-places-disagree failure this document warns about for the
DOI in step 6.

| file | what carried the title |
|---|---|
| `paper/manuscript.md` | the `#` heading |
| `CITATION.cff` | `title:`, and the `abstract:`, which described a decomposition study only |
| `.zenodo.json` | `title:`, and the `description`, same problem |
| `README.md` | the `#` heading; now carries the short form with the full title beneath it |
| `src/__init__.py` | the package docstring |
| `notebooks/01_walkthrough.ipynb` | the first markdown cell |
| `paper/public_health_policy.md` | the "Companion to:" line |

Short form where the full title does not fit: *Decomposing U.S. Crude Death Rates, 2010-2024*.

Year ranges are written with a hyphen throughout, matching the interval strings `src/report.py` builds into
`results.json`. The title carried an en-dash briefly and the paper rendered `2010-2019`
two ways on one page as a result.

`CITATION.cff` also carries `version: 0.1.0` and `date-released:`. The date was
**deliberately left wrong until tag time** — it read `"2026-08-31"`, a date that passed
without a release — and was corrected to `"2026-09-02"` in `0b4645c`, the commit the tag
points at, so the file never described a release that did not exist.

### The regression test, and its result

Nothing in this restructure was allowed to touch a computed value. `python -m src.report` was
re-run afterwards and `git diff` reports **no change** in `data/processed/results.json` or in
any of the five figures. 219 tests pass, including the sweep in `tests/test_documents.py` for
statistic-shaped literals — the new §4.4 table and every figure quoted in the new abstract are
bound to tokens, not typed.

> One note for whoever reads a raw `git status` here. `results.json` will show as modified
> after any report or test run, at 4,372 bytes against the blob's 4,173 — exactly its 199
> newlines. That is the CRLF normalization documented in step 2, not a moved result.
> **`git diff` is the authority, not `git status`, and not a byte count.**

## Open, in the order to tackle it

### 1. Review the arithmetic — scoped, not whole-repo ✅ done 2026-08-31

**Outcome: five findings, all nit severity, all fixed. No published number moved.** Verified
rather than asserted: `python -m src.report` was re-run after the fixes and `git diff` reports
no content change in `data/processed/results.json`, `figures/` or either built manuscript.

The five, and where they went:

| finding | fix |
|---|---|
| `age_adjusted_rate` inner-joins after normalizing weights — a band on one side only yields a downward-biased partial sum | guard, plus the root-cause fix below |
| `kitagawa` intersects the two years' bands without renormalizing shares | guard, same commit |
| `PER` imported and unused in `excess.py` and `decomposition.py` | removed |
| `excess_mortality` declared `by_age` and `standard_pop` and read neither | removed, four call sites updated |
| `excess.py` docstring described a conversion the code does not perform | docstring corrected |

**The root cause sat outside the reviewed files.** `loader.load_deaths_by_age` checked that the
age-band set was a *subset* of `AGE_GROUPS`, never that it was complete — and a missing band is
not a missing *value*, so `_require_complete` saw nothing wrong. The completeness guarantee did
exist, but only in `fetch.assert_population_identity` and `fetch.assert_annual_identity`, which
run on promotion rather than on load; any path reaching the CSVs without `promote()` was
unguarded. That is now refused at the loader, for `deaths_by_age` and `covid_deaths_by_age`
alike, and the two guards in `rates.py` and `decomposition.py` are defence in depth rather than
the only defence.

Worth keeping: **neither join defect could have been caught by a test on the output.** The
Kitagawa additivity identity holds just as exactly over biased shares as over correct ones, so
the invariant this suite leans on hardest is blind to that failure by construction.

#### What the scoping cost, measured against what it predicted

The note below predicted that a scoped review buys depth on the arithmetic and pays for it in
coverage of the data path. Both halves came true, and the price was paid in a specific way
worth recording:

- **The review got a fact wrong because of the scope.** It reported that `excess_mortality`
  "has no callers in the repo — this is fresh API surface being introduced by this PR." There
  are four (`report.py`, `treatments.py`, `test_excess.py`, and two notebook cells). `report.py`
  was not on the branch, so the reviewer could not see it. The finding was right; its reasoning
  about blast radius was wrong.
- **It overstated exposure on both join findings**, because `fetch.py`'s identity assertions
  were not in scope either. It could not know that the committed data satisfies them, so it
  could not tell a live defect from a latent one. Both were latent.

Neither is a fault in the review. Both are the arithmetic of reviewing three files instead of
sixty-nine, and the right response is the one taken here: treat a scoped review's claims about
*the rest of the repository* as unverified, and check them against the repository before acting.
A reviewer that cannot see `report.py` cannot be wrong about `report.py` in a way that is its
own fault.

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

`fetch.py`, `census.py`, `vintage.py` and `treatments.py` are **not** reviewed by this pass and
remain unreviewed. They are left for future PRs whose diffs are small enough for a review to
mean something, rather than being swept into one pass that would skim all of them. Note what
this does and does not buy: the review covers the arithmetic, not the data path that feeds it.

`loader.py` is a partial exception after the fact — the review did not read it, but its
completeness hole was found by following a finding upstream, and that one function is now
guarded and tested. The rest of the module remains unreviewed.

`review-base` and `review-arithmetic` were deleted once the findings were in. They existed to
be diffed, never merged: the parent shared no history with `main` and the files on them were
copies of files `main` already tracks. Recreating an equivalent pair is a two-command job if
another scoped review is wanted — see the commit that introduced them for the plumbing.

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

**A second phantom diff, unrelated to figures and already live.** `paper/manuscript_built.md`
and `paper/public_health_policy_built.md` show as modified after any `python -m pytest` run,
because `tests/test_documents.py` calls `report.build_document()` and that writes the files as
a side effect. `git diff` then reports *no* content change. The explanation is line endings:
`.gitattributes` stores these as LF, Python's `write_text` emits CRLF on Windows, so the
working file differs from the blob by one byte per line while normalizing to something
identical. `data/processed/results.json` behaves the same way after a report run — it came
back 4,372 bytes against the blob's 4,173, which is exactly its 199 newlines.

The rule that resolves it: **`git diff` is the authority, not `git status`, and not a byte
count.** Status flags the file; diff normalizes and shows the truth. `git checkout -- <path>`
discards the churn. This is worth knowing before a release, because it is indistinguishable at
a glance from a real change and it is *always present* on Windows after a test run.

Note this is the benign half of a hazard the README already records the dangerous half of:
where a recorded SHA-256 is the artifact (the Census files, the WONDER exports), the same
normalization moves bytes underneath the hash, which is why those paths carry `-text` in
`.gitattributes`. Nothing here has a recorded hash, so nothing here is at risk.

### 3. Create the GitHub repository and push ✅ done 2026-08-31

**Pushed.** `origin/main` carries all 27 commits at `4e12f99`, 69 files, tracking configured.
Verified against the remote rather than assumed: `git ls-remote` shows `refs/heads/main` and
nothing else — no tags, and neither scaffolding branch. `figures/` and
`data/processed/results.json` are present, and no ignored artifact reached the remote.

Two attempts failed silently first, which is worth recording because the failure mode gives no
output at all. Git Credential Manager had **no stored GitHub credential**, so `git push` blocked
on an interactive sign-in that a non-interactive shell cannot answer: it printed nothing and
hung until timeout, rather than erroring. Both `git ls-remote` returning zero refs and the
absence of a `[branch "main"]` section in `.git/config` are reliable ways to tell "never
pushed" from "pushed and something went wrong." The fix was signing in from a real terminal.

Authorship metadata was declared before tagging rather than left to inference: GitHub's
Contributors panel had read the AI co-author trailer as the sole contributor, and Zenodo pulls
creator metadata from GitHub when it mints a DOI. `CITATION.cff` and `.zenodo.json` now state
it explicitly, so the citation record says what was declared rather than what was guessed.

### 3b. Superseded — how the repository was created

Public. **`origin` is configured** —
`https://github.com/terryfinberg/mortality-analysis.git` — and **nothing has been pushed.**
`main` is the only branch and the one GitHub should treat as default; it is already named to
match, so nothing needs fixing in settings afterwards. The scaffolding branches from step 1
are deleted, so there is nothing left that must be kept back from a push.

Adding the remote does not create the repository. If it does not already exist on GitHub, the
first `git push -u origin main` fails on authentication rather than saying so plainly; create
it there first, empty, with no README, licence or `.gitignore` — GitHub's initialisers would
put a commit on the remote that this history does not contain.

### 4. Connect Zenodo — **BEFORE tagging** ✅ done, before the Release

The toggle was armed while there was still no Release, which is the state this step was
written to produce: an armed toggle with no Release makes no DOI and no record, so it could
not be done too early. The warning below is kept rather than deleted, because it is the part
that costs a version number when it is got wrong, and the next release has to get it right
too.

> **Order matters and getting it wrong costs a version number.** Zenodo archives only
> Releases created *after* the repository toggle is switched on. **A pushed tag is not a
> Release.** Enable the Zenodo integration for the repository first, then create the Release
> in the GitHub UI. Tagging first and connecting after means the DOI never appears, and the
> fix is cutting a throwaway v0.1.1 purely to trigger it.

### 5. Tag `v0.1.0`, create the Release, mint the DOI ✅ done 2026-09-02

Executed in the order the step prescribed, which was the whole of the step:

1. **Zenodo toggle on** (step 4), while there was still no Release for it to archive.
2. **`CITATION.cff` fixed, then tagged.** `date-released:` went to `"2026-09-02"` in
   `0b4645c`; `version:` was already `0.1.0` and needed no change. The annotated tag
   `v0.1.0` points at that commit, so the file *at the tag* describes the release that
   exists. Commit and tag were pushed together.
3. **Release created in the GitHub UI**, which is the event Zenodo watches. Two DOIs came
   back, a version DOI and a concept DOI; both are in the banner and in step 6.

The DOI is permanent and the archive is fixed at `v0.1.0`. Everything after it — this
document, the DOI insertions — is a post-tag commit on `main`, which is normal and does not
disturb what was archived. No re-tag.

Still worth reading before anything is posted: step 7 below, on the preprint licence. That
decision is also effectively irreversible, and it is independent of the DOI.

### 6. Put the DOI everywhere it was pending ✅ done 2026-09-02

The step was written as "two places, not one": a DOI recorded in only one of them produces a
repository whose "Cite this repository" button disagrees with the preprint, which is worse
than one that omits it in both. Grepping for the pending language found five places, not
two.

| file | what it now carries |
|---|---|
| `CITATION.cff` | `doi:` = version DOI, `identifiers:` = concept DOI described as such. That split is the CFF convention and it records both without ambiguity |
| `paper/manuscript.md` | a **Data availability** declaration naming the version DOI, the concept DOI and the development repository separately |
| `paper/medrxiv_submission.md` | the version DOI replaces the placeholder at the top, with the reason it is the version and not the concept DOI |
| `README.md` | both DOIs under "License and citation", with which to cite when |
| `UAT_CHECKLIST.md` | the two release items closed, with the DOIs recorded against them |

`.zenodo.json` needs no DOI. Zenodo mints the DOI *from* that record, so a DOI written into
it would be describing its own output.

**The version DOI leads wherever a result is cited.** A reader following a DOI out of the
manuscript should reach the archive that produced the numbers in it, not a later release
whose numbers may have moved. The concept DOI is the one to cite for the project as an
ongoing thing, and it is labelled that way rather than left for a reader to infer.

`CITATION.cff`'s `orcid:` field was commented out until an iD existed, rather than filled
with a dummy, because an ORCID-shaped string that resolves to nobody is worse than an absent
field — it looks checkable and fails only for whoever tries. **Registered 2026-09-02:**
`0009-0006-1598-4200`, now in `CITATION.cff` (as the full `https://orcid.org/…` URL, which
is the form CFF wants), `.zenodo.json` (bare, which is the form Zenodo wants) and the
manuscript's Declarations. The checksum was verified before it was written anywhere.

### 8. Cut `v0.1.1` ✅ done 2026-09-03 — DOI `10.5281/zenodo.22267191`

`v0.1.0` is archived and permanent and its manuscript is not the manuscript anyone should
read. The deposit predates the whole Declarations section bar the AI disclosure, carries the
abstract wording that permits a false per-band reading, has no band-level §4.1, names figures
as prose filenames in the order 1, 5, 3, 4, and archives `fig2` uncited. A preprint citing a
DOI that resolves to that is worse than one citing nothing.

**What has to be true before the tag.** Each is checkable, and the point of listing them is
that the tag is the last moment any of them can be fixed:

1. `git status` clean, `main` level with `origin/main`.
2. `python -m src.report` run, and `git diff` clean on `data/processed/results.json` and
   `figures/` — a tag whose archive disagrees with its own committed results is the defect
   this release exists to fix.
3. All tests pass.
4. **No file names this release's version DOI.** It does not exist yet. See the banner.
5. `CITATION.cff` says `version: 0.1.1` and `date-released:` is the actual tag day, in the
   commit the tag points at, so the file never describes a release that does not exist.
6. The manuscript's release string comes from `{{RELEASE_VERSION}}`, not typed.

**Executed in this order, and the order is the whole of it.**

1. Commit every one of the above **together**. The tag points at one commit and every file in
   it has to describe `v0.1.1`.
2. Tag `v0.1.1`, annotated, on that commit. Push commit and tag.
3. **Build the submission artifacts from the tagged tree, now** — `python -m src.export
   --both`. This is the step with a trap in it: do it after step 5 and the PDF you post
   carries a DOI line the archived manuscript does not, and the preprint and the deposit
   diverge again, which is exactly how `v0.1.0` went wrong.
4. Create the Release in the GitHub UI. Zenodo archives it and mints `v0.1.1`'s version DOI.
5. **Post-tag**, add that version DOI to `CITATION.cff` under `identifiers:` with a
   `description` naming the release. Commit and push. The archive is untouched; this is for
   whoever reads `main` later. **Done** — `10.5281/zenodo.22267191`, and `dist/` was
   deliberately *not* rebuilt afterward.
6. Post the preprint using the PDF built at step 3. ← superseded by step 9

Steps 1 through 5 are done. The preprint was never posted from this tag; step 9 supersedes
it.

### 9. Cut `v0.1.2` — the typography the source never contained

**The defect.** `v0.1.1`'s PDF sets `2023's` as `2023′s`, with a U+2032 PRIME where the
apostrophe belongs, in the abstract, in §4.4 and in §4.5. It is not a typo in the
manuscript. `paper/manuscript.md` has held an ordinary ASCII apostrophe throughout, and no
edit to it could have fixed this.

**Where it comes from, because the mechanism is the whole lesson.** Pandoc's reader
resolves `'` to U+2019 in the AST. Pandoc's *typst writer* then normalises that back to an
ASCII apostrophe, on the assumption that typst will re-smarten it. Typst's rule is not
pandoc's: an apostrophe following a digit becomes a prime, because `5'11"` is the case that
rule was written for. So `2023's` came out wrong and `NVSR's` came out right, in the same
paragraph, from identical source characters. The fix is `--to typst-smart` in
`build_pdf()`, which turns the smart extension off in the *writer* so it emits real
punctuation, and makes pandoc's template emit `#set smartquote(enabled: false)` so typst
renders what it is given.

**Why it survived two readers.** A prime is not illegible. It is *almost right*, and the
eye supplies the apostrophe it expects. Both the author and Claude read that page.

**What guards it now**, in `tests/test_export.py` under Typography:

- `test_the_manuscript_uses_only_allowed_characters` — an explicit allowlist of the
  non-ASCII characters `manuscript.md` and `manuscript_built.md` may contain, run over
  every line. An allowlist and not a blocklist: the character that got through was one
  nobody had thought to look for.
- `test_the_typst_path_disables_the_writers_smart_extension` — **this is the one that
  would have caught the prime, and the allowlist is not.** The source was innocent; the
  build was not. A test over the source file alone would have passed while the PDF stayed
  wrong, which is worth remembering the next time a fix looks like it belongs in the
  prose.
- `test_the_typst_source_carries_real_punctuation` — the mechanism on real pandoc output:
  the writer must emit U+2019, *and* the document must tell typst to leave it alone.
  Either alone is insufficient.

Both were verified by reintroducing the bug and watching them fail.

**The em dash is gone from the manuscript**, all twelve of them, and is deliberately
absent from the allowlist. House style, not a typo, so nothing else would have caught it
returning. Seven single dashes became a period, a colon or a comma; four paired
parentheticals became parentheses. `paper/manuscript.md` is now pure ASCII.

**`dist/abstract.txt` is new.** medRxiv's abstract field accepts ASCII punctuation only
and rejects a paste without naming the character it objected to; Demographic Research's
form is expected to behave the same way. `src/export.py --abstract` writes the abstract as
plain ASCII with markdown emphasis stripped, ready to paste. Every substitution is spelled
out in `ASCII_PUNCTUATION` and an unmapped character is an **error**, not a silent
deletion — a dropped character leaves a sentence that still reads plausibly, which is how
a wrong abstract gets submitted.

**Executed in the same order as step 8, and for the same reason.** The trap is unchanged:
build `dist/` from the tagged tree *before* recording the new version DOI, or the posted
PDF carries a DOI line the archived manuscript does not.

`results.json` and all five figures are byte-identical to `v0.1.1`. 219 tests pass.

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
