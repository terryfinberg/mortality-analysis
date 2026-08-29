"""Data loading with fail-loud validation.

Design principle: this module refuses to hand back a partially populated
dataset. Every downstream calculation assumes complete, verified inputs,
so an incomplete CSV raises rather than silently propagating NaN into a
figure or a manuscript number.

Populate the CSVs in data/raw/ from the primary sources cited in each
row's source_citation column before running anything else. See
UAT_CHECKLIST.md section 1.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

AGE_GROUPS = ["0-24", "25-44", "45-64", "65-74", "75-84", "85+"]


class IncompleteDataError(RuntimeError):
    """Raised when a required CSV has missing values.

    This is deliberately fatal. An analysis run on partial data produces
    numbers that look authoritative and are not.
    """


class UnverifiedDataError(RuntimeError):
    """Raised in strict mode when rows lack a verified_by attestation."""


def _require_complete(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = df[df[cols].isna().any(axis=1)]
    if not missing.empty:
        n = len(missing)
        preview = missing.head(5).to_string(index=False)
        raise IncompleteDataError(
            f"{name}: {n} row(s) have missing values in {cols}.\n"
            f"Populate data/raw/ from the cited primary sources first.\n"
            f"First offending rows:\n{preview}"
        )


def _require_verified(df: pd.DataFrame, name: str) -> None:
    if "verified_by" not in df.columns:
        return
    unver = df[df["verified_by"].isna() | (df["verified_by"].astype(str).str.strip() == "")]
    if not unver.empty:
        raise UnverifiedDataError(
            f"{name}: {len(unver)} row(s) have no verified_by attestation. "
            f"Strict mode requires each value to be signed off against its "
            f"source_citation. Re-run with strict=False to bypass during "
            f"development, but never for a figure or manuscript build."
        )


def load_annual_deaths(strict: bool = True) -> pd.DataFrame:
    """Total U.S. deaths by year. Returns columns: year, deaths, status."""
    df = pd.read_csv(DATA_DIR / "us_annual_deaths.csv")
    _require_complete(df, ["deaths"], "us_annual_deaths.csv")
    if strict:
        _require_verified(df, "us_annual_deaths.csv")
    df["deaths"] = df["deaths"].astype(int)
    return df[["year", "deaths", "status"]].sort_values("year").reset_index(drop=True)


def load_population(strict: bool = True) -> pd.DataFrame:
    """Mid-year U.S. resident population by year."""
    df = pd.read_csv(DATA_DIR / "us_population.csv")
    _require_complete(df, ["population"], "us_population.csv")
    if strict:
        _require_verified(df, "us_population.csv")
    df["population"] = df["population"].astype(int)
    return df[["year", "population"]].sort_values("year").reset_index(drop=True)


def load_deaths_by_age(strict: bool = True) -> pd.DataFrame:
    """Deaths and population by year and age group (long format)."""
    df = pd.read_csv(DATA_DIR / "deaths_by_age.csv")
    _require_complete(df, ["deaths", "population"], "deaths_by_age.csv")
    if strict:
        _require_verified(df, "deaths_by_age.csv")
    bad = set(df["age_group"]) - set(AGE_GROUPS)
    if bad:
        raise ValueError(f"deaths_by_age.csv has unexpected age groups: {sorted(bad)}")
    df["deaths"] = df["deaths"].astype(int)
    df["population"] = df["population"].astype(int)
    return df[["year", "age_group", "deaths", "population"]]


def load_covid_deaths_by_age(strict: bool = True) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "covid_deaths_by_age.csv")
    _require_complete(df, ["covid_deaths"], "covid_deaths_by_age.csv")
    if strict:
        _require_verified(df, "covid_deaths_by_age.csv")
    df["covid_deaths"] = df["covid_deaths"].astype(int)
    return df[["year", "age_group", "covid_deaths"]]


def load_standard_population() -> pd.Series:
    """2000 U.S. Standard Population weights, indexed by age group.

    Weights sum to 1,000,000 by construction; this is asserted on load
    because a transcription error here silently biases every
    age-adjusted rate in the analysis.
    """
    df = pd.read_csv(DATA_DIR / "standard_population_2000.csv")
    s = df.set_index("age_group")["weight_per_million"]
    total = int(s.sum())
    if total != 1_000_000:
        raise ValueError(
            f"Standard population weights sum to {total:,}, expected 1,000,000. "
            f"Check against NCHS Statistical Notes No. 20, Table 1."
        )
    return s.reindex(AGE_GROUPS)


@dataclass
class Dataset:
    """Everything the analysis needs, loaded and validated together."""

    annual_deaths: pd.DataFrame
    population: pd.DataFrame
    by_age: pd.DataFrame
    covid_by_age: pd.DataFrame
    standard_pop: pd.Series

    @property
    def years(self) -> list[int]:
        return sorted(self.annual_deaths["year"].unique().tolist())


def load_all(strict: bool = True) -> Dataset:
    return Dataset(
        annual_deaths=load_annual_deaths(strict),
        population=load_population(strict),
        by_age=load_deaths_by_age(strict),
        covid_by_age=load_covid_deaths_by_age(strict),
        standard_pop=load_standard_population(),
    )
