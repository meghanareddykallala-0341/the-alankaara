import pandas as pd
from pathlib import Path

folder = Path("boutique/ml/data")
source = folder / "alankaara_recommendation_dataset_v1.csv"
output = folder / "recommendation_label_review.csv"

df = pd.read_csv(source)

review = df[
    [
        "scenario_id",
        "product_name",
        "category",
        "price_inr",
        "user_occasion",
        "user_budget_max_inr",
        "user_weather",
        "user_preferred_style",
        "user_preferred_colour",
        "label",
    ]
].copy()

review["reviewed_label"] = ""
review["review_notes"] = ""
review.to_csv(output, index=False)

print(f"Created: {output}")
print(f"Rows to review: {len(review)}")
print("Original labels are preserved in the label column.")
