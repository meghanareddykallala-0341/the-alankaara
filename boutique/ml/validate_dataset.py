import pandas as pd
from pathlib import Path

DATA_DIR = Path("boutique/ml/data")

dataset = pd.read_csv(DATA_DIR / "alankaara_recommendation_dataset_v1.csv")
catalogue = pd.read_csv(DATA_DIR / "alankaara_product_catalog_seed_v1.csv")

print("=== ALANKAARA DATASET VALIDATION ===")
print("Recommendation rows:", len(dataset))
print("Catalogue products:", len(catalogue))
print("Missing values:", dataset.isnull().sum().sum())
print("Duplicate rows:", dataset.duplicated().sum())
print("Duplicate scenario IDs:", dataset["scenario_id"].duplicated().sum())
print("\nLabel counts:")
print(dataset["label"].value_counts())
print("\nProduct data sources:")
print(catalogue["data_source"].value_counts())
print("\nLabels by product:")
print(dataset.groupby("product_id")["label"].nunique().value_counts())

missing_products = set(dataset["product_id"]) - set(catalogue["product_id"])
print("\nProducts missing from catalogue:", missing_products)

assert dataset.isnull().sum().sum() == 0, "Missing values found"
assert dataset.duplicated().sum() == 0, "Duplicate rows found"
assert dataset["scenario_id"].is_unique, "Duplicate scenario IDs found"
assert not missing_products, "Dataset contains products absent from catalogue"

print("\nBasic validation passed.")
print("Note: labels are heuristic-generated and need review before model training.")
