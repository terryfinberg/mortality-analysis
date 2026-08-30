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

from . import decomposition, excess, figures, loader, rates

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
        adjusted, ds.by_age, ds.standard_pop,
        ds.annual_deaths[["year", "deaths"]], ds.population,
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

    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "results.json").write_text(json.dumps(res, indent=2))

    figures.fig_crude_vs_adjusted(crude, adjusted)
    figures.fig_age_specific_rates(age_rates)
    figures.fig_excess(ex.table)
    figures.fig_covid_by_age(covid_share)
    figures.fig_decomposition(decomps)

    return res


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
        "EXCESS_2020_2021": f"{res['excess']['total_2020_2021']:,}",
        "EXCESS_TOTAL": f"{res['excess']['total_pandemic_era']:,}",
        "BASELINE_WINDOW": res["excess"]["baseline"],
    }
    # Stable aliases so the manuscript template does not break when the
    # dataset gains a year. PRE = first->2019, POST = 2019->last,
    # FULL = first->last, matching the order built in compute().
    aliases = ["PRE", "POST", "FULL"]
    for alias, d in zip(aliases, res["decomposition"]):
        flat[f"DECOMP_{alias}_INTERVAL"] = d["interval"]
        flat[f"DECOMP_{alias}_TOTAL"] = d["total_change"]
        flat[f"DECOMP_{alias}_RATE"] = d["rate_effect"]
        flat[f"DECOMP_{alias}_AGE"] = d["age_effect"]
        flat[f"DECOMP_{alias}_RATIO"] = d["ratio"]

    # How much larger age-specific mortality improvement would have had to be
    # for the rate effect to match the age effect: (ratio - 1) as a percentage.
    # Derived rather than written into the prose, because it moves whenever the
    # ratio does and a stale version of it reads as a finding.
    pre_ratio = res["decomposition"][0]["ratio"]
    flat["DECOMP_PRE_RATE_SHORTFALL_PCT"] = round((pre_ratio - 1) * 100)
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
