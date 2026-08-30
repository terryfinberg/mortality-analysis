# CDC WONDER query parameters

WONDER does not produce stable, shareable URLs for query results. What follows is the
parameter set needed to reproduce each extract by hand, plus notes for automating it.

**Portal:** https://wonder.cdc.gov/
**Underlying Cause of Death, 1999-2020:** https://wonder.cdc.gov/ucd-icd10.html
**Underlying Cause of Death, 2018-present (expanded):** https://wonder.cdc.gov/ucd-icd10-expanded.html
**Multiple Cause of Death, 2018-present:** https://wonder.cdc.gov/mcd-icd10-expanded.html
**Provisional Mortality Statistics:** https://wonder.cdc.gov/mcd-icd10-provisional.html

---

## Query 1: All-cause deaths and population by age group and year

**Populates:** `data/raw/deaths_by_age.csv` (columns `deaths`, `population`)

| Setting | Value |
|---|---|
| Database | Underlying Cause of Death (use the 1999-2020 database through 2020, expanded 2018-present thereafter) |
| Group Results By | Year, then Ten-Year Age Groups |
| Cause of death | All causes (no restriction) |
| Years | 2010 through most recent available |
| Show | Deaths, Population, Crude Rate |

**Post-processing.** WONDER returns ten-year bands. Collapse to the six groups used here:

| Target group | WONDER bands to sum |
|---|---|
| 0-24 | < 1 year, 1-4, 5-14, 15-24 |
| 25-44 | 25-34, 35-44 |
| 45-64 | 45-54, 55-64 |
| 65-74 | 65-74 |
| 75-84 | 75-84 |
| 85+ | 85+ |

Rows with age "Not Stated" must be recorded separately, not silently dropped. If they exceed
0.1 percent of total deaths in any year, note it in the manuscript's limitations section.

---

## Query 2: Total annual deaths

**Populates:** `data/raw/us_annual_deaths.csv`

Prefer the NVSR "Deaths: Final Data for [year]" PDF, Table B, over WONDER for this series.
The published report is the citable authority and its total is what reviewers will check.
Use WONDER only as a cross-check; if the two disagree, the NVSR figure wins and the
discrepancy is worth a footnote.

For provisional years, use CDC Vital Statistics Rapid Release:
https://www.cdc.gov/nchs/nvss/vsrr.htm

---

## Query 3: COVID-19 deaths by age group

**Populates:** `data/raw/covid_deaths_by_age.csv`

| Setting | Value |
|---|---|
| Database | Multiple Cause of Death (or Provisional Mortality for recent years) |
| Group Results By | Year, then Ten-Year Age Groups |
| **UCD - ICD-10 Codes** | **U07.1 (COVID-19)** |
| Years | 2020 through most recent |
| Show | Deaths |

**Important distinction.** Selecting U07.1 as *underlying* cause counts deaths where COVID-19
was the primary cause. Selecting it under *multiple cause* counts deaths where COVID-19
appeared anywhere on the certificate. These differ materially, typically by 10-15 percent.
This analysis uses **underlying cause**. Record which you used in the `source_citation` column.

Collapse age bands as in Query 1.

---

## Automating this

WONDER exposes an XML POST API at `https://wonder.cdc.gov/controller/datarequest/D<NN>`,
where `<NN>` identifies the database. It is documented at
https://wonder.cdc.gov/wonder/help/WONDER-API.html.

Two constraints matter before you build against it:

The API blocks queries returning sub-national (state, county) detail for several databases,
on confidentiality grounds. National-level queries of the kind above are generally permitted,
but verify against the current terms rather than assuming.

The response schema has changed without announcement in the past. Any client should log the
raw XML on a parse failure and fail loudly rather than returning a partial result.

**A better first option.** CDC also publishes NCHS mortality datasets through its Socrata
open-data platform at https://data.cdc.gov/, which has a documented, stable REST API and
does not require XML construction. Before writing a WONDER client, search that catalog for
the series you need. Do not rely on a dataset identifier quoted from memory by anyone,
including an AI assistant; query the catalog and confirm the identifier and schema yourself.

---

## The export files (primary path)

WONDER is retrieved **by hand** and parsed from the saved export. This is not a workaround.
The series is frozen history — final data for 2010–2023 will not change — and a WONDER export
carries its complete query parameters in the file footer, so the export file *is* the
reproducibility artifact. A reviewer replays the footer's query and gets the same file. That
is stronger provenance than an XML client aimed at an endpoint whose schema has changed
without notice, and a TSV parser is far more testable.

Save exports to `data/raw/wonder_exports/` with **exactly** these names. `src/fetch.py` routes
on the filename.

**Four exports. None provisional.** 2024 is final in the Single Race database and that
database carries population, so the analysis grid contains no provisional data at any point.

| # | Filename | Database | Years | Cause | Show | Saved query URL |
|---|---|---|---|---|---|---|
| 1 | `allcause_by_age_2010-2017_ucd-bridged.txt` | Underlying Cause of Death, 1999–2020 | 2010–2017 | All causes | Deaths, Population, Crude Rate | |
| 2 | `allcause_by_age_2018-2024_ucd-singlerace.txt` | Underlying Cause of Death, 2018–2024, Single Race | 2018–2024 | All causes | Deaths, Population, Crude Rate | |
| 3 | `covid_u071_by_age_2020-2024_ucd-singlerace.txt` | Underlying Cause of Death, 2018–2024, Single Race | 2020–2024 | **UCD ICD-10 = U07.1** | Deaths | |
| 4 | `wonder_ucd_allcause_2018-2020_bridged_SEAM.txt` | Underlying Cause of Death, 1999–2020 | 2018–2020 | All causes | Deaths, Population, Crude Rate | |

### Saved query URLs

WONDER's **Save** button stores a query and returns a link that re-runs it. Paste each link
into the table above and into `saved_query_url` on the matching entry in `WONDER_EXPORTS`
(`src/fetch.py`) as you run the export.

**This supplements the written parameters; it does not replace them.** A saved query works
only for as long as CDC keeps hosting it. The footer inside the export file works forever and
travels with this repository. A reviewer in five years may find the link dead and the footer
intact, so **do not delete the parameter table because the links look sufficient.**

Nothing in `src/fetch.py` reads `saved_query_url` — no parse, cache key, or validation depends
on it — deliberately, so it cannot quietly become load-bearing.

Files 1–3 are the analysis grid: 2010–2017 bridged-race, 2018–2024 single-race,
non-overlapping, so no year is ever assembled from two databases.

### File 4 is validation only. It never enters the grid.

The grid changes population vintage at 2017/2018 — bridged-race before, single-race after —
and that seam sits **inside the 2010–2019 pre-pandemic baseline window**, which is the
paper's central comparison. File 4 re-reads 2018–2020 under the *old* bridged-race vintage,
so the same years can be differenced against file 2 and the size of the discontinuity
measured directly.

Deaths are the same certificates under either vintage, so deaths should barely move; a deaths
difference above 0.1 percent means the two exports are not the same query. Population is
where a real difference lives, and it propagates into every age-specific rate.

`python -m src.fetch --reconcile` reports the per-year, per-band deltas under a
**Vintage seam** heading, and flags the seam as material above 0.5 percent. If it is
material, the baseline trend fit contains a step, and that belongs in methods rather than in
a reviewer's report. A fitted line through stepped data still looks like a line, which is
exactly why this has to be measured rather than eyeballed.

`src/fetch.py` will **not** merge file 4 into the analysis grid; a test asserts it.

**Annual totals come free.** With *Show Totals* on, files 1 and 2 carry a per-year `Total` row,
which can populate `us_annual_deaths.csv`. The NVSR figure remains the citable authority per
Query 2; treat the WONDER total as the cross-check, and footnote any disagreement.

### Click path

> **Unverified.** `wonder.cdc.gov` returns HTTP 403 to this repository's tooling — an Akamai
> edge block covering CDC's main web properties — so the steps below were written from prior
> knowledge of the interface and could **not** be checked against the live site. WONDER
> renumbers and relabels its request sections between databases and over time. Treat this as
> a sketch to correct against what you actually see, not as a transcript.

1. Open the database page and accept the data-use restrictions.
2. **Organize table layout.** Group Results By `Year`, And By `Ten-Year Age Groups`. Leave
   *Show Totals* checked.
3. **Select location.** Leave at United States. Do not request state or county detail — the
   API and the export both restrict sub-national breakdowns on confidentiality grounds, and
   this analysis is national anyway.
4. **Select demographics.** Ten-Year Age Groups: `All Ages`. Leave sex, race, Hispanic origin
   at their defaults.
5. **Select year and month.** Choose the year range from the table above.
6. **Select cause of death.** All causes for files 1, 2 and 4. For file 3, open
   **UCD – ICD-10 Codes**, search `U07.1`, and select it. Confirm you are in the *underlying*
   cause selector, not multiple cause — see the distinction under Query 3; they differ by
   10–15 percent and the analysis uses underlying.
7. **Other sections** (weekday, autopsy, place of death): leave at defaults.
8. Click **Send**, then on the results page use the **Export** button.

For file 4, run the identical query as file 2 restricted to 2018–2020, but in the
**1999–2020 (bridged-race)** database rather than the Single Race one. Everything except the
database and the year range must match, or the comparison measures your query changes instead
of the vintage change.

### Two things that will break the parse

**Use Export, not copy-paste.** The `---` footer carries the query parameters. `fetch.py`
rejects an export without one, because a bare table of numbers is not a citable artifact and
silently accepting one would discard the entire reason for taking this route.

**A suppressed cell raises.** If any count comes back `Suppressed` or `Unreliable`, the parse
fails rather than coercing it to zero — suppressed means unknown, and zero is a claim. At
national level with ten-year bands this should not occur; if it does, something in the query
is narrower than intended.

`Not Stated` age rows are expected and handled: their deaths are summed into a separate
reported total, and a warning names the year and percentage if they exceed 0.1 percent.
WONDER reports `Not Applicable` for that row's population, which is correct — there is no
population of people whose age was not recorded — and the parser accepts it there only.

---

## Recording what you did

Every value you enter into `data/raw/` must have:

- `source_citation`, specific enough that a reviewer can find the exact table
- `verified_by`, your name or initials
- `verified_date`, ISO date

The loader refuses to run in strict mode without these. That is deliberate.
