"""Deterministically generate the two committed test fixtures.

Run with:  python scripts/generate_fixtures.py

Regenerates tests/fixtures/customer_segments.csv and tests/fixtures/house_prices.csv
from a fixed random seed. The resulting files are committed to the repository so
tests never depend on generating data at run time; re-run this script only if the
fixture design itself changes, and update the "known facts" documented below (and
in any tests that assert on them) to match.

customer_segments.csv (220 rows + 2 duplicated rows = 222 total)
  - 3 underlying customer segments with separable age/income/spending/visits
    centers (for clustering), each with a different membership-type mix.
  - `churned` is derived from a noisy risk score (membership type, spending
    score, visits per month) so the relationship is learnable but imperfect;
    the top ~35% highest-risk customers are labeled churned.
  - Exactly 6 missing values: 2 each in annual_income, spending_score, region
    (documented so profiling tests can assert on it directly).
  - Exactly 2 duplicate rows (full-row copies, including customer_id).

house_prices.csv (220 rows + 2 duplicated rows = 222 total)
  - price_usd is a noisy linear combination of area, bedrooms, age, distance
    to center, neighborhood premium and parking.
  - Exactly 6 missing values: 2 each in area_m2, neighborhood, has_parking.
  - Exactly 2 duplicate rows (full-row copies, including property_id).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def _inject_missing(df: pd.DataFrame, rng: np.random.Generator, column: str, count: int, excluded_index: set[int]) -> None:
    eligible = [i for i in df.index if i not in excluded_index and pd.notna(df.at[i, column])]
    chosen = rng.choice(eligible, size=count, replace=False)
    df.loc[chosen, column] = np.nan
    excluded_index.update(chosen)


def generate_customer_segments(rng: np.random.Generator) -> pd.DataFrame:
    segment_sizes = [80, 80, 60]
    segment_params = [
        # age_mean, age_sd, income_mean, income_sd, spend_mean, spend_sd, visits_mean, visits_sd
        (26, 4, 28000, 4500, 28, 9, 2.0, 0.8),
        (41, 5, 58000, 7000, 55, 10, 5.0, 1.3),
        (56, 6, 95000, 11000, 80, 9, 8.0, 1.8),
    ]
    membership_choices = [
        ["Basic", "Silver"],
        ["Silver", "Gold"],
        ["Gold", "Silver"],
    ]
    regions = ["North", "South", "East", "West"]

    rows: list[dict[str, object]] = []
    for size, params, memberships in zip(segment_sizes, segment_params, membership_choices):
        age_mean, age_sd, inc_mean, inc_sd, spend_mean, spend_sd, visit_mean, visit_sd = params
        ages = rng.normal(age_mean, age_sd, size).round().clip(18, 75).astype(int)
        incomes = rng.normal(inc_mean, inc_sd, size).round(2).clip(12000, None)
        spend = rng.normal(spend_mean, spend_sd, size).round(1).clip(0, 100)
        visits = rng.normal(visit_mean, visit_sd, size).round(1).clip(0, None)
        chosen_memberships = rng.choice(memberships, size=size)
        chosen_regions = rng.choice(regions, size=size)

        for i in range(size):
            rows.append(
                {
                    "age": int(ages[i]),
                    "annual_income": float(incomes[i]),
                    "spending_score": float(spend[i]),
                    "visits_per_month": float(visits[i]),
                    "membership_type": chosen_memberships[i],
                    "region": chosen_regions[i],
                }
            )

    df = pd.DataFrame(rows)

    membership_risk = df["membership_type"].map({"Basic": 3.0, "Silver": 1.0, "Gold": 0.0})
    risk = (
        membership_risk
        + (60 - df["spending_score"]) * 0.04
        + (5 - df["visits_per_month"]) * 0.5
        + rng.normal(0, 1.5, len(df))
    )
    threshold = np.quantile(risk, 0.65)
    df["churned"] = (risk > threshold).astype(int)

    shuffled_order = rng.permutation(len(df))
    df = df.iloc[shuffled_order].reset_index(drop=True)
    df.insert(0, "customer_id", [f"CUST{i + 1:04d}" for i in range(len(df))])

    duplicate_source_positions = [10, 50]
    duplicate_rows = df.iloc[duplicate_source_positions].copy()

    excluded_index: set[int] = set(duplicate_source_positions)
    _inject_missing(df, rng, "annual_income", 2, excluded_index)
    _inject_missing(df, rng, "spending_score", 2, excluded_index)
    _inject_missing(df, rng, "region", 2, excluded_index)

    df = pd.concat([df, duplicate_rows], ignore_index=True)
    final_order = rng.permutation(len(df))
    return df.iloc[final_order].reset_index(drop=True)


def generate_house_prices(rng: np.random.Generator) -> pd.DataFrame:
    n = 220
    neighborhoods = ["Downtown", "Riverside", "Hillside", "Suburb"]
    neighborhood_premium = {"Downtown": 45000, "Riverside": 30000, "Hillside": 20000, "Suburb": 0}

    area_m2 = rng.normal(120, 40, n).clip(35, 320).round(1)
    bedrooms = (area_m2 / 45 + rng.normal(0, 0.4, n)).round().clip(1, 6).astype(int)
    age_years = rng.uniform(0, 45, n).round(1)
    distance_to_center_km = rng.exponential(6, n).clip(0.3, 30).round(2)
    neighborhood = rng.choice(neighborhoods, size=n, p=[0.25, 0.25, 0.2, 0.3])
    has_parking = rng.choice(["yes", "no"], size=n, p=[0.65, 0.35])

    premium = np.array([neighborhood_premium[n_] for n_ in neighborhood])
    parking_bonus = np.where(has_parking == "yes", 12000, 0)
    noise = rng.normal(0, 18000, n)

    price_usd = (
        40000
        + area_m2 * 950
        + bedrooms * 8000
        - age_years * 900
        - distance_to_center_km * 1200
        + premium
        + parking_bonus
        + noise
    )
    price_usd = np.clip(price_usd, 25000, None).round(-2)

    df = pd.DataFrame(
        {
            "area_m2": area_m2,
            "bedrooms": bedrooms,
            "age_years": age_years,
            "distance_to_center_km": distance_to_center_km,
            "neighborhood": neighborhood,
            "has_parking": has_parking,
            "price_usd": price_usd,
        }
    )
    df.insert(0, "property_id", [f"PROP{i + 1:04d}" for i in range(len(df))])

    duplicate_source_positions = [15, 75]
    duplicate_rows = df.iloc[duplicate_source_positions].copy()

    excluded_index: set[int] = set(duplicate_source_positions)
    _inject_missing(df, rng, "area_m2", 2, excluded_index)
    _inject_missing(df, rng, "neighborhood", 2, excluded_index)
    _inject_missing(df, rng, "has_parking", 2, excluded_index)

    df = pd.concat([df, duplicate_rows], ignore_index=True)
    final_order = rng.permutation(len(df))
    return df.iloc[final_order].reset_index(drop=True)


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)
    customer_segments = generate_customer_segments(rng)
    house_prices = generate_house_prices(rng)

    customer_segments.to_csv(FIXTURES_DIR / "customer_segments.csv", index=False)
    house_prices.to_csv(FIXTURES_DIR / "house_prices.csv", index=False)

    print(f"customer_segments.csv: {len(customer_segments)} rows, "
          f"{customer_segments.duplicated().sum()} duplicate rows, "
          f"{int(customer_segments.isna().sum().sum())} missing cells, "
          f"churn rate {customer_segments['churned'].mean():.2%}")
    print(f"house_prices.csv: {len(house_prices)} rows, "
          f"{house_prices.duplicated().sum()} duplicate rows, "
          f"{int(house_prices.isna().sum().sum())} missing cells, "
          f"price range ${house_prices['price_usd'].min():,.0f}-${house_prices['price_usd'].max():,.0f}")


if __name__ == "__main__":
    main()
