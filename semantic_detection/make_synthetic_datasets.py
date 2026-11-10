"""Synthetic test datasets for the semantic / target / problem-type detector.

Usage:  python make_synthetic_datasets.py     (writes CSV files to ./synthetic)
Tests:  from make_synthetic_datasets import build; build()["name"]
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_FOLDER = Path(__file__).resolve().parent / "synthetic"


def build(seed=42):
    rng = np.random.default_rng(seed)
    data = {}

    # 1. Classification: customer churn (target = churn, last column)
    n = 500
    data["churn_classification.csv"] = pd.DataFrame({
        "customer_id": np.arange(1, n + 1),
        "age": rng.integers(18, 76, n),
        "monthly_spend": rng.normal(60, 20, n).round(2),
        "num_orders": rng.integers(0, 40, n),
        "support_tickets": rng.integers(0, 9, n),
        "signup_date": pd.date_range("2020-01-01", periods=n, freq="D"),
        "email": [f"user{i}@example.com" for i in range(n)],
        "contact": [f"425-555-{1000 + i:04d}" for i in range(n)],
        "churn": rng.binomial(1, 0.2, n),
    })

    # 2. Regression: house price (target = price)
    n = 400
    area = rng.integers(500, 4000, n)
    data["house_price_regression.csv"] = pd.DataFrame({
        "house_id": np.arange(1, n + 1),
        "area_sqft": area,
        "bedrooms": rng.integers(1, 6, n),
        "city": rng.choice(["Pune", "Mysuru", "Hubli", "Mangaluru"], n),
        "year_built": rng.integers(1980, 2024, n),
        "price": (area * 150 + rng.normal(0, 20000, n)).round(0),
    })

    # 3. Forecasting: monthly sales (date + numeric targets)
    months = pd.date_range("2023-01-01", periods=24, freq="MS")
    rows = []
    for product in ["A", "B", "C"]:
        for region in ["North", "South"]:
            for i, month in enumerate(months):
                units = int(100 + 3 * i + rng.integers(-10, 10))
                rows.append({
                    "date": month, "product": product, "region": region,
                    "units_sold": units,
                    "revenue": round(units * 25.5, 2),
                })
    data["sales_forecasting.csv"] = pd.DataFrame(rows)

    # 4. Clustering: no obvious target
    n = 300
    data["customer_segments_clustering.csv"] = pd.DataFrame({
        "customer_id": np.arange(1, n + 1),
        "age": rng.integers(18, 70, n),
        "annual_income": rng.normal(60000, 15000, n).round(0),
        "spending_score": rng.integers(1, 100, n),
        "gender": rng.choice(["Male", "Female"], n),
    })

    # 5. Ambiguous / poorly populated columns
    n = 200
    amount = rng.normal(500, 100, n).round(2)
    amount[rng.choice(n, 120, replace=False)] = np.nan
    data["ambiguous_targets.csv"] = pd.DataFrame({
        "record_id": np.arange(1, n + 1),
        "score": rng.integers(0, 101, n),
        "status": rng.choice(["Open", "Closed", "Pending"], n),
        "level": rng.integers(1, 6, n),
        "notes": ["Follow-up call scheduled with the customer about "
                  "an unresolved billing question and refund request."] * n,
        "pct_complete": [f"{p}%" for p in rng.integers(0, 101, n)],
        "is_active": rng.choice(["Y", "N"], n),
        "amount": amount,
        "constant_col": [5] * n,
        "empty_col": [np.nan] * n,
    })
    # 6. Anomaly detection: card transactions, a few extreme amounts,
    #    no label column
    n = 1000
    amount = rng.normal(80, 25, n).clip(5, None).round(2)
    items = rng.integers(1, 8, n)
    hour = rng.integers(0, 24, n)
    outliers = rng.choice(n, 15, replace=False)
    amount[outliers] = rng.uniform(2500, 9000, 15).round(2)
    items[outliers] = rng.integers(40, 90, 15)
    data["transactions_anomaly.csv"] = pd.DataFrame({
        "transaction_id": np.arange(1, n + 1),
        "amount": amount,
        "num_items": items,
        "hour_of_day": hour,
        "merchant_category": rng.choice(
            ["Grocery", "Fuel", "Online", "Travel", "Dining"], n),
    })

    # 7. Recommendation: users rate items
    n = 800
    data["ratings_recommendation.csv"] = pd.DataFrame({
        "user_id": rng.integers(1, 101, n),
        "item_id": rng.integers(1, 61, n),
        "rating": rng.integers(1, 6, n),
        "rated_on": pd.date_range("2024-01-01", periods=n, freq="6h"),
    })
    return data


def main():
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    for name, frame in build().items():
        frame.to_csv(OUTPUT_FOLDER / name, index=False)
        print(f"Wrote {name}  ({len(frame)} rows, {len(frame.columns)} columns)")


if __name__ == "__main__":
    main()
