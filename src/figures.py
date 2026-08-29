"""Figure generation. All figures write to figures/ as 300-dpi PNG."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
FIG_DIR.mkdir(exist_ok=True)

DPI = 300


def _save(fig, name: str) -> Path:
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_crude_vs_adjusted(crude, adjusted) -> Path:
    """The headline figure: crude and age-adjusted rates diverging."""
    df = crude.merge(adjusted, on="year")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(df["year"], df["crude_rate"], marker="o", label="Crude rate")
    ax.plot(df["year"], df["age_adjusted_rate"], marker="s",
            label="Age-adjusted rate (2000 std)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Deaths per 100,000")
    ax.set_title("U.S. mortality: crude vs age-adjusted")
    ax.legend()
    ax.grid(alpha=0.3)
    return _save(fig, "fig1_crude_vs_adjusted")


def fig_age_specific_rates(rates) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    for grp, sub in rates.groupby("age_group"):
        ax.plot(sub["year"], sub["rate"], marker="o", label=grp)
    ax.set_yscale("log")
    ax.set_xlabel("Year")
    ax.set_ylabel("Deaths per 100,000 (log scale)")
    ax.set_title("Age-specific mortality rates")
    ax.legend(title="Age group", fontsize=8)
    ax.grid(alpha=0.3, which="both")
    return _save(fig, "fig2_age_specific_rates")


def fig_excess(excess_table) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#c0392b" if v > 0 else "#2980b9"
              for v in excess_table["excess_deaths"]]
    ax.bar(excess_table["year"], excess_table["excess_deaths"], color=colors)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Year")
    ax.set_ylabel("Excess deaths vs baseline projection")
    ax.set_title("Excess mortality relative to pre-pandemic trend")
    ax.grid(alpha=0.3, axis="y")
    return _save(fig, "fig3_excess_mortality")


def fig_covid_by_age(share_table) -> Path:
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(share_table["age_group"], share_table["share_pct"], color="#8e44ad")
    ax.set_xlabel("Share of COVID-19 deaths (%)")
    ax.set_title("Distribution of COVID-19 deaths by age group")
    ax.grid(alpha=0.3, axis="x")
    return _save(fig, "fig4_covid_by_age")


def fig_decomposition(results) -> Path:
    """Stacked bar of rate effect vs age effect for each interval."""
    labels = [f"{r.year_start}-{r.year_end}" for r in results]
    rate = [r.rate_effect for r in results]
    age = [r.age_effect for r in results]
    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(labels))
    ax.bar(x, rate, label="Age-specific mortality effect", color="#2980b9")
    ax.bar(x, age, bottom=rate, label="Population aging effect", color="#e67e22")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("Contribution to crude-rate change (per 100,000)")
    ax.set_title("Kitagawa decomposition of crude-rate change")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    return _save(fig, "fig5_decomposition")
