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

**Values come from the WONDER exports**, derived as `sum(six bands) + not_stated` from
files 1 and 2 — the same export that supplies the age detail, so the annual identity is exact
rather than a cross-source comparison. `source_citation` names that export.

**NVSR is the corroboration source, not the value source.** Where you have confirmed WONDER's
total against a published NCHS report, record the volume and table in `corroborated_against`
with the date in `corroborated_date`. If the two ever disagree, that is a finding: record both
figures and footnote it rather than silently preferring either.

**Table B is not available for every year**, so the corroboration source differs by year
rather than being uniform. The worked plan, the year-by-year reference list and the resolved
basis question are in `UAT_CHECKLIST.md`, Section 7; the availability finding they rest on is
immediately below.

Two results from that work belong here, because they govern any comparison against NVSR:

- **NVSR totals include age-not-stated deaths**, per NVSR 61-4 Table 10 footnote 1. Compare
  against `deaths`, which is `sum(six bands) + not_stated`, not against the band sum. Same
  convention as WONDER.
- **Never compare the age-adjusted rate.** NCHS standardises over eleven age groups and this
  analysis uses six. The rates differ by construction, and a mismatch found that way is a
  property of the grouping rather than a discrepancy worth chasing.

This is a deliberate change from an earlier plan in which NVSR supplied the values. Citing a
report the number did not come from makes attestation mean "I checked this against NVSR",
which is a harder and differently-scoped claim than "I checked this against the committed
export" — and one that cannot be met uniformly across years. See **Provenance, attestation and
corroboration** in `README.md`.

### NVSR availability for recent years — RESOLVED 2026-08-30

Checked against the official NCHS index, <https://www.cdc.gov/nchs/products/nvsr.htm>, which
states it lists all reports released to date. **Absence from that index is meaningful**, which
is what distinguishes it from the FTP mirror; see the note below.

**The series is not retired, and 2023 is not yet published.**

| year | "Deaths: Final Data" report | released |
|---|---|---|
| 2021 | NVSR 73-8 | Oct 2024 |
| 2022 | NVSR 74-4 | Jun 2025 |
| 2023 | **not published** | — |
| 2024 | **not published** | — |

Latest issue of any kind at the time of checking: 75-5, August 2026. The observed lag from
reference year to final-data report is about three years, so **2023 is due but not out**, and
2024 is not expected for roughly another year. This is a publication delay, not a change of
policy — do not record it as the series having been discontinued.

**2024 has no published NVSR report at all.** Not a delayed one, none. Its values rest on the
committed export alone, and the paper should say so in those words rather than leaving the
reader to infer that every year got the same treatment.

Note that even where a report does exist, the corroboration it provides is **not independent**:
NVSR and WONDER are both NCHS products over the same mortality file. See "What the NVSR
corroboration does and does not establish" in `docs/denominator-methods.md`.

Consistent with the above: NVSR 75-5 is *United States Life Tables, 2024*, and 74-6 is the
2023 edition. Life tables are computed from the final mortality file, so NCHS holds final 2024
mortality data and has published *from* it — it simply has not published the "Deaths: Final
Data for 2024" report. That independently supports `status = final` for every year in the
grid, separately from WONDER's own footer.

> **Why the earlier answer was "not established" rather than "not published".** An earlier
> pass could not read cdc.gov — it returns HTTP 403 to this repository's tooling, the same
> Akamai block that covers WONDER — and searched
> `ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/NVSR/` instead. Neither report was
> there, but that mirror carries roughly 41 issue directories across volumes 52–75, where NVSR
> publishes many issues per volume. A partial index can confirm that a report exists and can
> never establish that one does not. The official index makes the negative claim; the mirror
> could not, and the distinction was worth keeping until someone could read the index.

For provisional years, were any ever to enter the grid, use CDC Vital Statistics Rapid
Release: https://www.cdc.gov/nchs/nvss/vsrr.htm. None currently do.

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
| 1 | `allcause_by_age_2010-2017_ucd-bridged.txt` | Underlying Cause of Death, 1999–2020 | 2010–2017 | All causes | Deaths, Population, Crude Rate | none — see below |
| 2 | `allcause_by_age_2018-2024_ucd-singlerace.txt` | Underlying Cause of Death, 2018–2024, Single Race | 2018–2024 | All causes | Deaths, Population, Crude Rate | https://wonder.cdc.gov/controller/saved/D158/D518F643 ⚠ |
| 3 | `covid_u071_by_age_2020-2024_ucd-singlerace.txt` | Underlying Cause of Death, 2018–2024, Single Race | 2020–2024 | **UCD ICD-10 = U07.1** | Deaths | https://wonder.cdc.gov/controller/saved/D158/D518F647 |
| 4 | `allcause_by_age_2018-2020_ucd-bridged_SEAM.txt` | Underlying Cause of Death, 1999–2020 | 2018–2020 | All causes | Deaths, Population, Crude Rate | |

Links for 2 and 3 verified live on 2026-08-29. **File 1 has no saved link and will not get
one:** it was exported before this field existed, and re-running a query against frozen
1999–2020 history purely to mint a link would buy nothing the footer does not already carry.
Blank is a valid state here, not an outstanding task.

⚠ **File 2's link may not replay to the same years.** Its footer carries no `Year/Month`
line, so a replay may return whatever the database holds at that time rather than 2018–2024.
See "What pins export 2" in `docs/denominator-methods.md`.

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
where a real difference could live, and it would propagate into every age-specific rate.

**Measured 2026-08-30: both are exactly zero.** All 18 overlapping cells agree to the person
in deaths and population, so the 2017/2018 boundary carries no vintage step. The reasoning
is that these queries carry no race stratification, and bridged-race and single-race are two
race-detail treatments of the same Census vintage. See "The bridged/single-race seam,
measured" in `docs/denominator-methods.md` for the mechanism and, more importantly, for the
limits of what a zero here licenses. **File 4 stays in the repository and stays out of the
grid.** A null result is a measurement, and it holds only for as long as the inputs it was
computed from are the ones on disk.

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
