import pandas as pd
from pathlib import Path

folder = Path("boutique/ml/data")

source = folder / "alankaara_recommendation_dataset_budget_reviewed.csv"
flags = folder / "occasion_label_flags.csv"
output = folder / "alankaara_training_dataset_v1.csv"

df = pd.read_csv(source)
flagged = pd.read_csv(flags)

before = len(df)
df = df[~df["scenario_id"].isin(flagged["scenario_id"])].copy()

df.to_csv(output, index=False)

print("Original reviewed rows:", before)
print("Rows held out for occasion review:", before - len(df))
print("Training rows:", len(df))
print("Missing values:", int(df.isna().sum().sum()))
print("Duplicate rows:", int(df.duplicated().sum()))
print("Saved:", output)
print("Note: This is a provisional dataset with synthetic labels.")
