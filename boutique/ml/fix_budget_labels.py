import pandas as pd
from pathlib import Path

folder = Path("boutique/ml/data")
df = pd.read_csv(folder / "alankaara_recommendation_dataset_v1.csv")

# Keep the original dataset unchanged.
# Mark over-budget recommendations as not recommended in a separate copy.
mask = (
    (df["price_inr"] > df["user_budget_max_inr"])
    & (df["label"] == "recommended")
)

print("Labels to review:", int(mask.sum()))
df.loc[mask, "label"] = "not_recommended"
df.loc[mask, "label_note"] = "Changed: product exceeds user's budget"

output = folder / "alankaara_recommendation_dataset_budget_reviewed.csv"
df.to_csv(output, index=False)

print("Saved:", output)
print("Remaining over-budget recommendations:",
      int(((df["price_inr"] > df["user_budget_max_inr"]) &
           (df["label"] == "recommended")).sum()))
print("Original dataset was not changed.")
