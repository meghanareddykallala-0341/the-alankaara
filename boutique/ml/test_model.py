import joblib
import pandas as pd
from pathlib import Path

model_path = Path("boutique/ml/alankaara_model.joblib")
model = joblib.load(model_path)

sample = pd.DataFrame([{
    "category": "Kurti",
    "price_inr": 1299,
    "product_colour": "Mustard",
    "product_style": "Everyday ethnic",
    "fabric": "Cotton",
    "occasion_tags": "Casual, College",
    "weather_suitability": "Warm",
    "user_occasion": "College",
    "user_budget_max_inr": 2000,
    "user_weather": "Warm",
    "user_preferred_style": "Everyday ethnic",
    "user_preferred_colour": "Mustard",
}])

prediction = model.predict(sample)[0]
print("Sample prediction:", prediction)

if hasattr(model, "predict_proba"):
    probabilities = model.predict_proba(sample)[0]
    print("Class probabilities:")
    for label, probability in zip(model.classes_, probabilities):
        print(f"{label}: {probability:.1%}")

print("\nSample test complete.")
