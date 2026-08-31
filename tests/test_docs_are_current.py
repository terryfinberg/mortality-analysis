"""Prose that asserts a current repository state, checked against that state.

This class of defect has been found three times in this project, every time by
a person reading rather than by anything failing:

1. README said "Eighty-two tests" long after there were eighty-six.
2. README opened with "the data files are intentionally empty" after they were
   populated, then with "not yet attested, so strict loading still refuses it"
   after the rows were signed -- in both cases changed by a commit that updated
   the numbers nearby and not the sentence.
3. UAT_CHECKLIST named `test_populated_data_is_still_unverified`, a test that
   had been replaced.

The common shape: a document states something true when written, a later commit
falsifies it, and nothing connects the two. It is the same failure as a
hardcoded computed value (see test_documents.py), one level up -- the claim is
about the repository rather than about a number.

Not everything is checkable this way. What is checkable cheaply is anything the
prose states that the repository can be asked directly: counts, names of tests,
and paths. Those are covered here.
"""
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

# The documents that describe the repository's current state, as opposed to its
# method. denominator-methods.md is excluded: it argues about data, and its
# numeric claims are covered by the doc-sync tests in test_vintage and
# test_treatments.
STATE_DOCS = [ROOT / "README.md", ROOT / "UAT_CHECKLIST.md"]

WORD_NUMBERS = {
    "eighty": 80, "ninety": 90, "one hundred": 100, "two hundred": 200,
}


@lru_cache(maxsize=1)
def _collected() -> tuple[str, ...]:
    """Node ids pytest actually collects, from a subprocess.

    Counting `def test_` in the source was the first attempt and it was wrong:
    test_fetch.py parametrises two tests into seven cases, so the scan
    undercounted by five and would have pinned the wrong number into the
    checklist -- a staleness check that itself asserted a stale figure.

    ``-o addopts=`` clears the project's ``-v``, which would otherwise print a
    tree rather than node ids. Collection does not execute anything.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(TESTS), "--collect-only", "-q",
         "-o", "addopts="],
        capture_output=True, text=True, cwd=ROOT,
    )
    ids = [ln.strip() for ln in result.stdout.splitlines() if "::" in ln]
    if not ids:
        raise AssertionError(
            f"could not collect tests; pytest said:\n{result.stdout[-2000:]}"
        )
    return tuple(ids)


def _test_function_names() -> set[str]:
    """Collected names, with any parametrize case suffix stripped."""
    names = set()
    for node in _collected():
        name = node.split("::")[-1]
        names.add(name.split("[")[0])
    return names


def collected_test_count() -> int:
    return len(_collected())


# Test functions that prose deliberately discusses in the past tense. Each is
# named here with why, so a genuine dangling reference still fails.
RETIRED_TESTS = {
    "test_repo_ships_with_unpopulated_data":
        "removed when the CSVs were populated, as the README instructed; the "
        "README explains the removal",
    "test_populated_data_is_still_unverified":
        "replaced by test_promotion_cannot_write_an_attestation once the rows "
        "were signed; both documents explain why",
}


def test_the_collected_count_exceeds_the_number_of_test_functions():
    """A guard on the guard: collection must be counting cases, not defs.

    If this ever came out equal it would mean the subprocess had silently
    fallen back to something def-shaped, and the count check below would be
    measuring the wrong thing.
    """
    defs = sum(
        len(re.findall(r"^def test_\w+", p.read_text(encoding="utf-8"), re.MULTILINE))
        for p in TESTS.glob("test_*.py")
    )
    assert collected_test_count() > defs, (
        "this suite parametrises at least one test, so collected cases must "
        "outnumber test functions"
    )


def test_stated_test_counts_match_the_suite():
    """"166 passed" in a checklist is a claim about right now."""
    actual = collected_test_count()
    found = 0
    for doc in STATE_DOCS:
        text = doc.read_text(encoding="utf-8")
        for m in re.finditer(r"\*\*(\d+) passed\*\*|(\d+) tests pass", text):
            stated = int(m.group(1) or m.group(2))
            found += 1
            assert stated == actual, (
                f"{doc.name} says {stated} tests; the suite has {actual}."
            )
    assert found >= 2, "expected the checklist to state the count at least twice"


def test_test_names_mentioned_in_prose_actually_exist():
    """A checklist telling you to watch a deleted test is worse than silent."""
    known = _test_function_names()
    modules = {p.stem for p in TESTS.glob("test_*.py")}
    missing = []
    for doc in STATE_DOCS + [ROOT / "docs" / "denominator-methods.md"]:
        text = doc.read_text(encoding="utf-8")
        for name in re.findall(r"`?(test_[a-z0-9_]{6,})`?", text):
            if name in known or name in modules or name in RETIRED_TESTS:
                continue
            missing.append(f"{doc.name} references {name}, which does not exist")
    assert not missing, "\n".join(missing)


def test_retired_test_names_really_are_gone():
    """The allowlist must not quietly cover a test that still exists.

    Otherwise a live test could be listed as retired and the reference check
    would stop guarding it.
    """
    known = _test_function_names()
    still_here = [n for n in RETIRED_TESTS if n in known]
    assert not still_here, (
        f"{still_here} are listed as retired but still exist. Remove them from "
        f"RETIRED_TESTS."
    )


def test_paths_mentioned_in_prose_exist():
    """Catches a file renamed or removed without updating the prose."""
    # Backticked, concrete, repo-relative: no wildcards, no <placeholders>,
    # and a real extension or a trailing slash.
    pattern = re.compile(r"`((?:src|tests|data|docs|paper|figures)/[\w./-]+)`")
    missing = []
    for doc in STATE_DOCS + [ROOT / "docs" / "denominator-methods.md",
                             ROOT / "DATA.md"]:
        for path in set(pattern.findall(doc.read_text(encoding="utf-8"))):
            if "*" in path or "<" in path:
                continue
            if not (ROOT / path).exists():
                missing.append(f"{doc.name} references {path}, which does not exist")
    assert not missing, "\n".join(missing)


def test_stated_corroboration_count_matches_the_data():
    """"13 of 15 annual totals" is a claim the CSV can answer."""
    annual = pd.read_csv(ROOT / "data" / "raw" / "us_annual_deaths.csv")
    done = int(annual["corroborated_against"].notna().sum())
    total = len(annual)

    text = (ROOT / "README.md").read_text(encoding="utf-8")
    stated = re.search(r"(\d+) of (\d+) annual totals", text)
    assert stated, "README no longer states the corroboration count"
    assert (int(stated.group(1)), int(stated.group(2))) == (done, total), (
        f"README says {stated.group(0)}; the data has {done} of {total}."
    )


def test_readme_does_not_claim_the_data_is_unpopulated_or_unsigned():
    """The two specific sentences that went stale, as literal guards.

    Narrow on purpose. A general "is this sentence still true" check is not
    available, but the exact claims that have already rotted once are cheap to
    pin, and a reader who reintroduces one gets told.
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    annual = pd.read_csv(ROOT / "data" / "raw" / "us_annual_deaths.csv")

    if annual["deaths"].notna().all():
        assert "data files are intentionally empty" not in text
        assert "ship with citations and no values" not in text
    if annual["verified_by"].notna().all():
        assert "every row's `verified_by` is\nblank" not in text
        assert "will not run until you do" not in text


def test_the_module_table_lists_every_source_module():
    """A new module that no document mentions is invisible to a reader."""
    listed = set(re.findall(r"^\| `(\w+\.py)` \|",
                            (ROOT / "README.md").read_text(encoding="utf-8"),
                            re.MULTILINE))
    on_disk = {
        p.name for p in (ROOT / "src").glob("*.py")
        if p.name != "__init__.py"
    }
    assert on_disk - listed == set(), (
        f"README's module table omits {sorted(on_disk - listed)}"
    )
    assert listed - on_disk == set(), (
        f"README's module table lists modules that do not exist: "
        f"{sorted(listed - on_disk)}"
    )
