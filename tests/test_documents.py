"""The prose must not restate a computed number as a literal.

`src/report.py` exists so that a number cannot appear in the paper without the
code having produced it. That guarantee held only for values already written as
tokens; nothing stopped a literal being typed beside them, and several were --
the pre-pandemic age-to-rate ratio appeared three times in the manuscript as
`3.41`, and the policy framework's Preamble carried an empirical claim about
publication lag that the repository's own NVSR research contradicted.

A literal that happens to be right today is the exact failure this project was
rebuilt around: it agrees with itself indefinitely, and goes stale silently the
first time the data moves.
"""
import json
import re
from pathlib import Path

import pytest

from src import report

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "data" / "processed" / "results.json"


@pytest.fixture(scope="module")
def results():
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def _computed_values(res) -> dict[float, str]:
    """Every scalar results.json publishes, keyed by value."""
    out: dict[float, str] = {}

    def put(v, label):
        if isinstance(v, (int, float)):
            out.setdefault(round(float(v), 4), label)

    for key in ("crude_rate_first", "crude_rate_last", "adjusted_rate_first",
                "adjusted_rate_last", "covid_share_65plus"):
        put(res[key], key)
    for d in res["decomposition"]:
        for k in ("total_change", "rate_effect", "age_effect", "ratio"):
            put(d[k], f"decomposition[{d['interval']}].{k}")
    ex = res["excess"]
    put(ex["baseline_slope"], "excess.baseline_slope")
    put(ex["total_2020_2021"], "excess.total_2020_2021")
    put(ex["total_pandemic_era"], "excess.total_pandemic_era")
    for row in ex["by_year"]:
        put(row["excess_deaths"], f"excess.by_year[{row['year']}]")
    for row in res["covid_by_age"]:
        put(row["covid_deaths"], f"covid_by_age[{row['age_group']}].deaths")
        put(round(row["share_pct"], 1), f"covid_by_age[{row['age_group']}].share")
    return out


# Only "statistic-shaped" literals: something with a decimal point or thousands
# separator. A bare integer is far more likely to be a year, a section number or
# a journal volume -- the manuscript's bibliography contains a `26(3)` that
# collides with an age effect of 26.0 and is obviously not a restatement of it.
#
# The trailing guard is `(?!\d)` and NOT `(?![\w.])`. The stricter version was
# the first thing written here and it silently exempted every literal that ends
# a sentence: `the three, 3.41.` did not match, because the full stop failed the
# lookahead. A checker with a hole in it is worse than no checker, since the
# suite then reports the absence of a search as the absence of a problem.
LITERAL = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+\.\d+)(?!\d)")

# Literals that are legitimately not from results.json. Each needs a reason.
ALLOWED: dict[str, str] = {
    "3.87": "upper bound of the 2010-treatment range; from the alternative "
            "treatments table in docs/denominator-methods.md, which the "
            "pipeline does not yet reproduce. Flagged in the prose as such.",
}


def _templates():
    return [ROOT / "paper" / name for name in report.TEMPLATES]


def test_every_template_builds_with_no_unresolved_tokens(results):
    """A token the flattener does not know must fail loudly, not silently."""
    for name in report.TEMPLATES:
        built = report.build_document(name, results)
        text = built.read_text(encoding="utf-8")
        leftover = re.findall(r"\{\{(\w+)\}\}", text)
        assert not leftover, f"{built.name} has unsubstituted tokens: {leftover}"


def test_templates_do_not_restate_a_computed_value_as_a_literal(results):
    """The sweep, made permanent.

    Any statistic-shaped literal matching a value in results.json is either a
    duplication that will go stale, or a coincidence that needs recording in
    ALLOWED with its reason.
    """
    values = _computed_values(results)
    offenders = []

    for path in _templates():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in LITERAL.finditer(line):
                raw = m.group(1)
                if raw in ALLOWED:
                    continue
                key = round(float(raw.replace(",", "")), 4)
                if key in values:
                    offenders.append(
                        f"  {path.name}:{lineno} literal {raw!r} == "
                        f"{values[key]}\n      {line.strip()[:120]}"
                    )

    assert not offenders, (
        "Prose restates a computed value as a literal. Bind it to a token in "
        "report._flatten(), or add it to ALLOWED with the reason it is not "
        "derived:\n" + "\n".join(offenders)
    )


def test_policy_preamble_derives_its_empirical_claim(results):
    """The Preamble asserts a magnitude; it must come from the pipeline."""
    template = (ROOT / "paper" / "public_health_policy.md").read_text(encoding="utf-8")
    assert "{{COVID_SHARE_65PLUS}}" in template
    assert "{{COVID_YEAR_FIRST}}" in template and "{{COVID_YEAR_LAST}}" in template

    built = report.build_document("public_health_policy.md", results).read_text(
        encoding="utf-8"
    )
    share = results["covid_share_65plus"]
    assert f"{share} percent" in built
    # And it must name its own window: the COVID series starts after the
    # mortality grid does, so borrowing the paper's first year would overstate
    # the period the share covers.
    assert str(results["covid_years"]["first"]) in built
    assert results["covid_years"]["first"] != results["years"]["first"]


def test_the_shortfall_token_tracks_the_ratio(results):
    """241 percent is (ratio - 1); it must move when the ratio does."""
    flat = report._flatten(results)
    ratio = results["decomposition"][0]["ratio"]
    assert flat["DECOMP_PRE_RATE_SHORTFALL_PCT"] == str(round((ratio - 1) * 100))

    moved = json.loads(json.dumps(results))
    moved["decomposition"][0]["ratio"] = ratio + 1.0
    assert report._flatten(moved)["DECOMP_PRE_RATE_SHORTFALL_PCT"] != \
        flat["DECOMP_PRE_RATE_SHORTFALL_PCT"]
