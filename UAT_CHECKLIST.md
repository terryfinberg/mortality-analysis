# User acceptance testing

Work through these in order. Each section has a pass condition. If a section fails, stop and
resolve it before continuing; later sections assume earlier ones passed.

---

## Section 1: Environment

- [ ] `.\bootstrap.ps1` (Windows) or `./bootstrap.sh` completes without error
- [ ] `.venv` directory exists
- [ ] `python -m pytest` reports **209 passed**
- [ ] Jupyter kernel "Python (fragile-equilibrium)" appears in `jupyter kernelspec list`

**Pass condition:** 209 tests pass.

`data/raw/` is now populated from the committed WONDER exports and attested, so the old
"repo ships empty" guard is gone. Two checks replaced it:
`test_promotion_cannot_write_an_attestation` (the durable one — no machine path can write
`verified_by`, whatever the CSVs currently hold) and
`test_the_committed_data_is_signed_and_loads_strictly`. If the first **fails**, something in
the fetch path has gained the ability to sign, which is the failure this project exists to
prevent.

---

## Section 2: Data population

This is the section that takes real time. Budget two to three hours.

Values reach the CSVs one of two ways: you type them in, or `src/fetch.py` retrieves them
and `promote()` copies them across. Either way, **you** fill `verified_by` and
`verified_date`, and only for rows where you personally opened the source and checked.

### The four provenance columns

| Column | Meaning | Who may write it |
|---|---|---|
| `source_type` | `api` if fetched, `manual` if typed in | either |
| `fetched_from` | `wonder-export:<filename>@sha256:<hash>` | `src.fetch.promote()` |
| `verified_by` | a person checked this value against the cited export | **a human, only** |
| `corroborated_against` | a separate publication reports the same figure (not independent — see Section 7) | **a human, only** |

Provenance is not attestation. `fetched_from` records where bytes came from; it cannot tell
you the fetch pulled the right series with the right filter. Only `verified_by` says a person
confirmed the number belongs here, and only `verified_by` satisfies the loader's strict mode.

**Consequence to expect:** after a successful fetch and promote, the files will be fully
populated and `python -m src.report` will still raise `UnverifiedDataError`. That is correct.
Automation got the numbers into place; it did not sign them off. Do not work around it by
pasting a value into `verified_by` — that is the exact failure this repository exists to
prevent.

If `promote()` changes a value you had already signed off on, it clears that row's
`verified_by`. Re-check the new value and re-sign.

All four are populated from the committed WONDER exports by
`python -m src.fetch --promote --write`. NVSR and Census are **corroboration** sources, not
value sources — see Section 7.

- [ ] `data/raw/us_annual_deaths.csv`: export Total rows, as `sum(six bands) + not_stated`
- [ ] `data/raw/us_population.csv`: export Population column, summed across the bands
- [ ] `data/raw/deaths_by_age.csv`: WONDER Query 1, collapsed to six age groups
- [ ] `data/raw/covid_deaths_by_age.csv`: WONDER Query 3, underlying cause U07.1

If you fetched rather than typed:

- [ ] `python -m src.fetch --reconcile` run, and `data/processed/reconciliation_<date>.md`
      reviewed cell by cell rather than skimmed
- [ ] every promoted row has `source_type` = `api` and a `fetched_from` string
- [ ] `verified_by` is blank on every row you have not personally checked

**Cross-checks before you continue.**

The first is an **exact identity**, not a tolerance. It must hold to the death:

- [ ] For each year: `sum(deaths across age groups)` + `not_stated` == `deaths` in
      `us_annual_deaths.csv`. Exactly. No margin.

      WONDER does not distribute "Not Stated" deaths among age groups, so the six bands fall
      short of the published annual total by exactly the Not Stated count — around 130 deaths
      a year, about 0.005 percent. That is why this is an identity and not a percentage check:
      a threshold loose enough to catch a real collapse error is roughly a hundred times wider
      than this gap, so a systematic shortfall would reconcile clean forever while being wrong
      every single year. **A tolerance absorbs systematic bias; an identity cannot.**

      `python -m src.fetch --reconcile` asserts this and raises on violation.

- [ ] For each year: `sum(population across age groups)` == `population` in
      `us_population.csv`. Exactly. No margin.

      `us_population.csv` is sourced from the same WONDER export as the age bands, so both
      sides of this are the same numbers and any difference is an arithmetic defect, not a
      vintage difference. This used to be a 0.5 percent tolerance because the denominator came
      from Census; it does not any more.

- [ ] For each year, our computed crude rate equals WONDER's published `Crude Rate` column to
      one decimal place.

      This is the strongest check in the file, and the only one that reaches outside the
      repository. WONDER computed that rate itself, from the same counts, without reference to
      our code. Because our denominator is now WONDER's denominator, agreement is required
      rather than hoped for, and disagreement localizes the defect to deaths, population, or
      the rate arithmetic. `python -m src.fetch --reconcile` asserts it and raises on
      violation.

The rest are genuine tolerances, because they compare quantities that are not defined to be
equal:

- [ ] COVID deaths in any year do not exceed total deaths in that year.
- [ ] No year has population moving by more than 2 percent from the prior year.

> **The 2017/2018 seam is unaffected by any of this.** Moving the denominator to WONDER
> removes the *cross-source* mismatch; it does not remove the bridged-race to single-race
> vintage change at 2017/2018, which is internal to WONDER. File 4 still measures it.

**Pass condition:** all four files complete, all cross-checks within tolerance.

---

## Section 3: Loader

- [ ] `python -c "from src import loader; d = loader.load_all(); print(d.years)"` prints the
      year range with no exception
- [ ] `python -c "from src import loader; print(loader.load_standard_population().sum())"`
      prints `1000000`

**Pass condition:** loader accepts the data in strict mode.

If you get `UnverifiedDataError`, some row lacks a `verified_by` entry. Fill it in if you
checked it. Do not fill it in to make the error go away.

---

## Section 4: Analysis run

- [ ] `python -m src.report` completes without error
- [ ] `data/processed/results.json` exists
- [ ] Five PNGs exist in `figures/`
- [ ] `paper/manuscript_built.md` exists and contains **no** `{{TOKEN}}` strings

Check: `grep -c '{{' paper/manuscript_built.md` should return `0`.

**Sanity review of results.json.** These are judgment checks, not automated:

- [ ] Age-adjusted rates are lower than crude rates in later years (expected in an aging
      population), if reversed, check the standard population weights
- [ ] The 2010-2019 age effect is positive (population aged) and the rate effect is negative
      (mortality improved). If both have the same sign, something is wrong with the age-band
      mapping.
- [ ] Rate effect plus age effect equals total change, to the printed precision
- [ ] Excess deaths for 2020 and 2021 are large and positive; for 2010-2019 they are small
      and roughly centered on zero
- [ ] The share of COVID deaths aged 65+ is a large majority

**Pass condition:** pipeline runs clean and the sanity checks hold.

An implausible result here is more likely a data-entry error than a code error. The code is
tested; the data is hand-entered.

---

## Section 5: Notebook

- [ ] `jupyter lab` opens
- [ ] `notebooks/01_walkthrough.ipynb` runs top to bottom with the fragile-equilibrium kernel
- [ ] Numbers printed in the notebook match `data/processed/results.json`

**Pass condition:** notebook and pipeline agree. They call the same modules, so disagreement
means a stale kernel; restart and rerun.

---

## Section 6: Pre-submission

- [ ] Work the corroboration plan below and record what you actually achieved
- [ ] Confirm the `status` column still matches its source. All 15 years are currently
      `final`: the grid takes 2018–2024 from the final Single Race database, not from VSRR,
      so no year is provisional. `promote_from_exports()` derives this from
      `ExportSpec.provisional` rather than it being typed in — if a provisional export is
      ever added, the flag follows the source automatically
- [ ] Run the excess-mortality analysis with at least two alternative baseline windows and
      record how much the headline figure moves
- [ ] Read the manuscript limitations section against what you actually did and add anything
      missing
- [ ] Fill `verified_by` and `verified_date` for every row, against the cited source
- [x] Push to GitHub, tag a release, connect Zenodo, mint the DOI — concept DOI
      10.5281/zenodo.22263667. `v0.1.0` (2026-09-02) is version DOI
      10.5281/zenodo.22263668; later releases add theirs to `CITATION.cff` after archiving
- [x] Put the DOI into `paper/medrxiv_submission.md`, `CITATION.cff`, `README.md` and the
      manuscript's Declarations

---

## Section 7: Corroboration plan

Corroboration is a **separate claim from attestation**. Attestation says a value faithfully
reproduces the committed export it came from, and is achievable for all 150 rows today.
Corroboration says a separate NCHS publication reports the same figure. It is not uniformly
available, and this plan is built around what exists rather than around one source assumed to
cover every year. See **Provenance, attestation and corroboration** in `README.md`.

> **Not independent confirmation.** NVSR and WONDER are both NCHS products over the same
> mortality file and the same Census-derived denominators. This establishes that the query
> returned what NCHS published in its report of record. It is not evidence that NCHS is
> correct. The full statement is in `docs/denominator-methods.md`, "What the NVSR
> corroboration does and does not establish" — read it before describing this work to anyone,
> because "independent" is the word that comes out by reflex and it is wrong.

**Status: 13 of 15 done.** 2010–2022 recorded; 2023 and 2024 have no published report.
`tests/test_nvsr_corroboration.py` pins all thirteen figures and recompares them, so the
column is a check rather than a claim.

Blank `corroborated_against` means **not corroborated**. It does not mean corroboration
failed. Leave it blank rather than reaching for a weaker source to fill the column.

### What is available, by year

| years | source | status |
|---|---|---|
| 2010–2022 | "Deaths: Final Data for [year]", Table B | Published. 2021 is NVSR 73-8, 2022 is NVSR 74-4; look each earlier year up in the index |
| 2023 | NVSR 74-11 *Trends in Births and Deaths: United States, 2010–2023*, or NVSR 74-10 *Deaths: Leading Causes for 2023* | Published, but **neither is Table B** — see the comparability check below |
| 2024 | **none** | No independent published source exists |

Index: <https://www.cdc.gov/nchs/products/nvsr.htm>. "Deaths: Final Data for 2023" is due —
the lag runs about three years — but not out as of 2026-08-30.

### The basis question — RESOLVED, 2010 done

**NVSR totals include age-not-stated deaths. Compare against the `deaths` column, not
`deaths − not_stated`.** Settled from NVSR Vol. 61 No. 4 (*Deaths: Final Data for 2010*),
Table 10, footnote 1, read directly on 2026-08-30: *"Figures for age not stated included in
'All ages' but not distributed among age groups."* Same convention as WONDER. The band-sum
figure 2,468,309 appears nowhere in that document, which is the negative check on the same
point.

2010 is corroborated three ways and recorded as
`NVSR Vol. 61 No. 4, Table B (total deaths, crude rate); Table 10 (age distribution)`:

| what | NVSR | ours |
|---|---|---|
| Table B, all causes | 2,468,435 | `us_annual_deaths.deaths` |
| Table B, crude death rate | 799.5 | our computed rate, and WONDER's published column |
| Table 10, by age | 24,586 / 4,316 / 5,279 / 29,551 / 42,259 / 70,033 / 183,207 / 310,802 / 407,151 / 625,651 / 765,474, plus 126 not stated | the WONDER export, cell for cell across all eleven bands |

The crude-rate agreement holds for all thirteen corroborated years, not just 2010, and it is a
finding in its own right: neither publication prints the other's population, so deaths matching
exactly plus rates matching to one decimal means the **denominators agree** to within the
rounding of the rate. That is inference about the denominator, which is why
`us_population.csv` stays unmarked — see the note under 2011–2022 below.

> ### ⚠ Do NOT compare the age-adjusted rate
>
> Table B also gives an age-adjusted rate — **747.0** for 2010. **It is not comparable to
> ours.** NCHS standardises over its eleven age groups; this analysis collapses to six. Two
> direct standardisations over different groupings of the same standard population do not
> agree, and the difference is a property of the grouping, not a discrepancy in the data.
>
> This is the obvious next thing to try after Table B's total and crude rate both match, which
> is exactly why it is called out here. A mismatch found this way would look like a real
> finding and would not be one. Corroborate counts and crude rates; leave the adjusted rate
> alone.

- [x] **2011–2022 (12 years). Done 2026-08-30.** All twelve match Table B exactly on total
      deaths, and our computed crude rate matches NVSR's published rate to one decimal in
      every one. Each figure appears twice per report — narrative sentence and Table B — and
      the two agree. Recorded per year with its own volume and issue.

      `us_population.csv` is deliberately **not** marked. Recovering the denominator by
      dividing deaths by the published rate is an inference, not a document stating a figure,
      and that column holds only the latter. The inference itself is recorded as a finding in
      `docs/denominator-methods.md` and asserted by
      `test_rate_agreement_implies_the_denominators_agree`.
- [x] **2023 — NVSR 74-11 checked and used, for the COUNT ONLY. Done 2026-08-30.**

      Page 10 gives 3,090,964 for 2023, matching our export. It also reproduces 2022's
      3,279,857 (agreeing with NVSR 74-4) and 2010's 2,468,435 (agreeing with NVSR 61-4),
      which is a useful internal consistency check on the report itself.

      Recorded with `corroborated_measures = count`, not `count,rate`. The column now
      distinguishes the two, because 2023 is a weaker claim than 2010–2022 and should not
      read as though it were the same.
      **Its rates are NOT comparable to ours, for four separate reasons.** The comparability
      check was the thing flagged as most likely to go quietly wrong, and it did not survive
      it. From 74-11's methods, verbatim:

      > "Population data for 2010 are based on April 1 census counts and for 2011-2019, July 1
      > postcensal estimates are based on the 2010 census. Population data for 2020 are based
      > on April 1 population estimates and for 2021, 2022, and 2023, July 1 postcensal
      > estimates are derived from a blended base that incorporates the 2020 census, Vintage
      > 2020 estimates, and 2020 Demographic Analysis estimates."

      and its table note: *"Rates are based on populations enumerated as of April 1 for 2010,
      estimated April 1 for 2020, and July 1 for all other years."*

      1. **2020 is on an April 1 basis** in 74-11; ours is July 1 from Vintage 2020. A
         different measurement basis at the pivotal year of the series.
      2. **2021–2023 sit on a blended base**, not the per-year vintage chain WONDER carries
         and this analysis inherits.
      3. **Its rates are per 1,000 to one decimal**, so one printed digit is worth 100 per
         100,000. It could not discriminate our 922.9 from anything between roughly 915 and
         925 even if the denominators did match.
      4. **Its own methods say the 2020 rates were revised** and may differ from those in
         *Deaths: Final Data for 2020* — see the separate finding below.

      Reason 3 alone would make the comparison uninformative; reasons 1 and 2 would make it
      wrong. Recording it as rate corroboration would have manufactured agreement out of a
      measure too coarse to disagree.

> **A finding, not a limitation.** Reason 4 is the valuable part. NCHS has published two
> different crude death rates for 2020 in two of its own reports and named denominator
> rebasing as the cause. That is an agency-published instance of this project's denominator
> argument, which until now rested on our own measurement. It is written up as finding 4 in
> `docs/denominator-methods.md` and reported in manuscript section 4.4.
- [ ] **2024 — leave blank, and say so in the paper.** There is no independent published
      source. Do not fill this column from WONDER, a VSRR provisional release, or a press
      figure: each would either restate the value's own source or corroborate it against
      something weaker than itself. 2024 rests on the committed export alone, and the
      manuscript should state that in those words.
- [ ] Record the achieved count in the manuscript — "N of 15 annual totals corroborated
      against an independent NCHS publication" — rather than a phrasing that implies fifteen

### Reference list, 2011–2022

Confirmed against the CDC index on 2026-08-30. Prefix each path with
`https://www.cdc.gov/nchs/data/nvsr/`.

| year | NVSR | path |
|---|---|---|
| 2011 | 63-3 | `nvsr63/nvsr63_03.pdf` |
| 2012 | 63-9 | `nvsr63/nvsr63_09.pdf` |
| 2013 | 64-2 | `nvsr64/nvsr64_02.pdf` |
| 2014 | 65-4 | `nvsr65/nvsr65_04.pdf` |
| 2015 | 66-6 | `nvsr66/nvsr66_06.pdf` |
| 2016 | 67-5 | `nvsr67/nvsr67_05.pdf` |
| 2017 | 68-9 | `nvsr68/nvsr68_09-508.pdf` |
| 2018 | 69-13 | `nvsr69/nvsr69-13-508.pdf` |
| 2019 | 70-8 | `nvsr70/nvsr70-08-508.pdf` |
| 2020 | 72-10 | `nvsr72/nvsr72-10.pdf` |
| 2021 | 73-8 | `nvsr73/nvsr73-08.pdf` |
| 2022 | 74-4 | `nvsr74/nvsr74-04.pdf` |

**These paths are recorded as given and must not be reconstructed from a pattern.** The
convention is inconsistent in three separate ways: underscores before 2018 (`nvsr63_03`) and
hyphens after (`nvsr69-13`), a `-508` accessibility suffix on 2017 through 2019 but not on
2020 onward, and a directory that tracks the volume rather than the year. Deriving 2018's
path from 2017's gives the wrong filename. This is the same failure that a guessed
`nc-est2019-agesex-res.csv` produced against the Census server — see
`data/raw/census/PROVENANCE.md`.

2010 is not in this table because it is done; its citation is in the CSV.

**Pass condition:** you would be comfortable with a reviewer pulling any single number in the
paper and tracing it to a source document.

That is the actual standard. Everything above is in service of it.
