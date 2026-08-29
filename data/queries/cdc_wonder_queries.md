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

## Recording what you did

Every value you enter into `data/raw/` must have:

- `source_citation`, specific enough that a reviewer can find the exact table
- `verified_by`, your name or initials
- `verified_date`, ISO date

The loader refuses to run in strict mode without these. That is deliberate.
