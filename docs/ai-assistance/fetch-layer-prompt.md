# Prompt for Claude Code: build the live data acquisition layer

> **Historical record. Do not follow these instructions.**
>
> This is the prompt that commissioned `src/fetch.py`, kept for transparency about how that
> module came to exist rather than as a task anyone should now run. **The work it describes is
> done**, and re-running it against the current repository would be destructive.
>
> It also describes a repository state that no longer holds. Where it says the data files are
> empty and the values are meant to be transcribed by hand, that was true when it was written
> and is not true now: the CSVs were populated from four committed CDC WONDER exports and every
> row was attested by a person. See `README.md` for the current state.
>
> Two things in it are worth reading even so, because they became load-bearing constraints in
> the module that resulted: the instruction not to use a dataset identifier recalled from
> training rather than retrieved from a live catalogue response, and the requirement never to
> return a partially parsed result. Both are enforced by tests today.
>
> Moved here from the repository root on 2026-08-31. It read as an active instruction sitting
> next to the README, which is not what a published research repository should present to a
> reader arriving at it.

---

Read these files first, in this order, before writing anything:

- `README.md` for the project's purpose and the reason the data files are empty
- `src/loader.py` for the data contract, especially `IncompleteDataError` and `UnverifiedDataError`
- `data/queries/cdc_wonder_queries.md` for the three queries and the age-band collapse table
- `data/raw/deaths_by_age.csv` and the other three raw CSVs for the exact target schemas
- `tests/conftest.py` to see the fixture style used in this repo

This project analyzes U.S. mortality and is headed for a medRxiv preprint. Its single biggest
credibility weakness right now is that the input values are meant to be transcribed by hand from
published PDFs rather than fetched programmatically. Your job is to remove that weakness by
building a fetch layer, without introducing a worse one in its place.

Build a new module `src/fetch.py` plus supporting files. Requirements:

1. **Discover the data sources; do not assume them.** Query the CDC Socrata catalog at
   `https://data.cdc.gov/api/catalog/v1` to find the NCHS datasets that supply (a) annual deaths
   and population by age group, (b) total annual deaths including provisional years, and
   (c) COVID-19 deaths by age with U07.1 as underlying cause. Print the candidate dataset
   identifiers, titles, update dates, and column schemas you find, and stop there on the first
   run so I can confirm the choice before you build against it. Do not use a dataset ID that you
   recalled from training rather than retrieved from the catalog just now. If you find yourself
   typing an identifier you did not read from a live response, stop and tell me.

2. **Fall back to WONDER only if Socrata cannot supply a series.** If you need it, the XML POST
   endpoint is documented at `https://wonder.cdc.gov/wonder/help/WONDER-API.html`. Note in the
   code that WONDER blocks sub-national detail for confidentiality and that its schema has changed
   without notice in the past. Log the raw response body to `data/raw/fetched/_debug/` on any
   parse failure and raise; never return a partially parsed result.

3. **Cache every response.** Write raw payloads to `data/raw/fetched/<series>_<YYYY-MM-DD>.<ext>`
   before parsing. Reruns on the same day must read the cache rather than re-hitting the API.
   Add a `--refresh` flag to force a new fetch.

4. **Collapse age bands using the mapping in `cdc_wonder_queries.md`.** Handle rows with age
   "Not Stated" or equivalent by summing them into a separate reported total, never by dropping
   them silently. If they exceed 0.1 percent of deaths in any year, emit a warning naming the year
   and the percentage.

5. **Do not write into `data/raw/*.csv`.** Write parsed output to `data/raw/fetched/` only. Then
   produce a reconciliation report comparing, cell by cell, the fetched value against whatever is
   currently in the corresponding raw CSV: year, age group where applicable, current value,
   fetched value, absolute difference, percent difference. Blank current values should be reported
   as "unpopulated" rather than as a zero-to-N difference. Print the report and also write it to
   `data/processed/reconciliation_<YYYY-MM-DD>.md`.

6. **Add a separate, explicit promotion step.** A function `promote(series, dry_run=True)` that
   copies fetched values into the raw CSVs and sets `verified_by` to a machine provenance string
   in the form `fetch:<dataset_id>@<access_date>`, distinct from a human initial. Default it to
   dry run. Do not call it automatically from anywhere. Before you implement this, tell me what
   you think the right semantics are for `verified_by` when the value came from an API rather than
   a person reading a PDF, because that distinction matters to the paper's integrity claim and I
   want to decide it rather than inherit it.

7. **Tests in `tests/test_fetch.py`.** Mock the HTTP layer entirely; no test may touch the
   network. Cover: correct parsing of a representative response, the age-band collapse arithmetic,
   "Not Stated" handling, cache hit and cache miss behavior, and that a malformed response raises
   rather than returning partial data. Match the existing fixture style in `conftest.py`.

8. **Add a `--check` mode** that fetches, reconciles, and exits non-zero if any cell differs from
   the populated raw CSV by more than 0.5 percent. This is so it can run in CI later.

Constraints:

- Do not modify `src/loader.py`, `src/rates.py`, `src/decomposition.py`, or `src/excess.py`. If
  you believe one of them needs to change, stop and explain why instead.
- Do not modify any existing test.
- Do not add a dependency beyond `requests` without asking. The project currently runs on pandas,
  numpy, matplotlib, and pytest.
- Do not populate `data/raw/*.csv` as a side effect of anything.

Definition of done: `python -m pytest` passes with the new tests included, `python -m src.fetch
--discover` prints the candidate datasets, and `python -m src.fetch --reconcile` produces the
report against the current (empty) raw files without error.

Run the tests when you are finished and show me the reconciliation report before we decide
whether to promote anything.

---

## After Claude Code finishes

Bring the reconciliation report back here and we will work through:

- whether the fetched figures match the NVSR published totals, since the two can legitimately
  differ and the published report is the citable authority
- what `verified_by` should mean for machine-fetched values
- whether section 6.1 of the manuscript can be rewritten now that acquisition is reproducible
- whether `--check` should run on a schedule to catch provisional-year revisions
