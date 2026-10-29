
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
FILE = DATA_DIR / "alankaara_recommendation_dataset_v1.csv"

df = pd.read_csv(FILE)

print("\n=== ALANKAARA DATASET REVIEW ===")
print("\nTotal rows:", len(df))
print("\nLabel counts:")
print(df["label"].value_counts())

print("\n=== SAMPLE RECOMMENDATIONS ===")
columns = [
    "product_name",
    "category",
    "price_inr",
    "user_occasion",
    "user_budget_max_inr",
    "user_weather",
    "label",
]

print(df[columns].head(20).to_string(index=False))

# Save a copy for manual label review
review_file = DATA_DIR / "recommendation_label_review.csv"

df[[
    "scenario_id",
    "product_id",
    "product_name",
    "category",
    "price_inr",
    "user_occasion",
    "user_budget_max_inr",
    "user_weather",
    "user_preferred_style",
    "user_preferred_colour",
    "label",
    "label_note",
]].to_csv(review_file, index=False)

print("\nReview file created:", review_file)
print("Open this CSV in Excel and review the labels.")
