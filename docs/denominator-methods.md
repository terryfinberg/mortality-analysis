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

Vintage 2024 restated 2023 upward by **+1,891,336** (334,914,895 → 336,806,231),
**+0.565%**. Measured at band level on 2026-08-30 against Census
`nc-est2024-agesex-res.csv`, `POPESTIMATE2023`, `SEX=0`.

> **Every number in this section is computed, not quoted.** Regenerate the three
> tables below with `python -m src.vintage`. The Census inputs are committed
> under `data/raw/census/` with their SHA-256s and source URLs in
> `PROVENANCE.md` — a Census CSV carries no query footer the way a WONDER export
> does, so that file is the only provenance it has. `tests/test_vintage.py`
> asserts these tables still match what `src/vintage.py` computes, so a change
> to a band mapping either moves these numbers or fails the suite. That is
> deliberate: this section makes claims about the most recent year in the paper,
> and a claim nobody can regenerate is the failure this repository was rebuilt to
> remove.

| band | V2023 (WONDER) | V2024 | change | |
|---|---|---|---|---|
| 0-24 | 103,385,133 | 104,131,631 | +746,498 | +0.722% |
| 25-44 | 89,933,209 | 90,761,574 | +828,365 | +0.921% |
| 45-64 | 82,348,192 | 82,586,319 | +238,127 | +0.289% |
| 65-74 | 34,685,284 | 34,716,756 | +31,472 | +0.091% |
| 75-84 | 18,368,097 | 18,355,398 | **−12,699** | **−0.069%** |
| 85+ | 6,194,980 | 6,254,553 | +59,573 | +0.962% |

**Verdict: NON-UNIFORM.** Spread 1.031 percentage points against a +0.565%
total, scoring **1.83** on the threshold of 1.0. The fold ratio is undefined
rather than large: 75-84 moves *down* while the national total moves up, so
there is no max/min ratio across the sign change. A revision that pushes one
band opposite to the total is about as far from proportional as this measure
reaches.

The band collapse was validated before anything was computed from it: WONDER's
2024 equals Census V2024's 2024 **exactly in all six bands**, which is what
WONDER's footer claims and an independent check that single-year Census ages
fold onto our bands correctly.

#### Finding 1: a quarter of the recent decline is not mortality

**26.6% of the published 2023→2024 crude decline is denominator restatement,
and 70% of that reads as mortality improvement that did not happen.**

| | crude 2023 | crude 2024 | change | rate effect | age effect | age/rate |
|---|---|---|---|---|---|---|
| A as published | 922.9 | 903.4 | −19.47 | −32.81 | +13.34 | 0.406 |
| B 2023 at V2024 | 917.7 | 903.4 | −14.29 | −29.18 | +14.89 | 0.510 |

Deaths are identical in both — the certificates do not change. Additivity holds
exactly in both (rate + age = total to six decimals).

The restatement moves the total by **+5.18 points**, and splits **70.1% into the
rate effect (+3.63)** and **29.9% into the age effect (+1.55)**. So **11.1% of
the published −32.81 rate effect is denominator restatement rather than
mortality**, and 11.6% of the published age effect likewise.

Non-uniformity is what put any of it in the age effect at all. Had the
restatement been uniform, the whole 5.18 points would have booked as a rate
effect and read as a mortality improvement that never occurred. It is not
uniform, so some is absorbed elsewhere — but **the majority still lands in the
rate effect**, in the most recent year the paper reports. The non-uniform
finding is not reassurance.

**Report the range, not a point estimate:** crude change **−14.3 to −19.5**,
rate effect **−29.2 to −32.8**, age effect **+13.3 to +14.9**.

#### Finding 2: the headline ratio is basis-dependent

**The age-to-rate ratio moves 0.406 → 0.510 on a denominator choice — +25.5%.**

This is the same class of result as the 2010 slope leverage below: a headline
quantity that shifts by a magnitude no reader would guess from the size of the
input change. A +0.565% population revision moves the reported ratio by a
quarter, and it moves the **first decimal digit**: 0.4 becomes 0.5. Quoting this
ratio to three digits without naming a vintage claims about two digits of
precision the number does not have.

#### Finding 3: there is no consistent vintage to be consistent with

**Vintage 2025 restates 2024 to 340,003,797 against WONDER's 340,110,988, and
restates 2023 again — after V2024 had already restated it.** Verified against
Census `nc-est2025-agesex-res.csv` on 2026-08-30. V2025 moved **every year** in
the V2024 series, including the estimates base:

| reference year | V2024 | V2025 | change |
|---|---|---|---|
| base 2020 | 331,515,736 | 331,516,113 | +377 |
| 2020 | 331,577,720 | 331,578,104 | +384 |
| 2021 | 332,099,760 | 332,100,166 | +406 |
| 2022 | 334,017,321 | 333,996,304 | −21,017 |
| 2023 | 336,806,231 | 336,755,052 | −51,179 |
| 2024 | 340,110,988 | 340,003,797 | −107,191 |

Note the shape: the revisions grow with recency. The years a paper most wants to
report are the years least settled.

**This is why a full consistent-vintage reanalysis is not attempted here, and it
is a decision rather than an omission.** "Consistent V2024" was already obsolete
when treatment B above was computed — 2023 had been restated a second time.
Rebasing the whole series onto V2024 would produce numbers that are internally
consistent, externally stale, and wrong again by next June, while destroying the
crude-rate match against WONDER that is this pipeline's only external
validation. There is no terminal state to converge on. A basis that moves
annually is not a foundation, and treating the newest vintage as truth simply
relocates the arbitrariness rather than removing it.

The access date in each export footer is what pins which vintage a given run
used. That, not a rebasing exercise, is the reproducibility mechanism.

#### Finding 4: NCHS has published two crude rates for 2020, and said why

Findings 1 to 3 rest on our own measurement. This one does not.

**NVSR Vol. 74 No. 11, *Trends in Births and Deaths: United States, 2010–2023*,
states in its methods:**

> "Rates for 2020 have been revised, using blended base population estimates,
> and may differ from those published in 'Births: Final Data for 2020' and
> 'Deaths: Final Data for 2020,' which were based on postcensal population
> estimates based on the 2010 census."

That is the agency publishing two different crude death rates for the same year,
in two of its own reports, and naming the denominator rebasing as the cause.

It converts the argument of this document into an instance. The claim that a
crude rate is a statement about a denominator as much as about mortality does
not depend on accepting our sensitivity analysis: NCHS has demonstrated it in
its own catalogue. Cite this rather than only the internal measurements when the
point needs to carry weight with a reader who has not read the code.

Two practical consequences:

- **A crude rate carries a vintage, whether or not the publication says so.**
  Comparing rates across two publications, or across years spanning a rebasing,
  requires establishing a shared denominator basis first. 2020 in particular now
  has at least two published rates depending on which report you open.
- **It reinforces finding 3.** Rebasing is not a one-off correction that
  eventually settles; it is what the estimate series does. V2025 moved every
  year of V2024, and NCHS republished 2020 on a new base. There is no version of
  "the" 2020 crude rate to converge on.

#### Scope of the vintage sensitivity claim

This analysis reports vintage sensitivity **as a range at the two points where
it was measured** — the 2010 baseline basis and the 2023→2024 restatement — and
**does not attempt a full consistent-vintage reanalysis of the whole series,
because the vintage chain has no terminal state.** V2025 moves 2024 after V2024
moved 2023.

Stated as a decision rather than left as an open to-do, because it is not a task
that can ever be completed: any consistent-basis run is obsolete at the next
vintage release. The pre-pandemic Kitagawa is deliberately **not** re-run on a
V2024 basis; that result already survives a stated range (age-to-rate 3.41–3.87
across the three 2010 treatments), and a range that holds is the robustness
claim the paper makes.

### 3. The 2010 measurement basis

April 1 count against July 1 estimates, as above. Input error 0.188%; slope
leverage 11–20%; excess-mortality effect ~1%.

**Corroborated by NVSR, not inferred from WONDER.** This was originally read off
WONDER's own footer ("Population figures for 2010 are April 1 Census counts")
and confirmed against `CENSUS2010POP`. NCHS states it independently in the
publication of record: **NVSR Vol. 61 No. 4, *Deaths: Final Data for 2010*,
Table B header note** — *"Rates are based on populations enumerated as of April
1 for 2010 and estimated as of July 1 for 2009 using revised intercensal
estimates."* Read directly on 2026-08-30.

That matters because the whole treatment-C′ apparatus rests on the premise that
2010 is measured on a different basis. The premise now has three supports:
WONDER's footer, an exact band-by-band match against Census `CENSUS2010POP`, and
NCHS's own statement in the report a reviewer will reach for.

**Three supports, not three independent ones.** WONDER's footer and the NVSR
note are both NCHS saying the same thing in two places. Only the Census match
comes from outside NCHS, and even that is the agency whose estimates NCHS
processes. What the three together establish is that the April 1 basis is
documented and consistently stated wherever it appears — not that it has been
confirmed by three unrelated parties.

Three treatments, all reported:

| treatment | interval | slope | excess 2020-21 | age-to-rate ratio |
|---|---|---|---|---|
| A as published | 2010-2019 | −1.779 | 1,117,059 | 3.405 |
| B 2010 excluded | 2011-2019 | −1.415 | 1,105,148 | 3.599 |
| C' published July 1 | 2010-2019 | −1.585 | 1,110,739 | 3.872 |

> **Computed, not quoted.** `src/treatments.py` produces this table; regenerate
> it with `python -m src.treatments`, and `tests/test_treatments.py` fails if
> the doc drifts from it. It was previously a table of asserted numbers — rows
> B and C′ appeared nowhere in `src/` or `tests/`, so the robustness range the
> manuscript rests on was half computed and half typed.
>
> **When first computed, on 2026-08-30, all three reproduced the asserted
> values exactly** — slope, excess and ratio, to every published digit. That is
> recorded because it was the outcome, not because it was expected: had they
> differed, the difference would have been the finding rather than a footnote.
>
> Treatment C′ takes its denominator from `CENSUS2010POP`'s companion column
> `POPESTIMATE2010` in `data/raw/census/nc-est2020-agesex-res.csv`, and
> `assert_wonder_2010_is_the_decennial_count()` verifies band by band that
> WONDER's 2010 really is the April 1 count before C′ is computed. If it were
> not, replacing 2010 would be an unexplained substitution rather than a
> basis correction.

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

## What the NVSR corroboration does and does not establish

Thirteen of the fifteen annual totals, 2010 through 2022, agree exactly with
Table B of the corresponding *Deaths: Final Data* report, and our computed crude
rate agrees with NVSR's published rate to one decimal in every one of those
years. Recorded per row in `corroborated_against`, and recomputed on every test
run by `tests/test_nvsr_corroboration.py`.

**NVSR and WONDER are not independent of each other.** Both are NCHS products
drawing on the same underlying mortality file and the same Census-derived
denominators.

So state the finding precisely:

> This corroboration establishes that our query returned what NCHS published in
> its report of record. **It is not independent confirmation, and it is not
> evidence that NCHS is correct.**

What it rules out is a specific and real class of error: a query that returned
the wrong slice — wrong cause selection, wrong location, a filter left set, an
export truncated — would not reproduce the published national total for thirteen
consecutive years. That is worth having, and it is all it is.

What it cannot rule out is anything shared by both products: an error in the
underlying mortality file, in the Census denominators, or in NCHS's processing
of either. No amount of agreement between two NCHS publications speaks to that.

This wording exists because the sloppy version was used out loud during the work
— NVSR was described as an "independent" source in a recap, which is exactly the
overstatement being guarded against here. Two documents from one agency built on
one data file corroborate a *query*, not a *fact*.

### The rate agreement is a finding, and it is about the denominators

Worth stating separately, because it is easy to lose inside the totals.

Neither publication prints the other's population beside its rate. But a crude
rate is deaths over population: with deaths matching **exactly** and the rate
matching to NVSR's printed precision across all thirteen years, the denominators
must agree to within the rounding of the rate. `test_rate_agreement_implies_the_denominators_agree`
asserts that formally, by checking our population falls inside the interval
NVSR's printed rate implies.

**This is inference about the denominator, not a document stating it**, and the
distinction is why `us_population.csv` carries no corroboration. That column
holds what a source states. Recovering a denominator by division is a different
kind of claim and belongs in prose like this, where its reasoning is visible.

Subject, of course, to the limit above: it establishes that our denominator is
NCHS's denominator, which was never seriously in doubt, and says nothing about
whether NCHS's denominator is right. The Vintage 2024 restatement in
discontinuity 2 is a standing reminder that "NCHS's denominator" is not one
fixed quantity.

---

## Two things that cost an hour to rediscover

**Census directory layout.** National totals live under `state/totals/`, **not**
`national/totals/` — `national/` contains only `asrh/`. Population by age is in
`national/asrh/nc-est<vintage>-agesex-res.csv` (`SEX == "0"`, single-year `AGE`,
`999` is the total row). Vintage directories are named by range, e.g.
`2020-2024/`. **Discover the paths by listing; do not guess them.** Two guesses
failed before listing worked.

Re-confirmed 2026-08-30 while pulling V2024 and V2025: `2020-2025/national/asrh/`
serves, `2020-2025/national/totals/` still returns 404. Two further details worth
having — `AGE` tops out at `100`, which is the 100-and-over code rather than
exactly 100, so the six-band collapse takes `85 <= AGE <= 100`; and the
single-year rows sum exactly to the `AGE == 999` row, which is free arithmetic
validation of any collapse before you compute anything from it. Also note
`www2.census.gov` is reachable from this repository's tooling even though
`wonder.cdc.gov` returns 403, so Census figures can be checked directly rather
than quoted.

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
