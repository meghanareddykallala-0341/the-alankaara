import pandas as pd
from pathlib import Path

folder = Path("boutique/ml/data")
file = folder / "alankaara_recommendation_dataset_budget_reviewed.csv"
df = pd.read_csv(file)

print("Rows:", len(df))
print("\nLabel counts:")
print(df["label"].value_counts())
print("\nMissing values:", int(df.isna().sum().sum()))
print("Duplicate rows:", int(df.duplicated().sum()))

over_budget = df[
    (df["price_inr"] > df["user_budget_max_inr"])
    & (df["label"] == "recommended")
]
print("Over-budget recommendations:", len(over_budget))

print("\nDataset validation complete.")
