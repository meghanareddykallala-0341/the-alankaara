import pandas as pd
from pathlib import Path

folder = Path("boutique/ml/data")
df = pd.read_csv(folder / "alankaara_recommendation_dataset_v1.csv")

# Find products outside the user's budget that were marked recommended
budget_issue = df[
    (df["price_inr"] > df["user_budget_max_inr"])
    & (df["label"] == "recommended")
].copy()

# Find products whose category may not suit the stated occasion
occasion_map = {
    "Office": {"Kurti", "Saree", "Coord set", "Footwear", "Handbag", "Jewellery"},
    "College": {"Kurti", "Coord set", "Footwear", "Handbag", "Jewellery", "Saree"},
    "Wedding": {"Saree", "Lehenga", "Anarkali", "Jewellery", "Dupatta", "Footwear", "Handbag", "Blouse"},
    "Festive": {"Saree", "Lehenga", "Anarkali", "Kurti", "Indo-western", "Jewellery", "Dupatta", "Footwear", "Handbag", "Blouse"},
    "Party": {"Saree", "Lehenga", "Anarkali", "Coord set", "Indo-western", "Jewellery", "Footwear", "Handbag", "Blouse"},
    "Casual": {"Kurti", "Coord set", "Footwear", "Handbag", "Jewellery", "Saree"},
    "Travel": {"Kurti", "Coord set", "Footwear", "Handbag"},
    "Family function": {"Saree", "Lehenga", "Anarkali", "Kurti", "Indo-western", "Jewellery", "Dupatta", "Footwear", "Handbag", "Blouse"},
}

df["occasion_mismatch_flag"] = df.apply(
    lambda r: r["category"] not in occasion_map.get(r["user_occasion"], set()),
    axis=1,
)

occasion_issue = df[
    df["occasion_mismatch_flag"] & (df["label"] == "recommended")
].copy()

cols = [
    "scenario_id", "product_name", "category", "price_inr",
    "user_occasion", "user_budget_max_inr", "label"
]

budget_issue[cols].to_csv(folder / "budget_label_flags.csv", index=False)
occasion_issue[cols].to_csv(folder / "occasion_label_flags.csv", index=False)

print("Recommended items over budget:", len(budget_issue))
print("Potential occasion mismatches:", len(occasion_issue))
print("\nSaved budget flags to budget_label_flags.csv")
print("Saved occasion flags to occasion_label_flags.csv")
print("\nFirst 20 over-budget recommendations:")
print(budget_issue[cols].head(20).to_string(index=False))
