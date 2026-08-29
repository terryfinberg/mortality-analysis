import pandas as pd

from src import rates


def test_crude_rate_basic():
    deaths = pd.DataFrame({"year": [2020], "deaths": [1000]})
    pop = pd.DataFrame({"year": [2020], "population": [1_000_000]})
    out = rates.crude_rate(deaths, pop)
    assert out.loc[0, "crude_rate"] == 100.0


def test_age_specific_rates(by_age_stationary):
    out = rates.age_specific_rates(by_age_stationary)
    row = out[(out["year"] == 2000) & (out["age_group"] == "85+")].iloc[0]
    assert row["rate"] == 5000.0


def test_population_shares_sum_to_one(by_age_stationary):
    shares = rates.population_shares(by_age_stationary)
    for _, sub in shares.groupby("year"):
        assert abs(sub["share"].sum() - 1.0) < 1e-12


def test_age_adjusted_equals_crude_when_structure_matches_standard(standard_pop):
    """If the population has exactly the standard age structure, the
    age-adjusted rate must equal the crude rate."""
    total = 10_000_000
    rows = []
    for age, w in standard_pop.items():
        pop = int(total * w / 1_000_000)
        rows.append({"year": 2020, "age_group": age,
                     "deaths": int(pop * 0.01), "population": pop})
    by_age = pd.DataFrame(rows)

    adj = rates.age_adjusted_rate(by_age, standard_pop)
    crude = by_age["deaths"].sum() / by_age["population"].sum() * 100_000
    assert abs(adj.loc[0, "age_adjusted_rate"] - crude) < 1.0
