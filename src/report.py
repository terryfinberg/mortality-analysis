"""Compute every number the manuscript cites and emit results.json.

The manuscript in paper/manuscript.md contains {{TOKEN}} placeholders.
build_manuscript() substitutes computed values into them. This exists so
that a number can never appear in the paper without having been produced
by the code in this repository -- the failure mode where a figure is
regenerated and a sentence in the text still quotes the old value simply
cannot happen.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import decomposition, excess, figures, loader, rates, treatments, vintage

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
PROCESSED = ROOT / "data" / "processed"


def compute(strict: bool = True) -> dict:
    ds = loader.load_all(strict=strict)

    crude = rates.crude_rate(ds.annual_deaths, ds.population)
    adjusted = rates.age_adjusted_rate(ds.by_age, ds.standard_pop)
    age_rates = rates.age_specific_rates(ds.by_age)

    years = ds.years
    y0, y_pre, y_last = years[0], 2019, years[-1]

    decomps = [
        decomposition.kitagawa(ds.by_age, y0, y_pre),
        decomposition.kitagawa(ds.by_age, y_pre, y_last),
        decomposition.kitagawa(ds.by_age, y0, y_last),
    ]

    ex = excess.excess_mortality(
        adjusted, ds.annual_deaths[["year", "deaths"]], ds.population,
        baseline_start=y0, baseline_end=y_pre,
    )

    covid_share = excess.covid_share_by_age(ds.covid_by_age)
    elderly = covid_share[covid_share["age_group"].isin(["65-74", "75-84", "85+"])]

    res = {
        "years": {"first": y0, "pre_pandemic": y_pre, "last": y_last},
        "crude_rate_first": round(float(crude.iloc[0]["crude_rate"]), 1),
        "crude_rate_last": round(float(crude.iloc[-1]["crude_rate"]), 1),
        "adjusted_rate_first": round(float(adjusted.iloc[0]["age_adjusted_rate"]), 1),
        "adjusted_rate_last": round(float(adjusted.iloc[-1]["age_adjusted_rate"]), 1),
        "decomposition": [
            {
                "interval": f"{d.year_start}-{d.year_end}",
                "total_change": round(d.total_change, 1),
                "rate_effect": round(d.rate_effect, 1),
                "age_effect": round(d.age_effect, 1),
                "ratio": round(d.ratio, 2),
            }
            for d in decomps
        ],
        "excess": {
            "baseline": f"{ex.baseline_years[0]}-{ex.baseline_years[1]}",
            "baseline_slope": round(ex.slope_per_year, 3),
            "total_2020_2021": round(ex.total_excess(2020, 2021)),
            "total_pandemic_era": round(ex.total_excess(2020, y_last)),
            "by_year": [
                {
                    "year": int(r.year),
                    "excess_deaths": round(float(r.excess_deaths)),
                    "excess_pct": round(float(r.excess_pct), 1),
                }
                for r in ex.table.itertuples()
            ],
        },
        "covid_by_age": covid_share.to_dict(orient="records"),
        "covid_share_65plus": round(float(elderly["share_pct"].sum()), 1),
        # The COVID series starts later than the mortality grid, so any claim
        # about the share has to name its own window rather than borrow the
        # paper's. Recorded here so the prose can cite it without a literal.
        "covid_years": {
            "first": int(ds.covid_by_age["year"].min()),
            "last": int(ds.covid_by_age["year"].max()),
        },
    }

    # The 2010 measurement-basis robustness range. Computed rather than quoted:
    # the manuscript's "not marginal under any treatment" claim rests on it.
    treats = treatments.compute_treatments(
        ds.by_age, ds.annual_deaths, ds.population, ds.standard_pop
    )
    lo, hi = treatments.ratio_range(treats)
    res["treatments"] = [
        {
            "key": t.key,
            "label": t.label,
            "interval": t.interval_label,
            "baseline_slope": round(t.baseline_slope, 3),
            "excess_2020_2021": round(t.excess_2020_2021),
            "rate_effect": round(t.rate_effect, 1),
            "age_effect": round(t.age_effect, 1),
            "age_to_rate_ratio": round(t.age_to_rate_ratio, 3),
        }
        for t in treats
    ]
    res["treatment_ratio_range"] = {"low": round(lo, 2), "high": round(hi, 2)}

    # The Vintage 2024 restatement of 2023, cited in the manuscript's
    # limitations. Derived here so the prose cannot hold a stale copy.
    uniformity = vintage.restatement_uniformity()
    shift = vintage.kitagawa_treatments()
    res["vintage_restatement"] = {
        "year": vintage.RESTATED_YEAR,
        "from_vintage": vintage.WONDER_VINTAGE,
        "to_vintage": vintage.RESTATING_VINTAGE,
        "population_pct_change": round(uniformity.total_pct_change, 3),
        "uniform": bool(uniformity.uniform),
        "share_of_decline_pct": round(shift.restatement_share_of_decline, 1),
        "rate_share_of_restatement_pct": round(shift.rate_share_of_restatement, 1),
        "age_share_of_restatement_pct": round(shift.age_share_of_restatement, 1),
    }

    # Which way age-specific risk actually moved, band by band. Section 4.1
    # reads Figure 2 aloud, and the honest reading is that the movement is
    # not all one way: the older bands fall, the midlife bands rise, and the
    # rate effect in 4.2 is the exposure-weighted net of the two.
    #
    # Counted here rather than described in the prose because the first
    # draft of that sentence said rates decline in "nearly every band" and
    # it was wrong by two of six. A sentence like that is right until the
    # data moves and then silently wrong, which is the failure this whole
    # token mechanism exists to prevent.
    # The pre-pandemic column is not decoration. Section 5.1 claims the
    # reversal is not an artefact of the shock, and that claim is only
    # checkable against the interval that excludes it.
    #
    # The death share is here for the same reason. The first draft of 5.1 said
    # the rising bands were "where few deaths occur"; 45-64 carries about a
    # sixth of all deaths, so that was false, and the true version -- that they
    # carry about a fifth between them and are outweighed anyway -- is the more
    # useful sentence. Neither could be written safely without the number.
    first = age_rates[age_rates["year"] == y0].set_index("age_group")["rate"]
    pre = age_rates[age_rates["year"] == y_pre].set_index("age_group")["rate"]
    last = age_rates[age_rates["year"] == y_last].set_index("age_group")["rate"]

    deaths_last = ds.by_age[ds.by_age["year"] == y_last]
    total_deaths_last = float(deaths_last["deaths"].sum())
    share_last = (
        deaths_last.set_index("age_group")["deaths"].astype(float)
        / total_deaths_last * 100
    )

    def _pct(a: float, b: float) -> float:
        return round((b - a) / a * 100, 1)

    res["age_band_change"] = [
        {
            "age_group": g,
            "rate_first": round(float(first[g]), 1),
            "rate_last": round(float(last[g]), 1),
            "pct_change": _pct(float(first[g]), float(last[g])),
            "pct_change_pre": _pct(float(first[g]), float(pre[g])),
            "death_share_last": round(float(share_last[g]), 1),
        }
        for g in sorted(first.index)
    ]

    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "results.json").write_text(json.dumps(res, indent=2))

    figures.fig_crude_vs_adjusted(crude, adjusted)
    figures.fig_age_specific_rates(age_rates)
    figures.fig_excess(ex.table)
    figures.fig_covid_by_age(covid_share)
    figures.fig_decomposition(decomps)

    return res


# Small counts read as words in prose, not numerals. The map stops at
# twelve and falls back to digits above it: the age grid has six bands and
# NCHS's has eleven, so twelve is headroom rather than a guess.
_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
    12: "twelve",
}


def _word(n: int) -> str:
    return _WORDS.get(n, str(n))


def _release_version() -> str:
    """The release this manuscript belongs to, read from CITATION.cff.

    The data availability statement names its own release, and that string
    cannot be typed into the template: it would be correct for exactly one
    tag and silently wrong for every one after it. CITATION.cff is where the
    version already lives, so the manuscript reads it from there and the two
    cannot disagree.

    Parsed with a regex rather than the yaml module because report.py has no
    other reason to depend on it and this is one scalar on a line of its own.
    """
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    m = re.search(r"^version:\s*[\"']?([^\s\"']+)", text, re.M)
    if not m:
        raise KeyError(
            "CITATION.cff has no version: field, and the manuscript's data "
            "availability statement names the release it belongs to."
        )
    return m.group(1)


def _join(items: list[str]) -> str:
    """Serial list: "a", "a and b", "a, b, and c"."""
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _flatten(res: dict) -> dict[str, str]:
    """Map {{TOKEN}} names to string values."""
    flat = {
        "YEAR_FIRST": res["years"]["first"],
        "YEAR_PRE": res["years"]["pre_pandemic"],
        "YEAR_LAST": res["years"]["last"],
        "CRUDE_FIRST": res["crude_rate_first"],
        "CRUDE_LAST": res["crude_rate_last"],
        "ADJ_FIRST": res["adjusted_rate_first"],
        "ADJ_LAST": res["adjusted_rate_last"],
        "COVID_SHARE_65PLUS": res["covid_share_65plus"],
        "COVID_YEAR_FIRST": res["covid_years"]["first"],
        "COVID_YEAR_LAST": res["covid_years"]["last"],
        "RATIO_RANGE_LOW": res["treatment_ratio_range"]["low"],
        "RATIO_RANGE_HIGH": res["treatment_ratio_range"]["high"],
        "VINTAGE_POP_PCT": res["vintage_restatement"]["population_pct_change"],
        "VINTAGE_SHARE_OF_DECLINE": res["vintage_restatement"]["share_of_decline_pct"],
        "VINTAGE_RATE_SHARE": res["vintage_restatement"]["rate_share_of_restatement_pct"],
        "EXCESS_2020_2021": f"{res['excess']['total_2020_2021']:,}",
        "EXCESS_TOTAL": f"{res['excess']['total_pandemic_era']:,}",
        "BASELINE_WINDOW": res["excess"]["baseline"],
        "RELEASE_VERSION": _release_version(),
    }
    # Stable aliases so the manuscript template does not break when the
    # dataset gains a year. PRE = first->2019, POST = 2019->last,
    # FULL = first->last, matching the order built in compute().
    aliases = ["PRE", "POST", "FULL"]
    for alias, d in zip(aliases, res["decomposition"]):
        flat[f"DECOMP_{alias}_INTERVAL"] = d["interval"]
        flat[f"DECOMP_{alias}_TOTAL"] = d["total_change"]
        flat[f"DECOMP_{alias}_RATE"] = d["rate_effect"]
        # Magnitude, for prose that carries the direction in words ("moved
        # it down by X") rather than in a minus sign. Separated deliberately:
        # a literal magnitude typed into the text would pass
        # test_documents.py only because its sign differs from the stored
        # value, which is a hole in the check rather than a licence to use
        # one.
        flat[f"DECOMP_{alias}_RATE_ABS"] = abs(d["rate_effect"])
        flat[f"DECOMP_{alias}_AGE"] = d["age_effect"]
        flat[f"DECOMP_{alias}_RATIO"] = d["ratio"]

    # The three treatments of the 2010 measurement basis, as a table in
    # section 4.4. Aliased A/B/C by position rather than keyed by the results
    # file's own "C'" -- an apostrophe cannot appear in a {{TOKEN}} name, and
    # position is what the table's row order follows anyway.
    for alias, t in zip(["A", "B", "C"], res.get("treatments", [])):
        flat[f"TREAT_{alias}_LABEL"] = t["label"]
        flat[f"TREAT_{alias}_INTERVAL"] = t["interval"]
        flat[f"TREAT_{alias}_RATE"] = t["rate_effect"]
        flat[f"TREAT_{alias}_AGE"] = t["age_effect"]
        flat[f"TREAT_{alias}_RATIO"] = t["age_to_rate_ratio"]
        flat[f"TREAT_{alias}_EXCESS"] = f"{t['excess_2020_2021']:,}"

    # How much larger age-specific mortality improvement would have had to be
    # for the rate effect to match the age effect: (ratio - 1) as a percentage.
    # Derived rather than written into the prose, because it moves whenever the
    # ratio does and a stale version of it reads as a finding.
    pre_ratio = res["decomposition"][0]["ratio"]
    flat["DECOMP_PRE_RATE_SHORTFALL_PCT"] = round((pre_ratio - 1) * 100)

    # Section 4.1's reading of Figure 2. Counts are rendered as words
    # because they appear mid-sentence in prose, and the band names are
    # joined into a list rather than typed, so naming the exceptions cannot
    # drift from which bands actually are the exceptions.
    bands = res.get("age_band_change", [])
    if bands:
        falling = [b for b in bands if b["pct_change"] < 0]
        rising = [b for b in bands if b["pct_change"] > 0]
        flat["AGE_BANDS_TOTAL_WORD"] = _word(len(bands))
        flat["AGE_BANDS_FALLING_WORD"] = _word(len(falling))
        flat["AGE_BANDS_RISING_WORD"] = _word(len(rising))
        flat["AGE_BANDS_RISING_LIST"] = _join(
            [b["age_group"] for b in rising]
        )

        # Section 5.1 needs the reversal's size, the band it is in, and its
        # pre-pandemic value -- the last of these because the claim being made
        # is that the shock did not cause it. "Worst" is by magnitude of rise,
        # picked from the data rather than named in the prose, so the sentence
        # cannot end up pointing at the wrong band.
        if rising:
            worst = max(rising, key=lambda b: b["pct_change"])
            flat["AGE_BAND_RISE_MAX_GROUP"] = worst["age_group"]
            flat["AGE_BAND_RISE_MAX_PCT"] = worst["pct_change"]
            flat["AGE_BAND_RISE_MAX_PCT_PRE"] = worst["pct_change_pre"]
            flat["AGE_BANDS_RISING_DEATH_SHARE"] = round(
                sum(b["death_share_last"] for b in rising), 1
            )
    return {k: str(v) for k, v in flat.items()}


# Templates that carry computed values, and where each is written.
#
# The policy framework is here because its Preamble makes empirical claims. A
# model statute asserting a magnitude that nothing in the repository produced is
# the same defect as a paper doing it, and arguably worse: a policy document is
# read by people who will not open the code.
TEMPLATES: dict[str, str] = {
    "manuscript.md": "manuscript_built.md",
    "public_health_policy.md": "public_health_policy_built.md",
}


def build_document(template_name: str, res: dict | None = None) -> Path:
    """Substitute computed values into one template."""
    if res is None:
        res = json.loads((PROCESSED / "results.json").read_text())
    template = (PAPER / template_name).read_text()
    values = _flatten(res)

    unresolved = []

    def sub(m):
        key = m.group(1)
        if key not in values:
            unresolved.append(key)
            return m.group(0)
        return values[key]

    out = re.sub(r"\{\{(\w+)\}\}", sub, template)
    if unresolved:
        raise KeyError(
            f"{template_name} references undefined tokens: "
            f"{sorted(set(unresolved))}. Add them to report._flatten() or fix "
            f"the template."
        )
    dest = PAPER / TEMPLATES[template_name]
    dest.write_text(out)
    return dest


def build_manuscript(res: dict | None = None) -> Path:
    """Substitute computed values into the manuscript template."""
    return build_document("manuscript.md", res)


def build_all(res: dict | None = None) -> list[Path]:
    """Build every template that cites computed values."""
    return [build_document(name, res) for name in TEMPLATES]


if __name__ == "__main__":
    r = compute()
    built = build_all(r)
    print(json.dumps(r, indent=2))
    for p in built:
        print(f"\nWritten to {p}")
