# Denominator methods and known discontinuities

Working notes on the population denominator: where it comes from, the
discontinuities in it, and the method for telling a real mortality change from
a restatement of the population.

---

## Why the denominator comes from WONDER

Population is taken from the Population column of the same WONDER export that
supplies the deaths, summed across ten-year age groups — not fetched separately
from Census.

WONDER's population figures are themselves NCHS-processed Census estimates, so
this is a choice of vintage, not a change of source. It buys two things:

1. `sum(age bands) == annual population` becomes an exact identity rather than a
   cross-source comparison needing a tolerance.
2. **The crude-rate check.** WONDER publishes its own Crude Rate column. Because
   the denominator is WONDER's denominator, our computed rate must reproduce
   WONDER's published rate. It does, for all 15 years, to one decimal. This is
   the pipeline's only external validation — the only check that reaches outside
   this repository.

**Do not switch to a single-vintage Census series to make the denominator
internally tidy.** It would break the crude-rate match, which costs more than
the tidiness is worth. Consistency with the issuing agency beats internal
consistency.

---

## Is it a mortality change, or a denominator restatement?

**This is a band-level question. The national total cannot answer it.**

| | what happens | how it reads |
|---|---|---|
| **Uniform** revision | every age-specific rate moves by the same proportion; shares untouched | Kitagawa books it entirely as a **rate effect** — a mortality change that never happened |
| **Non-uniform** revision | shares move | part lands in the **age effect** |

Both can produce an identical national total. The total is not evidence either
way, and treating a small total as proof of a small effect is the mistake.

### Use `assess_vintage_uniformity()`

```python
from src.fetch import assess_vintage_uniformity

result = assess_vintage_uniformity(by_age, 2023, 2024)
print(result.summary())
```

Returns per-band percentage change, the spread between the largest and smallest
band, that spread as a multiple of the overall change, the fold ratio, and a
`uniform` verdict. The threshold is
`fetch.VINTAGE_UNIFORMITY_SPREAD_MULTIPLE`, currently `1.0`.

### The worked case: 2010

WONDER carries the **April 1 decennial count** for 2010 while every other year
is a **July 1 estimate**. Verified band by band against Census `CENSUS2010POP`;
our 2010 denominators reproduce it exactly.

Moving to the published July 1 figure is **+0.188% nationally** — small enough
to wave through. Band by band:

| band | change | | band | change |
|---|---|---|---|---|
| 0-24 | +0.032% | | 65-74 | +0.659% |
| 25-44 | +0.071% | | 75-84 | +0.132% |
| 45-64 | +0.343% | | 85+ | **+0.912%** |

A **28.8-fold** spread; 0.880 percentage points against a 0.188% total, scoring
**4.67** on the threshold. It moved the age effect (99.43 → 96.72), not only the
rate effect. Inspecting the total alone would have mis-attributed all of it to
mortality.

**Why these numbers are recomputed from source rather than quoted.** The
national figure above was `+0.184%` for a while — the value implied by an
*interpolated* July 1 denominator, calculated before the published Census
estimate was found. Once the published figure superseded it, the stale number
survived in code comments and a working note, and propagated into discussion
outside this repository. It was caught only because a test recomputed the
percentage from the source band figures instead of asserting the number someone
had written down. A quoted constant would have agreed with itself indefinitely.
That is the case for the method, not an argument about carelessness: derived
figures go stale silently, and the only reliable defence is recomputing them
from their inputs.

`tests/test_fetch.py` pins this case as a regression fixture using the real
published Census figures. That deviates from the suite's usual
obviously-unreal-fixtures rule, deliberately: a synthetic stand-in would prove
the arithmetic but not that the threshold catches the case it was calibrated on.
**Those values are a fixture, never analysis input.**

---

## The three known discontinuities

Different causes, different magnitudes, different remedies. They share a
denominator and nothing else. Section 6 of the manuscript gives each its own
subsection rather than bundling them.

### 1. Per-year vintage chain

WONDER carries each year at the vintage current when that year was first
estimated, never revised backward. Its 2023 equals Census Vintage 2023 exactly
and its 2024 equals Vintage 2024 exactly, both to the person.

**WONDER states this chain in every export's footer, and states it the same way
each time.** Files 2 and 3 both carry it — file 2 as caveat 3, file 3 as caveat
4 — in identical text: 2024 from Vintage 2024, 2023 from Vintage 2023, 2022 from
Vintage 2022, each released by the Census Bureau on a named date, and each built
on the Modified Blended Base used in lieu of the April 1 2020 decennial count.
File 1 carries the bridged-race equivalent, per year back to 1999, including the
line that makes the 2010 case below visible at all: *"Population figures for 2010
are April 1 Census counts."*

So the vintage chain is **documented by the source, not inferred by us**, and
that is the footing to argue from. What the footer establishes is *which*
vintage each year is drawn from. What it cannot establish is that the figures
carried are that vintage — a caveat is a claim about provenance, and this
repository's whole argument is that a provenance claim is not a verification.
That is what the Census check is for, and it holds: WONDER's 2023 equals Vintage
2023 and its 2024 equals Vintage 2024, both to the person, confirmed against the
published series rather than taken from the caveat.

The real asymmetry between the exports is one of **substance, not completeness**:
file 1's population basis genuinely differs from files 2 and 3, bridged-race
against single-race, with 2010 an April 1 count rather than a July 1 estimate.
That difference is the subject of discontinuities 2 and 3 below. It is not a
documentation gap.

> **Correction, 2026-08-30.** An earlier version of this section claimed file 2
> "carries no population caveat at all" and built the inconsistent-documentation
> argument on that. The claim was wrong: the caveat was in the file the whole
> time, and the file predates the note. Recorded rather than quietly edited, for
> the same reason as the `+0.184%` case above — a wrong statement that gets
> silently replaced leaves no trace for anyone who read it and passed it on.

This is what NCHS itself does when it publishes rates, which is why our crude
rates reproduce WONDER's. **It is a feature.** The cost is that a trend fit
across those years carries vintage-revision noise — usually fractions of a
percent, occasionally a methodology change.

### 2. Vintage 2024 methodology restatement

Vintage 2024 restated 2023 upward by **+1,891,336** (334,914,895 → 336,806,231).

| basis | 2023→2024 growth | crude change |
|---|---|---|
| WONDER as published | +1.551% | −19.5 |
| consistent V2024 | +0.981% | −14.3 |

So **≈5.2 points, about 27%**, of the 2023→2024 crude decline is restatement
rather than mortality change.

Vintage 2025 already exists and restates again (2024 → 340,003,797). WONDER will
carry these eventually. The access date in each export footer is what pins which
vintage a given run used.

**Still to do:** run `assess_vintage_uniformity` on the V2023→V2024 restatement
of 2023, **at band level**. The question is not how large the revision is but
whether it is uniform. Then re-run the pre-pandemic Kitagawa and the excess
figures on a consistent-V2024 denominator as a **sensitivity, not a
replacement**.

### 3. The 2010 measurement basis

April 1 count against July 1 estimates, as above. Input error 0.188%; slope
leverage 11–20%; excess-mortality effect ~1%.

Three treatments, all reported:

| treatment | interval | slope | excess 2020-21 | age-to-rate ratio |
|---|---|---|---|---|
| A as published | 2010–2019 | −1.779 | 1,117,059 | 3.405 |
| B 2010 excluded | 2011–2019 | −1.415 | 1,105,148 | 3.599 |
| C′ published July 1 | 2010–2019 | −1.585 | 1,110,739 | 3.872 |

A stays primary, because it preserves the crude-rate match. The improvement rate
is reported as a **range**, −1.41 to −1.78, not a point estimate.

---

## What pins export 2

Export 2's footer carries **no `Year/Month` line**. Exports 1 and 3 both pin
their years explicitly; export 2's Query Parameters block simply has no year
entry. Its data rows do run 2018–2024, seven years, thirteen rows each.

**Hypothesis, not established fact.** The years were selected individually in
the form and the *Currently selected* panel listed all seven, so the selection
was made. WONDER appears to omit the `Year/Month` line when the selection covers
the database's entire range, treating a full selection as no restriction rather
than as a filter. Exports 1 and 3 are both strict subsets of their databases and
both pin their years, which is consistent with that reading — but consistent is
not confirmed. Two files agreeing with a guess is weak evidence, and CDC's own
tooling is unreachable from here (`wonder.cdc.gov` returns 403), so this has not
been checked against the live site. **Do not promote this to a fact without
testing it**: run one query selecting every year and one selecting all but the
last, from the same database, and compare the two footers.

### The consequence, which does not depend on the cause

Whatever the mechanism, the effect is the same and it is what matters: **export
2's saved query may replay as "all dates"** and therefore return 2018–2025 once
WONDER adds 2025, silently, with no change to the link.

So for export 2 the hierarchy inverts:

| | usual case (exports 1, 3) | export 2 |
|---|---|---|
| authoritative | the query — replay it, get the file | **the committed file and its data rows** |
| supporting | the file is a snapshot of that replay | the query, which may replay wider |

Everywhere else in this repository the query is the thing that pins the extract
and the file is a snapshot of running it; that is the entire argument for
committing the exports with their footers. For export 2 that is backwards. The
bytes in `data/raw/wonder_exports/allcause_by_age_2018-2024_ucd-singlerace.txt`,
and specifically the fact that its rows stop at 2024, are what fixes the year
range. The saved link records how the extract was obtained. It does not
constrain what a replay returns.

Practical consequences:

- A reviewer replaying export 2's link and getting a 2025 row has **not** found
  a discrepancy in this analysis. They have re-run a wider query. Compare
  against the committed file, not against a fresh replay.
- If export 2 is ever re-exported, the row count is the quick eyeball check:
  92 data lines, 7 years × 13 rows + 1 grand total. A file with more years is a
  different extract and needs the analysis grid re-examined, not a silent
  substitution.
- **A widened re-export is caught in code.** `assert_export_years_match_spec()`
  compares `spec.years` against the years actually parsed out of the file, on
  every load, in both directions, and names both ranges when they disagree:

  ```
  allcause_by_age_2018-2024_ucd-singlerace.txt: the export's years do not match the registry.
    WONDER_EXPORTS declares: 2018-2024 (7 year(s))
    the file contains:       2018-2025 (8 year(s))
    present in the file but not declared: 2025.
  ```

  Before that assertion existed the declared range read like a guard without
  being one: `spec.years` was used only by the tests, for grid coverage and
  non-overlap, and by `load_seam()` to select the single-race spec. A file that
  came back with a 2025 row would have parsed cleanly, joined the analysis grid,
  extended the crude-rate check by a year, and passed. Truncation is checked the
  same way and for the same reason — losing 2024 from this file would shorten
  the baseline window rather than fail.

---

## The bridged/single-race seam, measured

**Result: exactly zero.** Export 4 was run on 2026-08-30 and differenced against
export 2 over their overlap. All 18 cells — 3 years × 6 bands — agree **to the
person**, in deaths *and* population. Worst population difference 0.000%, worst
deaths difference 0.000%.

| | bridged (file 4) | single-race (file 2) |
|---|---|---|
| 2018 85+ deaths | 880,280 | 880,280 |
| 2018 85+ population | 6,544,503 | 6,544,503 |
| 2018 75-84 population | 15,394,374 | 15,394,374 |

**Why it is zero, rather than merely small.** Bridged-race and single-race are
two race-detail treatments of the *same* Census vintage estimate for a given
year, and NCHS derives the bridged file from the Census single-race file. The
footers show the pairing directly: file 4 gives 2018 as Vintage 2018 released by
NCHS on June 25 2019; file 2 gives 2018 as Vintage 2018 released by the Census
Bureau on June 20 2019 — five days earlier, the input to the first. **These
queries carry no race stratification**, so the age×all-races totals are the same
numbers reached by two routes. Zero is the expected answer once the mechanism is
stated, which is a reason to trust it, not a reason to have skipped measuring.

**Ruling out the obvious failure.** An all-zero difference is exactly what
comparing a file against itself produces, so that was checked rather than
assumed: the two files have different SHA-256 hashes, different row counts
(40 vs 92), and different column sets — file 2 carries the confidence-interval
columns that file 4 lacks. They are distinct extracts that agree.

### What this establishes, and what it does not

**Establishes:** the 2017/2018 grid boundary carries **no vintage step**. The
grid takes 2017 from the bridged database and 2018 from the single-race one, and
because the two databases report identical populations across the overlap, that
boundary is arithmetically identical to staying inside one database. The
2010–2019 pre-pandemic baseline window therefore has no step at 2017/2018, and
the baseline trend fit is not absorbing one. This was the open risk that
justified building export 4; it is closed.

**Does not establish:**

- Anything about the **per-year vintage chain** (discontinuity 1). That is a
  within-database property and is untouched by this comparison.
- Anything about the **Vintage 2024 restatement** (discontinuity 2), which
  remains open and still needs `assess_vintage_uniformity` at band level.
- That the two databases are interchangeable **in general**. They are
  interchangeable *for a query with no race stratification*. Stratify by race
  and they are not, which is the entire reason race bridging exists. Do not
  generalise this null result past the query that produced it.

Reproduce with `python -m src.fetch --reconcile`, under the **Vintage seam**
heading. The same run reports the crude-rate check: **15 of 15 years match**
WONDER's published Crude Rate, 2010 through 2024.

---

## Two things that cost an hour to rediscover

**Census directory layout.** National totals live under `state/totals/`, **not**
`national/totals/` — `national/` contains only `asrh/`. Population by age is in
`national/asrh/nc-est<vintage>-agesex-res.csv` (`SEX == "0"`, single-year `AGE`,
`999` is the total row). Vintage directories are named by range, e.g.
`2020-2024/`. **Discover the paths by listing; do not guess them.** Two guesses
failed before listing worked.

**Do not soften export 4's framing.** The 2017→2018 aggregate population change
(+0.445%) looks unremarkable against its neighbours. That is *not* evidence the
bridged-to-single-race seam is small — aggregate smoothness can mask offsetting
band-level differences. It is the same trap as the 2010 case, where a 0.188%
total concealed a 28.8-fold spread. Measure it at band level before drawing any
conclusion.

**Measured, 2026-08-30: the seam is exactly zero.** See below. The instruction
above stands unchanged — it said measure rather than infer, and measuring is
what produced the answer. A null result reached by measurement is not the same
claim as a null result assumed from the aggregate, and this section is not
evidence that the caution was unnecessary.
