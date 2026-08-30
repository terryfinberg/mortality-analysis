# User acceptance testing

Work through these in order. Each section has a pass condition. If a section fails, stop and
resolve it before continuing; later sections assume earlier ones passed.

---

## Section 1: Environment

- [ ] `.\bootstrap.ps1` (Windows) or `./bootstrap.sh` completes without error
- [ ] `.venv` directory exists
- [ ] `python -m pytest` reports **143 passed**
- [ ] Jupyter kernel "Python (fragile-equilibrium)" appears in `jupyter kernelspec list`

**Pass condition:** 143 tests pass.

`data/raw/` is now populated from the committed WONDER exports, so the old
"repo ships empty" guard is gone. The check that replaced it is
`test_populated_data_is_still_unverified`: if that **fails**, someone has written into
`verified_by` without doing the verification, which is the failure this project exists to
prevent. Find out who and on what basis before proceeding.

---

## Section 2: Data population

This is the section that takes real time. Budget two to three hours.

Values reach the CSVs one of two ways: you type them in, or `src/fetch.py` retrieves them
and `promote()` copies them across. Either way, **you** fill `verified_by` and
`verified_date`, and only for rows where you personally opened the source and checked.

### The three provenance columns

| Column | Meaning | Who may write it |
|---|---|---|
| `source_type` | `api` if fetched, `manual` if typed in | either |
| `fetched_from` | `fetch:<dataset_id>@<access_date>` | `src.fetch.promote()` |
| `verified_by` | a person checked this value against the cited source | **a human, only** |

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

- [ ] `data/raw/us_annual_deaths.csv`: from NVSR "Deaths: Final Data" Table B, per year
- [ ] `data/raw/us_population.csv`: from Census Bureau NST-EST vintage files, July 1 column
- [ ] `data/raw/deaths_by_age.csv`: from CDC WONDER Query 1, collapsed to six age groups
- [ ] `data/raw/covid_deaths_by_age.csv`: from CDC WONDER Query 3, underlying cause U07.1

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
- [ ] Push to GitHub, tag a release, connect Zenodo, mint the DOI
- [ ] Put the DOI into `paper/medrxiv_submission.md`

---

## Section 7: Corroboration plan

Corroboration is a **separate claim from attestation**. Attestation says a value faithfully
reproduces the committed export it came from, and is achievable for all 150 rows today.
Corroboration says an *independent* NCHS publication reports the same figure. It is not
uniformly available, and this plan is built around what exists rather than around one source
assumed to cover every year. See **Provenance, attestation and corroboration** in `README.md`.

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

- [ ] **2010–2022 (13 years).** Compare `us_annual_deaths.deaths` against Table B of each
      year's report. Record e.g. `NVSR 74-4, Table B` in `corroborated_against`.
- [ ] **Confirm the Table B basis on the first year you check.** Table B should be the total
      including deaths with age not stated, which is what `deaths` holds — our `deaths` is
      `sum(six bands) + not_stated`, and `not_stated` runs 57–163 a year. If Table B turns out
      to exclude them, every subsequent comparison inherits the error. Settle it once, on one
      year, against the actual table.
- [ ] **2023 — try NVSR 74-11 first.** One document covering 2010–2023 from the same agency is
      a better corroboration instrument than thirteen separate reports: a single consistent
      editorial basis, and it would corroborate the *shape* of the series, not just its
      endpoints.
- [ ] **Before relying on 74-11, check comparability. This is the one that can quietly go
      wrong.** It is keyworded to crude death rate, so it corroborates a *rate*, not a count,
      and a rate is only comparable if the denominator is. Our crude rates use WONDER's own
      per-year population, each year at the vintage current when it was first estimated (see
      `docs/denominator-methods.md`, discontinuity 1). A trends report spanning 2010–2023 and
      published in 2025 may well have rebased every year onto **one** consistent vintage,
      which is a deliberate and defensible choice — and would make its rates not directly
      comparable to ours. Establish which before recording anything:
    - [ ] Read 74-11's methods for its population source and vintage
    - [ ] If it rebases, do **not** record it as corroboration of our rates. Either compare
          counts instead if it publishes them, or note it as a related-but-different series
    - [ ] If it uses the same per-year vintage chain, it corroborates 2010–2023 in one
          instrument, and that is worth more than the individual Table B checks
- [ ] **2023 fallback.** If 74-11 is not comparable, try NVSR 74-10 (*Deaths: Leading Causes
      for 2023*) for a total, and record whichever you actually used.
- [ ] **2024 — leave blank, and say so in the paper.** There is no independent published
      source. Do not fill this column from WONDER, a VSRR provisional release, or a press
      figure: each would either restate the value's own source or corroborate it against
      something weaker than itself. 2024 rests on the committed export alone, and the
      manuscript should state that in those words.
- [ ] Record the achieved count in the manuscript — "N of 15 annual totals corroborated
      against an independent NCHS publication" — rather than a phrasing that implies fifteen

**Pass condition:** you would be comfortable with a reviewer pulling any single number in the
paper and tracing it to a source document.

That is the actual standard. Everything above is in service of it.
