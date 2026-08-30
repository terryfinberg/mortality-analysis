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

WONDER's own documentation of this is **inconsistent between exports of the same
database**. The bridged export states the vintage per year. The all-cause
2018–2024 export (file 2) carries no population caveat at all. The COVID
2020–2024 export (file 3), from the *same* single-race database, does state it —
2024 from Vintage 2024, 2023 from Vintage 2023, 2022 from Vintage 2022, each
released by the Census Bureau on a named date, and each built on the Modified
Blended Base used in lieu of the April 1 2020 decennial count. So the caveat's
absence from file 2 is not evidence that its denominators are single-vintage.
Read the vintage attribution off whichever export documents it, and confirm
against Census rather than relying on the footer being complete.

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
total concealed a 28.8-fold spread. Measure it at band level with
`assess_vintage_uniformity` before drawing any conclusion.
