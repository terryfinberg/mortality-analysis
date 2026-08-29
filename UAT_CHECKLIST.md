# User acceptance testing

Work through these in order. Each section has a pass condition. If a section fails, stop and
resolve it before continuing; later sections assume earlier ones passed.

---

## Section 1: Environment

- [ ] `.\bootstrap.ps1` (Windows) or `./bootstrap.sh` completes without error
- [ ] `.venv` directory exists
- [ ] `python -m pytest` reports **73 passed**
- [ ] Jupyter kernel "Python (fragile-equilibrium)" appears in `jupyter kernelspec list`

**Pass condition:** 73 tests pass on empty data.

If `test_repo_ships_with_unpopulated_data` **fails** at this stage, someone has put values in
`data/raw/`. Find out where they came from before proceeding.

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

- [ ] Re-verify five annual death totals against the NVSR PDFs, chosen at random. Any
      mismatch means re-checking all of them.
- [ ] Confirm provisional years are still labeled provisional and the values match the
      current VSRR release, not an older one
- [ ] Run the excess-mortality analysis with at least two alternative baseline windows and
      record how much the headline figure moves
- [ ] Read the manuscript limitations section against what you actually did and add anything
      missing
- [ ] Add a LICENSE file
- [ ] Push to GitHub, tag a release, connect Zenodo, mint the DOI
- [ ] Put the DOI into `paper/medrxiv_submission.md`

**Pass condition:** you would be comfortable with a reviewer pulling any single number in the
paper and tracing it to a source document.

That is the actual standard. Everything above is in service of it.
